"""Diagnosis of the M3/M4 anomaly (audit 18 s.1; user decision 2026-10-10): with mTLS the
throughput at 1 and 10 writers was HIGHER (209-213 vs 112-116 ops/s at 1 writer), which a TLS
cost cannot explain. Time-boxed to ~1 hour. Diagnostic, NOT a confirmatory measurement.

Three server configurations, FANOUT 10, same image, same compose generator, same benchmark:
  A  plain, container CMD `uvicorn service:app` (as in M3)                [DIB_DIST_MTLS=0]
  B  plain, SAME LAUNCHER AS THE mTLS ARM, without TLS: uvicorn.Server(uvicorn.Config(
     'service:app', http=PeerCertH11Protocol)) through a compose override `command:`
     (mtls.py:91-95,158; PeerCertH11Protocol returns early without ssl_object, mtls.py:59-62)
                                                                           [DIB_DIST_MTLS=0]
  C  mTLS (as in M3)                                                       [DIB_DIST_MTLS=1]
Per cell: writers 1 and 10, 200 timed ops + 20 warm-up per worker; the latency PER OPERATION
TYPE (the benchmark computes it in run_one_batch, but its CSV discards it) and the number of
uvicorn access-log lines on site-0 and evidence (P-log requirement: the access log must exist
in every mode). An idle background sample (other_cores, steal_pct, 12 s, containers excluded,
node_monitor.idle_window) is taken on the node before each cell. 5 repetitions; the three
configurations are shuffled within each repetition.

Hypotheses (stated before running, from the code reading in audit 18):
  H-D1  The launcher explains the gap. Operationalized at 1 writer on the per-repetition mean
        throughput: the launcher is the cause if |mean(B) - mean(C)| < |mean(B) - mean(A)|,
        i.e. B is closer to C (mTLS launcher) than to A (CLI launcher); otherwise the
        launcher is excluded as the cause. Reported with the 95% bootstrap CI of
        mean(B)-mean(A) and mean(B)-mean(C).
  H-D2  The access log is present in all three configurations: >= 90% of the requests that
        reach site-0 appear as `"POST /...` lines. Falsified otherwise.
Reading: B ~ C -> the launcher is the cause and the plain arms of M3 must be rerun with the
identical launcher (~20 cells); B ~ A (and C differs) -> the launcher is excluded and the
cause is in the TLS path or in the app path (service.py MTLS branch). The per-operation
latencies say whether the gap is in site operations (commit: SQLite write) or in all of them.

Usage: python3 diag_1writer.py --out <dir> --pki-local <dir> --tree '~/dib_tnsm/tree-<commit>'
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as m3  # noqa: E402  (sh_node, wait_healthy, NODE_IP; main() is guarded)
import distributed_concurrency_benchmark as bench  # noqa: E402

CONFIGS = ("A", "B", "C")
LAUNCHER = ("import uvicorn; from dib.registry.distributed.mtls import PeerCertH11Protocol; "
            "uvicorn.Server(uvicorn.Config('service:app', host='0.0.0.0', port=8000, "
            "http=PeerCertH11Protocol)).run()")


def override_yaml() -> str:
    lines = ["services:"]
    for svc in ["evidence"] + [f"site-{i}" for i in range(10)]:
        lines += [f"  {svc}:", f"    command: [\"python\", \"-c\", {json.dumps(LAUNCHER)}]"]
    return "\n".join(lines) + "\n"


def compose(tree: str, cfg: str) -> str:
    dist = f"{tree}/code/src/dib/registry/distributed"
    mtls = 1 if cfg == "C" else 0
    env = f"DIB_DIST_FANOUT_CONCURRENCY=10 DIB_DIST_MTLS={mtls} DIB_DIST_PKI_DIR=$HOME/dib_tnsm/pki"
    files = f"-f $HOME/dib_tnsm/m3/diag_f10_m{mtls}.yml" + (" -f $HOME/dib_tnsm/m3/diag_override.yml" if cfg == "B" else "")
    return (f"export PATH=/snap/bin:$PATH && cd {dist} && mkdir -p $HOME/dib_tnsm/m3 && "
            f"{env} python3 generate_compose.py > $HOME/dib_tnsm/m3/diag_f10_m{mtls}.yml && "
            f"docker compose -p dibtnsm {files} --project-directory {dist} ")


def access_lines(container: str) -> int:
    out = m3.sh_node(f"/snap/bin/docker logs {container} 2>&1 | grep -c '\"POST /' || true")
    return int(out.strip() or 0)


def boot(xs, f=statistics.mean, n=10000, rng=random.Random(20261010)):
    v = sorted(f([rng.choice(xs) for _ in xs]) for _ in range(n))
    return f(xs), v[int(0.025 * n)], v[int(0.975 * n)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--pki-local", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--writers", default="1,10")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    writers = [int(x) for x in a.writers.split(",")]
    rng = random.Random(a.seed)
    m3.sh_node("mkdir -p $HOME/dib_tnsm/m3 && cat > $HOME/dib_tnsm/m3/diag_override.yml <<'EOF'\n" + override_yaml() + "EOF")
    cells = []
    for rep in range(a.reps):
        order = list(CONFIGS)
        rng.shuffle(order)
        cells += [(c, rep) for c in order]
    log = (out / "cells.jsonl").open("a")
    for k, (cfg, rep) in enumerate(cells):
        base = compose(a.tree, cfg)
        m3.sh_node(base + "down -v --remove-orphans", check=False)
        m3.sh_node(base + "up -d")
        m3.wait_healthy((10, 1 if cfg == "C" else 0))
        bg = json.loads(m3.sh_node(f"python3 {a.tree}/experiments_tnsm/common/node_monitor.py sample --seconds 12 "
                                   "--exclude-project dibtnsm"))
        scheme = "https" if cfg == "C" else "http"
        bench.configure(evidence_url=f"{scheme}://{m3.NODE_IP}:18100",
                        site_urls=[f"{scheme}://{m3.NODE_IP}:{18110 + i}" for i in range(10)],
                        pki_dir=a.pki_local if cfg == "C" else None)
        bench.seed_all()
        res = {}
        for w in writers:
            bench.run_one_batch(w, 20, bench._MIX_REALISTIC)  # warm-up, discarded
            lat, unexpected, wall, kinds = bench.run_one_batch(w, 200, bench._MIX_REALISTIC)
            res[str(w)] = {
                "throughput": w * 200 / wall, "wall_s": wall, "unexpected": unexpected, "errors": dict(kinds),
                "per_op": {op: {"n": len(v), "p50_ms": 1000 * statistics.median(v), "mean_ms": 1000 * statistics.mean(v),
                                "max_ms": 1000 * max(v)} for op, v in sorted(lat.items())},
            }
        req_counts = {"site0_post_lines": access_lines("dibtnsm-site-0-1"),
                      "evidence_post_lines": access_lines("dibtnsm-evidence-1")}
        rec = {"cell": k, "config": cfg, "rep": rep, "t_utc": datetime.now(timezone.utc).isoformat(),
               "background_idle": bg, "results": res, "access_log": req_counts}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(f"[{k + 1}/{len(cells)}] {cfg} rep={rep} " + " ".join(f"w{w}:{res[str(w)]['throughput']:.1f}" for w in writers)
              + f" bg_other={bg['other_cores']} steal={bg['steal_pct']} access={req_counts}", flush=True)
    m3.sh_node(compose(a.tree, "A") + "down -v --remove-orphans", check=False)
    recs = [json.loads(l) for l in (out / "cells.jsonl").open()]
    summary = {"hypotheses": {}, "throughput": {}}
    for w in writers:
        xs = {c: [r["results"][str(w)]["throughput"] for r in recs if r["config"] == c] for c in CONFIGS}
        summary["throughput"][str(w)] = {c: boot(v) for c, v in xs.items()}
        if w == 1:
            ba = [b - x for b, x in zip(xs["B"], xs["A"])]
            bc = [b - x for b, x in zip(xs["B"], xs["C"])]
            mba = statistics.mean(xs["B"]) - statistics.mean(xs["A"])
            mbc = statistics.mean(xs["B"]) - statistics.mean(xs["C"])
            summary["hypotheses"]["H-D1"] = {"B_minus_A": boot(ba), "B_minus_C": boot(bc),
                                             "launcher_is_cause": abs(mbc) < abs(mba)}
    ops = {}
    for c in CONFIGS:
        for w in writers:
            agg = {}
            for r in recs:
                if r["config"] == c:
                    for op, d in r["results"][str(w)]["per_op"].items():
                        agg.setdefault(op, []).append(d["p50_ms"])
            ops[f"{c}_w{w}"] = {op: round(statistics.mean(v), 2) for op, v in agg.items()}
    summary["per_op_p50_ms_mean"] = ops
    summary["access_log_by_config"] = {c: [r["access_log"] for r in recs if r["config"] == c] for c in CONFIGS}
    summary["background_idle_other_cores_max"] = max(r["background_idle"]["other_cores"] for r in recs)
    summary["background_idle_steal_max"] = max(r["background_idle"]["steal_pct"] for r in recs)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
