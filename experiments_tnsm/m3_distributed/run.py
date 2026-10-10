"""M3/M4 (plan rev. 5, Passo 3; audit 04 s.2, audit 14, audit 17): distributed deployment
on the node, fan-out concurrency and cost of mTLS. Runs on THIS host (the load generator);
the services run in Docker on the node 192.168.100.57 (compose project "dibtnsm").

Deliberate difference from M6/M7 (declared in the manifest): here the generator is on
another host, so as not to take CPU from the services under load; in M6/M7 it runs on the
node (single clock for the log probe). Absolute latencies of M3/M4 and M6/M7 are NOT
comparable (M3/M4 include the LAN hop, ~0.17 ms RTT, audit 04 s.7.2).

Arms: FANOUT_CONCURRENCY in {1, 10} x mTLS in {off, on} = 4 arms. 10 repetitions; in each
repetition the 4 arms run in an order shuffled with --seed (arms alternate, never in
blocks). One cell = (arm, repetition): the cluster is recreated from scratch
(`docker compose down -v`, then `up -d` with the arm's compose file, fresh databases), then
the unmodified benchmark (code/scripts/distributed_concurrency_benchmark.py) runs once
(--repeats 1) with writer counts 1, 10, 50, 100 in an order shuffled per cell, 200 timed
operations per worker after 20 warm-up operations per worker (discarded).
Compose files: generate_compose.py with DIB_DIST_FANOUT_CONCURRENCY and DIB_DIST_MTLS
(DIB_DIST_PKI_DIR = the node's PKI copy); everything else as committed (reconcile
trigger T = 5 s, jitter 0.5 s). mTLS arm: certificates from make_dist_pki.py with
--extra-san-ip 192.168.100.57 (one SAN more than the default, so that this host can verify
the node's IP; recorded in the manifest with the script hash).

Hypotheses (stated before running)
  H-M3a  Under the realistic mix only dispute/restore fan out (10% of operations), so the
         fan-out concurrency is not the throughput bottleneck: at 100 writers the mean
         throughput with FANOUT 10 is within +-10% of FANOUT 1 (mTLS off). Falsified if the
         95% bootstrap CI of the ratio FANOUT10/FANOUT1 lies entirely outside [0.9, 1.1].
         (The audit 04 M3 comparison N = 10 vs N = 1 needs N = 1 and moves to M5.)
  H-M3b  No unexpected errors in any cell (in particular no http.403 in the mTLS arms).
         Falsified by one cell with unexpected_errors > 0.
  H-M4   mTLS costs <= 20% of throughput at 100 writers and <= 5 ms of p50 at 1 writer
         (FANOUT 10). The client reuses connections (httpx.Client); between services there
         is no pool (audit 13 s.9.1), so this is an UPPER BOUND of the mTLS cost.
         Falsified if the CI of the throughput ratio mTLS/plain lies entirely below 0.8, or
         the CI of the p50 difference lies entirely above 5 ms.
Statistics: unit = cell; mean with 95% percentile bootstrap CI over cells (10000
resamples, seed 20261010); ratios via paired-by-repetition bootstrap. Node background load
is recorded before and after each cell (loadavg and top processes); no cell is discarded
silently.

Usage: python3 run.py --out <dir> --pki-local <dir> [--reps 10] [--pilot]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NODE = "ubuntu@192.168.100.57"
NODE_IP = "192.168.100.57"
SSH = ["ssh", "-o", "BatchMode=yes", "-i", str(Path.home() / ".ssh/id_ed25519_lab"), NODE]
ARMS = [(f, m) for f in (1, 10) for m in (0, 1)]
WRITERS = [1, 10, 50, 100]


def sh_node(cmd: str, check=True, timeout=900) -> str:
    r = subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"node command failed ({r.returncode}): {cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def compose_cmd(tree: str, arm) -> str:
    f, m = arm
    dist = f"{tree}/code/src/dib/registry/distributed"
    env = (f"DIB_DIST_FANOUT_CONCURRENCY={f} DIB_DIST_MTLS={m} DIB_DIST_PKI_DIR=$HOME/dib_tnsm/pki")
    return (f"export PATH=/snap/bin:$PATH && cd {dist} && mkdir -p $HOME/dib_tnsm/m3 && "
            f"{env} python3 generate_compose.py > $HOME/dib_tnsm/m3/compose_f{f}_m{m}.yml && "
            f"docker compose -p dibtnsm -f $HOME/dib_tnsm/m3/compose_f{f}_m{m}.yml --project-directory {dist} ")


def wait_healthy(arm, timeout=90) -> float:
    f, m = arm
    scheme = "https" if m else "http"
    t0 = time.time()
    # health from the node itself (localhost SAN), so readiness does not depend on this host's client
    probe = ("python3 - <<'EOF'\nimport ssl,urllib.request,time,sys\n"
             f"urls=['{scheme}://localhost:18100/health']+['{scheme}://localhost:%d/health'%(18110+i) for i in range(10)]\n"
             "ctx=None\n"
             + ("ctx=ssl.create_default_context(cafile='/home/ubuntu/dib_tnsm/pki/ca.crt');"
                "ctx.load_cert_chain('/home/ubuntu/dib_tnsm/pki/admin.crt','/home/ubuntu/dib_tnsm/pki/admin.key')\n" if m else "")
             + "deadline=time.time()+80\nok=set()\nwhile time.time()<deadline and len(ok)<len(urls):\n"
             "  for u in urls:\n    if u in ok: continue\n    try:\n"
             "      urllib.request.urlopen(u,timeout=1,context=ctx); ok.add(u)\n    except Exception: pass\n"
             "  time.sleep(0.2)\nprint(len(ok)); sys.exit(0 if len(ok)==len(urls) else 1)\nEOF")
    sh_node(probe, timeout=timeout)
    return time.time() - t0


def node_load() -> dict:
    out = sh_node("cat /proc/loadavg; ps -eo pcpu,comm --sort=-pcpu | sed -n 2,6p")
    lines = out.strip().splitlines()
    return {"loadavg": lines[0], "top": lines[1:]}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--pki-local", required=True, help="local copy of the node PKI (client identities)")
    ap.add_argument("--tree", required=True, help="tree on the node, e.g. ~/dib_tnsm/tree-<commit>")
    ap.add_argument("--commit", required=True)
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--ops-per-worker", type=int, default=200)
    ap.add_argument("--warmup-ops", type=int, default=20)
    ap.add_argument("--pilot", action="store_true", help="one cell (FANOUT 10, mTLS on), writers 1,10")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    cells = []
    if a.pilot:
        cells = [((10, 1), 0)]
    else:
        for rep in range(a.reps):
            order = ARMS[:]
            rng.shuffle(order)
            cells += [(arm, rep) for arm in order]
    pki_manifest = json.loads((Path(a.pki_local) / "pki_manifest.json").read_text())
    bench = ROOT / "code/scripts/distributed_concurrency_benchmark.py"
    manifest = {
        "started_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv, "commit": a.commit,
        "seed": a.seed, "cells": [[list(c[0]), c[1]] for c in cells],
        "generator_host": platform.node(), "generator_python": sys.version, "node": NODE_IP,
        "deliberate_difference": "generator on another host than the services (M6/M7: on the node); "
                                 "absolute latencies not comparable with M6/M7",
        "pki": {"extra_san_ip": pki_manifest.get("extra_san_ip"), "not_after": pki_manifest.get("not_after"),
                "make_dist_pki_sha256": sha(ROOT / "code/scripts/make_dist_pki.py"),
                "note": "mTLS certificates carry one more SAN (IP of the node) than the default"},
        "sha256": {"benchmark": sha(bench), "run.py": sha(Path(__file__)),
                   "service.py": sha(ROOT / "code/src/dib/registry/distributed/service.py"),
                   "generate_compose.py": sha(ROOT / "code/src/dib/registry/distributed/generate_compose.py")},
        "node_service_sha256": sh_node(f"sha256sum {a.tree}/code/src/dib/registry/distributed/service.py").split()[0],
        "disk_node_start": sh_node("df -h / | tail -1").strip(),
        "disk_host_start": subprocess.run(["df", "-h", "/root/Desktop"], capture_output=True, text=True).stdout.splitlines()[-1],
    }
    log = (out / "cells.jsonl").open("a")
    for k, (arm, rep) in enumerate(cells):
        f, m = arm
        writers = [1, 10] if a.pilot else WRITERS[:]
        if not a.pilot:
            rng.shuffle(writers)
        base = compose_cmd(a.tree, arm)
        sh_node(base + "down -v --remove-orphans", check=False)
        sh_node(base + ("up -d --build" if k == 0 else "up -d"))
        t_ready = wait_healthy(arm)
        before = node_load()
        csv_path = out / f"cell_{k:03d}_f{f}_m{m}_r{rep}.csv"
        scheme = "https" if m else "http"
        cmd = [sys.executable, str(bench), "--worker-counts", ",".join(map(str, writers)),
               "--ops-per-worker", str(a.ops_per_worker), "--warmup-ops", str(a.warmup_ops), "--repeats", "1",
               "--output", str(csv_path), "--evidence-url", f"{scheme}://{NODE_IP}:18100",
               "--site-urls", ",".join(f"{scheme}://{NODE_IP}:{18110 + i}" for i in range(10))]
        if m:
            cmd += ["--pki", a.pki_local]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        wall = time.time() - t0
        after = node_load()
        (out / f"cell_{k:03d}.log").write_text(r.stdout + r.stderr)
        rows = list(csv.DictReader(csv_path.open())) if csv_path.exists() else []
        rec = {"cell": k, "fanout": f, "mtls": m, "rep": rep, "writer_order": writers, "returncode": r.returncode,
               "ready_s": round(t_ready, 2), "wall_s": round(wall, 1), "rows": rows,
               "node_before": before, "node_after": after}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(f"[{k + 1}/{len(cells)}] f={f} m={m} rep={rep} rc={r.returncode} wall={wall:.0f}s "
              + " ".join(f"{x['n_workers']}:{x['throughput_ops_per_sec_mean']}" for x in rows), flush=True)
    sh_node(compose_cmd(a.tree, cells[-1][0]) + "down -v --remove-orphans", check=False)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["disk_node_end"] = sh_node("df -h / | tail -1").strip()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
