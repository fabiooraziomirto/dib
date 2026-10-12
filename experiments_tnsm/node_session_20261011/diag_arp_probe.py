#!/usr/bin/env python3
"""Diagnostic (docs/audit/72): connect-time probe from the evidence container to a KILLED site-3 (docker compose kill), at lan, arm D, no watcher.
Pre-registered hypothesis (before running): the multi-second stalls (multiples of ~4 s) of POST /dispute and /restore seen with k = 50 (diag_dead_site_latency.py)
come from the network layer of the harness (L2 neighbour resolution of the killed container's IP), not from DIB code: the connect time of a probe to the dead
site is ~0 s (refused/unreachable) most of the time and shows periodic plateaus of ~1-4 s, aligned with changes of the state of the neighbour entry in the
evidence container's /proc/net/arp. Falsified if the probe sees NO plateau > 0.5 s in 150 s, or plateaus not related to any /proc/net/arp change.
Usage: python3 diag_arp_probe.py --tree <tree> --out <file.json> [--seconds 150]"""
import argparse
import json
import sys
import time
from pathlib import Path

PROBE = ("import socket,time,json,sys\n"
         "t0=time.time();res=[]\n"
         "while time.time()-t0<%d:\n"
         "    a=time.perf_counter()\n"
         "    s=socket.socket();s.settimeout(5.0)\n"
         "    try:\n"
         "        s.connect(('site-3',8000));e='connected'\n"
         "    except Exception as x:\n"
         "        e=type(x).__name__+':'+str(getattr(x,'errno',''))\n"
         "    s.close()\n"
         "    res.append((round(time.time()-t0,2),round(time.perf_counter()-a,3),e))\n"
         "    time.sleep(0.25)\n"
         "print(json.dumps(res))\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=int, default=150)
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
        arp_before = env.sh("/snap/bin/docker exec dibtnsm-evidence-1 cat /proc/net/arp", check=False)
        env.sh(env.compose() + "kill site-3")
        t_kill = time.time()
        import subprocess, threading
        snaps = []

        def sample():
            while time.time() - t_kill < a.seconds + 5:
                snaps.append((round(time.time() - t_kill, 1), env.sh("/snap/bin/docker exec dibtnsm-evidence-1 cat /proc/net/arp", check=False)))
                time.sleep(2.0)
        th = threading.Thread(target=sample)
        th.start()
        probe = env.sh(f"/snap/bin/docker exec dibtnsm-evidence-1 python -c \"{PROBE % a.seconds}\"", check=False, timeout=a.seconds + 60)
        th.join()
        out = {"arp_before_kill": arp_before, "snapshots": snaps, "probe_raw": probe[-200000:]}
        try:
            res = json.loads(probe.strip().splitlines()[-1])
            out["probe"] = res
            slow = [x for x in res if x[1] > 0.5]
            out["summary"] = {"n": len(res), "slow_gt_0.5s": len(slow), "max_s": max(x[1] for x in res), "errors": sorted({x[2] for x in res})}
        except Exception as exc:  # noqa: BLE001
            out["summary"] = {"parse_error": str(exc)}
    finally:
        env.down()
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out.get("summary")))


if __name__ == "__main__":
    main()
