#!/usr/bin/env python3
"""Unattended night sequence on the node (user plan of 2026-10-11): calibrations at `wan`, B1 at `wan`, B2-kill only if the L_dns
rule allows it, teardown, and (only with >= 3 h left) M1/M2 two-arm. Runs DETACHED (setsid nohup, PID file) from the frozen tree,
no sudo, no change to netem or to the watcher, no change to code: it only calls the frozen scripts and applies the pre-registered
rules mechanically. Declared before running (hypotheses are those of run.py; this file only orchestrates):
  * the L_dns rule is applied mechanically to the measured L_dns of the DEAD site seen from the resolving container (evidence)
    under netem: p95 <= 50 ms AND a watcher polling at <= 0.1 s -> B2-kill; otherwise B2-kill is NOT run and the value is reported;
  * the P-log threshold is 10% of the predicted direct withdrawal of the cell (prediction (a): n_RTT*R for FANOUT 10, 10*n_RTT*R for
    the sequential FANOUT 1, R = 2d), per arm and FANOUT, accepted if the calibrated p95 of the log latency is below it; the file is
    written and its sha256 recorded BEFORE B1, and the sequence waits (--commit-wait-min) for a flag file so that the session can
    commit it first; if no one commits it in time the sequence goes on (noted) and the file is committed in the morning (same hash);
  * the B1 groups follow the registered order (seed 20261014, run.group_cells) and each group is ONE run.py invocation (same
    (arm, FANOUT, T) key, one cluster: the rule is unchanged); a failed group does not stop the queue; three consecutive profile
    failures stop the block; no new group starts after --end-utc; disk < 2 GB or a leftover dibtnsm container stops everything.
Not done here: k = 50, B2-partition, any interpretation of results. Usage (on the node, from the frozen tree):
  setsid nohup <venv>/python night.py --tree <tree> --out <dir> --end-utc 2026-10-11T06:00:00Z --watcher-poll 0.5 \
     --expect <relpath>=<sha256> ... > <dir>/night.stdout 2>&1 & echo $! > <dir>/night.pid"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as m67  # noqa: E402

SERVICE_SHA = "3186304363ed309241134752689423088dda98b9d8fe3bcdf9669749264398fd"
LDNS_MAX_MS = 50.0
M12_MIN_LEFT_S = 3 * 3600
MIN_FREE_BYTES = 2_000_000_000
DOCKER = "/snap/bin/docker"
SEED = 20261014


def ldns_decision(killed_p95_ms, watcher_poll: float) -> tuple[str, str]:
    if killed_p95_ms is None:
        return "skip", "L_dns not measured: B2-kill not run"
    if killed_p95_ms <= LDNS_MAX_MS:
        if watcher_poll <= 0.1:
            return "run", f"L_dns p95 {killed_p95_ms:.1f} ms <= 50 ms and watcher poll {watcher_poll} s <= 0.1 s"
        return "skip", (f"L_dns p95 {killed_p95_ms:.1f} ms <= 50 ms, but the watcher polls every {watcher_poll} s (> 0.1 s needed by B2-kill, "
                        f"and it must not be changed overnight): B2-kill not run")
    return "skip", (f"L_dns p95 {killed_p95_ms:.1f} ms > 50 ms: user decision (rule: >= 0.5 s only B2-partition + kill-min; in between "
                    f"recompute the cost table)")


def plog_thresholds(profile: str, calibrated_p95_ms: float) -> dict:
    R = m67.PROFILES[profile]["R"]
    cells = {}
    for arm in ("D", "C"):
        for fo in (1, 10):
            pred = (m67.N_RTT[arm] * R * (10 if fo == 1 else 1)) * 1000.0     # sequential fan-out reaches the last site after 10 deliveries
            thr = 0.10 * pred
            cells[f"{arm}/{fo}"] = {"predicted_direct_median_ms": pred, "threshold_ms": thr, "accepted": calibrated_p95_ms < thr}
    return {"profile": profile, "calibrated_p95_ms": calibrated_p95_ms,
            "rule": "p95 of the log latency < 10% of the median direct withdrawal of the cell (denominator: prediction (a), "
                    "n_RTT*R, x10 for the sequential FANOUT 1); the per-cell rule on the OBSERVED median stays in the cell summary",
            "cells": cells}


def group_order(profile: str, blocks: list[str], arms: list[str], seed: int) -> list[tuple]:
    cells = m67.plan(profile, blocks, arms, None, None)
    rng = random.Random(seed)
    rng.shuffle(cells)
    return [k for k, _ in m67.group_cells(cells, rng)]


def can_start(end_ts: float, now: float) -> bool:
    return now < end_ts


def can_start_m12(end_ts: float, now: float) -> bool:
    return end_ts - now >= M12_MIN_LEFT_S


class FailureCounter:
    def __init__(self, limit: int):
        self.limit, self.n = limit, 0

    def record(self, ok: bool) -> bool:
        """True when `limit` consecutive failures were reached."""
        self.n = 0 if ok else self.n + 1
        return self.n >= self.limit


def check_hashes(root: Path, expect: dict) -> list[str]:
    bad = []
    for rel, sha in expect.items():
        p = root / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            bad.append(rel)
    return bad


def parse_ldns(text: str):
    try:
        return json.loads(text.strip())
    except ValueError:
        pass
    import re
    m = re.search(r"\{.*\"killed\".*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------------------------------------------- runtime
def now_s() -> float:
    return time.time()


def log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).strftime('%FT%T.%fZ')[:-4]}Z {msg}", flush=True)


class State:
    def __init__(self, path: Path):
        self.path, self.d = path, {"events": []}

    def event(self, kind: str, **kw) -> None:
        self.d["events"].append({"t": datetime.now(timezone.utc).isoformat(), "kind": kind, **kw})
        self.save()
        log(f"{kind} {json.dumps(kw, default=str)}")

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, indent=1, default=str))
        tmp.replace(self.path)


def run_logged(cmd: list[str], logfile: Path, timeout: float) -> int:
    with logfile.open("ab") as fh:
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT)
        try:
            return p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            return -9


def project_containers() -> list[str]:
    r = subprocess.run([DOCKER, "ps", "-a", "--filter", "label=com.docker.compose.project=dibtnsm", "--format", "{{.Names}}"],
                       capture_output=True, text=True, timeout=60)
    return [x for x in r.stdout.split() if x]


def teardown(tree: Path, st: State) -> None:
    if not project_containers():
        return
    try:
        m67.Env(str(tree), "D", 10, 5, Path.home() / "dib_tnsm/pki").down()   # docker compose -p dibtnsm down -v --remove-orphans
    except Exception as exc:  # noqa: BLE001
        st.event("teardown_error", error=repr(exc))
    st.event("teardown", left=project_containers())


def free_ok() -> bool:
    return shutil.disk_usage("/").free >= MIN_FREE_BYTES


def run_groups(label: str, block: str, keys: list[tuple], a, tree: Path, out: Path, st: State, end_ts: float, extra) -> None:
    py = sys.executable
    fc = FailureCounter(3)
    for key in keys:
        arm, fo, T = key
        name = f"{label}_{arm}" + ("" if block == "b2kill" else f"_f{fo}")
        if not can_start(end_ts, now_s()):
            st.event("skip_group_after_end", group=name)
            continue
        if not free_ok():
            st.event("stop_block_disk", block=label)
            return
        cmd = [py, str(tree / "experiments_tnsm/m67_retraction/run.py"), "--block", block, "--profile", a.profile, "--tree", str(tree),
               "--out", str(out / name), "--arms", arm, "--seed", str(SEED), "--profile-wait", "90"] + extra(arm, fo, T)
        st.event("group_start", group=name, cmd=cmd[2:])
        rc = run_logged(cmd, out / f"{name}.log", timeout=4 * 3600)
        cells = out / name / "cells.jsonl"
        aborted = []
        if cells.exists():
            aborted = [json.loads(l).get("aborted") for l in cells.read_text().splitlines() if l.strip() and json.loads(l).get("aborted")]
        ok = rc == 0 and not aborted
        st.event("group_end", group=name, returncode=rc, aborted=aborted, ok=ok)
        teardown(tree, st)
        if fc.record(ok):
            st.event("stop_block_three_failures", block=label)
            return


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--end-utc", required=True, help="no new group or block after this time (ISO, Z)")
    ap.add_argument("--profile", default="wan")
    ap.add_argument("--arms", default="D,C")
    ap.add_argument("--watcher-poll", type=float, required=True, help="poll interval (s) the user started the watcher with")
    ap.add_argument("--expect", action="append", default=[], help="relpath=sha256 of a frozen file (repeatable); mismatch is fatal")
    ap.add_argument("--commit-wait-min", type=float, default=10.0)
    ap.add_argument("--no-m12", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tree = Path(a.tree).expanduser().resolve()
    out = Path(a.out).expanduser()
    arms = a.arms.split(",")
    end_ts = datetime.fromisoformat(a.end_utc.replace("Z", "+00:00")).timestamp()
    b1_keys = group_order(a.profile, ["b1"], arms, SEED)
    b2_keys = group_order(a.profile, ["b2kill"], arms, SEED)
    if a.dry_run:
        print(f"DRY RUN profile={a.profile} end={a.end_utc} watcher_poll={a.watcher_poll}")
        print("B1 group order:", b1_keys)
        print("B2-kill group order (only if the L_dns rule allows):", b2_keys)
        print("L_dns rule at poll", a.watcher_poll, "and p95 12 ms ->", ldns_decision(12.0, a.watcher_poll))
        return 0
    out.mkdir(parents=True, exist_ok=True)
    (out / "night.pid").write_text(str(os.getpid()))
    st = State(out / "state.json")
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    expect = dict(x.split("=", 1) for x in a.expect)
    st.event("start", tree=str(tree), end_utc=a.end_utc, watcher_poll=a.watcher_poll, python=sys.version.split()[0])
    try:
        bad = check_hashes(tree, expect) + check_hashes(tree, {"code/src/dib/registry/distributed/service.py": SERVICE_SHA})
        if bad:
            st.event("fatal_hash_mismatch", files=bad)
            return 2
        st.event("hashes_ok", files=sorted(expect) + ["code/src/dib/registry/distributed/service.py"])
        if project_containers():
            st.event("fatal_leftover_containers", containers=project_containers())
            return 2
        if not free_ok():
            st.event("fatal_disk", free=shutil.disk_usage("/").free)
            return 2
        # ---- 1.1 calibrations
        py = sys.executable
        cdir = out / "calib"
        rc = run_logged([py, str(tree / "experiments_tnsm/m67_retraction/calib_profile.py"), "--tree", str(tree), "--out", str(cdir),
                         "--profile", a.profile, "--profile-wait", "90"], out / "calib.log", timeout=3600)
        res = ldns = logs = None
        try:
            res = json.loads((cdir / f"calib_{a.profile}_result.json").read_text())
            ldns = parse_ldns((cdir / f"calib_ldns_{a.profile}.txt").read_text())
            logs = json.loads((cdir / f"calib_logs_{a.profile}.json").read_text())
        except Exception as exc:  # noqa: BLE001
            st.event("calibration_incomplete", error=repr(exc))
        st.event("calibration", returncode=rc, rtt_check_ok=(res or {}).get("rtt_check_ok"),
                 generator_path_ms=(res or {}).get("generator_path_ms"), ldns=ldns)
        teardown(tree, st)
        if rc != 0 or not res or not res.get("rtt_check_ok") or logs is None:
            st.event("stop_wan_block", reason="calibration failed or the profile was not confirmed by the RTT probe")
        else:
            p95 = max([logs["single"]["p95_ms"]] + [v["p95_ms"] for v in logs["parallel"].values() if isinstance(v, dict) and "p95_ms" in v])
            thr = plog_thresholds(a.profile, p95)
            tf = out / f"plog_thresholds_{a.profile}.json"
            tf.write_text(json.dumps(thr, indent=1))
            st.event("threshold_file", path=str(tf), sha256=hashlib.sha256(tf.read_bytes()).hexdigest(), calibrated_p95_ms=p95, cells=thr["cells"])
            flag = out / "threshold_committed"
            t_w = now_s()
            while not flag.exists() and now_s() - t_w < a.commit_wait_min * 60:
                time.sleep(5)
            st.event("threshold_commit_wait", flag_seen=flag.exists(), waited_s=round(now_s() - t_w))
            # ---- 1.2 B1
            run_groups("b1", "b1", b1_keys, a, tree, out, st, end_ts,
                       lambda arm, fo, T: ["--fanouts", str(fo), "--plog-thresholds", str(tf), "--plog-p95-ms", str(p95)])
            # ---- 1.3 B2-kill, only if the rule allows it
            killed = (ldns or {}).get("killed", {})
            decision, why = ldns_decision(killed.get("p95_ms"), a.watcher_poll)
            st.event("ldns_decision", decision=decision, reason=why, killed=killed, alive=(ldns or {}).get("alive"))
            if decision == "run" and can_start(end_ts, now_s()):
                arms_keys = [(arm, 10, 5.0) for arm in arms]          # one invocation per arm (both T inside, 10 trials per cell)
                run_groups("b2kill", "b2kill", arms_keys, a, tree, out, st, end_ts,
                           lambda arm, fo, T: ["--l-dns", str(killed["p95_ms"] / 1000.0),
                                               "--watch-log", str(Path.home() / f"dib_tnsm/m67/watch_{a.profile}.log")])
        # ---- 1.3b teardown
        teardown(tree, st)
        # ---- 3. M1/M2, only with >= 3 h left, serialized after the wan block
        commit = tree.name.split("-", 1)[-1]
        for name, script, extra in (("m1", "m1_single_node/run.py", []), ("m2", "m2_p99_tail/run.py", ["--arm", "deploy"])):
            if a.no_m12 or not can_start_m12(end_ts, now_s()):
                st.event("skip_" + name, reason="--no-m12 or less than 3 h left")
                continue
            d = out / name
            st.event(name + "_start")
            rc = run_logged([py, str(tree / "experiments_tnsm" / script), "--code", str(tree / "code"), "--out", str(d), "--commit", commit] + extra,
                            out / f"{name}.log", timeout=12 * 3600)
            st.event(name + "_end", returncode=rc)
            n_cells = len((d / "cells.jsonl").read_text().splitlines()) if (d / "cells.jsonl").exists() else 0
            (out / f"{name}_STATE.md").write_text(f"{name}: returncode {rc}, cells written {n_cells}. Not analysed.\n")
    except KeyboardInterrupt:
        st.event("interrupted")
    except Exception as exc:  # noqa: BLE001
        st.event("orchestrator_error", error=repr(exc))
    finally:
        teardown(tree, st)
        st.event("done", containers_left=project_containers(), free_bytes=shutil.disk_usage("/").free)
        (out / "DONE").write_text(datetime.now(timezone.utc).isoformat())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
