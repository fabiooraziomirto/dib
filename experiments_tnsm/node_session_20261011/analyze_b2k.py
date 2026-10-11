"""Analysis of B2-kill (audit 45). Local only; reuses analyze_b1.py (med_ci, diff_ci) unchanged. Tests: test_analyze_b2k.py (written first).
Per cell (profile, arm, T, k) of the b2kill invocations: (d-kill) falsified iff the bootstrap CI (percentile 95%, 10 000, seed 20261011) lower bound of the
median convergence_s exceeds the cell's bound_s; (e) violated by any trial with violation_over_bound or final_all_monitor_only False (I1-I3 are NOT checked
beyond this); T15 - T5 descriptive only (Q9). Usage: python3 analyze_b2k.py <b2k out dir with b2k_<profile>/b2kill_<arm>/> [--out report.md]"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "m67_retraction"))
import analyze_b1 as b1  # noqa: E402
import blockdata  # noqa: E402


def cell_summary(rows: list, bound_s: float, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(b1.SEED)
    ex = Counter(r.get("excluded_reason") or ("client_timeout" if r.get("client_timeout") else "excluded") for r in rows if r.get("excluded"))
    used = [r for r in rows if not r.get("excluded")]
    conv = [r["convergence_s"] for r in used if r.get("convergence_s") is not None]
    e_viol = sum(1 for r in used if r.get("violation_over_bound") or r.get("final_all_monitor_only") is False)
    t = b1.med_ci(conv, rng) if conv else None
    if t is None:
        d = "not evaluable"
    else:
        d = "falsified" if t[1] > bound_s else ("inconclusive" if t[0] > bound_s else "not falsified")
    return {"n": len(used), "n_converged": len(conv), "n_never": sum(1 for r in used if r.get("convergence_s") is None), "median_ci": t,
            "bound_s": bound_s, "d_kill": d, "e_violations": e_viol, "excluded_by_cause": dict(ex)}


def global_e(summaries: list[dict]) -> str:
    return "falsified" if any(s["e_violations"] for s in summaries) else "not falsified"


def t_difference(rows15: list, rows5: list, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(b1.SEED)
    a = [r["convergence_s"] for r in rows15 if not r.get("excluded") and r.get("convergence_s") is not None]
    b = [r["convergence_s"] for r in rows5 if not r.get("excluded") and r.get("convergence_s") is not None]
    if not a or not b:
        return None
    d, lo, hi = b1.diff_ci(a, b, rng)
    return {"diff_s": d, "lo": lo, "hi": hi, "n15": len(a), "n5": len(b)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(a.dir)
    rng = random.Random(b1.SEED)
    cells = []
    for bd in sorted(root.glob("b2k_*")):
        prof = bd.name[4:]
        for ad in sorted(bd.glob("b2kill_*")):
            try:
                for c in blockdata.load_cells(ad):
                    if "rows" in c and "aborted" not in c:
                        cells.append((prof, ad.name, c))
            except FileNotFoundError:
                continue
    L = ["# B2-kill analysis (audit 45)", "", "| profile | arm | T | k | n | converged | never | median s [CI] | bound s | (d-kill) | (e) violations | excluded |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    sums, by = [], {}
    for prof, dn, c in sorted(cells, key=lambda x: (x[0], x[2]["cell_spec"]["arm"], x[2]["cell_spec"]["k"], x[2]["cell_spec"]["T"])):
        sp = c["cell_spec"]
        s = cell_summary(c["rows"], c["budget"]["bound_kill_s"], rng)
        sums.append(s)
        by[(prof, sp["arm"], sp["k"], sp["T"])] = c["rows"]
        t = s["median_ci"]
        L.append(f"| {prof} | {sp['arm']} | {sp['T']} | {sp['k']} | {s['n']} | {s['n_converged']} | {s['n_never']} | {b1.fmt(t) if t else '—'} | {s['bound_s']:.2f} | {s['d_kill']} | {s['e_violations']} | {s['excluded_by_cause'] or 0} |")
    n_f = sum(1 for s in sums if s["d_kill"] == "falsified")
    L += ["", f"**(d-kill)** falsified in {n_f}/{len(sums)} cells; **(e)** {global_e(sums)} (I1-I3 only through `final_all_monitor_only`; no other invariant checked).",
          "", "## T15 - T5 (descriptive, decision Q9; no verdict)", ""]
    for (prof, arm, k, T), rows in sorted(by.items()):
        if T == 15 and (prof, arm, k, 5) in by:
            d = t_difference(rows, by[(prof, arm, k, 5)], rng)
            if d is None:
                L.append(f"- {prof}/{arm}/k={k}: not evaluable (a side has no converged trial)")
                continue
            L.append(f"- {prof}/{arm}/k={k}: {d['diff_s']:.3f} s [{d['lo']:.3f}; {d['hi']:.3f}] (n15={d['n15']}, n5={d['n5']}); reference interval [0; 1.5] s (a14:254-257), not a criterion")
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
