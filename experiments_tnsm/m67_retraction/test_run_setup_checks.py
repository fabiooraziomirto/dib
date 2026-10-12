"""D5 (audit 90 sez. 8): the setup of an episode/trial must CHECK the answers of /query and /commit, otherwise an episode can start with sites that are not Active without anybody knowing.
Hypotheses (before the change; falsification = any assertion failing):
 D5-1  setup_fact on all-200 {"applied": true} answers returns the seeded score id and makes exactly one /query and one /commit per site (order query then commit, identity op-site-<i>);
 D5-2  a non-200 status or {"applied": false} on /query or on /commit raises SetupFailed naming the site and the step ("query"/"commit") and the observed status/body;
 D5-3  episode_b1 turns SetupFailed into an EXCLUDED episode with excluded_reason "setup_failed" and the detail, it does not propagate and it does not count as a service failure;
 D5-4  the b2-kill trial setup (site-3) uses the same check: check_step() raises SetupFailed for a refusal and returns for 200/applied.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._b = status, body if body is not None else {"applied": True}

    def json(self):
        return self._b


class FakeEnv:
    ev = "https://ev"

    def __init__(self, answers=None):
        self.calls, self.answers = [], answers or {}

    def site(self, i):
        return f"https://site-{i}"

    def req(self, method, url, identity, timeout, **kw):
        self.calls.append((method, url, identity))
        if url.endswith("/seed"):
            return Resp(200, {"id": 7})
        for (i, step), resp in self.answers.items():
            if url == f"https://site-{i}/{step}":
                return resp
        return Resp()


def test_d5_1_ok():
    env = FakeEnv()
    assert r.setup_fact(env, "x.example", [0, 1, 2], 30.0) == 7
    per_site = {i: [c for c in env.calls if c[1].startswith(f"https://site-{i}/")] for i in range(3)}
    for i, cs in per_site.items():
        assert [c[1].rsplit("/", 1)[1] for c in cs] == ["query", "commit"] and all(c[2] == f"op-site-{i}" for c in cs)


@pytest.mark.parametrize("step", ["query", "commit"])
@pytest.mark.parametrize("bad", [Resp(409, {"detail": "cannot commit"}), Resp(200, {"applied": False})])
def test_d5_2_refusal_raises(step, bad):
    env = FakeEnv({(1, step): bad})
    with pytest.raises(r.SetupFailed) as ei:
        r.setup_fact(env, "x.example", [0, 1, 2], 30.0)
    assert ei.value.site == 1 and ei.value.step == step and str(bad.status_code) in str(ei.value)


def test_d5_3_episode_excluded(monkeypatch):
    env = FakeEnv({(2, "commit"): Resp(409, {"detail": "x"})})
    env.arm, env.T, env.fanout = "D", 5.0, 10
    env.queues_clean = lambda timeout: (True, 0.0)
    row = r.episode_b1(env, "lan", "t", 0)
    assert row["excluded"] is True and row["excluded_reason"] == "setup_failed" and "commit" in row["setup_failed"]


def test_d5_4_check_step():
    r.check_step(Resp(), 3, "query")
    with pytest.raises(r.SetupFailed):
        r.check_step(Resp(200, {"applied": False}), 3, "commit")
    with pytest.raises(r.SetupFailed):
        r.check_step(Resp(500, {}), 3, "query")


class RawResp:
    """A response whose body is NOT json (a plain-text 500/503, an HTML proxy page, an empty body)."""

    def __init__(self, status, text):
        self.status_code, self.text = status, text

    def json(self):
        import json
        return json.loads(self.text)


def test_d5_5_non_json_refusal_raises_setup_failed():
    """Found on the node (audit 98): R1 on the final tree crashed with JSONDecodeError at episode 8 because check_step parsed the body of a non-200 answer. Any non-200 answer, JSON or not,
    and any 200 whose body is not a JSON object, must raise SetupFailed (never another exception) carrying the status and the start of the body."""
    for resp in (RawResp(500, "Internal Server Error"), RawResp(503, ""), RawResp(409, "<html>x</html>")):
        with pytest.raises(r.SetupFailed) as ei:
            r.check_step(resp, 4, "commit")
        assert str(resp.status_code) in str(ei.value) and ei.value.site == 4 and ei.value.step == "commit"
    with pytest.raises(r.SetupFailed):
        r.check_step(RawResp(200, "not json"), 4, "query")
    with pytest.raises(r.SetupFailed):
        r.check_step(RawResp(200, "[1]"), 4, "query")


def test_d5_6_setup_fact_with_non_json_refusal_is_an_excluded_episode():
    class E(FakeEnv):
        arm, T, fanout = "D", 5.0, 10
        queues_clean = lambda self, timeout: (True, 0.0)  # noqa: E731

    env = E({(2, "commit"): RawResp(503, "Service Unavailable")})
    row = r.episode_b1(env, "lan", "t", 0)
    assert row["excluded"] is True and row["excluded_reason"] == "setup_failed" and "503" in row["setup_failed"]


# ---- audit 102: the setup retries a clean 503 (evidence unreachable / reconcile lock busy: nothing changed) up to 3 attempts per step, never a 409/500
class Seq(FakeEnv):
    """Answers each (site, step) from a list, then 200 {"applied": true}."""

    def __init__(self, plan):
        super().__init__()
        self.plan, self.n = plan, {}

    def req(self, method, url, identity, timeout, **kw):
        for (i, step), answers in self.plan.items():
            if url == f"https://site-{i}/{step}":
                k = self.n.get((i, step), 0)
                self.n[(i, step)] = k + 1
                if k < len(answers):
                    return answers[k]
        return super().req(method, url, identity, timeout, **kw)


def test_d5_7_503_is_retried(monkeypatch):
    monkeypatch.setattr(r.time, "sleep", lambda s: None)
    env = Seq({(1, "commit"): [Resp(503, {"detail": "evidence unreachable"})], (2, "query"): [RawResp(503, "x"), RawResp(503, "x")]})
    assert r.setup_fact(env, "x.example", [0, 1, 2], 30.0) == 7
    assert env.n[(1, "commit")] == 2 and env.n[(2, "query")] == 3 and env.setup_retries == 3


def test_d5_8_three_503_fail_and_409_500_are_not_retried(monkeypatch):
    monkeypatch.setattr(r.time, "sleep", lambda s: None)
    env = Seq({(1, "query"): [Resp(503, {})] * 3})
    with pytest.raises(r.SetupFailed) as ei:
        r.setup_fact(env, "x.example", [0, 1], 30.0)
    assert ei.value.status == 503 and env.n[(1, "query")] == 3
    for code in (409, 500):
        env = Seq({(1, "commit"): [Resp(code, {"detail": "x"})] * 3})
        with pytest.raises(r.SetupFailed):
            r.setup_fact(env, "x.example", [0, 1], 30.0)
        assert env.n[(1, "commit")] == 1


def test_d5_9_episode_row_counts_retries(monkeypatch):
    monkeypatch.setattr(r.time, "sleep", lambda s: None)

    class E(Seq):
        arm, T, fanout = "D", 5.0, 10
        queues_clean = lambda self, timeout: (True, 0.0)  # noqa: E731

        def warm_many(self, ids):   # stop right after the setup: the row must already carry the retry count
            raise r.ClientTimeout("stop after setup")

    env = E({(0, "commit"): [Resp(503, {})]})
    row = r.episode_b1(env, "lan", "t", 0)
    assert row.get("setup_retries") == 1
