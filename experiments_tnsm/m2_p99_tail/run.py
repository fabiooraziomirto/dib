"""M2 (audit 04 sez. 2, reformulated 2026-10-10 before launch): where the single-node p99
tail comes from, on the free node, with two GIL controls.

Configuration under test (default engine, DIB_SQLITE_WAL unset; recorded per run in the
manifest): SQLite journal_mode=delete, synchronous=FULL (2), busy_timeout=5000 ms
(pysqlite default); SQLAlchemy QueuePool pool_size=5, max_overflow=10, pool timeout 30 s.
M1 showed a p99 equal to 30.0 s at 100 writers: that is the pool checkout timeout, a
ceiling, not a latency.

Arm (plan rev. 5, Passo 7, added 2026-10-10 before launch): M2 runs on the DEPLOY arm by
default (--arm deploy: DIB_SQLITE_WAL=1, DIB_SQLITE_POOL_SIZE=max(writers, 5), set through
common/cells.py:set_arm before each cell's engine is built); the configuration paragraph
above describes the default arm, kept selectable with --arm default. The hypotheses below
are unchanged and apply to the arm that is run (recorded in the manifest and in each cell).

Cells (randomized together with --seed, fresh SQLite database per cell, 200 timed ops per
worker after a discarded warm-up of 20 per worker):
  threads    the unmodified harness (fsm_concurrency_harness.run_throughput_sweep, OS
             threads, one shared engine and pool) with the timing decomposition of
             instrument.py; writers 1, 10, 50 x 10 cells, 100 x 20 cells;
  null       GIL control (a): the same harness and threads with timed_call replaced by a
             no-op (no session, no SQLite); 100 threads x 10 cells -> ceiling of harness+GIL;
  processes  GIL control (b): one OS process per writer (fork), each with its own engine and
             pool on the same database file, running the harness's operation mix (do_op
             replicated from fsm_concurrency_harness.py:150-178, worker_id = process index);
             writers 10, 50, 100 x 10 cells. Removes both the GIL and the shared pool.

Per cell (instrument.py): error rate by type (TimeoutError = pool checkout timeout;
OperationalError = SQLite busy timeout), throughput of (i) all ops (the harness's
number), (ii) ops without error, counting InvalidStateTransition (business rejection)
as completed, (iii) ops without any exception; p50/p99 of completed ops only; for the
p99 tail of completed ops the shares of total latency spent before holding the write
lock (to_lock_s; to_first_stmt_s for ops that never write), in the pool
(to_first_stmt_s), in the first write statement (first_write_s) and in commit; per-writer
waiting distribution (Gini of each writer's total waiting time, max/median).

Hypotheses (stated before running; replace the retry-based H-M2, which could not tell
serial waiting from starvation):
  H-M2a  at 100 writers (threads) the p99 tail of completed operations is time spent
         waiting until the write lock is held: the mean (over cells) of the tail-average
         share to_lock_s/total_s is >= 0.5.
  H-M2b  commit work is not the tail: the mean tail share commit_s/total_s is < 1%.
         Falsification of H-M2: H-M2a share < 0.5, or H-M2b share >= 1%.
  H-M2c  the waiting is a fair serial queue, not starvation: Gini of per-writer total
         waiting time <= 0.3 at 100 writers (threads). Falsified (-> starvation) if > 0.3.
  H-G1   (control a) the harness+GIL ceiling is not binding: null-op throughput at 100
         threads is >= 10x the completed-ops throughput of the threads cells at 100.
         Falsified if < 10x (then the measured throughput is not attributable to SQLite).
  H-G2   (control b) the GIL and the shared pool are not the bottleneck: completed-ops
         throughput with processes at 100 writers is < 2x that with threads at 100.
         Falsified if >= 2x.
Statistics (analyze.py): per-cell values, bootstrap over cells (never over operations,
which are correlated within a cell), all cells and cells not flagged by the discard rule
fixed before measuring. Limits: fresh database per cell; M2 throughput is not comparable
with M1 (instrumentation overhead); G4 (quiet host) not satisfied.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import statistics
import sys
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cells  # noqa: E402
import instrument  # noqa: E402


def gini(xs: list[float]) -> float:
    xs = sorted(x for x in xs)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * sum(xs)) - (n + 1) / n


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]


def metrics(timed: list[dict], wall: float, total_ops: int) -> dict:
    completed = [r for r in timed if r["error"] == "" or r["business_rejection"]]
    clean = [r for r in timed if r["error"] == ""]
    errors = Counter(r["error"] for r in timed if r["error"] and not r["business_rejection"])
    lat = [r["total_s"] for r in completed]
    p99 = pct(lat, 0.99)
    tail = [r for r in completed if r["total_s"] >= p99] if completed else []

    def share(r, key):
        v = r[key]
        if key == "to_lock_s" and v is None:
            v = r["to_first_stmt_s"]
        return (v or 0.0) / r["total_s"] if r["total_s"] else 0.0

    def mean_share(key):
        return round(statistics.fmean(share(r, key) for r in tail), 5) if tail else None

    def wait(r):  # waiting before the write lock is held; a failed op waited its whole latency
        if r["error"] and not r["business_rejection"]:
            return r["total_s"]
        v = r["to_lock_s"] if r["to_lock_s"] is not None else r["to_first_stmt_s"]
        return v or 0.0

    per_writer = defaultdict(float)
    for r in timed:
        per_writer[r["thread"]] += wait(r)
    w = list(per_writer.values())
    med = statistics.median(w) if w else 0.0
    return {
        "timed_ops": len(timed), "total_ops": total_ops, "wall_s": round(wall, 3),
        "throughput": round(total_ops / wall, 3) if wall else 0.0,
        "throughput_completed": round(len(completed) / wall, 3) if wall else 0.0,
        "throughput_clean": round(len(clean) / wall, 3) if wall else 0.0,
        "error_rate": round(1 - len(completed) / len(timed), 6) if timed else None,
        "timeout_rate": round(errors.get("TimeoutError", 0) / len(timed), 6) if timed else None,
        "error_types": dict(errors),
        "business_rejections": sum(r["business_rejection"] for r in timed),
        "p50_ms": round(pct(lat, 0.50) * 1000, 3), "p95_ms": round(pct(lat, 0.95) * 1000, 3),
        "p99_ms": round(p99 * 1000, 3), "tail_ops": len(tail),
        "tail_share_to_lock": mean_share("to_lock_s"),
        "tail_share_pool": mean_share("to_first_stmt_s"),
        "tail_share_first_write": mean_share("first_write_s"),
        "tail_share_commit": mean_share("commit_s"),
        "tail_mean_attempts": round(statistics.fmean(r["attempts"] for r in tail), 4) if tail else None,
        "writers": len(w), "wait_gini": round(gini(w), 5),
        "wait_max_over_median": round(max(w) / med, 4) if w and med else None,
    }


# ---- process mode ---------------------------------------------------------------------

def _proc_op(harness, services, get_session, worker_id: int, op_index: int):
    """Replica of fsm_concurrency_harness.run_throughput_sweep.do_op (lines 150-178)."""
    import datetime as _dt
    device_type = ("cam-a", "cam-b", "cam-c")[worker_id % 3]
    endpoint = f"ep-{op_index % 5}.example"
    op = ["contribute", "query", "attest", "dispute", "commit", "restore"][op_index % 6]
    if op == "contribute":
        harness.timed_call(get_session, "record_observation", {
            "site_id": f"worker-{worker_id}", "device_id": "d1", "device_type": device_type,
            "fqdn": endpoint, "remote_ip": None, "protocol": "https", "port": 443,
            "timestamp": _dt.datetime(2026, 1, 1 + (op_index % 27), tzinfo=_dt.timezone.utc),
            "source_dataset": "load_test", "evidence_type": "flow"})
    elif op == "query":
        harness.timed_call(get_session, "query_score", f"worker-{worker_id}", device_type, endpoint, "https", 443)
    elif op == "attest":
        harness.timed_call(get_session, "attest_score", device_type, endpoint, "https", 443, f"worker-{worker_id}")
    elif op == "dispute":
        harness.timed_call(get_session, "dispute_score", device_type, endpoint, "https", 443, f"worker-{worker_id}")
    elif op == "commit":
        harness.timed_call(get_session, "operator_commit", f"worker-{worker_id}", device_type, endpoint, "https", 443)
    else:
        harness.timed_call(get_session, "restore_score", device_type, endpoint, "https", 443)


def _proc_main(harness, services, worker_id, warmup, ops, barrier, conn):
    import dib.registry.db as db_module
    if db_module._engine is not None:
        db_module._engine.dispose(close=False)  # never reuse the parent's connections
    db_module._engine = None
    db_module._SessionLocal = None
    threading.current_thread().name = f"proc-{worker_id}"
    get_session = harness.new_session_factory()
    for o in range(warmup):
        _proc_op(harness, services, get_session, worker_id, o)
    instrument.records.clear()
    barrier.wait()
    for o in range(ops):
        _proc_op(harness, services, get_session, worker_id, o)
    conn.send(instrument.records[:])
    conn.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cells.common_args(p)
    p.set_defaults(reps="threads:1:10,threads:10:10,threads:50:10,threads:100:20,null:100:10,"
                        "processes:10:10,processes:50:10,processes:100:10")
    p.add_argument("--arm", choices=("default", "deploy"), default="deploy")
    a = p.parse_args()
    code = Path(a.code).resolve()
    harness = cells.import_harness(code)
    import p99_tail_breakdown as ptb  # noqa: F401  (imported for its hash; wrapping points reused)
    from dib.registry import services

    instrument.install(harness, services, ptb)
    instrumented_timed_call = harness.timed_call

    def null_timed_call(get_session, fn_name, *args, **kwargs):
        started = time.perf_counter()
        return time.perf_counter() - started, None, None

    def run_cell(spec, db: Path) -> dict:
        mode, n = spec
        cells.set_arm(a.arm, n)
        get_session = cells.fresh(harness, db)
        if mode in ("threads", "null"):
            harness.timed_call = null_timed_call if mode == "null" else instrumented_timed_call
            instrument.records.clear()
            try:
                row = harness.run_throughput_sweep(get_session, [n], a.ops_per_worker,
                                                   warmup_ops=a.warmup_ops, repeats=1)[0]
            finally:
                harness.timed_call = instrumented_timed_call
            if mode == "null":
                return {"mode": mode, "throughput": row["throughput_ops_per_sec_mean"],
                        "throughput_completed": row["throughput_ops_per_sec_mean"],
                        "wall_s": row["wall_seconds_mean"], "total_ops": row["total_ops"]}
            timed = instrument.records[-(n * a.ops_per_worker):]
            return {"mode": mode, **metrics(timed, row["wall_seconds_mean"], row["total_ops"])}
        # processes: seed through the harness (same five endpoints x three types), then fork
        for dt in ("cam-a", "cam-b", "cam-c"):
            for i in range(5):
                harness.seed_score(get_session, dt, f"ep-{i}.example")
        ctx = mp.get_context("fork")
        barrier = ctx.Barrier(n + 1)
        pipes, procs = [], []
        for w in range(n):
            parent, child = ctx.Pipe(duplex=False)
            pr = ctx.Process(target=_proc_main, args=(harness, services, w, a.warmup_ops,
                                                       a.ops_per_worker, barrier, child))
            pr.start()
            child.close()
            pipes.append(parent)
            procs.append(pr)
        barrier.wait()
        t0 = time.perf_counter()
        timed = []
        for parent in pipes:
            timed += parent.recv()
        wall = time.perf_counter() - t0
        for pr in procs:
            pr.join(timeout=60)
        return {"mode": mode, **metrics(timed, wall, n * a.ops_per_worker)}

    files = [code / "src/dib/registry/services.py", code / "src/dib/registry/db.py",
             code / "scripts/fsm_concurrency_harness.py", code / "scripts/p99_tail_breakdown.py",
             Path(__file__).resolve(), Path(instrument.__file__).resolve(),
             Path(cells.__file__).resolve(), Path(cells.nm.__file__).resolve()]
    def probe(db: Path) -> dict:
        cells.set_arm(a.arm, 100)
        return {"arm": a.arm, **cells.sqlite_settings(harness, db)}

    cells.run_cells(a, Path(a.out), run_cell, files, sqlite_probe=probe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
