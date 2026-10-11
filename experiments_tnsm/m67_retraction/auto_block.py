#!/usr/bin/env python3
"""Orchestrator of the network blocks (FASE 3 of the automation plan, 2026-10-11). NEW file: it does not modify night.py, run.py or any frozen
script; it only calls them (calib_profile.py, run.py) and reuses night.py's pure functions (thresholds, hashes, state). It runs ON THE NODE,
detached (see launch_auto_block.sh), WITHOUT sudo: the netem profile is requested from the user's watcher v2 (netem_watch2.sh) through
profile_ctl.py and verified from the watcher's own profile.applied (11 of 11 containers, coherent `tc qdisc show`).

Sequence of ONE block (profile P; blocks lan_before -> degraded -> lan_after in this order; wan / regional only if named with --blocks):
  1. initial checks, stop on any failure: no dibtnsm container, no run.py process, df / > 2 GB, every PKI certificate valid until at least
     end + 2 h, sha256 of the frozen tree and of the new files (+ service.py), watcher heartbeat alive;
  2. request P to the watcher (acknowledged without a cluster; confirmed 11 of 11 once the cluster exists, by the ProfileMonitor);
  3. (not at lan: user decision 2026-10-11) calibration: calib_profile.py --profile P (RTT check, log latency, L_dns in the same invocation); mechanical P-log thresholds with
     night.plog_thresholds; file written, sha256 recorded in the state BEFORE the first B1 datum (the node has no git: the file is committed
     with the same hash afterwards; with --commit-wait-min > 0 the block waits for the flag file `threshold_committed`);
  4. B1 with the pre-registered design, ONE run.py invocation PER GROUP (arm, FANOUT) in the registered order (user decision 2026-10-11,
     replaces the single invocation), seed 20261014 (episodes per cell from run.py:
     50 at degraded, 10 at lan/wan); --smoke = 3 episodes, FANOUT 10 only (same code path);
  5. teardown of the project, data manifest DATA.sha256 (sha256 of every file but *.pcap), request `lan` and check of profile.applied.
The workstation copy of the data with sha256 on both sides is NOT done here (it needs ssh): it is done by the supervising session.
Rules applied mechanically (declared before running): a block STOPS (child terminated with SIGINT, then SIGKILL; teardown; `lan` requested;
manifest written) if the watcher heartbeat dies, disk < 2 GB, a PKI certificate expires, profile.applied stops matching the expected state,
or the RTT check fails on 3 consecutive cells; a failed step is recorded and the queue goes on with the next block (whose initial checks
decide); ONE relaunch of a step, only if it produced no data and with the cause recorded (B1: per group, no non-aborted cell in cells.jsonl; calibration:
no result with rtt_check_ok); a step that produced data is never relaunched; no thresholds, discard rules or code are changed. B2-kill is NOT
part of this sequence. A non-smoke block needs smoke_ok_<profile> (written by a successful --smoke with the same hashes). Exit status: 3 if a final `lan` request could not be confirmed, else 0.
Usage (on the node): python auto_block.py --tree <tree> --out <dir> --end-utc <ISO Z> --hashes <frozen_hashes file> --dir ~/dib_tnsm/m67
       [--blocks lan_before,degraded,lan_after] [--smoke] [--commit-wait-min 0] [--dry-run]"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import night  # noqa: E402
import profile_ctl as pc  # noqa: E402
from make_plog_thresholds import p95_of  # noqa: E402
from night import MIN_FREE_BYTES, SEED, SERVICE_SHA, State, check_hashes  # noqa: E402

BLOCKS = {"lan_before": "lan", "degraded": "degraded", "lan_after": "lan", "wan": "wan", "regional": "regional"}   # registered order
DEFAULT_BLOCKS = ["lan_before", "degraded", "lan_after"]
PKI_MARGIN_S = 2 * 3600
RTT_STREAK_STOP = 3
PREFLIGHT_HEARTBEAT_MAX_AGE_S = 10.0     # fresher than the 15 s used during the run: a block does not start on a stale heartbeat
_WATCH_RE = re.compile(r"netem_watch\w*\.sh")
RUN_REL = "experiments_tnsm/m67_retraction/run.py"
CALIB_REL = "experiments_tnsm/m67_retraction/calib_profile.py"
SERVICE_REL = "code/src/dib/registry/distributed/service.py"


def select_blocks(spec: str | None) -> list[str]:
    if not spec:
        return list(DEFAULT_BLOCKS)
    want = [x.strip() for x in spec.split(",") if x.strip()]
    bad = [x for x in want if x not in BLOCKS]
    if bad:
        raise ValueError(f"unknown block(s) {bad}; allowed: {list(BLOCKS)}")
    return [b for b in BLOCKS if b in want]


# ---------------------------------------------------------------------------------------------------------------- system access
class System:
    """Everything that touches the node. Tests replace it."""
    def containers(self) -> list[str]:
        return night.project_containers()

    def runpy_running(self) -> bool:
        me = {os.getpid(), os.getppid()}
        for p in Path("/proc").glob("[0-9]*"):
            try:
                if int(p.name) not in me and b"m67_retraction/run.py" in (p / "cmdline").read_bytes():
                    return True
            except OSError:
                continue
        return False

    def other_watchers(self) -> list[tuple[int, str]]:
        """(pid, command line) of every process that runs a netem_watch*.sh script OTHER than netem_watch2.sh (the v1 watcher left active
        overnight reapplied `degraded` over the v2 in the first smoke). The sudo/timeout wrappers of the v2 carry netem_watch2.sh and are not listed."""
        me, out = {os.getpid(), os.getppid()}, []
        for p in Path("/proc").glob("[0-9]*"):
            try:
                if int(p.name) in me:
                    continue
                cmd = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            except OSError:
                continue
            if any(m != "netem_watch2.sh" for m in _WATCH_RE.findall(cmd)):
                out.append((int(p.name), cmd[:200]))
        return out

    def free_bytes(self) -> float:
        return shutil.disk_usage("/").free

    def pki_not_after(self, pki_dir) -> float:
        """Earliest notAfter (epoch) of every certificate under pki_dir; 0.0 (fail closed) if none can be read."""
        best = None
        for f in sorted(Path(pki_dir).rglob("*.crt")) + sorted(Path(pki_dir).rglob("*.pem")):
            r = subprocess.run(["openssl", "x509", "-noout", "-enddate", "-in", str(f)], capture_output=True, text=True, timeout=30)
            if r.returncode != 0 or "notAfter=" not in r.stdout:
                continue
            t = datetime.strptime(r.stdout.split("notAfter=", 1)[1].strip(), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc).timestamp()
            best = t if best is None else min(best, t)
        return 0.0 if best is None else best

    def teardown(self, tree: Path, st: State) -> None:
        night.teardown(tree, st)

    def spawn(self, cmd: list[str], logfile: Path) -> subprocess.Popen:
        # launched with `&` from a non-interactive shell, this process ignores SIGINT and a child would inherit that (Python then installs no
        # KeyboardInterrupt handler: terminate() would do nothing): give the child the default disposition (smoke of 2026-10-11)
        return subprocess.Popen(cmd, stdout=open(logfile, "ab"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))


@dataclass
class Ctx:
    tree: Path
    out: Path
    end_ts: float
    ctl: Any
    system: Any
    state: State
    expect: dict
    smoke: bool = False
    tick_s: float = 2.0
    commit_wait_s: float = 0.0
    py: str = sys.executable
    check_service_hash: bool = True
    request_timeout_s: float = 120.0
    calib_timeout_s: float = 3600.0
    run_timeout_s: float = 4 * 3600.0
    pki_dir: str = str(Path.home() / "dib_tnsm/pki")
    hb_max_age_s: float = pc.HEARTBEAT_MAX_AGE_S
    profile_wait_s: int = 90
    pki_recheck_s: float = 60.0
    require_smoke: bool = True
    smoke_dir: Path = Path.home() / "dib_tnsm/m67/smoke"
    seed: int = SEED
    arms: str = "D,C"
    on_tick: Callable | None = None
    _pki_checked: float = field(default=0.0, repr=False)


# ---------------------------------------------------------------------------------------------------------------- pure helpers
def _cells(path: Path) -> list[dict]:
    out = []
    try:
        for l in Path(path).read_text().splitlines():
            if l.strip():
                try:
                    out.append(json.loads(l))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def data_cells(path: Path) -> int:
    """Cells of a cells.jsonl that carry data (run.py writes aborted-group records without `cell_spec`)."""
    return sum(1 for r in _cells(path) if "cell_spec" in r and not r.get("aborted"))


def rtt_streak(path: Path) -> int:
    """Consecutive trailing records of cells.jsonl whose RTT check failed (a cell with profile_check_ok false, or an aborted group)."""
    n = 0
    for r in reversed(_cells(path)):
        if r.get("profile_check_ok") is False or "profile check failed" in str(r.get("aborted", "")):
            n += 1
        else:
            break
    return n


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_data_manifest(bdir: Path) -> Path:
    """DATA.sha256 (sha256sum format, paths relative to bdir), every file but *.pcap and the manifest itself."""
    lines = []
    for f in sorted(bdir.rglob("*")):
        if f.is_file() and f.suffix != ".pcap" and f.name != "DATA.sha256" and not f.is_symlink():
            lines.append(f"{sha256_file(f)}  {f.relative_to(bdir)}")
    out = bdir / "DATA.sha256"
    out.write_text("\n".join(lines) + ("\n" if lines else ""))
    return out


def calib_cmd(py: str, tree: Path, out: Path, prof: str, profile_wait: int) -> list[str]:
    return [py, str(tree / CALIB_REL), "--tree", str(tree), "--out", str(out), "--profile", prof, "--profile-wait", str(profile_wait)]


def b1_cmd(py: str, tree: Path, out: Path, prof: str, seed: int, arms: str, fanouts: str, profile_wait: int, smoke: bool,
           thr: str | None = None, p95: str | None = None) -> list[str]:
    cmd = [py, str(tree / RUN_REL), "--block", "b1", "--profile", prof, "--tree", str(tree), "--out", str(out), "--arms", arms,
           "--fanouts", fanouts, "--seed", str(seed), "--profile-wait", str(profile_wait)]
    if thr is not None:
        cmd += ["--plog-thresholds", thr, "--plog-p95-ms", p95]
    return cmd + (["--episodes", "3"] if smoke else [])


def hashes_id(expect: dict) -> str:
    return hashlib.sha256(json.dumps(sorted(expect.items())).encode()).hexdigest()


def b1_groups(prof: str, arms: str, seed: int, smoke: bool) -> list[tuple]:
    """Groups (arm, FANOUT, T) in the registered order (night.group_order: same shuffle as run.py); smoke keeps FANOUT 10 only."""
    return [k for k in night.group_order(prof, ["b1"], arms.split(","), seed) if not smoke or k[1] == 10]


# ---------------------------------------------------------------------------------------------------------------- monitor
class ProfileMonitor:
    """Records every new profile.applied record in profile_events.jsonl; returns a problem text when a record with all 11 containers
    does not match the expected state. Partial clusters (a cluster being created) and `containers: 0` are recorded and ignored."""
    def __init__(self, ctl, path: Path):
        self.ctl, self.path, self.last = ctl, Path(path), None

    def poll(self) -> str | None:
        try:
            a = self.ctl.read_applied()
        except pc.ProfileError:
            return None
        if a.epoch_ms == self.last:
            return None
        self.last = a.epoch_ms
        probs, coherent = [], None
        if a.containers == len(pc.NAMES) and self.ctl.expected_base is not None:
            probs = pc.check_coherent(a, self.ctl.expected_base, self.ctl.expected_partition)
            coherent = not probs
        with self.path.open("a") as f:
            f.write(json.dumps({"epoch_ms": a.epoch_ms, "applied_utc": a.applied_utc, "request": a.request, "trigger": a.trigger, "base": a.base,
                                "partition": a.partition, "containers": a.containers, "coherent": coherent, "problems": probs}) + "\n")
        return "; ".join(probs) if probs else None


# ---------------------------------------------------------------------------------------------------------------- checks and supervision
def preflight(ctx: Ctx) -> list[str]:
    probs = []
    c = ctx.system.containers()
    if c:
        probs.append(f"dibtnsm container present: {c}")
    if ctx.system.runpy_running():
        probs.append("a run.py process is running")
    free = ctx.system.free_bytes()
    if free < MIN_FREE_BYTES:
        probs.append(f"disk: {free / 1e9:.2f} GB free on /, need > 2 GB")
    pki = ctx.system.pki_not_after(ctx.pki_dir)
    if pki <= ctx.end_ts + PKI_MARGIN_S:
        probs.append(f"pki: earliest certificate expiry {datetime.fromtimestamp(pki, timezone.utc).isoformat()} is not 2 h beyond the end "
                     f"{datetime.fromtimestamp(ctx.end_ts, timezone.utc).isoformat()}")
    exp = dict(ctx.expect)
    if ctx.check_service_hash:
        exp[SERVICE_REL] = SERVICE_SHA
    bad = check_hashes(ctx.tree, exp)
    if bad:
        probs.append(f"hash mismatch or missing file: {bad}")
    others = ctx.system.other_watchers()
    if others:
        probs.append(f"another netem watcher is running besides the v2 (it would fight over the qdisc): {others}")
    try:
        ctx.ctl.check_alive(min(ctx.hb_max_age_s, PREFLIGHT_HEARTBEAT_MAX_AGE_S))
    except pc.WatcherDown as exc:
        probs.append(f"watcher not alive or heartbeat older than {PREFLIGHT_HEARTBEAT_MAX_AGE_S:g} s: {exc}")
    return probs


def smoke_marker(ctx: Ctx, prof: str) -> Path:
    return Path(ctx.smoke_dir) / f"smoke_ok_{prof}.json"


def smoke_ok(ctx: Ctx, prof: str) -> bool:
    try:
        return json.loads(smoke_marker(ctx, prof).read_text()).get("hashes_id") == hashes_id(ctx.expect)
    except (OSError, ValueError):
        return False


def _violation(ctx: Ctx, cells: Path | None, monitor: ProfileMonitor | None) -> str | None:
    try:
        ctx.ctl.check_alive(ctx.hb_max_age_s)
    except pc.WatcherDown as exc:
        return f"watcher stopped: {exc}"
    free = ctx.system.free_bytes()
    if free < MIN_FREE_BYTES:
        return f"disk below 2 GB ({free / 1e9:.2f} GB)"
    now = time.time()
    if now - ctx._pki_checked >= ctx.pki_recheck_s:
        ctx._pki_checked = now
        if ctx.system.pki_not_after(ctx.pki_dir) <= now:
            return "pki certificate expired"
    if monitor is not None:
        p = monitor.poll()
        if p:
            return f"profile.applied does not match the expected profile: {p}"
    if cells is not None and rtt_streak(cells) >= RTT_STREAK_STOP:
        return f"rtt does not match the profile on {rtt_streak(cells)} consecutive cells"
    return None


def terminate(proc: subprocess.Popen, grace_s: float = 120.0) -> None:
    proc.send_signal(signal.SIGINT)                    # KeyboardInterrupt: the child's own finally clauses take the cluster down
    try:
        proc.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def supervised_run(ctx: Ctx, cmd: list[str], logfile: Path, timeout_s: float, cells: Path | None = None,
                   monitor: ProfileMonitor | None = None) -> tuple[int | None, str | None]:
    """Runs a child; returns (returncode, stop_reason). stop_reason is set when a block-stop rule fired and the child was terminated."""
    proc = ctx.system.spawn(cmd, logfile)
    t0 = time.time()
    while True:
        try:
            return proc.wait(timeout=ctx.tick_s), None
        except subprocess.TimeoutExpired:
            pass
        if ctx.on_tick:
            ctx.on_tick()
        reason = _violation(ctx, cells, monitor)
        if reason is None and time.time() - t0 > timeout_s:
            reason = f"child timeout after {timeout_s:.0f} s"
        if reason:
            terminate(proc)
            return proc.returncode, reason


def _tail(p: Path, n: int = 5) -> str:
    try:
        return " | ".join(p.read_text(errors="replace").splitlines()[-n:])
    except OSError:
        return "(no log)"


# ---------------------------------------------------------------------------------------------------------------- one block
def _calibrate(ctx: Ctx, name: str, prof: str, bdir: Path, mon: ProfileMonitor, res: dict):
    """Returns (p95_ms, None) or (None, reason)."""
    st = ctx.state
    for attempt in (1, 2):
        cdir = bdir / ("calib" if attempt == 1 else "calib_retry1")
        log = bdir / ("calib.log" if attempt == 1 else "calib_retry1.log")
        st.event("calibration_start", block=name, attempt=attempt)
        rc, reason = supervised_run(ctx, calib_cmd(ctx.py, ctx.tree, cdir, prof, ctx.profile_wait_s), log, ctx.calib_timeout_s, None, mon)
        ctx.system.teardown(ctx.tree, st)
        if reason:
            return None, reason
        result = logs = ldns = None
        try:
            result = json.loads((cdir / f"calib_{prof}_result.json").read_text())
            logs = json.loads((cdir / f"calib_logs_{prof}.json").read_text())
            ldns = night.parse_ldns((cdir / f"calib_ldns_{prof}.txt").read_text())
        except (OSError, ValueError):
            pass
        st.event("calibration", block=name, attempt=attempt, returncode=rc, rtt_check_ok=(result or {}).get("rtt_check_ok"),
                 generator_path_ms=(result or {}).get("generator_path_ms"), ldns=ldns)
        if result and result.get("rtt_check_ok") and logs is not None:
            return p95_of(logs), None
        cause = f"returncode {rc}, rtt_check_ok {(result or {}).get('rtt_check_ok')}, log: {_tail(log)}"
        if attempt == 1:
            st.event("calibration_retry", block=name, cause=cause)
        else:
            return None, f"calibration failed twice (profile not confirmed by the RTT or no result): {cause}"
    return None, "calibration"


def _b1(ctx: Ctx, name: str, prof: str, bdir: Path, mon: ProfileMonitor, thr: Path | None, p95: float | None, res: dict) -> str | None:
    """B1 as ONE run.py invocation PER GROUP (arm, FANOUT), in the registered order (user decision 2026-10-11). A group is relaunched once,
    only if it produced no data (cause recorded); a group with data is never relaunched; a failed group does not stop the queue. Returns a
    stop reason or None."""
    st = ctx.state
    fc = night.FailureCounter(3)
    res["groups"] = {}
    for arm, fo, T in b1_groups(prof, ctx.arms, ctx.seed, ctx.smoke):
        g = f"{arm}_f{fo}"
        n = 0
        for attempt in (1, 2):
            od = bdir / (f"b1_{g}" if attempt == 1 else f"b1_{g}_retry1")
            log = bdir / (f"b1_{g}.log" if attempt == 1 else f"b1_{g}_retry1.log")
            cmd = b1_cmd(ctx.py, ctx.tree, od, prof, ctx.seed, arm, str(fo), ctx.profile_wait_s, ctx.smoke,
                         None if thr is None else str(thr), None if p95 is None else repr(p95))
            st.event("b1_start", block=name, group=g, attempt=attempt, cmd=cmd[1:])
            rc, reason = supervised_run(ctx, cmd, log, ctx.run_timeout_s, od / "cells.jsonl", mon)
            ctx.system.teardown(ctx.tree, st)
            n = data_cells(od / "cells.jsonl")
            aborted = [r.get("aborted") for r in _cells(od / "cells.jsonl") if r.get("aborted")]
            st.event("b1_end", block=name, group=g, attempt=attempt, returncode=rc, data_cells=n, aborted=aborted, stop=reason)
            res["b1_data_cells"] += n
            if reason:
                return reason
            if n == 0 and attempt == 1:
                st.event("b1_retry", block=name, group=g, cause=f"no data produced; returncode {rc}, aborted {aborted}, log: {_tail(log)}")
                continue
            if n == 0:
                res["groups"][g] = "no data after one relaunch"
            elif rc != 0 or aborted:
                res["groups"][g] = f"data produced, returncode {rc}, aborted {aborted}; not relaunched"
            else:
                res["groups"][g] = "ok"
            break
        if res["groups"][g] != "ok":
            res["status"], res["reason"] = "done_with_errors", "; ".join(f"{k}: {v}" for k, v in res["groups"].items() if v != "ok")
        if fc.record(n > 0):
            return "three consecutive groups without data"
    return None


def run_block(ctx: Ctx, name: str) -> dict:
    prof = BLOCKS[name]
    bdir = ctx.out / name
    bdir.mkdir(parents=True, exist_ok=True)
    st = ctx.state
    res = {"block": name, "profile": prof, "status": "done", "reason": None, "lan_confirmed": None, "b1_data_cells": 0}
    st.event("block_start", block=name, profile=prof, smoke=ctx.smoke)
    probs = preflight(ctx)
    if not ctx.smoke and ctx.require_smoke and not smoke_ok(ctx, prof):
        probs.append(f"smoke: no successful --smoke run of profile {prof} with these hashes ({smoke_marker(ctx, prof)}); new groups need their smoke cell first")
    if probs:
        res.update(status="stopped", reason="preflight: " + "; ".join(probs))
        st.event("stop_block", block=name, reason=res["reason"])
        return res
    stop = None
    try:
        a = ctx.ctl.request(prof, timeout_s=ctx.request_timeout_s, allow_no_cluster=True)
        st.event("profile_requested", block=name, request=prof, containers=getattr(a, "containers", None))
        mon = ProfileMonitor(ctx.ctl, bdir / "profile_events.jsonl")
        if prof == "lan":     # user decision 2026-10-11: no calibration and no thresholds at lan (as the earlier lan sessions: dispute-rtt)
            p95, tf, stop = None, None, None
            st.event("calibration_skipped", block=name, reason="lan: no calibration, no P-log thresholds")
        else:
            p95, stop = _calibrate(ctx, name, prof, bdir, mon, res)
            tf = None
            if stop is None:
                thr = night.plog_thresholds(prof, p95)
                tf = bdir / f"plog_thresholds_{prof}.json"
                tf.write_text(json.dumps(thr, indent=1))
                st.event("threshold_file", block=name, path=str(tf), sha256=sha256_file(tf), calibrated_p95_ms=p95, cells=thr["cells"])
                flag, t_w = bdir / "threshold_committed", time.time()
                while not flag.exists() and time.time() - t_w < ctx.commit_wait_s:
                    time.sleep(min(5.0, max(0.05, ctx.commit_wait_s)))
                st.event("threshold_commit_wait", block=name, flag_seen=flag.exists(), waited_s=round(time.time() - t_w))
        if stop is None:
            stop = _b1(ctx, name, prof, bdir, mon, tf, p95, res)
    except pc.ProfileError as exc:
        stop = f"profile request failed: {exc}"
    except KeyboardInterrupt:
        stop = "interrupted"
    finally:
        if stop:
            res.update(status="stopped", reason=stop)
            st.event("stop_block", block=name, reason=stop)
        try:
            ctx.system.teardown(ctx.tree, st)
            write_data_manifest(bdir)
        except Exception as exc:  # noqa: BLE001
            st.event("block_cleanup_error", block=name, error=repr(exc))
        try:
            ctx.ctl.request("lan", timeout_s=ctx.request_timeout_s, allow_no_cluster=True)
            res["lan_confirmed"] = True
            st.event("lan_confirmed", block=name)
        except pc.ProfileError as exc:
            res["lan_confirmed"] = False
            st.event("lan_not_confirmed", block=name, error=str(exc))
    if ctx.smoke and res["status"] == "done" and res["lan_confirmed"]:
        Path(ctx.smoke_dir).mkdir(parents=True, exist_ok=True)
        smoke_marker(ctx, prof).write_text(json.dumps({"hashes_id": hashes_id(ctx.expect), "block": name, "utc": datetime.now(timezone.utc).isoformat()}))
        st.event("smoke_ok", block=name, profile=prof)
    st.event("block_end", block=name, status=res["status"], reason=res["reason"])
    (bdir / "BLOCK.json").write_text(json.dumps(res, indent=1))
    return res


def exit_code(results: list[dict]) -> int:
    return 3 if any(r.get("lan_confirmed") is False for r in results) else 0


def write_report(ctx: Ctx, results: list[dict]) -> None:
    ev = ctx.state.d["events"]
    out = ["# Raw report of the automated blocks (generated by auto_block.py from state.json; not an analysis)", ""]
    for r in results:
        be = [e for e in ev if e.get("block") == r["block"]]
        out += [f"## {r['block']} (profile {r['profile']}): {r['status']}", f"- reason: {r['reason']}",
                f"- steps recorded: {', '.join(e['kind'] for e in be)}",
                f"- B1 cells with data: {r['b1_data_cells']}; final `lan` confirmed: {r['lan_confirmed']}"]
        for e in be:
            if e["kind"] == "threshold_file":
                out.append(f"- threshold file {e['path']} sha256 {e['sha256']} (calibrated p95 {e['calibrated_p95_ms']} ms), recorded before B1")
            if e["kind"] in ("calibration_retry", "b1_retry"):
                out.append(f"- relaunch ({e['kind']}): {e['cause']}")
        out.append("")
    (ctx.out / "REPORT_raw.md").write_text("\n".join(out))


def run_all(ctx: Ctx, blocks: list[str]) -> list[dict]:
    ctx.out.mkdir(parents=True, exist_ok=True)
    (ctx.out / "manifest.json").write_text(json.dumps({
        "block_order": blocks, "profiles": [BLOCKS[b] for b in blocks], "seed": ctx.seed, "arms": ctx.arms, "smoke": ctx.smoke, "tree": str(ctx.tree),
        "end_utc": datetime.fromtimestamp(ctx.end_ts, timezone.utc).isoformat(), "expected_hashes": ctx.expect, "python": sys.version.split()[0],
        "host": platform.node(), "argv": sys.argv, "started_utc": datetime.now(timezone.utc).isoformat(),
        "rules": "see the docstring of auto_block.py; B2-kill is not part of the sequence"}, indent=1))
    results = []
    for b in blocks:
        results.append(run_block(ctx, b))
    write_report(ctx, results)
    return results


# ---------------------------------------------------------------------------------------------------------------- command line
def dry_run(a, blocks: list[str]) -> None:
    tree = Path(a.tree)
    print(f"DRY RUN auto_block: tree={tree} out={a.out} end={a.end_utc} watcher dir={a.dir} smoke={a.smoke}")
    print("B2-kill is never part of this sequence.")
    for b in blocks:
        prof = BLOCKS[b]
        out = Path(a.out) / b
        print(f"\n== block {b} (profile {prof})")
        print("  0. initial checks: no dibtnsm container, no run.py, df / > 2 GB, PKI valid until end + 2 h, hashes, watcher heartbeat")
        print(f"  1. request {prof}   (profile_ctl.ProfileCtl.request, file {a.dir}/profile.request)")
        if prof == "lan":
            print("  2-3. no calibration, no thresholds at lan")
        else:
            print("  2. " + " ".join(calib_cmd(sys.executable, tree, out / "calib", prof, 90)))
            print(f"  3. thresholds: night.plog_thresholds({prof!r}, p95) -> {out}/plog_thresholds_{prof}.json, sha256 into the state before B1")
        thr = None if prof == "lan" else "<thresholds.json>"
        for arm, fo, _T in b1_groups(prof, "D,C", SEED, a.smoke):
            print("  4. " + " ".join(b1_cmd(sys.executable, tree, out / f"b1_{arm}_f{fo}", prof, SEED, arm, str(fo), 90, a.smoke, thr, None if thr is None else "<p95>")))
        print(f"  5. teardown, {out}/DATA.sha256 (no pcap), request lan, check of profile.applied")
        print("  (a non-smoke block needs smoke_ok_<profile> from a successful --smoke with the same hashes)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--end-utc", required=True, help="expected end of the whole sequence (ISO, Z): the PKI must outlive it by 2 h")
    ap.add_argument("--dir", default=str(Path.home() / "dib_tnsm/m67"), help="request directory of netem_watch2.sh")
    ap.add_argument("--hashes", default=None, help="frozen_hashes file (sha256sum format: '<sha256>  <path relative to the tree>')")
    ap.add_argument("--blocks", default=None, help="subset of " + ",".join(BLOCKS) + " (default: " + ",".join(DEFAULT_BLOCKS) + ")")
    ap.add_argument("--smoke", action="store_true", help="B1 with 3 episodes and FANOUT 10 only (smoke cell); a successful one enables the profile")
    ap.add_argument("--smoke-dir", default=str(Path.home() / "dib_tnsm/m67/smoke"))
    ap.add_argument("--commit-wait-min", type=float, default=0.0)
    ap.add_argument("--pki", default=str(Path.home() / "dib_tnsm/pki"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    blocks = select_blocks(a.blocks)
    if a.dry_run:
        dry_run(a, blocks)
        return 0
    if not a.hashes:
        print("auto_block: --hashes is required (the table the user compared)", file=sys.stderr)
        return 2
    expect = {}
    for line in Path(a.hashes).read_text().splitlines():
        if line.strip():
            sha, rel = line.split(None, 1)
            expect[rel.strip()] = sha
    tree, out = Path(a.tree).expanduser().resolve(), Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / "auto_block.pid").write_text(str(os.getpid()))
    end_ts = datetime.fromisoformat(a.end_utc.replace("Z", "+00:00")).timestamp()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    st = State(out / "state.json")
    ctx = Ctx(tree=tree, out=out, end_ts=end_ts, ctl=pc.ProfileCtl(a.dir), system=System(), state=st, expect=expect, smoke=a.smoke,
              commit_wait_s=a.commit_wait_min * 60, pki_dir=a.pki, smoke_dir=Path(a.smoke_dir))
    st.event("start", tree=str(tree), blocks=blocks, end_utc=a.end_utc, smoke=a.smoke, python=sys.version.split()[0])
    results = []
    try:
        results = run_all(ctx, blocks)
    except KeyboardInterrupt:
        st.event("interrupted")
    finally:
        st.event("done", results=[{k: r[k] for k in ("block", "status", "reason", "lan_confirmed")} for r in results])
        (out / "DONE").write_text(datetime.now(timezone.utc).isoformat())
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
