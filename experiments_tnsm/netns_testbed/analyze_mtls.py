#!/usr/bin/env python3
"""Verdicts of docs/audit/95 (criteria fixed before any data). Usage:
python3 analyze_mtls.py --eq-c DIR --eq-d DIR --oos-c DIR --oos-d DIR [--out report.md]   (DIR = a `testbed.py launch` output with episodes_*.jsonl)"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis as an  # noqa: E402

PRED = {"X1": {"v4": 0.307, "v5": 0.348, "D": 0.217}, "X2": {"v4": 0.217, "v5": 0.248, "D": 0.150},
        "X3": {"v4": 0.288, "v5": 0.319, "D": 0.210}, "X4": {"v4": 0.353, "v5": 0.388, "D": 0.265}}
MED1 = {"X1": {"v4": 5900, "v5": 5980, "D": 4060}, "X2": {"v4": 7700, "v5": 8100, "D": 5100}}
XD = {"X1": 60, "X2": 100, "X3": 150, "X4": 150}
EQ_D, EQ_C = 0.176, 0.309


def verdict(m: dict) -> dict:
    """m = {cond: {"C": late share of C, "D": late share of D}}."""
    interp = [x for x in sorted(m) if abs(m[x]["D"] - PRED[x]["D"]) <= 0.04 + 1e-12]
    unint = [x for x in sorted(m) if x not in interp]
    h_v1 = bool(interp) and all(abs(m[x]["C"] - PRED[x]["v5"]) <= 0.04 + 1e-12 for x in interp)
    e5 = statistics.mean(m[x]["C"] - PRED[x]["v5"] for x in interp) if interp else None
    e4 = statistics.mean(m[x]["C"] - PRED[x]["v4"] for x in interp) if interp else None
    h_v2 = bool(interp) and abs(e5) <= 0.02 + 1e-12 and e4 > 0.02
    return {"h_v0": not unint, "h_v1": h_v1, "h_v2": h_v2, "interpretable": interp, "uninterpretable": unint, "eps5": e5, "eps4": e4}


def eq_verdict(d_late: float, c_late: float) -> dict:
    a, b = abs(d_late - EQ_D) <= 0.04 + 1e-12, abs(c_late - EQ_C) <= 0.05 + 1e-12
    return {"h_v3a": a, "h_v3b": b, "h_v3": a and b}


def outcome(eq_ok: bool, v: dict) -> str:
    if len(v["uninterpretable"]) >= 2:
        return "inconclusive"
    if not eq_ok or not v["h_v1"]:
        return "not_confirmed"
    return "supports" if v["h_v2"] else "coherent_not_preferred"


def load(d: Path) -> list[dict]:
    out = []
    for f in sorted(d.glob("episodes_*.jsonl")):
        out += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    for a in ("eq-c", "eq-d", "oos-c", "oos-d"):
        ap.add_argument("--" + a, required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    eqc, eqd, oc, od = (load(Path(x)) for x in (a.eq_c, a.eq_d, a.oos_c, a.oos_d))
    L = ["| prova | braccio | R (s) | episodi validi | quota in ritardo | IC 95 % | previsione | |", "|---|---|---|---|---|---|---|---|"]
    m, t0 = {}, []
    ecs = [e for e in eqc if e["cell"]["kind"] == "eq"]
    eds = [e for e in eqd if e["cell"]["kind"] == "eq"]
    sc, sd = an.late_share_ci(ecs, 0.4, "C"), an.late_share_ci(eds, 0.4, "D")
    ev = eq_verdict(sd[0], sc[0])
    L.append(f"| EQ | D | 0,4 | {sum(e['setup_ok'] for e in eds)} | {sd[0]:.3f} | [{sd[1]:.3f}; {sd[2]:.3f}] | {EQ_D} | H-V3a {'regge' if ev['h_v3a'] else 'CADE'} |")
    L.append(f"| EQ | C | 0,4 | {sum(e['setup_ok'] for e in ecs)} | {sc[0]:.3f} | [{sc[1]:.3f}; {sc[2]:.3f}] | {EQ_C} | H-V3b {'regge' if ev['h_v3b'] else 'CADE'} |")
    for x, d in XD.items():
        R = 2 * d / 1000
        row = {}
        for arm, eps in (("C", oc), ("D", od)):
            sel = [e for e in eps if e["cell"]["kind"] == "oos" and e["cell"]["cond"] == x and e["cell"]["policy"] == "P0"]
            s = an.late_share_ci(sel, R, arm)
            row[arm] = s[0]
            L.append(f"| {x} | {arm} | {R:g} | {sum(e['setup_ok'] for e in sel)} | {s[0]:.3f} | [{s[1]:.3f}; {s[2]:.3f}] | " + (f"v4 {PRED[x]['v4']}, v5 {PRED[x]['v5']} |" if arm == "C" else f"{PRED[x]['D']} |") + " |")
        m[x] = row
        for arm, eps in (("C", oc), ("D", od)):
            z = [e for e in eps if e["cell"]["kind"] == "T0" and e["cell"]["d_ms"] == d]
            if z:
                t0.append((x, arm, an.t0_valid(z, R, False, arm=arm)["valid"]))
    v = verdict(m)
    res = outcome(ev["h_v3"], v)
    L += ["", "## T-0 (senza perdita, validità del testbed per ritardo)", ""] + [f"- {x} {arm}: {'valido' if ok else 'NON valido'}" for x, arm, ok in t0]
    L += ["", "## C/1 e D/1 (descrittivo, 60 episodi X1 e X2)", ""]
    for x in ("X1", "X2"):
        R = 2 * XD[x] / 1000
        for arm, eps in (("C", oc), ("D", od)):
            sel = [e for e in eps if e["cell"]["kind"] == "oos" and e["cell"]["cond"] == x and e["cell"]["policy"] == "S1"]
            comp = sorted(1000 * max(e["applies"].values()) for e in sel if e["setup_ok"] and len(e["applies"]) == 10 and all(q is not None for q in e["applies"].values()))
            L.append(f"- {x} {arm}: mediana ultimo sito " + (f"{statistics.median(comp):.0f} ms su {len(comp)} episodi completi, previsione " + (f"v4 {MED1[x]['v4']} / v5 {MED1[x]['v5']}" if arm == "C" else f"{MED1[x]['D']}") if comp else "n/d"))
    L += ["", "## Verdetti (criteri di audit 95)", "",
          f"- H-V3 (equivalenza del testbed con mTLS): {'regge' if ev['h_v3'] else 'CADE'}",
          f"- H-V0 (controllo D, quattro condizioni): {'regge' if v['h_v0'] else 'CADE in ' + ', '.join(v['uninterpretable'])}",
          f"- H-V1 (|C − v5| ≤ 0,04 in ogni condizione interpretabile): {'regge' if v['h_v1'] else 'CADE'}",
          f"- H-V2 (|ε5| ≤ 0,02 e ε4 > 0,02): {'regge' if v['h_v2'] else 'CADE'} (ε5 = {v['eps5']}, ε4 = {v['eps4']})",
          f"- **Esito per il paper: {res}**"]
    t = "\n".join(L) + "\n"
    print(t)
    if a.out:
        Path(a.out).write_text(t)


if __name__ == "__main__":
    main()
