"""trial_b2kill must not leave site-3 dead when a trial is excluded after `kill site-3` (audit 57; found by the B2k data of 2026-10-11).
Hypotheses (written before the fix; falsification = any assertion failing):
 F-1  a ClientTimeout raised after `kill site-3` and before `start site-3` leads to exactly ONE `start site-3` command, after the kill, and the row is still
      excluded with its cause and carries site3_restarted_after_exception = True;
 F-2  the same for a TransportFailure;
 F-3  an exception BEFORE the kill (here at /seed) issues no start and no flag;
 F-4  the restart is best effort: if the start command itself fails the original cause is kept and the row records the failure (no masking exception);
 F-5  an exception after a successful `start site-3` (flag started) does not issue a second start.
No docker, no network: a FAKE Env records the commands."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


class _Resp:
    def json(self):
        return {"id": 7, "pending": [], "applied": True}   # D5: the setup checks "applied"; the fixture answered nothing about it before

    status_code = 200


class FakeEnv:
    arm, T, fanout = "D", 5.0, 10
    ev = "https://evidence"

    def __init__(self, fail_at=None, exc=None, start_fails=False, fail_after_start=False):
        self.cmds, self.fail_at, self.exc, self.start_fails, self.fail_after_start = [], fail_at, exc, start_fails, fail_after_start

    def queues_clean(self, timeout):
        return True, 0.0

    def site(self, i):
        return f"https://site-{i}"

    def compose(self):
        return "COMPOSE "

    def warm(self, identity, url=None):
        pass

    def sh(self, cmd, check=True, timeout=300):
        self.cmds.append(cmd)
        if self.start_fails and "start site-3" in cmd:
            raise RuntimeError("docker start failed")
        return ""

    def req(self, method, url, identity, timeout, **kw):
        if self.fail_at and self.fail_at in url:
            raise self.exc
        if self.fail_after_start and url.endswith("/export_mud"):
            raise self.exc
        return _Resp()


def starts(env):
    return [c for c in env.cmds if "start site-3" in c]


def kills(env):
    return [c for c in env.cmds if "kill site-3" in c]


def test_f1_client_timeout_after_kill_restarts_site3():
    env = FakeEnv("/dispute", r.ClientTimeout("t"))
    row = r.trial_b2kill(env, "lan", 2, 0, None)
    assert row["excluded"] and "client_timeout" in row
    assert len(kills(env)) == 1 and len(starts(env)) == 1 and env.cmds.index(starts(env)[0]) > env.cmds.index(kills(env)[0])
    assert row["site3_restarted_after_exception"] is True


def test_f2_transport_failure_after_kill_restarts_site3():
    env = FakeEnv("/dispute", r.TransportFailure("ReadError", "x"))
    row = r.trial_b2kill(env, "lan", 2, 0, None)
    assert row["excluded"] and row["excluded_reason"] == "transport_error" and len(starts(env)) == 1
    assert row["site3_restarted_after_exception"] is True


def test_f3_exception_before_kill_issues_no_start():
    env = FakeEnv("/seed", r.ClientTimeout("t"))
    row = r.trial_b2kill(env, "lan", 2, 0, None)
    assert row["excluded"] and not kills(env) and not starts(env) and "site3_restarted_after_exception" not in row


def test_f4_failed_restart_keeps_the_original_cause():
    env = FakeEnv("/dispute", r.ClientTimeout("t"), start_fails=True)
    row = r.trial_b2kill(env, "lan", 2, 0, None)
    assert row["excluded"] and "client_timeout" in row
    assert row["site3_restarted_after_exception"] is False and "docker start failed" in row["site3_restart_error"]


def test_f5_no_second_start_after_a_normal_start(monkeypatch):
    """The export polling catches generic exceptions itself; a TransportFailure out of logs after the start is raised by the fake `logs`."""
    env = FakeEnv()
    env.logs = lambda *a, **k: (_ for _ in ()).throw(r.TransportFailure("X", "after start"))
    monkeypatch.setattr(r.time, "sleep", lambda *_: None)
    monkeypatch.setattr(r, "parse_access_lines", lambda *a, **k: [])
    # make the export poll succeed immediately with a document that has no endpoint, so the loop ends at once
    class _Ok(_Resp):
        status_code = 200
        def json(self):
            return {"id": 7, "pending": [], "mud": {}, "applied": True}   # D5
    env.req = lambda method, url, identity, timeout, **kw: _Ok()
    row = r.trial_b2kill(env, "lan", 1, 0, None)
    assert len(starts(env)) == 1 and row["excluded"] and "site3_restarted_after_exception" not in row
