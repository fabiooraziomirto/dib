"""Audit 44 s.3: exact region of DIB admission (T1 algebra, T2 on the real DIBScorer). Not executed before this commit.

Run from the repo root:
    PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -m pytest analysis_fs/test_a5_region.py -q -p no:cacheprovider

Claim under test (derived on paper, audit 44 s.3): with gamma = 0, alpha = 3/5, beta = 2/5, theta = 13/20, m = 2, an
eligible class and no dispute, DIB admits iff |S_e| >= 2 and C_s >= 5/12 and C_t >= (theta - alpha*C_s)/beta.
Falsification: any grid point (T1) or synthetic endpoint outside the tie zone (T2) where `accepted` differs from the
prediction. Tie zone: |exact score - theta| < 1e-12 is listed apart and asserted neither way (code compares floats,
dib.py:47). The assertion is not weakened if it fails; the failure is reported (CLAUDE.md).
Module under test: analysis_fs/a5_region.py (predictor, exact Fractions).
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from fractions import Fraction as F
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dib.core.models import Observation  # noqa: E402
from dib.evaluation.dib import DIBScorer, ScoringConfig  # noqa: E402

import a5_region as R  # noqa: E402

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_t1_algebra_equivalence_on_grid():
    """score >= theta  <=>  C_s >= 5/12 and C_t >= (theta - alpha*C_s)/beta, exactly, ties included."""
    a, b, th = F(3, 5), F(2, 5), F(13, 20)
    assert R.PHI == F(5, 12) == (th - b) / a
    n_checked = 0
    for N in (5, 6, 10, 12, 20, 50, 100):
        for K in range(N + 1):
            cs = F(K, N)
            for j in range(101):
                ct = F(j, 100)
                assert (a * cs + b * ct >= th) == R.region(cs, ct), (N, K, j)
                n_checked += 1
    assert n_checked == sum((N + 1) * 101 for N in (5, 6, 10, 12, 20, 50, 100))


def test_t1_threshold_values():
    assert R.ct_threshold(F(1)) == F(1, 8)
    assert R.ct_threshold(F(5, 12)) == F(1)
    assert R.ct_threshold(F(1, 2)) == F(13, 20) * F(5, 2) - F(3, 2) * F(1, 2)


def _population(rng: random.Random):
    n_sites = rng.randint(2, 12)
    days = rng.randint(1, 6)
    obs = []
    eps = [("a.vendor.example", "https", 443), ("b.vendor.example", "https", 443), ("update.vendor.example", "https", 443),
           ("192.168.1.5", "tcp", 8080), ("local-0.d.example", "https", 443)]
    for s in range(n_sites):
        for e, proto, port in eps:
            if rng.random() < rng.choice((0.2, 0.5, 0.9)):
                for _ in range(rng.randint(1, 4)):
                    d = rng.randrange(days)
                    obs.append(Observation(site_id=f"s{s}", device_id=None, device_type="d", fqdn=e, remote_ip=None,
                                           protocol=proto, port=port,
                                           timestamp=T0 + timedelta(days=d, seconds=rng.randrange(3600)),
                                           source_dataset="syn", evidence_type="flow"))
    return obs


@pytest.mark.parametrize("seed", range(40))
def test_t2_prediction_matches_scorer(seed):
    obs = _population(random.Random(seed))
    cfg = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2, graph_enabled=False)
    ties = []
    for s in DIBScorer(cfg).score(obs):
        cs, ct = F(s.site_confidence), F(s.temporal_confidence)
        exact = F(3, 5) * cs + F(2, 5) * ct
        if abs(exact - F(13, 20)) < F(1, 10**12):
            ties.append((s.endpoint, float(exact)))
            continue
        eligible = s.endpoint_class in {"dns", "ntp", "update", "vendor-cloud"}
        assert s.accepted == R.predict(s.supporting_sites, cs, ct, eligible, m=2), (seed, s)
    # ties are listed, not asserted
    assert isinstance(ties, list)


def test_t2_single_source_inside_region_is_rejected_by_quorum():
    """Two sites, one endpoint reported by one site only, every day: C_s = 1/2 >= 5/12 and C_t = 0.7 + 0.3*30/33 (> 0.875) put the score above
    theta (exact), so only the quorum m = 2 rejects it (dib.py:45-46). Guards the |S_e| >= m clause (mutation m = 1)."""
    obs = []
    for d in range(3):
        for k in range(10):  # s0: 10 reports/day of the solo endpoint -> frequency ratio 30/33
            obs.append(Observation(site_id="s0", device_id=None, device_type="d", fqdn="solo.vendor.example",
                                   remote_ip=None, protocol="https", port=443,
                                   timestamp=T0 + timedelta(days=d, seconds=k), source_dataset="syn", evidence_type="flow"))
        obs.append(Observation(site_id="s1", device_id=None, device_type="d", fqdn="both.vendor.example",
                               remote_ip=None, protocol="https", port=443,
                               timestamp=T0 + timedelta(days=d), source_dataset="syn", evidence_type="flow"))
    cfg = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2, graph_enabled=False)
    solo = next(s for s in DIBScorer(cfg).score(obs) if s.endpoint == "solo.vendor.example")
    cs, ct = F(solo.site_confidence), F(solo.temporal_confidence)
    assert solo.supporting_sites == 1 and R.region(cs, ct)
    assert solo.accepted is False and R.predict(1, cs, ct, True, m=2) is False
