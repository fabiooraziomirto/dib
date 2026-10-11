"""Exact admission region of DIB at (alpha, beta, theta) = (3/5, 2/5, 13/20), gamma = 0 (audit 44 s.3)."""
from fractions import Fraction as F

ALPHA, BETA, THETA = F(3, 5), F(2, 5), F(13, 20)
PHI = (THETA - BETA) / ALPHA  # 5/12


def ct_threshold(cs: F) -> F:
    """Minimum C_t for a given C_s: (theta - alpha*C_s)/beta."""
    return (THETA - ALPHA * cs) / BETA


def region(cs: F, ct: F) -> bool:
    return cs >= PHI and ct >= ct_threshold(cs)


def predict(supporting_sites: int, cs: F, ct: F, eligible: bool, m: int = 2) -> bool:
    return eligible and supporting_sites >= m and region(cs, ct)
