#!/usr/bin/env python3
"""Verdicts T-0..T-3 of audit 75 on a testbed run. Predictions are RECOMPUTED from the model (retry_model/model.py, rto=True, seed 20261012, 20 000 episodes), the same call that
produced the table committed in audit 75 before the testbed existed. Usage: python3 analyze_run.py <run dir> [--out report.md]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "retry_model"))
import analysis as an  # noqa: E402
import model as mdl  # noqa: E402

TOL_LATE, TOL_SLOW = 0.04, 0.12           # T-1 criteria of audit 75


def load(run: Path) -> dict:
    cells: dict = {}
    for f in sorted(run.glob("episodes_*.jsonl")):
        for l in f.read_text().splitlines():
            if l.strip():
                e = json.loads(l)
                c = e["cell"]
                cells.setdefault((c["d_ms"], c["loss_pct"], c["policy"]), []).append(e)
    return cells


def predict(d_ms: int, loss_pct: int, policy: str) -> dict:
    kw = {"warm_first": True} if policy == "P1" else {}
    return mdl.simulate("D", 10, episodes=20000, seed=20261012, p_loss=loss_pct / 100, R_=2 * d_ms / 1000, rto=True, **kw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cells = load(Path(a.run))
    L = ["# Banco netns: verdetti T-0..T-3 (audit 75)", ""]
    # T-0
    L += ["## T-0 (validità, p = 0)", "", "| d ms | politica | mediana per sito ms | nominale ms | in ritardo | n | valido |", "|---|---|---|---|---|---|---|"]
    t0_ok = True
    for d in (50, 100, 200):
        for pol in ("P0", "P1"):
            eps = cells.get((d, 0, pol), [])
            v = an.t0_valid(eps, 2 * d / 1000, pol == "P1")
            t0_ok &= bool(v["valid"])
            L.append(f"| {d} | {pol} | {1000 * v.get('median_s', float('nan')):.0f} | {1000 * v.get('nominal_s', float('nan')):.0f} | {v.get('late')} | {v.get('n')} | {v['valid']} |")
    L += ["", f"**T-0: {'SUPERATO' if t0_ok else 'FALLITO: il banco non è valido, nulla di ciò che segue si riporta'}**", ""]
    # T-1 / T-2 / T-3
    L += ["## Celle (60 episodi; previsione del modello v2 tra parentesi)", "",
          "| d ms | perdita | politica | validi | in ritardo per sito | slow episodes | pending episodi | mediana ultimo ms | p95 ultimo ms |", "|---|---|---|---|---|---|---|---|---|"]
    t1_ok, t1_big, t1_n = 0, 0, 0
    t2_reduced, t2_total, t3_bad = 0, 0, []
    detail = []
    for d in (50, 100, 200):
        for p in (2, 5, 10):
            summ, pred = {}, {}
            for pol in ("P0", "P1"):
                eps = cells.get((d, p, pol), [])
                summ[pol] = an.cell_summary(eps, 2 * d / 1000, pol == "P1")
                pred[pol] = predict(d, p, pol)
                s, m = summ[pol], pred[pol]
                f = lambda x, n=3: "—" if x is None else f"{x:.{n}f}"  # noqa: E731
                L.append(f"| {d} | {p}% | {pol} | {s['n_valid']} | {f(s['late_share'])} ({f(m['late_share'])}) | {f(s['slow_episode_fraction'])} ({f(m['slow_episode_fraction'])}) | "
                         f"{f(s['pending_fraction'])} ({f(m['pending_fraction'])}) | {f(s['median_last_ms'], 0)} ({f(m['median_ms'], 0)}) | {f(s['p95_last_ms'], 0)} ({f(m['p95_ms'], 0)}) |")
            s0, m0 = summ["P0"], pred["P0"]
            if s0["late_share"] is not None and s0["slow_episode_fraction"] is not None:
                t1_n += 1
                dl, ds = abs(s0["late_share"] - m0["late_share"]), abs(s0["slow_episode_fraction"] - m0["slow_episode_fraction"])
                ok = dl <= TOL_LATE and ds <= TOL_SLOW
                t1_ok += ok
                t1_big += (dl > 2 * TOL_LATE or ds > 2 * TOL_SLOW)
                detail.append(f"- ({d} ms, {p}%): |Δ late| = {dl:.3f}, |Δ slow| = {ds:.3f} -> {'ok' if ok else 'FUORI'}")
            ci = an.boot_diff_late_share(cells.get((d, p, "P1"), []), cells.get((d, p, "P0"), []), 2 * d / 1000, True, False)
            m0s, m1s = an.median_site_ms(cells.get((d, p, "P0"), [])), an.median_site_ms(cells.get((d, p, "P1"), []))
            if ci is not None and m0s is not None and m1s is not None:
                t2_total += 1
                red = ci[1] < 0 and m1s < m0s
                t2_reduced += red
                detail.append(f"- T-2 ({d} ms, {p}%): late(P1) - late(P0) IC95 [{ci[0]:.3f}; {ci[1]:.3f}], mediana per sito P1 {m1s:.0f} contro P0 {m0s:.0f} ms -> {'ridotto' if red else 'NON ridotto'}")
            if summ["P0"]["pending_fraction"] is not None and summ["P1"]["pending_fraction"] is not None and summ["P1"]["pending_fraction"] - summ["P0"]["pending_fraction"] > 0.03:
                t3_bad.append((d, p))
    L += ["", "## Dettaglio", ""] + detail + ["", "## Verdetti", ""]
    L.append(f"- **T-1 (modello fuori campione, P0):** {t1_ok}/{t1_n} celle entro i criteri (late ±{TOL_LATE}, slow ±{TOL_SLOW}); celle oltre il doppio: {t1_big}. "
             f"**{'MODELLO VALIDO' if (t1_n == 9 and t1_ok >= 7 and t1_big == 0) else 'MODELLO NON VALIDATO'}** (regola: ≥ 7/9 e nessuna oltre il doppio).")
    L.append(f"- **T-2 (effetto di P1):** P1 riduce le consegne in ritardo in {t2_reduced}/{t2_total} condizioni. **{'FALSIFICATA' if (t2_total - t2_reduced) >= 3 else 'non falsificata'}** (falsificata se non riduce in ≥ 3).")
    L.append(f"- **T-3 (sicurezza):** pending(P1) − pending(P0) > 3 punti in: {t3_bad or 'nessuna condizione'}. **{'FALSIFICATA' if t3_bad else 'non falsificata'}**.")
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)


if __name__ == "__main__":
    main()
