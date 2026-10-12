#!/usr/bin/env python3
"""Verdicts of docs/audit/107 (criteria fixed before any data): validation of model v5 (mTLS) on the REAL deployment at four out-of-sample conditions X1-X4. Usage:
python3 analyze_node_oos.py --x1 DIR --x2 DIR --x3 DIR --x4 DIR [--out report.md]    (DIR = a run.py b1 output dir with cells.jsonl: arms D and C, FANOUT 10)"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

PRED = {"X1": {"v4": 0.307, "v5": 0.348, "D": 0.217}, "X2": {"v4": 0.217, "v5": 0.248, "D": 0.150},
        "X3": {"v4": 0.288, "v5": 0.319, "D": 0.210}, "X4": {"v4": 0.353, "v5": 0.388, "D": 0.265}}
XR = {"X1": 0.12, "X2": 0.20, "X3": 0.30, "X4": 0.30}


def _counts(rows, R, arm):
    nominal = (2.5 if arm == "C" else 1.5) * R
    out = []
    for r in rows:
        if r.get("excluded"):
            continue
        v = [x for x in (r.get("withdrawn_plog_s") or {}).values() if x is not None]
        out.append((sum(1 for x in v if x > nominal + 0.75 * R), len(v)))
    return out


def late_share(rows, R, arm, res=5000, seed=20261012):
    c = _counts(rows, R, arm)
    if not c:
        return None
    share = sum(x for x, _ in c) / max(sum(n for _, n in c), 1)
    rng = random.Random(seed)
    vals = []
    for _ in range(res):
        s = rng.choices(c, k=len(c))
        vals.append(sum(x for x, _ in s) / max(sum(n for _, n in s), 1))
    vals.sort()
    return share, vals[int(0.025 * res)], vals[int(0.975 * res) - 1]


def verdict(m):
    interp = [x for x in sorted(m) if abs(m[x]["D"] - PRED[x]["D"]) <= 0.04 + 1e-12]
    unint = [x for x in sorted(m) if x not in interp]
    h1 = bool(interp) and all(abs(m[x]["C"] - PRED[x]["v5"]) <= 0.05 + 1e-12 for x in interp)
    if interp:
        e5 = [m[x]["C"] - PRED[x]["v5"] for x in interp]
        e4 = [m[x]["C"] - PRED[x]["v4"] for x in interp]
        mae5, mae4 = statistics.mean(abs(v) for v in e5), statistics.mean(abs(v) for v in e4)
        h2 = mae5 < mae4 and abs(statistics.mean(e5)) <= 0.04 + 1e-12
        eps = {"mae5": mae5, "mae4": mae4, "eps5": statistics.mean(e5), "eps4": statistics.mean(e4)}
    else:
        h2, eps = False, {}
    return {"h_n0": not unint, "h_n1": h1, "h_n2": h2, "interpretable": interp, "uninterpretable": unint, **eps}


def outcome(v):
    if len(v["uninterpretable"]) >= 2:
        return "inconclusive"
    if not v["h_n1"]:
        return "not_confirmed"
    return "supports" if v["h_n2"] else "coherent_not_preferred"


def _rows(d):
    out = {}
    for l in (Path(d) / "cells.jsonl").read_text().splitlines():
        if l.strip():
            c = json.loads(l)
            if "rows" in c and "aborted" not in c:
                out[(c["cell_spec"]["arm"], c["cell_spec"]["fanout"])] = c
    return out


def main():
    ap = argparse.ArgumentParser()
    for k in ("x1", "x2", "x3", "x4"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    L = ["| condizione | R (s) | braccio | episodi | esclusi | quota in ritardo [IC 95 %] | previsione | immagine |", "|---|---|---|---|---|---|---|---|"]
    m = {}
    for x, d in zip(("X1", "X2", "X3", "X4"), (a.x1, a.x2, a.x3, a.x4)):
        cells, R, row = _rows(d), XR[x], {}
        for arm in ("D", "C"):
            c = cells[(arm, 10)]
            s, lo, hi = late_share(c["rows"], R, arm)
            row[arm] = s
            shas = {v[:8] for v in (c.get("image_service_sha256") or {}).values()}
            L.append(f"| {x} | {R:g} | {arm} | {len(c['rows'])} | {sum(1 for r in c['rows'] if r.get('excluded'))} | {s:.3f} [{lo:.3f}; {hi:.3f}] | " + (f"D {PRED[x]['D']}" if arm == "D" else f"v4 {PRED[x]['v4']}, v5 {PRED[x]['v5']}") + f" | {sorted(shas)} |")
        m[x] = row
    v = verdict(m)
    res = outcome(v)
    L += ["", "## Verdetti (criteri di audit 107)", "",
          f"- H-N0 (controllo D, ±0,04): {'regge' if v['h_n0'] else 'CADE in ' + ', '.join(v['uninterpretable'])}",
          f"- H-N1 (|C − v5| ≤ 0,05 in ogni condizione interpretabile): {'regge' if v['h_n1'] else 'CADE'}",
          f"- H-N2 (MAE v5 < MAE v4 e |ε5| ≤ 0,04): {'regge' if v['h_n2'] else 'CADE'} (MAE5 = {v.get('mae5')}, MAE4 = {v.get('mae4')}, ε5 = {v.get('eps5')}, ε4 = {v.get('eps4')})",
          f"- **Esito per il paper: {res}**"]
    t = "\n".join(L) + "\n"
    print(t)
    if a.out:
        Path(a.out).write_text(t)


if __name__ == "__main__":
    main()
