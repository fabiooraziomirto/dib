"""Punto A: impact of the 8 out-of-period UNSW rows (1970-2016) on admission.

Run: PYTHONPATH=code/src python3 analysis_fs/spurious_dates.py [--workers 3]
(--workers = processes for the paper pipeline; one more process runs the A2 part)
Inputs (read-only, outside the repo):
  /root/Desktop/DIB/data/processed/observations_enriched.csv          (paper scripts' default)
  /root/Desktop/DIB/data/processed/observations_enriched_item1fixed.csv (A2 multiseed input)
Outputs (analysis_fs/out/):
  spurious_rows.csv                 the 8 rows, both files, with 1-based file line
  observations_enriched_nospurious.csv, observations_enriched_item1fixed_nospurious.csv
                                    filtered copies (gitignored, large)
  spurious_dates_impact.csv         every endpoint of the affected types, before/after
  spurious_dates_a2.csv             A2 raw, k=3 and k=5, affected types, before/after
  spurious_dates_results_scan.csv   cells in results/*.csv of affected types close to theta
  spurious_dates_summary.csv

Design: the pure date effect is measured on the SAME partition. The paper's
pipeline (read_observations_csv -> filter_observations(exclude_non_global_ips)
-> partition_observations(random, seed) -> DIBScorer) is run once, and the 8
rows are then removed from the partitioned population. Re-running a script on
a filtered file would ALSO reshuffle the partition (the shuffle runs over the
row list); that second effect is seed variance, not a date effect, and is
not measured here.

Restricted scoring (exact, [D] checked on seed 42 by `check_restricted`): with
gamma=0 a type's scores depend only on that type's rows plus, under trust
weighting, the site weights computed from the whole population. So the
affected types are scored with observations = their rows and
trust_observations = the whole (before / after) population, with
trust_reference_breadth calibrated on the whole population, exactly as
recall_funnel.py:201 and ablation_multiseed.py:47 do. Other types are
unaffected iff site breadth and the reference breadth are unchanged; checked
per seed (`breadth_unchanged`).

Hypotheses (stated before running):
  S1 the 8 rows survive the private-IP filter (all global IPs) and sit in 3
     types: AugustDoorBell (|D_d| 110 -> 108), NestDropCam (93 -> 89),
     WithingsSleepSensor (89 -> 87);
  S2 removing them can only RAISE day coverage, so every score of those types
     rises by at most 0.4*0.7*(|D_d|/|D_d'| - 1) (0.0052 / 0.0126 / 0.0064),
     plus a negligible frequency term;
  S3 site breadth is unchanged (the rows' endpoints are also seen on other
     days at the same sites), so no other type moves;
  S4 a handful of facts of the affected types cross theta upward at some
     seeds; the paper's queue counts move by at most a few facts;
  S5 the A2 raw maxima at k=3/k=5 for the affected types rise by < 0.013;
     no fabricated fact crosses theta.
"""
from __future__ import annotations

import argparse
import csv
import multiprocessing
import time
from dataclasses import replace as dc_replace
from pathlib import Path

from dib.core.io import filter_observations, read_observations_csv
from dib.core.models import Observation
from dib.evaluation.dib import DIBScorer, ScoringConfig
from dib.evaluation.trust import calibrate_reference_breadth, compute_site_breadth
from dib.simulator.sites import partition_observations

DATA = Path("/root/Desktop/DIB/data/processed")
ENRICHED = DATA / "observations_enriched.csv"
ITEM1 = DATA / "observations_enriched_item1fixed.csv"
OUT = Path(__file__).resolve().parent / "out"
REPO = Path(__file__).resolve().parents[1]
CUTOFF = "2016-09-01"
SEEDS = list(range(20)) + [42]
RAW = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2, graph_enabled=False)
DELTA_BOUND = {"AugustDoorBell": 0.28 * (110 / 108 - 1), "NestDropCam": 0.28 * (93 / 89 - 1),
               "WithingsSleepSensor": 0.28 * (89 / 87 - 1)}


def find_spurious(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as fh:
        for line_no, r in enumerate(csv.DictReader(fh), start=2):
            if r["timestamp"] < CUTOFF:
                rows.append({"file": path.name, "line": line_no, **{k: r[k] for k in
                             ("site_id", "device_id", "device_type", "fqdn", "remote_ip", "protocol", "port", "timestamp")}})
    return rows


def write_filtered_copy(src: Path, dst: Path) -> int:
    dropped = 0
    with src.open(newline="") as fin, dst.open("w", newline="") as fout:
        header = fin.readline()
        fout.write(header)
        ts_idx = header.rstrip("\n").split(",").index("timestamp")
        for line in fin:
            if line.split(",")[ts_idx] < CUTOFF:  # no quoted commas before timestamp in these files
                dropped += 1
                continue
            fout.write(line)
    return dropped


def is_spurious(o: Observation) -> bool:
    return o.timestamp.year < 2016 or (o.timestamp.year == 2016 and o.timestamp.month < 9)


def trust_config(ref_breadth: float) -> ScoringConfig:
    return dc_replace(RAW, trust_weighted=True, trust_reference_breadth=ref_breadth)


def score_types(population: list[Observation], types: set[str], ref_breadth: float | None):
    """ref_breadth None -> raw breadth; otherwise trust weighting with that reference."""
    rows = [o for o in population if o.device_type in types]
    if ref_breadth is not None:
        return DIBScorer(trust_config(ref_breadth)).score(rows, trust_observations=population)
    return DIBScorer(RAW).score(rows)


def check_restricted(population: list[Observation], types: set[str], ref_breadth: float) -> int:
    full = {s.endpoint_key: s for s in DIBScorer(trust_config(ref_breadth)).score(population) if s.device_type in types}
    part = {s.endpoint_key: s for s in score_types(population, types, ref_breadth)}
    assert full.keys() == part.keys()
    for k, s in full.items():
        assert abs(s.score - part[k].score) < 1e-12 and s.accepted == part[k].accepted, k
    return len(full)


def _paper_worker(seeds: list[int]) -> tuple[list[dict], list[dict]]:
    obs = list(filter_observations(read_observations_csv(ENRICHED), exclude_non_global_ips=True))
    impact, checks = [], []
    for seed in seeds:
        sites = partition_observations(obs, 10, strategy="random", seed=seed)
        before = [o for s in sites for o in s.observations if o.fqdn or o.remote_ip]
        after = [o for o in before if not is_spurious(o)]
        types = {o.device_type for o in before if is_spurious(o)}
        breadth_same = compute_site_breadth(before) == compute_site_breadth(after)
        ref_b, ref_a = calibrate_reference_breadth(before), calibrate_reference_breadth(after)
        checks.append({"seed": seed, "removed_rows": len(before) - len(after), "affected_types": ";".join(sorted(types)),
                       "breadth_unchanged": breadth_same, "reference_breadth_unchanged": ref_b == ref_a,
                       "restricted_equivalence_keys": check_restricted(before, types, ref_b) if seed == 42 else ""})
        for trust in (True, False):
            b = {s.endpoint_key: s for s in score_types(before, types, ref_b if trust else None)}
            a = {s.endpoint_key: s for s in score_types(after, types, ref_a if trust else None)}
            for key in sorted(b.keys() | a.keys()):
                sb, sa = b.get(key), a.get(key)
                impact.append({"experiment": "paper_pipeline(observations_enriched.csv)", "seed": seed,
                               "config": "graph_free_selected(trust)" if trust else "raw_breadth",
                               "device_type": key[0], "endpoint": key[1], "protocol": key[2], "port": key[3],
                               "score_before": round(sb.score, 9) if sb else "", "score_after": round(sa.score, 9) if sa else "",
                               "delta": round(sa.score - sb.score, 9) if sb and sa else "",
                               "accepted_before": bool(sb and sb.accepted), "accepted_after": bool(sa and sa.accepted),
                               "eligible_class": (sb or sa).endpoint_class})
        print(f"paper pipeline seed {seed} done", flush=True)
    return impact, checks


def _a2_worker(_: int) -> list[dict]:
    import a2_raw_k
    obs = list(read_observations_csv(ITEM1))
    out = []
    for seed in range(20):
        part = a2_raw_k.partition(obs, seed)
        types = {o.device_type for o in part if is_spurious(o)}
        before = [o for o in part if o.device_type in types]
        after = [o for o in before if not is_spurious(o)]
        for k in (3, 5):
            for label, pop in (("before", before), ("after", after)):
                for r in a2_raw_k.run_trial(pop, seed, k):
                    out.append({**r, "population": label})
        print(f"a2 seed {seed} done", flush=True)
    return out


def scan_results() -> list[dict]:
    """Cells of affected types in results/**/*.csv whose score lies in
    [theta - bound, theta): the only ones the date effect could push across."""
    out = []
    for path in sorted((REPO / "results").rglob("*.csv")):
        with path.open(newline="") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                continue
            dev_col = next((c for c in reader.fieldnames if c in ("device_type", "target_device_type", "device")), None)
            score_cols = [c for c in reader.fieldnames if "score" in c.lower() and "rwv" not in c.lower()]
            if not dev_col or not score_cols:
                continue
            for i, r in enumerate(reader, start=2):
                d = r.get(dev_col)
                if d not in DELTA_BOUND:
                    continue
                for c in score_cols:
                    try:
                        v = float(r[c])
                    except (TypeError, ValueError):
                        continue
                    if 0.65 - DELTA_BOUND[d] - 1e-9 <= v < 0.65:
                        out.append({"file": str(path.relative_to(REPO)), "line": i, "device_type": d, "column": c,
                                    "score": v, "bound": round(DELTA_BOUND[d], 6), "max_after": round(v + DELTA_BOUND[d], 6)})
    return out


def write(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("none\n")
        return
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=3)
    a = p.parse_args()
    OUT.mkdir(exist_ok=True)
    t0 = time.monotonic()
    spurious = find_spurious(ENRICHED) + find_spurious(ITEM1)
    write(OUT / "spurious_rows.csv", spurious)
    for src in (ENRICHED, ITEM1):
        n = write_filtered_copy(src, OUT / f"{src.stem}_nospurious.csv")
        print(f"{src.name}: dropped {n} rows", flush=True)
    write(OUT / "spurious_dates_results_scan.csv", scan_results())

    # one process for the A2 part, a.workers processes for the paper pipeline
    chunks = [SEEDS[i::a.workers] for i in range(a.workers)]
    with multiprocessing.Pool(a.workers + 1) as pool:
        a2_async = pool.apply_async(_a2_worker, (0,))
        parts = pool.map(_paper_worker, chunks, chunksize=1)
        a2 = a2_async.get()
    impact = sorted((r for part in parts for r in part[0]),
                    key=lambda r: (r["seed"], r["config"], r["device_type"], r["endpoint"], r["protocol"], r["port"]))
    checks = sorted((r for part in parts for r in part[1]), key=lambda r: r["seed"])
    write(OUT / "spurious_dates_impact.csv", impact)
    write(OUT / "spurious_dates_checks.csv", checks)
    a2.sort(key=lambda r: (r["seed"], r["k"], r["device_type"], r["population"]))
    write(OUT / "spurious_dates_a2.csv", a2)

    summary = []
    for cfg in ("graph_free_selected(trust)", "raw_breadth"):
        for seed in SEEDS:
            sel = [r for r in impact if r["config"] == cfg and r["seed"] == seed]
            elig = [r for r in sel if r["eligible_class"] in ("dns", "ntp", "update", "vendor-cloud")]
            summary.append({"config": cfg, "seed": seed, "endpoints": len(sel),
                            "admitted_before": sum(r["accepted_before"] for r in sel),
                            "admitted_after": sum(r["accepted_after"] for r in sel),
                            "newly_admitted": sum(r["accepted_after"] and not r["accepted_before"] for r in sel),
                            "newly_rejected": sum(r["accepted_before"] and not r["accepted_after"] for r in sel),
                            "max_delta": max((r["delta"] for r in sel if r["delta"] != ""), default=0),
                            "min_delta": min((r["delta"] for r in sel if r["delta"] != ""), default=0),
                            "eligible_within_bound_below_theta_before": sum(
                                1 for r in elig if r["score_before"] != "" and
                                0.65 - DELTA_BOUND[r["device_type"]] <= r["score_before"] < 0.65)})
    write(OUT / "spurious_dates_summary.csv", summary)
    for s in summary:
        if s["seed"] == 42 or s["newly_admitted"] or s["newly_rejected"]:
            print(s)
    print("breadth unchanged at every seed:", all(c["breadth_unchanged"] and c["reference_breadth_unchanged"] for c in checks))
    print(f"total {time.monotonic() - t0:.0f}s")


if __name__ == "__main__":
    main()
