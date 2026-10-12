#!/usr/bin/env python3
"""Verdicts T-V0..T-V3 of audit 78 (model v3 validation on NEW conditions). Predictions recomputed from the model (rto=True, reconcile=True, seed 20261012, 20 000 episodes).
Usage: python3 analyze_v3.py <run dir> [--out report.md]"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "retry_model"))
import analysis as an  # noqa: E402
import analyze_s1 as s1  # noqa: E402
import model as mdl  # noqa: E402

CONDITIONS = [(75, 3), (75, 7), (150, 3), (150, 7)]


def t_v1(cells: list[dict]) -> dict:
    ok = sum(1 for c in cells if c["late"] <= 0.04 and c["slow"] <= 0.12 and c["pending"] <= 0.02)
    return {"cells_ok": ok, "n": len(cells), "holds": ok >= 3}


def t_v2(rel_errors: list[float]) -> dict:
    ok = sum(1 for e in rel_errors if e <= 0.25)
    return {"cells_ok": ok, "n": len(rel_errors), "holds": ok >= 3}


def overall(v0: bool, v1: bool, v2: bool) -> str:
    return "VALIDATO" if (v0 and v1 and v2) else "NON VALIDATO"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cells = s1.load(Path(a.run))
    L = ["# Banco netns: validazione confermativa del modello v3 (audit 78)", ""]
    v0 = True
    L += ["## T-V0 (validità, P0 a p = 0)", "", "| d ms | mediana per sito ms | nominale ms | in ritardo | n | valido |", "|---|---|---|---|---|---|"]
    for d in (75, 150):
        v = an.t0_valid(cells.get((d, 0, "P0"), []), 2 * d / 1000, False)
        v0 &= bool(v["valid"])
        L.append(f"| {d} | {1000 * v.get('median_s', float('nan')):.0f} | {1000 * v.get('nominal_s', float('nan')):.0f} | {v.get('late')} | {v.get('n')} | {v['valid']} |")
    L += ["", f"**T-V0: {'SUPERATO' if v0 else 'FALLITO: nulla di ciò che segue si riporta'}**", "",
          "## Parallelo (P0): misura (previsione v3)", "", "| d ms | perdita | validi | in ritardo per sito | slow episodes | pending | mediana ultimo ms | p95 ms |", "|---|---|---|---|---|---|---|---|"]
    pc = []
    for d, p in CONDITIONS:
        eps = cells.get((d, p, "P0"), [])
        s = an.cell_summary(eps, 2 * d / 1000, False)
        m = mdl.simulate("D", 10, episodes=20000, seed=20261012, p_loss=p / 100, R_=2 * d / 1000, rto=True, reconcile=True)
        pend = s["pending_fraction"] if s["pending_fraction"] is not None else 1.0
        pc.append({"late": abs(s["late_share"] - m["late_share"]) if s["late_share"] is not None else 1.0,
                   "slow": abs(s["slow_episode_fraction"] - m["slow_episode_fraction"]) if s["slow_episode_fraction"] is not None else 1.0, "pending": pend})
        f = lambda x, n=3: "—" if x is None else f"{x:.{n}f}"  # noqa: E731
        L.append(f"| {d} | {p}% | {s['n_valid']} | {f(s['late_share'])} ({f(m['late_share'])}) | {f(s['slow_episode_fraction'])} ({f(m['slow_episode_fraction'])}) | {f(pend)} (0) | "
                 f"{f(s['median_last_ms'], 0)} ({f(m['median_ms'], 0)}) | {f(s['p95_last_ms'], 0)} ({f(m['p95_ms'], 0)}) |")
    L += ["", "## Sequenziale (S1): misura (previsione v3)", "", "| d ms | perdita | validi | mediana ultimo ms [IC] | p95 ms | errore relativo |", "|---|---|---|---|---|---|"]
    rel = []
    for d, p in CONDITIONS:
        eps = cells.get((d, p, "S1"), [])
        ls = s1._lasts(eps)
        m = mdl.simulate("D", 1, episodes=20000, seed=20261012, p_loss=p / 100, R_=2 * d / 1000, rto=True, reconcile=True)
        if ls:
            med = statistics.median(ls)
            ci = s1.boot_median_ci(ls)
            e = abs(med - m["median_ms"]) / m["median_ms"]
            rel.append(e)
            p95 = sorted(ls)[int(0.95 * (len(ls) - 1))]
            L.append(f"| {d} | {p}% | {sum(1 for x in eps if x['setup_ok'])}/{len(eps)} | {med:.0f} [{ci[0]:.0f}; {ci[1]:.0f}] ({m['median_ms']:.0f}) | {p95:.0f} ({m['p95_ms']:.0f}) | {e:.2f} |")
        else:
            rel.append(9.9)
            L.append(f"| {d} | {p}% | 0 | n/d | | |")
    r1, r2 = t_v1(pc), t_v2(rel)
    L += ["", "## Verdetti", "",
          f"- **T-V1 (parallelo):** {r1['cells_ok']}/{r1['n']} celle entro i criteri -> **{'regge' if r1['holds'] else 'NON regge'}** (regola: ≥ 3/4).",
          f"- **T-V2 (sequenziale):** {r2['cells_ok']}/{r2['n']} celle entro ±25 % -> **{'regge' if r2['holds'] else 'NON regge'}** (regola: ≥ 3/4).",
          f"- **Modello v3 fuori campione: {overall(v0, r1['holds'], r2['holds'])}** (richiede T-V0, T-V1 e T-V2)."]
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)


if __name__ == "__main__":
    main()
