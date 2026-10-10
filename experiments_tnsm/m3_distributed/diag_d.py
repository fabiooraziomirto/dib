"""Configuration D (approved 2026-10-10; audit 18 s.1.1): control for the M3/M4 anomaly.
Diagnostic, NOT a confirmatory measurement. Time-boxed: no new cell starts after --deadline
(default 22:25 local); the diagnosis limit (22:32) is not extended.

Configurations (FANOUT 10, same image, compose generator and benchmark as M3):
  A  plain, CMD `uvicorn service:app` (as in M3)
  C  mTLS (as in M3)
  D  plain (DIB_DIST_MTLS=0), launcher of B (uvicorn.Server + PeerCertH11Protocol) via a compose
     override, plus launcher_d.py, which sets service._HTTP_TLS FROM OUTSIDE to a prebuilt SSL
     context (no TLS on the listener); service.py and code/src untouched.
Cells: 5 repetitions x {A, C, D}, order shuffled within each repetition; writers 1 and 10,
200 timed ops + 20 warm-up per worker; idle background sample (node_monitor.idle_window, 12 s,
containers of project dibtnsm excluded) before each cell; p50 per operation type; count of
`POST /apply_fanout` lines on site-0 after the warm-up batch and after the timed batch of
each writer count (direct evidence on where the fan-outs happen).

Interpretation FIXED BEFORE LAUNCH (operational rule, per-repetition mean throughput at 1 writer,
95% bootstrap CIs over the 5 repetitions):
  D >= C  (mechanism CONFIRMED): CI_D lies above CI_C or overlaps it, and CI_D lies entirely above
          CI_A. Then the cost of mTLS is measured between C and D.
  D between A and C (PARTIAL explanation, an unidentified factor remains): CI_D entirely above
          CI_A and entirely below CI_C.
  D ~ A  (mechanism does NOT explain the gap): CI_D overlaps CI_A and lies entirely below CI_C.
  (Any other pattern is reported as it is and counted as "ambiguous".)
Expected vs observed saving, reported whatever the outcome: expected saving per site operation =
6.15 ms (httpx default-verify Client construction, measured in the service image, audit 18);
observed = p50(query, commit) of A minus that of D at 1 writer; also C versus A (3.7-3.9 ms in
the first diagnosis). The mechanism is NOT declared proven if D does not align with C.

Usage: python3 diag_d.py --out <dir> --pki-local <dir> --tree '~/dib_tnsm/tree-<commit>'
"""
from __future__ import annotations

import argparse
import hashlib
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

CONFIGS = ("A", "C", "D")
_TREE = None
EXPECTED_SAVING_MS = 6.15
LAUNCHER_B = ("import uvicorn; from dib.registry.distributed.mtls import PeerCertH11Protocol; "
              "uvicorn.Server(uvicorn.Config('service:app', host='0.0.0.0', port=8000, "
              "http=PeerCertH11Protocol)).run()")


def override_yaml(tree: str) -> str:
    lines = ["services:"]
    for svc in ["evidence"] + [f"site-{i}" for i in range(10)]:
        lines += [f"  {svc}:", "    command: [\"python\", \"/launcher_d.py\"]", "    volumes:",
                  f"      - {tree}/experiments_tnsm/m3_distributed/launcher_d.py:/launcher_d.py:ro"]
    return "\n".join(lines) + "\n"


def compose(tree: str, cfg: str) -> str:
    dist = f"{tree}/code/src/dib/registry/distributed"
    mtls = 1 if cfg == "C" else 0
    env = f"DIB_DIST_FANOUT_CONCURRENCY=10 DIB_DIST_MTLS={mtls} DIB_DIST_PKI_DIR=$HOME/dib_tnsm/pki"
    files = f"-f $HOME/dib_tnsm/m3/diag_f10_m{mtls}.yml" + (" -f $HOME/dib_tnsm/m3/diag_d_override.yml" if cfg == "D" else "")
    return (f"export PATH=/snap/bin:$PATH && cd {dist} && mkdir -p $HOME/dib_tnsm/m3 && "
            f"{env} python3 generate_compose.py > $HOME/dib_tnsm/m3/diag_f10_m{mtls}.yml && "
            f"docker compose -p dibtnsm {files} --project-directory {dist} ")


def count(container: str, pattern: str) -> int:
    out = m3.sh_node(f"/snap/bin/docker logs {container} 2>&1 | grep -c '{pattern}' || true")
    return int(out.strip() or 0)


def boot(xs, f=statistics.mean, n=10000, rng=random.Random(20261011)):
    v = sorted(f([rng.choice(xs) for _ in xs]) for _ in range(n))
    return f(xs), v[int(0.025 * n)], v[int(0.975 * n)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def classify(ci_a, ci_c, ci_d) -> str:
    (_, a_lo, a_hi), (_, c_lo, c_hi), (_, d_lo, d_hi) = ci_a, ci_c, ci_d
    if d_lo > a_hi and (d_hi >= c_lo):
        return "D>=C: mechanism confirmed"
    if d_lo > a_hi and d_hi < c_lo:
        return "D between A and C: partial explanation"
    if d_lo <= a_hi and d_hi >= a_lo and d_hi < c_lo:
        return "D~A: mechanism does not explain the gap"
    return "ambiguous"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--pki-local", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20261011)
    ap.add_argument("--writers", default="1,10")
    ap.add_argument("--deadline", default="22:25", help="local HH:MM; no new cell after it")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    writers = [int(x) for x in a.writers.split(",")]
    rng = random.Random(a.seed)
    home = m3.sh_node("echo $HOME").strip()
    if a.tree.startswith("~"):  # the snap compose does not expand ~ like the shell: use an absolute path
        a.tree = home + a.tree[1:]
    assert a.tree.startswith("/"), a.tree
    global _TREE
    _TREE = a.tree
    # a missing bind source would be created as a (root-owned) directory by the daemon
    m3.sh_node(f"test -f {a.tree}/experiments_tnsm/m3_distributed/launcher_d.py")
    node_service = m3.sh_node(f"sha256sum {a.tree}/code/src/dib/registry/distributed/service.py").split()[0]
    node_launcher = m3.sh_node(f"sha256sum {a.tree}/experiments_tnsm/m3_distributed/launcher_d.py").split()[0]
    manifest = {"started_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv, "node_tree": a.tree,
                "node_service_sha256": node_service, "node_launcher_d_sha256": node_launcher,
                "local_launcher_d_sha256": sha(Path(__file__).with_name("launcher_d.py")),
                "diag_d_sha256": sha(Path(__file__)),
                "benchmark_sha256": sha(ROOT / "code/scripts/distributed_concurrency_benchmark.py"),
                "note_launcher_d": "_HTTP_TLS is set from outside (service._HTTP_TLS = {'verify': prebuilt context}) "
                                   "by launcher_d.py before serving; service.py is unmodified",
                "expected_saving_ms": EXPECTED_SAVING_MS, "deadline": a.deadline}
    m3.sh_node("mkdir -p $HOME/dib_tnsm/m3 && cat > $HOME/dib_tnsm/m3/diag_d_override.yml <<'EOF'\n" + override_yaml(a.tree) + "EOF")
    cells = []
    for rep in range(a.reps):
        order = list(CONFIGS)
        rng.shuffle(order)
        cells += [(c, rep) for c in order]
    manifest["cell_order"] = [c for c, _ in cells]
    log = (out / "cells.jsonl").open("a")
    stopped = None
    for k, (cfg, rep) in enumerate(cells):
        if datetime.now().strftime("%H:%M") > a.deadline:
            stopped = f"deadline {a.deadline} reached before cell {k}"
            break
        base = compose(a.tree, cfg)
        m3.sh_node(base + "down -v --remove-orphans", check=False)
        m3.sh_node(base + "up -d")
        m3.wait_healthy((10, 1 if cfg == "C" else 0))
        bg = json.loads(m3.sh_node(f"python3 {a.tree}/experiments_tnsm/common/node_monitor.py sample --seconds 12 "
                                   "--exclude-project dibtnsm"))
        launcher_line = count("dibtnsm-site-0-1", "launcher_d: service._HTTP_TLS set") if cfg == "D" else None
        scheme = "https" if cfg == "C" else "http"
        bench.configure(evidence_url=f"{scheme}://{m3.NODE_IP}:18100",
                        site_urls=[f"{scheme}://{m3.NODE_IP}:{18110 + i}" for i in range(10)],
                        pki_dir=a.pki_local if cfg == "C" else None)
        bench.seed_all()
        res, fan = {}, {"after_seed": count("dibtnsm-site-0-1", "POST /apply_fanout")}
        for w in writers:
            bench.run_one_batch(w, 20, bench._MIX_REALISTIC)  # warm-up, discarded
            fan[f"w{w}_after_warmup"] = count("dibtnsm-site-0-1", "POST /apply_fanout")
            lat, unexpected, wall, kinds = bench.run_one_batch(w, 200, bench._MIX_REALISTIC)
            fan[f"w{w}_after_timed"] = count("dibtnsm-site-0-1", "POST /apply_fanout")
            res[str(w)] = {
                "throughput": w * 200 / wall, "wall_s": wall, "unexpected": unexpected, "errors": dict(kinds),
                "per_op": {op: {"n": len(v), "p50_ms": 1000 * statistics.median(v), "mean_ms": 1000 * statistics.mean(v)}
                           for op, v in sorted(lat.items())}}
        rec = {"cell": k, "config": cfg, "rep": rep, "t_utc": datetime.now(timezone.utc).isoformat(),
               "background_idle": bg, "launcher_d_log_lines": launcher_line, "apply_fanout_site0": fan, "results": res}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(f"[{k + 1}/{len(cells)}] {cfg} rep={rep} " + " ".join(f"w{w}:{res[str(w)]['throughput']:.1f}" for w in writers)
              + f" bg_other={bg['other_cores']} steal={bg['steal_pct']} fanout={fan} launcher_d={launcher_line}", flush=True)
    m3.sh_node(compose(a.tree, "A") + "down -v --remove-orphans", check=False)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["stopped_reason"] = stopped
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    recs = [json.loads(l) for l in (out / "cells.jsonl").open()]
    summary = {"cells": len(recs), "stopped_reason": stopped, "throughput": {}, "per_op_p50_ms": {}}
    for w in writers:
        xs = {c: [r["results"][str(w)]["throughput"] for r in recs if r["config"] == c] for c in CONFIGS}
        summary["throughput"][str(w)] = {c: boot(v) for c, v in xs.items() if len(v) > 1}
    if all(len([r for r in recs if r["config"] == c]) > 1 for c in CONFIGS):
        t1 = summary["throughput"]["1"]
        summary["classification_1writer"] = classify(t1["A"], t1["C"], t1["D"])
    for c in CONFIGS:
        for w in writers:
            agg = {}
            for r in recs:
                if r["config"] == c:
                    for op, d in r["results"][str(w)]["per_op"].items():
                        agg.setdefault(op, []).append(d["p50_ms"])
            summary["per_op_p50_ms"][f"{c}_w{w}"] = {op: round(statistics.mean(v), 2) for op, v in agg.items()}
    p = summary["per_op_p50_ms"]
    try:
        site_ops = ("query", "commit")
        a1 = statistics.mean(p["A_w1"][o] for o in site_ops)
        summary["saving_ms_w1"] = {"expected_from_microbench": EXPECTED_SAVING_MS,
                                   "observed_A_minus_D": a1 - statistics.mean(p["D_w1"][o] for o in site_ops),
                                   "observed_A_minus_C": a1 - statistics.mean(p["C_w1"][o] for o in site_ops)}
    except KeyError:
        pass
    summary["apply_fanout_site0_by_cell"] = [r["apply_fanout_site0"] for r in recs]
    summary["background_idle_other_cores_max"] = max(r["background_idle"]["other_cores"] for r in recs)
    summary["background_idle_steal_max"] = max(r["background_idle"]["steal_pct"] for r in recs)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:  # always take the project down, also on an error
        if _TREE:
            m3.sh_node(compose(_TREE, "A") + "down -v --remove-orphans", check=False)
    raise SystemExit(rc)
