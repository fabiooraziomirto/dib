#!/usr/bin/env python3
"""H-R1b of audit 88: old-code run (audit 86) against the corrected-code rerun. Usage: python3 compare_deploy.py <old b1 dir> <new b1 dir> [--out report.md]"""
from __future__ import annotations

import argparse
import statistics
from pathlib import Path

import analyze_deploy as ad


def regression_verdict(old: dict, new: dict) -> dict:
    cells = [k for k in ("D10", "C10") if abs(new["late"][k] - old["late"][k]) > 0.04 + 1e-12]
    cells += [k for k in ("D1", "C1") if abs(new["med"][k] - old["med"][k]) > 0.15 * old["med"][k] + 1e-9]
    return {"regression": bool(cells), "cells": cells}


def metrics(d: Path) -> dict:
    cells = ad._cells(d)
    out = {"late": {}, "med": {}}
    for arm in ("D", "C"):
        out["late"][f"{arm}10"] = ad.per_site_late_share(cells[(arm, 10)]["rows"], ad.NOMINAL[arm])
        out["med"][f"{arm}1"] = statistics.median(ad._last(cells[(arm, 1)]["rows"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    o, n = metrics(Path(a.old)), metrics(Path(a.new))
    v = regression_verdict(o, n)
    L = ["| cella | vecchio | nuovo | differenza |", "|---|---|---|---|"]
    for k in ("D10", "C10"):
        L.append(f"| late share {k} | {o['late'][k]:.3f} | {n['late'][k]:.3f} | {n['late'][k]-o['late'][k]:+.3f} (soglia ±0,04) |")
    for k in ("D1", "C1"):
        L.append(f"| mediana ultimo sito {k} ms | {o['med'][k]:.0f} | {n['med'][k]:.0f} | {100*(n['med'][k]/o['med'][k]-1):+.1f} % (soglia ±15 %) |")
    L += ["", f"**H-R1b: {'FALSIFICATA, celle fuori soglia: ' + ', '.join(v['cells']) if v['regression'] else 'regge (nessuna regressione)'}.**"]
    t = "\n".join(L) + "\n"
    print(t)
    if a.out:
        Path(a.out).write_text(t)


if __name__ == "__main__":
    main()
