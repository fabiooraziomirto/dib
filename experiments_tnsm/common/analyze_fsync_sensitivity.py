#!/usr/bin/env python3
"""Sensitivity of M1/M2 (night 2026-10-10/11) to the initial fsync stall: order, trend, errors, and the registered verdicts recomputed without the cells
closest to the stall. Definitions committed BEFORE any computation in docs/audit/39_sensibilita_fsync_m1_m2.md (c3e3777); tests: test_analyze_fsync_sensitivity.py.
The registered verdicts (audit 38) are NOT replaced: this only reports whether they change. Usage: python3 analyze_fsync_sensitivity.py [--out file]"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import analyze_m1_arms as am

HERE = Path(__file__).resolve().parents[1]
M1 = HERE / "m1_single_node" / "night_20261011"
M2 = HERE / "m2_p99_tail" / "night_20261011"
ET_SECONDS = 600.0


def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(list(x)), ranks(list(y))
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    sx = sum((a - mx) ** 2 for a in rx)
    sy = sum((b - my) ** 2 for b in ry)
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy) ** 0.5


def excluded(cells, name, started_unix):
    if name == "ET":
        return [c for c in cells if c["t_start_unix"] - started_unix < ET_SECONDS]
    k = {"E5": 5, "E10": 10, "E20": 20}[name]
    return sorted(cells, key=lambda c: c["cell"])[:k]


def group_trend(cells, min_cells=8, early=10):
    groups = defaultdict(list)
    for c in cells:
        groups[(c["mode"], c["n_workers"])].append(c)
    rows = []
    for (arm, n), cs in sorted(groups.items()):
        if len(cs) < min_cells:
            continue
        pos = [c["cell"] for c in cs]
        thr = [c["result"]["throughput"] for c in cs]
        errs = [c["result"].get("unexpected_errors") for c in cs]
        rho_e = None if any(e is None for e in errs) else spearman(pos, errs)
        e_early = [c["result"]["throughput"] for c in cs if c["cell"] < early]
        e_rest = [c["result"]["throughput"] for c in cs if c["cell"] >= early]
        rows.append({"arm": arm, "n_workers": n, "cells": len(cs), "mean_position": statistics.fmean(pos), "rho_throughput": spearman(pos, thr), "rho_errors": rho_e,
                     "early_n": len(e_early), "rest_n": len(e_rest), "early_mean": statistics.fmean(e_early) if e_early else None,
                     "rest_mean": statistics.fmean(e_rest) if e_rest else None})
    return rows


def errors_by_arm(cells, early=10):
    out = {}
    for c in cells:
        a = out.setdefault(c["mode"], {"early_with_errors": 0, "early_cells": 0, "rest_with_errors": 0, "rest_cells": 0, "positions_with_errors": []})
        bad = c["result"]["unexpected_errors"] > 0
        k = "early" if c["cell"] < early else "rest"
        a[f"{k}_cells"] += 1
        a[f"{k}_with_errors"] += int(bad)
        if bad:
            a["positions_with_errors"].append(c["cell"])
    for a in out.values():
        a["positions_with_errors"].sort()
    return out


def compare_verdicts(cells, name, started_unix, seed=20261010, resamples=10_000):
    drop = {c["cell"] for c in excluded(cells, name, started_unix)}
    rest = [c for c in cells if c["cell"] not in drop]
    reg = {(v["id"], v["arm"], v["subset"]): v["falsified"] for v in am.verdicts(cells, seed, resamples)}
    exc = {(v["id"], v["arm"], v["subset"]): v["falsified"] for v in am.verdicts(rest, seed, resamples)} if rest else {}
    out = []
    for key in sorted(reg):
        e = exc.get(key)
        out.append({"id": key[0], "arm": key[1], "subset": key[2], "registered": reg[key], "excluded_set": e, "changed": e != reg[key], "cells_left": len(rest)})
    return out


def _w(v):
    return {True: "FALSIFIED", False: "not falsified", None: "not evaluable"}[v]


def _f(x, d=3):
    return "n/a" if x is None else f"{x:.{d}f}"


def render(m1, m2, started1, started2, seed, resamples):
    L = ["# Sensitivity of M1/M2 to the initial fsync stall (definitions: docs/audit/39, c3e3777)", "",
         "## M1, order: first 20 cells (position: arm, writers, rep, throughput ops/s, unexpected errors)"]
    for c in sorted(m1, key=lambda c: c["cell"])[:20]:
        L.append(f"- {c['cell']}: {c['mode']}, {c['n_workers']}, rep {c['rep']}, {c['result']['throughput']:.1f}, {c['result']['unexpected_errors']}")
    L += ["", "## M1, trend per group (cells >= 8): Spearman of position with throughput / unexpected errors; throughput of cells at positions < 10 against the rest", "",
          "| arm | writers | cells | mean position | rho(position, throughput) | rho(position, errors) | early n / mean | rest n / mean |", "|---|---|---|---|---|---|---|---|"]
    for r in group_trend(m1):
        L.append(f"| {r['arm']} | {r['n_workers']} | {r['cells']} | {r['mean_position']:.1f} | {_f(r['rho_throughput'])} | {_f(r['rho_errors'])} | {r['early_n']} / {_f(r['early_mean'], 1)} | {r['rest_n']} / {_f(r['rest_mean'], 1)} |")
    L += ["", "## M1, errors by arm: cells with unexpected errors among the first 10 cells and the rest; positions of all cells with errors", ""]
    for arm, a in sorted(errors_by_arm(m1).items()):
        L.append(f"- {arm}: first 10 cells {a['early_with_errors']}/{a['early_cells']} with errors; rest {a['rest_with_errors']}/{a['rest_cells']}; positions with errors: {a['positions_with_errors']}")
    L += ["", "## M1, registered verdicts recomputed without the excluded cells (same criteria, seed and resamples as audit 38)"]
    for name in ("E5", "E10", "E20", "ET"):
        cmp = compare_verdicts(m1, name, started1, seed, resamples)
        L += ["", f"### {name}: {len(excluded(m1, name, started1))} cells excluded, {cmp[0]['cells_left'] if cmp else 0} left", "", "| hypothesis | arm | subset | registered | without the set | changes |", "|---|---|---|---|---|---|"]
        for v in cmp:
            L.append(f"| {v['id']} | {v['arm']} | {v['subset']} | {_w(v['registered'])} | {_w(v['excluded_set'])} | {'CHANGES' if v['changed'] else 'unchanged'} |")
    L += ["", "## M2 (control: no stall before M2), trend per group (cells >= 8): Spearman of position with throughput; throughput at positions < 10 against the rest", "",
          "| mode | writers | cells | mean position | rho(position, throughput) | early n / mean | rest n / mean |", "|---|---|---|---|---|---|---|"]
    for r in group_trend(m2):
        L.append(f"| {r['arm']} | {r['n_workers']} | {r['cells']} | {r['mean_position']:.1f} | {_f(r['rho_throughput'])} | {r['early_n']} / {_f(r['early_mean'], 1)} | {r['rest_n']} / {_f(r['rest_mean'], 1)} |")
    return "\n".join(L) + "\n"


def _started(manifest_dir):
    m = json.loads((manifest_dir / "manifest.json").read_text())
    return datetime.fromisoformat(m["started_utc"]).timestamp()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    m1 = [json.loads(line) for line in (M1 / "cells.jsonl").open()]
    m2 = [json.loads(line) for line in (M2 / "cells.jsonl").open()]
    text = render(m1, m2, _started(M1), _started(M2), 20261010, 10_000)
    if a.out:
        Path(a.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
