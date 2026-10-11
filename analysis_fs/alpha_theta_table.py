"""Descriptive (alpha, theta) table (audit 42). Exact arithmetic with Fraction; recall/precision are READ from
results/sensitivity/*.csv (not recomputed); pairs not covered by a sweep are 'non disponibile'.

Usage (repo root): python3 analysis_fs/alpha_theta_table.py [--csv-dir results/sensitivity]
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction as F
from pathlib import Path

PAIRS = [(F(6, 10), F(65, 100)), (F(7, 10), F(65, 100)), (F(6, 10), F(7, 10)), (F(55, 100), F(6, 10))]
F_S = F(3, 10)
NA = "non disponibile"
CORPORA = ("moniotr", "yourthings")


def fstar(a: F, th: F) -> F:
    return (th - (1 - a)) / a


def ratio(a: F, th: F) -> F:
    return (th + a - 1) / (1 - th)


def margin(a: F, th: F) -> F:
    return fstar(a, th) - F_S


def satisfies_criterion(a: F, th: F) -> bool:
    """Criterion with f_s = 0.30: f* must exceed f_s (positive margin)."""
    return margin(a, th) > 0


def coverage(a: F, th: F) -> tuple:
    """Which sweeps of results/sensitivity contain the pair (alpha_sweep: theta = 0.65, theta_sweep: alpha = 0.6)."""
    out = []
    grid_a = {F(4, 10) + F(5, 100) * i for i in range(11)}
    grid_t = {F(5, 10) + F(25, 1000) * i for i in range(13)}
    if th == F(65, 100) and a in grid_a:
        out.append("alpha_sweep")
    if a == F(6, 10) and th in grid_t:
        out.append("theta_sweep")
    return tuple(out)


def _fr(x: str) -> F:
    return F(x).limit_denominator(10**6)


def _read(path: Path) -> list:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def build_rows(csv_dir: Path) -> list:
    rows = []
    for corpus in CORPORA:
        sweeps = {"alpha_sweep": _read(csv_dir / f"{corpus}_alpha_sweep.csv"),
                  "theta_sweep": _read(csv_dir / f"{corpus}_theta_sweep.csv")}
        for a, th in PAIRS:
            base = {"corpus": corpus, "alpha": a, "theta": th, "fstar": fstar(a, th), "r": ratio(a, th),
                    "margin": margin(a, th), "criterion_ok": satisfies_criterion(a, th)}
            cov = coverage(a, th)
            if not cov:
                rows.append({**base, "source": "-", "admitted": NA, "precision": NA, "recall": NA, "f1": NA})
            for src in cov:
                hit = [x for x in sweeps[src] if _fr(x["alpha"]) == a and _fr(x["theta"]) == th]
                assert len(hit) == 1, (corpus, src, a, th, len(hit))
                h = hit[0]
                rows.append({**base, "source": src, "admitted": h["admitted_endpoint_count"],
                             "precision": h["precision"], "recall": h["recall"], "f1": h["f1"]})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", default="results/sensitivity")
    a = ap.parse_args()
    print("| corpus | alpha | theta | f* | r | f*-0.30 | Criterion f_s=0.30 | sweep | admitted | precision | recall | f1 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for x in build_rows(Path(a.csv_dir)):
        print(f"| {x['corpus']} | {float(x['alpha'])} | {float(x['theta'])} | {x['fstar']} | {x['r']} | {x['margin']} | "
              f"{'si' if x['criterion_ok'] else 'NO'} | {x['source']} | {x['admitted']} | {x['precision']} | {x['recall']} | {x['f1']} |")


if __name__ == "__main__":
    main()
