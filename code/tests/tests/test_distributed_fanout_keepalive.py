"""Tests of the OPT-IN persistent fan-out connections of distributed/service.py (docs/audit/62; hypotheses H-K1..K4 there are about the node
measurement, these tests are about the code). PRE-REGISTRATION: written and committed BEFORE the implementation (2026-10-12); on the current service.py
the tests that need the new names fail and must be reported as they are. DIST = code/src/dib/registry/distributed/service.py.

Contract (opt-in, default behaviour unchanged):
  DIB_DIST_FANOUT_KEEPALIVE (env, default 0) -> FANOUT_KEEPALIVE; DIB_DIST_FANOUT_WARM_INTERVAL (env, default 2.0 s; 0 = no warmer) -> WARM_INTERVAL.
  _new_site_client() -> a persistent httpx.Client (injectable in tests); _site_client(i) -> the cached client of site i (created once, under a lock);
  _drop_site_client(i, client=None) closes and forgets it; _close_site_clients() drops all; _warm_once(i) sends GET {site}/health on the cached client and
  drops it on an HTTP error; _start_warmers() / _stop_warmers() run one daemon thread per site (only the evidence role, only with KEEPALIVE and WARM_INTERVAL > 0).
  _deliver_to_site: with KEEPALIVE the attempts go through _site_client(i).post (same JSON, same timeout _FANOUT_TIMEOUT_S, same 3 attempts, same outbox
  row on failure); an HTTP error drops the client so that the NEXT attempt opens a fresh connection; otherwise the client stays.
Hypotheses (falsification = any assertion failing):
 K-1  default (KEEPALIVE off): no client is ever constructed and the cache stays empty; deliveries are exactly those of today;
 K-2  KEEPALIVE on: the first delivery to a site constructs ONE client, later deliveries reuse it, and no delivery goes through httpx.post;
 K-3  an injected failure on attempt 1 drops (closes) the client, attempt 2 uses a NEW client and succeeds, and no outbox row is written;
 K-4  three failures write the same outbox row as today and drop the client each time (3 constructions);
 K-5  _site_client is thread-safe: 8 threads asking for the same site construct ONE client;
 K-6  _warm_once uses the cached client for GET /health and drops it when the site is down;
 K-7  _close_site_clients closes every client and empties the cache; warmers: one thread per site, stopped by _stop_warmers, none unless KEEPALIVE and interval > 0;
 K-8  end to end: a dispute followed by a restore reaches the same final site states with KEEPALIVE on as with it off.
"""
from __future__ import annotations

import threading

import httpx
import pytest

from _dist_harness import make_cluster  # noqa: F401


class FakeClient:
    def __init__(self, net, serial):
        self.net, self.serial, self.closed, self.posts, self.gets = net, serial, False, 0, 0

    def post(self, url, **kw):
        self.posts += 1
        return self.net.post(url, **kw)

    def get(self, url, **kw):
        self.gets += 1
        return self.net.get(url, **kw)

    def close(self):
        self.closed = True


def _install(c):
    made = []

    def factory():
        fc = FakeClient(c.net, len(made))
        made.append(fc)
        return fc

    c.evidence_mod._new_site_client = factory
    return made


def _cluster(make_cluster, keepalive: bool, **env):
    e = {"DIB_DIST_FANOUT_KEEPALIVE": "1" if keepalive else "0", "DIB_DIST_FANOUT_WARM_INTERVAL": "0"}
    e.update(env)
    return make_cluster(n_sites=3, env=e)


def _deliver(c, i, seq=1):
    c.evidence_mod._deliver_to_site(i, 1, seq, "dispute", "disputed")


def _outbox(c):
    return c.evidence_mod._evidence_db.run(lambda con: con.execute("SELECT site_id, score_id, seq FROM pending_fanout").fetchall())


def test_k1_default_off_constructs_nothing(make_cluster):
    c = _cluster(make_cluster, keepalive=False)
    made = _install(c)
    c.seed()
    _deliver(c, 1)
    _deliver(c, 1, seq=2)
    assert made == [] and c.evidence_mod._site_clients == {} and c.evidence_mod.FANOUT_KEEPALIVE is False


def test_k2_reuse(make_cluster):
    c = _cluster(make_cluster, keepalive=True)
    made = _install(c)
    c.seed()
    _deliver(c, 1)
    _deliver(c, 1, seq=2)
    _deliver(c, 2)
    assert len(made) == 2 and made[0].posts == 2 and made[1].posts == 1
    assert c.evidence_mod._site_client(1) is made[0]
    assert not any(cl.closed for cl in made)


def test_k3_failure_drops_client_and_retries_on_a_new_one(make_cluster):
    c = _cluster(make_cluster, keepalive=True)
    made = _install(c)
    c.seed()
    c.net.fail_next[(1, "/apply_fanout")] = 1
    _deliver(c, 1)
    assert len(made) == 2 and made[0].closed and not made[1].closed and made[1].posts == 1
    assert _outbox(c) == []


def test_k4_three_failures_write_the_outbox_row(make_cluster):
    c = _cluster(make_cluster, keepalive=True)
    made = _install(c)
    sid = c.seed()
    c.net.fail_next[(1, "/apply_fanout")] = 3
    _deliver(c, 1)
    assert len(made) == 3 and all(cl.closed for cl in made)
    assert _outbox(c) == [("site-1", sid, 1)]


def test_k5_thread_safe_creation(make_cluster):
    c = _cluster(make_cluster, keepalive=True)
    made = _install(c)
    barrier, got = threading.Barrier(8), []

    def worker():
        barrier.wait()
        got.append(c.evidence_mod._site_client(2))

    ts = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(made) == 1 and all(g is made[0] for g in got)


def test_k6_warm_once(make_cluster):
    c = _cluster(make_cluster, keepalive=True)
    made = _install(c)
    c.evidence_mod._warm_once(1)
    assert len(made) == 1 and made[0].gets == 1 and not made[0].closed
    c.net.down.add(1)
    c.evidence_mod._warm_once(1)
    assert made[0].closed and 1 not in c.evidence_mod._site_clients


def test_k7_close_and_warmers(make_cluster):
    c = _cluster(make_cluster, keepalive=True, DIB_DIST_FANOUT_WARM_INTERVAL="0.05")
    made = _install(c)
    mod = c.evidence_mod
    c.seed()
    _deliver(c, 0)
    _deliver(c, 1)
    mod._close_site_clients()
    assert all(cl.closed for cl in made) and mod._site_clients == {}
    mod._start_warmers()
    try:
        assert len(mod._warmer_threads) == 3 and all(t.is_alive() for t in mod._warmer_threads)
    finally:
        mod._stop_warmers()
    assert mod._warmer_threads == []
    # off: no warmer
    c2 = _cluster(make_cluster, keepalive=False, DIB_DIST_FANOUT_WARM_INTERVAL="0.05")
    c2.evidence_mod._start_warmers()
    assert c2.evidence_mod._warmer_threads == []
    c3 = _cluster(make_cluster, keepalive=True, DIB_DIST_FANOUT_WARM_INTERVAL="0")
    c3.evidence_mod._start_warmers()
    assert c3.evidence_mod._warmer_threads == []


def _final_states(make_cluster, keepalive):
    c = _cluster(make_cluster, keepalive=keepalive)
    if keepalive:
        _install(c)
    sid = c.seed()
    for s in range(3):
        c.stage(s)
        c.commit(s)
    c.dispute("site-0")
    after_dispute = [c.state(s, sid)["state"] for s in range(3)]
    c.restore()
    return after_dispute, [c.state(s, sid)["state"] for s in range(3)]


def test_k8_same_final_states(make_cluster):
    off = _final_states(make_cluster, False)
    on = _final_states(make_cluster, True)
    assert on == off and "disputed" in on[0]


# ---- K-9, K-10 (added 2026-10-12 after docs/audit/76 run 1: the warm connection was often cold) --------------------------------------------------------------
def test_k9_pool_keeps_two_connections():
    """A ping in flight must not force a delivery to open a new connection: the real httpx client keeps up to 2 idle connections per site."""
    import importlib.util
    import sys
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / "src" / "dib" / "registry" / "distributed" / "service.py"
    # the module reads its role from the environment at import; use the harness-less path: read the limits from the source text of _new_site_client
    text = src.read_text()
    block = text[text.index("def _new_site_client"):text.index("def _site_client(")]
    assert "max_keepalive_connections=2" in block


def test_k10_ping_timeout_is_longer_than_the_delivery_timeout(make_cluster):
    """A ping delayed by a TCP retransmission (RTO ~1.2 s at RTT 0.4 s) must not drop a good connection: the ping timeout exceeds the 1 s delivery timeout."""
    c = _cluster(make_cluster, keepalive=True)
    seen = {}

    class Rec(FakeClient):
        def get(self, url, **kw):
            seen["timeout"] = kw.get("timeout")
            return super().get(url, **kw)

    c.evidence_mod._new_site_client = lambda: Rec(c.net, 0)
    c.evidence_mod._warm_once(1)
    assert seen["timeout"] is not None and seen["timeout"] > c.evidence_mod._FANOUT_TIMEOUT_S
