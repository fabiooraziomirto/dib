#!/usr/bin/env python3
"""Diagnostic (docs/audit/72), at lan, arm D, no watcher: back-to-back getaddrinfo('site-3') from the evidence container while site-3 is KILLED
(Docker's embedded DNS answers NXDOMAIN for the vanished name, possibly after asking the upstream resolver). Pre-registered hypothesis (before running): in a burst
of 2000 resolutions at the rate of a k = 50 B2k trial (~45 per second) some calls stall for >= 1 s, with durations clustered near multiples of ~4-5 s (the 4.02 /
8.03 / 16.03 / 24.03 s calls of diag_dead_site_latency.py k = 50); at 4 Hz (diag_arp_probe.py, 589 calls, max 0.024 s) there is no stall. Falsified if no call
among the 2000 takes >= 1 s. Usage: python3 diag_dns_burst.py --tree <tree> --out <file.json>"""
import argparse
import json
import sys
import time
from pathlib import Path

PROBE = ("import socket,time,json\n"
         "res=[]\n"
         "for i in range(%d):\n"
         "    a=time.perf_counter()\n"
         "    try:\n"
         "        socket.getaddrinfo('site-3',8000)\n"
         "        e='ok'\n"
         "    except Exception as x:\n"
         "        e=type(x).__name__+':'+str(getattr(x,'errno',''))\n"
         "    res.append((i,round(time.perf_counter()-a,4),e))\n"
         "print(json.dumps(res))\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=2000)
    a = ap.parse_args()
    tree = Path(a.tree)
    sys.path.insert(0, str(tree / "experiments_tnsm" / "m67_retraction"))
    sys.path.insert(0, str(tree / "experiments_tnsm" / "common"))
    import run as r
    env = r.Env(str(tree), "D", 10, 5.0, Path.home() / "dib_tnsm" / "pki")
    env.up()
    out = {}
    try:
        env.healthy()
        time.sleep(8)
        resolv = env.sh("/snap/bin/docker exec dibtnsm-evidence-1 cat /etc/resolv.conf", check=False)
        env.sh(env.compose() + "kill site-3")
        t0 = time.time()
        raw = env.sh(f"/snap/bin/docker exec dibtnsm-evidence-1 python -c \"{PROBE % a.n}\"", check=False, timeout=900)
        res = json.loads(raw.strip().splitlines()[-1])
        slow = [x for x in res if x[1] >= 1.0]
        out = {"resolv_conf": resolv, "n": len(res), "wall_s": round(time.time() - t0, 1), "slow_ge_1s": slow, "max_s": max(x[1] for x in res),
               "errors": sorted({x[2] for x in res}), "durations_sorted_tail": sorted(x[1] for x in res)[-20:]}
    finally:
        env.down()
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n", "wall_s", "max_s", "errors")}), "slow>=1s:", len(out.get("slow_ge_1s", [])))


if __name__ == "__main__":
    main()
