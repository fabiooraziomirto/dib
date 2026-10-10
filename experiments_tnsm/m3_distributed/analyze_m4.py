"""Analysis of the M4 rerun (run_m4.py). Unit = cell; bootstrap over cells (10000 resamples,
seed 20261013); throughput ratios C/D paired by block (repetition). Verdicts use the criteria
fixed in run_m4.py's docstring before launch:
  H-M4a (1 writer):   falsified if the CI of C/D lies entirely outside [0.50, 0.72]
  H-M4b (10 writers): falsified if the CI of C/D lies entirely outside [0.68, 0.86]
  50, 100 writers: exploratory, reported with the bottleneck caution.
Discard rule (experiments_tnsm/common/discard_rule.json): FLAGGED cells = pre-cell idle sample
other_cores > 1.0 or steal_pct > 2.0; results on all cells and on unflagged cells.
Usage: python3 analyze_m4.py <run dir>
"""
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

d = Path(sys.argv[1])
recs = [json.loads(l) for l in (d / "cells.jsonl").open()]
rng = random.Random(20261013)
WR = sorted({int(w) for r in recs for w in r["results"]})
OPS = ("query", "commit", "attest", "dispute", "restore")


def boot(xs, n=10000):
    xs = list(xs)
    v = sorted(st.mean([rng.choice(xs) for _ in xs]) for _ in range(n))
    return st.mean(xs), v[int(0.025 * n)], v[int(0.975 * n)]


def sel(arm, w, key, only=None):
    return {r["block"]: r["results"][str(w)][key] for r in recs if r["arm"] == arm and (only is None or only(r))}


def paired_ratio(w, only=None):
    c, dd = sel("C", w, "throughput", only), sel("D", w, "throughput", only)
    blocks = sorted(set(c) & set(dd))
    return boot([c[b] / dd[b] for b in blocks]) + (len(blocks),)


out = {"cells": len(recs), "arms": dict(Counter(r["arm"] for r in recs)), "throughput": {}, "ratio_C_over_D": {}, "verdicts": {}}
flag = [r for r in recs if r["flagged_pre"]]
unflag = lambda r: not r["flagged_pre"]
print(f"cells {len(recs)}, flagged by the discard rule (pre-cell idle sample): {len(flag)}")
print("pre-cell background other_cores %.3f-%.3f, steal %.3f-%.3f" % (
    min(r["background_idle"]["other_cores"] for r in recs), max(r["background_idle"]["other_cores"] for r in recs),
    min(r["background_idle"]["steal_pct"] for r in recs), max(r["background_idle"]["steal_pct"] for r in recs)))
print("\n== throughput (ops/s), mean [95% CI over cells]; paired ratio C/D (by block)")
crit = {1: (0.50, 0.72), 10: (0.68, 0.86)}
for w in WR:
    row = {}
    for arm in ("D", "C"):
        xs = list(sel(arm, w, "throughput").values())
        row[arm] = boot(xs)
    out["throughput"][w] = row
    m, lo, hi, nb = paired_ratio(w)
    m2, lo2, hi2, nb2 = paired_ratio(w, unflag) if flag else (m, lo, hi, nb)
    out["ratio_C_over_D"][w] = {"all": [m, lo, hi, nb], "unflagged": [m2, lo2, hi2, nb2]}
    line = f"  w={w:3d}: D {row['D'][0]:7.1f} [{row['D'][1]:7.1f},{row['D'][2]:7.1f}]  C {row['C'][0]:7.1f} [{row['C'][1]:7.1f},{row['C'][2]:7.1f}]  C/D {m:.3f} [{lo:.3f},{hi:.3f}] ({nb} blocks)"
    if w in crit:
        a, b = crit[w]
        fals = hi < a or lo > b
        out["verdicts"][f"H-M4{'a' if w == 1 else 'b'}"] = "FALSIFIED" if fals else "not falsified"
        line += f"   predicted ~{0.61 if w == 1 else 0.77}, interval [{a},{b}] -> {'FALSIFIED' if fals else 'not falsified'}"
    else:
        line += "   (exploratory)"
    print(line)
print("\n== overall latency (ms) mean over cells: p50 / p95 / p99")
for w in WR:
    for arm in ("D", "C"):
        print(f"  w={w:3d} {arm}: " + " / ".join(f"{st.mean(sel(arm, w, k).values()):7.2f}" for k in ("p50_ms", "p95_ms", "p99_ms")))
print("\n== p50 per operation type (ms), mean [95% CI over cells]")
per = {}
for w in WR:
    for op in OPS:
        row = {}
        for arm in ("D", "C"):
            xs = [r["results"][str(w)]["per_op_p50_ms"][op] for r in recs if r["arm"] == arm]
            row[arm] = boot(xs)
        per[f"{w}_{op}"] = row
        print(f"  w={w:3d} {op:8s} D {row['D'][0]:7.2f} [{row['D'][1]:7.2f},{row['D'][2]:7.2f}]   C {row['C'][0]:7.2f} [{row['C'][1]:7.2f},{row['C'][2]:7.2f}]   C-D {row['C'][0]-row['D'][0]:+.2f}")
out["per_op_p50"] = per
print("\n== unexpected errors")
tot = Counter()
by = defaultdict(int)
for r in recs:
    for w, v in r["results"].items():
        by[(r["arm"], int(w))] += v["unexpected"]
        tot.update(v["errors"])
print("  total", sum(tot.values()), dict(tot))
print("  by (arm, writers):", {f"{a}{w}": n for (a, w), n in sorted(by.items()) if n})
out["errors"] = {"total": sum(tot.values()), "types": dict(tot), "by_arm_writers": {f"{a}{w}": n for (a, w), n in sorted(by.items())}}
print("\n== cell order:", [r["arm"] for r in recs])
(d / "summary.json").write_text(json.dumps(out, indent=1, default=str))
