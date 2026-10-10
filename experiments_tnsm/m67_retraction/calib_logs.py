"""Calibration of the log probe P-log (GATE 2, audit 14 s.3; audit 17/18). Runs ON THE NODE,
root namespace, with the dibtnsm cluster up (plain HTTP, profile lan). Stdlib only.

Measures the latency of the Docker log pipeline: for each request, t_send = time.time()
just before sending GET /health, then the timestamp that `docker logs -t` puts on the
uvicorn access-log line of that request (daemon receive time, same CLOCK_REALTIME).
latency = t_log - t_send (includes the request handling, which is ~ms at lan).
Two phases: (1) evidence only, sequential; (2) evidence and site-0 IN PARALLEL (two threads,
interleaved), to check the relative order and offset of the two containers' lines.
Declared before running: no hypothesis test; the output is the distribution (p50, p95, max)
used to fix, BEFORE the M6/M7 launch, the per-profile acceptance threshold of P-log
(p95 < 10% of the profile's median direct withdrawal; audit 14 s.2, C8).

Usage: python3 calib_logs.py --n 100 --out calib_logs.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import threading
import time
import urllib.request
from datetime import datetime

TARGETS = {"dibtnsm-evidence-1": "http://localhost:18100/health", "dibtnsm-site-0-1": "http://localhost:18110/health"}
DOCKER = "/snap/bin/docker"


_CONNS: dict = {}


def send(url: str, sink: list, fresh: bool = False) -> None:
    """GET /health. By default on a REUSED connection (warmed by the caller): through the userland docker-proxy a fresh
    connection adds one netem d before the request reaches the container, which would inflate the measured log latency by
    d at wan/degraded. `fresh=True` opens a new connection (diagnostic only)."""
    import http.client
    from urllib.parse import urlparse
    u = urlparse(url)
    key = (u.hostname, u.port)
    if fresh or key not in _CONNS:
        _CONNS[key] = http.client.HTTPConnection(u.hostname, u.port, timeout=5)
    c = _CONNS[key]
    t = time.time()
    c.request("GET", u.path)
    c.getresponse().read()
    sink.append(t)
    if fresh:
        c.close()
        _CONNS.pop(key, None)


def log_times(container: str, since: float) -> list[float]:
    out = subprocess.run([DOCKER, "logs", "-t", "--since", f"{since - 1:.3f}", container],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout
    ts = []
    for line in out.splitlines():
        if "GET /health" in line:
            stamp = line.split(" ", 1)[0]  # RFC3339Nano
            ts.append(datetime.fromisoformat(stamp[:26] + "+00:00" if stamp.endswith("Z") else stamp).timestamp())
    return sorted(t for t in ts if t >= since)


def stats(xs: list[float]) -> dict:
    xs = sorted(xs)
    if not xs:
        return {"n": 0}
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
    return {"n": len(xs), "p50_ms": 1000 * statistics.median(xs), "p95_ms": 1000 * q(0.95), "max_ms": 1000 * xs[-1],
            "min_ms": 1000 * xs[0]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--gap", type=float, default=0.05)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    for u in TARGETS.values():                       # warm-up: open the persistent connections, not measured
        send(u, [])
    time.sleep(0.5)
    # phase 1: evidence only
    t0 = time.time()
    sent = []
    for _ in range(a.n):
        send(TARGETS["dibtnsm-evidence-1"], sent)
        time.sleep(a.gap)
    time.sleep(1.0)
    logged = log_times("dibtnsm-evidence-1", t0)
    pairs = list(zip(sent, logged))
    res["single"] = {"sent": len(sent), "logged": len(logged), **stats([l - s for s, l in pairs])}
    # phase 2: evidence and site-0 in parallel
    t0 = time.time()
    sent2 = {c: [] for c in TARGETS}

    def loop(c):
        for _ in range(a.n):
            send(TARGETS[c], sent2[c])
            time.sleep(a.gap)

    th = [threading.Thread(target=loop, args=(c,)) for c in TARGETS]
    [t.start() for t in th]
    [t.join() for t in th]
    time.sleep(1.0)
    par = {}
    merged = []
    for c in TARGETS:
        lg = log_times(c, t0)
        lat = [l - s for s, l in zip(sent2[c], lg)]
        par[c] = {"sent": len(sent2[c]), "logged": len(lg), **stats(lat)}
        merged += [(s, l, c) for s, l in zip(sent2[c], lg)]
    # order check: is the log order (by docker timestamp) the same as the send order across containers?
    by_send = [c for _, _, c in sorted(merged, key=lambda x: x[0])]
    by_log = [c for _, _, c in sorted(merged, key=lambda x: x[1])]
    inversions = sum(1 for i in range(len(merged)) if by_send[i] != by_log[i])
    res["parallel"] = par
    res["parallel_order_mismatch_positions"] = inversions
    res["parallel_offset_p50_ms"] = (par["dibtnsm-site-0-1"].get("p50_ms", 0) - par["dibtnsm-evidence-1"].get("p50_ms", 0))
    # phase 3 (diagnostic): FRESH connections to evidence, to show the docker-proxy dial effect (+d under netem)
    t0 = time.time()
    sent3 = []
    for _ in range(min(a.n, 30)):
        send(TARGETS["dibtnsm-evidence-1"], sent3, fresh=True)
        time.sleep(a.gap)
    time.sleep(1.0)
    lg3 = log_times("dibtnsm-evidence-1", t0)
    res["fresh_connection_diagnostic"] = {"sent": len(sent3), "logged": len(lg3), **stats([l - s for s, l in zip(sent3, lg3)])}
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
