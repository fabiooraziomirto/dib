"""Analysis of M1/M2 cells (audit 04 sez. 2): per-cell statistics, bootstrap over CELLS.

Usage: python3 analyze.py m1|m2 <dir containing cells.jsonl> [--resamples 10000 --seed 20261010]
Writes <dir>/summary.csv and <dir>/summary.md.

* The resampling unit is the cell (one repetition): operations inside a cell share one
  queue and are correlated, so they are never resampled individually. Each metric is
  first computed per cell (throughput, p50, p99, ...), then its mean gets a 95% percentile
  bootstrap CI over the cells.
* "all" = every cell; "filtered" = cells not flagged by the discard rule fixed before
  measuring (recorded in each cell); the number of flagged cells is always reported.
* Throughput definitions. M1 (harness aggregates only): ``throughput`` = all timed
  operations / wall time, failures included (the harness's number);
  ``throughput_completed`` = (operations - unexpected errors) / wall time, where
  InvalidStateTransition (business rejection) counts as completed. M2: also
  ``throughput_clean`` = operations without any exception / wall time.
* Latency. In M1 the harness reports percentiles over ALL operations, failures
  included. A cell whose p99 >= 29.9 s with unexpected errors is censored at the
  SQLAlchemy pool checkout timeout (30 s): its p99 is a ceiling, not a latency, and it is
  excluded from the latency statistics (counted in ``p99_censored_cells``). Success-only
  percentiles are not available for M1 (no per-operation data); M2 reports them.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path

CENSOR_MS = 29_900.0
M2_METRICS = ["throughput", "throughput_completed", "throughput_clean", "error_rate", "timeout_rate",
              "p50_ms", "p95_ms", "p99_ms", "tail_share_to_lock", "tail_share_pool",
              "tail_share_first_write", "tail_share_commit", "tail_mean_attempts", "wait_gini",
              "wait_max_over_median"]


def boot_ci(xs, resamples, rng):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not xs:
        return None, None, None
    means = sorted(statistics.fmean(rng.choices(xs, k=len(xs))) for _ in range(resamples))
    return statistics.fmean(xs), means[int(0.025 * resamples)], means[min(resamples - 1, int(0.975 * resamples))]


def m1_values(c):
    r = c["result"]
    censored = r["unexpected_errors"] > 0 and r["p99_ms"] >= CENSOR_MS
    return {
        "throughput": r["throughput"],
        "throughput_completed": (r["total_ops"] - r["unexpected_errors"]) / r["wall_s"],
        "error_rate": r["unexpected_errors"] / r["total_ops"],
        "p50_ms": r["p50_ms"], "p95_ms": r["p95_ms"],
        "p99_ms": None if censored else r["p99_ms"],
        "_censored": censored,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["m1", "m2"])
    p.add_argument("dir", type=Path)
    p.add_argument("--resamples", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=20261010)
    a = p.parse_args()
    cells = [json.loads(line) for line in (a.dir / "cells.jsonl").open()]
    groups: dict[tuple, list[dict]] = {}
    for c in cells:
        groups.setdefault((c.get("mode", "threads"), c["n_workers"]), []).append(c)
    rows, ci = [], {}
    for key in sorted(groups):
        mode, n = key
        for subset in ("all", "filtered"):
            cs = [c for c in groups[key] if subset == "all" or not c["disturbed"]]
            if a.kind == "m1":
                vals = [m1_values(c) for c in cs]
                names = ["throughput", "throughput_completed", "error_rate", "p50_ms", "p95_ms", "p99_ms"]
            else:
                vals = [c["result"] for c in cs]
                names = [m for m in M2_METRICS if any(m in v for v in vals)]
            row = {"mode": mode, "n_workers": n, "subset": subset, "cells": len(cs),
                   "flagged": sum(c["disturbed"] for c in groups[key])}
            if a.kind == "m1":
                row["p99_censored_cells"] = sum(v["_censored"] for v in vals)
            row["other_cores_during_mean"] = round(statistics.fmean(c["monitor"]["during"]["other_cores"] for c in cs), 4) if cs else None
            for m in names:
                rng = random.Random(f"{a.seed}-{mode}-{n}-{subset}-{m}")
                mean, lo, hi = boot_ci([v.get(m) for v in vals], a.resamples, rng)
                row[f"{m}_mean"] = None if mean is None else round(mean, 5)
                row[f"{m}_ci_lo"] = None if lo is None else round(lo, 5)
                row[f"{m}_ci_hi"] = None if hi is None else round(hi, 5)
                ci[(mode, n, subset, m)] = (mean, lo, hi)
            rows.append(row)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (a.dir / "summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    def fmt(t, d=1):
        return "n/a" if t is None or t[0] is None else f"{t[0]:.{d}f} [{t[1]:.{d}f}, {t[2]:.{d}f}]"

    verdicts = []
    for subset in ("all", "filtered"):
        if a.kind == "m1":
            t50, t100 = ci.get(("threads", 50, subset, "throughput")), ci.get(("threads", 100, subset, "throughput"))
            if t50 and t100 and t50[0] is not None and t100[0] is not None:
                fals = t100[1] > t50[2]
                verdicts.append(f"H-M1 [{subset}] throughput (all ops) 50 = {fmt(t50)}, 100 = {fmt(t100)} ops/s -> "
                                f"{'FALSIFIED' if fals else 'not falsified'}; completed-ops throughput 50 = "
                                f"{fmt(ci[('threads', 50, subset, 'throughput_completed')])}, 100 = "
                                f"{fmt(ci[('threads', 100, subset, 'throughput_completed')])}; error rate at 100 = "
                                f"{fmt(ci[('threads', 100, subset, 'error_rate')], 4)}")
        else:
            g = lambda mode, n, m: ci.get((mode, n, subset, m))  # noqa: E731
            lock, commit, gin = g("threads", 100, "tail_share_to_lock"), g("threads", 100, "tail_share_commit"), g("threads", 100, "wait_gini")
            if lock and lock[0] is not None:
                verdicts.append(f"H-M2a/b [{subset}] tail share before lock held = {fmt(lock, 3)} (>= 0.5), "
                                f"commit share = {fmt(commit, 4)} (< 0.01) -> "
                                f"{'FALSIFIED' if lock[0] < 0.5 or commit[0] >= 0.01 else 'not falsified'}")
                verdicts.append(f"H-M2c [{subset}] Gini of per-writer waiting = {fmt(gin, 3)} (<= 0.3 fair serial queue) -> "
                                f"{'FALSIFIED (starvation)' if gin[0] > 0.3 else 'not falsified'}")
            null, thr = g("null", 100, "throughput"), g("threads", 100, "throughput_completed")
            if null and thr and null[0] and thr[0]:
                verdicts.append(f"H-G1 [{subset}] null-op {fmt(null)} vs threads completed {fmt(thr)} ops/s: ratio "
                                f"{null[0] / thr[0]:.1f} (>= 10) -> {'FALSIFIED' if null[0] / thr[0] < 10 else 'not falsified'}")
            proc = g("processes", 100, "throughput_completed")
            if proc and thr and proc[0] and thr[0]:
                verdicts.append(f"H-G2 [{subset}] processes completed {fmt(proc)} vs threads {fmt(thr)} ops/s: ratio "
                                f"{proc[0] / thr[0]:.2f} (< 2) -> {'FALSIFIED' if proc[0] / thr[0] >= 2 else 'not falsified'}")
    md = ["| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)]
    md += ["| " + " | ".join(str(r.get(k, "")) for k in fields) + " |" for r in rows]
    (a.dir / "summary.md").write_text("\n".join(md + ["", *verdicts]) + "\n")
    print("\n".join(verdicts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
