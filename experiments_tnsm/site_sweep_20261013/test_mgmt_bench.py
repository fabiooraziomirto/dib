"""Unit tests of the corrected management-path benchmark (no cluster needed).

Hypotheses: (1) the mix contains no client-side no-op; (2) a 409 is a rejection, any
other non-2xx (incl. 403, 5xx) is an error, never a success; (3) a transport failure
is recorded with its outcome and still timed. Falsification: any assertion below.
"""
from collections import Counter

import httpx
import pytest

import mgmt_bench


def test_mix_has_no_noop_and_keeps_old_proportions():
    assert "contribute" not in mgmt_bench.MIX
    assert Counter(mgmt_bench.MIX) == {"query": 8, "commit": 7, "attest": 1, "dispute": 1, "restore": 1}
    old = [op for op in mgmt_bench.base._MIX_REALISTIC if op != "contribute"]
    assert mgmt_bench.MIX == old


@pytest.mark.parametrize("status,body,expected", [
    (200, {"applied": True}, ("ok", True)),
    (200, {"applied": False}, ("ok", False)),
    (200, {"acked": True}, ("ok", None)),
    (409, {"detail": "x"}, ("rejected", None)),
    (403, {"detail": "x"}, ("error", None)),
    (503, {"detail": "x"}, ("error", None)),
    (500, None, ("error", None)),
])
def test_classify(status, body, expected):
    resp = httpx.Response(status, json=body) if body is not None else httpx.Response(status, text="boom")
    assert mgmt_bench.classify(resp) == expected


def test_transport_error_is_recorded(monkeypatch):
    class Boom:
        def post(self, *a, **k):
            raise httpx.ConnectTimeout("t")

    monkeypatch.setattr(mgmt_bench.base, "_client_for", lambda identity: Boom())
    monkeypatch.setattr(mgmt_bench.base, "N_SITES", 2)
    r = mgmt_bench.do_op(0, 0, 0.0)
    assert r["outcome"] == "timeout" and r["status"] == "ConnectTimeout" and r["changed"] is False
    assert r["latency_s"] >= 0


def test_changed_only_for_state_changes(monkeypatch):
    class Ok:
        def __init__(self, body):
            self.body = body

        def post(self, *a, **k):
            return httpx.Response(200, json=self.body)

    monkeypatch.setattr(mgmt_bench.base, "N_SITES", 1)
    idx = {op: mgmt_bench.MIX.index(op) for op in set(mgmt_bench.MIX)}
    monkeypatch.setattr(mgmt_bench.base, "_client_for", lambda identity: Ok({"applied": False}))
    assert mgmt_bench.do_op(0, idx["dispute"], 0.0)["changed"] is False
    assert mgmt_bench.do_op(0, idx["query"], 0.0)["changed"] is False
    assert mgmt_bench.do_op(0, idx["commit"], 0.0)["changed"] is True
    monkeypatch.setattr(mgmt_bench.base, "_client_for", lambda identity: Ok({"applied": True}))
    assert mgmt_bench.do_op(0, idx["dispute"], 0.0)["changed"] is True
