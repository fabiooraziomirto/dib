"""Passo 1: bounded A2 in raw breadth with explicit adversary counts k.

Derived from (copy kept unmodified in analysis_fs/orig/):
  /root/Desktop/DIB/reports/item1_private_ip_filter/poisoning_multiseed_full_coverage.py
  sha256 824d6b92459aa63a7ffbd4d8a0c3996d38856ac40be5dfccfcf50fe314f4b2d7
Input (default, same as the original):
  /root/Desktop/DIB/data/processed/observations_enriched_item1fixed.csv
  sha256 4de5423cec2d15bb76d1ab569b865bd46bf2082b5af89d010772d872c55ac8ed

Changes against the original, all deliberate:
  * trust_weighted=False (raw breadth, the quantity Criterion 1 bounds);
  * theta=0.65, min_reporting_sites=2, success = DIBScorer's own `accepted`
    (admit_auto, dib.py:45-47: quorum, eligibility, score >= theta), not
    `max_score > theta` with theta=0 and default m=1 (original :59-60, :86-90);
  * adversaries: explicit k in 0..5, drawn per device type from that type's
    ES_d (sites with >=1 row of the type), not int(round(10*f)) over all ten
    sites (poisoning.py:23-25); k_d = min(k, |ES_d|);
  * no device type is excluded: types with |ES_d| < 10 are reported in a
    separate summary with their effective share k_d/|ES_d|.
Unchanged: 10 pseudo-sites, partition_observations(strategy="random", seed),
seeds 0-19, single-shot fabrication (one copy of the site's first template
row per malicious (site, device), timestamp +1 s, fqdn evil-c2.net, https/443).

Hypotheses (stated before running):
  H-A2.1 k=0 injects nothing (no fake key is scored).
  H-A2.2 For full-coverage types (|ES_d| = 10), C_s = k/10 exactly and no
         admission for k <= 4 (sup 0.64 < 0.65).
  H-A2.3 Single-shot fabrication gives tiny C_t, so k=5 (sup 0.70) is still
         rejected: admission at k=5 needs persistence/flood (Passo 2).
  H-A2.4 Raw-breadth scores at k=3 / k=5 are close to, but not equal to, the
         paper's trust-weighted 0.321/0.490 (means) and 0.354/0.534 (maxima).
  H-A2.5 NetatmoWeatherStation (|ES_d| = 2) is admitted whenever k >= 2 (C_s = 1),
         the case the original script excluded.
"""
from __future__ import annotations

import argparse
import csv
import multiprocessing
import random
import statistics
import time
from collections import defaultdict
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from dib.core.io import read_observations_csv
from dib.core.models import Observation
from dib.evaluation.dib import DIBScorer, ScoringConfig
from dib.simulator.sites import partition_observations

FAKE = "evil-c2.net"
OUT = Path(__file__).resolve().parent / "out"
CONFIG = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2,
                       graph_enabled=False, trust_weighted=False)


def es_by_device(observations: list[Observation]) -> dict[str, list[str]]:
    es: dict[str, set[str]] = defaultdict(set)
    for o in observations:
        if o.fqdn or o.remote_ip:
            es[o.device_type].add(o.site_id)
    return {d: sorted(s) for d, s in es.items()}


def inject_k_from_es(observations: list[Observation], k: int, seed: int) -> tuple[list[Observation], dict[str, list[str]]]:
    """Per device type, pick min(k, |ES_d|) malicious sites uniformly from ES_d."""
    es = es_by_device(observations)
    template: dict[tuple[str, str], Observation] = {}
    for o in observations:
        template.setdefault((o.site_id, o.device_type), o)
    chosen: dict[str, list[str]] = {}
    fakes: list[Observation] = []
    for device in sorted(es):
        rng = random.Random(f"{seed}:{k}:{device}")
        sites = rng.sample(es[device], min(k, len(es[device]))) if k else []
        chosen[device] = sorted(sites)
        for site in sorted(sites):
            t = template[(site, device)]
            fakes.append(replace(t, fqdn=FAKE, remote_ip=None, protocol="https", port=443,
                                 timestamp=t.timestamp + timedelta(seconds=1),
                                 evidence_type="poisoned_endpoint"))
    return observations + fakes, chosen


def partition(observations, seed: int, site_count: int = 10) -> list[Observation]:
    sites = partition_observations(observations, site_count, strategy="random", seed=seed)
    return [o for s in sites for o in s.observations]


def run_trial(redistributed: list[Observation], seed: int, k: int) -> list[dict]:
    poisoned, chosen = inject_k_from_es(redistributed, k, seed)
    es = es_by_device(redistributed)
    scores = {s.device_type: s for s in DIBScorer(CONFIG).score(poisoned) if s.endpoint == FAKE}
    rows = []
    for device in sorted(es):
        s = scores.get(device)
        kd = len(chosen[device])
        rows.append({
            "seed": seed, "device_type": device, "k": k, "k_d": kd, "ES_d": len(es[device]),
            "share": round(kd / len(es[device]), 6),
            "site_confidence": round(s.site_confidence, 6) if s else 0.0,
            "temporal_confidence": round(s.temporal_confidence, 6) if s else 0.0,
            "max_score": round(s.score, 6) if s else 0.0,
            "max_score_quorum": round(s.score, 6) if s and s.supporting_sites >= 2 else 0.0,
            "supporting_sites": s.supporting_sites if s else 0,
            "admitted": bool(s and s.accepted), "trust_weighted": False,
        })
    return rows


def _worker(job) -> list[dict]:
    path, seeds, ks = job
    obs = list(read_observations_csv(path))
    rows: list[dict] = []
    for seed in seeds:
        redistributed = partition(obs, seed)
        for k in ks:
            rows += run_trial(redistributed, seed, k)
        print(f"seed {seed} done", flush=True)
    return rows


def summarise(rows: list[dict]) -> list[dict]:
    out = []
    for k in sorted({r["k"] for r in rows}):
        for scope, pred in (("full_coverage(ES_d=10)", lambda r: r["ES_d"] == 10),
                            ("low_coverage(ES_d<10)", lambda r: r["ES_d"] < 10)):
            sel = [r for r in rows if r["k"] == k and pred(r)]
            if not sel:
                continue
            per_seed = defaultdict(float)
            for r in sel:
                per_seed[r["seed"]] = max(per_seed[r["seed"]], r["max_score"])
            vals = list(per_seed.values())
            out.append({"k": k, "scope": scope, "seeds": len(vals),
                        "types": len({r["device_type"] for r in sel}),
                        "mean_of_per_seed_max": round(statistics.mean(vals), 4),
                        "sd_of_per_seed_max": round(statistics.pstdev(vals), 4),
                        "max_over_seeds": round(max(vals), 4),
                        "admissions(type x seed)": sum(r["admitted"] for r in sel),
                        "seeds_with_admission": len({r["seed"] for r in sel if r["admitted"]})})
    return out


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--observations", type=Path,
                   default=Path("/root/Desktop/DIB/data/processed/observations_enriched_item1fixed.csv"))
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--ks", type=int, nargs="+", default=[0, 1, 2, 3, 4, 5])
    p.add_argument("--workers", type=int, default=2)
    a = p.parse_args()
    OUT.mkdir(exist_ok=True)
    t0 = time.monotonic()
    jobs = [(a.observations, seeds, a.ks) for seeds in (list(range(a.seeds))[i::a.workers] for i in range(a.workers))]
    with multiprocessing.Pool(a.workers) as pool:
        rows = [r for part in pool.map(_worker, jobs) for r in part]
    rows.sort(key=lambda r: (r["seed"], r["k"], r["device_type"]))
    write(OUT / "a2_raw_k.csv", rows)
    summary = summarise(rows)
    write(OUT / "a2_raw_k_summary.csv", summary)
    low = [r for r in rows if r["ES_d"] < 10 and r["k"] > 0]
    write(OUT / "a2_raw_k_low_coverage.csv", low)
    for s in summary:
        print(s)
    print(f"total {time.monotonic() - t0:.0f}s")


if __name__ == "__main__":
    main()
