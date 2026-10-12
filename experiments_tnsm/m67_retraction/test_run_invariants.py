"""Opt-in end-of-episode invariant check in run.py (audit 90 sez. 5). Default OFF (DIB_M67_INVARIANTS unset or 0): behaviour and rows unchanged. Hypotheses (falsified by any failing assertion):
 V-1  invariants_enabled() is True only for DIB_M67_INVARIANTS=1;
 V-2  end_state_invariants(env, ep, sid, sites) reads GET /state/<sid> of every site (identity admin), GET /scores of the fact at the evidence and the pending counts, and returns
      {"violations": [...], "unreadable_sites": [...]} using common/invariants.py with the B1 event log (a 200 commit per site, one 200 dispute, no restore);
 V-3  a clean disputed episode (all sites disputed, evidence disputed, same seq, empty queues) -> no violation; one site still `active` after the dispute with an empty queue -> ExportSafe
      and I1-free (commit was 200) for that site; a 404 /state -> that site is NOT a violation and is not listed as unreadable (absent row); a transport error -> listed as unreadable, no violation;
 V-4  episode_b1 with the flag ON writes row["invariants"], with the flag OFF there is no "invariants" key; a failure inside the check never excludes the episode (it is reported as invariants_error);
 V-5  the manifest flag: invariants_enabled() is recorded under "invariants" in manifest (helper manifest_flags()).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._b = status, body

    def json(self):
        return self._b


class Env:
    ev = "https://ev"

    def __init__(self, states, score=None, pending=None, boom=()):
        self.states, self.score, self.pend, self.boom = states, score or {"id": 7, "status": "disputed", "fanout_seq": 1}, pending or {}, set(boom)

    def site(self, i):
        return f"https://s{i}"

    def req(self, method, url, identity, timeout, **kw):
        assert identity == "admin"
        if url.startswith(self.ev + "/scores"):
            return Resp(200, self.score)
        i = int(url.split("//s")[1].split("/")[0])
        if i in self.boom:
            raise r.TransportFailure("ReadError", "x")
        st = self.states.get(i)
        return Resp(404, {"detail": "no local decision"}) if st is None else Resp(200, st)

    def read_pending(self, sites):
        return {i: [{"score_id": 7, "seq": 1}] * self.pend.get(i, 0) for i in sites}


def st(state, la=1, origin=None):
    return {"state": state, "origin": origin, "last_applied_seq": la}


def test_v1_flag(monkeypatch):
    monkeypatch.delenv("DIB_M67_INVARIANTS", raising=False)
    assert r.invariants_enabled() is False
    monkeypatch.setenv("DIB_M67_INVARIANTS", "0")
    assert r.invariants_enabled() is False
    monkeypatch.setenv("DIB_M67_INVARIANTS", "1")
    assert r.invariants_enabled() is True


def test_v3_clean():
    out = r.end_state_invariants(Env({i: st("disputed") for i in range(3)}), "e.example", 7, [0, 1, 2])
    assert out == {"violations": [], "unreadable_sites": []}


def test_v3_active_after_dispute_is_export_unsafe():
    out = r.end_state_invariants(Env({0: st("disputed"), 1: st("active", la=0)}), "e.example", 7, [0, 1])
    kinds = [v[0] for v in out["violations"]]
    assert "ExportSafe" in kinds and "I1_ActiveWithoutCommit" not in kinds


def test_v3_404_and_transport_error():
    out = r.end_state_invariants(Env({0: st("disputed")}, boom=(2,)), "e.example", 7, [0, 1, 2])
    assert out["violations"] == [] and out["unreadable_sites"] == [2]


def test_v4_episode_flag_off_and_failure_is_not_exclusion(monkeypatch):
    class E(Env):
        arm, T, fanout = "D", 5.0, 1

        def queues_clean(self, timeout):
            return True, 0.0

    monkeypatch.delenv("DIB_M67_INVARIANTS", raising=False)
    assert r.invariants_row(E({}), "e", 7, [0]) == {}
    monkeypatch.setenv("DIB_M67_INVARIANTS", "1")
    assert "violations" in r.invariants_row(E({0: st("disputed")}), "e", 7, [0])["invariants"]
    e = E({})
    e.req = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    out = r.invariants_row(e, "e", 7, [0])
    assert "invariants_error" in out and "excluded" not in out


def test_v5_manifest_flags(monkeypatch):
    monkeypatch.setenv("DIB_M67_INVARIANTS", "1")
    assert r.manifest_flags()["invariants"] is True
    monkeypatch.delenv("DIB_M67_INVARIANTS")
    assert r.manifest_flags()["invariants"] is False
