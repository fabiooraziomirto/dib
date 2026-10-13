"""Lifecycle-mix sweep: every request is a state change (pre-registration: docs/audit/130).

Each writer w owns one fact (device type cam-a/b/c by w % 3, endpoint lc-<cell>-w<w>.example),
seeded by the admin and queried at its site (w % N) before the timed batch, so the record is
MonitorOnly. The writer then runs, strictly in sequence, the cycle
    commit (site, MonitorOnly -> Active) ; dispute (evidence, Active -> Disputed, fan-out to
    every site) ; restore (admin, Disputed -> MonitorOnly, fan-out)
ops_per_worker times (a multiple of 3). Every request is expected to be a 2xx state change; a
409 is recorded as `rejected` and counted as UNEXPECTED here (it would mean a race in the
service or the harness), never as a success. Same transport, identities, topology, provenance
check and resource sampling as sweep.py; no retries; warm-up = one cycle per writer on separate
facts, discarded.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mgmt_bench  # noqa: E402
import sweep  # noqa: E402

base = mgmt_bench.base
CYCLE = ("commit", "dispute", "restore")


def fact(cell: str, w: int) -> dict:
    return {"device_type": ("cam-a", "cam-b", "cam-c")[w % 3], "endpoint": f"lc-{cell}-w{w}.example"}


def prepare(cell: str, n_workers: int) -> None:
    """Setup, not timed: seed and query each writer's fact at its site. Raises on any non-200."""
    for w in range(n_workers):
        body = fact(cell, w)
        r = base._client_for("admin" if base._MTLS else None).post(f"{base.EVIDENCE_URL}/seed", json=body)
        r.raise_for_status()
        site = w % base.N_SITES
        r = base._client_for(base.route("query", site)[1]).post(f"{base.site_url(site)}/query", json=body)
        r.raise_for_status()
        if not r.json().get("applied"):
            raise RuntimeError(f"query not applied for {body}")


def request(op: str, w: int, body: dict):
    site = w % base.N_SITES
    _t, identity = base.route(op, site)
    client = base._client_for(identity)
    if op == "commit":
        return client.post(f"{base.site_url(site)}/commit", json=body)
    if op == "dispute":
        return client.post(f"{base.EVIDENCE_URL}/dispute", json={**body, "site_id": f"site-{site}"})
    return client.post(f"{base.EVIDENCE_URL}/restore", json=body)


def worker(w: int, cell: str, n_ops: int, t_origin: float) -> list[dict]:
    body, out = fact(cell, w), []
    for k in range(n_ops):
        op = CYCLE[k % 3]
        started = time.perf_counter()
        status, outcome, applied = None, None, None
        try:
            resp = request(op, w, body)
            status = resp.status_code
            outcome, applied = mgmt_bench.classify(resp)
        except Exception as exc:  # noqa: BLE001 - classified
            name = type(exc).__name__
            outcome, status = ("timeout" if "Timeout" in name else "transport"), name
        lat = time.perf_counter() - started
        changed = outcome == "ok" and (op != "dispute" or bool(applied))
        out.append({"worker": w, "op": op, "site": w % base.N_SITES, "status": status, "outcome": outcome,
                    "applied": applied, "changed": changed, "t_start": started - t_origin, "latency_s": lat})
    return out


def run_batch(cell: str, n_workers: int, n_ops: int) -> tuple[list[dict], float]:
    t_origin = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n_workers) as pool:  # ONE future per writer: its ops stay sequential
        parts = list(pool.map(lambda w: worker(w, cell, n_ops, t_origin), range(n_workers)))
    return [r for p in parts for r in p], time.perf_counter() - t_origin


def run_cell(tag: str, n_workers: int, n_ops: int, repeats: int, raw: Path, sampler) -> dict:
    prepare(f"{tag}-warm", n_workers)
    run_batch(f"{tag}-warm", n_workers, 3)  # warm-up, discarded
    reps = []
    with gzip.open(raw, "wt", newline="") as f:
        wr = None
        for rep in range(repeats):
            cell = f"{tag}-r{rep}"
            prepare(cell, n_workers)
            sampler.begin()
            cpu0 = mgmt_bench.client_cpu_s()
            records, wall = run_batch(cell, n_workers, n_ops)
            cpu1 = mgmt_bench.client_cpu_s()
            res = sampler.end()
            for r in records:
                r["rep"] = rep
            if wr is None:
                wr = csv.DictWriter(f, fieldnames=list(records[0].keys()))
                wr.writeheader()
            wr.writerows(records)
            reps.append({"rep": rep, "wall_s": wall, "requests": len(records),
                         **{k: sum(r["outcome"] == k for r in records) for k in ("ok", "rejected", "error", "timeout", "transport")},
                         "changed": sum(bool(r["changed"]) for r in records), "client_cpu_s": cpu1 - cpu0, **res})
    return {"n_workers": n_workers, "ops_per_worker": n_ops, "repeats": reps}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--transport", choices=["http", "mtls"], required=True)
    ap.add_argument("--pki", type=Path)
    ap.add_argument("--sites", default="1,2,5,10")
    ap.add_argument("--workers", default="1,10,50,100")
    ap.add_argument("--repeats", type=int, default=5)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    mtls = a.transport == "mtls"
    if mtls:
        from scripts.make_dist_pki import build
        nb = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)
        (a.out / "pki_manifest.json").write_text(json.dumps(build(a.pki, 10, nb, 72.0, ["cam-a", "cam-b", "cam-c"]), indent=1) + "\n")
    man = {"prereg": "docs/audit/130", "transport": a.transport, "mix": "per-writer cycle " + "/".join(CYCLE),
           "started_utc": datetime.now(timezone.utc).isoformat(),
           "commit": sweep.run(["git", "rev-parse", "HEAD"], cwd=sweep.ROOT).stdout.strip(),
           "dirty": sweep.run(["git", "status", "--porcelain"], cwd=sweep.ROOT).stdout.splitlines(),
           "tree_sha256": {str(p.relative_to(sweep.ROOT)): sweep.sha(p) for p in [sweep.DIST / "service.py", sweep.DIST / "mtls.py",
                           HERE / "lifecycle_bench.py", HERE / "mgmt_bench.py", HERE / "sweep.py"]},
           "python": sys.version.split()[0], "cells": []}
    try:
        for n in [int(x) for x in a.sites.split(",")]:
            ids = sweep.up(n, mtls, a.pki, a.out)
            man.setdefault("containers", {})[str(n)] = sweep.verify(ids)
            scheme = "https" if mtls else "http"
            base.configure(evidence_url=f"{scheme}://localhost:18100",
                           site_urls=[f"{scheme}://localhost:{18110 + i}" for i in range(n)], pki_dir=a.pki if mtls else None)
            sampler = sweep.Sampler(ids)
            for w in [int(x) for x in a.workers.split(",")]:
                n_ops = 3 * max(10, 300 // w)
                cell = run_cell(f"n{n}w{w}", w, n_ops, a.repeats, a.out / f"raw_n{n}_w{w}.csv.gz", sampler)
                cell.update(n_sites=n, transport=a.transport)
                man["cells"].append(cell)
                print(f"N={n} W={w}: " + ", ".join(f"{x['requests'] / x['wall_s']:.0f} req/s ok={x['ok']} rej={x['rejected']} "
                                                  f"err={x['error'] + x['timeout'] + x['transport']}" for x in cell["repeats"]), flush=True)
                (a.out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
            man.setdefault("containers_end", {})[str(n)] = sweep.verify(ids)
            sweep.down(a.out, n)
    except Exception as exc:  # noqa: BLE001
        man["fatal"] = f"{type(exc).__name__}: {exc}"
        print("FATAL", man["fatal"], flush=True)
    finally:
        man["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (a.out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
        for n in [int(x) for x in a.sites.split(",")]:
            if (a.out / f"compose_n{n}.yml").exists():
                sweep.down(a.out, n)
    return 0 if "fatal" not in man else 2


if __name__ == "__main__":
    raise SystemExit(main())
