"""Punto B: two adversary-sampling models for the low-coverage types.

Run: PYTHONPATH=code/src python3 analysis_fs/netatmo_sampling.py   (~2 min)
Input: observations_enriched_item1fixed.csv (as a2_raw_k.py), 10 pseudo-sites,
partition_observations(random, seed), seeds 0-19, k = 1..5, single-shot
fabrication, raw breadth, m=2, theta=0.65.

Models:
  uniform  k malicious sites drawn uniformly among ALL ten sites, with the same
           RNG call as the original script (random.Random(seed).sample(sorted
           sites, k), poisoning.py:22-25); per type K_d = |malicious ∩ ES_d|
           ~ Hypergeom(10, k, |ES_d|).
  es_d     k malicious sites drawn inside ES_d (a2_raw_k.py): K_d = min(k, |ES_d|),
           deterministic.
Only NetatmoWeatherStation and BlipCareBPMeter are scored, restricted to their
own rows (exact under raw breadth and gamma=0, see worst_case_real.py).

Expected probability per (type, k): P(K_d >= 2 and K_d/|ES_d| > 5/12), i.e. the
fact is admissible in principle (quorum met, share above the analytical
limit), averaged over the 20 seeds' |ES_d| (BlipCare's |ES_d| varies 4-8).
Under single-shot fabrication admissibility is necessary, not sufficient, for
admission, so for BlipCare the observed admission rate can be lower.

Hypotheses (stated before running):
  N1 uniform, k=3: Netatmo covered (K_d = 2) exactly in seeds 1, 6, 13, as in
     the original run (same RNG call), so 3/20 against an expected 8/120 = 0.067;
  N2 es_d, k>=2: Netatmo admitted 20/20 (share 1.0), matching a2_raw_k;
  N3 Netatmo admitted iff K_d = 2 (score 0.94), never with K_d = 1 (quorum).
"""
from __future__ import annotations

import csv
import random
import statistics
from collections import defaultdict
from dataclasses import replace
from datetime import timedelta
from fractions import Fraction
from math import comb
from pathlib import Path

from dib.core.io import read_observations_csv
from dib.core.models import Observation
from dib.evaluation.dib import DIBScorer, ScoringConfig
from dib.simulator.sites import partition_observations

DATA = Path("/root/Desktop/DIB/data/processed/observations_enriched_item1fixed.csv")
OUT = Path(__file__).resolve().parent / "out"
TYPES = ("NetatmoWeatherStation", "BlipCareBPMeter")
FAKE = "evil-c2.net"
CONFIG = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2, graph_enabled=False)
LIM = Fraction(5, 12)


def admissible(kd: int, n: int) -> bool:
    return kd >= 2 and Fraction(kd, n) > LIM


def p_admissible_uniform(k: int, n: int, total: int = 10) -> Fraction:
    return sum((Fraction(comb(n, j) * comb(total - n, k - j), comb(total, k)) for j in range(0, min(k, n) + 1)
                if k - j <= total - n and admissible(j, n)), Fraction(0))


def inject(rows: list[Observation], device: str, sites: list[str]) -> list[Observation]:
    template: dict[str, Observation] = {}
    for o in rows:
        if o.device_type == device:
            template.setdefault(o.site_id, o)
    fakes = [replace(template[s], fqdn=FAKE, remote_ip=None, protocol="https", port=443,
                     timestamp=template[s].timestamp + timedelta(seconds=1), evidence_type="poisoned_endpoint")
             for s in sorted(sites)]
    return rows + fakes


def main() -> None:
    OUT.mkdir(exist_ok=True)
    obs = list(read_observations_csv(DATA))
    rows = []
    for seed in range(20):
        sites = partition_observations(obs, 10, strategy="random", seed=seed)
        part = [o for s in sites for o in s.observations]
        all_sites = sorted({o.site_id for o in part})
        for device in TYPES:
            own = [o for o in part if o.device_type == device and (o.fqdn or o.remote_ip)]
            es = sorted({o.site_id for o in own})
            for k in range(1, 6):
                uniform = sorted(set(random.Random(seed).sample(all_sites, k)) & set(es))
                es_model = sorted(random.Random(f"{seed}:{k}:{device}").sample(es, min(k, len(es))))
                for model, chosen in (("uniform", uniform), ("es_d", es_model)):
                    score = None
                    if chosen:
                        score = next(s for s in DIBScorer(CONFIG).score(inject(own, device, chosen)) if s.endpoint == FAKE)
                    rows.append({"seed": seed, "device_type": device, "k": k, "model": model, "ES_d": len(es),
                                 "k_d": len(chosen), "share": round(len(chosen) / len(es), 6),
                                 "chosen": ";".join(chosen), "score": round(score.score, 6) if score else 0.0,
                                 "admitted": bool(score and score.accepted),
                                 "admissible": admissible(len(chosen), len(es))})
        print(f"seed {seed} done", flush=True)
    with (OUT / "netatmo_sampling.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    table = []
    for device in TYPES:
        for k in range(1, 6):
            for model in ("uniform", "es_d"):
                sel = [r for r in rows if r["device_type"] == device and r["k"] == k and r["model"] == model]
                if model == "uniform":
                    expected = statistics.mean(float(p_admissible_uniform(k, r["ES_d"])) for r in sel)
                else:
                    expected = statistics.mean(float(admissible(min(k, r["ES_d"]), r["ES_d"])) for r in sel)
                table.append({"device_type": device, "k": k, "model": model,
                              "ES_d_range": f"{min(r['ES_d'] for r in sel)}-{max(r['ES_d'] for r in sel)}",
                              "share_range": f"{min(r['share'] for r in sel):.3f}-{max(r['share'] for r in sel):.3f}",
                              "expected_p_admissible": round(expected, 4),
                              "observed_admissible": f"{sum(r['admissible'] for r in sel)}/20",
                              "observed_admitted": f"{sum(r['admitted'] for r in sel)}/20",
                              "seeds_admitted": ";".join(str(r["seed"]) for r in sel if r["admitted"])})
    with (OUT / "netatmo_sampling_table.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    for t in table:
        print(t)


if __name__ == "__main__":
    main()
