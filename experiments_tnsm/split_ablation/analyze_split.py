"""C_s-only / C_t-only ablation and split sweep on the three real labs (audit 53; hypotheses H-S1..H-S3 are there, committed before this code).
Usage (repo root): python3 experiments_tnsm/split_ablation/analyze_split.py --out experiments_tnsm/split_ablation/run_20261011
Real data are read IN PLACE (outside the repo); only per-receiver aggregates are written. Nothing is reported unless V0 reproduces the locked set."""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(ROOT / "code" / "scripts"))
sys.path.insert(0, str(ROOT / "experiments_tnsm" / "baseline_quorum_persistence"))

from moniotr_cross_lab import (  # noqa: E402
    ELIGIBLE, collapse_site_three, load, load_label_mapping, mean, per_device_metrics, set_metrics, sha256,
)
from dib.evaluation.intent_overlap import classify_core  # noqa: E402

DATA = Path("/root/Desktop/DIB/data/processed")
INPUTS = (DATA / "moniotr_full_observations.csv", DATA / "yourthings_observations.csv")
MAPPING = ROOT / "docs" / "label_mapping_v16.csv"
SPLITS = (0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def score_keys_variant(data, sites, *, w=0.7, alpha=0.6, beta=0.4, theta=0.65, m=2, gate=True):
    """Parametric copy of moniotr_cross_lab.score_keys (lines 324-372): C_t = min(1, w*d + (1 - w)*f); value = alpha*C_s + beta*C_t."""
    predicted = set()
    for key, supporters_all in data.endpoints.items():
        supporters = supporters_all & sites
        device, endpoint, protocol, port = key
        eligible = data.device_sites[device] & sites
        if not supporters or not eligible:
            continue
        site_conf = len(supporters) / len(eligible)
        endpoint_days = {day for site in sites for day in data.site_endpoint_days[(site, key)]}
        device_days = {day for site in sites for day in data.site_device_days[(site, device)]}
        endpoint_count = sum(data.site_endpoint_date_counts[(site, key, day)] for site in sites for day in data.site_endpoint_days[(site, key)])
        device_count = sum(data.site_device_date_counts[(site, device, day)] for site in sites for day in data.site_device_days[(site, device)])
        active_day_ratio = len(endpoint_days) / max(len(device_days), 1)
        frequency_ratio = endpoint_count / max(device_count, 1)
        temporal = min(1.0, w * active_day_ratio + (1 - w) * frequency_ratio)
        value = alpha * site_conf + beta * temporal
        portable = classify_core(endpoint, protocol, port) in ELIGIBLE
        if value >= theta and (not gate or portable) and len(supporters) >= m:
            predicted.add(key)
    return predicted


def quorum_class_set(data, sources):
    """{keys with >= 2 supporters among the sources and an eligible class}, computed without scores."""
    return {k for k, rep in data.endpoints.items() if len(rep & sources) >= 2 and classify_core(k[1], k[2], k[3]) in ELIGIBLE}


VARIANTS = {"V0": {}, **{f"w{w}": {"w": w} for w in SPLITS if w != 0.7}, "Cs-only": {"alpha": 1.0, "beta": 0.0}, "Ct-only": {"alpha": 0.0, "beta": 1.0}}


def run():
    sites = ("US", "UK", "YT")
    data = load(INPUTS[0], extra_paths=list(INPUTS[1:]), collapse_fn=collapse_site_three, label_map=load_label_mapping(MAPPING))
    out = []
    for receiver in sites:
        sources = set(sites) - {receiver}
        devices, locked, _ = per_device_metrics(data, sites, receiver)
        assert len(devices) == 6
        sets = {name: {k for k in score_keys_variant(data, sources, **kw) if k[0] in devices} for name, kw in VARIANTS.items()}
        assert sets["V0"] == locked, f"V0 does not reproduce the locked set at {receiver}"           # validity condition of audit 53
        qc = {k for k in quorum_class_set(data, sources) if k[0] in devices}

        def metrics(cands):
            ms = [set_metrics({k for k in cands if k[0] == d}, data.profiles[receiver][d]) for d in devices]
            return dict(candidates=len(cands), coverage=sum(any(k[0] == d for k in cands) for d in devices) / 6,
                        precision=mean(ms, "precision"), recall=mean(ms, "recall"), f1=mean(ms, "f1"))
        rec = {"receiver": receiver, "variants": {n: metrics(s) for n, s in sets.items()},
               "symdiff_with_V0": {n: len(s ^ sets["V0"]) for n, s in sets.items() if n != "V0"},
               "H-S1_sets_equal_to_V0": {n: sets[n] == sets["V0"] for n in ("w0.6", "w0.8", "w0.9")},
               "H-S2_Cs_only_equals_quorum_class": sets["Cs-only"] == qc, "quorum_class_candidates": len(qc),
               "H-S3_Ct_only_subset_of_V0": sets["Ct-only"] <= sets["V0"]}
        out.append(rec)
    verdicts = {"H-S1": "falsified" if any(not v for r in out for v in r["H-S1_sets_equal_to_V0"].values()) else "not falsified",
                "H-S2": "falsified" if any(not r["H-S2_Cs_only_equals_quorum_class"] for r in out) else "not falsified",
                "H-S3": "falsified" if any(not r["H-S3_Ct_only_subset_of_V0"] for r in out) else "not falsified"}
    return out, verdicts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res, verdicts = run()
    (out / "aggregates.json").write_text(json.dumps({"receivers": res, "verdicts": verdicts}, indent=1))
    files = [Path(__file__), MAPPING, *INPUTS, ROOT / "code/scripts/moniotr_cross_lab.py"]
    (out / "manifest.json").write_text(json.dumps({"argv": sys.argv, "python": sys.version, "platform": platform.platform(),
                                                   "audit": "docs/audit/53_prereg_split_ablation.md", "sha256": {str(f): sha256(f) for f in files}}, indent=1))
    print(json.dumps(verdicts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
