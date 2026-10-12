#!/usr/bin/env python3
"""Diagnosis of the HTTP 500s of the episode setup (audit 98/101). Runs ON THE NODE through deploy_diag.sh (applier in user space, degraded). Brings up the 11-container deployment of arm C (mTLS) with the
tree's run.py machinery, then repeats the setup of run.py (seed a fact, /query + /commit on the 10 sites in parallel, identity op-site-<i>) for N facts WITHOUT any dispute. For every non-200 answer it
records the site, step, status, body and the site container's log of the last 20 s (docker logs), and classifies the last exception of the traceback found there.
Hypothesis (audit 101): the 500s are unhandled httpx errors (timeout/connect/read) of the call to the evidence made by the service. Usage: diag_setup500.py <tree> <out.json> [--facts 50] [--arm C]."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def classify_log(text: str) -> dict:
    """Last exception line of the LAST traceback in a container log and the service frame that raised it."""
    lines = text.splitlines()
    last_tb = max((i for i, l in enumerate(lines) if "Traceback (most recent call last)" in l), default=None)
    if last_tb is None:
        return {"exception": None, "frame": None}
    tb = lines[last_tb:]
    exc = None
    for l in tb[1:]:
        if re.match(r"^[A-Za-z_][\w.]*(Error|Exception|Timeout|Exit)\b.*", l.strip()) and not l.startswith(" "):
            exc = l.strip()
    frames = [l.strip() for l in tb if l.strip().startswith('File "') and "service.py" in l]
    return {"exception": exc, "frame": frames[-1] if frames else None}


def is_httpx_error(exc: str | None) -> bool:
    return bool(exc) and bool(re.match(r"^(httpx\.|httpcore\.)", exc))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("out")
    ap.add_argument("--facts", type=int, default=50)
    ap.add_argument("--arm", default="C")
    ap.add_argument("--pki", default=str(Path.home() / "dib_tnsm" / "pki"))
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.tree) / "experiments_tnsm" / "m67_retraction"))
    import run as r  # noqa: E402

    env = r.Env(a.tree, a.arm, 10, 5.0, Path(a.pki))
    env.up()
    rows, t_start = [], time.time()
    try:
        env.healthy()
        ok, rtt, bad, timing = r.wait_profile(env, "degraded", 90)
        if not ok:
            Path(a.out).write_text(json.dumps({"aborted": "profile check failed", "bad": bad}))
            return

        def one(i, ep, sid):
            res = []
            body = {"device_type": "cam-a", "endpoint": ep}
            for step in ("query", "commit"):
                t = time.time()
                try:
                    resp = env.req("POST", f"{env.site(i)}/{step}", f"op-site-{i}", 30.0, json=body)
                    st, txt = resp.status_code, resp.text[:160]
                except Exception as exc:  # noqa: BLE001
                    st, txt = None, repr(exc)[:160]
                res.append({"site": i, "step": step, "status": st, "body": txt, "t": t, "dt_s": time.time() - t})
                if st != 200:
                    break
            return res

        for n in range(a.facts):
            ep = f"diag500-{n}.example"
            sid = env.req("POST", f"{env.ev}/seed", "admin", 30.0, json={"device_type": "cam-a", "endpoint": ep}).json()["id"]
            with ThreadPoolExecutor(max_workers=10) as ex:
                per_site = list(ex.map(lambda i: one(i, ep, sid), range(10)))
            for res in per_site:
                for x in res:
                    if x["status"] != 200:
                        logtxt = env.logs(f"dibtnsm-site-{x['site']}-1", x["t"] - 20)
                        rows.append({"fact": n, **x, "classified": classify_log(logtxt), "log_tail": logtxt[-1500:]})
            time.sleep(0.5)
    finally:
        env.down()
        n500 = [x for x in rows if x["status"] == 500]
        Path(a.out).write_text(json.dumps({"arm": a.arm, "facts": a.facts, "n_non200": len(rows), "n_500": len(n500),
                                           "n_500_httpx": sum(1 for x in n500 if is_httpx_error(x["classified"]["exception"])),
                                           "started": t_start, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
