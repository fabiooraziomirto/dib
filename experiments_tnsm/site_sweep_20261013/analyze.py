"""Analysis of the site-count sweep (pre-registration: docs/audit/123).

Usage: python analyze.py RUN_DIR [RUN_DIR ...] --out OUT_DIR
Reads manifest.json (per-repetition counters and resources) and raw_n*_w*.csv.gz
(one row per request). Writes cells.csv, per_op.csv, ratios.csv, summary.json, table.md.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

CORE_RULE = 0.85   # audit 123 H-S4 (a), (c)
PLATEAU = 0.10     # audit 123 H-S4 (b)


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    f, c = math.floor(k), math.ceil(k)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def load_raw(path: Path) -> list[dict]:
    with gzip.open(path, "rt", newline="") as f:
        return list(csv.DictReader(f))


def boot_ratio(a: list[float], b: list[float], seed=20261013, n=10000):
    rng = random.Random(seed)
    rs = sorted(statistics.mean(rng.choices(a, k=len(a))) / statistics.mean(rng.choices(b, k=len(b))) for _ in range(n))
    return statistics.mean(a) / statistics.mean(b), rs[int(0.025 * n)], rs[int(0.975 * n) - 1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    cells, per_op, thr = [], [], defaultdict(dict)
    for run in a.runs:
        man = json.loads((run / "manifest.json").read_text())
        tr = man["transport"]
        for cell in man["cells"]:
            n, w = cell["n_sites"], cell["n_workers"]
            reps = cell["repeats"]
            raw = load_raw(run / f"raw_n{n}_w{w}.csv.gz")
            lat = [float(r["latency_s"]) for r in raw]
            outcomes = Counter(r["outcome"] for r in raw)
            statuses = Counter(f"{r['op']}:{r['status']}" for r in raw if r["outcome"] not in ("ok",))
            att = [x["requests"] / x["wall_s"] for x in reps]
            ok = [x["ok"] / x["wall_s"] for x in reps]
            chg = [x["changed"] / x["wall_s"] for x in reps]
            thr[(tr, n)][w] = att
            client_cores = [x["client_cpu_s"] / x["wall_s"] for x in reps]
            ev_cores = [x["container_cpu_s"]["evidence"] / x["wall_s"] for x in reps]
            site_cores = [max(v for k, v in x["container_cpu_s"].items() if k != "evidence") / x["wall_s"] for x in reps]
            mem_ev = max(x["container_mem_max_bytes"].get("evidence", 0) for x in reps)
            mem_site = max(max((v for k, v in x["container_mem_max_bytes"].items() if k != "evidence"), default=0) for x in reps)
            row = {"transport": tr, "n_sites": n, "n_workers": w, "requests": len(raw), "repeats": len(reps),
                   "attempted_rps_mean": statistics.mean(att), "attempted_rps_sd": statistics.stdev(att) if len(att) > 1 else 0,
                   "ok_rps_mean": statistics.mean(ok), "changed_rps_mean": statistics.mean(chg),
                   "p50_ms": 1000 * pct(lat, .5), "p95_ms": 1000 * pct(lat, .95), "p99_ms": 1000 * pct(lat, .99),
                   "ok": outcomes["ok"], "rejected_409": outcomes["rejected"], "error": outcomes["error"],
                   "timeout": outcomes["timeout"], "transport_err": outcomes["transport"],
                   "non_ok_by_op_status": ";".join(f"{k}x{v}" for k, v in sorted(statuses.items())),
                   "client_cores_mean": statistics.mean(client_cores), "evidence_cores_mean": statistics.mean(ev_cores),
                   "busiest_site_cores_mean": statistics.mean(site_cores),
                   "evidence_mem_max_mib": mem_ev / 2 ** 20, "site_mem_max_mib": mem_site / 2 ** 20,
                   "host_busy_fraction_mean": statistics.mean(x["host_busy_fraction"] for x in reps),
                   "loadavg1_mean": statistics.mean(x["loadavg"][0] for x in reps)}
            cells.append(row)
            by_op = defaultdict(list)
            for r in raw:
                by_op[r["op"]].append(r)
            for op, rs in sorted(by_op.items()):
                l = [float(r["latency_s"]) for r in rs]
                oc = Counter(r["outcome"] for r in rs)
                per_op.append({"transport": tr, "n_sites": n, "n_workers": w, "op": op, "requests": len(rs),
                               "ok": oc["ok"], "rejected_409": oc["rejected"], "error": oc["error"], "timeout": oc["timeout"],
                               "transport_err": oc["transport"], "changed": sum(r["changed"] == "True" for r in rs),
                               "p50_ms": 1000 * pct(l, .5), "p95_ms": 1000 * pct(l, .95), "p99_ms": 1000 * pct(l, .99)})
    # bottleneck rule (H-S4)
    by_key = {(c["transport"], c["n_sites"], c["n_workers"]): c for c in cells}
    for c in cells:
        ws = sorted(w for (t, n, w) in by_key if t == c["transport"] and n == c["n_sites"])
        higher = [w for w in ws if w > c["n_workers"]]
        plateau = None
        if higher:
            nxt = by_key[(c["transport"], c["n_sites"], higher[0])]
            plateau = nxt["attempted_rps_mean"] <= (1 + PLATEAU) * c["attempted_rps_mean"]
        c["plateau_to_next_W"] = plateau
        if c["client_cores_mean"] >= CORE_RULE:
            c["bottleneck"] = "client-limited (load generator >= 0.85 core): not attributable to the service"
        elif plateau and c["evidence_cores_mean"] >= CORE_RULE:
            c["bottleneck"] = "evidence service"
        elif plateau and c["busiest_site_cores_mean"] >= CORE_RULE:
            c["bottleneck"] = "site service"
        else:
            c["bottleneck"] = "not attributable"
    ratios = []
    for (tr, n), byw in sorted(thr.items()):
        if n == 1:
            continue
        for w in (50, 100):
            if w in byw and w in thr.get((tr, 1), {}):
                r, lo, hi = boot_ratio(byw[w], thr[(tr, 1)][w])
                ratios.append({"transport": tr, "n_sites": n, "n_workers": w, "ratio_vs_n1": r, "ci95_lo": lo, "ci95_hi": hi,
                               "distribution_increases_throughput": lo > 1})
    for name, rows in (("cells.csv", cells), ("per_op.csv", per_op), ("ratios.csv", ratios)):
        if rows:
            with (a.out / name).open("w", newline="") as f:
                wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                wr.writeheader()
                wr.writerows(rows)
    (a.out / "summary.json").write_text(json.dumps({"cells": cells, "ratios": ratios}, indent=1) + "\n")
    lines = []
    for tr in sorted({c["transport"] for c in cells}):
        lines += [f"### {tr}", "", "| Sites | Writers | attempted req/s | ok req/s | state-changing/s | p50 / p95 / p99 ms | 409 | unexpected | client cores | evidence cores | bottleneck |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in sorted((c for c in cells if c["transport"] == tr), key=lambda c: (c["n_sites"], c["n_workers"])):
            lines.append(f"| {c['n_sites']} | {c['n_workers']} | {c['attempted_rps_mean']:.1f} ± {c['attempted_rps_sd']:.1f} | "
                         f"{c['ok_rps_mean']:.1f} | {c['changed_rps_mean']:.1f} | {c['p50_ms']:.1f} / {c['p95_ms']:.1f} / {c['p99_ms']:.1f} | "
                         f"{c['rejected_409']} | {c['error'] + c['timeout'] + c['transport_err']} | {c['client_cores_mean']:.2f} | "
                         f"{c['evidence_cores_mean']:.2f} | {c['bottleneck']} |")
        lines.append("")
        for r in (r for r in ratios if r["transport"] == tr):
            lines.append(f"- N={r['n_sites']} vs N=1 at W={r['n_workers']}: {r['ratio_vs_n1']:.2f}x [{r['ci95_lo']:.2f}, {r['ci95_hi']:.2f}]")
        lines.append("")
    (a.out / "table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
