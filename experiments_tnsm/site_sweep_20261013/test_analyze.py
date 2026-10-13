"""analyze.py on a synthetic sweep: the H-S4 rule and the ratio CI must behave as pre-registered.

Hypotheses: a cell whose load generator uses >= 0.85 core is never attributed to a
service component; a plateau with the evidence at >= 0.85 core is attributed to it;
a ratio whose CI lies above 1 is flagged. Falsification: any assertion below.
"""
import csv
import gzip
import json

import analyze


def write_run(d, transport, cells):
    d.mkdir()
    man = {"transport": transport, "cells": []}
    for n, w, rps, client, ev in cells:
        reps = []
        for rep in range(5):
            wall = 10.0
            reps.append({"rep": rep, "wall_s": wall, "requests": int(rps * wall) + rep, "ok": int(rps * wall * .6),
                         "rejected": int(rps * wall * .4), "error": 0, "timeout": 0, "transport": 0, "changed": 5,
                         "client_cpu_s": client * wall,
                         "container_cpu_s": {"evidence": ev * wall, "site-0": 0.2 * wall},
                         "container_mem_max_bytes": {"evidence": 2 ** 26, "site-0": 2 ** 25},
                         "host_busy_fraction": 0.5, "loadavg": [9.0, 9.0, 9.0]})
        man["cells"].append({"n_sites": n, "n_workers": w, "ops_per_worker": 20, "repeats": reps})
        with gzip.open(d / f"raw_n{n}_w{w}.csv.gz", "wt", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["op", "outcome", "status", "latency_s", "changed"])
            wr.writeheader()
            for i in range(200):
                wr.writerow({"op": "commit" if i % 2 else "query", "outcome": "ok" if i % 3 else "rejected",
                             "status": 200 if i % 3 else 409, "latency_s": 0.001 * (i + 1), "changed": "True" if i % 2 else "False"})
    (d / "manifest.json").write_text(json.dumps(man))


def test_rules(tmp_path, monkeypatch):
    write_run(tmp_path / "run", "http", [
        (1, 50, 300.0, 0.3, 0.95), (1, 100, 310.0, 0.3, 0.97),      # plateau, evidence busy -> evidence
        (2, 50, 600.0, 0.9, 0.5), (2, 100, 900.0, 0.95, 0.5),       # client >= 0.85 -> not attributable
    ])
    monkeypatch.setattr("sys.argv", ["analyze.py", str(tmp_path / "run"), "--out", str(tmp_path / "out")])
    assert analyze.main() == 0
    s = json.loads((tmp_path / "out" / "summary.json").read_text())
    cell = {(c["n_sites"], c["n_workers"]): c for c in s["cells"]}
    assert cell[(1, 50)]["bottleneck"] == "evidence service"
    assert cell[(2, 50)]["bottleneck"].startswith("client-limited")
    r = {(x["n_sites"], x["n_workers"]): x for x in s["ratios"]}
    assert r[(2, 50)]["distribution_increases_throughput"] is True
    assert r[(2, 50)]["ci95_lo"] > 1.9
