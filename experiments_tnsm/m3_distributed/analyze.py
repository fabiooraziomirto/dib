"""Analysis of M3/M4 cells (audit 18). Unit = cell; bootstrap over cells (never over ops),
10000 resamples, seed 20261010, 95% percentile CI; ratios paired by repetition.
Hypotheses and falsification criteria are those of run.py's docstring (fixed before the run).
Reports ALL cells, the cells flagged by the discard rule (experiments_tnsm/common/
discard_rule.json: other_cores > 1.0 or steal > 2%; here only the node's load/top is
recorded per cell, so 'flagged' = top non-DIB process list not available -> reported as a
limitation, nothing discarded), error counts by type per arm, and the 1-writer anomaly.

Usage: python3 analyze.py <run dir>
"""
from __future__ import annotations

import csv
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

d = Path(sys.argv[1])
cells = [json.loads(l) for l in (d / "cells.jsonl").open()]
rng = random.Random(20261010)


def boot(xs, f=statistics.mean, n=10000):
    xs = list(xs)
    v = sorted(f([rng.choice(xs) for _ in xs]) for _ in range(n))
    return f(xs), v[int(0.025 * n)], v[int(0.975 * n)]


def val(c, w, key):
    for r in c["rows"]:
        if int(r["n_workers"]) == w:
            return float(r[key])


arm = lambda c: (c["fanout"], c["mtls"])
rows_out = []
print("== throughput (ops/s), mean [95% CI over cells], n cells per arm")
for w in (1, 10, 50, 100):
    for a in sorted({arm(c) for c in cells}):
        xs = [val(c, w, "throughput_ops_per_sec_mean") for c in cells if arm(c) == a]
        p50 = [1000 * val(c, w, "p50_latency_s_mean") for c in cells if arm(c) == a]
        p99 = [1000 * val(c, w, "p99_latency_s_mean") for c in cells if arm(c) == a]
        m, lo, hi = boot(xs); mp, plo, phi = boot(p50); m9, l9, h9 = boot(p99)
        print(f"  w={w:3d} fanout={a[0]:2d} mtls={a[1]}: thr {m:7.1f} [{lo:7.1f},{hi:7.1f}]  p50 {mp:6.1f}ms [{plo:.1f},{phi:.1f}]  p99 {m9:7.1f}ms [{l9:.1f},{h9:.1f}]  n={len(xs)}")
        rows_out.append({"writers": w, "fanout": a[0], "mtls": a[1], "n": len(xs), "thr": m, "thr_lo": lo, "thr_hi": hi,
                         "p50_ms": mp, "p50_lo": plo, "p50_hi": phi, "p99_ms": m9, "p99_lo": l9, "p99_hi": h9})


def paired(num_arm, den_arm, w, key, diff=False):
    by = defaultdict(dict)
    for c in cells:
        by[c["rep"]][arm(c)] = val(c, w, key)
    r = [(by[k][num_arm] - by[k][den_arm]) if diff else by[k][num_arm] / by[k][den_arm] for k in by]
    return boot(r)


print("== H-M3a: throughput ratio FANOUT10/FANOUT1 at 100 writers, mTLS off (paired by repetition); falsified if CI entirely outside [0.9,1.1]")
m, lo, hi = paired((10, 0), (1, 0), 100, "throughput_ops_per_sec_mean")
print(f"  ratio {m:.3f} [{lo:.3f}, {hi:.3f}] -> {'FALSIFIED' if (hi < 0.9 or lo > 1.1) else 'not falsified'}")
m2, lo2, hi2 = paired((10, 1), (1, 1), 100, "throughput_ops_per_sec_mean")
print(f"  (mTLS on) ratio {m2:.3f} [{lo2:.3f}, {hi2:.3f}]")

print("== H-M4 (FANOUT 10): throughput ratio mTLS/plain at 100 writers; falsified if CI entirely below 0.8")
m, lo, hi = paired((10, 1), (10, 0), 100, "throughput_ops_per_sec_mean")
print(f"  ratio {m:.3f} [{lo:.3f}, {hi:.3f}] -> {'FALSIFIED' if hi < 0.8 else 'not falsified'}")
print("== H-M4 (FANOUT 10): p50 difference mTLS - plain at 1 writer (ms); falsified if CI entirely above 5 ms")
m, lo, hi = paired((10, 1), (10, 0), 1, "p50_latency_s_mean", diff=True)
print(f"  diff {1000*m:.2f} ms [{1000*lo:.2f}, {1000*hi:.2f}] -> {'FALSIFIED' if 1000 * lo > 5 else 'not falsified'}")
for w in (10, 50, 100):
    m, lo, hi = paired((10, 1), (10, 0), w, "throughput_ops_per_sec_mean")
    print(f"  (descriptive) thr ratio mTLS/plain at {w}: {m:.3f} [{lo:.3f},{hi:.3f}]")

print("== H-M3b: unexpected errors")
tot = Counter(); per_arm = defaultdict(int); cells_with = []
ops_arm = defaultdict(int)
for c in cells:
    n = 0
    for r in c["rows"]:
        e = int(r["unexpected_errors"])
        n += e
        ops_arm[arm(c)] += int(r["total_ops"])
        for part in filter(None, r["error_types"].split(";")):
            k, _, v = part.rpartition("x")
            tot[k] += int(v)
    per_arm[arm(c)] += n
    if n:
        cells_with.append((c["cell"], arm(c), n))
print("  total", sum(tot.values()), "in", len(cells_with), "cells of", len(cells), "->", "FALSIFIED (>0)" if tot else "not falsified")
print("  by type:", dict(tot))
print("  by arm (errors / timed ops):", {a: f"{per_arm[a]}/{ops_arm[a]} = {100*per_arm[a]/ops_arm[a]:.4f}%" for a in sorted(per_arm)})
print("  http.403:", sum(v for k, v in tot.items() if "403" in k))

print("== 1-writer anomaly: throughput at 1 writer by arm vs worker->site routing")
print("  mean thr at w=1:", {a: round(statistics.mean(val(c, 1, 'throughput_ops_per_sec_mean') for c in cells if arm(c) == a), 1) for a in sorted({arm(c) for c in cells})})

print("== node load before each cell (loadavg1), by arm")
ld = defaultdict(list)
for c in cells:
    ld[arm(c)].append(float(c["node_before"]["loadavg"].split()[0]))
print("  ", {a: round(statistics.mean(v), 2) for a, v in sorted(ld.items())}, "max", max(max(v) for v in ld.values()))

with (d / "summary.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0]))
    w.writeheader()
    w.writerows(rows_out)
