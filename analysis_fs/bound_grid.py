"""Point 3: Criterion 1 bound vs worst-case adversary, analytic and via DIBScorer.

Run from repo root:  PYTHONPATH=code/src python3 analysis_fs/bound_grid.py
Outputs (analysis_fs/out/):
  bound_grid_analytic.csv  per (N, alpha, theta): k_max tolerated by the bound,
                           and k_max actually tolerated at finite flood ratio rho
  bound_grid_empirical.csv per (N, k, alpha): DIBScorer score, analytic bound,
                           analytic score at the realised rho, admitted flag
  kmax_by_N.csv            alpha=0.6, theta=0.65 summary per N

Hypothesis (stated before running): with every honest site in ES_d holding
>=1 observation of d, the adversary's best strategy (all k report, cover every
day of D_d, flood volume by ratio rho = n_adv/n_honest) gives
    score(rho) = alpha*k/N + beta*(0.7 + 0.3*rho/(1+rho))  <  alpha*k/N + beta
so DIBScorer never exceeds the bound, the bound is a supremum (never attained
for k<N), and the bound's k_max = ceil(N*(1-(1-theta)/alpha)) - 1.
"""
from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

from dib.core.models import Observation
from dib.evaluation.dib import DIBScorer, ScoringConfig

OUT = Path(__file__).resolve().parent / "out"
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
ALPHAS = [Fraction(x, 100) for x in range(50, 95, 5)]
THETAS = [Fraction(x, 100) for x in range(55, 85, 5)]
RHOS = [1, 10, 100, 10**6]
M_QUORUM = 2


def sup_score(alpha: Fraction, k: int, n: int) -> Fraction:
    if k == n:
        return Fraction(1)
    return alpha * Fraction(k, n) + (1 - alpha)


def score_at_rho(alpha: Fraction, k: int, n: int, rho: int) -> Fraction:
    if k == n:
        return Fraction(1)
    return alpha * Fraction(k, n) + (1 - alpha) * (Fraction(7, 10) + Fraction(3, 10) * Fraction(rho, rho + 1))


def kmax(n: int, admitted) -> int:
    """Largest k such that every k' in [0, k] is rejected (quorum included)."""
    best = -1
    for k in range(0, n + 1):
        if k >= M_QUORUM and admitted(k):
            break
        best = k
    return best


def analytic() -> list[dict]:
    rows = []
    for n in range(4, 51):
        for a in ALPHAS:
            for t in THETAS:
                row = {"N": n, "alpha": float(a), "theta": float(t),
                       "f_limit": float(1 - (1 - t) / a) if a > 0 else None,
                       "kmax_bound": kmax(n, lambda k: sup_score(a, k, n) >= t)}
                for rho in RHOS:
                    row[f"kmax_rho{rho}"] = kmax(n, lambda k, rho=rho: score_at_rho(a, k, n, rho) >= t)
                rows.append(row)
    return rows


def population(n: int, k: int, rho: int) -> list[Observation]:
    """One day (so day coverage is 1 by construction); each honest site one
    legit observation; adversaries jointly submit rho * h fake observations."""
    h = n - k
    def ob(site, fqdn, sec):
        return Observation(site_id=site, device_id=None, device_type="d", fqdn=fqdn, remote_ip=None,
                           protocol="https", port=443, timestamp=T0 + timedelta(seconds=sec),
                           source_dataset="grid", evidence_type="flow")
    out = [ob(f"h{i}", "legit.example", 0) for i in range(h)]
    total = rho * h if h else k
    per = math.ceil(total / k)
    out += [ob(f"a{j}", "fake.example", s) for j in range(k) for s in range(per)]
    return out


def empirical() -> list[dict]:
    rows = []
    rho = 100
    for n in range(4, 51):
        for k in range(1, n + 1):
            obs = population(n, k, rho)
            h = n - k
            n_adv = sum(1 for o in obs if o.fqdn == "fake.example")
            for a in (Fraction(1, 2), Fraction(3, 5), Fraction(7, 10)):
                cfg = ScoringConfig(alpha=float(a), beta=float(1 - a), gamma=0.0, theta=0.65,
                                    min_reporting_sites=M_QUORUM, graph_enabled=False)
                s = next(x for x in DIBScorer(cfg).score(obs) if x.endpoint == "fake.example")
                bound = sup_score(a, k, n)
                realised = (a * Fraction(k, n) + (1 - a) * (Fraction(7, 10) + Fraction(3, 10) * Fraction(n_adv, n_adv + h))
                            if h else Fraction(1))
                rows.append({"N": n, "k": k, "alpha": float(a), "f": k / n, "rho_realised": n_adv / h if h else None,
                             "score_dibscorer": s.score, "score_analytic_realised": float(realised),
                             "bound": float(bound), "gap_bound_minus_score": float(bound) - s.score,
                             "exceeds_bound": s.score > float(bound) + 1e-12,
                             "matches_analytic": abs(s.score - float(realised)) < 1e-9,
                             "admitted": s.accepted})
    return rows


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    an = analytic()
    write(OUT / "bound_grid_analytic.csv", an)
    em = empirical()
    write(OUT / "bound_grid_empirical.csv", em)
    summary = []
    for n in range(4, 51):
        sel = [r for r in em if r["N"] == n and r["alpha"] == 0.6]
        row_an = next(r for r in an if r["N"] == n and r["alpha"] == 0.6 and r["theta"] == 0.65)
        k_emp = kmax(n, lambda k: next(r for r in sel if r["k"] == k)["admitted"])
        honest = [r for r in sel if r["k"] < n]
        summary.append({"N": n, "kmax_bound": row_an["kmax_bound"], "f_kmax_bound": row_an["kmax_bound"] / n,
                        "kmax_dibscorer_rho100": k_emp, "kmax_rho1e6_analytic": row_an["kmax_rho1000000"],
                        "kmax_at_fs030": math.floor(0.3 * n + 1e-9),
                        "min_gap_bound_minus_score": min(r["gap_bound_minus_score"] for r in honest),
                        "any_exceeds_bound": any(r["exceeds_bound"] for r in sel),
                        "all_match_analytic": all(r["matches_analytic"] for r in sel)})
    write(OUT / "kmax_by_N.csv", summary)
    print("violations (DIBScorer > bound):", sum(r["exceeds_bound"] for r in em), "of", len(em))
    print("mismatch vs analytic:", sum(not r["matches_analytic"] for r in em))
    diff = [r for r in an if r["kmax_bound"] != r["kmax_rho1000000"]]
    print("analytic cells where kmax_bound != kmax(rho=1e6):", len(diff), "of", len(an))
    for r in summary:
        if r["N"] in (4, 5, 6, 7, 10, 12, 20, 24, 30, 50):
            print(r)


if __name__ == "__main__":
    main()
