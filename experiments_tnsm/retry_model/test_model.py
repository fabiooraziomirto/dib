"""Tests of retry_model/model.py (audit 60 s.3-4). Hypotheses (before the module; falsification = any assertion failing):
 M-1  without loss: D attempt applies at 0.6 s and returns at 0.8 s; C applies at 1.0 s and returns at 1.2 s; a warm (kept-alive) attempt applies at 0.2 s;
 M-2  a lost connect packet fails the attempt at exactly the phase timeout (1.0 s); three failures give a pending delivery after 3.0 s with no apply;
 M-3  a lost RESPONSE fails the attempt but the request was already applied: first_apply stays at the first arrival (idempotent), the delivery still retries;
 M-4  a lost REQUEST fails at t_connect + timeout and the request never applied; the retry applies at t_fail + 0.6 (D);
 M-5  C has an extra TLS phase (2 packets); its failure costs t_tcp + timeout;
 M-6  FANOUT 10 starts every site at t = 0 (episode apply = max of the sites); FANOUT 1 starts site j when site j-1 returned;
 M-7  a shorter phase timeout (0.6) shortens the failed attempt to 0.6 s; the hedge opens a second connect at 0.5 s and completes at 0.9 s when the first SYN is lost;
 M-8  the episode is 'complete' iff no site is pending; seeded runs are reproducible.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as m  # noqa: E402


def scripted(*lost_flags):
    it = iter(lost_flags)
    return lambda kind: next(it, False)


def test_m1_no_loss():
    a = m.attempt("D", lost=scripted())
    assert (a["apply"], a["dur"], a["ok"]) == pytest.approx((0.6, 0.8, True))
    c = m.attempt("C", lost=scripted())
    assert (c["apply"], c["dur"], c["ok"]) == pytest.approx((1.0, 1.2, True))
    w = m.attempt("D", lost=scripted(), warm=True)
    assert (w["apply"], w["dur"]) == pytest.approx((0.2, 0.4))


def test_m2_connect_loss_and_pending():
    a = m.attempt("D", lost=scripted(True))
    assert a["dur"] == pytest.approx(1.0) and a["apply"] is None and not a["ok"]
    d = m.deliver("D", lost=m.always_lost)
    assert d["pending"] and d["first_apply"] is None and d["ret"] == pytest.approx(3.0)


def test_m3_response_loss_is_applied_once():
    # packets: syn, synack, request, response -> response lost on attempt 1 only
    d = m.deliver("D", lost=scripted(False, False, False, True))
    assert d["first_apply"] == pytest.approx(0.6) and not d["pending"]
    assert d["ret"] == pytest.approx(1.4 + 0.8)          # failed attempt: 0.4 + 1.0, then a clean attempt of 0.8


def test_m4_request_loss():
    d = m.deliver("D", lost=scripted(False, False, True))   # request lost on attempt 1
    assert d["first_apply"] == pytest.approx(1.4 + 0.6)


def test_m5_tls_phase():
    a = m.attempt("C", lost=scripted(False, False, True))     # tcp ok, ClientHello lost
    assert a["dur"] == pytest.approx(0.4 + 1.0) and a["apply"] is None


def test_m6_fanout_modes():
    """Site 3 loses its first SYN, the others are clean (D). Parallel: site 3 applies at 1.0 + 0.6 = 1.6 s, the episode ends there.
    Sequential: sites 0-2 return at 0.8, 1.6, 2.4 s; site 3 starts at 2.4, fails at 3.4, retries and applies at 2.4 + 1.0 + 0.6 = 4.0 s, returns at
    4.2 s; sites 4-9 start at 4.2 + 0.8*(j - 4); site 9 starts at 8.2 and applies at 8.8 s."""
    def flags():
        return {i: scripted(True) if i == 3 else scripted() for i in range(10)}
    assert m.episode("D", fanout=10, lost_by_site=flags())["apply_last"] == pytest.approx(1.6)
    assert m.episode("D", fanout=1, lost_by_site=flags())["apply_last"] == pytest.approx(8.8)


def test_m7_timeout_and_hedge():
    a = m.attempt("D", lost=scripted(True), timeout=0.6)
    assert a["dur"] == pytest.approx(0.6)
    h = m.attempt("D", lost=scripted(True, False, False, False, False, False), hedge_s=0.5)   # first SYN lost, hedge clean
    assert h["apply"] == pytest.approx(0.5 + 0.4 + 0.2)


def test_m8_reproducible_and_complete_flag():
    r1 = m.simulate("D", fanout=10, episodes=200, seed=1)
    r2 = m.simulate("D", fanout=10, episodes=200, seed=1)
    assert r1 == r2 and 0.0 <= r1["pending_fraction"] <= 1.0
    z = m.simulate("D", fanout=10, episodes=50, seed=1, p_loss=0.0)
    assert z["median_ms"] == pytest.approx(600.0) and z["pending_fraction"] == 0.0 and z["late_share"] == 0.0
