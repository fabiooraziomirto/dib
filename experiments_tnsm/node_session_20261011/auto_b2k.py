#!/usr/bin/env python3
"""B2-kill orchestrator (audit 45; audit 43 B1a + B2k). Runs ON THE NODE, detached, no sudo. It only orchestrates the FROZEN scripts of the tree
(calib_profile.py, run.py --block b2kill) and reuses auto_block.py (imported from the tree, unchanged) for the checks, the supervision and the
profile controller; it adds the one thing auto_block does not do: request `<profile>+fast` (watcher poll 0.1 s, needed by the L_dns rule).
Per block (profiles lan, degraded, wan, in this order; k = 1/10/50 at lan, 1/10 elsewhere, 10 trials per cell, T = 5/15: run.py B2_KS/B2_TS):
  0. auto_block.preflight (no container, no run.py, disk > 2 GB, PKI 2 h beyond the end, hashes, one watcher, fresh heartbeat);
  1. request `<profile>+fast` (the Applied record must say poll_s <= 0.1);
  2. calib_profile.py at the profile (also at lan: L_dns of the dead site seen from the resolving container, RTT check, P-log);
  3. night.ldns_decision(killed p95, poll_s): run only if p95 <= 50 ms and poll <= 0.1 s; the attempt is recorded in --attempts-file; two failed
     attempts on two different UTC days refuse a third (audit 45 s.5); no threshold change;
  4. ONE run.py --block b2kill per arm (D, then C) with --l-dns p95/1000 and --watch-log; a group with data is never relaunched, one without data
     is relaunched once;
  5. teardown, data manifest (sha256, no pcap), plain `lan` request (checked; a failed one makes the exit code 3).
Deviation from audit 43 B2k dependencies ("smoke cell of B2-kill"): run.py has no smoke option for b2kill; the `lan` block (the cheapest, ~0.4 h)
runs first and its data are kept; a failure there stops the sequence. Usage: see launch_auto_b2k.sh."""
from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROFILES = ["lan", "degraded", "wan"]
LDNS_MAX_ATTEMPT_DAYS = 2


def load_auto_block(tree: Path):
    sys.path.insert(0, str(Path(tree) / "experiments_tnsm" / "m67_retraction"))
    import auto_block  # noqa: WPS433
    return auto_block


def _attempts(path: Path, prof: str) -> list[dict]:
    try:
        rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    except OSError:
        return []
    return [r for r in rows if r.get("profile") == prof]


def attempts_exhausted(path: Path, prof: str) -> bool:
    """True when failed L_dns attempts exist on >= 2 different UTC days (a third is refused; same-day failures count once)."""
    return len({r["utc_date"] for r in _attempts(path, prof) if not r.get("passed")}) >= LDNS_MAX_ATTEMPT_DAYS


def record_attempt(path: Path, prof: str, p95, passed: bool, poll_s) -> None:
    with Path(path).open("a") as f:
        f.write(json.dumps({"profile": prof, "utc_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "utc": datetime.now(timezone.utc).isoformat(),
                            "killed_p95_ms": p95, "poll_s": poll_s, "passed": passed}) + "\n")


def exit_code(results: list[dict]) -> int:
    return 3 if any(r.get("lan_confirmed") is False for r in results) else 0


def run_b2k_block(ab, ctx, prof: str, attempts_file: Path, watch_log: str) -> dict:
    night, pc = ab.night, ab.pc
    bdir = ctx.out / f"b2k_{prof}"
    bdir.mkdir(parents=True, exist_ok=True)
    st = ctx.state
    res = {"block": f"b2k_{prof}", "profile": prof, "status": "done", "reason": None, "lan_confirmed": None, "b2k_data_cells": 0, "groups": {}}
    st.event("block_start", block=res["block"], profile=prof)
    probs = ab.preflight(ctx)
    if attempts_exhausted(attempts_file, prof):
        probs.append("L_dns attempt rule: two failed attempts on two different days already recorded; no third attempt")
    if probs:
        res.update(status="stopped", reason="preflight: " + "; ".join(probs))
        st.event("stop_block", block=res["block"], reason=res["reason"])
        return res
    stop = None
    try:
        a = ctx.ctl.request(prof + "+fast", timeout_s=ctx.request_timeout_s, allow_no_cluster=True)
        poll_s = float(a.poll_s)
        st.event("profile_requested", block=res["block"], request=prof + "+fast", poll_s=poll_s)
        mon = ab.ProfileMonitor(ctx.ctl, bdir / "profile_events.jsonl", grace_s=ctx.monitor_grace_s)
        cdir = bdir / "calib"
        rc, reason = ab.supervised_run(ctx, ab.calib_cmd(ctx.py, ctx.tree, cdir, prof, ctx.profile_wait_s), bdir / "calib.log", ctx.calib_timeout_s, None, mon)
        ctx.system.teardown(ctx.tree, st)
        stop = reason
        ldns = None
        if stop is None:
            try:
                ldns = night.parse_ldns((cdir / f"calib_ldns_{prof}.txt").read_text())
                result = json.loads((cdir / f"calib_{prof}_result.json").read_text())
            except (OSError, ValueError):
                result = None
            st.event("calibration", block=res["block"], returncode=rc, rtt_check_ok=(result or {}).get("rtt_check_ok"), ldns=ldns)
            if not result or not result.get("rtt_check_ok"):
                stop = "calibration failed (RTT check not confirmed or no result)"
        if stop is None:
            killed = (ldns or {}).get("killed", {})
            p95 = killed.get("p95_ms")
            decision, why = night.ldns_decision(p95, poll_s)
            st.event("ldns_decision", block=res["block"], decision=decision, reason=why, killed=killed, alive=(ldns or {}).get("alive"), poll_s=poll_s)
            record_attempt(attempts_file, prof, p95, decision == "run", poll_s)
            if decision != "run":
                res.update(status="skipped", reason=why)
            else:
                for arm in ctx.arms.split(","):
                    for attempt in (1, 2):
                        od = bdir / (f"b2kill_{arm}" if attempt == 1 else f"b2kill_{arm}_retry1")
                        cmd = [ctx.py, str(ctx.tree / ab.RUN_REL), "--block", "b2kill", "--profile", prof, "--tree", str(ctx.tree), "--out", str(od),
                               "--arms", arm, "--seed", str(ctx.seed), "--profile-wait", str(ctx.profile_wait_s), "--l-dns", repr(p95 / 1000.0),
                               "--watch-log", watch_log]
                        st.event("b2k_start", block=res["block"], arm=arm, attempt=attempt, cmd=cmd[1:])
                        rc, reason = ab.supervised_run(ctx, cmd, bdir / f"{od.name}.log", ctx.run_timeout_s, od / "cells.jsonl", mon)
                        ctx.system.teardown(ctx.tree, st)
                        n = ab.data_cells(od / "cells.jsonl")
                        aborted = [r.get("aborted") for r in ab._cells(od / "cells.jsonl") if r.get("aborted")]
                        st.event("b2k_end", block=res["block"], arm=arm, attempt=attempt, returncode=rc, data_cells=n, aborted=aborted, stop=reason)
                        res["b2k_data_cells"] += n
                        if reason:
                            stop = reason
                            break
                        if n == 0 and attempt == 1:
                            st.event("b2k_retry", block=res["block"], arm=arm, cause=f"no data; returncode {rc}, aborted {aborted}")
                            continue
                        res["groups"][arm] = "ok" if (n > 0 and rc == 0 and not aborted) else f"returncode {rc}, data_cells {n}, aborted {aborted}"
                        break
                    if stop:
                        break
                if any(v != "ok" for v in res["groups"].values()) and not stop:
                    res.update(status="done_with_errors", reason="; ".join(f"{k}: {v}" for k, v in res["groups"].items() if v != "ok"))
    except pc.ProfileError as exc:
        stop = f"profile request failed: {exc}"
    except KeyboardInterrupt:
        stop = "interrupted"
    finally:
        if stop:
            res.update(status="stopped", reason=stop)
            st.event("stop_block", block=res["block"], reason=stop)
        try:
            ctx.system.teardown(ctx.tree, st)
            ab.write_data_manifest(bdir)
        except Exception as exc:  # noqa: BLE001
            st.event("block_cleanup_error", block=res["block"], error=repr(exc))
        try:
            ctx.ctl.request("lan", timeout_s=ctx.request_timeout_s, allow_no_cluster=True)
            res["lan_confirmed"] = True
            st.event("lan_confirmed", block=res["block"])
        except pc.ProfileError as exc:
            res["lan_confirmed"] = False
            st.event("lan_not_confirmed", block=res["block"], error=str(exc))
    st.event("block_end", block=res["block"], status=res["status"], reason=res["reason"])
    (bdir / "BLOCK.json").write_text(json.dumps(res, indent=1))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--end-utc", required=True)
    ap.add_argument("--hashes", required=True)
    ap.add_argument("--dir", default=str(Path.home() / "dib_tnsm/m67"))
    ap.add_argument("--profiles", default=",".join(PROFILES))
    ap.add_argument("--attempts-file", default=str(Path.home() / "dib_tnsm/m67/ldns_attempts.jsonl"))
    ap.add_argument("--watch-log", default=str(Path.home() / "dib_tnsm/m67/watch2_stdout.log"))
    a = ap.parse_args(argv)
    ab = load_auto_block(Path(a.tree))
    tree, out = Path(a.tree).expanduser().resolve(), Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / "auto_b2k.pid").write_text(str(os.getpid()))
    expect = {}
    for line in Path(a.hashes).read_text().splitlines():
        if line.strip():
            sha, rel = line.split(None, 1)
            expect[rel.strip()] = sha
    end_ts = datetime.fromisoformat(a.end_utc.replace("Z", "+00:00")).timestamp()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    st = ab.State(out / "state.json")
    ctx = ab.Ctx(tree=tree, out=out, end_ts=end_ts, ctl=ab.pc.ProfileCtl(a.dir), system=ab.System(), state=st, expect=expect, require_smoke=False)
    profiles = a.profiles.split(",")
    (out / "manifest.json").write_text(json.dumps({"profiles": profiles, "seed": ctx.seed, "arms": ctx.arms, "tree": str(tree), "expected_hashes": expect,
        "end_utc": a.end_utc, "python": sys.version.split()[0], "host": platform.node(), "argv": sys.argv, "watch_log": a.watch_log,
        "attempts_file": a.attempts_file, "started_utc": datetime.now(timezone.utc).isoformat(), "audit": "45"}, indent=1))
    results = []
    for p in profiles:
        r = run_b2k_block(ab, ctx, p, Path(a.attempts_file), a.watch_log)
        results.append(r)
        if r["status"] == "stopped" or (p == "lan" and r["status"] != "done"):
            st.event("sequence_stopped", after=p, status=r["status"], reason=r["reason"])
            break
    (out / "REPORT_raw.md").write_text("# Raw report (auto_b2k.py; not an analysis)\n\n" + "\n".join(
        f"- {r['block']}: {r['status']}; reason: {r['reason']}; data cells: {r['b2k_data_cells']}; groups: {r['groups']}; lan confirmed: {r['lan_confirmed']}" for r in results) + "\n")
    st.event("done", results=[(r["block"], r["status"]) for r in results])
    (out / "DONE").write_text(datetime.now(timezone.utc).isoformat())
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
