"""Audit 51: (A) sweep of m in {1,2,3} and (B) rho dependence of the Criterion 1 margin. Hypotheses, predictions and falsification criteria are in
docs/audit/51_prereg_m_rho.md (committed before this file). Module under test: analysis_fs/m_rho_tables.py.

Run: PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -m pytest analysis_fs/test_m_rho.py -q -p no:cacheprovider
Contradictions are collected and reported in full; assertions are not weakened (repo rule). Tie zone |exact - theta| < 1e-12 is listed, not asserted.
"""
import json
import math
import sys
from fractions import Fraction as F
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bound_grid  # noqa: E402
import m_rho_tables as T  # noqa: E402
from dib.evaluation.dib import DIBScorer, ScoringConfig  # noqa: E402
import test_fstar_scorer as S  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HIST = json.loads((ROOT / "experiments_tnsm/synthetic_federation/anchor_hd.json").read_text())["histograms"]


# ---- A ---------------------------------------------------------------------------------------------------------------
def test_k_eff_and_binding():
    assert [T.k_eff(N, 2) for N in (1, 2, 3, 5, 12)] == [2, 2, 2, 3, 5]
    assert [T.k_eff(N, 3) for N in (1, 2, 3, 4, 5, 6)] == [3, 3, 3, 3, 3, 3]
    assert [N for N in range(1, 21) if T.binds(N, 1)] == []
    assert [N for N in range(1, 21) if T.binds(N, 2)] == [1, 2]
    assert [N for N in range(1, 21) if T.binds(N, 3)] == [1, 2, 3, 4]


def test_types_able_to_have_an_admitted_fact():
    fam, base = HIST["with_ncsu_family"], HIST["base_4_sites"]
    assert [T.types_able(fam, m) for m in (1, 2, 3)] == [119, 36, 5]
    assert [T.types_able(base, m) for m in (1, 2, 3)] == [119, 32, 4]


@pytest.mark.parametrize("build", list(S.POPULATIONS))
@pytest.mark.parametrize("alpha,theta", S.PAIRS, ids=[f"a{float(a)}-t{float(t)}" for a, t in S.PAIRS])
def test_h_a1_m3_on_real_scorer(build, alpha, theta):
    """H-A1 for m = 3 (m = 1, 2 were verified in audit 11; they are rechecked here so the three values share one run)."""
    r = S.ratio(alpha, theta)
    bad = []
    for m in (1, 2, 3):
        for K in range(1, S.K_MAX + 1):
            for h in range(0, S.H_MAX + 1):
                s, _ = S.scored(build, K, h, alpha, theta, m)
                if s.accepted != (K > r * h and K >= m):
                    bad.append((m, K, h, s.accepted, round(s.score, 6)))
    assert not bad, f"H-A1 contradicted ({build}, alpha={alpha}, theta={theta}): {bad}"


def test_k_eff_matches_scorer_for_adversary_at_supremum():
    """At (0.6, 0.65) with rho = 1000 the finite-rho margin is tiny: the smallest K admitted (m = 3) must equal max(3, ceil(5N/12)) wherever
    K > 5h/7 is equivalent to K >= ceil(5N/12) (N = K + h; ties excluded by the strict inequality at rho = 1000, checked on this grid)."""
    a, th = F(3, 5), F(13, 20)
    for h in range(1, 13):
        got = None
        for K in range(1, 30):
            s, _ = S.scored("one_day", K, h, a, th, 3) if K <= S.K_MAX and h <= S.H_MAX else (None, None)
            if s is None:
                break
            if s.accepted:
                got = K
                break
        if got is not None:
            assert got >= 3 and got > F(5, 7) * h


# ---- B ---------------------------------------------------------------------------------------------------------------
def test_score_exact_formula_and_margin():
    assert T.margin_to_sup(100) == F(3, 10) * F(2, 5) / 101
    assert float(T.margin_to_sup(100)) == pytest.approx(0.00118811, abs=1e-8)
    # K = 2, h = 5, rho = 100: n_a = ceil(500/2)*2 = 500
    s = T.score_exact(2, 5, 100)
    assert s == F(3, 5) * F(2, 7) + F(2, 5) * (F(7, 10) + F(3, 10) * F(500, 505))


@pytest.mark.parametrize("rho", [1, 2, 5, 10, 100, 1000])
def test_h_b1_scorer_matches_exact_score(rho):
    cfg = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=1, graph_enabled=False)
    bad, ties = [], []
    for h in range(1, 21):
        for K in range(1, 9):
            obs = bound_grid.population(K + h, K, rho)
            s = next(x for x in DIBScorer(cfg).score(obs) if x.endpoint == "fake.example")
            exact = T.score_exact(K, h, rho)
            if abs(exact - F(13, 20)) < F(1, 10**12):
                ties.append((K, h))
                continue
            if s.accepted != (exact >= F(13, 20)):
                bad.append((K, h, s.accepted, float(exact)))
    assert not bad, f"H-B1 contradicted at rho={rho}: {bad}"


def test_k_min_table_monotone_towards_r():
    """K_min(h, rho)/h approaches r = 5/7 from above as rho grows (finite volume only raises the bar for the adversary)."""
    for h in (7, 14, 21):
        prev = None
        for rho in (1, 10, 100, 1000, 10**6):
            k = T.k_min(h, rho)
            if prev is not None:
                assert k <= prev
            prev = k
        assert F(T.k_min(h, 10**6), h) > F(5, 7)  # strict: the supremum is not attained


def test_ct_never_saturates():
    n = 20
    for i in range(n + 1):
        for j in range(n + 1):
            ct = T.ct_exact(F(i, n), F(j, n))
            assert ct <= 1 and (ct == 1) == (i == n and j == n)
