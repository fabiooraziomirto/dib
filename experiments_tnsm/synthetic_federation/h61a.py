"""H6-1a and H6-2 (plan rev. 5, Passo 6; audit 14 s.4, audit 16): DIB against the binomial
bound of Criterion 1, one device type at a time.

Definitions read in the code BEFORE writing this script (GATE 1, audit 14 s.3)
-----------------------------------------------------------------------------
* Admission of a fact e of type d (code/src/dib/evaluation/dib.py):
    accepted = admit_auto(score, theta, class, supporting_sites=|S_e|, min_reporting_sites=m)
  (call at dib.py:286-298), where admit_auto (dib.py:22-47) is
    |S_e| >= m  AND  class in {dns, ntp, update, vendor-cloud}  AND  score >= theta
    AND NOT open_dispute (always False here, dib.py:25,47).
  |S_e| = number of distinct sites reporting e (dib.py:196,250).
* score = alpha*C_s + beta*C_t + gamma*C_g (dib.py:272-276), with
  C_s = |S_e| / |ES_d| in raw-breadth mode (dib.py:268), ES_d = every site holding at least
  one observation of type d, adversaries included (dib.py:195,249);
  C_t = min(1, 0.7*days_e/days_d + 0.3*n_e/n_d) (dib.py:269-271).
* Criterion 1 (paper; audit 09, 11): with gamma = 0 and beta = 1 - alpha, adversary-only
  evidence (K of N = |ES_d| sites) is rejected whenever K/N < f* = 1 - (1-theta)/alpha
  = 5/12 at (alpha, theta) = (0.6, 0.65), because score <= alpha*K/N + beta < theta.
  Counting form (audit 11): rejected if K < ceil(5N/12) (strictly below the margin).
  With m = 2 a single site (K = 1) is also rejected by the quorum.

Secondary rules that can admit an A2 fact with n_avv < ceil(5N/12) (GATE 1 check)
-------------------------------------------------------------------------------
  R1. Graph term: with gamma > 0 (configs/graph_augmented.yaml: gamma 0.2, graph on) the
      score gains up to gamma*C_g and the bound above no longer holds. EXCLUDED here:
      gamma = 0, graph_enabled = False (configs/graph_free_*.yaml).
  R2. Trust weighting: the SELECTED paper configuration configs/graph_free_selected.yaml
      has trust_weighted: true (LOCKED_CONFIGS.md:12). Then C_s = sum_{S_e} w / sum_{ES_d} w
      (dib.py:256-259) with w = min(1, breadth/reference) (trust.py:86-104): adversaries
      with full weight and down-weighted honest sites can exceed 5/12 with K/N < 5/12.
      So D0 as stated in the plan DOES NOT HOLD for the selected configuration.
      -> D0 is checked on the raw-breadth configuration (configs/graph_free_unweighted_
         federation.yaml, the one Criterion 1 is stated for: "raw-breadth shares below
         5/12"). For the trust-weighted configuration the plan's D0 is REDEFINED as
         D0': no admission when the WEIGHTED adversary share sum_adv w / sum_{ES_d} w is
         below 5/12. D0' AWAITS USER CONFIRMATION before any launch (GATE 1).
  R3. Denominator: ES_d counts only sites with an observation of d (dib.py:195). An honest
      site of type d with no observation shrinks N. Here every honest site has one
      observation (bound_grid.population), and N is taken from DIB's own eligible_sites,
      asserted equal to the generated N.
  R4. Honest support of the fabricated endpoint would raise |S_e| above K: excluded by
      construction (fresh endpoint "fake.example" reported only by adversaries).
  R5. Class gate: "fake.example" https/443 classifies as vendor-cloud (eligible), so the
      class gate never protects; this is the worst case.

Construction
------------
One device type, N sites; each site adversarial with probability q (H1, independent) or,
for H6-2, beta-binomial with intra-class correlation rho_corr = 0.3 (shared latent). The
population is analysis_fs.bound_grid.population(N, K, rho=100): one day, every honest site
one legit observation, the K adversaries jointly flood the fabricated fact (total collusion,
plan's principal A2 strategy). The population is a deterministic function of (N, K), so
DIBScorer is run once per distinct (N, K) and memoized; the per-trial outcome is that
memoized decision (exact, not an approximation). Every trial records n_avv BEFORE scoring.

Hypotheses (declared before running; plan rev. 5)
-------------------------------------------------
G   generator control, without DIB: X_gen = #trials with n_avv >= ceil(5N/12).
    G-excess (25 points): defect if the one-sided CP lower bound of X_gen/n exceeds
    p* = fs_binomial.p_violate(N, q). G-deficit (9 powered points, p* >= 2.8e-3): defect if
    the one-sided CP upper bound is below p*.
D0  deterministic, outside the statistical family: in trials with n_avv < ceil(5N/12), DIB
    (raw configuration) admits NO A2 fact. One admission falsifies H6-1a at any point.
D1  X_dib = #trials with the A2 fact admitted. H6-1a falsified if the CP lower bound of
    X_dib/n exceeds p* (25 tests).
Family: 59 one-sided tests (25 + 9 + 25), Bonferroni, alpha per test = 0.05/59, the same for
all. Discordant outcomes: G fails -> H6-1a void until the generator is fixed; D0 fails ->
DIB violates Criterion 1, stop and report (no fix without the user); D1 rejects with G and
D0 passing is impossible (X_dib <= X_gen) -> analysis bug. Descriptive only: admission rate
conditional on n_avv >= ceil(5N/12).
H6-2 (rho_corr = 0.3): X_gen exceeds p*. Separate family of 9 one-sided tests at the same
alpha per test (0.05/59). GATE 4 (audit 16 s.2): with the beta-binomial the expected excess
on the 9 points is 1.6x-42x p*, detectable with power ~1 at n = 20000, so no point is
excluded. Falsified if the CP lower bound exceeds p* at none of the 9 points.

Usage:  PYTHONPATH=code/src:. python3 experiments_tnsm/synthetic_federation/h61a.py \
            --trials 20000 --seed 20261010 --out <dir> [--rho-corr 0 | 0.3] [--config raw|trust]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_dist

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(ROOT))

from analysis_fs.bound_grid import population  # noqa: E402
from analysis_fs.fs_binomial import p_violate  # noqa: E402
from dib.evaluation.dib import DIBScorer, ScoringConfig  # noqa: E402
from dib.evaluation.trust import compute_site_trust_weights  # noqa: E402

NS = (5, 10, 20, 50, 100)
QS = (0.01, 0.05, 0.10, 0.20, 0.30)
RHO_FLOOD = 100
ALPHA_FAMILY = 0.05 / 59
POWERED_MIN_PSTAR = 2.8e-3  # G-deficit power (plan rev. 5): p* >= 2.8e-3 -> 9 points
FSTAR_NUM, FSTAR_DEN = 5, 12

CONFIGS = {
    # configs/graph_free_unweighted_federation.yaml
    "raw": dict(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2,
                graph_enabled=False, trust_weighted=False),
    # configs/graph_free_selected.yaml (trust reference: 1 = honest breadth in this construction)
    "trust": dict(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2,
                  graph_enabled=False, trust_weighted=True, trust_reference_breadth=1.0),
}


def kmin(n: int) -> int:
    return math.ceil(FSTAR_NUM * n / FSTAR_DEN)


def cp_lower(x: int, n: int, a: float) -> float:
    return 0.0 if x == 0 else float(beta_dist.ppf(a, x, n - x + 1))


def cp_upper(x: int, n: int, a: float) -> float:
    return 1.0 if x == n else float(beta_dist.ppf(1 - a, x + 1, n - x))


@lru_cache(maxsize=None)
def dib_decision(config_name: str, n: int, k: int) -> dict:
    """Real DIBScorer on bound_grid.population(n, k, RHO_FLOOD); memoized (deterministic)."""
    if k == 0:
        return {"admitted": False, "eligible_sites": n, "supporting_sites": 0, "score": None,
                "weighted_adv_share": 0.0}
    obs = population(n, k, RHO_FLOOD)
    cfg = ScoringConfig(**CONFIGS[config_name])
    fake = next(s for s in DIBScorer(cfg).score(obs) if s.endpoint == "fake.example")
    weights = compute_site_trust_weights(obs, reference_breadth=cfg.trust_reference_breadth)
    adv = {o.site_id for o in obs if o.fqdn == "fake.example"}
    elig = {o.site_id for o in obs}
    w_share = sum(weights.get(s, 0.0) for s in adv) / sum(weights.get(s, 0.0) for s in elig)
    return {"admitted": bool(fake.accepted), "eligible_sites": fake.eligible_sites,
            "supporting_sites": fake.supporting_sites, "score": fake.score,
            "weighted_adv_share": w_share, "endpoint_class": fake.endpoint_class}


def draw_k(rng: np.random.Generator, n: int, q: float, rho_corr: float, trials: int) -> np.ndarray:
    if rho_corr == 0:
        return rng.binomial(n, q, size=trials)
    a = q * (1 / rho_corr - 1)
    b = (1 - q) * (1 / rho_corr - 1)
    return rng.binomial(n, rng.beta(a, b, size=trials))


def run_point(n: int, q: float, trials: int, rng, rho_corr: float, config_name: str) -> dict:
    ks = draw_k(rng, n, q, rho_corr, trials)          # n_avv recorded before any scoring
    km = kmin(n)
    counts = np.bincount(ks, minlength=n + 1)
    x_gen = int(counts[km:].sum())
    x_dib = d0_viol = d0p_viol = cond_adm = 0
    for k in np.nonzero(counts)[0]:
        c = int(counts[k])
        dec = dib_decision(config_name, n, int(k))
        assert dec["eligible_sites"] == n, (n, k, dec)                       # R3
        assert dec["supporting_sites"] == int(k), (n, k, dec)                # R4
        if dec["admitted"]:
            x_dib += c
            if k < km:
                d0_viol += c
            if dec["weighted_adv_share"] * FSTAR_DEN < FSTAR_NUM:
                d0p_viol += c
            if k >= km:
                cond_adm += c
    pstar = p_violate(n, q)
    powered = pstar >= POWERED_MIN_PSTAR
    a = ALPHA_FAMILY
    return {
        "N": n, "q": q, "rho_corr": rho_corr, "config": config_name, "trials": trials,
        "kmin": km, "p_star": pstar, "powered": powered,
        "x_gen": x_gen, "x_dib": x_dib,
        "gen_cp_lower": cp_lower(x_gen, trials, a), "gen_cp_upper": cp_upper(x_gen, trials, a),
        "dib_cp_lower": cp_lower(x_dib, trials, a),
        "G_excess_defect": cp_lower(x_gen, trials, a) > pstar,
        "G_deficit_defect": powered and cp_upper(x_gen, trials, a) < pstar,
        "D0_violations": d0_viol, "D0prime_violations": d0p_viol,
        "D1_falsified": cp_lower(x_dib, trials, a) > pstar,
        "cond_admission_rate": (cond_adm / x_gen) if x_gen else None,
        "k_hist": {int(k): int(counts[k]) for k in np.nonzero(counts)[0]},
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--trials", type=int, default=20000)
    p.add_argument("--seed", type=int, default=20261010)
    p.add_argument("--rho-corr", type=float, default=0.0)
    p.add_argument("--config", choices=sorted(CONFIGS), default="raw")
    p.add_argument("--out", required=True)
    p.add_argument("--points", default=None, help="subset 'N:q,N:q' (pilot/tests)")
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    points = [(n, q) for n in NS for q in QS]
    if a.points:
        points = [(int(s.split(":")[0]), float(s.split(":")[1])) for s in a.points.split(",")]
    rng = np.random.default_rng(a.seed)
    t0 = time.time()
    rows = [run_point(n, q, a.trials, rng, a.rho_corr, a.config) for n, q in points]
    elapsed = time.time() - t0
    with (out / "points.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[k for k in rows[0] if k != "k_hist"])
        w.writeheader()
        for r in rows:
            w.writerow({k: v for k, v in r.items() if k != "k_hist"})
    (out / "k_hist.json").write_text(json.dumps({f"{r['N']}:{r['q']}": r["k_hist"] for r in rows}))
    files = [Path(__file__), ROOT / "analysis_fs/bound_grid.py", ROOT / "analysis_fs/fs_binomial.py",
             ROOT / "code/src/dib/evaluation/dib.py", ROOT / "code/src/dib/evaluation/trust.py"]
    manifest = {"argv": sys.argv, "seed": a.seed, "trials": a.trials, "rho_corr": a.rho_corr,
                "config": a.config, "scoring": CONFIGS[a.config], "rho_flood": RHO_FLOOD,
                "alpha_per_test": ALPHA_FAMILY, "elapsed_s": round(elapsed, 3),
                "python": sys.version, "platform": platform.platform(),
                "numpy": np.__version__, "sha256": {str(f.relative_to(ROOT)): sha256(f) for f in files}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(rows)} points, {elapsed:.1f} s -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
