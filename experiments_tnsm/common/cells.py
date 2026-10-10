"""Shared cell loop for M1 and M2 (audit 04 sez. 2): randomized order, fresh SQLite database
per cell, background-load monitoring before/during/after each cell, disk guard, manifest.

A *cell* is one (writers, repetition) pair: one call of the unmodified harness function
``fsm_concurrency_harness.run_throughput_sweep(get_session, [n], ops, warmup_ops, repeats=1)``
on a new database, so warm-up and seeding are the harness's own. Nothing is discarded
here: every cell is written to cells.jsonl with its monitor readings and the flag of the
discard rule fixed beforehand (discard_rule.json, audit 04 sez. 7.2).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import node_monitor as nm  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_rule() -> dict:
    return json.loads((HERE / "discard_rule.json").read_text())


def disturbed(rule: dict, during: dict) -> tuple[bool, list[str]]:
    reasons = []
    if during["other_cores"] > rule["max_other_cores"]:
        reasons.append(f"other_cores {during['other_cores']} > {rule['max_other_cores']}")
    if during["steal_pct"] > rule["max_steal_pct"]:
        reasons.append(f"steal_pct {during['steal_pct']} > {rule['max_steal_pct']}")
    return bool(reasons), reasons


def parse_reps(spec: str) -> list[tuple]:
    """'1:10,100:20' -> [(1,0)..(1,9),(100,0)..(100,19)];
    'threads:100:20,null:100:10' -> [(("threads",100),0).., (("null",100),0)..]."""
    cells = []
    for part in spec.split(","):
        bits = part.split(":")
        if len(bits) == 2:
            key, r = int(bits[0]), int(bits[1])
        else:
            key, r = (bits[0], int(bits[1])), int(bits[2])
        cells += [(key, i) for i in range(r)]
    return cells


def sqlite_settings(harness, db: Path) -> dict:
    """journal_mode, synchronous, busy_timeout and pool parameters of the engine the
    harness builds (default configuration), probed on a throw-away database."""
    import dib.registry.db as db_module

    harness.fresh_engine(db)
    engine = db_module._engine
    with engine.connect() as c:
        out = {k: c.exec_driver_sql(f"PRAGMA {k}").scalar() for k in ("journal_mode", "synchronous", "busy_timeout")}
    pool = engine.pool
    out.update({"pool_class": type(pool).__name__, "pool_size": pool.size(),
                "pool_max_overflow": getattr(pool, "_max_overflow", None),
                "pool_timeout_s": getattr(pool, "_timeout", None),
                "DIB_SQLITE_WAL": os.environ.get("DIB_SQLITE_WAL", ""),
                "DIB_SQLITE_POOL_SIZE": os.environ.get("DIB_SQLITE_POOL_SIZE", "")})
    engine.dispose()
    db_module._engine = None
    db_module._SessionLocal = None
    for suffix in ("", "-wal", "-shm", "-journal"):
        Path(f"{db}{suffix}").unlink(missing_ok=True)
    return out


def manifest_base(args, code: Path, files: list[Path]) -> dict:
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    return {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv,
        "commit": args.commit,
        "seed": args.seed,
        "python_vv": sys.version.replace("\n", " "),
        "python_executable": sys.executable,
        "sqlite_version": __import__("sqlite3").sqlite_version,
        "pip_freeze": freeze.splitlines(),
        "host": nm.host_info(),
        "uptime_load_at_start": open("/proc/loadavg").read().strip(),
        "disk_free_mb_at_start": nm.disk_free_mb(),
        "sha256": {str(f.relative_to(code.parent) if code.parent in f.parents else f): sha256(f) for f in files},
        "discard_rule": load_rule(),
        "g4_host_quiet": "NOT satisfied: k3s server, a registry container and other user sessions run on the "
                         "node (audit 04 sez. 7.2); background load is recorded per cell and the discard "
                         "rule is applied in the analysis, never silently",
    }


def run_cells(args, out: Path, run_cell, files: list[Path], sqlite_probe=None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    code = Path(args.code).resolve()
    cells = parse_reps(args.reps)
    random.Random(args.seed).shuffle(cells)
    manifest = manifest_base(args, code, files)
    manifest["cell_order"] = cells
    rule = manifest["discard_rule"]
    tmp = Path(args.tmp_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    manifest["filesystem"] = nm.fs_info(str(tmp))
    manifest["fsync_bench_before"] = nm.fsync_bench(str(tmp))
    if sqlite_probe is not None:
        manifest["sqlite"] = sqlite_probe(tmp / "probe.db")
    log = (out / "cells.jsonl").open("a")
    stopped = None
    for k, (spec, rep) in enumerate(cells):
        n = spec[1] if isinstance(spec, tuple) else spec
        free = nm.disk_free_mb()
        if free < args.min_free_mb:
            stopped = f"disk free {free} MB < {args.min_free_mb} MB before cell {k}"
            break
        before = nm.short_window(2.0)
        db = tmp / f"cell_{k}.db"
        a = nm.Snapshot(nm.own_pids())
        t0 = time.time()
        result = run_cell(spec, db)
        b = nm.Snapshot(nm.own_pids())
        during = nm.window(a, b)
        for suffix in ("", "-wal", "-shm", "-journal"):
            Path(f"{db}{suffix}").unlink(missing_ok=True)
        after = nm.short_window(2.0)
        flag, reasons = disturbed(rule, during)
        rec = {"cell": k, "n_workers": n, "mode": spec[0] if isinstance(spec, tuple) else "threads", "rep": rep, "t_start_unix": round(t0, 2),
               "result": result, "monitor": {"before": before, "during": during, "after": after},
               "disk_free_mb_before": free, "disk_free_mb_after": nm.disk_free_mb(),
               "disturbed": flag, "disturbed_reasons": reasons}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(f"[cell {k + 1}/{len(cells)}] {spec} rep={rep} disturbed={flag} "
              f"{ {kk: v for kk, v in result.items() if kk in ('throughput', 'p99_ms')} }", flush=True)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["stopped_reason"] = stopped
    manifest["cells_completed"] = sum(1 for _ in (out / "cells.jsonl").open())
    manifest["disk_free_mb_at_end"] = nm.disk_free_mb()
    manifest["fsync_bench_after"] = nm.fsync_bench(str(tmp))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"done: {manifest['cells_completed']} cells, stopped={stopped}", flush=True)


def common_args(p) -> None:
    p.add_argument("--code", required=True, help="deployed code/ directory (contains src/ and scripts/)")
    p.add_argument("--out", required=True)
    p.add_argument("--commit", required=True, help="git commit of the deployed tree")
    p.add_argument("--seed", type=int, default=20261010)
    p.add_argument("--reps", default="1:10,10:10,50:10,100:20")
    p.add_argument("--ops-per-worker", type=int, default=200)
    p.add_argument("--warmup-ops", type=int, default=20)
    p.add_argument("--tmp-dir", default="/tmp/dib_tnsm_db")
    p.add_argument("--min-free-mb", type=int, default=2000)


ARMS = ("default", "deploy")


def set_arm(arm: str, n: int) -> dict:
    """Engine configuration arm (plan rev. 5, Passo 7), through the existing opt-in
    environment variables only (code/src/dib/registry/db.py:244-262), set before the engine
    of the cell is built (fresh() disposes and rebuilds it):
      default  DIB_SQLITE_WAL and DIB_SQLITE_POOL_SIZE unset (journal_mode=delete,
               busy_timeout 5 s, QueuePool 5 + 10 overflow, checkout timeout 30 s);
      deploy   DIB_SQLITE_WAL=1 (WAL, busy_timeout 30 s, synchronous FULL) and
               DIB_SQLITE_POOL_SIZE=max(n, 5) (pool n + overflow n >= writers).
    Returns the values set, recorded in each cell."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    for k in ("DIB_SQLITE_WAL", "DIB_SQLITE_POOL_SIZE"):
        os.environ.pop(k, None)
    if arm == "deploy":
        os.environ["DIB_SQLITE_WAL"] = "1"
        os.environ["DIB_SQLITE_POOL_SIZE"] = str(max(n, 5))
    return {k: os.environ.get(k, "") for k in ("DIB_SQLITE_WAL", "DIB_SQLITE_POOL_SIZE")}


def import_harness(code: Path):
    sys.path.insert(0, str(code / "src"))
    sys.path.insert(0, str(code / "scripts"))
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    import fsm_concurrency_harness as harness  # noqa: E402

    return harness


def fresh(harness, db: Path):
    import dib.registry.db as db_module

    if db_module._engine is not None:
        db_module._engine.dispose()
    harness.fresh_engine(db)
    return harness.new_session_factory()
