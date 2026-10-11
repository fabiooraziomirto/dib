"""default - D at `lan` (P-a1 and P-a2 of the frozen prediction 6c11e48), same-session cells of `b1_default/` (run 2026-10-11 08:26-08:30 UTC,
tree bf272e8). Written AFTER the per-cell medians of that run had been printed by analyze_b1.py (disclosed: default f1 ~128 ms vs D f1 ~48 ms);
the registered criteria and the method (difference of medians, independent bootstrap over episodes, 10000 resamples, seed 20261011) are those of
analyze_b1.py and are not chosen from these numbers.
Criteria (registered intervals; reading fixed at 8b7b45e: FALSIFIED only if the CI is ENTIRELY outside; if it crosses a bound: inconclusive):
  P-a1  default - D, last site (P-log), FANOUT 1: +61.5 ms, interval [46, 77]
  P-a2  default - D, FANOUT 10: between +6 and +62 ms, interval [3, 75]
Both are evaluated on the last-site P-log and on dispute-rtt (bias 0 at lan); the P-log acceptance of each cell is reported (D FANOUT 10 is NOT
accepted by the per-cell 10% rule in this run: its recorded measure is dispute-rtt, so for P-a2 the dispute-rtt line is the consistent one).
Hypothesis: the `default` arm, never run live with this driver, behaves as the registered prediction; falsification as above.
Usage: python3 analyze_default_vs_d.py lan_20261011/b1_default"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_b1 as a  # noqa: E402


def classify(x, lo, hi):
    if lo <= x[1] and x[2] <= hi:
        return "CI entirely inside"
    if x[2] < lo or x[1] > hi:
        return "CI ENTIRELY OUTSIDE: falsified"
    return "CI crosses a bound: inconclusive"


def main():
    d = Path(sys.argv[1])
    cells = [json.loads(x) for x in (d / "cells.jsonl").read_text().splitlines()]
    by = {}
    for c in cells:
        sp = c["cell_spec"]
        rows = c["rows"]
        by[(sp["arm"], sp["fanout"])] = {"rtt": [1000 * r["dispute_rtt_s"] for r in rows if not r.get("excluded") and "dispute_rtt_s" in r],
                                         "last": a.last_site(rows), "acc": c["summary"]["plog_acceptable_rule_10pct"]}
    rng = random.Random(a.SEED)
    out = []
    for (fo, lo, hi, name, point) in ((1, 46, 77, "P-a1", 61.5), (10, 3, 75, "P-a2", "6..62")):
        for q, qn in (("last", "last-site P-log"), ("rtt", "dispute-rtt")):
            x = a.diff_ci(by[("default", fo)][q], by[("D", fo)][q], rng)
            out.append(f"- {name} FANOUT {fo}, {qn}: default - D = {x[0]:.2f} ms [{x[1]:.2f}; {x[2]:.2f}] vs registered {point} ms, interval [{lo}, {hi}] -> {classify(x, lo, hi)} "
                       f"(P-log accepted: default {by[('default', fo)]['acc']}, D {by[('D', fo)]['acc']})")
    text = "\n".join(out) + "\n"
    print(text)
    (d.parent / "analysis_default_vs_d.md").write_text("# default - D at lan (same session)\n\n" + text)


if __name__ == "__main__":
    main()
