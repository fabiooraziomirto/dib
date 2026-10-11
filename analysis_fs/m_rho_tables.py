"""Exact tables for audit 51: (A) quorum m in {1,2,3}; (B) volume rho in the Criterion 1 margin. alpha = 3/5, beta = 2/5, theta = 13/20, gamma = 0.
Usage: python3 analysis_fs/m_rho_tables.py   (prints markdown tables; nothing is written)"""
from __future__ import annotations

import json
import math
from fractions import Fraction as F
from pathlib import Path

ALPHA, BETA, THETA = F(3, 5), F(2, 5), F(13, 20)
PHI = (THETA - BETA) / ALPHA          # 5/12
ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "experiments_tnsm/synthetic_federation/anchor_hd.json"


def ceil_phi(N: int) -> int:
    return math.ceil(PHI * N)


def k_eff(N: int, m: int) -> int:
    """Smallest number of supporting sites at which a fact can be admitted (persistence at its maximum)."""
    return max(m, ceil_phi(N))


def binds(N: int, m: int) -> bool:
    return m > ceil_phi(N)


def types_able(hist: dict, m: int) -> int:
    """Device types with h independent sites that can have an admitted fact: need h >= m (max support is h; ceil(5h/12) <= h)."""
    return sum(c for h, c in hist.items() if int(h) >= m)


def ct_exact(d: F, f: F) -> F:
    return min(F(1), F(7, 10) * d + F(3, 10) * f)


def score_exact(K: int, h: int, rho: int) -> F:
    """Score of the fabricated fact in bound_grid.population(K + h, K, rho): one day; n_a = K * ceil(total/K), total = rho*h (or K if h = 0)."""
    total = rho * h if h else K
    n_a = K * math.ceil(F(total, K))
    return ALPHA * F(K, K + h) + BETA * ct_exact(F(1), F(n_a, n_a + h))


def margin_to_sup(rho: int) -> F:
    """beta * (1 - C_t) at the supremum of volume share: 0.3*beta/(1 + rho)."""
    return F(3, 10) * BETA / (1 + rho)


def k_min(h: int, rho: int, k_max: int = 10_000) -> int:
    for K in range(1, k_max + 1):
        if score_exact(K, h, rho) >= THETA:
            return K
    raise ValueError("no K up to k_max")


def main() -> None:
    hist = json.loads(HIST.read_text())["histograms"]
    print("## A. Effective quorum k_eff(N, m) = max(m, ceil(5N/12)); * = m binds\n")
    print("| N | m = 1 | m = 2 | m = 3 |\n|---|---|---|---|")
    for N in range(1, 13):
        print(f"| {N} | " + " | ".join(f"{k_eff(N, m)}{'*' if binds(N, m) else ''}" for m in (1, 2, 3)) + " |")
    print("\nm binds for N in: " + "; ".join(f"m = {m}: {[N for N in range(1, 21) if binds(N, m)] or 'none'}" for m in (1, 2, 3)))
    print("\n## Device types able to have an admitted fact (h >= m), by h_d histogram variant\n")
    print("| variant | types | m = 1 | m = 2 | m = 3 |\n|---|---|---|---|---|")
    for name, hs in hist.items():
        print(f"| {name} | {sum(hs.values())} | " + " | ".join(str(types_able(hs, m)) for m in (1, 2, 3)) + " |")
    print("\n## B. Smallest K admitted by the score alone (m = 1), K_min(h, rho); r = 5/7\n")
    rhos = (1, 2, 5, 10, 100, 1000, 10**6)
    print("| h | " + " | ".join(f"rho = {r}" for r in rhos) + " | 5h/7 |\n|---|" + "---|" * (len(rhos) + 1))
    for h in (1, 2, 3, 5, 7, 10, 14, 20):
        print(f"| {h} | " + " | ".join(str(k_min(h, r)) for r in rhos) + f" | {float(F(5, 7) * h):.2f} |")
    print("\nMargin to the supremum, beta*0.3/(1 + rho): " + "; ".join(f"rho = {r}: {float(margin_to_sup(r)):.5f}" for r in rhos))


if __name__ == "__main__":
    main()
