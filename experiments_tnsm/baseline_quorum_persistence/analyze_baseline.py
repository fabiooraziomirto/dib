"""Baseline B(m, tau) 'quorum + persistence, no score' (audit 40; audit 36 item 5.3b).

Definitions, hypotheses H-B1..H-B3 and thresholds are those of docs/audit/40_prereg_baseline_quorum_persistenza.md
(committed before any computation). This file only implements them; nothing here changes a threshold.

Usage (from the repo root):
  python3 experiments_tnsm/baseline_quorum_persistence/analyze_baseline.py all --out <dir>
  subcommands: s1 | s2 | real | all. Real data are read in place (outside the repo); only aggregates are written.
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(ROOT / "code" / "scripts"))
sys.path.insert(0, str(ROOT / "experiments_tnsm" / "synthetic_federation"))
sys.path.insert(0, str(ROOT / "experiments_tnsm" / "m67_retraction"))

from moniotr_cross_lab import (  # noqa: E402
    ELIGIBLE, collapse_site_three, load, load_label_mapping, mean, per_device_metrics, score_keys, set_metrics, sha256,
)
from dib.evaluation.intent_overlap import classify_core  # noqa: E402

SEED = 20261012
TAUS = (0.0, 0.05, 0.125, 0.25, 0.5)
FINE_GRID = tuple(round(i * 0.005, 3) for i in range(201))
H_B2_MARGIN = 0.02
P_STAR_REGISTERED = 1e-3
DATA = Path("/root/Desktop/DIB/data/processed")
INPUTS = (DATA / "moniotr_full_observations.csv", DATA / "yourthings_observations.csv")
MAPPING = ROOT / "docs" / "label_mapping_v16.csv"
REFERENCE = ROOT / "results" / "three_lab_matched" / "matched_ablation.csv"
RUNS = ROOT / "experiments_tnsm" / "synthetic_federation" / "runs"


# ---- the baseline -------------------------------------------------------------------------------------------
def admit(n_sites, active_day_ratio, eligible, m, tau):
    """|S_e| >= m, active_day_ratio >= tau, eligible class. No score, no alpha/beta/theta."""
    return n_sites >= m and active_day_ratio >= tau and bool(eligible)


def key_table(data, sources, devices):
    """key -> (|S_e| over sources, active_day_ratio over sources, eligible class), as in score_keys
    (moniotr_cross_lab.py:324-376): days of the endpoint over days of the device, both counted on the sources."""
    table = {}
    devices = set(devices)
    for key, reporters in data.endpoints.items():
        device, endpoint, protocol, port = key
        supporters = reporters & sources
        if device not in devices or not supporters:
            continue
        ep_days = {d for s in sources for d in data.site_endpoint_days[(s, key)]}
        dev_days = {d for s in sources for d in data.site_device_days[(s, device)]}
        table[key] = (len(supporters), len(ep_days) / max(len(dev_days), 1),
                      classify_core(endpoint, protocol, port) in ELIGIBLE)
    return table


def select(table, m, tau):
    return {k for k, (n, adr, ok) in table.items() if admit(n, adr, ok, m, tau)}


def tau_match(table, m, target, grid=FINE_GRID):
    """Grid tau whose candidate count is closest to target; ties to the smaller tau. Returns (tau, count)."""
    best = None
    for tau in grid:
        n = len(select(table, m, tau))
        if best is None or abs(n - target) < abs(best[1] - target):
            best = (tau, n)
    return best


def rate_from_hist(hist, trials, m):
    x = sum(c for k, c in hist.items() if int(k) >= m)
    return x, x / trials


# ---- verdicts (thresholds of audit 40 s.4) -------------------------------------------------------------------
def verdict_hb1(rows):
    better = sum(r["prec_dib"] > r["prec_base"] for r in rows)
    return "not falsified" if better * 2 > len(rows) else "falsified"


def verdict_hb2(rows):
    return "falsified" if any(round(r["rec_base"] - r["rec_dib"], 12) > H_B2_MARGIN for r in rows) else "not falsified"


def verdict_hb3(points, testable=lambda p_star: p_star < P_STAR_REGISTERED):
    tested = [p for p in points if testable(p["p_star"])]
    return "falsified" if any(p["r_B"] <= p["r_dib"] for p in tested) else "not falsified"


# ---- S1: adversary-only facts, from the recorded histograms ---------------------------------------------------
def s1():
    from analyze_c import clopper_pearson
    out = []
    for run in ("h61a_rho0", "h62_rho03"):
        hist = json.loads((RUNS / run / "k_hist.json").read_text())
        for row in csv.DictReader((RUNS / run / "points.csv").open()):
            h, trials = hist[f"{row['N']}:{row['q']}"], int(row["trials"])
            assert sum(h.values()) == trials
            r_dib = int(row["x_dib"]) / trials
            rec = dict(run=run, N=int(row["N"]), q=float(row["q"]), trials=trials, p_star=float(row["p_star"]),
                       r_dib=r_dib, x_dib=int(row["x_dib"]))
            for m in (1, 2, 3):
                x, r = rate_from_hist(h, trials, m)
                rec[f"x_B{m}"], rec[f"r_B{m}"] = x, r
                rec[f"ci_B{m}"] = clopper_pearson(x, trials)
            rec["r_B"] = rec["r_B2"]
            rec["ratio_B2_dib"] = rec["r_B2"] / r_dib if r_dib > 0 else None
            out.append(rec)
    return out


# ---- S2: benign recall on the synthetic federation, q = 0 -------------------------------------------------------
S2_NS = (10, 20, 50, 100)
S2_PRESENCES = (0.2, 0.4, 0.6, 0.8)
S2_MS = (1, 2, 3)
S2_TAUS = (0.0, 0.125, 0.25, 0.5)
S2_REPLICAS = 50
BOOT = 10000


def s2_replica(point, seed, profiles, h61b):
    """h61b.replica() unchanged (q = 0, rho_corr = 0); its DIBScorer is wrapped only to capture the observations
    and the scores, so the generator is not re-implemented."""
    captured = {}
    real = h61b.DIBScorer

    class Capture(real):
        def score(self, observations, *a, **k):
            scores = super().score(observations, *a, **k)
            captured["obs"], captured["scores"] = observations, scores
            return scores
    h61b.DIBScorer = Capture
    try:
        h61b.replica(point, seed, profiles)
    finally:
        h61b.DIBScorer = real
    obs, scores = captured["obs"], captured["scores"]
    days_ep, days_dev, sites_ep = {}, {}, {}
    for o in obs:
        k = o.endpoint_key
        days_ep.setdefault(k, set()).add(o.timestamp.date())
        days_dev.setdefault(o.device_type, set()).add(o.timestamp.date())
        sites_ep.setdefault(k, set()).add(o.site_id)
    hosted = {o.device_type for o in obs}
    bench = {d: {(d, e[0], e[1], e[2]) for e in profiles["types"][d]} for d in hosted}
    dib = {s.endpoint_key for s in scores if s.accepted}
    table = {k: (len(sites_ep[k]), len(days_ep[k]) / max(len(days_dev[k[0]]), 1),
                 classify_core(k[1], k[2], k[3]) in ELIGIBLE) for k in sites_ep if k[0] in hosted}
    res = {"DIB": statistics.fmean(len(dib & b) / len(b) for b in bench.values())}
    for m in S2_MS:
        for tau in S2_TAUS:
            sel = select(table, m, tau)
            res[f"B{m}_{tau}"] = statistics.fmean(len(sel & b) / len(b) for b in bench.values())
    return res


def boot_median_ci(values, rng, n=BOOT):
    meds = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(n))
    return meds[int(0.025 * n)], meds[int(0.975 * n) - 1]


def s2(replicas=S2_REPLICAS):
    import h61b
    profiles = h61b.type_profiles()
    rng = random.Random(SEED)
    rows = []
    for i, (N, pres) in enumerate((N, p) for N in S2_NS for p in S2_PRESENCES):
        point = {"N": N, "presence": pres, "q": 0.0, "rho_corr": 0.0, "anchored": False}
        reps = [s2_replica(point, SEED * 1_000_003 + i * 7919 + r, profiles, h61b) for r in range(replicas)]
        for name in reps[0]:
            vals = [r[name] for r in reps]
            lo, hi = boot_median_ci(vals, rng)
            rows.append(dict(N=N, presence=pres, arm=name, median=statistics.median(vals), ci_low=lo, ci_high=hi,
                             replicas=replicas))
    return rows


# ---- three real labs -----------------------------------------------------------------------------------------------
STAGES = ("union", "quorum", "quorum_score", "DIB")


def real():
    sites = ("US", "UK", "YT")
    label_map = load_label_mapping(MAPPING)
    data = load(INPUTS[0], extra_paths=list(INPUTS[1:]), collapse_fn=collapse_site_three, label_map=label_map)
    with REFERENCE.open() as f:
        reference = {(r["receiver"], r["stage"]): r for r in csv.DictReader(f)}
    out = []
    for receiver in sites:
        sources = set(sites) - {receiver}
        devices, locked, _ = per_device_metrics(data, sites, receiver)
        assert len(devices) == 6
        source_union = {k for k, rep in data.endpoints.items() if k[0] in devices and rep & sources}
        quorum = {k for k in source_union if len(data.endpoints[k] & sources) >= 2}
        scored, _ = score_keys(data, sources, gate=False, quorum=True)
        stages = {"union": source_union, "quorum": quorum, "quorum_score": scored & source_union, "DIB": locked}

        def metrics(cands):
            ms = [set_metrics({k for k in cands if k[0] == d}, data.profiles[receiver][d]) for d in devices]
            return dict(candidates=len(cands), coverage=sum(any(k[0] == d for k in cands) for d in devices) / 6,
                        precision=mean(ms, "precision"), recall=mean(ms, "recall"), f1=mean(ms, "f1"))
        # reproduction check (audit 40 s.3): nothing is reported unless the four reference rows are reproduced exactly
        for stage, cands in stages.items():
            got, ref = metrics(cands), reference[(receiver, stage)]
            assert got["candidates"] == int(ref["candidates"]), (receiver, stage)
            for k in ("coverage", "precision", "recall", "f1"):
                assert abs(got[k] - float(ref[k])) < 1e-12, (receiver, stage, k)
        table = key_table(data, sources, devices)
        assert select(table, 2, 0.0) <= quorum
        rec = {"receiver": receiver, "stages": {s: metrics(c) for s, c in stages.items()}, "baseline": {}}
        for m in (1, 2):
            for tau in TAUS:
                rec["baseline"][f"m{m}_tau{tau}"] = metrics(select(table, m, tau))
        rec["baseline"]["m3"] = "non definito (due sole sorgenti)"
        tau_m, n_m = tau_match(table, 2, len(locked))
        rec["tau_match"] = tau_m
        rec["baseline"]["m2_tau_match"] = metrics(select(table, 2, tau_m))
        assert rec["baseline"]["m2_tau_match"]["candidates"] == n_m
        out.append(rec)
    hb1 = [dict(receiver=r["receiver"], prec_dib=r["stages"]["DIB"]["precision"],
                prec_base=r["baseline"]["m2_tau_match"]["precision"]) for r in out]
    hb2 = [dict(receiver=r["receiver"], rec_dib=r["stages"]["DIB"]["recall"],
                rec_base=r["baseline"]["m2_tau_match"]["recall"]) for r in out]
    return out, {"H-B1": (verdict_hb1(hb1), hb1), "H-B2": (verdict_hb2(hb2), hb2)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("cmd", choices=("s1", "s2", "real", "all"))
    p.add_argument("--out", required=True)
    p.add_argument("--replicas", type=int, default=S2_REPLICAS)
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    if a.cmd in ("s1", "all"):
        res["s1"] = s1()
        res["H-B3"] = verdict_hb3(res["s1"])
        res["H-B3_powered_reading"] = verdict_hb3(res["s1"], testable=lambda ps: ps >= P_STAR_REGISTERED)
    if a.cmd in ("real", "all"):
        res["real"], res["real_verdicts"] = real()
    if a.cmd in ("s2", "all"):
        res["s2"] = s2(a.replicas)
    (out / "aggregates.json").write_text(json.dumps(res, indent=1))
    files = [Path(__file__), REFERENCE, MAPPING, *INPUTS]
    (out / "manifest.json").write_text(json.dumps({
        "argv": sys.argv, "seed": SEED, "python": sys.version, "platform": platform.platform(),
        "audit": "docs/audit/40_prereg_baseline_quorum_persistenza.md",
        "sha256": {str(f): sha256(f) for f in files}}, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k.startswith("H-B") or k == "real_verdicts"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
