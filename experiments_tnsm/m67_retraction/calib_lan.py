"""Calibrations at `lan` (user decision 2026-10-10, audit 18 s.2.4 B): runs ON THE NODE, no sudo,
from a pinned tree. Brings up the plain arm D (FANOUT 10, T = 5), then
  1. checks Env.healthy() and Env.measure_rtt_ms() at lan (partial exercise of run.py's live code);
  2. calib_logs.py --n 100: distribution of the latency of `docker logs -t` with ONE container
     (evidence) and with TWO in parallel (evidence + site-0), order and relative offset;
  3. calib_ldns.sh: duration of a connection attempt (getaddrinfo) towards site-3 alive and after
     `compose kill site-3` (50 samples each);
  4. netem_apply.sh --dry-run for every profile (lists the nsenter/tc commands; nothing applied).
It declares NO threshold and NO B2 variant: those also depend on `wan` and `degraded`, which need
the user's sudo commands. The cluster is always taken down in a finally.
Usage (on the node): ~/dib_tnsm/venv/bin/python calib_lan.py --tree ~/dib_tnsm/tree-<commit> --out <dir>
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as m67  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tree = a.tree if a.tree.startswith("/") else str(Path.home()) + a.tree[1:]
    home = str(Path.home())
    Path(f"{home}/dib_tnsm/m67").mkdir(parents=True, exist_ok=True)
    override = "services:\n" + "".join(
        f"  {s}:\n    command: [\"python\", \"/launcher_d.py\"]\n    volumes:\n"
        f"      - {tree}/experiments_tnsm/m3_distributed/launcher_d.py:/launcher_d.py:ro\n"
        for s in ["evidence"] + [f"site-{i}" for i in range(m67.N_SITES)])
    assert Path(f"{tree}/experiments_tnsm/m3_distributed/launcher_d.py").is_file()
    ov = Path(f"{home}/dib_tnsm/m67/override_d.yml")
    ov.write_text(override)
    env = m67.Env(tree, "D", 10, 5, Path(f"{home}/dib_tnsm/pki"))
    res = {"started": time.time(), "tree": tree}
    try:
        env.up()
        res["healthy_s"] = env.healthy()
        res["rtt_ms_lan"] = env.measure_rtt_ms()
        res["rtt_check_lan"] = m67.rtt_matches("lan", res["rtt_ms_lan"])
        subprocess.run([sys.executable, f"{tree}/experiments_tnsm/m67_retraction/calib_logs.py", "--n", "100", "--out", str(out / "calib_logs_lan.json")],
                       check=True, capture_output=True, text=True)
        res["calib_logs"] = json.loads((out / "calib_logs_lan.json").read_text())
        gen = f"{home}/dib_tnsm/m67/gen_D_f10_T5.yml"
        dist = f"{tree}/code/src/dib/registry/distributed"
        r = subprocess.run(["bash", f"{tree}/experiments_tnsm/m67_retraction/calib_ldns.sh", gen, dist, "lan", str(ov)],
                           capture_output=True, text=True, timeout=600)
        (out / "calib_ldns_lan.txt").write_text(r.stdout + r.stderr)
        res["calib_ldns_returncode"] = r.returncode
        dry = {}
        for prof in ["lan", "regional", "wan", "degraded", "extreme", "mixed"]:
            d = subprocess.run(["bash", f"{tree}/experiments_tnsm/m67_retraction/netem_apply.sh", "--dry-run", prof], capture_output=True, text=True)
            dry[prof] = d.stdout + d.stderr
            (out / f"dryrun_{prof}.txt").write_text(dry[prof])
        res["dry_run_lines"] = {p: len(t.splitlines()) for p, t in dry.items()}
    finally:
        env.down()
        res["finished"] = time.time()
        (out / "calib_lan_result.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k not in ("calib_logs",)}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
