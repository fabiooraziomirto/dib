"""Prediction (c) at `degraded`: share of deliveries that end in pending, per arm (D, C), with exact Clopper-Pearson 95% CIs (two-sided,
pure Python, no dependency). Written and committed BEFORE any `degraded` datum (and before the tcpdump block).
Observable (prediction_c_observable.md): per site and episode, with k = 1 fan-out per fact in B1: a delivery is "in pending" if the evidence log
shows an ack line after t0 for that site or the delivery was still pending at the deadline (summary field n_pending_sites_log, computed by
run.summarize_rows from the log, not from the generator's reads). Denominator = deliveries executed = episodes x 10 sites of the NON-excluded episodes.
Population: B1 cells only (50 episodes per cell at degraded), pooled over FANOUT 1 and 10 per arm (declared here; per-FANOUT counts are reported
descriptively). The tcpdump-block episodes are NOT part of the count.
Registered intervals (audit 14 "Tabella degli intervalli"; conditional on the tcpdump calibration, to be frozen after it): D predicted
0.0063-0.0115, falsified if the CI is entirely outside [0.004, 0.015]; C predicted 0.028-0.064, falsified if entirely outside [0.025, 0.08]; the
registered text adds "or the mTLS arm does not exceed the arm without mTLS" (read as: point estimate of C <= point estimate of D). A CI that crosses a
bound is "inconclusive" (rule of audit 25 s.A.2). wan/regional/mixed: >= 2 pending in the block falsifies; extreme: not computed here.
Hypothesis: as registered; falsification: as above. Usage: python3 analyze_c.py <degraded b1 dir with cells.jsonl> [--out file.md]"""
import json
import math
import sys
from pathlib import Path

INTERVALS = {"D": (0.004, 0.015), "C": (0.025, 0.08)}
PREDICTED = {"D": (0.0063, 0.0115), "C": (0.028, 0.064)}


def _binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k), X ~ Binomial(n, p), via the log-pmf recursion (stable for n up to a few thousand)."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    lp, lq = math.log(p), math.log1p(-p)
    s = 0.0
    for i in range(0, k + 1):
        s += math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
    return min(1.0, s)


def clopper_pearson(x: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided CI: lower = p with P(X >= x | p) = alpha/2, upper = p with P(X <= x | p) = alpha/2 (bisection)."""
    def bis(f, lo=0.0, hi=1.0):
        for _ in range(100):
            mid = (lo + hi) / 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    lower = 0.0 if x == 0 else bis(lambda p: 1.0 - _binom_cdf(x - 1, n, p) >= alpha / 2)
    upper = 1.0 if x == n else bis(lambda p: _binom_cdf(x, n, p) <= alpha / 2)
    return lower, upper


def classify(ci: tuple[float, float], interval: tuple[float, float]) -> str:
    lo, hi = interval
    if ci[1] < lo or ci[0] > hi:
        return "CI entirely outside: falsified"
    if ci[0] >= lo and ci[1] <= hi:
        return "CI entirely inside"
    return "CI crosses a bound: inconclusive"


def counts(path: Path) -> dict:
    out: dict = {}
    for line in path.read_text().splitlines():
        c = json.loads(line)
        if "rows" not in c or "aborted" in c:
            continue
        sp, s = c["cell_spec"], c["summary"]
        ok = [r for r in c["rows"] if not r.get("excluded")]
        a = out.setdefault(sp["arm"], {"x": 0, "n": 0, "cells": {}})
        x, n = s["n_pending_sites_log"], 10 * len(ok)
        a["x"] += x
        a["n"] += n
        a["cells"][sp["fanout"]] = (x, n)
    return out


def report(path: Path) -> str:
    cs = counts(path)
    L = ["| arm | pending / deliveries (pooled) | share | CP 95% CI | predicted | registered interval | classification | per FANOUT (pending/deliveries) |", "|---|---|---|---|---|---|---|---|"]
    for arm in ("D", "C"):
        if arm not in cs:
            continue
        x, n = cs[arm]["x"], cs[arm]["n"]
        ci = clopper_pearson(x, n)
        L.append(f"| {arm} | {x} / {n} | {x / n:.5f} | [{ci[0]:.5f}; {ci[1]:.5f}] | {PREDICTED[arm][0]}-{PREDICTED[arm][1]} | {INTERVALS[arm]} | {classify(ci, INTERVALS[arm])} | "
                 + ", ".join(f"f{k}: {v[0]}/{v[1]}" for k, v in sorted(cs[arm]["cells"].items())) + " |")
    if "D" in cs and "C" in cs:
        pd, pc = cs["D"]["x"] / cs["D"]["n"], cs["C"]["x"] / cs["C"]["n"]
        L.append(f"\nSecond clause (registered): mTLS arm exceeds the arm without mTLS? point estimates C {pc:.5f} vs D {pd:.5f}: "
                 + ("yes (clause satisfied)" if pc > pd else "NO: the registered clause is violated"))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    text = report(Path(sys.argv[1]) / "cells.jsonl")
    print(text)
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(text)
