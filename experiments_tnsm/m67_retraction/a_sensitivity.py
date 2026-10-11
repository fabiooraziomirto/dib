"""Sensitivity of rule (a) at `wan` to the choice of the `lan` reference (user request 2026-10-11). Descriptive; it does NOT replace the
pre-registered verdict of audit 27 (reference = the adjacent `lan` session 'before', 08:40 UTC), which stays the result.
Hypothesis (declared before running): the verdict "not falsified" of the four wan cells does not change if the reference is any of the three
`lan` sessions of the day (b1 07:52, b1_default 08:27, before 08:40) or their maximum, because the highest threshold-lowering reference
(smallest lan median) still leaves the wan median under pred + 3 x reference. Falsification of the robustness: any combination giving a verdict
other than "not falsified". Also reported: the reference value below which the verdict would change (median > threshold; CI lower > threshold),
which shows which cells can be sensitive at all.
Measure: last-site P-log of the wan cell (all four are P-log-apply); the lan reference uses the same quantity (last-site P-log), median over episodes.
Usage: python3 a_sensitivity.py"""
import json
import statistics as S
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_b1 as a  # noqa: E402
import random  # noqa: E402

N_RTT = {"D": 2, "C": 3}
R = 0.160
SESS = {"07:52 (b1)": HERE / "lan_20261011/b1", "08:27 (b1_default)": HERE / "lan_20261011/b1_default", "08:40 (before, adjacent)": HERE / "lan_ref_20261011/before"}


def cells(d):
    return {(c["cell_spec"]["arm"], c["cell_spec"]["fanout"]): c for c in map(json.loads, (d / "cells.jsonl").read_text().splitlines())}


def main():
    rng = random.Random(a.SEED)
    wan = cells(HERE / "wan_20261011/b1")
    lan = {k: cells(v) for k, v in SESS.items()}
    out = ["| arm | FANOUT | wan median ms [CI] | 10xn_RTTxR or n_RTTxR ms | reference | lan median ms | threshold ms | excess ms | verdict |", "|---|---|---|---|---|---|---|---|---|"]
    lim = []
    for key in sorted(wan):
        arm, fo = key
        t = a.med_ci(a.last_site(wan[key]["rows"]), rng)
        pred = 1000 * N_RTT[arm] * R * (10 if fo == 1 else 1)
        meds = {}
        for s, cs in lan.items():
            if key in cs:
                meds[s] = S.median(a.last_site(cs[key]["rows"]))
        meds["max of sessions"] = max(meds.values())
        for s, m in meds.items():
            ra = a.rule_a(t, pred, m)
            out.append(f"| {arm} | {fo} | {t[0]:.1f} [{t[1]:.1f}; {t[2]:.1f}] | {pred:.0f} | {s} | {m:.2f} | {ra['threshold_ms']:.1f} | {ra['excess_ms']:.1f} | {ra['verdict']} |")
        # reference value at which the verdict would change (3 x ref = median - pred, or CI lower - pred)
        r_med = (t[0] - pred) / 3
        r_ci = (t[1] - pred) / 3
        lim.append(f"- {arm} FANOUT {fo}: median {t[0]:.1f} vs pred {pred:.0f} (diff {t[0] - pred:+.1f} ms): " +
                   (f"verdict would become 'inconclusive' only for a lan reference below {r_med:.2f} ms and 'falsified' below {r_ci:.2f} ms (lan medians of the day: {min(meds.values()):.1f}-{max(meds.values()):.1f} ms)"
                    if t[0] > pred else "the median is below the network term alone: no non-negative reference can make it exceed the threshold"))
    text = "\n".join(out) + "\n\n" + "\n".join(lim) + "\n"
    print(text)
    (HERE / "wan_20261011/sensitivity_a.md").write_text("# Sensitivity of rule (a) to the lan reference (descriptive; the pre-registered verdict is the adjacent 'before' session)\n\n" + text)


if __name__ == "__main__":
    main()
