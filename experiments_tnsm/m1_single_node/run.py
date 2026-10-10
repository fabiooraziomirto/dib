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

Two arms (plan rev. 5, Passo 7, added 2026-10-10 before the rerun; the first run with the
default arm only was stopped at 40/50 cells and is kept unanalyzed in aborted_20261010/):
cells are (arm, writers, repetition), arms mixed in the same randomized order; the arm is
set only through the existing environment variables (common/cells.py:set_arm).
  default  as above (pool checkout timeout 30 s caps the p99: censored, audit 04 s.7.4);
  deploy   DIB_SQLITE_WAL=1 and DIB_SQLITE_POOL_SIZE=max(writers, 5).
Additional hypotheses (stated before running):
  H-M1b  in the deploy arm no cell has unexpected errors (no pool-checkout or busy timeout)
         at any writer count. Falsified by one deploy cell with unexpected_errors > 0.
  H-M1c  at 100 writers the completed-ops throughput of the deploy arm is not lower than
         that of the default arm. Falsified if the deploy 95% CI lies entirely below the
         default one.
H-M1 above is tested separately in each arm.

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
    p.set_defaults(reps="default:1:10,default:10:10,default:50:10,default:100:20,"
                        "deploy:1:10,deploy:10:10,deploy:50:10,deploy:100:20")
    a = p.parse_args()
    code = Path(a.code).resolve()
    harness = cells.import_harness(code)

    def run_cell(spec, db: Path) -> dict:
        arm, n = spec
        env = cells.set_arm(arm, n)
        get_session = cells.fresh(harness, db)
        row = harness.run_throughput_sweep(get_session, [n], a.ops_per_worker,
                                           warmup_ops=a.warmup_ops, repeats=1)[0]
        return {"throughput": row["throughput_ops_per_sec_mean"], "wall_s": row["wall_seconds_mean"],
                "p50_ms": round(row["p50_latency_s_mean"] * 1000, 3),
                "p95_ms": round(row["p95_latency_s_mean"] * 1000, 3),
                "p99_ms": round(row["p99_latency_s_mean"] * 1000, 3),
                "total_ops": row["total_ops"], "unexpected_errors": row["unexpected_errors"],
                "arm": arm, "env": env}

    files = [code / "src/dib/registry/services.py", code / "src/dib/registry/db.py",
             code / "scripts/fsm_concurrency_harness.py", Path(__file__).resolve(),
             Path(cells.__file__).resolve(), Path(cells.nm.__file__).resolve()]
    def probe(db: Path) -> dict:
        out = {arm: (cells.set_arm(arm, 100), cells.sqlite_settings(harness, db))[1] for arm in cells.ARMS}
        cells.set_arm("default", 1)
        return out

    cells.run_cells(a, Path(a.out), run_cell, files, sqlite_probe=probe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
