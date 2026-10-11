"""Secondary analysis of 5.3b, POST-HOC (audit 41 s.1-s.3): set comparison and paired bootstrap of H-B2.

(a) per receiver, counts only: |C_DIB|, |C_B(2, tau_match)|, |intersection|, |symmetric difference|; tau_match is
    READ from the confirmatory run (run_20261012/real/aggregates.json) and the code asserts that recomputing it with
    analyze_baseline.tau_match gives the same value and the same candidate count.
(b) audit 41 s.2: d = recall_dev(B(2, tau_match)) - recall_dev(DIB) per (receiver, device); units with an empty
    reference excluded; paired bootstrap, percentile 95%, B = 10 000, seed 20261012 (pooled and each receiver, each with
    its own random.Random(seed)); with n < 10 the interval is descriptive and no verdict is formed.
(c) per-device values are written OUTSIDE the repo (--private-dir, sha256 recorded in the manifest); the repo
    receives only counts, intervals, n and verdicts (--out).

Usage (repo root):
  python3 experiments_tnsm/baseline_quorum_persistence/analyze_secondary.py \
      --confirmatory experiments_tnsm/baseline_quorum_persistence/run_20261012/real/aggregates.json \
      --private-dir <dir outside the repo> --out experiments_tnsm/baseline_quorum_persistence/run_secondary
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import sys
from math import fsum
from pathlib import Path

SEED = 20261012
B = 10000
LO_IDX = 250            # int(0.025 * B)
HI_IDX = 9749           # int(0.975 * B) - 1
MIN_N = 10
DEGENERATE = "non falsificata; nessuna differenza osservata, nessun potere"
HERE = Path(__file__).resolve().parent


def delta_counts(c_dib, c_base):
    return {"dib": len(c_dib), "base": len(c_base), "inter": len(c_dib & c_base), "symdiff": len(c_dib ^ c_base)}


def unit_differences(units):
    """units: (device, n_reference, recall_dib, recall_base). d = base - dib; empty reference excluded."""
    return [rb - rd for _, n_ref, rd, rb in units if n_ref > 0]


def paired_bootstrap(diffs, B=B, seed=SEED):
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(fsum(rng.choices(diffs, k=n)) / n for _ in range(B))
    return means[int(0.025 * B)], means[int(0.975 * B) - 1]


def secondary_verdict(diffs, lo, hi):
    if len(diffs) < MIN_N:
        return "descrittivo (n < 10): nessun verdetto"
    if all(d == 0 for d in diffs):
        return DEGENERATE
    return "falsificata" if lo > 0 else "non falsificata"


def run(confirmatory, private_dir, out):
    sys.path.insert(0, str(HERE))
    import analyze_baseline as ab
    from moniotr_cross_lab import collapse_site_three, load, load_label_mapping, per_device_metrics, set_metrics, sha256

    agg = json.loads(Path(confirmatory).read_text())
    data = load(ab.INPUTS[0], extra_paths=list(ab.INPUTS[1:]), collapse_fn=collapse_site_three,
                label_map=load_label_mapping(ab.MAPPING))
    sites = ("US", "UK", "YT")
    private_rows, repo = [], {"receivers": {}}
    all_diffs = []
    for rec in agg["real"]:
        r = rec["receiver"]
        sources = set(sites) - {r}
        devices, locked, _ = per_device_metrics(data, sites, r)
        table = ab.key_table(data, sources, devices)
        tau_c = rec["tau_match"]
        tau_now, n_now = ab.tau_match(table, 2, len(locked))
        assert tau_now == tau_c and n_now == rec["baseline"]["m2_tau_match"]["candidates"], (r, tau_now, tau_c)
        c_b = ab.select(table, 2, tau_c)
        assert len(locked) == rec["stages"]["DIB"]["candidates"] and len(c_b) == n_now
        units = []
        for dev in devices:
            obs = data.profiles[r][dev]
            rd = set_metrics({k for k in locked if k[0] == dev}, obs)["recall"]
            rb = set_metrics({k for k in c_b if k[0] == dev}, obs)["recall"]
            units.append((dev, len(obs), rd, rb))
            private_rows.append(dict(receiver=r, device=dev, n_reference=len(obs), recall_dib=rd, recall_base=rb,
                                     d=rb - rd))
        d = unit_differences(units)
        lo, hi = paired_bootstrap(d) if d else (None, None)
        repo["receivers"][r] = {"tau_match": tau_c, "sets": delta_counts(locked, c_b), "n_units": len(d),
                                "units_d_nonzero": sum(x != 0 for x in d), "mean_d": fsum(d) / len(d) if d else None,
                                "ci95": [lo, hi], "verdict": secondary_verdict(d, lo, hi) if d else "n = 0"}
        all_diffs += d
    lo, hi = paired_bootstrap(all_diffs)
    repo["pooled"] = {"n_units": len(all_diffs), "units_d_nonzero": sum(x != 0 for x in all_diffs),
                      "mean_d": fsum(all_diffs) / len(all_diffs), "ci95": [lo, hi],
                      "verdict": secondary_verdict(all_diffs, lo, hi)}
    private = Path(private_dir)
    private.mkdir(parents=True, exist_ok=True)
    pf = private / "per_device_53b.csv"
    with pf.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(private_rows[0]))
        w.writeheader()
        w.writerows(private_rows)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "secondary.json").write_text(json.dumps(repo, indent=1))
    files = [Path(__file__), HERE / "analyze_baseline.py", Path(confirmatory), ab.MAPPING, *ab.INPUTS]
    (out / "manifest.json").write_text(json.dumps({
        "argv": sys.argv, "seed": SEED, "B": B, "python": sys.version, "platform": platform.platform(),
        "label": "POST-HOC (audit 41 s.1)", "private_file": str(pf), "private_file_sha256": sha256(pf),
        "sha256": {str(f): sha256(f) for f in files}}, indent=1))
    print(json.dumps(repo, indent=1))
    return repo


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--confirmatory", required=True)
    p.add_argument("--private-dir", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    run(a.confirmatory, a.private_dir, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
