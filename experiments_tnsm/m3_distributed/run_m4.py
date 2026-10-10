"""M4 rerun (user decision 2026-10-10; audit 18 s.1.3-1.5): cost of mTLS measured between
C (mTLS) and D (plain, same launcher as C, prebuilt SSL context set from outside), because the
original M3/M4 plain arm (default configuration, A) pays ~6.15 ms per inter-service call for an
httpx default SSL context (service.py:161,381; audit 18 s.1.3), which made mTLS look faster at 1
and 10 writers. The original M4 data (run_20261010) stay as the "default configuration" with a
note; this rerun is NOT compared with those mTLS cells: C and D are measured in the SAME blocks.

Design. Arms: C = mTLS (DIB_DIST_MTLS=1, CMD python -m dib.registry.distributed.mtls);
D = DIB_DIST_MTLS=0 + compose override running launcher_d.py (uvicorn.Server +
PeerCertH11Protocol, service._HTTP_TLS = {"verify": prebuilt context} set FROM OUTSIDE before
serving; service.py and code/src untouched). FANOUT_CONCURRENCY fixed at 10 in both arms: the
mix exercises no fan-out in the timed phases (audit 18 s.1.2), so the value is irrelevant to
the result and is declared only for reproducibility. 10 repetitions; in each repetition one C
cell and one D cell form a BLOCK, order shuffled with --seed. One cell = cluster recreated
(`down -v`, `up -d`, fresh databases), idle background sample (node_monitor.idle_window, 12 s,
project containers excluded), seed, then writers 1, 10, 50, 100 in an order shuffled per cell,
each with a discarded warm-up batch (20 ops/worker) and a timed batch (200 ops/worker), run
in-process through distributed_concurrency_benchmark.run_one_batch (per-operation latencies).
Generator on THIS host (the node runs the services): a deliberate difference from M6/M7 (there
the generator runs on the node); absolute latencies are not comparable between the two.

Predictions (declared before launch, from the diagnosis of 2026-10-10, 5 repetitions):
  H-M4a  1 writer:   throughput ratio C/D = 214.6/351.6 ~ 0.61. Falsified if the 95% bootstrap CI
         of the paired (same-block) ratio lies entirely outside [0.50, 0.72].
  H-M4b  10 writers: C/D = 444.0/579.2 ~ 0.77. Falsified if the CI lies entirely outside
         [0.68, 0.86].
  Exploratory (no hypothesis): 50 and 100 writers. A database/evidence bottleneck can hide part
  of the effect there (the original M4 ratio at 100 writers, 0.83, was measured against the
  default arm), so those ratios are reported with that caution and are NOT confirmatory.
  Reported without a threshold: p50 per operation type (site operations query/commit,
  evidence operations attest/dispute/restore) with 95% CIs, overall p50/p95/p99, unexpected
  errors by type.
Statistics (analyze_m4.py): unit = cell; bootstrap over cells, 10000 resamples, seed 20261013;
ratios paired by block. The only reportable cost of mTLS is the ratio C/D, for this prototype
(no connection pool between services: a full handshake per inter-service call), and at 50/100
writers exploratory; no number is an "upper bound".
Discard rule (experiments_tnsm/common/discard_rule.json, thresholds unchanged): a cell is
FLAGGED if the pre-cell idle sample has other_cores > 1.0 or steal_pct > 2.0 (the during-cell
window is not measured: the generator is on another host); flagged cells are never dropped,
results are reported on all cells and on unflagged cells with the flagged count.

Usage: python3 run_m4.py --out <dir> --pki-local <dir> --tree '~/dib_tnsm/tree-<commit>' [--pilot]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as m3  # noqa: E402  (sh_node, wait_healthy, NODE_IP)
import diag_d as dd  # noqa: E402  (compose, override_yaml)
import distributed_concurrency_benchmark as bench  # noqa: E402

ARMS = ("C", "D")
WRITERS = [1, 10, 50, 100]
FANOUT = 10
_TREE = None


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pct(xs, p):
    return bench.pct(sorted(xs), p)


def main() -> int:
    global _TREE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--pki-local", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20261013)
    ap.add_argument("--ops-per-worker", type=int, default=200)
    ap.add_argument("--warmup-ops", type=int, default=20)
    ap.add_argument("--writers", default=",".join(map(str, WRITERS)))
    ap.add_argument("--pilot", action="store_true", help="one block, writers 1,10, 20 ops (not a measurement)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    home = m3.sh_node("echo $HOME").strip()
    tree = home + a.tree[1:] if a.tree.startswith("~") else a.tree
    assert tree.startswith("/"), tree
    _TREE = tree
    writers = [int(x) for x in a.writers.split(",")]
    ops, warm, reps = a.ops_per_worker, a.warmup_ops, a.reps
    if a.pilot:
        writers, ops, warm, reps = [1, 10], 20, 5, 1
    rule = json.loads((ROOT / "experiments_tnsm/common/discard_rule.json").read_text())
    pki = json.loads((Path(a.pki_local) / "pki_manifest.json").read_text())
    not_after = datetime.strptime(pki["not_after"], "%Y%m%d%H%M%SZ").replace(tzinfo=timezone.utc)
    # PKI expiry vs estimated duration (~125 s per cell): refuse to start if it does not fit with a 30 min margin
    est_s = 2 * reps * 140
    left = (not_after - datetime.now(timezone.utc)).total_seconds()
    assert left > est_s + 1800, f"PKI valid for {left:.0f} s only, need {est_s + 1800} s: regenerate it"
    m3.sh_node(f"test -f {tree}/experiments_tnsm/m3_distributed/launcher_d.py")  # missing bind source -> daemon would create a directory
    m3.sh_node("mkdir -p $HOME/dib_tnsm/m3 && cat > $HOME/dib_tnsm/m3/diag_d_override.yml <<'EOF'\n" + dd.override_yaml(tree) + "EOF")
    rng = random.Random(a.seed)
    cells = []
    for rep in range(reps):
        order = list(ARMS)
        rng.shuffle(order)
        cells += [(arm, rep) for arm in order]
    manifest = {
        "started_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv, "seed": a.seed, "pilot": a.pilot,
        "fanout_concurrency_fixed": FANOUT, "arms": {"C": "mTLS", "D": "plain + launcher_d.py (prebuilt SSL context)"},
        "cell_order": [[c, r] for c, r in cells], "ops_per_worker": ops, "warmup_ops": warm,
        "generator_host": platform.node(), "generator_python": sys.version, "node_tree": tree,
        "deliberate_difference": "generator on this host; M6/M7 run it on the node; absolute latencies not comparable",
        "node_service_sha256": m3.sh_node(f"sha256sum {tree}/code/src/dib/registry/distributed/service.py").split()[0],
        "node_launcher_d_sha256": m3.sh_node(f"sha256sum {tree}/experiments_tnsm/m3_distributed/launcher_d.py").split()[0],
        "note_launcher_d": "_HTTP_TLS is set from outside (service._HTTP_TLS = {'verify': prebuilt context}) by "
                           "launcher_d.py before serving; service.py is unmodified",
        "sha256_local": {k: sha(ROOT / p) for k, p in {
            "run_m4.py": "experiments_tnsm/m3_distributed/run_m4.py", "diag_d.py": "experiments_tnsm/m3_distributed/diag_d.py",
            "launcher_d.py": "experiments_tnsm/m3_distributed/launcher_d.py",
            "benchmark": "code/scripts/distributed_concurrency_benchmark.py", "node_monitor.py": "experiments_tnsm/common/node_monitor.py",
            "make_dist_pki.py": "code/scripts/make_dist_pki.py", "discard_rule.json": "experiments_tnsm/common/discard_rule.json"}.items()},
        "pki": {"not_after": pki["not_after"], "extra_san_ip": pki.get("extra_san_ip"),
                "note": "mTLS certificates carry one more SAN (IP of the node) than the default"},
        "disk_node_start": m3.sh_node("df -h / | tail -1").strip(), "discard_rule": rule,
    }
    log = (out / "cells.jsonl").open("a")
    for k, (arm, rep) in enumerate(cells):
        base = dd.compose(tree, arm)
        m3.sh_node(base + "down -v --remove-orphans", check=False)
        m3.sh_node(base + "up -d")
        m3.wait_healthy((FANOUT, 1 if arm == "C" else 0))
        bg = json.loads(m3.sh_node(f"python3 {tree}/experiments_tnsm/common/node_monitor.py sample --seconds 12 "
                                   "--exclude-project dibtnsm"))
        flagged = bg["other_cores"] > rule["max_other_cores"] or bg["steal_pct"] > rule["max_steal_pct"]
        scheme = "https" if arm == "C" else "http"
        bench.configure(evidence_url=f"{scheme}://{m3.NODE_IP}:18100",
                        site_urls=[f"{scheme}://{m3.NODE_IP}:{18110 + i}" for i in range(10)],
                        pki_dir=a.pki_local if arm == "C" else None)
        bench.seed_all()
        order = writers[:]
        rng.shuffle(order)
        res = {}
        for w in order:
            bench.run_one_batch(w, warm, bench._MIX_REALISTIC)  # warm-up, discarded
            lat, unexpected, wall, kinds = bench.run_one_batch(w, ops, bench._MIX_REALISTIC)
            allv = [v for vals in lat.values() for v in vals]
            res[str(w)] = {
                "throughput": w * ops / wall, "wall_s": wall, "unexpected": unexpected, "errors": dict(kinds),
                "p50_ms": 1000 * pct(allv, 0.5), "p95_ms": 1000 * pct(allv, 0.95), "p99_ms": 1000 * pct(allv, 0.99),
                "per_op_p50_ms": {op: 1000 * statistics.median(v) for op, v in sorted(lat.items())},
                "per_op_n": {op: len(v) for op, v in sorted(lat.items())}}
        rec = {"cell": k, "arm": arm, "rep": rep, "block": rep, "writer_order": order, "t_utc": datetime.now(timezone.utc).isoformat(),
               "background_idle": bg, "flagged_pre": flagged, "results": res}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(f"[{k + 1}/{len(cells)}] {arm} rep={rep} " + " ".join(f"w{w}:{res[str(w)]['throughput']:.1f}" for w in sorted(map(int, res)))
              + f" bg_other={bg['other_cores']} steal={bg['steal_pct']} flagged={flagged} "
              + f"errs={sum(r['unexpected'] for r in res.values())}", flush=True)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["disk_node_end"] = m3.sh_node("df -h / | tail -1").strip()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:  # always take the project down, also on an error
        if _TREE:
            m3.sh_node(dd.compose(_TREE, "C") + "down -v --remove-orphans", check=False)
    raise SystemExit(rc)
