"""Tests of auto_b2k.py (B2-kill orchestrator, audit 45) with a FAKE system and FAKE controller (as test_auto_block.py); nothing real is touched.
Hypotheses (declared before the module was written; falsification = any assertion failing):
K-1  the profile order is lan, degraded, wan; a block does not start (no request, no child) if auto_block.preflight reports a problem;
K-2  each block requests `<profile>+fast`, runs calib_profile.py at that profile (also at lan), reads the killed-site L_dns p95 from calib_ldns_<p>.txt
     and applies night.ldns_decision with the poll_s of the profile.applied it got: run only if p95 <= 50 ms AND poll_s <= 0.1;
K-3  if the decision is skip, run.py is never called, the reason is in the state, `lan` is requested at the end;
K-4  B2-kill is ONE run.py --block b2kill invocation per arm (D then C) with --l-dns = p95/1000 and --watch-log; a group that produced data is not relaunched;
     one without data is relaunched once;
K-5  the L_dns attempt rule: two earlier failed attempts (p95 > 50 ms) on two different UTC days refuse a third; a failed attempt is recorded;
K-6  the final request is plain `lan` (no +fast) and is checked; a failed one gives a non-zero exit code.
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
import auto_b2k as bk  # noqa: E402
from test_auto_block import FakeSystem, CALIB_OK, RUN_OK  # noqa: E402

GOOD = [{"cell": i, "cell_spec": {"arm": "D"}, "profile_check_ok": True} for i in range(3)]


class FakeCtl:
    def __init__(self, poll_s=0.1):
        self.requests, self.poll_s, self.expected_base, self.expected_partition = [], poll_s, None, None
        self.fail_lan = False
        self.names = pc.NAMES

    def check_alive(self, *_a, **_k): pass
    def read_applied(self): return None

    def request(self, value, timeout_s=60, allow_no_cluster=False, **_k):
        if value == "lan" and self.fail_lan:
            raise pc.ProfileError("lan not confirmed")
        self.requests.append(value)
        self.expected_base = value.split("+")[0]
        return pc.Applied(request=value, trigger="request", applied_utc="x", epoch_ms=int(time.time() * 1000), base=self.expected_base,
                          partition=None, poll_s=self.poll_s if value.endswith("+fast") else 0.5, containers=0)


def make_ctx(tmp_path, poll_s=0.1, ldns_ms=3.4, run_rows=GOOD, run_rc=0):
    sysm = FakeSystem()
    sysm.script("calib_profile.py", CALIB_OK.replace('"p95_ms": 3.4', f'"p95_ms": {ldns_ms}'), rtt="True")
    sysm.script("run.py", RUN_OK, rows=json.dumps(run_rows), sleep=0, rc=run_rc)
    st = ab.State(tmp_path / "state.json")
    tree = tmp_path / "tree"
    (tree / "experiments_tnsm/m67_retraction").mkdir(parents=True)
    for rel in ("run.py", "calib_profile.py"):
        (tree / "experiments_tnsm/m67_retraction" / rel).write_text("")
    ctx = ab.Ctx(tree=tree, out=tmp_path / "out", end_ts=time.time() + 6 * 3600, ctl=FakeCtl(poll_s), system=sysm, state=st, expect={},
                 check_service_hash=False, require_smoke=False, tick_s=0.05, commit_wait_s=0.0, py=sys.executable)
    ctx.out.mkdir()
    return ctx


def kinds(ctx):
    return [e["kind"] for e in ctx.state.d["events"]]


def test_profile_order():
    assert bk.PROFILES == ["lan", "degraded", "wan"]


def test_preflight_problem_blocks_everything(tmp_path):
    ctx = make_ctx(tmp_path)
    ctx.system.containers_ = ["dibtnsm-x"]
    r = bk.run_b2k_block(ab, ctx, "lan", attempts_file=tmp_path / "att.jsonl", watch_log="w.log")
    assert r["status"] == "stopped" and "preflight" in r["reason"]
    assert ctx.ctl.requests == [] and ctx.system.spawned == []


def test_decision_run_requests_fast_and_runs_both_arms(tmp_path):
    ctx = make_ctx(tmp_path)
    r = bk.run_b2k_block(ab, ctx, "degraded", attempts_file=tmp_path / "att.jsonl", watch_log="w.log")
    assert ctx.ctl.requests[0] == "degraded+fast" and ctx.ctl.requests[-1] == "lan"
    runs = [c for c in ctx.system.spawned if Path(c[1]).name == "run.py"]
    assert [c[c.index("--arms") + 1] for c in runs] == ["D", "C"]
    for c in runs:
        assert c[c.index("--block") + 1] == "b2kill" and c[c.index("--profile") + 1] == "degraded"
        assert float(c[c.index("--l-dns") + 1]) == pytest.approx(0.0034) and c[c.index("--watch-log") + 1] == "w.log"
    assert r["status"] == "done" and r["lan_confirmed"] is True
    assert any(c[1].endswith("calib_profile.py") for c in ctx.system.spawned)


def test_calibration_also_at_lan(tmp_path):
    ctx = make_ctx(tmp_path)
    bk.run_b2k_block(ab, ctx, "lan", attempts_file=tmp_path / "att.jsonl", watch_log="w.log")
    assert any(c[1].endswith("calib_profile.py") and c[c.index("--profile") + 1] == "lan" for c in ctx.system.spawned)


@pytest.mark.parametrize("poll,ldns", [(0.5, 3.4), (0.1, 51.0)])
def test_skip_when_rule_fails(tmp_path, poll, ldns):
    ctx = make_ctx(tmp_path, poll_s=poll, ldns_ms=ldns)
    r = bk.run_b2k_block(ab, ctx, "degraded", attempts_file=tmp_path / "att.jsonl", watch_log="w.log")
    assert not [c for c in ctx.system.spawned if Path(c[1]).name == "run.py"]
    assert r["status"] == "skipped" and "ldns_decision" in kinds(ctx) and ctx.ctl.requests[-1] == "lan"


def test_failed_attempt_is_recorded_and_third_refused(tmp_path):
    att = tmp_path / "att.jsonl"
    ctx = make_ctx(tmp_path, ldns_ms=80.0)
    bk.run_b2k_block(ab, ctx, "degraded", attempts_file=att, watch_log="w.log")
    rec = [json.loads(l) for l in att.read_text().splitlines()]
    assert len(rec) == 1 and rec[0]["profile"] == "degraded" and rec[0]["passed"] is False
    att.write_text("\n".join(json.dumps(x) for x in [
        {"profile": "degraded", "utc_date": "2026-10-12", "passed": False}, {"profile": "degraded", "utc_date": "2026-10-13", "passed": False}]))
    ctx2 = make_ctx(tmp_path / "b")
    (tmp_path / "b").mkdir(exist_ok=True)
    assert bk.attempts_exhausted(att, "degraded") is True
    r = bk.run_b2k_block(ab, ctx2, "degraded", attempts_file=att, watch_log="w.log")
    assert r["status"] == "stopped" and "attempt" in r["reason"] and ctx2.system.spawned == []


def test_attempts_same_day_count_once(tmp_path):
    att = tmp_path / "att.jsonl"
    att.write_text("\n".join(json.dumps({"profile": "wan", "utc_date": "2026-10-12", "passed": False}) for _ in range(2)))
    assert bk.attempts_exhausted(att, "wan") is False        # two failures on the SAME day are one attempt


def test_group_without_data_relaunched_once(tmp_path):
    ctx = make_ctx(tmp_path, run_rows=[], run_rc=1)
    bk.run_b2k_block(ab, ctx, "lan", attempts_file=tmp_path / "att.jsonl", watch_log="w.log")
    runs = [c for c in ctx.system.spawned if Path(c[1]).name == "run.py"]
    assert len(runs) == 4          # (D, C) x (first + one relaunch)


def test_failed_lan_gives_nonzero_exit(tmp_path):
    ctx = make_ctx(tmp_path)
    ctx.ctl.fail_lan = True
    r = bk.run_b2k_block(ab, ctx, "lan", attempts_file=tmp_path / "att.jsonl", watch_log="w.log")
    assert r["lan_confirmed"] is False and bk.exit_code([r]) == 3
