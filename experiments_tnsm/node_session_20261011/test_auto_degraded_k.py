"""Tests of auto_degraded_k.py (docs/audit/62: degraded measurements of the opt-in persistent connections, started by itself when the watcher is alive again).
Fake system / controller as test_auto_b2k.py; nothing real is touched. Hypotheses (before the module; falsification = any assertion failing):
 Q-1  the step order is b1_on, b1_off, b2k_on; arms D then C inside each step;
 Q-2  DIB_M67_KEEPALIVE seen by each child run.py is '1' for b1_on and b2k_on and '0' for b1_off; calibration children see '0'; the variable is restored afterwards;
 Q-3  one calibration at degraded, thresholds file written (sha256 in the state) BEFORE the first b1 child; b1 children get --fanouts 10 and the thresholds; b2kill children get --l-dns;
 Q-4  the L_dns rule of audit 45 applies (p95 > 50 ms or poll_s > 0.1 -> no b2k_on; b1 steps still run);
 Q-5  wait_for_watcher returns False at the deadline without ever starting, True as soon as the heartbeat is alive;
 Q-6  no step starts after the deadline; a preflight problem stops everything; the final request is plain `lan`.
"""
import json
import sys
import time
from pathlib import Path

import pytest

M67 = Path(__file__).resolve().parent.parent / "m67_retraction"
sys.path.insert(0, str(M67))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import auto_block as ab  # noqa: E402
import profile_ctl as pc  # noqa: E402
import auto_degraded_k as dk  # noqa: E402
from test_auto_block import FakeSystem, CALIB_OK  # noqa: E402
from test_auto_b2k import FakeCtl  # noqa: E402

RUN_ENV = r'''
import json, sys, pathlib, os
a = sys.argv[1:]; out = pathlib.Path(a[a.index("--out") + 1]); out.mkdir(parents=True, exist_ok=True)
(out / "cells.jsonl").write_text(json.dumps({"cell": 1, "cell_spec": {"arm": "D"}, "profile_check_ok": True}) + "\n")
(out / "env.txt").write_text(os.environ.get("DIB_M67_KEEPALIVE", "UNSET") + "\n" + " ".join(a))
'''
CALIB_ENV = CALIB_OK + r'''
import os
(out / "calib_env.txt").write_text(os.environ.get("DIB_M67_KEEPALIVE", "UNSET"))
'''


def make_ctx(tmp_path, poll_s=0.1, ldns_ms=3.4):
    sysm = FakeSystem()
    sysm.script("calib_profile.py", CALIB_ENV.replace('"p95_ms": 3.4', f'"p95_ms": {ldns_ms}'), rtt="True")
    sysm.script("run.py", RUN_ENV)
    st = ab.State(tmp_path / "state.json")
    tree = tmp_path / "tree"
    (tree / "experiments_tnsm/m67_retraction").mkdir(parents=True)
    for rel in ("run.py", "calib_profile.py"):
        (tree / "experiments_tnsm/m67_retraction" / rel).write_text("")
    ctx = ab.Ctx(tree=tree, out=tmp_path / "out", end_ts=time.time() + 6 * 3600, ctl=FakeCtl(poll_s), system=sysm, state=st, expect={},
                 check_service_hash=False, require_smoke=False, tick_s=0.05, commit_wait_s=0.0, py=sys.executable)
    ctx.out.mkdir()
    return ctx


def run_cmds(ctx):
    return [c for c in ctx.system.spawned if Path(c[1]).name == "run.py"]


def test_q1_q2_q3_order_env_and_args(tmp_path, monkeypatch):
    monkeypatch.delenv("DIB_M67_KEEPALIVE", raising=False)
    ctx = make_ctx(tmp_path)
    res = dk.run_sequence(ab, ctx, deadline=time.time() + 3600, watch_log="w.log")
    cmds = run_cmds(ctx)
    outs = [Path(c[c.index("--out") + 1]) for c in cmds]
    assert [o.parent.name + "/" + o.name for o in outs] == ["b1_on/D", "b1_on/C", "b1_off/D", "b1_off/C", "b2k_on/D", "b2k_on/C"]
    envs = [(o / "env.txt").read_text().split("\n")[0] for o in outs]
    assert envs == ["1", "1", "0", "0", "1", "1"]
    assert (ctx.out / "calib" / "calib_env.txt").read_text() == "0"
    import os
    assert "DIB_M67_KEEPALIVE" not in os.environ
    for c in cmds[:4]:
        assert c[c.index("--block") + 1] == "b1" and c[c.index("--fanouts") + 1] == "10" and "--plog-thresholds" in c and "--plog-p95-ms" in c
    for c in cmds[4:]:
        assert c[c.index("--block") + 1] == "b2kill" and float(c[c.index("--l-dns") + 1]) == pytest.approx(0.0034)
    kinds = [e["kind"] for e in ctx.state.d["events"]]
    assert kinds.index("threshold_file") < kinds.index("step_start")
    assert ctx.ctl.requests[0] == "degraded+fast" and ctx.ctl.requests[-1] == "lan"
    assert res["status"] == "done" and res["lan_confirmed"] is True


def test_q4_ldns_rule_skips_b2k_only(tmp_path):
    ctx = make_ctx(tmp_path, ldns_ms=80.0)
    res = dk.run_sequence(ab, ctx, deadline=time.time() + 3600, watch_log="w.log")
    names = {Path(c[c.index("--out") + 1]).parent.name for c in run_cmds(ctx)}
    assert names == {"b1_on", "b1_off"} and res["b2k_skipped"]
    ctx2 = make_ctx(tmp_path / "x", poll_s=0.5)
    (tmp_path / "x").mkdir(exist_ok=True)


def test_q5_wait_for_watcher():
    class Dead:
        def check_alive(self, *a, **k):
            raise pc.WatcherDown("no heartbeat")

    class Alive:
        def check_alive(self, *a, **k):
            return None
    t0 = time.time()
    assert dk.wait_for_watcher(Dead(), deadline=time.time() + 0.3, poll_s=0.05, pc=pc) is False
    assert 0.25 <= time.time() - t0 < 2
    assert dk.wait_for_watcher(Alive(), deadline=time.time() + 5, poll_s=0.05, pc=pc) is True


def test_q6_deadline_and_preflight(tmp_path):
    ctx = make_ctx(tmp_path)
    res = dk.run_sequence(ab, ctx, deadline=time.time() - 1, watch_log="w.log")
    assert res["status"] == "stopped" and run_cmds(ctx) == []
    ctx2 = make_ctx(tmp_path / "p")
    (tmp_path / "p").mkdir(exist_ok=True)
    ctx2.system.containers_ = ["dibtnsm-x"]
    res2 = dk.run_sequence(ab, ctx2, deadline=time.time() + 3600, watch_log="w.log")
    assert res2["status"] == "stopped" and "preflight" in res2["reason"] and ctx2.ctl.requests == []


def test_q7_deadline_between_arms(tmp_path):
    """The deadline passes while the first child runs: no further child starts (guards the per-arm deadline check)."""
    ctx2 = make_ctx(tmp_path / "d")
    (tmp_path / "d").mkdir(exist_ok=True)
    ctx2.system.scripts["run.py"] = [("import time\n" + RUN_ENV + "\ntime.sleep(1.5)\n", {})]
    t_end = time.time() + 2.5
    res2 = dk.run_sequence(ab, ctx2, deadline=t_end, watch_log="w.log")
    assert res2["status"] == "stopped" and "deadline" in res2["reason"]
    assert 1 <= len(run_cmds(ctx2)) < 6
