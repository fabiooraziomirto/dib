"""Offline tests of the pure decision logic of night.py (unattended sequence on the node, user plan of 2026-10-11).
Hypotheses (declared first): N-a the L_dns rule is applied mechanically (<= 50 ms and watcher poll <= 0.1 s -> run B2-kill;
otherwise skip with the reason, including the case of a 0.5 s watcher); N-b the P-log threshold is 10% of the predicted
direct withdrawal of the cell (prediction (a)), per arm and FANOUT, with accepted = calibrated p95 below it; N-c the group
order is the pre-registered one (seed 20261014, same function as run.py); N-d no new group starts after the end time; M1/M2
only with >= 3 h left; N-e three consecutive profile failures stop the block; N-f hashes: a mismatch is fatal."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import night as n  # noqa: E402


def test_na_ldns_rule():
    assert n.ldns_decision(12.0, 0.1)[0] == "run"
    assert n.ldns_decision(50.0, 0.1)[0] == "run"
    d, why = n.ldns_decision(12.0, 0.5)
    assert d == "skip" and "0.5" in why and "poll" in why
    d, why = n.ldns_decision(50.1, 0.1)
    assert d == "skip" and "user decision" in why
    d, why = n.ldns_decision(900.0, 0.1)
    assert d == "skip" and "user decision" in why
    assert n.ldns_decision(None, 0.1)[0] == "skip"


def test_nb_thresholds_per_arm_and_fanout():
    t = n.plog_thresholds("wan", 2.4)
    assert abs(t["cells"]["D/10"]["predicted_direct_median_ms"] - 320.0) < 1e-6          # n_RTT 2 x R 160 ms
    assert abs(t["cells"]["D/1"]["predicted_direct_median_ms"] - 3200.0) < 1e-6          # 10 sequential deliveries
    assert abs(t["cells"]["C/10"]["predicted_direct_median_ms"] - 480.0) < 1e-6
    assert abs(t["cells"]["D/10"]["threshold_ms"] - 32.0) < 1e-6
    assert t["cells"]["D/10"]["accepted"] is True and t["calibrated_p95_ms"] == 2.4
    assert n.plog_thresholds("wan", 40.0)["cells"]["D/10"]["accepted"] is False        # p95 above 10%
    assert t["rule"].startswith("p95 of the log latency < 10%")


def test_nc_group_order_is_the_registered_one():
    import random
    import run
    cells = run.plan("wan", ["b1"], ["D", "C"], [1, 10], None)
    rng = random.Random(20261014)
    rng.shuffle(cells)
    expect = [k for k, _ in run.group_cells(cells, rng)]
    assert n.group_order("wan", ["b1"], ["D", "C"], 20261014) == expect and len(expect) == 4


def test_nd_time_rules():
    end = 1000.0
    assert n.can_start(end, 999.0) and not n.can_start(end, 1000.0) and not n.can_start(end, 1500.0)
    assert n.can_start_m12(end, 1000.0 - 3 * 3600 - 1) is True
    assert n.can_start_m12(end, 1000.0 - 3 * 3600 + 1) is False


def test_ne_consecutive_failures_stop_the_block():
    c = n.FailureCounter(3)
    assert [c.record(False), c.record(False), c.record(True), c.record(False), c.record(False), c.record(False)] == [False, False, False, False, False, True]


def test_nf_hash_mismatch_is_fatal(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    import hashlib
    good = hashlib.sha256(b"x").hexdigest()
    assert n.check_hashes(tmp_path, {"a.txt": good}) == []
    assert n.check_hashes(tmp_path, {"a.txt": "0" * 64}) == ["a.txt"]
    assert n.check_hashes(tmp_path, {"missing.txt": good}) == ["missing.txt"]


def test_ldns_parse():
    text = '{"label": "wan", "alive": {"n": 50, "p50_ms": 2.0, "p95_ms": 3.0, "max_ms": 4.0, "outcomes": ["True"]},\n "killed": {"n": 50, "p50_ms": 2.6, "p95_ms": 3.1, "max_ms": 5.0, "outcomes": ["gaierror(-2, \'Name or service not known\')"]}}\n'
    r = n.parse_ldns(text)
    assert r["killed"]["p95_ms"] == 3.1 and r["alive"]["n"] == 50
    assert n.parse_ldns("garbage") is None


def _fake_env(monkeypatch, tmp_path, killed_p95, end_offset_s, log_p95=2.4, fail_b1=False):
    """Run night.main() end to end with a FAKE subprocess layer: calib_profile/run.py/M1/M2 calls only write the files the real
    ones would write; nothing touches docker, the node or netem."""
    import time as _t
    calls = []

    def fake_run_logged(cmd, logfile, timeout):
        script = Path(cmd[1]).name
        calls.append((f"{Path(cmd[1]).parent.name}/{script}", cmd[2:]))
        if script == "calib_profile.py":
            d = Path(cmd[cmd.index("--out") + 1])
            d.mkdir(parents=True, exist_ok=True)
            (d / "calib_wan_result.json").write_text(json.dumps({"rtt_check_ok": True, "generator_path_ms": {"reused_ms": 81, "fresh_ms": 163, "reused_ok": True, "fresh_ok": True}}))
            (d / "calib_ldns_wan.txt").write_text(json.dumps({"label": "wan", "alive": {"p95_ms": 3.0}, "killed": {"p50_ms": 2.0, "p95_ms": killed_p95}}))
            (d / "calib_logs_wan.json").write_text(json.dumps({"single": {"p95_ms": log_p95}, "parallel": {"a": {"p95_ms": log_p95}, "b": {"p95_ms": 1.0}}}))
            return 0
        if script == "run.py" and "--block" in cmd:
            d = Path(cmd[cmd.index("--out") + 1])
            d.mkdir(parents=True, exist_ok=True)
            (d / "cells.jsonl").write_text(json.dumps({"aborted": "profile check failed"} if fail_b1 else {"cell": 1}) + "\n")
            return 1 if fail_b1 else 0
        d = Path(cmd[cmd.index("--out") + 1])
        d.mkdir(parents=True, exist_ok=True)
        (d / "cells.jsonl").write_text("{}\n{}\n")
        return 0

    monkeypatch.setattr(n, "run_logged", fake_run_logged)
    monkeypatch.setattr(n, "project_containers", lambda: [])
    monkeypatch.setattr(n, "teardown", lambda tree, st: None)
    monkeypatch.setattr(n, "free_ok", lambda: True)
    tree = tmp_path / "tree-abc1234"
    (tree / "code/src/dib/registry/distributed").mkdir(parents=True)
    svc = tree / "code/src/dib/registry/distributed/service.py"
    svc.write_text("x")
    monkeypatch.setattr(n, "SERVICE_SHA", __import__("hashlib").sha256(b"x").hexdigest())
    end = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(_t.time() + end_offset_s))
    return calls, tree, end


def test_ng_end_to_end_with_fake_subprocesses(monkeypatch, tmp_path):
    calls, tree, end = _fake_env(monkeypatch, tmp_path, killed_p95=12.0, end_offset_s=5 * 3600)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["night.py", "--tree", str(tree), "--out", str(out), "--end-utc", end, "--watcher-poll", "0.5", "--commit-wait-min", "0"])
    assert n.main() == 0
    names = [c[0] for c in calls]
    assert names[0] == "m67_retraction/calib_profile.py" and names.count("m67_retraction/run.py") == 4          # B1 only: the 0.5 s watcher excludes B2-kill
    ev = json.loads((out / "state.json").read_text())["events"]
    kinds = [e["kind"] for e in ev]
    assert kinds.index("threshold_file") < kinds.index("group_start")               # the file is written BEFORE B1
    dec = next(e for e in ev if e["kind"] == "ldns_decision")
    assert dec["decision"] == "skip" and "0.5" in dec["reason"]
    assert [e["group"] for e in ev if e["kind"] == "group_start"] == ["b1_C_f10", "b1_D_f1", "b1_C_f1", "b1_D_f10"]   # registered order
    assert (out / "DONE").exists() and (out / "plog_thresholds_wan.json").exists()
    assert "m1_start" in kinds and "m2_start" in kinds                               # 5 h left >= 3 h
    thr = json.loads((out / "plog_thresholds_wan.json").read_text())
    assert thr["calibrated_p95_ms"] == 2.4


def test_nh_b2kill_runs_only_when_rule_and_watcher_allow(monkeypatch, tmp_path):
    calls, tree, end = _fake_env(monkeypatch, tmp_path, killed_p95=12.0, end_offset_s=1 * 3600)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["night.py", "--tree", str(tree), "--out", str(out), "--end-utc", end, "--watcher-poll", "0.1", "--commit-wait-min", "0", "--no-m12"])
    assert n.main() == 0
    b2 = [c for c in calls if c[0] == "m67_retraction/run.py" and "b2kill" in c[1]]
    assert len(b2) == 2 and all("--watch-log" in c[1] for c in b2)                    # one invocation per arm
    ev = json.loads((out / "state.json").read_text())["events"]
    assert not any(e["kind"] == "m1_start" for e in ev)
    # slow L_dns: not run, value reported
    calls, tree, end = _fake_env(monkeypatch, tmp_path / "s", killed_p95=1005.0, end_offset_s=3600)
    out2 = tmp_path / "out2"
    monkeypatch.setattr(sys, "argv", ["night.py", "--tree", str(tree), "--out", str(out2), "--end-utc", end, "--watcher-poll", "0.1", "--commit-wait-min", "0", "--no-m12"])
    n.main()
    assert not [c for c in calls if c[0] == "m67_retraction/run.py" and "b2kill" in c[1]]
    assert next(e for e in json.loads((out2 / "state.json").read_text())["events"] if e["kind"] == "ldns_decision")["killed"]["p95_ms"] == 1005.0


def test_ni_failures_stop_block_and_end_time_blocks_new_groups(monkeypatch, tmp_path):
    calls, tree, end = _fake_env(monkeypatch, tmp_path, killed_p95=12.0, end_offset_s=1 * 3600, fail_b1=True)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["night.py", "--tree", str(tree), "--out", str(out), "--end-utc", end, "--watcher-poll", "0.5", "--commit-wait-min", "0", "--no-m12"])
    n.main()
    assert [c[0] for c in calls].count("m67_retraction/run.py") == 3                                  # three consecutive failures stop the block
    calls, tree, end = _fake_env(monkeypatch, tmp_path / "e", killed_p95=12.0, end_offset_s=-10)
    out2 = tmp_path / "out2"
    monkeypatch.setattr(sys, "argv", ["night.py", "--tree", str(tree), "--out", str(out2), "--end-utc", end, "--watcher-poll", "0.5", "--commit-wait-min", "0"])
    n.main()
    kinds = [e["kind"] for e in json.loads((out2 / "state.json").read_text())["events"]]
    assert "group_start" not in kinds and kinds.count("skip_group_after_end") == 4 and "m1_start" not in kinds


def test_nj_hash_mismatch_aborts_before_anything(monkeypatch, tmp_path):
    calls, tree, end = _fake_env(monkeypatch, tmp_path, killed_p95=12.0, end_offset_s=3600)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["night.py", "--tree", str(tree), "--out", str(out), "--end-utc", end, "--watcher-poll", "0.5",
                                       "--expect", "code/src/dib/registry/distributed/service.py=" + "0" * 64])
    assert n.main() == 2 and calls == []
