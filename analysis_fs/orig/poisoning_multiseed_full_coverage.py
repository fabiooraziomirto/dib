"""Re-run of scripts/poisoning_multiseed.py's core loop, modified to exclude
devices that are not observed at every simulated site (eligible_sites <
site_count) from the max-fake-endpoint-score-across-devices measurement.

Methodology note (declared explicitly, not silent): under the Item-1
private-IP-filter fix, one device (NetatmoWeatherStation) collapses from
17,219 to 2 raw observations (2 of 10 simulated sites), and another
(BlipCareBPMeter) to 4 of 10 sites. Lemma 1's bound assumes the malicious
fraction f is measured over the ELIGIBLE site population for that specific
device; scripts/poisoning_multiseed.py's inject_fake_endpoint selects
malicious sites uniformly over all site_count sites, which only guarantees
the nominal global f equals the per-device f when every device is present
at every site. For a device present at only 2 of 10 sites, a uniform
3-of-10 malicious draw can (and empirically does, in 3/20 seeds at
f=0.30) put both of that device's 2 eligible sites in the malicious set,
giving that device an effective per-device f of 1.0 rather than the
nominal 0.30 -- breaking the bound's applicability for that device, not
the bound's algebra itself. This script excludes devices with
eligible_sites < site_count from the cross-device max, keeping the
methodology's original per-device max-across-devices structure for the
26 of 28 devices where the nominal f is actually realized.

Does not modify scripts/poisoning_multiseed.py itself -- this is a
separate, explicitly-labelled variant.
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace as dataclass_replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dib.core.io import read_observations_csv
from dib.evaluation.dib import DIBScorer, ScoringConfig
from dib.evaluation.trust import calibrate_reference_breadth
from dib.experiments.poisoning import inject_fake_endpoint
from dib.simulator.sites import partition_observations

FAKE_FQDN = "evil-c2.net"


def run_trial(observations, seed, fraction, site_count, partition_strategy, dib_config, theta):
    sites = partition_observations(observations, site_count, strategy=partition_strategy, seed=seed)
    redistributed = [obs for site in sites for obs in site.observations]
    poisoned = inject_fake_endpoint(redistributed, fraction, seed=seed)

    trial_config = dib_config
    if dib_config.trust_weighted:
        trial_config = dataclass_replace(
            dib_config, trust_reference_breadth=calibrate_reference_breadth(redistributed)
        )
    scores = DIBScorer(trial_config).score(poisoned)
    fake_scores = [s for s in scores if s.endpoint == FAKE_FQDN]
    full_coverage_scores = [s for s in fake_scores if s.eligible_sites == site_count]
    excluded = [(s.device_type, s.eligible_sites, round(s.score, 6)) for s in fake_scores if s.eligible_sites != site_count]
    max_score = max((s.score for s in full_coverage_scores), default=0.0)
    accepted = max_score > theta
    return {
        "seed": seed,
        "fraction": fraction,
        "fake_endpoint_score": round(max_score, 6),
        "poisoning_succeeded": int(accepted),
        "excluded_devices": ";".join(f"{dt}(elig={e},score={sc})" for dt, e, sc in excluded),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", default="data/processed/observations_enriched_item1fixed.csv")
    parser.add_argument("--site-count", type=int, default=10)
    parser.add_argument("--partition-strategy", default="random")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--fractions", type=float, nargs="+", required=True)
    parser.add_argument("--theta", type=float, default=0.65)
    parser.add_argument("--alpha", type=float, required=True)
    parser.add_argument("--beta", type=float, required=True)
    parser.add_argument("--gamma", type=float, required=True)
    parser.add_argument("--graph-enabled", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--trust-weighted", action="store_true", default=False)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    observations = read_observations_csv(Path(args.observations))
    dib_config = ScoringConfig(
        alpha=args.alpha, beta=args.beta, gamma=args.gamma, theta=0.0,
        graph_enabled=args.graph_enabled, trust_weighted=args.trust_weighted,
    )

    rows = []
    for seed in range(args.seeds):
        for fraction in args.fractions:
            row = run_trial(observations, seed, fraction, args.site_count, args.partition_strategy, dib_config, args.theta)
            rows.append(row)
            print(f"seed={seed} fraction={fraction} score={row['fake_endpoint_score']:.6f} "
                  f"excluded=[{row['excluded_devices']}]", flush=True)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["seed", "fraction", "fake_endpoint_score", "poisoning_succeeded", "excluded_devices"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    raise SystemExit(main())
