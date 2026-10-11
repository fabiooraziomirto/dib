"""Prediction (c) at `degraded`: share of deliveries that end in pending, per arm (D, C), with exact Clopper-Pearson 95% CIs (two-sided,
pure Python, no dependency). Written and committed (7684585) BEFORE any `degraded` datum; revised 2026-10-11 (this revision also committed BEFORE any
`degraded` B1 datum, the smokes are not data) as declared in the next paragraph.
REVISION 2026-10-11 (user decision, before B1): (1) the intervals D [0.004, 0.015] and C [0.025, 0.08] are UNCHANGED, not recomputed after seeing the tcpdump
counts. (2) DISCLOSURE: the tcpdump block (400 deliveries, 200 per arm: pending 2/200 for D and 6/200 for C) was KNOWN before B1; B1 is the CONFIRMATORY test
(50 episodes x 10 sites x FANOUT 1 and 10 = 1000 deliveries per arm, FANOUT 1 and 10 pooled because f^3 depends on the attempt, not on the concurrency). The
tcpdump episodes are not part of the count. (3) UNAMBIGUOUS FORM of the criterion: (c) is FALSIFIED if the Clopper-Pearson CI of an arm lies ENTIRELY outside
that arm's interval, OR if the mTLS arm does not exceed the arm without mTLS in the sense that the CI of C lies ENTIRELY BELOW the CI of D (disjoint CIs in the
opposite direction); a CI that crosses a bound, or CIs that overlap, is "inconclusive" for that clause, never "falsified". This replaces the earlier code
reading of the second clause (point estimate of C <= point estimate of D), which is still printed as information. (4) The count is recomputed from the
episode rows (not from the stored summary) so that episodes excluded for overlap with an unsettled netem profile (docstring of analyze_b1.py,
profile_exclusion.py) leave both the numerator and the denominator; give --profile-events and --watch-log to apply it. (5) Input: one run.py directory or a
block directory of b1_*/ groups (blockdata.py). The exclusion code has not been run on any degraded B1 data. (6) HOW n IS COUNTED (declared 2026-10-11, before B1): the
numerator x and the denominator n are taken over the SAME set of episodes: those NOT excluded AND carrying dispute_rtt_s (a recorded response). n = 10 x
(that number of episodes), x = sites in pending of those episodes. A non-excluded episode WITHOUT dispute_rtt_s (no response recorded) is counted in NEITHER x
nor n, and its number is reported per arm in the report ("without dispute_rtt_s"); it is not replaced. (The earlier code counted such an episode in n but not
in x; the case does not occur in the lan_before data, where every row has dispute_rtt_s.)
Observable (prediction_c_observable.md): per site and episode, with k = 1 fan-out per fact in B1: a delivery is "in pending" if the evidence log
shows an ack line after t0 for that site or the delivery was still pending at the deadline (summary field n_pending_sites_log, computed by
run.summarize_rows from the log, not from the generator's reads). Denominator = deliveries executed = episodes x 10 sites of the NON-excluded episodes.
Population: B1 cells only (50 episodes per cell at degraded), pooled over FANOUT 1 and 10 per arm (declared here; per-FANOUT counts are reported
descriptively). The tcpdump-block episodes are NOT part of the count.
Registered intervals (audit 14 "Tabella degli intervalli"; conditional on the tcpdump calibration, to be frozen after it): D predicted
0.0063-0.0115, falsified if the CI is entirely outside [0.004, 0.015]; C predicted 0.028-0.064, falsified if entirely outside [0.025, 0.08]; the
registered text adds "or the mTLS arm does not exceed the arm without mTLS" (earlier read as point estimate of C <= point estimate of D; now, see REVISION: CI of C
entirely below the CI of D). A CI that crosses a bound is "inconclusive" (rule of audit 25 s.A.2). wan/regional/mixed: >= 2 pending in the block falsifies; extreme: not computed here.
Hypothesis: as registered; falsification: as above. Usage: python3 analyze_c.py <run dir with cells.jsonl, or block dir with b1_*/ groups> [--profile-events <block>/profile_events.jsonl] [--watch-log watch2.log] [--out file.md]"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blockdata  # noqa: E402
import profile_exclusion as px  # noqa: E402

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


def row_pending_sites(r: dict) -> int:
    """Sites in pending of one episode, from the evidence LOG as run.summarize_rows does: an ack line after t0 or a delivery still pending at the deadline."""
    acks = {i for i, t in (r.get("plog_ack_ts") or {}).items() if t is not None}
    left = {i for i, n in (r.get("pending_left") or {}).items() if n}
    return len(acks | left)


def counts_from_cells(cells: list[dict]) -> dict:
    out: dict = {}
    for c in cells:
        if "rows" not in c or "aborted" in c:
            continue
        sp = c["cell_spec"]
        live = [r for r in c["rows"] if not r.get("excluded")]
        ok = [r for r in live if "dispute_rtt_s" in r]                  # x and n over the same episodes (docstring, point 6)
        a = out.setdefault(sp["arm"], {"x": 0, "n": 0, "no_rtt": 0, "cells": {}})
        x = sum(row_pending_sites(r) for r in ok)
        n = 10 * len(ok)
        a["x"] += x
        a["n"] += n
        a["no_rtt"] += len(live) - len(ok)
        k = a["cells"].get(sp["fanout"], (0, 0))
        a["cells"][sp["fanout"]] = (k[0] + x, k[1] + n)
    return out


def counts(path: Path) -> dict:
    """Counts from a cells.jsonl (compatibility) or from a run/block directory."""
    path = Path(path)
    if path.is_dir():
        return counts_from_cells(blockdata.load_block(path)[0])
    return counts_from_cells([json.loads(line) for line in path.read_text().splitlines() if line.strip()])


def second_clause(ci_d: tuple[float, float], ci_c: tuple[float, float], pd: float, pc: float) -> str:
    if ci_c[1] < ci_d[0]:
        return f"FALSIFIED: the CI of C [{ci_c[0]:.5f}; {ci_c[1]:.5f}] lies entirely below the CI of D [{ci_d[0]:.5f}; {ci_d[1]:.5f}] (the mTLS arm does not exceed D; point estimates C {pc:.5f}, D {pd:.5f})"
    if ci_c[0] > ci_d[1]:
        return f"satisfied: the CI of C lies entirely above the CI of D (point estimates C {pc:.5f}, D {pd:.5f})"
    return f"inconclusive for this clause: the CIs overlap (point estimates C {pc:.5f}, D {pd:.5f}; point estimate of C {'above' if pc > pd else 'NOT above'} D, information only)"


def report(source, profile_events=None, watch_log_text=None) -> str:
    profile = None
    if Path(source).is_dir():
        cells, man = blockdata.load_block(source)
        profile = man.get("profile")
    else:
        cells = [json.loads(l) for l in Path(source).read_text().splitlines() if l.strip()]
    return report_from_cells(cells, profile_events, watch_log_text, profile)


def report_from_cells(cells, profile_events=None, watch_log_text=None, profile=None) -> str:
    L = []
    if profile != "degraded":
        L.append(f"**Profile is {profile!r}, not `degraded`: (c) is a prediction at `degraded`; the classification below is NOT a test of (c).**\n")
    if profile_events or watch_log_text:
        labelled = ([("monitor", iv) for iv in px.monitor_intervals(profile_events)] if profile_events else []) + \
                   ([("watch2.log", iv) for iv in px.watch_unsettled_intervals(watch_log_text)] if watch_log_text else [])
        n_ex = sum(px.mark_overlaps(c["rows"], labelled)[0] for c in cells if "rows" in c and "aborted" not in c)
        L.append(f"Exclusion by overlap with an unsettled netem profile applied: {n_ex} episode(s) excluded ({len(labelled)} interval(s) read).\n")
    else:
        L.append("**WARNING: exclusion by overlap NOT applied (no --profile-events / --watch-log).**\n")
    cs = counts_from_cells(cells)
    L += ["| arm | pending / deliveries (pooled) | share | CP 95% CI | predicted | registered interval | classification | per FANOUT (pending/deliveries) |", "|---|---|---|---|---|---|---|---|"]
    cis = {}
    for arm in ("D", "C"):
        if arm not in cs or not cs[arm]["n"]:
            continue
        x, n = cs[arm]["x"], cs[arm]["n"]
        cis[arm] = clopper_pearson(x, n)
        L.append(f"| {arm} | {x} / {n} | {x / n:.5f} | [{cis[arm][0]:.5f}; {cis[arm][1]:.5f}] | {PREDICTED[arm][0]}-{PREDICTED[arm][1]} | {INTERVALS[arm]} | {classify(cis[arm], INTERVALS[arm])} | "
                 + ", ".join(f"f{k}: {v[0]}/{v[1]}" for k, v in sorted(cs[arm]["cells"].items())) + " |")
    L.append("\nNon-excluded episodes without dispute_rtt_s (in neither x nor n): " + ", ".join(f"{a}: {cs[a]['no_rtt']}" for a in ("D", "C") if a in cs))
    if "D" in cis and "C" in cis:
        L.append("\nSecond clause (registered, unambiguous form of the 2026-10-11 revision): " + second_clause(cis["D"], cis["C"], cs["D"]["x"] / cs["D"]["n"], cs["C"]["x"] / cs["C"]["n"]))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    args = sys.argv
    opt = lambda k: args[args.index(k) + 1] if k in args else None  # noqa: E731
    wl = Path(opt("--watch-log")).read_text() if opt("--watch-log") else None
    src = Path(args[1])
    text = report(src if src.is_dir() else src, opt("--profile-events"), wl)
    print(text)
    if opt("--out"):
        Path(opt("--out")).write_text(text)
