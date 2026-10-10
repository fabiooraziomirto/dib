"""M2 (audit 04 sez. 2): where the single-node p99 tail comes from, on the free node.

What runs: the same cells as M1 (fresh database per cell, randomized order, 200 timed
operations per worker after a discarded warm-up of 20; writers 1/10/50 x 10, 100 x 20) with
the instrumentation of code/scripts/p99_tail_breakdown.py applied unchanged: its
_counting_retry around services._retry_on_conflict, _timed_commit around
Session.commit and _instrumented_timed_call around harness.timed_call. Per timed operation
it records total latency, time inside Session.commit() and the number of attempts of the
optimistic-retry loop. The instrumentation adds overhead: M2 latencies are not M1
latencies and are not compared with them.

Hypothesis (stated before running, from audit 04 sez. 2):
  H-M2  the p99 tail at 100 writers is waiting, not retries and not commit work: over the
        100-writer cells, the mean (across cells) of the mean attempts of the operations in
        the p99 tail is <= 1.5, and the mean share of commit time in the p99 tail is < 1%.
Falsification: either bootstrap mean exceeds its threshold (1.5 attempts; 1%).
Not tested here: WHO serializes (SQLite lock or GIL); that needs M2b (postponed).

Statistics as in M1 (analyze.py): per-cell metrics, bootstrap CIs, all cells and cells not
flagged by the discard rule fixed beforehand, flagged count always reported.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import cells  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cells.common_args(p)
    a = p.parse_args()
    code = Path(a.code).resolve()
    harness = cells.import_harness(code)
    import p99_tail_breakdown as ptb  # same harness module object (fsm_concurrency_harness)
    from dib.registry import services
    from sqlalchemy.orm import Session as SASession

    assert ptb.harness is harness
    services._retry_on_conflict = ptb._counting_retry
    SASession.commit = ptb._timed_commit
    harness.timed_call = ptb._instrumented_timed_call

    def run_cell(n: int, db: Path) -> dict:
        get_session = cells.fresh(harness, db)
        ptb._records.clear()
        row = harness.run_throughput_sweep(get_session, [n], a.ops_per_worker,
                                           warmup_ops=a.warmup_ops, repeats=1)[0]
        timed = ptb._records[-(n * a.ops_per_worker):]
        totals = [r["total_s"] for r in timed]
        p99 = ptb.pct(totals, 0.99)
        tail = [r for r in timed if r["total_s"] >= p99]
        errors = Counter(r["error"] for r in timed if r["error"])
        return {
            "throughput": row["throughput_ops_per_sec_mean"], "timed_ops": len(timed),
            "p50_ms": round(ptb.pct(totals, 0.50) * 1000, 3), "p99_ms": round(p99 * 1000, 3),
            "mean_commit_ms": round(statistics.mean(r["commit_s"] for r in timed) * 1000, 4),
            "commit_share_of_p99_pct": round(100 * statistics.mean(r["commit_s"] for r in tail) / p99, 4) if p99 else 0.0,
            "mean_attempts": round(statistics.mean(r["attempts"] for r in timed), 4),
            "max_attempts": max(r["attempts"] for r in timed),
            "mean_attempts_in_p99_tail": round(statistics.mean(r["attempts"] for r in tail), 4),
            "tail_ops": len(tail),
            "error_types": dict(errors), "unexpected_errors": row["unexpected_errors"],
        }

    files = [code / "src/dib/registry/services.py", code / "src/dib/registry/db.py",
             code / "scripts/fsm_concurrency_harness.py", code / "scripts/p99_tail_breakdown.py",
             Path(__file__).resolve(), Path(cells.__file__).resolve(), Path(cells.nm.__file__).resolve()]
    cells.run_cells(a, Path(a.out), run_cell, files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
