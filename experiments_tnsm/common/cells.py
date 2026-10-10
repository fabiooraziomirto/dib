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


def parse_reps(spec: str) -> list[tuple[int, int]]:
    """'1:10,10:10,50:10,100:20' -> [(1,0)..(1,9),(10,0)..,(100,19)]."""
    cells = []
    for part in spec.split(","):
        n, r = (int(x) for x in part.split(":"))
        cells += [(n, i) for i in range(r)]
    return cells


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


def run_cells(args, out: Path, run_cell, files: list[Path]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    code = Path(args.code).resolve()
    cells = parse_reps(args.reps)
    random.Random(args.seed).shuffle(cells)
    manifest = manifest_base(args, code, files)
    manifest["cell_order"] = cells
    rule = manifest["discard_rule"]
    tmp = Path(args.tmp_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    log = (out / "cells.jsonl").open("a")
    stopped = None
    for k, (n, rep) in enumerate(cells):
        free = nm.disk_free_mb()
        if free < args.min_free_mb:
            stopped = f"disk free {free} MB < {args.min_free_mb} MB before cell {k}"
            break
        before = nm.short_window(2.0)
        db = tmp / f"cell_{k}.db"
        a = nm.Snapshot(nm.own_pids())
        t0 = time.time()
        result = run_cell(n, db)
        b = nm.Snapshot(nm.own_pids())
        during = nm.window(a, b)
        for suffix in ("", "-wal", "-shm", "-journal"):
            Path(f"{db}{suffix}").unlink(missing_ok=True)
        after = nm.short_window(2.0)
        flag, reasons = disturbed(rule, during)
        rec = {"cell": k, "n_workers": n, "rep": rep, "t_start_unix": round(t0, 2),
               "result": result, "monitor": {"before": before, "during": during, "after": after},
               "disk_free_mb_before": free, "disk_free_mb_after": nm.disk_free_mb(),
               "disturbed": flag, "disturbed_reasons": reasons}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(f"[cell {k + 1}/{len(cells)}] n={n} rep={rep} disturbed={flag} "
              f"{ {kk: v for kk, v in result.items() if kk in ('throughput', 'p99_ms')} }", flush=True)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["stopped_reason"] = stopped
    manifest["cells_completed"] = sum(1 for _ in (out / "cells.jsonl").open())
    manifest["disk_free_mb_at_end"] = nm.disk_free_mb()
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
