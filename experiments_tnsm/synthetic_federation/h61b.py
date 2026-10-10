"""H6-1b (plan rev. 5, Passo 6; audit 14 s.4, audit 16): DIB admission against ranked-union
baselines (volume, support; score as reference) under A2, on a synthetic federation anchored on real per-type behaviour.

Abstract line (to be reported verbatim with any result of this script):
  "La federazione sintetica (N >= 10 siti per tipo) e' piu' favorevole alla guardia della
   popolazione reale osservabile (piu' siti per tipo rendono piu' facile soddisfare
   Criterion 1), in cui la mediana di h_d e' 1 e i siti indipendenti sono al piu' 5
   (audit 11); i risultati mostrano il comportamento del meccanismo a scala, non quello
   atteso nelle federazioni misurate oggi."

Generator (assumptions are explicit parameters, all in the manifest)
--------------------------------------------------------------------
* Device types and benign behaviour: the 27 UNSW-IoTraffic types; per type, the top
  TOP_ENDPOINTS endpoint keys by observation count in the processed UNSW corpus
  (/root/Desktop/DIB/data/processed/observations_enriched.csv, sha256 in the manifest,
  aggregated once into a cache OUTSIDE the repo). Only the distribution over sites is
  synthetic.
* N sites; each site hosts type d with probability `presence` (anchored point: N_d drawn
  from experiments_tnsm/synthetic_federation/anchor_hd.json over 5 sites).
* Benign site of type d: endpoint of popularity rank r observed with probability r^-ZIPF_S
  (rank 1 always), on each of W days with probability 0.5 (>= 1 day), one observation per
  active day; plus LOCAL_DIVERGENCE * (#observed) site-unique legitimate endpoints.
* Adversary: each (site, type d) hosting pair is adversarial with probability q
  (independent), or beta-binomial with intra-class correlation rho_corr shared per type
  (vendor latent). Adversarial sites keep the benign behaviour (camouflage) and, in total
  collusion (principal A2 strategy), all report the same A2_FACTS fabricated vendor-cloud
  endpoints every day with FLOOD observations per day each. A2 endpoints are fresh (no
  honest support). n_avv per type and |S_e & Adv| per A2 fact are recorded BEFORE scoring.
* DIB = DIBScorer with configs/graph_free_unweighted_federation.yaml (alpha 0.6, beta 0.4,
  gamma 0, theta 0.65, m = 2, raw breadth); queue = accepted facts, B = |queue|.

Design change (2026-10-10, before launch, motivated by the pilot; audit 16 s.4)
-----------------------------------------------------------------------------
The first design ranked the union by DIB's own score at budget B. The pilot showed that
this cannot separate admission from ranking: with the same score an A2 fact reaches the
top B only when K/N > f*, i.e. when DIB admits it too, so differences came from the class
gate and from budget filling (one diagnostic replica had the opposite sign). The sign of
the hypothesis below is fixed from the reasoning that follows, NOT from the pilot outcome.

Baselines (the SAME class filter for all: only facts whose class is eligible,
dib.py:19, classify_core; the class filter is therefore NOT a contribution of admission,
and what is measured is the effect of quorum + score threshold net of the class filter):
  ranked-volume  rank by number of observations of the fact (what a flood maximizes);
  ranked-sites   rank by number of reporting sites |S_e| (pure support, no score);
  references (not in the falsification family): ranked-score (DIB score, the old
  union_ranked_budget.py:50-73 ordering), ranked-support-2 / -3 (|S_e| >= 2 / 3, then score).
Budgets: c * B with c in {1, 2, 5} (tests) and the curve c in {1, 1.5, 2, 3, 5, 10}
(descriptive). Expected A2 count in the top round(c*B) with ties in random order:
union_ranked_budget.budget_yield (:76-100). DIB presents its whole queue (B facts) at every c.

Hypothesis H6-1b (declared before running; does not change after launch)
-----------------------------------------------------------------------
Reasoning: the A2 adversaries flood their fabricated facts and all report them, so the
fabricated facts have the highest volume and, when K is large, a support comparable to
popular benign facts; neither volume nor support alone encodes the share K/N of the type's
reporting sites, which is what the score threshold bounds (Criterion 1). Hence, for every
q in the sweep (all below f* = 5/12):
  for baseline in {ranked-volume, ranked-sites} and c in {1, 2, 5}:
  the expected number of A2 facts in the baseline's top round(c*B) EXCEEDS the number of A2
  facts in DIB's queue.
* Unit: replica; 200 replicas per point; paired diff = A2_baseline(c) - A2_DIB (counts).
* Testable (point, baseline, c): >= 50 of 200 replicas with an A2 fact in DIB's queue or in
  the baseline prefix; others descriptive only.
* Test: one-sided Wilcoxon signed-rank (H0: median diff <= 0); bootstrap 95% CI for effect.
* Family: 170 points x 2 baselines x 3 budgets = up to 1020 tests; Holm, FWER 5%, over the
  testable ones.
* Falsified if Holm does not reject H0 for at least one testable (point, baseline, c).
  An outcome unfavourable to DIB is reported as a result.
* Partial outcomes reported by factor (baseline, c, rho_corr, N, presence, q); in
  particular whether the advantage disappears at large c ("ranking gets there by volume").
* References (ranked-score, ranked-support-m): same statistics, reported, not in the family.
Sweep (170 points): N in {10, 20, 50, 100} x presence in {0.2, 0.4, 0.6, 0.8} x q in
{0.01, 0.05, 0.1, 0.2, 0.3} x rho_corr in {0, 0.3}, plus the anchored point x q x rho_corr.
Zipf s = 1.0 and local divergence 5% fixed (their sensitivity is outside H6-1b).

Usage:
  run:     python3 h61b.py run --replicas 200 --seed 20261010 --workers 12 --out <dir> [--points ...]
  analyze: python3 h61b.py analyze <dir>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(ROOT / "code" / "scripts"))

from dib.core.models import Observation  # noqa: E402
from dib.evaluation.dib import ELIGIBLE_CLASSES, DIBScorer, ScoringConfig  # noqa: E402
from union_ranked_budget import budget_yield  # noqa: E402

UNSW_CSV = Path("/root/Desktop/DIB/data/processed/observations_enriched.csv")
CACHE = Path("/root/Desktop/DIB/outputs/tnsm_synth/unsw_type_profiles.json")  # outside the repo
ANCHOR = Path(__file__).resolve().parent / "anchor_hd.json"

TOP_ENDPOINTS = 30
ZIPF_S = 1.0
LOCAL_DIVERGENCE = 0.05
W_DAYS = 7
A2_FACTS = 3
FLOOD = 50
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
NS = (10, 20, 50, 100)
PRESENCES = (0.2, 0.4, 0.6, 0.8)
QS = (0.01, 0.05, 0.10, 0.20, 0.30)
RHOS = (0.0, 0.3)
FAMILY_BASELINES = ("ranked-volume", "ranked-sites")
REFERENCE_BASELINES = ("ranked-score", "ranked-support-2", "ranked-support-3")
BASELINES = FAMILY_BASELINES + REFERENCE_BASELINES
TEST_C = (1, 2, 5)
CURVE_C = (1, 1.5, 2, 3, 5, 10)
TESTABLE_MIN = 50
SCORING = dict(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2,
               graph_enabled=False, trust_weighted=False)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def type_profiles() -> dict:
    """Per-type top endpoint keys from the UNSW corpus, cached outside the repo."""
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    counts: dict[str, Counter] = defaultdict(Counter)
    with UNSW_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if not row["timestamp"].startswith("201"):   # spurious 1970 rows (audit 08 s.11)
                continue
            endpoint = (row["fqdn"] or row["remote_ip"]).lower()
            if not endpoint:
                continue
            counts[row["device_type"]][(endpoint, row["protocol"].lower(), int(row["port"]))] += 1
    prof = {"source": str(UNSW_CSV), "sha256": sha256(UNSW_CSV),
            "types": {d: [list(k) for k, _ in c.most_common(TOP_ENDPOINTS)] for d, c in sorted(counts.items())}}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(prof))
    return prof


def _ob(site, dtype, endpoint, proto, port, day, sec=0):
    return Observation(site_id=site, device_id=None, device_type=dtype, fqdn=endpoint, remote_ip=None,
                       protocol=proto, port=port, timestamp=T0 + timedelta(days=day, seconds=sec),
                       source_dataset="synthetic", evidence_type="flow")


def replica(point: dict, seed: int, profiles: dict) -> dict:
    rng = random.Random(seed)
    types = sorted(profiles["types"])
    if point["anchored"]:
        hist = json.loads(ANCHOR.read_text())["histograms"]["with_ncsu_family"]
        hs, ws = zip(*[(int(h), c) for h, c in hist.items()])
        sites = [f"s{i:03d}" for i in range(5)]
        hosting = {d: rng.sample(sites, rng.choices(hs, ws)[0]) for d in types}
    else:
        sites = [f"s{i:03d}" for i in range(point["N"])]
        hosting = {d: [s for s in sites if rng.random() < point["presence"]] for d in types}
    obs: list[Observation] = []
    a2_keys = set()
    record = {}
    for d in types:
        hs_d = hosting[d]
        if not hs_d:
            continue
        q = point["q"]
        if point["rho_corr"] > 0:
            r = point["rho_corr"]
            q = rng.betavariate(q * (1 / r - 1), (1 - q) * (1 / r - 1))
        adv = [s for s in hs_d if rng.random() < q]
        record[d] = {"N_d": len(hs_d), "n_avv": len(adv)}       # recorded before scoring
        eps = profiles["types"][d]
        for s in hs_d:
            seen = 0
            for r, (ep, proto, port) in enumerate(eps, start=1):
                if rng.random() < r ** -ZIPF_S:
                    seen += 1
                    days = [x for x in range(W_DAYS) if rng.random() < 0.5] or [rng.randrange(W_DAYS)]
                    obs += [_ob(s, d, ep, proto, port, x) for x in days]
            for j in range(round(LOCAL_DIVERGENCE * seen)):
                obs.append(_ob(s, d, f"local-{s}-{j}.{d.lower()}.example", "https", 443, rng.randrange(W_DAYS)))
        for i in range(A2_FACTS):
            ep = f"a2-{i}.{d.lower()}.attacker-cloud.example"
            if adv:
                a2_keys.add((d, ep, "https", 443))
            for s in adv:
                obs += [_ob(s, d, ep, "https", 443, x, y) for x in range(W_DAYS) for y in range(FLOOD)]
    scores = DIBScorer(ScoringConfig(**SCORING)).score(obs)
    volume = Counter(o.endpoint_key for o in obs)
    queue = [s for s in scores if s.accepted]
    budget = len(queue)
    dib_a2 = sum(1 for s in queue if s.endpoint_key in a2_keys)
    out = {"seed": seed, "budget": budget, "dib_a2": dib_a2, "a2_facts": len(a2_keys),
           "types": record, "n_obs": len(obs)}
    eligible = [s for s in scores if s.endpoint_class in ELIGIBLE_CLASSES]   # same class filter for all
    for b in BASELINES:
        if b == "ranked-volume":
            ranked = [(volume[s.endpoint_key], s.endpoint_key) for s in eligible]
        elif b == "ranked-sites":
            ranked = [(s.supporting_sites, s.endpoint_key) for s in eligible]
        else:
            m = 0 if b == "ranked-score" else int(b[-1])
            ranked = [(s.score, s.endpoint_key) for s in eligible if s.supporting_sites >= m]
        ranked.sort(key=lambda t: (-t[0], str(t[1])))
        out[b] = {str(c): budget_yield(ranked, a2_keys, round(c * budget))[0] for c in CURVE_C}
    return out


def all_points() -> list[dict]:
    pts = [{"N": n, "presence": p, "q": q, "rho_corr": r, "anchored": False}
           for n in NS for p in PRESENCES for q in QS for r in RHOS]
    pts += [{"N": 5, "presence": None, "q": q, "rho_corr": r, "anchored": True} for q in QS for r in RHOS]
    return pts


def point_id(p: dict) -> str:
    return ("anchored" if p["anchored"] else f"N{p['N']}_p{p['presence']}") + f"_q{p['q']}_r{p['rho_corr']}"


def _job(args):
    point, seed, profiles = args
    return point_id(point), replica(point, seed, profiles)


def run(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    profiles = type_profiles()
    points = all_points()
    if a.points:
        wanted = set(a.points.split(","))
        points = [p for p in points if point_id(p) in wanted]
    jobs = [(p, a.seed * 1_000_003 + i * 7919 + r, profiles)
            for i, p in enumerate(points) for r in range(a.replicas)]
    t0 = time.time()
    with (out / "replicas.jsonl").open("w") as fh, ProcessPoolExecutor(max_workers=a.workers) as ex:
        for pid, res in ex.map(_job, jobs, chunksize=4):
            res["point"] = pid
            fh.write(json.dumps(res) + "\n")
    elapsed = time.time() - t0
    files = [Path(__file__), ANCHOR, ROOT / "code/scripts/union_ranked_budget.py",
             ROOT / "code/src/dib/evaluation/dib.py"]
    manifest = {"argv": sys.argv, "seed": a.seed, "replicas": a.replicas, "workers": a.workers,
                "points": [point_id(p) for p in points], "scoring": SCORING,
                "generator": {"TOP_ENDPOINTS": TOP_ENDPOINTS, "ZIPF_S": ZIPF_S, "LOCAL_DIVERGENCE": LOCAL_DIVERGENCE,
                              "W_DAYS": W_DAYS, "A2_FACTS": A2_FACTS, "FLOOD": FLOOD},
                "unsw_csv_sha256": profiles["sha256"], "elapsed_s": round(elapsed, 2),
                "python": sys.version, "platform": platform.platform(),
                "sha256": {str(f.relative_to(ROOT)): sha256(f) for f in files}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(jobs)} replicas in {elapsed:.1f} s -> {out}")
    return 0


def analyze(a) -> int:
    import numpy as np
    from scipy.stats import wilcoxon
    out = Path(a.dir)
    by_point = defaultdict(list)
    for line in (out / "replicas.jsonl").open():
        r = json.loads(line)
        by_point[r["point"]].append(r)
    rng = np.random.default_rng(20261010)
    tests = []
    for pid, reps in sorted(by_point.items()):
        for b in BASELINES:
            for c in CURVE_C:
                diffs = np.array([r[b][str(c)] - r["dib_a2"] for r in reps])
                n_with_a2 = sum(1 for r in reps if r["dib_a2"] > 0 or r[b][str(c)] > 0)
                in_family = b in FAMILY_BASELINES and c in TEST_C
                row = {"point": pid, "baseline": b, "c": c, "family": in_family, "replicas": len(reps),
                       "n_with_a2": n_with_a2, "testable": n_with_a2 >= TESTABLE_MIN,
                       "mean_diff": float(diffs.mean()), "mean_dib_a2": float(np.mean([r["dib_a2"] for r in reps]))}
                boots = [rng.choice(diffs, len(diffs)).mean() for _ in range(2000)]
                row["ci_low"], row["ci_high"] = (float(x) for x in np.percentile(boots, [2.5, 97.5]))
                if row["testable"] and c in TEST_C:
                    row["p"] = (float(wilcoxon(diffs, alternative="greater", zero_method="wilcox").pvalue)
                                if np.any(diffs != 0) else 1.0)
                tests.append(row)
    family = sorted((t for t in tests if t["family"] and t["testable"]), key=lambda t: t["p"])
    m = len(family)
    stop = False
    for i, t in enumerate(family):
        t["holm_threshold"] = 0.05 / (m - i)
        stop = stop or t["p"] > t["holm_threshold"]
        t["holm_reject"] = not stop
    keys = ["point", "baseline", "c", "family", "replicas", "n_with_a2", "testable", "mean_dib_a2", "mean_diff",
            "ci_low", "ci_high", "p", "holm_threshold", "holm_reject"]
    with (out / "h61b_tests.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for t in tests:
            w.writerow({k: t.get(k) for k in keys})
    falsified = any(not t["holm_reject"] for t in family)
    n_fam = sum(1 for t in tests if t["family"])
    print(f"family: {m} testable of {n_fam}; H6-1b {'FALSIFIED' if falsified else 'not falsified'}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--replicas", type=int, default=200)
    r.add_argument("--seed", type=int, default=20261010)
    r.add_argument("--workers", type=int, default=12)
    r.add_argument("--out", required=True)
    r.add_argument("--points", default=None)
    an = sub.add_parser("analyze")
    an.add_argument("dir")
    a = p.parse_args(argv)
    return run(a) if a.cmd == "run" else analyze(a)


if __name__ == "__main__":
    raise SystemExit(main())
