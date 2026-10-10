"""Point 5: probability that the per-device adversarial share breaks Criterion 1.

Run: python3 analysis_fs/finite_n.py   (exact arithmetic, < 1 s)
Output: analysis_fs/out/finite_n.csv

Two models, both for one device type d whose eligible population has n sites:
  binomial      each of the n sites is adversarial iid with probability p
  hypergeom     k = p*N adversaries fixed among N consortium sites; d is
                observed by n of them, chosen independently of adversary status
                (so K_d ~ Hypergeom(N, k, n)). Excludes H2 (adversaries
                claiming d), under which K_d = k deterministically.

Events (K = adversaries in ES_d):
  exceeds_fs     K/n > 0.30            (declared assumption violated)
  bound_unsafe   K/n >= 5/12           (Criterion 1 gives no guarantee; tie included)
  admissible     K >= 2 and K/n > 5/12 (adversary-only fact can actually be staged
                                        given enough persistence/flood; m=2 quorum;
                                        tie excluded because sup is not attained, H3)
Hypothesis (stated before running): for n = N the probabilities are small at
p=0.1 and grow quickly with p for small N; for small n (2-4 sites, the
common case in the independent-deployment corpora) they are large even at p=0.1.
"""
from __future__ import annotations

import csv
from fractions import Fraction
from math import comb
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
FS = Fraction(3, 10)
LIM = Fraction(5, 12)


def events(K: int, n: int) -> tuple[bool, bool, bool]:
    s = Fraction(K, n)
    return s > FS, s >= LIM, (K >= 2 and s > LIM)


def binom(n: int, p: Fraction) -> list[Fraction]:
    return [comb(n, K) * p**K * (1 - p) ** (n - K) for K in range(n + 1)]


def hyper(N: int, k: int, n: int) -> list[Fraction]:
    tot = comb(N, n)
    return [Fraction(comb(k, K) * comb(N - k, n - K), tot) if K <= k and n - K <= N - k else Fraction(0)
            for K in range(n + 1)]


def probs(pmf: list[Fraction], n: int) -> tuple[float, float, float]:
    acc = [Fraction(0)] * 3
    for K, pk in enumerate(pmf):
        for i, e in enumerate(events(K, n)):
            if e:
                acc[i] += pk
    return tuple(float(x) for x in acc)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows = []
    ps = [Fraction(1, 10), Fraction(2, 10), Fraction(3, 10)]
    for N in (10, 20, 50, 100):
        for p in ps:
            for n in sorted({2, 3, 4, 6, 10, N // 2, N}):
                if n > N:
                    continue
                b = probs(binom(n, p), n)
                k = int(p * N)
                h = probs(hyper(N, k, n), n)
                rows.append({"N": N, "p": float(p), "n_ES_d": n, "k_fixed": k,
                             "binom_exceeds_fs": b[0], "binom_bound_unsafe": b[1], "binom_admissible": b[2],
                             "hyper_exceeds_fs": h[0], "hyper_bound_unsafe": h[1], "hyper_admissible": h[2]})
    with (OUT / "finite_n.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        if r["n_ES_d"] in (2, 4, r["N"]):
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


if __name__ == "__main__":
    main()
