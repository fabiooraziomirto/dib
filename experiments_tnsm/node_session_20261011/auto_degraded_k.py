#!/usr/bin/env python3
"""Degraded measurements of the opt-in persistent fan-out connections (docs/audit/62, predictions H-K1..K4), started BY ITSELF when the watcher v2 is alive
again and not after --not-after. Runs on the node, detached, no sudo; reuses the frozen auto_block.py / night.py / run.py unchanged (imported from the tree).
Sequence at `degraded` (profile requested as `degraded+fast`, one calibration with the keep-alive OFF):
  b1_on  : run.py --block b1 --fanouts 10, arms D then C, DIB_M67_KEEPALIVE=1 (50 episodes per cell: run.py default at degraded);
  b1_off : the same with DIB_M67_KEEPALIVE=0 (control in the SAME session and tree);
  b2k_on : run.py --block b2kill, arms D then C, DIB_M67_KEEPALIVE=1, only if the L_dns rule of audit 45 allows it (p95 <= 50 ms and poll <= 0.1 s).
Stops: auto_block.preflight problems, watcher heartbeat, disk, PKI, profile incoherence (supervised_run); a child without data is relaunched ONCE; no step starts
after the deadline; the final request is plain `lan`."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROF = "degraded"
STEPS = [("b1_on", "b1", True), ("b1_off", "b1", False), ("b2k_on", "b2kill", True)]


def load_auto_block(tree: Path):
    sys.path.insert(0, str(Path(tree) / "experiments_tnsm" / "m67_retraction"))
    import auto_block
    return auto_block


def wait_for_watcher(ctl, deadline: float, poll_s: float = 30.0, pc=None) -> bool:
    """True as soon as the watcher heartbeat is fresh; False at the deadline."""
    while True:
        try:
            ctl.check_alive(10.0)
            return True
        except pc.WatcherDown:
            pass
        if time.time() + poll_s > deadline:
            time.sleep(max(0.0, deadline - time.time()))
            return False
        time.sleep(poll_s)


def _set_env(value: str | None):
    old = os.environ.get("DIB_M67_KEEPALIVE")
    if value is None:
        os.environ.pop("DIB_M67_KEEPALIVE", None)
    else:
        os.environ["DIB_M67_KEEPALIVE"] = value
    return old


def _restore_env(old):
    if old is None:
        os.environ.pop("DIB_M67_KEEPALIVE", None)
    else:
        os.environ["DIB_M67_KEEPALIVE"] = old


def run_sequence(ab, ctx, deadline: float, watch_log: str) -> dict:
    night, pc = ab.night, ab.pc
    st, bdir = ctx.state, ctx.out
    res = {"status": "done", "reason": None, "lan_confirmed": None, "steps": {}, "b2k_skipped": None}
    if time.time() >= deadline:
        res.update(status="stopped", reason="deadline passed before the start")
        st.event("stop", reason=res["reason"])
        return res
    probs = ab.preflight(ctx)
    if probs:
        res.update(status="stopped", reason="preflight: " + "; ".join(probs))
        st.event("stop", reason=res["reason"])
        return res
    stop = None
    old_env = os.environ.get("DIB_M67_KEEPALIVE")
    try:
        a = ctx.ctl.request(PROF + "+fast", timeout_s=ctx.request_timeout_s, allow_no_cluster=True)
        poll_s = float(a.poll_s)
        st.event("profile_requested", request=PROF + "+fast", poll_s=poll_s)
        mon = ab.ProfileMonitor(ctx.ctl, bdir / "profile_events.jsonl", grace_s=ctx.monitor_grace_s)
        _set_env("0")                                                   # calibration with the keep-alive OFF
        p95, stop = ab._calibrate(ctx, "degraded_k", PROF, bdir, mon, {})
        if stop is None:
            cdir = bdir / ("calib_retry1" if (bdir / "calib_retry1" / f"calib_{PROF}_result.json").exists() else "calib")
            ldns = night.parse_ldns((cdir / f"calib_ldns_{PROF}.txt").read_text())
            killed = (ldns or {}).get("killed", {})
            thr = night.plog_thresholds(PROF, p95)
            tf = bdir / f"plog_thresholds_{PROF}.json"
            tf.write_text(json.dumps(thr, indent=1))
            st.event("threshold_file", path=str(tf), sha256=hashlib.sha256(tf.read_bytes()).hexdigest(), calibrated_p95_ms=p95)
            decision, why = night.ldns_decision(killed.get("p95_ms"), poll_s)
            st.event("ldns_decision", decision=decision, reason=why, killed=killed)
            for step, block, ka in STEPS:
                if step == "b2k_on" and decision != "run":
                    res["b2k_skipped"] = why
                    continue
                for arm in ctx.arms.split(","):
                    if time.time() >= deadline:
                        stop = "deadline reached before " + step + "/" + arm
                        break
                    for attempt in (1, 2):
                        od = bdir / step / (arm if attempt == 1 else arm + "_retry1")
                        cmd = [ctx.py, str(ctx.tree / ab.RUN_REL), "--block", block, "--profile", PROF, "--tree", str(ctx.tree), "--out", str(od),
                               "--arms", arm, "--seed", str(ctx.seed), "--profile-wait", str(ctx.profile_wait_s)]
                        cmd += (["--fanouts", "10", "--plog-thresholds", str(tf), "--plog-p95-ms", repr(p95)] if block == "b1"
                                else ["--l-dns", repr(killed["p95_ms"] / 1000.0), "--watch-log", watch_log])
                        _set_env("1" if ka else "0")
                        st.event("step_start", step=step, arm=arm, attempt=attempt, keepalive=ka, cmd=cmd[1:])
                        try:
                            rc, reason = ab.supervised_run(ctx, cmd, bdir / f"{step}_{od.name}.log", ctx.run_timeout_s, od / "cells.jsonl", mon)
                        finally:
                            _set_env("0")
                        ctx.system.teardown(ctx.tree, st)
                        n = ab.data_cells(od / "cells.jsonl")
                        st.event("step_end", step=step, arm=arm, attempt=attempt, returncode=rc, data_cells=n, stop=reason)
                        res["steps"][f"{step}/{arm}"] = {"returncode": rc, "data_cells": n}
                        if reason:
                            stop = reason
                            break
                        if n == 0 and attempt == 1:
                            st.event("step_retry", step=step, arm=arm)
                            continue
                        break
                    if stop:
                        break
                if stop:
                    break
    except pc.ProfileError as exc:
        stop = f"profile request failed: {exc}"
    except KeyboardInterrupt:
        stop = "interrupted"
    finally:
        _restore_env(old_env)
        if stop:
            res.update(status="stopped", reason=stop)
            st.event("stop", reason=stop)
        try:
            ctx.system.teardown(ctx.tree, st)
            ab.write_data_manifest(bdir)
        except Exception as exc:  # noqa: BLE001
            st.event("cleanup_error", error=repr(exc))
        try:
            ctx.ctl.request("lan", timeout_s=ctx.request_timeout_s, allow_no_cluster=True)
            res["lan_confirmed"] = True
            st.event("lan_confirmed")
        except pc.ProfileError as exc:
            res["lan_confirmed"] = False
            st.event("lan_not_confirmed", error=str(exc))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--end-utc", required=True, help="expected end (PKI margin check)")
    ap.add_argument("--not-after", required=True, help="ISO Z: neither start nor wait beyond this time")
    ap.add_argument("--hashes", required=True)
    ap.add_argument("--dir", default=str(Path.home() / "dib_tnsm/m67"))
    ap.add_argument("--watch-log", default=str(Path.home() / "dib_tnsm/m67/watch2_stdout.log"))
    a = ap.parse_args(argv)
    ab = load_auto_block(Path(a.tree))
    tree, out = Path(a.tree).expanduser().resolve(), Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / "auto_degraded_k.pid").write_text(str(os.getpid()))
    expect = {}
    for line in Path(a.hashes).read_text().splitlines():
        if line.strip():
            sha, rel = line.split(None, 1)
            expect[rel.strip()] = sha
    iso = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()  # noqa: E731
    end_ts, deadline = iso(a.end_utc), iso(a.not_after)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    st = ab.State(out / "state.json")
    ctl = ab.pc.ProfileCtl(a.dir)
    st.event("waiting_for_watcher", not_after=a.not_after)
    if not wait_for_watcher(ctl, deadline, pc=ab.pc):
        st.event("watcher_never_alive_before_deadline")
        (out / "NOT_STARTED").write_text(datetime.now(timezone.utc).isoformat())
        return 0
    ctx = ab.Ctx(tree=tree, out=out, end_ts=end_ts, ctl=ctl, system=ab.System(), state=st, expect=expect, require_smoke=False, check_service_hash=False)
    (out / "manifest.json").write_text(json.dumps({"tree": str(tree), "expected_hashes": expect, "steps": [s[0] for s in STEPS], "seed": ctx.seed,
        "arms": ctx.arms, "python": sys.version.split()[0], "host": platform.node(), "argv": sys.argv, "audit": "62",
        "started_utc": datetime.now(timezone.utc).isoformat(), "not_after": a.not_after}, indent=1))
    res = run_sequence(ab, ctx, deadline, a.watch_log)
    (out / "RESULT.json").write_text(json.dumps(res, indent=1))
    st.event("done", status=res["status"])
    (out / "DONE").write_text(datetime.now(timezone.utc).isoformat())
    return 3 if res["lan_confirmed"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
