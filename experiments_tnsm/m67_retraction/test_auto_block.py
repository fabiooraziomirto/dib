"""Tests of auto_block.py (orchestrator of the network blocks, FASE 3) with a FAKE system (containers, disk, PKI, processes), a FAKE profile
controller and FAKE child scripts (tiny python -c programs that write the files run.py / calib_profile.py would write). Nothing real is
touched: no docker, no watcher, no node. Hypotheses (declared before the module was written):
A-1  a block does not start (no request, no child) if ANY of the initial checks fails: a dibtnsm container, a run.py process, < 2 GB free,
     the PKI expiring before end+2 h, a hash mismatch (frozen tree and new files), a dead watcher; the reason is recorded;
A-2  the sequence of a block is exactly: profile request -> calibration (calib_profile.py) -> threshold file written, sha256 recorded in the
     state BEFORE B1 -> B1 (ONE run.py invocation: D,C, FANOUT 1,10, seed 20261014, thresholds, p95) -> teardown -> data manifest with sha256
     (no pcap) -> request `lan`; the default blocks are lan_before, degraded, lan_after, in that order; wan/regional only when named; B2-kill never;
A-3  the thresholds use the mechanical rule of night.py (imported) and the run is given the file and the p95;
A-4  B1 is relaunched ONCE, and only if the first invocation produced no data, with the cause recorded; a group that produced data is not relaunched;
A-5  a block stops, the child is terminated, `lan` is requested and the manifest written, when: the watcher heartbeat dies, the disk falls below
     2 GB, the PKI expires, profile.applied stops matching the expected state, or the RTT check fails on 3 consecutive cells;
A-6  a non-zero exit of run.py that produced data does not stop the queue (next block goes on) and nothing is retried;
A-7  a failed calibration (RTT not confirmed) stops the block before B1; `lan` is still requested;
A-8  a failed final `lan` request is recorded and makes the exit code non-zero;
A-9  --smoke runs B1 with 3 episodes and FANOUT 10 only (same code path);
A-10 the ProfileMonitor records every profile.applied record, ignores partial clusters and flags an 11-of-11 record that does not match;
A-11 the manifest lists sha256 of every data file, excludes *.pcap, and verifies;
A-12 --dry-run prints the plan and the exact commands and touches nothing.
Falsification: any assertion failing."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

import auto_block as ab
import profile_ctl as pc

NAMES = pc.NAMES
HERE_DIR = Path(__file__).resolve().parent
CALIB_OK = r'''
import json, sys, pathlib
a = sys.argv[1:]; out = pathlib.Path(a[a.index("--out") + 1]); prof = a[a.index("--profile") + 1]
out.mkdir(parents=True, exist_ok=True)
(out / f"calib_{prof}_result.json").write_text(json.dumps({"rtt_check_ok": %(rtt)s, "profile": prof, "generator_path_ms": {}}))
(out / f"calib_logs_{prof}.json").write_text(json.dumps({"single": {"p95_ms": 2.0}, "parallel": {"two": {"p95_ms": 2.4}}}))
(out / f"calib_ldns_{prof}.txt").write_text(json.dumps({"alive": {"p95_ms": 0.2}, "killed": {"p95_ms": 3.4}}))
'''
RUN_OK = r'''
import json, sys, pathlib, time
a = sys.argv[1:]; out = pathlib.Path(a[a.index("--out") + 1]); out.mkdir(parents=True, exist_ok=True)
rows = %(rows)s
with (out / "cells.jsonl").open("a") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
(out / "episodes.jsonl").write_text("{}\n")
(out / "capture.pcap").write_bytes(b"pcap")
time.sleep(%(sleep)s)
sys.exit(%(rc)s)
'''
GOOD_ROWS = [{"cell": i, "cell_spec": {"arm": "D"}, "profile_check_ok": True} for i in range(4)]


class FakeSystem:
    def __init__(self):
        self.containers_, self.runpy, self.free, self.pki = [], False, 50e9, time.time() + 10 * 86400
        self.spawned, self.scripts, self.teardowns, self.on_tick = [], {}, 0, None
        self.others = []

    def containers(self): return list(self.containers_)
    def runpy_running(self): return self.runpy
    def other_watchers(self): return list(self.others)
    def free_bytes(self): return self.free
    def pki_not_after(self, pki_dir): return self.pki
    def teardown(self, tree, st): self.teardowns += 1

    def script(self, name, code, **kw):
        self.scripts.setdefault(name, []).append((code, kw))

    def spawn(self, cmd, logfile):
        name = Path(cmd[1]).name
        self.spawned.append(cmd)
        q = self.scripts.get(name)
        code, kw = q.pop(0) if len(q) > 1 else q[0]
        return subprocess.Popen([sys.executable, "-c", code % kw, *cmd[2:]], stdout=open(logfile, "ab"), stderr=subprocess.STDOUT)


class FakeCtl:
    def __init__(self, fail_lan=False):
        self.calls, self.expected_base, self.expected_partition = [], None, None
        self.alive, self.applied, self.fail_lan = True, None, fail_lan
        self.ticks = 0

    def check_alive(self, max_age_s=15.0):
        self.max_ages = getattr(self, "max_ages", []) + [max_age_s]
        self.ticks += 1
        if not self.alive:
            raise pc.WatcherDown("heartbeat dead")
        return 0.1

    def request(self, value, timeout_s=60.0, allow_no_cluster=False, **kw):
        if not self.alive:
            raise pc.WatcherDown("heartbeat dead")
        self.calls.append(value)
        if value == "lan" and self.fail_lan:
            raise pc.ProfileTimeout("no profile.applied for lan")
        kind, site, _ = pc.parse_request(value)
        if kind in pc.BASES:
            self.expected_base, self.expected_partition = kind, None
        return None

    def read_applied(self, max_age_s=None):
        if self.applied is None:
            raise pc.ProfileError("none")
        return self.applied

    def log_tail(self, n=5): return ""


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_ctx(tmp_path, system=None, ctl=None, smoke=False, expect=None, end_in=4 * 3600, tick=0.05, commit_wait=0.0, require_smoke=False):
    tree = tmp_path / "tree"
    (tree / "code/src/dib/registry/distributed").mkdir(parents=True, exist_ok=True)
    (tree / "experiments_tnsm/m67_retraction").mkdir(parents=True, exist_ok=True)
    f = tree / "experiments_tnsm/m67_retraction/netem_watch2.sh"
    f.write_text("echo hi\n")
    ctx = ab.Ctx(tree=tree, out=tmp_path / "out", end_ts=time.time() + end_in, ctl=ctl or FakeCtl(), system=system or FakeSystem(),
                 state=ab.State(tmp_path / "state.json") if hasattr(ab, "State") else None,
                 expect=expect if expect is not None else {}, smoke=smoke, tick_s=tick, commit_wait_s=commit_wait, py=sys.executable,
                 check_service_hash=False, request_timeout_s=5.0, calib_timeout_s=60, run_timeout_s=60)
    ctx.pki_recheck_s = 0.0
    ctx.require_smoke = require_smoke
    ctx.smoke_dir = tmp_path / "smoke"
    ctx.out.mkdir(parents=True, exist_ok=True)
    return ctx


def kinds(ctx): return [e["kind"] for e in ctx.state.d["events"]]


def good_system():
    s = FakeSystem()
    s.script("calib_profile.py", CALIB_OK, rtt="True")
    s.script("run.py", RUN_OK, rows=repr(GOOD_ROWS), sleep=0.0, rc=0)
    return s


# ------------------------------------------------------------------------------------------------------------------ A-1
@pytest.mark.parametrize("what", ["container", "runpy", "disk", "pki", "hash", "watcher", "otherwatcher"])
def test_a1_initial_checks_stop_the_block_before_anything(tmp_path, what):
    s = good_system()
    ctl = FakeCtl()
    expect = {}
    if what == "container": s.containers_ = ["dibtnsm-evidence-1"]
    if what == "runpy": s.runpy = True
    if what == "disk": s.free = 1.9e9
    if what == "pki": s.pki = time.time() + 4 * 3600 + 3600           # expires 1 h after the end, margin is 2 h
    if what == "watcher": ctl.alive = False
    if what == "otherwatcher": s.others = [(2326458, "bash /usr/local/lib/dib-netem/netem_watch.sh --poll 0.5 degraded")]
    ctx = make_ctx(tmp_path, system=s, ctl=ctl)
    if what == "hash": ctx.expect = {"experiments_tnsm/m67_retraction/netem_watch2.sh": "0" * 64}
    r = ab.run_block(ctx, "degraded")
    assert r["status"] == "stopped" and r["reason"].startswith("preflight")
    assert s.spawned == [] and ctl.calls == []                          # no request, no child
    token = {"container": "container", "runpy": "run.py", "disk": "disk", "pki": "pki", "hash": "hash", "watcher": "watcher", "otherwatcher": "another netem watcher"}[what]
    assert "stop_block" in kinds(ctx) and token in r["reason"].lower()


def test_a1_good_preflight_passes(tmp_path):
    ctx = make_ctx(tmp_path, system=good_system())
    assert ab.preflight(ctx) == []
    f = ctx.tree / "experiments_tnsm/m67_retraction/netem_watch2.sh"
    ctx.expect = {"experiments_tnsm/m67_retraction/netem_watch2.sh": sha(f)}
    assert ab.preflight(ctx) == []


# ------------------------------------------------------------------------------------------------------------------ A-2, A-3, A-11
def test_a2_sequence_of_a_block(tmp_path):
    s = good_system()
    ctl = FakeCtl()
    ctx = make_ctx(tmp_path, system=s, ctl=ctl)
    r = ab.run_block(ctx, "degraded")
    assert r["status"] == "done", r
    assert ctl.calls == ["degraded", "lan"]
    names = [Path(c[1]).name for c in s.spawned]
    assert names == ["calib_profile.py"] + ["run.py"] * 4                                 # one run.py invocation PER GROUP
    cal, run = s.spawned[0], s.spawned[1]
    import night
    groups = night.group_order("degraded", ["b1"], ["D", "C"], 20261014)
    got = [(c[c.index("--arms") + 1], int(c[c.index("--fanouts") + 1])) for c in s.spawned[1:]]
    assert got == [(a_, f_) for a_, f_, _ in groups]                                       # registered order
    assert cal[cal.index("--profile") + 1] == "degraded" and "--profile-wait" in cal
    assert run[2:6] == ["--block", "b1", "--profile", "degraded"] and "b2kill" not in " ".join(run)
    for flag, val in [("--seed", "20261014"), ("--profile-wait", "90")]:
        assert run[run.index(flag) + 1] == val
    assert "--episodes" not in run and "--tree" in run
    tf = Path(run[run.index("--plog-thresholds") + 1])
    assert tf.is_file() and float(run[run.index("--plog-p95-ms") + 1]) == 2.4
    k = kinds(ctx)
    assert k.index("threshold_file") < k.index("b1_start") and k.index("calibration") < k.index("threshold_file")      # A-2: hash before any B1 datum
    ev = next(e for e in ctx.state.d["events"] if e["kind"] == "threshold_file")
    assert ev["sha256"] == sha(tf)
    import night
    thr = json.loads(tf.read_text())
    assert thr == night.plog_thresholds("degraded", 2.4)                                                               # A-3: the night's rule
    assert thr["cells"]["D/1"]["threshold_ms"] == pytest.approx(800.0) and thr["cells"]["C/10"]["threshold_ms"] == pytest.approx(120.0)
    assert s.teardowns >= 1


def test_a2_default_block_order_and_names():
    assert ab.DEFAULT_BLOCKS == ["lan_before", "degraded", "lan_after"]
    assert ab.select_blocks(None) == ["lan_before", "degraded", "lan_after"]
    assert ab.select_blocks("degraded,lan_before") == ["lan_before", "degraded"]               # registered order, not the typed one
    assert ab.select_blocks("lan_before,wan,degraded") == ["lan_before", "degraded", "wan"]
    with pytest.raises(ValueError):
        ab.select_blocks("b2kill")
    with pytest.raises(ValueError):
        ab.select_blocks("extreme")
    assert ab.BLOCKS["lan_before"] == ab.BLOCKS["lan_after"] == "lan" and ab.BLOCKS["degraded"] == "degraded"


def test_a2_all_default_blocks_in_order_with_lan_between(tmp_path):
    s = good_system()
    ctl = FakeCtl()
    ctx = make_ctx(tmp_path, system=s, ctl=ctl)
    res = ab.run_all(ctx, ab.DEFAULT_BLOCKS)
    assert [r["status"] for r in res] == ["done"] * 3
    assert ctl.calls == ["lan", "lan", "degraded", "lan", "lan", "lan"]
    assert [Path(c[1]).name for c in s.spawned].count("calib_profile.py") == 1             # no calibration at lan
    for b in ab.DEFAULT_BLOCKS:
        assert (ctx.out / b / "DATA.sha256").is_file()
    assert not any("b2kill" in " ".join(c) for c in s.spawned)
    man = json.loads((ctx.out / "manifest.json").read_text())
    assert man["block_order"] == ["lan_before", "degraded", "lan_after"] and man["seed"] == 20261014


def test_a11_manifest_excludes_pcap_and_verifies(tmp_path):
    s = good_system()
    ctx = make_ctx(tmp_path, system=s)
    ab.run_block(ctx, "lan_before")
    d = ctx.out / "lan_before"
    lines = (d / "DATA.sha256").read_text().splitlines()
    assert lines and not any(".pcap" in l for l in lines) and not any("DATA.sha256" in l for l in lines)
    for l in lines:
        h, rel = l.split("  ", 1)
        assert sha(d / rel) == h
    assert any(l.endswith("cells.jsonl") and "b1_" in l for l in lines)


# ------------------------------------------------------------------------------------------------------------------ A-4, A-6
def test_a4_retry_once_per_group_only_without_data(tmp_path):
    s = good_system()
    # first invocation: no data -> relaunched once (data); the other three groups run once
    s.scripts["run.py"] = [(RUN_OK, dict(rows="[]", sleep=0.0, rc=1)), (RUN_OK, dict(rows=repr(GOOD_ROWS), sleep=0.0, rc=0))]
    ctx = make_ctx(tmp_path, system=s)
    r = ab.run_block(ctx, "lan_before")
    assert [Path(c[1]).name for c in s.spawned].count("run.py") == 5 and r["status"] == "done"
    ev = next(e for e in ctx.state.d["events"] if e["kind"] == "b1_retry")
    assert ev["cause"] and ev["group"]
    # never any data: each group gets one relaunch (2 invocations), a third consecutive group without data stops the block
    s2 = good_system()
    s2.scripts["run.py"] = [(RUN_OK, dict(rows="[]", sleep=0.0, rc=1))]
    ctx2 = make_ctx(tmp_path / "b", system=s2)
    r2 = ab.run_block(ctx2, "lan_before")
    assert [Path(c[1]).name for c in s2.spawned].count("run.py") == 6 and r2["b1_data_cells"] == 0
    assert r2["status"] == "stopped" and "three consecutive" in r2["reason"]


def test_a4_failed_group_does_not_stop_the_queue(tmp_path):
    s = good_system()
    s.scripts["run.py"] = [(RUN_OK, dict(rows="[]", sleep=0.0, rc=1)), (RUN_OK, dict(rows="[]", sleep=0.0, rc=1)),   # group 1 and its relaunch: no data
                           (RUN_OK, dict(rows=repr(GOOD_ROWS), sleep=0.0, rc=0))]                                    # the rest is fine
    ctx = make_ctx(tmp_path, system=s)
    r = ab.run_block(ctx, "lan_before")
    assert [Path(c[1]).name for c in s.spawned].count("run.py") == 5 and r["status"] == "done_with_errors"
    assert sum(v == "ok" for v in r["groups"].values()) == 3 and "no data after one relaunch" in r["reason"]


def test_a4_aborted_group_record_is_not_data(tmp_path):
    p = tmp_path / "cells.jsonl"
    p.write_text(json.dumps({"group": ["D", 1, 5.0], "aborted": "profile check failed"}) + "\n")
    assert ab.data_cells(p) == 0
    p.write_text(p.read_text() + json.dumps({"cell": 1, "cell_spec": {}, "profile_check_ok": True}) + "\n")
    assert ab.data_cells(p) == 1
    assert ab.data_cells(tmp_path / "missing.jsonl") == 0


# ------------------------------------------------------------------------------------------------------------------ A-5
def long_run_system():
    s = FakeSystem()
    s.script("calib_profile.py", CALIB_OK, rtt="True")
    s.script("run.py", RUN_OK, rows=repr(GOOD_ROWS), sleep=30, rc=0)
    return s


@pytest.mark.parametrize("what", ["watcher", "disk", "pki", "mismatch"])
def test_a5_mid_run_stops_terminate_the_child_and_restore_lan(tmp_path, what):
    s = long_run_system()
    ctl = FakeCtl()
    ctx = make_ctx(tmp_path, system=s, ctl=ctl)
    t0 = time.time()
    state = {"n": 0}

    def trigger():
        state["n"] += 1
        if state["n"] == 6:
            if what == "watcher": ctl.alive = False
            if what == "disk": s.free = 1e9
            if what == "pki": s.pki = time.time() - 1
            if what == "mismatch":
                ctl.applied = pc.parse_applied(_applied("degraded", {"dibtnsm-site-2-1": "qdisc noqueue 0: root refcnt 2"}))
    ctx.on_tick = trigger
    ctl.expected_base = None
    r = ab.run_block(ctx, "degraded")
    assert time.time() - t0 < 25                                                       # the child (30 s) was terminated
    token = {"watcher": "watcher", "disk": "disk", "pki": "pki", "mismatch": "profile"}[what]
    assert r["status"] == "stopped" and token in r["reason"].lower(), r
    assert ctl.calls[-1] == "lan" or what == "watcher"                                 # a dead watcher cannot be asked: recorded instead
    if what == "watcher":
        assert "lan_not_confirmed" in kinds(ctx)
    assert (ctx.out / "degraded" / "DATA.sha256").is_file()
    assert "stop_block" in kinds(ctx)


def _applied(base, override=None, n=11):
    nm = NAMES[:n]
    out = ["format: netem_watch2/1", "request: degraded", "trigger: recreate", "applied_utc: x", f"epoch_ms: {int(time.time() * 1000)}",
           f"base: {base}", "partition: none", "poll_s: 0.5", f"containers: {n}"]
    for i, name in enumerate(nm):
        q = (override or {}).get(name, "qdisc netem 8001: root refcnt 2 limit 1000 delay 200ms loss 5%" if base == "degraded" else "qdisc noqueue 0: root")
        out += [f"== {name} pid {3000 + i}", q]
    return "\n".join(out) + "\n"


def test_a5_three_consecutive_rtt_failures(tmp_path):
    p = tmp_path / "cells.jsonl"
    ok = {"cell": 1, "cell_spec": {}, "profile_check_ok": True}
    bad = {"cell": 2, "cell_spec": {}, "profile_check_ok": False}
    p.write_text("\n".join(json.dumps(x) for x in [ok, bad, bad, ok, bad, bad]) + "\n")
    assert ab.rtt_streak(p) == 2
    p.write_text("\n".join(json.dumps(x) for x in [ok, bad, bad, bad]) + "\n")
    assert ab.rtt_streak(p) == 3
    p.write_text(p.read_text() + json.dumps({"group": ["D", 1, 5.0], "aborted": "profile check failed: x"}) + "\n")
    assert ab.rtt_streak(p) == 4
    assert ab.rtt_streak(tmp_path / "nope") == 0


def test_a5_rtt_streak_stops_the_run(tmp_path):
    s = FakeSystem()
    s.script("calib_profile.py", CALIB_OK, rtt="True")
    bad = [{"cell": i, "cell_spec": {}, "profile_check_ok": False} for i in range(3)]
    s.script("run.py", RUN_OK, rows=repr(bad), sleep=30, rc=0)
    ctl = FakeCtl()
    ctx = make_ctx(tmp_path, system=s, ctl=ctl)
    t0 = time.time()
    r = ab.run_block(ctx, "degraded")
    assert time.time() - t0 < 25 and r["status"] == "stopped" and "rtt" in r["reason"] and ctl.calls[-1] == "lan"


# ------------------------------------------------------------------------------------------------------------------ A-7, A-8, A-9
def test_a7_failed_calibration_stops_before_b1(tmp_path):
    s = FakeSystem()
    s.script("calib_profile.py", CALIB_OK, rtt="False")
    s.script("run.py", RUN_OK, rows=repr(GOOD_ROWS), sleep=0, rc=0)
    ctl = FakeCtl()
    ctx = make_ctx(tmp_path, system=s, ctl=ctl)
    r = ab.run_block(ctx, "degraded")
    assert r["status"] == "stopped" and "calibration" in r["reason"]
    assert not any(Path(c[1]).name == "run.py" for c in s.spawned) and ctl.calls == ["degraded", "lan"]
    assert (ctx.out / "degraded" / "DATA.sha256").is_file()


def test_a8_failed_lan_request_is_recorded_and_nonzero(tmp_path):
    ctl = FakeCtl(fail_lan=True)
    ctx = make_ctx(tmp_path, system=good_system(), ctl=ctl)
    res = ab.run_all(ctx, ["degraded"])
    assert "lan_not_confirmed" in kinds(ctx) and res[0]["lan_confirmed"] is False
    assert ab.exit_code(res) != 0
    ok = ab.run_all(make_ctx(tmp_path / "b", system=good_system()), ["degraded"])
    assert ab.exit_code(ok) == 0


def test_a9_smoke_uses_3_episodes_and_fanout_10(tmp_path):
    s = good_system()
    ctx = make_ctx(tmp_path, system=s, smoke=True)
    ab.run_block(ctx, "degraded")
    runs = [c for c in s.spawned if Path(c[1]).name == "run.py"]
    assert len(runs) == 2                                                                  # FANOUT 10 only: D and C
    for run in runs:
        assert run[run.index("--episodes") + 1] == "3" and run[run.index("--fanouts") + 1] == "10"
    assert "smoke" in str(ctx.out / "degraded") or (ctx.out / "degraded").exists()


# ------------------------------------------------------------------------------------------------------------------ A-10
def test_a10_profile_monitor(tmp_path):
    ctl = FakeCtl()
    ctl.expected_base = "degraded"
    mon = ab.ProfileMonitor(ctl, tmp_path / "profile_events.jsonl")
    assert mon.poll() is None                                          # nothing yet
    ctl.applied = pc.parse_applied(_applied("degraded", n=6))
    assert mon.poll() is None                                          # partial cluster: ignored
    ctl.applied = pc.parse_applied(_applied("degraded"))
    ctl.applied.epoch_ms += 5
    assert mon.poll() is None
    assert mon.poll() is None                                          # same record: not recorded twice
    ctl.applied = pc.parse_applied(_applied("degraded", {"dibtnsm-site-5-1": "qdisc noqueue 0: root"}))
    ctl.applied.epoch_ms += 10
    p = mon.poll()
    assert p and "dibtnsm-site-5-1" in p
    rows = [json.loads(l) for l in (tmp_path / "profile_events.jsonl").read_text().splitlines()]
    assert [r["coherent"] for r in rows] == [None, True, False] and [r["containers"] for r in rows] == [6, 11, 11]


# ------------------------------------------------------------------------------------------------------------------ A-12, report
def test_a12_dry_run_prints_plan_and_touches_nothing(tmp_path, capsys):
    out = tmp_path / "o"
    rc = ab.main(["--tree", str(tmp_path / "t"), "--out", str(out), "--end-utc", "2026-10-14T06:00:00Z", "--dir", str(tmp_path / "d"), "--dry-run"])
    txt = capsys.readouterr().out
    assert rc == 0 and not out.exists()
    for needle in ["lan_before", "degraded", "lan_after", "calib_profile.py", "--block b1", "--seed 20261014", "--fanouts 1", "--fanouts 10", "request lan", "no calibration, no thresholds at lan"]:
        assert needle in txt, needle
    assert "b2kill" not in txt.replace("never", "")


def test_report_is_written(tmp_path):
    ctx = make_ctx(tmp_path, system=good_system())
    res = ab.run_all(ctx, ["degraded"])
    rep = (ctx.out / "REPORT_raw.md").read_text()
    assert "degraded" in rep and "done" in rep and "threshold" in rep.lower()


# ------------------------------------------------------------------------------------------------------------------ lan: no calibration, smoke gate
def test_lan_block_skips_calibration_and_thresholds(tmp_path):
    s = good_system()
    ctx = make_ctx(tmp_path, system=s)
    ab.run_block(ctx, "lan_after")
    assert "calibration_skipped" in kinds(ctx) and "threshold_file" not in kinds(ctx)
    for c in s.spawned:
        assert Path(c[1]).name == "run.py" and "--plog-thresholds" not in c and "--plog-p95-ms" not in c
    assert not (ctx.out / "lan_after" / "plog_thresholds_lan.json").exists()


def test_a13_smoke_gate(tmp_path):
    s = good_system()
    ctx = make_ctx(tmp_path, system=s, require_smoke=True)
    ctx.expect = {"experiments_tnsm/m67_retraction/netem_watch2.sh": sha(ctx.tree / "experiments_tnsm/m67_retraction/netem_watch2.sh")}
    r = ab.run_block(ctx, "degraded")                                  # no smoke yet: refused before anything
    assert r["status"] == "stopped" and "smoke" in r["reason"] and s.spawned == [] and ctx.ctl.calls == []
    ctx.smoke = True                                                    # the smoke cell itself is allowed and leaves the marker
    r = ab.run_block(ctx, "degraded")
    assert r["status"] == "done" and ab.smoke_ok(ctx, "degraded") and not ab.smoke_ok(ctx, "lan")
    ctx.smoke = False
    assert ab.run_block(ctx, "degraded")["status"] == "done"            # now the real block may start
    ctx.expect = {"experiments_tnsm/m67_retraction/netem_watch2.sh": "1" * 64}   # other hashes: the marker no longer counts
    assert not ab.smoke_ok(ctx, "degraded")


def test_a13_failed_smoke_leaves_no_marker(tmp_path):
    s = good_system()
    s.scripts["run.py"] = [(RUN_OK, dict(rows="[]", sleep=0.0, rc=1))]
    ctx = make_ctx(tmp_path, system=s, smoke=True)
    ab.run_block(ctx, "lan_before")
    assert not ab.smoke_ok(ctx, "lan")


# ------------------------------------------------------------------------------------------------------------------ A-14 (smoke of 2026-10-11)
def test_a14_children_do_not_inherit_ignored_sigint(tmp_path):
    """A process started with `&` from a non-interactive shell (launch_auto_block.sh: `setsid nohup ... &`) has SIGINT set to SIG_IGN, the child
    inherits it, Python then installs NO KeyboardInterrupt handler and terminate()'s SIGINT does nothing (first smoke: run.py went on for ~115 s
    after the stop rule fired). The real System.spawn must give the child the default SIGINT disposition even when the orchestrator ignores it."""
    import signal
    old = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        log = tmp_path / "sig.log"
        p = ab.System().spawn([sys.executable, "-c", "import signal; print(signal.getsignal(signal.SIGINT))"], log)
        p.wait(timeout=30)
    finally:
        signal.signal(signal.SIGINT, old)
    assert "default_int_handler" in log.read_text(), log.read_text()


def test_a1_preflight_demands_a_fresh_heartbeat(tmp_path):
    ctl = FakeCtl()
    ctx = make_ctx(tmp_path, system=good_system(), ctl=ctl)
    assert ab.preflight(ctx) == [] and ctl.max_ages[-1] == ab.PREFLIGHT_HEARTBEAT_MAX_AGE_S == 10.0


def test_a1_other_watcher_detection_on_the_real_system(tmp_path):
    """System.other_watchers sees a v1 watcher (netem_watch.sh) and any netem_watch*.sh but NOT netem_watch2.sh and its sudo/timeout wrappers."""
    import shutil
    d = tmp_path / "bin"
    d.mkdir()
    for name in ("netem_watch.sh", "netem_watch2.sh", "netem_watch3.sh"):
        (d / name).write_text("#!/usr/bin/env bash\nsleep 30\n")
    procs = [subprocess.Popen(["bash", str(d / n)]) for n in ("netem_watch.sh", "netem_watch2.sh")]
    procs.append(subprocess.Popen(["timeout", "30", "bash", str(d / "netem_watch2.sh")]))
    try:
        time.sleep(0.5)
        found = ab.System().other_watchers()
        assert any("netem_watch.sh" in c for _, c in found) and not any("netem_watch2.sh" in c for _, c in found)
        procs.append(subprocess.Popen(["bash", str(d / "netem_watch3.sh")]))
        time.sleep(0.5)
        assert any("netem_watch3.sh" in c for _, c in ab.System().other_watchers())
    finally:
        for p in procs:
            p.kill()
            p.wait()
    assert ab.System().other_watchers() == []


def test_a14_background_child_dies_after_terminate(tmp_path):
    """End to end of the smoke failure: a non-interactive shell starts the 'orchestrator' in BACKGROUND (`setsid nohup ... &`, so SIGINT is
    ignored there), which spawns a child through System.spawn and calls terminate(). The child must die from the SIGINT well within the grace
    period (here 20 s), not be killed at its end."""
    helper = tmp_path / "helper.py"
    helper.write_text(f"""
import sys, time, subprocess, json
sys.path.insert(0, {str(HERE_DIR)!r})
import auto_block as ab
log = {str(tmp_path / "child.log")!r}
p = ab.System().spawn([sys.executable, "-c", "import time\\ntry:\\n    time.sleep(120)\\nexcept KeyboardInterrupt:\\n    print('KI')\\n    raise"], log)
time.sleep(1.0)
t0 = time.time()
ab.terminate(p, grace_s=20)
print(json.dumps({{"elapsed": time.time() - t0, "rc": p.returncode}}), flush=True)
""")
    out = tmp_path / "out.json"
    sh = tmp_path / "launch.sh"
    sh.write_text(f"#!/usr/bin/env bash\nsetsid nohup {sys.executable} {helper} > {out} 2>&1 < /dev/null &\nwait\n")
    subprocess.run(["bash", str(sh)], timeout=60)
    r = json.loads(out.read_text().strip().splitlines()[-1])
    assert r["elapsed"] < 10 and r["rc"] not in (None, -9), r                       # died from SIGINT, not from the SIGKILL after the grace
    assert "KI" in (tmp_path / "child.log").read_text()
