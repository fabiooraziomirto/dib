#!/usr/bin/env python3
"""M1 verdicts per arm (default / deploy) and the pool-checkout censoring report, applying VERBATIM the criteria registered in
experiments_tnsm/m1_single_node/run.py:12-30 (committed c23d1e3 / a90b27a before the night run; pre-registration in docs/audit/37_prereg_m1_m2.md).
Needed because analyze.py looks for mode == 'threads' in M1 while the night cells carry mode = arm, so its built-in H-M1 verdict does not fire and
H-M1b / H-M1c are not implemented there. CIs use the same seed scheme as analyze.py (Random(f"{seed}-{mode}-{n}-{subset}-{metric}"), 95% percentile
bootstrap over CELLS, 10,000 resamples), so they coincide with summary.csv. Tests: test_analyze_m1_arms.py (synthetic).
Usage: python3 analyze_m1_arms.py <dir with cells.jsonl> [--seed 20261010 --resamples 10000]"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import analyze as an


def _ci(cells, mode, n, subset, metric, seed, resamples):
    cs = [c for c in cells if c["mode"] == mode and c["n_workers"] == n and (subset == "all" or not c["disturbed"])]
    vals = [an.m1_values(c)[metric] for c in cs]
    rng = random.Random(f"{seed}-{mode}-{n}-{subset}-{metric}")
    return an.boot_ci(vals, resamples, rng), len(cs)


def verdicts(cells, seed=20261010, resamples=10_000):
    out = []
    arms = sorted({c["mode"] for c in cells})
    for subset in ("all", "filtered"):
        for arm in arms:                                              # H-M1, tested separately in each arm
            (m50, lo50, hi50), n50 = _ci(cells, arm, 50, subset, "throughput", seed, resamples)
            (m100, lo100, hi100), n100 = _ci(cells, arm, 100, subset, "throughput", seed, resamples)
            fals = None if (m50 is None or m100 is None) else lo100 > hi50
            out.append({"id": "H-M1", "arm": arm, "subset": subset, "cells_used": n50 + n100, "ci50": (m50, lo50, hi50), "ci100": (m100, lo100, hi100), "falsified": fals})
        if "deploy" in arms:                                          # H-M1b: no deploy cell with unexpected errors at any writer count
            ds = [c for c in cells if c["mode"] == "deploy" and (subset == "all" or not c["disturbed"])]
            bad = sum(1 for c in ds if c["result"]["unexpected_errors"] > 0)
            out.append({"id": "H-M1b", "arm": "deploy", "subset": subset, "cells_used": len(ds), "cells_with_errors": bad, "falsified": bad > 0})
        if "deploy" in arms and "default" in arms:                    # H-M1c: at 100 writers deploy completed-ops throughput not below default
            (dm, dlo, dhi), nd = _ci(cells, "deploy", 100, subset, "throughput_completed", seed, resamples)
            (fm, flo, fhi), nf = _ci(cells, "default", 100, subset, "throughput_completed", seed, resamples)
            fals = None if (dm is None or fm is None) else dhi < flo
            out.append({"id": "H-M1c", "arm": "deploy vs default", "subset": subset, "cells_used": nd + nf, "ci_deploy": (dm, dlo, dhi), "ci_default": (fm, flo, fhi), "falsified": fals})
    return out


def censoring_report(cells):
    rep = {}
    for c in cells:
        r = rep.setdefault((c["mode"], c["n_workers"]), {"arm": c["mode"], "n_workers": c["n_workers"], "cells": 0, "censored": 0, "with_errors": 0})
        v = an.m1_values(c)
        r["cells"] += 1
        r["censored"] += int(v["_censored"])
        r["with_errors"] += int(c["result"]["unexpected_errors"] > 0)
    for r in rep.values():
        r["p99_uncensored_cells"] = r["cells"] - r["censored"]
    return [rep[k] for k in sorted(rep)]


def _f(t, d=1):
    return "n/a" if t is None or t[0] is None else f"{t[0]:.{d}f} [{t[1]:.{d}f}, {t[2]:.{d}f}]"


def render(cells, seed, resamples):
    L = ["# M1 per-arm verdicts (criteria of m1_single_node/run.py:12-30, verbatim)", ""]
    for v in verdicts(cells, seed, resamples):
        verdict = "not evaluable" if v["falsified"] is None else ("FALSIFIED" if v["falsified"] else "not falsified")
        if v["id"] == "H-M1":
            L.append(f"- {v['id']} [{v['arm']}, {v['subset']}, cells {v['cells_used']}]: throughput (all ops) at 50 = {_f(v['ci50'])}, at 100 = {_f(v['ci100'])} ops/s -> {verdict} (falsified iff CI100 lower > CI50 upper)")
        elif v["id"] == "H-M1b":
            L.append(f"- {v['id']} [{v['subset']}, deploy cells {v['cells_used']}]: deploy cells with unexpected errors = {v['cells_with_errors']} -> {verdict}")
        else:
            L.append(f"- {v['id']} [{v['subset']}, cells {v['cells_used']}]: completed-ops throughput at 100: deploy {_f(v['ci_deploy'])} vs default {_f(v['ci_default'])} ops/s -> {verdict} (falsified iff deploy CI upper < default CI lower)")
    L += ["", "# Pool-checkout censoring, reported separately (p99 >= 29.9 s with unexpected errors = ceiling of the 30 s checkout timeout, not a latency)", "",
          "| arm | writers | cells | censored (p99 at the ceiling) | cells with unexpected errors | cells with a usable p99 |", "|---|---|---|---|---|---|"]
    L += [f"| {r['arm']} | {r['n_workers']} | {r['cells']} | {r['censored']} | {r['with_errors']} | {r['p99_uncensored_cells']} |" for r in censoring_report(cells)]
    return "\n".join(L) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("dir", type=Path)
    p.add_argument("--seed", type=int, default=20261010)
    p.add_argument("--resamples", type=int, default=10_000)
    a = p.parse_args()
    cells = [json.loads(line) for line in (a.dir / "cells.jsonl").open()]
    text = render(cells, a.seed, a.resamples)
    (a.dir / "verdicts_by_arm.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
