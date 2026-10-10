"""Passo 3: mitigation OPTIONS, evaluated only (no change to code/src).

Run: PYTHONPATH=code/src python3 analysis_fs/mitigations.py   (~2 min)

`score_variant` re-implements DIBScorer's raw-breadth, graph-free scoring
(dib.py:186-308 with gamma=0, trust off) and adds two optional knobs:
  tenure_days T  (a) sites whose first-seen date is < T days before as_of are
                 excluded from the temporal aggregates (days, counts), but still
                 count in ES_d / S_de, as dib.py:195-205 does. first_seen is
                 taken either from observation timestamps (what dib.py:166-173
                 does) or from a supplied registration date (what the comment
                 at dib.py:107-110 assumes but the code does not do).
  cap c          (b) each site contributes at most c rows to n_de, and n_d is the
                 sum of the capped n_de of the type. Day coverage is NOT capped
                 (interpretation chosen here: cap on volume only).
Base case (no knobs) must equal DIBScorer exactly; `check_equivalence` asserts it
on the UNSW seed-42 partition.

Hypotheses (stated before running):
  M1 base re-implementation == DIBScorer on every scored key (score, accepted).
  M2 tenure, timestamp-based: no protection against the worst-case adversary,
     because covering every day of D_d makes its first-seen date old (forgeable).
  M3 tenure, registration-based: newcomers get C_t = 0, sup = alpha*share < theta
     for every share < 1 (alpha=0.6 < theta=0.65); insiders unchanged (5/12).
  M4 cap c: worst case over data, fr_fake <= k*c/(k*c+h) (each honest site has
     >= 1 row), so sup = alpha f + beta(0.7 + 0.3 * f c/(f c + 1 - f)); tau rises
     from 5/12 to ~0.514 at c=1 and tends back to 5/12 as c grows. On UNSW data
     (large honest volume) the flood term is almost removed (sup ~ alpha f + 0.28).
  Data note: 5 rows dated 1970-1990 are dropped before everything (see main()).
  M5 recall cost on UNSW: tenure removes everything once T exceeds the capture
     span (all pseudo-sites share one first-seen date); cap changes few facts.
"""
from __future__ import annotations

import argparse
import csv
import multiprocessing
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

from dib.core.io import read_observations_csv
from dib.core.models import Observation
from dib.evaluation.dib import ELIGIBLE_CLASSES, DIBScorer, ScoringConfig
from dib.evaluation.intent_overlap import classify_core
from dib.simulator.sites import partition_observations

DATA = Path("/root/Desktop/DIB/data/processed/observations_enriched_item1fixed.csv")
OUT = Path(__file__).resolve().parent / "out"
ALPHA, BETA, THETA, M = 0.6, 0.4, 0.65, 2
BASE = ScoringConfig(alpha=ALPHA, beta=BETA, gamma=0.0, theta=THETA, min_reporting_sites=M,
                     graph_enabled=False, trust_weighted=False)
FAKE = "evil-c2.net"


def score_variant(observations: list[Observation], *, cap: int | None = None, tenure_days: int | None = None,
                  registration: dict[str, date] | None = None) -> dict[tuple, dict]:
    quarantined: set[str] = set()
    if tenure_days is not None:
        first_seen: dict[str, date] = {}
        as_of = max(o.timestamp.date() for o in observations)
        for o in observations:
            d = o.timestamp.date()
            if o.site_id not in first_seen or d < first_seen[o.site_id]:
                first_seen[o.site_id] = d
        if registration:
            first_seen.update(registration)
        quarantined = {s for s, fs in first_seen.items() if (as_of - fs).days < tenure_days}
    sites_by_device: dict[str, set[str]] = defaultdict(set)
    sites_by_key: dict[tuple, set[str]] = defaultdict(set)
    days_by_key: dict[tuple, set[date]] = defaultdict(set)
    days_by_device: dict[str, set[date]] = defaultdict(set)
    site_key_count: Counter = Counter()
    for o in observations:
        key = o.endpoint_key
        sites_by_device[o.device_type].add(o.site_id)
        sites_by_key[key].add(o.site_id)
        if o.site_id in quarantined:
            continue
        days_by_key[key].add(o.timestamp.date())
        days_by_device[o.device_type].add(o.timestamp.date())
        site_key_count[(o.site_id, key)] += 1
    counts: Counter = Counter()
    counts_by_device: Counter = Counter()
    for (site, key), c in site_key_count.items():
        c = min(c, cap) if cap is not None else c
        counts[key] += c
        counts_by_device[key[0]] += c
    out = {}
    for key in sorted(sites_by_key):
        d, endpoint, protocol, port = key
        sc = len(sites_by_key[key]) / len(sites_by_device[d])
        adr = len(days_by_key[key]) / max(len(days_by_device[d]), 1)
        fr = counts[key] / max(counts_by_device[d], 1)
        tc = min(1.0, 0.7 * adr + 0.3 * fr)
        score = ALPHA * sc + BETA * tc
        cls = classify_core(endpoint, protocol, port)
        out[key] = {"score": score, "site_confidence": sc, "temporal_confidence": tc,
                    "accepted": len(sites_by_key[key]) >= M and cls in ELIGIBLE_CLASSES and score >= THETA}
    return out


def check_equivalence(observations: list[Observation]) -> int:
    mine = score_variant(observations)
    ref = DIBScorer(BASE).score(observations)
    assert len(ref) == len(mine)
    for s in ref:
        m = mine[s.endpoint_key]
        assert abs(m["score"] - s.score) < 1e-12 and m["accepted"] == s.accepted, s.endpoint_key
    return len(ref)


def tau_cap_worst(c: int) -> float:
    """Largest share f with sup score < theta, worst case over data (honest volume h rows)."""
    lo, hi = 0.0, 1.0
    for _ in range(80):
        f = (lo + hi) / 2
        fr = f * c / (f * c + 1 - f)
        if ALPHA * f + BETA * (0.7 + 0.3 * fr) < THETA:
            lo = f
        else:
            hi = f
    return lo


def worst_case_rows(observations: list[Observation], *, share_k: dict[str, int], newcomer: bool,
                    flood_per_day: int) -> list[Observation]:
    """Per type: k adversaries (newcomers or the first k ES_d members) report FAKE
    on every day of D_d, flood_per_day rows per day each, timestamps at noon."""
    es: dict[str, set[str]] = defaultdict(set)
    days: dict[str, set[date]] = defaultdict(set)
    for o in observations:
        es[o.device_type].add(o.site_id)
        days[o.device_type].add(o.timestamp.date())
    fakes = []
    for d, k in share_k.items():
        adv = [f"newcomer{j}" for j in range(k)] if newcomer else sorted(es[d])[:k]
        for s in adv:
            for day in sorted(days[d]):
                ob = Observation(site_id=s, device_id=None, device_type=d, fqdn=FAKE, remote_ip=None,
                                 protocol="https", port=443,
                                 timestamp=datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc),
                                 source_dataset="mitigation", evidence_type="fabricated")
                fakes += [ob] * flood_per_day
    return fakes


_POPS: dict[str, list[Observation]] = {}


def _admitted(task: tuple[str, dict]) -> set[tuple]:
    pop, kw = task
    return {k for k, x in score_variant(_POPS[pop], **kw).items() if x["accepted"]}


def _fake_stats(task: tuple[str, dict, tuple]) -> dict:
    pop, kw, full = task
    v = score_variant(_POPS[pop], **kw)
    fk = [x for key, x in v.items() if key[1] == FAKE and key[0] in full]
    return {"types": len(fk), "max_fake_score": round(max(x["score"] for x in fk), 6),
            "max_fake_ct": round(max(x["temporal_confidence"] for x in fk), 6),
            "types_admitted": sum(x["accepted"] for x in fk)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=2, help="processes over variants (fork, data shared copy-on-write)")
    a = p.parse_args()
    OUT.mkdir(exist_ok=True)
    t0 = time.monotonic()
    # 5 of 1,268,020 rows carry 1970-1990 timestamps (data artefact found while
    # running this script); they would set every tenure first-seen to 1970, so
    # they are dropped here, for base and variants alike.
    obs = [o for o in read_observations_csv(DATA) if (o.fqdn or o.remote_ip) and o.timestamp.year >= 2000]
    sites = partition_observations(obs, 10, strategy="random", seed=42)
    part = [o for s in sites for o in s.observations]
    print(f"loaded+partitioned {len(part)} in {time.monotonic() - t0:.0f}s", flush=True)
    print("M1 equivalence, keys checked:", check_equivalence(part), f"({time.monotonic() - t0:.0f}s)", flush=True)
    span = (max(o.timestamp.date() for o in part) - min(o.timestamp.date() for o in part)).days
    _POPS["part"] = part
    labels = ([("base", "", {})] + [("tenure(timestamp first-seen)", f"T={T}", {"tenure_days": T})
                                    for T in (1, 7, 30, 90, span, span + 1)]
              + [("cap per site per (d,e)", f"c={c}", {"cap": c}) for c in (1, 10, 100, 1000)])
    with multiprocessing.get_context("fork").Pool(a.workers) as pool:
        admitted_sets = pool.map(_admitted, [("part", kw) for _, _, kw in labels])
    base_admitted = admitted_sets[0]
    rows = [{"option": opt, "param": param, "admitted": len(adm), "lost": len(base_admitted - adm),
             "gained": len(adm - base_admitted), "capture_span_days": span}
            for (opt, param, _), adm in zip(labels, admitted_sets)]
    with (OUT / "mitigation_recall_cost.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r, flush=True)

    # Adversary sup on UNSW, full-coverage types: insider k=5 of 10 (share 0.5),
    # H2 newcomers k=8 vs h=10 (share 0.444); flood 200 rows per day per site.
    es = defaultdict(set)
    for o in part:
        es[o.device_type].add(o.site_id)
    full = sorted(d for d, s in es.items() if len(s) == 10)
    as_of = max(o.timestamp.date() for o in part)
    tasks, labels = [], []
    for label, newcomer, k in (("insider k=5/10", False, 5), ("H2 newcomers k=8, h=10", True, 8),
                               ("insider k=3/10 (f_s)", False, 3)):
        fakes = worst_case_rows(part, share_k={d: k for d in full}, newcomer=newcomer, flood_per_day=200)
        _POPS[label] = part + fakes
        reg = {f"newcomer{j}": as_of for j in range(k)} if newcomer else None
        variants = [("none", {}), ("tenure T=7, timestamp first-seen", {"tenure_days": 7}),
                    ("tenure T=7, registration first-seen", {"tenure_days": 7, "registration": reg or {}}),
                    ("cap c=1", {"cap": 1}), ("cap c=10", {"cap": 10}), ("cap c=100", {"cap": 100})]
        for name, kw in variants:
            tasks.append((label, kw, tuple(full)))
            labels.append((label, name))
    with multiprocessing.get_context("fork").Pool(a.workers) as pool:
        stats = pool.map(_fake_stats, tasks)
    sup_rows = [{"adversary": label, "option": name, **st} for (label, name), st in zip(labels, stats)]
    for r in sup_rows:
        print(r, flush=True)
    with (OUT / "mitigation_adversary_sup.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sup_rows[0]))
        w.writeheader()
        w.writerows(sup_rows)
    taus = [{"option": "none", "tau": float(1 - Fraction(35, 100) / Fraction(6, 10))}]
    taus += [{"option": f"cap c={c} (worst case over data)", "tau": round(tau_cap_worst(c), 4)} for c in (1, 2, 5, 10, 100, 1000)]
    taus += [{"option": "tenure, registration-based, newcomer adversary", "tau": "none admissible (alpha<theta)"},
             {"option": "tenure, any mode, established insider", "tau": float(1 - Fraction(35, 100) / Fraction(6, 10))}]
    with (OUT / "mitigation_tau.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["option", "tau"])
        w.writeheader()
        w.writerows(taus)
    for t in taus:
        print(t)
    print(f"total {time.monotonic() - t0:.0f}s")


if __name__ == "__main__":
    main()
