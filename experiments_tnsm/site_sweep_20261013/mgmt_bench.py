"""Management-path benchmark of the distributed service (pre-registration: docs/audit/123).

Corrects code/scripts/distributed_concurrency_benchmark.py (kept unchanged: other
campaigns import it) on three points, and reuses its routing, identities, seeding
and transport (one shared httpx.Client, timeout 5 s; mTLS clients per identity):

1. `contribute` is removed from the mix. The distributed prototype has no
   observation endpoint, so the old benchmark counted 2 client-side no-ops in every
   20 operations. MIX = the old _MIX_REALISTIC without them (18 entries: query x8,
   commit x7, attest x1, dispute x1, restore x1). This is a MANAGEMENT-PATH
   benchmark, not a contribution benchmark.
2. Every response is classified: ok (2xx), rejected (409: lifecycle conflict the
   API is designed to return, e.g. commit of an already Active fact, restore of an
   undisputed fact), error (any other status, incl. 403/5xx), timeout, transport
   (other client exceptions). `applied` is recorded when the body has it.
   The old benchmark counted every non-403 answer as a success.
3. Raw per-request records (op, status, outcome, latency) are kept, so per-type and
   pooled p50/p95/p99 are computed from all requests of a cell, not averaged per
   repetition.

No retries. Throughputs reported: attempted requests/s (all requests that reached
the wire), ok/s, state-changing/s (commit 200, restore 200, attest 200, dispute
200 with applied=true).
"""
from __future__ import annotations

import csv
import gzip
import resource
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "scripts"))
import distributed_concurrency_benchmark as base  # noqa: E402

MIX = [op for op in base._MIX_REALISTIC if op != "contribute"]
assert len(MIX) == 18


def classify(resp) -> tuple[str, bool | None]:
    if 200 <= resp.status_code < 300:
        applied = None
        try:
            body = resp.json()
            if isinstance(body, dict) and "applied" in body:
                applied = bool(body["applied"])
        except ValueError:
            pass
        return "ok", applied
    if resp.status_code == 409:
        return "rejected", None
    return "error", None


def do_op(worker_id: int, op_index: int, t_origin: float) -> dict:
    site_index = worker_id % base.N_SITES
    device_type = ("cam-a", "cam-b", "cam-c")[worker_id % 3]
    endpoint = f"ep-{op_index % 5}.example"
    op = MIX[op_index % len(MIX)]
    body = {"device_type": device_type, "endpoint": endpoint}
    _target, identity = base.route(op, site_index)
    client = base._client_for(identity)
    status, outcome, applied = None, None, None
    started = time.perf_counter()
    try:
        if op == "query":
            resp = client.post(f"{base.site_url(site_index)}/query", json=body)
        elif op == "commit":
            resp = client.post(f"{base.site_url(site_index)}/commit", json=body)
        elif op == "attest":
            resp = client.post(f"{base.EVIDENCE_URL}/attest", json={**body, "site_id": f"site-{site_index}"})
        elif op == "dispute":
            resp = client.post(f"{base.EVIDENCE_URL}/dispute", json={**body, "site_id": f"site-{site_index}"})
        else:
            resp = client.post(f"{base.EVIDENCE_URL}/restore", json=body)
        status = resp.status_code
        outcome, applied = classify(resp)
    except Exception as exc:  # noqa: BLE001 - classified
        name = type(exc).__name__
        outcome = "timeout" if "Timeout" in name else "transport"
        status = name
    latency = time.perf_counter() - started
    changed = (outcome == "ok" and (op in ("commit", "restore", "attest") or (op == "dispute" and applied)))
    return {"worker": worker_id, "op": op, "site": site_index, "status": status, "outcome": outcome,
            "applied": applied, "changed": changed, "t_start": started - t_origin, "latency_s": latency}


def run_batch(n_workers: int, ops_per_worker: int) -> tuple[list[dict], float]:
    t_origin = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = [pool.submit(do_op, w, o, t_origin) for w in range(n_workers) for o in range(ops_per_worker)]
        records = [f.result() for f in futures]
    return records, time.perf_counter() - t_origin


def client_cpu_s() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def run_cell(n_workers: int, ops_per_worker: int, repeats: int, warmup_ops: int, raw_path: Path, sampler=None) -> dict:
    if warmup_ops > 0:
        run_batch(n_workers, warmup_ops)  # discarded, including its errors (as the old benchmark)
    reps = []
    with gzip.open(raw_path, "wt", newline="") as f:
        w = None
        for rep in range(repeats):
            if sampler:
                sampler.begin()
            cpu0 = client_cpu_s()
            records, wall = run_batch(n_workers, ops_per_worker)
            cpu1 = client_cpu_s()
            res = sampler.end() if sampler else {}
            for r in records:
                r["rep"] = rep
            if w is None:
                w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
                w.writeheader()
            w.writerows(records)
            reps.append({"rep": rep, "wall_s": wall, "requests": len(records),
                         "ok": sum(r["outcome"] == "ok" for r in records),
                         "rejected": sum(r["outcome"] == "rejected" for r in records),
                         "error": sum(r["outcome"] == "error" for r in records),
                         "timeout": sum(r["outcome"] == "timeout" for r in records),
                         "transport": sum(r["outcome"] == "transport" for r in records),
                         "changed": sum(bool(r["changed"]) for r in records),
                         "client_cpu_s": cpu1 - cpu0, **res})
    return {"n_workers": n_workers, "ops_per_worker": ops_per_worker, "repeats": reps}
