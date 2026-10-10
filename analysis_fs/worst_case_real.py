"""Passo 2: worst-case bounded adversary on real UNSW data, scored by DIBScorer.

Run: PYTHONPATH=code/src python3 analysis_fs/worst_case_real.py   (~2 min)
Corpus: UNSW 10 pseudo-sites (observations_enriched_item1fixed.csv, sha256
4de5423c...), partition_observations(strategy="random", seed) for seeds 0-4.
The three-lab setup has N=3 < 6 and is reported only through k_tol
(out/hd_by_device.csv), as requested.

Adversary strategy, per device type d: the k malicious sites report the fake
fact (evil-c2.net, https/443, eligible as vendor-cloud) on EVERY day of D_d,
with total volume rho times the honest volume n_d of the type,
rho in {1, 2, 5, 10, 20, 50, 100} (1000 dropped: ~10^8 rows per seed,
over the time budget). The 5 rows dated 1970-1990 are kept, as in a2_raw_k.py;
the adversary simply also covers those days.
Levels per type:
  insider  k sites taken from ES_d (share k/|ES_d|):
           k_fs  = floor(0.30*|ES_d|), k_tol = largest k with k/|ES_d| < 5/12,
           k_tol+1.
  H2       k NEW site ids that never observed d (share k/(k+h_d), h_d=|ES_d|):
           k_fs = largest k with k/(k+h_d) <= 0.30, k_tol, k_tol+1.

Scoring population (exactness argument, [D] verified by `validate_full`):
with gamma=0 and no trust weighting, the fake fact's score depends only on
ES_d, D_d, its own supporters/days, and n_fake/(n_d+n_fake) (dib.py:255-279);
honest rows of other types do not enter. Rows for ρ=100 on the full corpus
would be ~10^8, so the scored population keeps, for type d, one honest row
per (site, day) present in d (R_d rows: ES_d and D_d unchanged) and adds
ceil(rho*R_d/(k*|D_d|)) fake rows per (adversary, day), so the realised
volume ratio is >= rho. `validate_full` scores the FULL honest population at
rho=1 with the same rule and checks every type against the closed form at its
realised ratio, as the reduced runs are; agreement in both means the
reduction changes nothing but the count scale.

Hypotheses (stated before running):
  W1 at k_tol (both variants) no admission for any rho (sup < theta);
  W2 at k_tol+1 admission once rho >= rho* (closed form), when k_tol+1 >= 2;
  W3 H2 has the same share arithmetic but needs no observation of d by the
     adversary; it reaches admission on every type with h_d >= 2;
  W4 at k_fs (insider, |ES_d|=10, k=3) the maximum score over rho approaches
     the bound 0.58, so the paper's "0.562 is the largest score at f_s=0.30"
     (paper:631) is a property of the tested strategy, not of the bound.
"""
from __future__ import annotations

import csv
import math
import random
import time
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from dib.core.io import read_observations_csv
from dib.core.models import Observation
from dib.evaluation.dib import DIBScorer, ScoringConfig
from dib.simulator.sites import partition_observations

DATA = Path("/root/Desktop/DIB/data/processed/observations_enriched_item1fixed.csv")
OUT = Path(__file__).resolve().parent / "out"
FAKE = "evil-c2.net"
CONFIG = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2,
                       graph_enabled=False, trust_weighted=False)
RHOS = [1, 2, 5, 10, 20, 50, 100]
LIM, FS = Fraction(5, 12), Fraction(3, 10)


def k_tol_insider(n: int) -> int:
    return max(k for k in range(n + 1) if Fraction(k, n) < LIM)


def k_fs_insider(n: int) -> int:
    return max(k for k in range(n + 1) if Fraction(k, n) <= FS)


def k_tol_h2(h: int) -> int:
    return max(k for k in range(0, 10 * h + 1) if Fraction(k, k + h) < LIM)


def k_fs_h2(h: int) -> int:
    return max(k for k in range(0, 10 * h + 1) if Fraction(k, k + h) <= FS)


def rho_star(share: Fraction) -> float:
    """Smallest volume ratio for admission with full day coverage (closed form)."""
    x = ((Fraction(65, 100) - Fraction(3, 5) * share) / Fraction(2, 5) - Fraction(7, 10)) / Fraction(3, 10)
    if x <= 0:
        return 0.0
    if x >= 1:
        return math.inf
    return float(x / (1 - x))


def closed_form(share: Fraction, ratio: Fraction) -> float:
    if share == 1:
        return 1.0
    return float(Fraction(3, 5) * share + Fraction(2, 5) * (Fraction(7, 10) + Fraction(3, 10) * ratio / (1 + ratio)))


def stats(observations: list[Observation]):
    es: dict[str, set[str]] = defaultdict(set)
    site_days: dict[str, set[tuple[str, object]]] = defaultdict(set)
    n: dict[str, int] = defaultdict(int)
    rep: dict[tuple[str, str, object], Observation] = {}
    for o in observations:
        if not (o.fqdn or o.remote_ip):
            continue
        d = o.device_type
        day = o.timestamp.date()
        es[d].add(o.site_id)
        site_days[d].add((o.site_id, day))
        n[d] += 1
        rep.setdefault((d, o.site_id, day), o)
    return es, site_days, n, rep


def fake_rows(device: str, adversaries: list[str], days: list, per_cell: int) -> list[Observation]:
    rows = []
    for site in adversaries:
        for day in days:
            ob = Observation(site_id=site, device_id=None, device_type=device, fqdn=FAKE, remote_ip=None,
                             protocol="https", port=443,
                             timestamp=datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc),
                             source_dataset="worst_case", evidence_type="fabricated")
            rows += [ob] * per_cell  # same object repeated: DIBScorer counts list items
    return rows


def score_fake(honest: list[Observation], fakes: list[Observation], device: str):
    return next(s for s in DIBScorer(CONFIG).score(honest + fakes, target_device_type=device) if s.endpoint == FAKE)


def run_seed(obs: list[Observation], seed: int) -> list[dict]:
    sites = partition_observations(obs, 10, strategy="random", seed=seed)
    part = [o for s in sites for o in s.observations]
    es, site_days, n, rep = stats(part)
    rows = []
    for device in sorted(es):
        members = sorted(es[device])
        days = sorted({day for _, day in site_days[device]})
        honest = [rep[(device, s, day)] for (s, day) in sorted(site_days[device])]
        R = len(honest)
        N = len(members)
        h = N
        levels = [("insider", "k_fs", k_fs_insider(N)), ("insider", "k_tol", k_tol_insider(N)),
                  ("insider", "k_tol+1", k_tol_insider(N) + 1),
                  ("H2", "k_fs", k_fs_h2(h)), ("H2", "k_tol", k_tol_h2(h)), ("H2", "k_tol+1", k_tol_h2(h) + 1)]
        rng = random.Random(f"{seed}:{device}")
        order = rng.sample(members, N)
        for variant, level, k in levels:
            if k == 0 or (variant == "insider" and k > N):
                continue
            adv = order[:k] if variant == "insider" else [f"newcomer{j}" for j in range(k)]
            share = Fraction(k, N) if variant == "insider" else Fraction(k, k + h)
            first_admit = None
            best = 0.0
            for rho in RHOS:
                per_cell = math.ceil(rho * R / (k * len(days)))
                fakes = fake_rows(device, adv, days, per_cell)
                s = score_fake(honest, fakes, device)
                realised = Fraction(len(fakes), R)
                assert abs(s.score - closed_form(share, realised)) < 1e-9, (device, k, rho)
                best = max(best, s.score)
                if s.accepted and first_admit is None:
                    first_admit = rho
                rows.append({"seed": seed, "device_type": device, "variant": variant, "level": level, "k": k,
                             "ES_d_honest_before": N, "share": round(float(share), 6), "rho": rho,
                             "rho_realised": round(float(realised), 4), "days": len(days), "n_d_honest": n[device],
                             "site_confidence": round(s.site_confidence, 6),
                             "temporal_confidence": round(s.temporal_confidence, 6),
                             "score": round(s.score, 6), "bound": round(float(Fraction(3, 5) * share + Fraction(2, 5)), 6)
                             if share < 1 else 1.0,
                             "rho_star_closed_form": rho_star(share), "admitted": s.accepted})
    return rows


def validate_full(obs: list[Observation], seed: int = 0, rho: int = 1) -> int:
    """Full honest population (every row, all types in one DIBScorer call) at
    rho=1, insider k_tol+1; check each type's fake score against the closed
    form at its realised ratio. Returns the number of types checked."""
    sites = partition_observations(obs, 10, strategy="random", seed=seed)
    part = [o for s in sites for o in s.observations if o.fqdn or o.remote_ip]
    es, site_days, n, _ = stats(part)
    fakes, expected = [], {}
    for device in sorted(es):
        N = len(es[device])
        k = k_tol_insider(N) + 1
        if k > N:
            continue
        days = sorted({day for _, day in site_days[device]})
        adv = random.Random(f"{seed}:{device}").sample(sorted(es[device]), N)[:k]
        per_cell = math.ceil(rho * n[device] / (k * len(days)))
        fakes += fake_rows(device, adv, days, per_cell)
        expected[device] = closed_form(Fraction(k, N), Fraction(per_cell * k * len(days), n[device]))
    got = {s.device_type: s.score for s in DIBScorer(CONFIG).score(part + fakes) if s.endpoint == FAKE}
    for device, value in expected.items():
        assert abs(got[device] - value) < 1e-9, (device, got[device], value)
    return len(expected)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    t0 = time.monotonic()
    obs = list(read_observations_csv(DATA))
    print(f"loaded {len(obs)} in {time.monotonic() - t0:.0f}s", flush=True)
    print("full-population validation, types checked:", validate_full(obs), f"({time.monotonic() - t0:.0f}s)", flush=True)
    rows = []
    for seed in range(5):
        rows += run_seed(obs, seed)
        print(f"seed {seed} done ({time.monotonic() - t0:.0f}s)", flush=True)
    with (OUT / "worst_case_real.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = []
    groups = defaultdict(list)
    for r in rows:
        cov = "ES_d=10" if r["ES_d_honest_before"] == 10 else "ES_d<10"
        groups[(r["variant"], r["level"], cov)].append(r)
    for (variant, level, cov), rs in sorted(groups.items()):
        cells = defaultdict(list)
        for r in rs:
            cells[(r["seed"], r["device_type"])].append(r)
        admitted_cells = [c for c in cells.values() if any(x["admitted"] for x in c)]
        min_rho = [min(x["rho"] for x in c if x["admitted"]) for c in admitted_cells]
        summary.append({"variant": variant, "level": level, "coverage": cov, "cells(type x seed)": len(cells),
                        "k_values": "/".join(map(str, sorted({r["k"] for r in rs}))),
                        "shares": "/".join(f"{s:.3f}" for s in sorted({r["share"] for r in rs})),
                        "max_score": max(r["score"] for r in rs),
                        "max_bound": max(r["bound"] for r in rs),
                        "min_gap_bound_minus_score": round(min(r["bound"] - r["score"] for r in rs), 6),
                        "cells_admitted": len(admitted_cells),
                        "min_rho_admission": min(min_rho) if min_rho else None,
                        "max_rho_admission": max(min_rho) if min_rho else None,
                        "rho_star_range": "/".join(f"{x:.2f}" for x in sorted({r["rho_star_closed_form"] for r in rs}))})
    with (OUT / "worst_case_real_summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    for s in summary:
        print(s)
    print(f"total {time.monotonic() - t0:.0f}s")


if __name__ == "__main__":
    main()
