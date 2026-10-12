#!/usr/bin/env python3
"""Verdicts T-W0..T-W2 of audit 80 (model v4 on NEW conditions). Predictions recomputed (rto, reconcile, req_segments = 2; seed 20261012; 20 000 episodes).
Usage: python3 analyze_v4.py <run dir> [--out report.md]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "retry_model"))
import analysis as an  # noqa: E402
import analyze_s1 as s1  # noqa: E402
import model as mdl  # noqa: E402

CONDITIONS = [(d, p) for d in (60, 120, 180) for p in (4, 8)]


def _passes(c: dict) -> bool:
    return c["late"] <= 0.03 and c["slow"] <= 0.10 and c["pending"] <= 0.02


def count_pass(cells: list[dict]) -> int:
    return sum(1 for c in cells if _passes(c))


def t_w1(cells: list[dict]) -> dict:
    ok = count_pass(cells)
    beyond = sum(1 for c in cells if c["late"] > 0.06 or c["slow"] > 0.20)
    return {"cells_ok": ok, "n": len(cells), "beyond_double": beyond, "holds": ok >= 5 and beyond == 0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cells = s1.load(Path(a.run))
    L = ["# Banco netns: validazione confermativa del modello v4 (audit 80)", "", "## T-W0 (validità, P0 a p = 0)", "", "| d ms | mediana per sito ms | nominale ms | in ritardo | n | valido |", "|---|---|---|---|---|---|"]
    w0 = True
    for d in (60, 120, 180):
        v = an.t0_valid(cells.get((d, 0, "P0"), []), 2 * d / 1000, False)
        w0 &= bool(v["valid"])
        L.append(f"| {d} | {1000 * v.get('median_s', float('nan')):.0f} | {1000 * v.get('nominal_s', float('nan')):.0f} | {v.get('late')} | {v.get('n')} | {v['valid']} |")
    L += ["", f"**T-W0: {'SUPERATO' if w0 else 'FALLITO: nulla di ciò che segue si riporta'}**", "",
          "## P0: misura (previsione v4) e confronto con v3", "", "| d ms | perdita | validi | in ritardo per sito | slow episodes | pending | mediana ultimo ms | p95 ms | v3 in ritardo |", "|---|---|---|---|---|---|---|---|---|"]
    c4, c3 = [], []
    for d, p in CONDITIONS:
        s = an.cell_summary(cells.get((d, p, "P0"), []), 2 * d / 1000, False)
        kw = dict(episodes=20000, seed=20261012, p_loss=p / 100, R_=2 * d / 1000, rto=True, reconcile=True)
        m4 = mdl.simulate("D", 10, req_segments=2, **kw)
        m3 = mdl.simulate("D", 10, req_segments=1, **kw)
        pend = s["pending_fraction"] if s["pending_fraction"] is not None else 1.0
        late = s["late_share"] if s["late_share"] is not None else 9.0
        slow = s["slow_episode_fraction"] if s["slow_episode_fraction"] is not None else 9.0
        c4.append({"late": abs(late - m4["late_share"]), "slow": abs(slow - m4["slow_episode_fraction"]), "pending": pend})
        c3.append({"late": abs(late - m3["late_share"]), "slow": abs(slow - m3["slow_episode_fraction"]), "pending": pend})
        f = lambda x, n=3: "—" if x is None else f"{x:.{n}f}"  # noqa: E731
        L.append(f"| {d} | {p}% | {s['n_valid']} | {f(s['late_share'])} ({f(m4['late_share'])}) | {f(s['slow_episode_fraction'])} ({f(m4['slow_episode_fraction'])}) | {f(pend)} (0) | "
                 f"{f(s['median_last_ms'], 0)} ({f(m4['median_ms'], 0)}) | {f(s['p95_last_ms'], 0)} ({f(m4['p95_ms'], 0)}) | {f(m3['late_share'])} |")
    r = t_w1(c4)
    L += ["", "## Verdetti", "",
          f"- **T-W1 (modello v4):** {r['cells_ok']}/{r['n']} celle entro ±3 punti (in ritardo), ±10 (slow) e pending ≤ 2 %; celle oltre il doppio: {r['beyond_double']} -> **{'MODELLO v4 VALIDATO' if (w0 and r['holds']) else 'MODELLO v4 NON VALIDATO'}** (regola: ≥ 5/6 e nessuna oltre il doppio).",
          f"- **T-W2 (descrittivo):** v3 avrebbe superato {count_pass(c3)}/{len(c3)} celle con le stesse tolleranze."]
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)


if __name__ == "__main__":
    main()
