"""CPU diagnosis at 100 writers (user decision 2026-10-10; audit 18 s.1.7.1 point 3). Diagnostic,
NOT confirmatory. Time-boxed to 20 minutes from launch; no extension. If it is not conclusive
the verdict is written as "cause of the plateau undetermined".

Question. In M4 (C = mTLS, D = plain with a prebuilt SSL context) the throughput at 100 writers
was ~824 (D) and ~448 (C) ops/s. Is the limit the CPU of the node (or of the evidence/site
containers), the CPU of the generator host (so the C/D ratio is distorted by the generator), or
neither (database / serialization)?

Configuration. Same stack as M4 at `lan` (no netem), generator on THIS host, services from a
pinned tree on the node (hash in the manifest): D = DIB_DIST_MTLS=0 + launcher_d.py override
(prebuilt SSL context, service.py untouched), C = mTLS; FANOUT 10. Cells: 3 x D + 1 x C, order
shuffled with --seed; each cell recreates the cluster, takes the idle background sample
(node_monitor.sample: other_cores, steal_pct), seeds, runs a discarded warm-up batch
(20 ops/worker) and ONE timed batch of 100 writers x 200 ops, during which
  * the node is sampled every second (cpu_sampler.py over ssh): /proc/stat (busy cores, steal)
    and, from the cgroup v2 cpu.stat of each dibtnsm container, the CPU of evidence and of
    each site (1.0 = one vCPU); plus one `docker stats --no-stream` snapshot as a cross-check;
  * this host (the generator) is sampled every second: /proc/stat (busy %, steal) and the CPU of
    the generator process itself (all its threads), which is the direct saturation measure of a
    Python generator (GIL).
Samples are aligned to the timed window with the measured clock offset node - generator.

Saturation thresholds (fixed here, before the run): a single-process service or the generator
process is "near saturation" if its mean CPU over the timed window is >= 0.85 cores; a host is
"near saturation" if its mean busy share over the window is >= 80% of its vCPUs. NODE saturated =
host busy >= 80% OR any dibtnsm container (evidence or a site) >= 0.85 cores. GENERATOR saturated =
generator process >= 0.85 cores OR generator host busy >= 80%.

Interpretation FIXED BEFORE THE RUN (per arm; D cells pooled, C reported separately):
  node saturated, generator not      -> the limit is the CPU of the node/containers
  generator saturated                -> the C/D ratio is distorted by the generator (direction
                                        unknown); also report whether the node is saturated
  neither saturated                  -> the limit is the database or serialization
  both saturated                     -> mixed picture, written as such
Whatever the outcome, no comment on the shape of the C/D curve beyond the data.

Usage: python3 diag_cpu100.py --out <dir> --pki-local <dir> --tree '~/dib_tnsm/tree-<commit>'
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "experiments_tnsm" / "common"))
import run as m3  # noqa: E402
import diag_d as dd  # noqa: E402
import distributed_concurrency_benchmark as bench  # noqa: E402
from cpu_sampler import Sampler  # noqa: E402

SAT_PROC, SAT_HOST_PCT = 0.85, 80.0
WRITERS, OPS, WARM = 100, 200, 20
_TREE = None


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def window(samples, lo, hi, shift=0.0):
    return [s for s in samples if lo <= s["t_unix"] - shift <= hi]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def summarize(node, gen, lo, hi, offset):
    nw, gw = window(node, lo, hi, offset), window(gen, lo, hi)
    names = sorted({n for s in nw for n in s["containers"]})
    cont = {n: mean([s["containers"].get(n) for s in nw]) for n in names}
    sites = {n: v for n, v in cont.items() if "site" in n}
    ev = {n: v for n, v in cont.items() if "evidence" in n}
    out = {"node_samples": len(nw), "gen_samples": len(gw),
           "node_host_busy_pct": mean([s["host_busy_pct"] for s in nw]), "node_host_busy_cores": mean([s["host_busy_cores"] for s in nw]),
           "node_steal_pct": mean([s["host_steal_pct"] for s in nw]),
           "containers_cores": cont, "evidence_cores": mean(ev.values()), "max_site_cores": max(sites.values()) if sites else None,
           "sum_containers_cores": sum(v for v in cont.values() if v is not None),
           "gen_proc_cores": mean([s["proc_cores"] for s in gw]), "gen_host_busy_pct": mean([s["host_busy_pct"] for s in gw]),
           "gen_steal_pct": mean([s["host_steal_pct"] for s in gw])}
    mx = max([v for v in (out["evidence_cores"], out["max_site_cores"]) if v is not None], default=0)
    out["node_saturated"] = bool((out["node_host_busy_pct"] or 0) >= SAT_HOST_PCT or mx >= SAT_PROC)
    out["generator_saturated"] = bool((out["gen_proc_cores"] or 0) >= SAT_PROC or (out["gen_host_busy_pct"] or 0) >= SAT_HOST_PCT)
    return out


def verdict(cells):
    node = [c["summary"]["node_saturated"] for c in cells]
    gen = [c["summary"]["generator_saturated"] for c in cells]
    n, g = all(node), all(gen)
    if not (n == any(node) and g == any(gen)):
        return "mixed picture across cells (saturation not consistent between repetitions)"
    if n and g:
        return "mixed picture: BOTH the node/containers and the generator are near saturation"
    if g:
        return "the generator is near saturation: the C/D ratio is distorted by the generator (direction unknown)"
    if n:
        return "the limit is the CPU of the node/containers"
    return "neither the node/containers nor the generator is near saturation: the limit is the database or serialization"


def main() -> int:
    global _TREE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--pki-local", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--minutes", type=float, default=20.0)
    a = ap.parse_args()
    t_launch = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    home = m3.sh_node("echo $HOME").strip()
    tree = home + a.tree[1:] if a.tree.startswith("~") else a.tree
    assert tree.startswith("/"), tree
    _TREE = tree
    m3.sh_node(f"test -f {tree}/experiments_tnsm/m3_distributed/launcher_d.py && test -f {tree}/experiments_tnsm/common/cpu_sampler.py")
    m3.sh_node("mkdir -p $HOME/dib_tnsm/m3 && cat > $HOME/dib_tnsm/m3/diag_d_override.yml <<'EOF'\n" + dd.override_yaml(tree) + "EOF")
    rng = random.Random(a.seed)
    cells = ["D", "D", "D", "C"]
    rng.shuffle(cells)
    manifest = {"started_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv, "seed": a.seed, "cell_order": cells,
                "thresholds": {"proc_cores": SAT_PROC, "host_busy_pct": SAT_HOST_PCT}, "node_tree": tree,
                "node_service_sha256": m3.sh_node(f"sha256sum {tree}/code/src/dib/registry/distributed/service.py").split()[0],
                "node_launcher_d_sha256": m3.sh_node(f"sha256sum {tree}/experiments_tnsm/m3_distributed/launcher_d.py").split()[0],
                "node_cpu_sampler_sha256": m3.sh_node(f"sha256sum {tree}/experiments_tnsm/common/cpu_sampler.py").split()[0],
                "local_sha256": {"diag_cpu100.py": sha(Path(__file__)), "cpu_sampler.py": sha(ROOT / "experiments_tnsm/common/cpu_sampler.py"),
                                 "benchmark": sha(ROOT / "code/scripts/distributed_concurrency_benchmark.py")},
                "generator_host": os.uname().nodename, "generator_ncpu": os.cpu_count(), "node_ncpu": m3.sh_node("nproc").strip(),
                "disk_node_start": m3.sh_node("df -h / | tail -1").strip(), "limit_minutes": a.minutes,
                "note_launcher_d": "_HTTP_TLS is set from outside by launcher_d.py; service.py unmodified"}
    results = []
    for k, arm in enumerate(cells):
        if time.time() - t_launch + 130 > a.minutes * 60:
            manifest["stopped_reason"] = f"20-minute limit before cell {k}"
            break
        base = dd.compose(tree, arm)
        m3.sh_node(base + "down -v --remove-orphans", check=False)
        m3.sh_node(base + "up -d")
        m3.wait_healthy((10, 1 if arm == "C" else 0))
        bg = json.loads(m3.sh_node(f"python3 {tree}/experiments_tnsm/common/node_monitor.py sample --seconds 12 --exclude-project dibtnsm"))
        scheme = "https" if arm == "C" else "http"
        bench.configure(evidence_url=f"{scheme}://{m3.NODE_IP}:18100",
                        site_urls=[f"{scheme}://{m3.NODE_IP}:{18110 + i}" for i in range(10)],
                        pki_dir=a.pki_local if arm == "C" else None)
        bench.seed_all()
        bench.run_one_batch(WRITERS, WARM, bench._MIX_REALISTIC)  # warm-up, discarded
        # clock offset node - generator (half round trip)
        t0 = time.time(); node_now = float(m3.sh_node("date +%s.%N").strip()); t1 = time.time()
        offset = node_now - (t0 + t1) / 2
        remote = subprocess.Popen(m3.SSH + [f"python3 {tree}/experiments_tnsm/common/cpu_sampler.py --seconds 120 --interval 1 --project dibtnsm"],
                                  stdout=subprocess.PIPE, text=True)
        local = Sampler(interval=1.0, pid=os.getpid())
        local.start()
        time.sleep(3.0)
        snap = {}

        def docker_stats():
            time.sleep(8)
            snap["docker_stats"] = m3.sh_node("/snap/bin/docker stats --no-stream --format '{{.Name}} {{.CPUPerc}}'", check=False)

        th = threading.Thread(target=docker_stats)
        th.start()
        t_start = time.time()
        lat, unexpected, wall, kinds = bench.run_one_batch(WRITERS, OPS, bench._MIX_REALISTIC)
        t_end = time.time()
        time.sleep(2.0)
        th.join()
        local_samples = local.stop()
        remote.terminate()
        node_samples = [json.loads(l) for l in remote.stdout.read().splitlines() if l.strip()]
        remote.wait(timeout=10)
        allv = sorted(v for vals in lat.values() for v in vals)
        summ = summarize(node_samples, local_samples, t_start, t_end, offset)
        rec = {"cell": k, "arm": arm, "throughput": WRITERS * OPS / wall, "wall_s": wall, "unexpected": unexpected, "errors": dict(kinds),
               "p50_ms": 1000 * bench.pct(allv, 0.5), "p99_ms": 1000 * bench.pct(allv, 0.99), "background_idle": bg,
               "clock_offset_s": offset, "t_start": t_start, "t_end": t_end, "docker_stats": snap.get("docker_stats"),
               "summary": summ}
        results.append(rec)
        (out / "cells.jsonl").open("a").write(json.dumps(rec) + "\n")
        (out / f"samples_cell{k}_{arm}.json").write_text(json.dumps({"node": node_samples, "generator": local_samples}))
        print(f"[{k + 1}/{len(cells)}] {arm}: {rec['throughput']:.1f} ops/s  node busy {summ['node_host_busy_pct']:.1f}% "
              f"evidence {summ['evidence_cores']:.2f} max-site {summ['max_site_cores']:.2f} cores | generator proc {summ['gen_proc_cores']:.2f} cores "
              f"host {summ['gen_host_busy_pct']:.1f}% | node_sat={summ['node_saturated']} gen_sat={summ['generator_saturated']} "
              f"bg_other={bg['other_cores']} steal={bg['steal_pct']} errs={unexpected}", flush=True)
    m3.sh_node(dd.compose(tree, "D") + "down -v --remove-orphans", check=False)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["disk_node_end"] = m3.sh_node("df -h / | tail -1").strip()
    summary = {"cells": len(results), "verdict_D": verdict([r for r in results if r["arm"] == "D"]) if any(r["arm"] == "D" for r in results) else None,
               "verdict_C": verdict([r for r in results if r["arm"] == "C"]) if any(r["arm"] == "C" for r in results) else None}
    manifest["summary"] = summary
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:  # always take the project down, also on an error
        if _TREE:
            m3.sh_node(dd.compose(_TREE, "D") + "down -v --remove-orphans", check=False)
    raise SystemExit(rc)
