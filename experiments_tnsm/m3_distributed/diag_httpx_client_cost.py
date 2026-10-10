"""Micro-check of the mechanism behind the M3/M4 anomaly (audit 18 s.1.1). Candidate: in the
plain arm service.py makes every inter-service call with module-level httpx.get(...,
**_HTTP_TLS) where _HTTP_TLS = {} (service.py:161,381), so each call builds a Client with the
DEFAULT verify=True, i.e. a new SSL context (CA bundle load) even for http:// URLs; with mTLS
_HTTP_TLS = {"verify": <prebuilt SSLContext>} (service.py:167), so no bundle load per call.
Hypothesis H-X (stated before running): constructing httpx.Client() with the default
verify costs >= 2 ms more than httpx.Client(verify=<prebuilt context>) on this stack.
Falsified if the median difference is < 2 ms. Measures construction only (no network).
Usage: python3 diag_httpx_client_cost.py   (stdlib + httpx; also run inside the service image)
"""
import json, ssl, statistics, time
import httpx

def timeit(make, n=200):
    xs = []
    for _ in range(n):
        t = time.perf_counter(); c = make(); xs.append(time.perf_counter() - t); c.close()
    xs.sort()
    return {"median_ms": 1000 * xs[len(xs) // 2], "p95_ms": 1000 * xs[int(0.95 * n)], "n": n}

ctx = ssl.create_default_context()
res = {"httpx": httpx.__version__, "python": __import__("sys").version.split()[0],
       "default_verify": timeit(lambda: httpx.Client(timeout=5.0)),
       "prebuilt_ctx": timeit(lambda: httpx.Client(timeout=5.0, verify=ctx)),
       "verify_false": timeit(lambda: httpx.Client(timeout=5.0, verify=False))}
res["diff_median_ms"] = res["default_verify"]["median_ms"] - res["prebuilt_ctx"]["median_ms"]
res["H-X_supported"] = res["diff_median_ms"] >= 2.0
print(json.dumps(res, indent=1))
