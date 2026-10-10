"""Count form of Criterion 1 on the real DIBScorer (Fase 2, TNSM revision).

Run from the repo root:
    PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 \
        python3 -m pytest analysis_fs/test_fstar_scorer.py -q -p no:cacheprovider

Hypothesis H (stated by the user, written before running):
  With (alpha, theta) = (0.6, 0.65), a fact reported only by K adversarial
  sites, and never by the h honest sites that observe the device type, is
  admitted if and only if K > 5h/7 (K >= 5h/7 with the tie excluded), even
  with adversarial volume rho = 100. For other (alpha, theta), 5/7 becomes
  r = (theta + alpha - 1) / (1 - theta), so H reads "admitted iff K > r*h".
  Grid: K = 1..8, h = 0..20; pairs (0.6, 0.65), (0.7, 0.65), (0.6, 0.7),
  (0.55, 0.6), i.e. r = 5/7, 1, 1, 3/8.

Adversary (worst case for Criterion 1): every adversarial site reports the
fake fact on every active day of the type, and the adversaries together
supply at least rho = 100 times the honest volume. Each honest site reports
one legitimate fact once per day. Two constructions, both reused helpers:
  - bound_grid.population: one day, adversary volume ceil(100h/K) per site;
  - test_followup._flood: three days, ceil(100h/K) reports per site per day.
Production scoring (code/src/dib/evaluation/dib.py): C_s = |S_e|/|ES_d|
(:276), C_t = min(1, 0.7*day ratio + 0.3*volume ratio) (:277-279),
score = alpha*C_s + beta*C_t (:281-285), admit_auto (:22-47) with quorum
min_reporting_sites (:45-46).

Prediction (exact Fraction arithmetic on the formula above, computed before
running DIBScorer): H is contradicted only where K = 1 and K > r*h, i.e.
(K, h) = (1, 0), (1, 1) at r = 5/7, (1, 0) at r = 1, and (1, 0), (1, 1),
(1, 2) at r = 3/8. There the score clears theta, but the quorum m = 2
rejects a single-source fact (dib.py:45-46). With m = 1 (score only), H
should hold on the whole grid. The finite volume (rho >= 100) moves the score
below the supremum by at most 0.3*beta/101, too little to flip any cell of
this grid.

Falsification criterion: any (K, h, alpha, theta) where the admission
decision of DIBScorer differs from "K > r*h". Contradictions are collected
and reported in full. The assertion is not weakened (repo rule): under
m = 2 the test is expected to FAIL on the K = 1 cells listed above. Also
checked: with h >= 1 the score stays strictly below the supremum
alpha*K/(K+h) + beta (bound never attained).
"""
from __future__ import annotations

import math
import sys
from fractions import Fraction as F
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dib.evaluation.dib import DIBScorer, ScoringConfig  # noqa: E402

import bound_grid  # noqa: E402
from test_followup import _flood  # noqa: E402

PAIRS = [(F(6, 10), F(65, 100)), (F(7, 10), F(65, 100)),
         (F(6, 10), F(7, 10)), (F(55, 100), F(6, 10))]
K_MAX, H_MAX, RHO, DAYS = 8, 20, 100, 3


def ratio(alpha: F, theta: F) -> F:
    return (theta + alpha - 1) / (1 - theta)


def one_day(K: int, h: int):
    # bound_grid.population takes N = K + h; honest "h*", adversaries "a*".
    return bound_grid.population(K + h, K, RHO), "fake.example"


def multi_day(K: int, h: int):
    per_day = math.ceil(F(RHO * h, K)) if h else 1
    return _flood([f"h{i}" for i in range(h)], [f"a{j}" for j in range(K)], DAYS, per_day), "fake.example"


POPULATIONS = {"one_day": one_day, "multi_day": multi_day}
_CACHE: dict = {}


def scored(build: str, K: int, h: int, alpha: F, theta: F, m: int):
    key = (build, K, h)
    if key not in _CACHE:
        _CACHE[key] = POPULATIONS[build](K, h)
    rows, fake = _CACHE[key]
    cfg = ScoringConfig(alpha=float(alpha), beta=float(1 - alpha), gamma=0.0, theta=float(theta),
                        min_reporting_sites=m, graph_enabled=False)
    return next(s for s in DIBScorer(cfg).score(rows) if s.endpoint == fake), rows


def contradictions(build: str, alpha: F, theta: F, m: int) -> list[tuple]:
    r = ratio(alpha, theta)
    out = []
    for K in range(1, K_MAX + 1):
        for h in range(0, H_MAX + 1):
            s, _ = scored(build, K, h, alpha, theta, m)
            if s.accepted != (K > r * h):
                out.append((K, h, f"H={K > r * h}", f"accepted={s.accepted}", round(s.score, 6),
                            f"|S_e|={s.supporting_sites}"))
    return out


@pytest.mark.parametrize("build", list(POPULATIONS))
@pytest.mark.parametrize("alpha,theta", PAIRS, ids=[f"a{float(a)}-t{float(t)}" for a, t in PAIRS])
def test_h_score_only_m1(build, alpha, theta):
    """H on the score alone (quorum m = 1): predicted to hold on the whole grid."""
    bad = contradictions(build, alpha, theta, m=1)
    assert not bad, f"H contradicted at (alpha={alpha}, theta={theta}, m=1, {build}): {bad}"


@pytest.mark.parametrize("build", list(POPULATIONS))
@pytest.mark.parametrize("alpha,theta", PAIRS, ids=[f"a{float(a)}-t{float(t)}" for a, t in PAIRS])
def test_h_operating_quorum_m2(build, alpha, theta):
    """H as stated, with the operating quorum m = 2: predicted to fail only at K = 1."""
    bad = contradictions(build, alpha, theta, m=2)
    assert not bad, f"H contradicted at (alpha={alpha}, theta={theta}, m=2, {build}): {bad}"


@pytest.mark.parametrize("build", list(POPULATIONS))
def test_supremum_never_attained(build):
    """With h >= 1, score < alpha*K/(K+h) + beta, and adversarial volume >= rho * honest."""
    for alpha, theta in PAIRS:
        for K in range(1, K_MAX + 1):
            for h in range(1, H_MAX + 1):
                s, rows = scored(build, K, h, alpha, theta, 2)
                n_adv = sum(1 for o in rows if o.fqdn == "fake.example")
                assert n_adv >= RHO * (len(rows) - n_adv)
                assert s.site_confidence == pytest.approx(K / (K + h))
                assert s.score < float(alpha * F(K, K + h) + (1 - alpha))
