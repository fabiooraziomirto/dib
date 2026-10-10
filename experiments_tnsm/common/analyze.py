"""Analysis of M1/M2 cells (audit 04 sez. 2): bootstrap CIs, all cells and filtered cells.

Usage: python3 analyze.py m1|m2 <dir containing cells.jsonl> [--resamples 10000 --seed 20261010]
Writes <dir>/summary.csv and <dir>/summary.md. The discard rule is the one recorded in
each cell at run time (fixed before running, discard_rule.json); nothing is dropped from
"all"; "filtered" excludes flagged cells and the count of flagged cells is reported.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from pathlib import Path

METRICS = {
    "m1": ["throughput", "p50_ms", "p95_ms", "p99_ms", "unexpected_errors"],
    "m2": ["throughput", "p50_ms", "p99_ms", "commit_share_of_p99_pct", "mean_attempts_in_p99_tail",
           "mean_attempts", "max_attempts", "unexpected_errors"],
}


def boot_ci(xs: list[float], resamples: int, rng: random.Random) -> tuple[float, float, float]:
    if not xs:
        return float("nan"), float("nan"), float("nan")
    means = sorted(statistics.fmean(rng.choices(xs, k=len(xs))) for _ in range(resamples))
    lo = means[int(0.025 * resamples)]
    hi = means[min(resamples - 1, int(0.975 * resamples))]
    return statistics.fmean(xs), lo, hi


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=sorted(METRICS))
    p.add_argument("dir", type=Path)
    p.add_argument("--resamples", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=20261010)
    a = p.parse_args()
    cells = [json.loads(line) for line in (a.dir / "cells.jsonl").open()]
    rows, verdicts = [], []
    by_n: dict[int, list[dict]] = {}
    for c in cells:
        by_n.setdefault(c["n_workers"], []).append(c)
    ci = {}
    for n in sorted(by_n):
        for subset in ("all", "filtered"):
            cs = [c for c in by_n[n] if subset == "all" or not c["disturbed"]]
            row = {"n_workers": n, "subset": subset, "cells": len(cs),
                   "flagged": sum(c["disturbed"] for c in by_n[n]),
                   "other_cores_during_mean": round(statistics.fmean(c["monitor"]["during"]["other_cores"] for c in cs), 4) if cs else None,
                   "steal_pct_during_mean": round(statistics.fmean(c["monitor"]["during"]["steal_pct"] for c in cs), 4) if cs else None}
            for m in METRICS[a.kind]:
                rng = random.Random(f"{a.seed}-{n}-{subset}-{m}")
                mean, lo, hi = boot_ci([float(c["result"][m]) for c in cs], a.resamples, rng)
                row[f"{m}_mean"], row[f"{m}_ci_lo"], row[f"{m}_ci_hi"] = (round(v, 4) for v in (mean, lo, hi))
                ci[(n, subset, m)] = (mean, lo, hi)
            rows.append(row)
    with (a.dir / "summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for subset in ("all", "filtered"):
        if a.kind == "m1":
            m50, lo50, hi50 = ci[(50, subset, "throughput")]
            m100, lo100, hi100 = ci[(100, subset, "throughput")]
            falsified = lo100 > hi50
            verdicts.append(f"H-M1 [{subset}]: throughput 50 = {m50:.1f} [{lo50:.1f}, {hi50:.1f}], "
                            f"100 = {m100:.1f} [{lo100:.1f}, {hi100:.1f}] ops/s -> "
                            f"{'FALSIFIED (CI at 100 entirely above CI at 50)' if falsified else 'not falsified (CIs overlap or 100 below)'}")
        else:
            att = ci[(100, subset, "mean_attempts_in_p99_tail")]
            share = ci[(100, subset, "commit_share_of_p99_pct")]
            falsified = att[0] > 1.5 or share[0] >= 1.0
            verdicts.append(f"H-M2 [{subset}]: at 100 writers mean attempts in p99 tail = {att[0]:.3f} "
                            f"[{att[1]:.3f}, {att[2]:.3f}] (threshold 1.5), commit share of p99 = {share[0]:.3f}% "
                            f"[{share[1]:.3f}, {share[2]:.3f}] (threshold 1%) -> "
                            f"{'FALSIFIED' if falsified else 'not falsified'}")
    md = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
    md += ["| " + " | ".join(str(r[k]) for k in rows[0]) + " |" for r in rows]
    (a.dir / "summary.md").write_text("\n".join(md + ["", *verdicts]) + "\n")
    print("\n".join(verdicts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
