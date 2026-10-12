#!/usr/bin/env python3
"""Diagnostic (docs/audit/72), runs ON the node at `lan` (no watcher): latency of each POST /dispute (x2) and /restore with site-3 DEAD, arms D and C,
k = 10 facts per repetition, 2 repetitions per arm, per-call client timeout 120 s so the real latency is observed (the registered B2k client timeout is 18 s at lan).
Pre-registered hypothesis (before running): per-call latency with a dead site is the same in D and C and about 3 s (3 attempts x 1 s connect timeout to the dead site,
service.py:120-121), i.e. median <= 4 s and max <= 9 s in BOTH arms; if the D arm shows calls beyond 18 s, or a latency that grows with the call index, the D-arm
client timeouts of audits 57/69/71 come from the service side and not from the harness. Falsified by D median > 4 s or D max > 9 s (the C arm is the control).
Usage: python3 diag_dead_site_latency.py --tree <tree> --out <file.json>"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--reps", type=int, default=2)
    a = ap.parse_args()
    tree = Path(a.tree)
    sys.path.insert(0, str(tree / "experiments_tnsm" / "m67_retraction"))
    sys.path.insert(0, str(tree / "experiments_tnsm" / "common"))
    import run as r
    pki = Path.home() / "dib_tnsm" / "pki"
    out = {"k": a.k, "reps": a.reps, "arms": {}}
    for arm in ("D", "C"):
        env = r.Env(str(tree), arm, 10, 5.0, pki)
        env.up()
        calls = []
        try:
            env.healthy()
            time.sleep(8)
            for rep in range(a.reps):
                eps = [f"diag-{arm}-r{rep}-{j}.example" for j in range(a.k)]
                for ep in eps:
                    body = {"device_type": "cam-a", "endpoint": ep}
                    env.req("POST", f"{env.ev}/seed", "admin", 30.0, json=body)
                    env.req("POST", f"{env.site(3)}/query", "op-site-3", 30.0, json=body)
                    env.req("POST", f"{env.site(3)}/commit", "op-site-3", 30.0, json=body)
                env.sh(env.compose() + "kill site-3")
                idx = 0
                for ep in eps:
                    body = {"device_type": "cam-a", "endpoint": ep}
                    for path, ident, extra in (("/dispute", "op-site-1", {"site_id": "site-1"}), ("/dispute", "op-site-2", {"site_id": "site-2"}), ("/restore", "admin", {})):
                        env.warm(ident)
                        t0 = time.perf_counter()
                        err = None
                        try:
                            env.req("POST", f"{env.ev}{path}", ident, 120.0, json={**body, **extra})
                        except Exception as exc:  # noqa: BLE001
                            err = f"{type(exc).__name__}: {str(exc)[:80]}"
                        calls.append({"rep": rep, "idx": idx, "path": path, "s": time.perf_counter() - t0, "err": err})
                        idx += 1
                env.sh(env.compose() + "start site-3")
                time.sleep(20)       # let site-3 reconcile before the next repetition
        finally:
            env.down()
        s = [c["s"] for c in calls if c["err"] is None]
        out["arms"][arm] = {"calls": calls, "n": len(calls), "errors": sum(1 for c in calls if c["err"]),
                            "median_s": statistics.median(s) if s else None, "max_s": max(s) if s else None,
                            "p95_s": sorted(s)[int(0.95 * (len(s) - 1))] if s else None}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: {x: v[x] for x in ("n", "errors", "median_s", "p95_s", "max_s")} for k, v in out["arms"].items()}))


if __name__ == "__main__":
    main()
