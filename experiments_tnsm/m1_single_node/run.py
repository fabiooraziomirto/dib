"""M1 (audit 04 sez. 2): single-node registry concurrency, in-process, on the free node.

What runs: the unmodified harness function
code/scripts/fsm_concurrency_harness.py::run_throughput_sweep (services.py called from OS
threads sharing one SQLAlchemy engine on one SQLite file; uniform 6-operation mix), one
cell = one (writers, repetition) on a fresh database, 200 timed operations per worker after
a discarded warm-up of 20 per worker. Writers 1, 10, 50 with 10 repetitions each and 100
with 20, in an order randomized with --seed. Python and packages: venv on the node with the
versions of /opt/conda/envs/dib312 (manifest: pip freeze).

Hypothesis (stated before running, from audit 04 sez. 2):
  H-M1  single-node throughput saturates between 50 and 100 writers: the 95% bootstrap
        CIs of the mean throughput at 50 and at 100 writers overlap.
Falsification: the CI at 100 writers lies entirely above the CI at 50 writers.
Also reported, without a pre-set threshold: p50/p95/p99 per writer count, unexpected
errors (the harness counts errors other than InvalidStateTransition).

Statistics (analysis in analyze.py, run afterwards): unit = cell (repetition); mean with
95% percentile bootstrap CI (10,000 resamples, seed 20261010), on all cells and on the
cells not flagged by the discard rule fixed before running (discard_rule.json); the number
of flagged cells is always reported. No comparison with other machines (the old
results/concurrency run used another host and another services.py, audit 04 sez. 1).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import cells  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cells.common_args(p)
    a = p.parse_args()
    code = Path(a.code).resolve()
    harness = cells.import_harness(code)

    def run_cell(n: int, db: Path) -> dict:
        get_session = cells.fresh(harness, db)
        row = harness.run_throughput_sweep(get_session, [n], a.ops_per_worker,
                                           warmup_ops=a.warmup_ops, repeats=1)[0]
        return {"throughput": row["throughput_ops_per_sec_mean"], "wall_s": row["wall_seconds_mean"],
                "p50_ms": round(row["p50_latency_s_mean"] * 1000, 3),
                "p95_ms": round(row["p95_latency_s_mean"] * 1000, 3),
                "p99_ms": round(row["p99_latency_s_mean"] * 1000, 3),
                "total_ops": row["total_ops"], "unexpected_errors": row["unexpected_errors"]}

    files = [code / "src/dib/registry/services.py", code / "src/dib/registry/db.py",
             code / "scripts/fsm_concurrency_harness.py", Path(__file__).resolve(),
             Path(cells.__file__).resolve(), Path(cells.nm.__file__).resolve()]
    cells.run_cells(a, Path(a.out), run_cell, files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
