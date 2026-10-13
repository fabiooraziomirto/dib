#!/usr/bin/env python3
"""Node T-0 of the mTLS gap (docs/audit/113): per-site late share and median shift of the apply time from the nominal in LOSSLESS profiles z1 (d 60 ms, R 0.12 s) and z3 (d 150 ms, R 0.30 s), arms D and C, FANOUT 10.
Usage: python3 analyze_lossless.py --z1 DIR --z3 DIR [--out report.md]   (DIR = run.py b1 output dir with cells.jsonl)"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

RS = {"z1": 0.12, "z3": 0.30}


def cell(rows, R, arm):
    nominal = (2.5 if arm == "C" else 1.5) * R
    vals, late, tot = [], 0, 0
    for r in rows:
        if r.get("excluded"):
            continue
        for x in (r.get("withdrawn_plog_s") or {}).values():
            if x is None:
                continue
            vals.append(x)
            tot += 1
            late += x > nominal + 0.75 * R
    return {"late_share": late / tot if tot else None, "median_shift_s": (statistics.median(vals) - nominal) if vals else None, "n_sites": tot}


def verdict_z(m):
    above = [k for k, v in sorted(m.items()) if v["late_share"] is not None and v["late_share"] > 0.02 + 1e-12]
    return {"h_z1": not above, "above": above}


def _cells(d):
    out = {}
    for l in (Path(d) / "cells.jsonl").read_text().splitlines():
        if l.strip():
            c = json.loads(l)
            if "rows" in c and "aborted" not in c:
                out[(c["cell_spec"]["arm"], c["cell_spec"]["fanout"])] = c
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--z1", required=True)
    ap.add_argument("--z3", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    L = ["| profilo | R (s) | braccio | episodi | esclusi | quota in ritardo | spostamento mediano rispetto al nominale (ms) | siti |", "|---|---|---|---|---|---|---|---|"]
    m = {}
    for z, d in (("z1", a.z1), ("z3", a.z3)):
        cells = _cells(d)
        for arm in ("D", "C"):
            c = cells[(arm, 10)]
            s = cell(c["rows"], RS[z], arm)
            m[(z, arm)] = s
            L.append(f"| {z} | {RS[z]:g} | {arm} | {len(c['rows'])} | {sum(1 for r in c['rows'] if r.get('excluded'))} | {s['late_share']:.3f} | {1000 * s['median_shift_s']:+.1f} | {s['n_sites']} |")
    v = verdict_z(m)
    L += ["", "## Verdetto (audit 113)", "", f"- H-Z1 (quota in ritardo ≤ 0,02 senza perdita in tutte le celle): {'regge' if v['h_z1'] else 'CADE in ' + ', '.join(f'{z}/{a_}' for z, a_ in v['above'])}"]
    t = "\n".join(L) + "\n"
    print(t)
    if a.out:
        Path(a.out).write_text(t)


if __name__ == "__main__":
    main()
