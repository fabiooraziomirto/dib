#!/usr/bin/env python3
"""Verdicts H-N1/H-N2 of audit 85 on a full-deployment run (run.py b1 output dir). Usage: python3 analyze_deploy.py <dir with b1/cells.jsonl> [--out report.md]"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

B5 = {"D10": 0.178, "C10": 0.310}                  # audit 83 (retrospective computation on the B5 data)
PRED = {"D10": 0.179, "C10": 0.251, "D1": 10600.0, "C1": 16400.0}
NOMINAL = {"D": 0.6, "C": 1.0}


def per_site_late_share(rows: list, nominal: float):
    v = [x for r in rows if not r.get("excluded") for x in (r.get("withdrawn_plog_s") or {}).values() if x is not None]
    return sum(1 for x in v if x > nominal + 0.3) / len(v) if v else None


def verdicts(late: dict, f1: dict) -> dict:
    h1 = all(abs(late[k] - B5[k]) <= 0.04 for k in ("D10", "C10"))
    h2 = (abs(late["D10"] - PRED["D10"]) <= 0.04 and abs(late["C10"] - PRED["C10"]) <= 0.08
          and abs(f1["D1"] - PRED["D1"]) <= 0.25 * PRED["D1"] and abs(f1["C1"] - PRED["C1"]) <= 0.25 * PRED["C1"])
    return {"h_n1": h1, "h_n2": h2, "validated": h1 and h2}


def _cells(d: Path):
    out = {}
    for l in (d / "cells.jsonl").read_text().splitlines():
        if l.strip():
            c = json.loads(l)
            if "rows" in c and "aborted" not in c:
                out[(c["cell_spec"]["arm"], c["cell_spec"]["fanout"])] = c
    return out


def _last(rows):
    v = []
    for r in rows:
        if r.get("excluded") or not r.get("withdrawn_plog_s"):
            continue
        pend = any(n for n in (r.get("pending_after_response") or {}).values()) or any(n for n in (r.get("pending_left") or {}).values()) or any(t is not None for t in (r.get("plog_ack_ts") or {}).values())
        x = [y for y in r["withdrawn_plog_s"].values() if y is not None]
        if not pend and len(x) == 10:
            v.append(1000 * max(x))
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cells = _cells(Path(a.run))
    L = ["# Distribuzione completa (11 container, mTLS, applicatore netem in user space): verdetti H-N1/H-N2 (audit 85)", "",
         "| arm | FANOUT | episodi | esclusi | quota in ritardo per sito (previsione v4) | mediana ultimo sito ms [n] (previsione v4) |", "|---|---|---|---|---|---|"]
    late, f1 = {}, {}
    for arm in ("D", "C"):
        for fo in (10, 1):
            c = cells.get((arm, fo))
            if not c:
                L.append(f"| {arm} | {fo} | assente | | | |")
                continue
            rows = c["rows"]
            lastv = _last(rows)
            med = statistics.median(lastv) if lastv else None
            ls = per_site_late_share(rows, NOMINAL[arm])
            if fo == 10:
                late[f"{arm}10"] = ls
            else:
                f1[f"{arm}1"] = med
            L.append(f"| {arm} | {fo} | {len(rows)} | {sum(1 for r in rows if r.get('excluded'))} | " + (f"{ls:.3f} ({PRED[f'{arm}10']:.3f})" if fo == 10 and ls is not None else "—") +
                     f" | {med:.0f} [{len(lastv)}] ({PRED[f'{arm}{fo}'] if fo == 1 else '—'}) |" if med else " | n/d |")
    if len(late) == 2 and len(f1) == 2 and all(v is not None for v in list(late.values()) + list(f1.values())):
        v = verdicts(late, f1)
        L += ["", "## Verdetti", "", f"- **H-N1 (applicatore equivalente a B5):** {'regge' if v['h_n1'] else 'NON regge'} (D/10 {late['D10']:.3f} contro 0,178; C/10 {late['C10']:.3f} contro 0,310; tolleranza ±0,04).",
              f"- **H-N2 (modello):** {'regge' if v['h_n2'] else 'NON regge'} (D/10 contro 0,179 ±0,04; C/10 contro 0,251 ±0,08; F1 D {f1['D1']:.0f} contro 10 600, C {f1['C1']:.0f} contro 16 400, ±25 %).",
              f"- **Modello v4 validato sulla distribuzione completa: {'SÌ' if v['validated'] else 'NO'}.**"]
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)


if __name__ == "__main__":
    main()
