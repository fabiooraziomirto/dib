#!/usr/bin/env python3
"""Probabilistic reading of the breadth-share assumption f_s (Criterion 1).

Hypotheses (declared before running, per repo CLAUDE.md):
 H1. Each of N sites hosting device type d is adversarial independently
     with probability q (A1: a site that hosts a compromised device of type d
     and reports its real malicious flows; A2: a colluding contributor).
 H2. The guard (alpha, theta, beta=1-alpha) rejects adversary-only evidence
     iff the adversarial breadth share K/N is STRICTLY below
     f* = 1 - (1-theta)/alpha  (Criterion 1; supremum never attained while an
     honest observer exists, so equality at f* is also rejected -- see
     analysis_fs/REPORT.md, H3).  Counting form: K/N < f*  <=>  K < 5h/7 for
     (alpha,theta)=(0.6,0.65) with h=N-K honest sites.
 H3. Device-level prevalence p -> site-level q = 1-(1-p)^n for n devices of
     type d per site (independence across devices; n=1 gives q=p).
Output: P(violation) = P(Binomial(N,q) >= ceil(f* N)), exact via Fraction
arithmetic on the threshold (no float ties).
Falsifier: if sites are positively correlated (shared firmware / vendor
cloud) the independent-binomial figure UNDERestimates the tail.
"""
import csv, sys
from fractions import Fraction
from math import comb, ceil

ALPHA, THETA = Fraction(6, 10), Fraction(65, 100)
FSTAR = 1 - (1 - THETA) / ALPHA            # = 5/12

def kmin(N):
    """smallest K with K/N >= f* (guard fails)."""
    return ceil(FSTAR * N)

def p_violate(N, q):
    k0 = kmin(N)
    return sum(comb(N, k) * q**k * (1 - q)**(N - k) for k in range(k0, N + 1))

def main(out):
    rows = []
    for N in (5, 10, 20, 50, 100):
        for q in (0.01, 0.05, 0.10, 0.20, 0.30):
            rows.append(dict(N=N, q=q, kmin=kmin(N),
                             f_star=float(FSTAR),
                             p_violation=p_violate(N, q)))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    # device-to-site mapping table (H3)
    print("site-level q = 1-(1-p)^n")
    for p in (0.01, 0.05, 0.10, 0.2825):
        print(p, [round(1 - (1 - p)**n, 3) for n in (1, 2, 4, 8)])
    print("f* =", FSTAR, float(FSTAR))
    for r in rows:
        print(r["N"], r["q"], r["kmin"], f'{r["p_violation"]:.2e}')

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fs_binomial.csv")
