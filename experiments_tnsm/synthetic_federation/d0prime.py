"""D0' (audit 16 s.2, confirmed by the user 2026-10-10): Criterion 1 for the TRUST-WEIGHTED
configuration, with uniform weights (control) and heterogeneous weights (the real test).

What DIB computes (read before writing; the check below uses exactly these quantities)
------------------------------------------------------------------------------------
* Weights: w_s = min(1, breadth_s / reference) (code/src/dib/evaluation/trust.py:86-104),
  breadth_s = distinct endpoint keys of site s over ALL device types (trust.py:57-67),
  computed on the scored observations when no trust_observations are passed
  (dib.py:157-161).
* Weighted breadth: C_s = sum_{s in S_e} w_s / sum_{s in ES_d} w_s (dib.py:256-259); the same
  normalization is used here (sum over S_e divided by sum over ES_d, from the same weights).
* Admission: score >= theta AND |S_e| >= m with |S_e| the UNWEIGHTED count (dib.py:250,292;
  admit_auto dib.py:22-47), class gate, no open dispute. alpha 0.6, beta 0.4, gamma 0,
  theta 0.65, m 2 (configs/graph_free_selected.yaml).
* D0' (weighted Criterion 1): for adversary-only evidence, score <= alpha*W + beta*C_t with
  C_t < 1 while an honest observation exists, so a fact is rejected whenever the weighted
  adversary share W = sum_adv w / sum_{ES_d} w is < 5/12 (strict); |S_e| >= 2 is the
  unweighted quorum.

Construction
------------
One device type d, N sites, K adversaries (K = 1..N, every value: an exhaustive grid in K
rather than binomial sampling, because D0' is a deterministic property); for each (N, K),
R random draws of the honest breadths. Population = analysis_fs.bound_grid.population
(N, K, rho=100) for type d, plus (b_s - 1) padding endpoints of another device type per
site, so that breadth_s = b_s without touching the statistics of type d.
* Honest breadths: b ~ uniform integer on [1, 2*REF - 1] (median REF), REF = 10 =
  trust_reference_breadth (as if calibrated at the median of clean data,
  trust.calibrate_reference_breadth). About half of the honest sites have weight < 1.
* Adversary breadth, two arms (declared attack surface: weights derive from observed
  breadth, so an adversary can PAD its breadth to gain weight):
    adv-low   b = 1    (w = 0.1, the Sybil case the weighting was designed for);
    adv-high  b = REF  (w = 1, an adversary that padded its breadth to full weight).
* Control arm uniform: REF = 0 (all weights 1, trust.py:102-103): weighted = raw.

Hypotheses (declared before running)
------------------------------------
H-D0'u (control, uniform weights): zero admissions with W < 5/12, and every decision equals
        the raw-configuration decision for the same population.
H-D0'h (heterogeneous weights, both adversary arms): zero admissions with W < 5/12 and zero
        admissions with |S_e| < 2. Falsified by ONE such admission (then: stop and report
        with file:line, no change to dib.py without the user).
Declared expectation, descriptive (not a test): in adv-high, DIB-weighted admits A2 facts
whose RAW share K/N is below 5/12 (the attack surface of the weighting: the raw Criterion 1
does not protect the selected configuration); in adv-low it admits only facts with raw share
well above 5/12. Reported as counts per N.

Usage: PYTHONPATH=code/src:. python3 experiments_tnsm/synthetic_federation/d0prime.py \
           --draws 20 --seed 20261010 --out <dir>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(ROOT))

from analysis_fs.bound_grid import population  # noqa: E402
from dib.core.models import Observation  # noqa: E402
from dib.evaluation.dib import DIBScorer, ScoringConfig  # noqa: E402
from dib.evaluation.trust import compute_site_trust_weights  # noqa: E402

NS = (5, 10, 20, 50, 100)
RHO_FLOOD = 100
REF = 10
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
BASE = dict(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2, graph_enabled=False)
ARMS = {"uniform": dict(ref=0.0, adv_b=1), "adv-low": dict(ref=float(REF), adv_b=1),
        "adv-high": dict(ref=float(REF), adv_b=REF)}


def pad(site: str, n: int) -> list[Observation]:
    return [Observation(site_id=site, device_id=None, device_type="pad", fqdn=f"pad-{j}.{site}.example",
                        remote_ip=None, protocol="https", port=443, timestamp=T0, source_dataset="grid",
                        evidence_type="flow") for j in range(n)]


def one(n: int, k: int, arm: str, rng: random.Random) -> dict:
    base = population(n, k, RHO_FLOOD)
    sites = sorted({o.site_id for o in base})
    adv = {o.site_id for o in base if o.fqdn == "fake.example"}
    breadth = {s: (ARMS[arm]["adv_b"] if s in adv else rng.randint(1, 2 * REF - 1)) for s in sites}
    obs = base + [o for s in sites for o in pad(s, breadth[s] - 1)]
    ref = ARMS[arm]["ref"]
    cfg_w = ScoringConfig(**BASE, trust_weighted=True, trust_reference_breadth=ref)
    cfg_r = ScoringConfig(**BASE, trust_weighted=False)
    fw = next((s for s in DIBScorer(cfg_w).score(obs) if s.endpoint == "fake.example"), None)
    fr = next((s for s in DIBScorer(cfg_r).score(obs) if s.endpoint == "fake.example"), None)
    w = compute_site_trust_weights(obs, reference_breadth=ref)
    elig = {o.site_id for o in obs if o.device_type == "d"}
    W = sum(w[s] for s in adv) / sum(w[s] for s in elig) if adv else 0.0
    if fw is not None:
        assert fw.eligible_sites == n and fw.supporting_sites == k
        assert math.isclose(fw.site_confidence, W, rel_tol=1e-12), (fw.site_confidence, W)  # same quantity as dib.py
    adm_w = bool(fw and fw.accepted)
    adm_r = bool(fr and fr.accepted)
    return {"N": n, "K": k, "arm": arm, "raw_share": k / n, "W": W,
            "admitted_weighted": adm_w, "admitted_raw": adm_r,
            "D0p_violation": adm_w and (W * 12 < 5 or k < 2),
            "raw_below_margin_admitted": adm_w and k * 12 < 5 * n}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--draws", type=int, default=20)
    p.add_argument("--seed", type=int, default=20261010)
    p.add_argument("--out", required=True)
    p.add_argument("--ns", default=",".join(map(str, NS)))
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.time()
    rows = []
    for n in map(int, a.ns.split(",")):
        for k in range(1, n + 1):  # K = 0: no A2 fact exists
            for arm in ARMS:
                for _ in range(a.draws if arm != "uniform" else 1):
                    rows.append(one(n, k, arm, rng))
    with (out / "d0prime_rows.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    summary = {}
    for arm in ARMS:
        r = [x for x in rows if x["arm"] == arm]
        summary[arm] = {
            "cases": len(r),
            "admitted_weighted": sum(x["admitted_weighted"] for x in r),
            "D0p_violations": sum(x["D0p_violation"] for x in r),
            "weighted_ne_raw": sum(x["admitted_weighted"] != x["admitted_raw"] for x in r),
            "raw_below_margin_admitted": sum(x["raw_below_margin_admitted"] for x in r),
            "raw_below_margin_admitted_by_N": {n: sum(x["raw_below_margin_admitted"] for x in r if x["N"] == n)
                                               for n in sorted({x["N"] for x in r})},
            "min_raw_share_admitted": min((x["raw_share"] for x in r if x["admitted_weighted"]), default=None),
        }
    files = [Path(__file__), ROOT / "analysis_fs/bound_grid.py", ROOT / "code/src/dib/evaluation/dib.py",
             ROOT / "code/src/dib/evaluation/trust.py"]
    manifest = {"argv": sys.argv, "seed": a.seed, "draws": a.draws, "REF": REF, "rho_flood": RHO_FLOOD,
                "arms": ARMS, "scoring": BASE, "elapsed_s": round(time.time() - t0, 2),
                "python": sys.version, "platform": platform.platform(),
                "sha256": {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
                "summary": summary}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
