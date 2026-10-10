"""H6-1c (EXPLORATORY; audit 16 s.7): reformulation that ORIGINATES FROM THE DATA OF H6-1b.

Status: exploratory. H6-1b (h61b.py, hypothesis committed in 07fb841 before its launch) is
FALSIFIED and stays so: its universal claim failed for ranked-sites at budget 1x
(802 of 892 testable tests confirmed). H6-1c was written after seeing those results, so
it can only be confirmed on FRESH data: same generator and sweep as H6-1b
(h61b.replica logic, 170 points x 200 replicas), NEW seeds never used in H6-1b
(base seed 20261012; H6-1b used 20261010; the per-replica seeds
base*1_000_003 + point_index*7919 + r are disjoint between the two runs, checked at start
and recorded in the manifest).

Hypothesis H6-1c (declared before any new data):
  "admission protects from the flood and when the operator reviews more facts than DIB's
   queue; at equal budget and with an adversarial share above 5/12, ranking by number of
   sites is as protective or more."
Operationally, with diff = A2_baseline(round(c*B)) - A2_DIB (counts, same class filter for
all baselines, as in H6-1b):
  C1 flood:          ranked-volume, c in {1, 2, 5}: diff > 0.          170 x 3 = 510 tests
  C2 larger budget:  ranked-sites,  c in {2, 5}:    diff > 0.          170 x 2 = 340 tests
  C3 equal budget:   ranked-sites,  c = 1, ONLY on replicas with at least one type whose
                     adversarial share is above the margin (n_avv >= ceil(5 N_d/12) and
                     n_avv >= 2): diff <= 0 ("as protective or more"). 170 tests
Tests: one-sided Wilcoxon signed-rank on the paired replica differences. C1, C2:
alternative "greater" (supported if rejected). C3: alternative "greater" too, i.e. the test
that would show the baseline WORSE than DIB; C3 is falsified if that test is rejected.
Testable: >= 50 replicas with an A2 fact in DIB's queue or in the prefix (C3: among the
replicas above the margin).
Family: all testable C1 + C2 + C3 tests (up to 1020), one Holm procedure, FWER 5%.
Falsified if Holm does not reject for some testable C1/C2 test, or Holm rejects some
testable C3 test. Reported also: points where ranked-sites is significantly MORE
protective (one-sided "less", descriptive, not in the family), and the reference
ranked-support-3 (descriptive).
Deterministic check (per type, exact attribution; H6-1b only recorded the replica count):
every A2 fact admitted by DIB belongs to a type with n_avv >= ceil(5 N_d/12) and
n_avv >= 2. One violation: stop and report (no change to dib.py).

Usage: python3 h61c.py run --replicas 200 --seed 20261012 --workers 12 --out <dir>
       python3 h61c.py analyze <dir>
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h61b  # noqa: E402  (frozen: generator, sweep, scorer config and baselines are reused as is)
from h61b import (ANCHOR, A2_FACTS, BASELINES, CURVE_C, FLOOD, LOCAL_DIVERGENCE, SCORING, TOP_ENDPOINTS,  # noqa: E402
                  W_DAYS, ZIPF_S, ELIGIBLE_CLASSES, Counter as _C, DIBScorer, ScoringConfig, _ob, budget_yield,
                  all_points, point_id, sha256, type_profiles)

H61B_SEED = 20261010
TESTABLE_MIN = 50


def kmin(n: int) -> int:
    return math.ceil(5 * n / 12)


def replica(point: dict, seed: int, profiles: dict) -> dict:
    """h61b.replica, unchanged generator, plus exact per-type attribution of admitted A2 facts."""
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
    obs, a2_keys, record = [], set(), {}
    for d in types:
        hs_d = hosting[d]
        if not hs_d:
            continue
        q = point["q"]
        if point["rho_corr"] > 0:
            r = point["rho_corr"]
            q = rng.betavariate(q * (1 / r - 1), (1 - q) * (1 / r - 1))
        adv = [s for s in hs_d if rng.random() < q]
        record[d] = {"N_d": len(hs_d), "n_avv": len(adv)}
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
    volume = _C(o.endpoint_key for o in obs)
    queue = [s for s in scores if s.accepted]
    budget = len(queue)
    admitted_by_type = _C(s.device_type for s in queue if s.endpoint_key in a2_keys)
    over = {d for d, v in record.items() if v["n_avv"] >= kmin(v["N_d"]) and v["n_avv"] >= 2}
    out = {"seed": seed, "budget": budget, "dib_a2": sum(admitted_by_type.values()), "a2_facts": len(a2_keys),
           "types": record, "a2_admitted_by_type": dict(admitted_by_type), "over_margin_types": sorted(over),
           "below_margin_admissions": sum(c for d, c in admitted_by_type.items() if d not in over),
           "n_obs": len(obs)}
    eligible = [s for s in scores if s.endpoint_class in ELIGIBLE_CLASSES]
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


def seeds(base: int, points: list, replicas: int) -> list[int]:
    return [base * 1_000_003 + i * 7919 + r for i in range(len(points)) for r in range(replicas)]


def _job(args):
    point, seed, profiles = args
    return point_id(point), replica(point, seed, profiles)


def run(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    profiles = type_profiles()
    points = all_points()
    new = seeds(a.seed, points, a.replicas)
    old = set(seeds(H61B_SEED, points, 200))
    overlap = len(old.intersection(new))
    if a.seed == H61B_SEED or overlap:
        raise SystemExit(f"seed overlap with H6-1b ({overlap}): refusing")
    jobs = [(p, new[i * a.replicas + r], profiles) for i, p in enumerate(points) for r in range(a.replicas)]
    t0 = time.time()
    viol = 0
    with (out / "replicas.jsonl").open("w") as fh, ProcessPoolExecutor(max_workers=a.workers) as ex:
        for pid, res in ex.map(_job, jobs, chunksize=4):
            res["point"] = pid
            viol += res["below_margin_admissions"]
            fh.write(json.dumps(res) + "\n")
    files = [Path(__file__), Path(h61b.__file__), ANCHOR]
    manifest = {"argv": sys.argv, "seed": a.seed, "h61b_seed": H61B_SEED, "seed_overlap_with_h61b": overlap,
                "seed_range": [min(new), max(new)], "replicas": a.replicas, "workers": a.workers,
                "points": len(points), "scoring": SCORING,
                "generator": {"TOP_ENDPOINTS": TOP_ENDPOINTS, "ZIPF_S": ZIPF_S, "LOCAL_DIVERGENCE": LOCAL_DIVERGENCE,
                              "W_DAYS": W_DAYS, "A2_FACTS": A2_FACTS, "FLOOD": FLOOD},
                "below_margin_admissions_total": viol, "unsw_csv_sha256": profiles["sha256"],
                "elapsed_s": round(time.time() - t0, 2), "python": sys.version, "platform": platform.platform(),
                "sha256": {f.name: sha256(f) for f in files}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(jobs)} replicas, below-margin admissions {viol} -> {out}")
    return 0


def analyze(a) -> int:
    import numpy as np
    from scipy.stats import wilcoxon
    out = Path(a.dir)
    by_point = defaultdict(list)
    for line in (out / "replicas.jsonl").open():
        r = json.loads(line)
        by_point[r["point"]].append(r)
    rng = np.random.default_rng(20261012)
    rows = []
    spec = [("C1", "ranked-volume", c, None) for c in (1, 2, 5)] + \
           [("C2", "ranked-sites", c, None) for c in (2, 5)] + [("C3", "ranked-sites", 1, "over")] + \
           [("ref", "ranked-support-3", c, None) for c in (1, 2, 5)]
    for pid, reps in sorted(by_point.items()):
        for part, b, c, sub in spec:
            rr = [r for r in reps if r["over_margin_types"]] if sub == "over" else reps
            diffs = np.array([r[b][str(c)] - r["dib_a2"] for r in rr])
            n_with = sum(1 for r in rr if r["dib_a2"] > 0 or r[b][str(c)] > 0)
            row = {"part": part, "point": pid, "baseline": b, "c": c, "replicas": len(rr), "n_with_a2": n_with,
                   "testable": n_with >= TESTABLE_MIN and part != "ref",
                   "mean_diff": float(diffs.mean()) if len(diffs) else None}
            if len(diffs):
                boots = [rng.choice(diffs, len(diffs)).mean() for _ in range(2000)]
                row["ci_low"], row["ci_high"] = (float(x) for x in np.percentile(boots, [2.5, 97.5]))
            if len(diffs) and np.any(diffs != 0):
                row["p_greater"] = float(wilcoxon(diffs, alternative="greater").pvalue)
                row["p_less"] = float(wilcoxon(diffs, alternative="less").pvalue)
            else:
                row["p_greater"] = row["p_less"] = 1.0
            rows.append(row)
    family = sorted((t for t in rows if t["testable"]), key=lambda t: t["p_greater"])
    m, stop = len(family), False
    for i, t in enumerate(family):
        t["holm_threshold"] = 0.05 / (m - i)
        stop = stop or t["p_greater"] > t["holm_threshold"]
        t["holm_reject_greater"] = not stop
    bad = [t for t in family if (t["part"] in ("C1", "C2") and not t["holm_reject_greater"])
           or (t["part"] == "C3" and t["holm_reject_greater"])]
    keys = ["part", "point", "baseline", "c", "replicas", "n_with_a2", "testable", "mean_diff", "ci_low",
            "ci_high", "p_greater", "p_less", "holm_threshold", "holm_reject_greater"]
    with (out / "h61c_tests.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for t in rows:
            w.writerow({k: t.get(k) for k in keys})
    print(f"family {m}; failing {len(bad)} {Counter(t['part'] for t in bad)}; "
          f"H6-1c {'FALSIFIED' if bad else 'not falsified (exploratory confirmation)'}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--replicas", type=int, default=200)
    r.add_argument("--seed", type=int, default=20261012)
    r.add_argument("--workers", type=int, default=12)
    r.add_argument("--out", required=True)
    an = sub.add_parser("analyze")
    an.add_argument("dir")
    a = p.parse_args(argv)
    return run(a) if a.cmd == "run" else analyze(a)


if __name__ == "__main__":
    raise SystemExit(main())
