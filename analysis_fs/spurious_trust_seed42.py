"""Punto A, follow-up: under trust weighting the 8 rows change site breadth
(spurious_dates_checks.csv: breadth changes at 19/21 seeds, the reference
breadth at 8/21), so types other than the three affected ones can move. This
script scores the WHOLE population before/after at seed 42 (the seed of the
paper's "346 facts", paper:530) with graph_free_selected (trust, m=2).

Run: PYTHONPATH=code/src python3 analysis_fs/spurious_trust_seed42.py   (~2 min)
Hypothesis (stated before running): the admitted set changes by 0 facts; at
most a few scores of other types move by < 1e-3. The other 20 seeds are not
re-scored here (time budget); they remain to be computed.
"""
from __future__ import annotations

import csv
from pathlib import Path

from dib.core.io import filter_observations, read_observations_csv
from dib.evaluation.dib import DIBScorer
from dib.evaluation.trust import calibrate_reference_breadth
from dib.simulator.sites import partition_observations

from spurious_dates import ENRICHED, OUT, is_spurious, trust_config


def main() -> None:
    obs = list(filter_observations(read_observations_csv(ENRICHED), exclude_non_global_ips=True))
    sites = partition_observations(obs, 10, strategy="random", seed=42)
    before = [o for s in sites for o in s.observations if o.fqdn or o.remote_ip]
    after = [o for o in before if not is_spurious(o)]
    sb = {s.endpoint_key: s for s in DIBScorer(trust_config(calibrate_reference_breadth(before))).score(before)}
    sa = {s.endpoint_key: s for s in DIBScorer(trust_config(calibrate_reference_breadth(after))).score(after)}
    adm_b = {k for k, s in sb.items() if s.accepted}
    adm_a = {k for k, s in sa.items() if s.accepted}
    affected = {o.device_type for o in before if is_spurious(o)}
    other = [k for k in sb if k in sa and k[0] not in affected]
    moved = [k for k in other if abs(sb[k].score - sa[k].score) > 1e-12]
    row = {"seed": 42, "config": "graph_free_selected(trust)", "admitted_before": len(adm_b), "admitted_after": len(adm_a),
           "newly_admitted": len(adm_a - adm_b), "newly_rejected": len(adm_b - adm_a),
           "other_type_keys": len(other), "other_type_keys_moved": len(moved),
           "max_abs_delta_other_types": max((abs(sb[k].score - sa[k].score) for k in moved), default=0.0)}
    with (OUT / "spurious_dates_trust_seed42.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader()
        w.writerow(row)
    print(row)


if __name__ == "__main__":
    main()
