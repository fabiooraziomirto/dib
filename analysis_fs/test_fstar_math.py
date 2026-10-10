"""Exact checks of the breadth-margin formulas used in paper Sec. IV-C.

Hypotheses (declared before running):
 H1. f* = (theta - beta)/alpha = 1 - (1-theta)/alpha equals 5/12 at
     (alpha, theta) = (0.6, 0.65), and alpha*f_s + beta = 0.58 at f_s = 0.30.
 H2. For K adversarial and h honest sites, K/(K+h) < f*  <=>
     K < ((theta+alpha-1)/(1-theta)) * h  (= 5h/7 at the operating point).
 H3. Three colluders need h >= 5 honest sites at the margin and h >= 7 at
     f_s = 0.30 (matches analysis_fs/REPORT.md, table of minimum h_d).
 H4. fs_binomial.kmin / p_violate agree with hand-computed values.
Pure arithmetic with Fraction: no production code is imported or changed.
Falsifier: any assertion failing means the paper text must be corrected.
"""
from fractions import Fraction as F

import pytest

import fs_binomial as fb

ALPHA, THETA = F(6, 10), F(65, 100)
BETA = 1 - ALPHA


def fstar(alpha, theta):
    return (theta - (1 - alpha)) / alpha


def test_h1_operating_point():
    assert fstar(ALPHA, THETA) == F(5, 12)
    assert fstar(ALPHA, THETA) == 1 - (1 - THETA) / ALPHA
    assert ALPHA * F(3, 10) + BETA == F(58, 100)


@pytest.mark.parametrize("alpha,theta", [
    (F(6, 10), F(65, 100)), (F(7, 10), F(65, 100)),
    (F(6, 10), F(7, 10)), (F(55, 100), F(6, 10)),
])
def test_h2_count_form_equivalence(alpha, theta):
    f = fstar(alpha, theta)
    ratio = (theta + alpha - 1) / (1 - theta)
    for K in range(0, 40):
        for h in range(1, 80):
            assert (F(K, K + h) < f) == (K < ratio * h)


def test_h3_three_colluders():
    f = fstar(ALPHA, THETA)
    assert min(h for h in range(1, 60) if 3 < F(5, 7) * h) == 5
    assert min(h for h in range(1, 60) if F(3, 3 + h) <= F(3, 10)) == 7
    assert f - F(3, 10) == F(7, 60)


def test_h4_binomial_tail():
    assert [fb.kmin(n) for n in (5, 10, 20, 50, 100)] == [3, 5, 9, 21, 42]
    assert fb.p_violate(10, 0.10) == pytest.approx(1.63e-3, rel=2e-2)
    assert fb.p_violate(20, 0.10) == pytest.approx(5.99e-5, rel=2e-2)
    assert fb.p_violate(50, 0.10) == pytest.approx(3.71e-9, rel=2e-2)
