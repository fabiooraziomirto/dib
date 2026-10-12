#!/usr/bin/env python3
"""Verdicts T-S0..T-S2 of audit 77. Predictions recomputed from the model (retry_model, rto=True, seed 20261012, 20 000 episodes).
Usage: python3 analyze_s1.py <s1 run dir> <parallel reference run dir (run_20261012b)> [--out report.md]"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "retry_model"))
import model as mdl  # noqa: E402


def median_gap(eps: list[dict]):
    """Median gap (s) between consecutive sorted apply times, over complete episodes."""
    gaps = []
    for e in eps:
        v = [x for x in e["applies"].values() if x is not None]
        if e["setup_ok"] and len(v) == 10:
            v.sort()
            gaps += [b - a for a, b in zip(v, v[1:])]
    return statistics.median(gaps) if gaps else None


def t_s1_verdict(measured: dict, predicted: dict, tol: float = 0.25) -> dict:
    inside = sum(1 for k in predicted if k in measured and measured[k] is not None and abs(measured[k] - predicted[k]) <= tol * predicted[k] + 1e-9)
    return {"within": inside, "n": len(predicted), "valid": inside >= 7}


def t_s2_verdict(ratios: list[float], threshold: float = 2.0) -> dict:
    return {"min_ratio": min(ratios) if ratios else None, "falsified": any(r < threshold for r in ratios)}


def t_s0_verdict(gaps: list, R: list) -> dict:
    low = sum(1 for g, r in zip(gaps, R) if g is None or g < 0.75 * r)
    return {"cells_below": low, "falsified": low > 2}


def load(run: Path) -> dict:
    cells: dict = {}
    for f in sorted(run.glob("episodes_*.jsonl")):
        for l in f.read_text().splitlines():
            if l.strip():
                e = json.loads(l)
                c = e["cell"]
                cells.setdefault((c["d_ms"], c["loss_pct"], c["policy"]), []).append(e)
    return cells


def _lasts(eps):
    return sorted(1000 * max(e["applies"].values()) for e in eps if e["setup_ok"] and len(e["applies"]) == 10 and all(v is not None for v in e["applies"].values()))


def boot_median_ci(xs, seed=20261012, res=10000):
    rng = random.Random(seed)
    v = sorted(statistics.median(rng.choices(xs, k=len(xs))) for _ in range(res))
    return v[int(0.025 * res)], v[int(0.975 * res) - 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_s1")
    ap.add_argument("run_par")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    s, p = load(Path(a.run_s1)), load(Path(a.run_par))
    L = ["# Banco netns: sequenziale contro parallelo (audit 77)", "", "| d ms | perdita | S1 validi/episodi | S1 mediana ms [IC] | previsione ms | P0 mediana ms | rapporto S1/P0 | gap mediano tra siti s | episodi incompleti S1 |", "|---|---|---|---|---|---|---|---|---|"]
    meas, pred, ratios, gaps, Rs = {}, {}, [], [], []
    for d in (50, 100, 200):
        for pl in (2, 5, 10):
            eps = s.get((d, pl, "S1"), [])
            ls = _lasts(eps)
            pr = mdl.simulate("D", 1, episodes=20000, seed=20261012, p_loss=pl / 100, R_=2 * d / 1000, rto=True)["median_ms"]
            lp = _lasts(p.get((d, pl, "P0"), []))
            m1 = statistics.median(ls) if ls else None
            m0 = statistics.median(lp) if lp else None
            g = median_gap(eps)
            meas[(d, pl)], pred[(d, pl)] = m1, pr
            if m1 and m0:
                ratios.append(m1 / m0)
            gaps.append(g)
            Rs.append(2 * d / 1000)
            ci = boot_median_ci(ls) if ls else None
            valid = sum(1 for e in eps if e["setup_ok"])
            L.append(f"| {d} | {pl}% | {valid}/{len(eps)} | {m1:.0f} [{ci[0]:.0f}; {ci[1]:.0f}] | {pr:.0f} | {m0:.0f} | {m1 / m0:.1f} | {g:.2f} | {valid - len(ls)} |" if (m1 and m0 and ci and g is not None) else f"| {d} | {pl}% | {valid}/{len(eps)} | n/d | {pr:.0f} | | | | |")
    v0, v1, v2 = t_s0_verdict(gaps, Rs), t_s1_verdict(meas, pred), t_s2_verdict(ratios)
    L += ["", "## Verdetti", "",
          f"- **T-S0 (sequenzialità):** celle con gap mediano < 0,75 R: {v0['cells_below']} -> **{'FALSIFICATA: il banco non è valido per S1' if v0['falsified'] else 'non falsificata'}**.",
          f"- **T-S1 (modello sequenziale):** {v1['within']}/{v1['n']} celle entro ±25 % -> **{'MODELLO SEQUENZIALE VALIDATO' if v1['valid'] else 'NON VALIDATO'}** (regola: ≥ 7/9).",
          f"- **T-S2 (default parallelo):** rapporto minimo S1/P0 = {v2['min_ratio']:.2f} (soglia 2,0) -> **{'FALSIFICATA' if v2['falsified'] else 'non falsificata'}**."]
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)


if __name__ == "__main__":
    main()
