"""Model v2 (audit 75): TCP retransmission timeout for packets after the handshake. Hypotheses (before the code; falsification = any assertion failing):
 R-1  rto(R) = R + max(2R, 0.2) (Linux: srtt + max(4*rttvar, 200 ms) with srtt = R, rttvar = R/2): 0.4 -> 1.2, 0.2 -> 0.6, 0.1 -> 0.3, 0.05 -> 0.25;
 R-2  at R = 0.4 the v2 attempt is the v1 attempt for every single-loss case (RTO 1.2 >= the 1.0 s phase timeout): request loss fails at t_connect + 1.0 with no apply,
      response loss fails at t_connect + 1.0 with the request applied;
 R-3  at R = 0.1 a lost request is retransmitted after rto = 0.3 s and the attempt SUCCEEDS: apply = 0.1 + 0.3 + 0.05, return = 0.1 + 0.1 + 0.3;
 R-4  two losses of the same packet at R = 0.1 (0.3 + 0.6 s) reach the 1.0 s timeout: the attempt fails;
 R-5  a SYN or SYN-ACK loss fails the attempt at the timeout for any R (initial RTO 1 s);
 R-6  the C TLS phase survives a single flight loss at R = 0.1 (phase time R + rto < 1.0) and fails at R = 0.4;
 R-7  v1 behaviour is unchanged when rto=False (default).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as m  # noqa: E402


def scripted(*flags):
    it = iter(flags)
    return lambda kind: next(it, False)


@pytest.mark.parametrize("R,expected", [(0.4, 1.2), (0.2, 0.6), (0.1, 0.3), (0.05, 0.25)])
def test_r1_rto(R, expected):
    assert m.rto(R) == pytest.approx(expected)


def test_r2_same_as_v1_at_R04():
    a = m.attempt("D", lost=scripted(False, False, True), rto=True)
    assert a["dur"] == pytest.approx(0.4 + 1.0) and a["apply"] is None and not a["ok"]
    b = m.attempt("D", lost=scripted(False, False, False, True), rto=True)
    assert b["dur"] == pytest.approx(0.4 + 1.0) and b["apply"] == pytest.approx(0.6) and not b["ok"]


def test_r3_request_loss_survives_at_R01():
    a = m.attempt("D", lost=scripted(False, False, True), rto=True, R_=0.1)
    assert a["ok"] and a["apply"] == pytest.approx(0.1 + 0.3 + 0.05) and a["dur"] == pytest.approx(0.1 + 0.1 + 0.3)


def test_r4_double_loss_times_out():
    a = m.attempt("D", lost=scripted(False, False, True, True), rto=True, R_=0.1)     # request lost, its retransmission lost
    assert not a["ok"] and a["dur"] == pytest.approx(0.1 + 1.0)


@pytest.mark.parametrize("R", [0.05, 0.1, 0.4])
def test_r5_syn_loss_always_fails(R):
    a = m.attempt("D", lost=scripted(True), rto=True, R_=R)
    assert a["dur"] == pytest.approx(1.0) and not a["ok"] and a["apply"] is None
    b = m.attempt("D", lost=scripted(False, True), rto=True, R_=R)
    assert b["dur"] == pytest.approx(1.0) and not b["ok"]


def test_r6_tls_flight_loss():
    ok = m.attempt("C", lost=scripted(False, False, True), rto=True, R_=0.1)         # ClientHello lost
    assert ok["ok"] and ok["dur"] > 0.3 + 0.1 * 3 - 0.01
    bad = m.attempt("C", lost=scripted(False, False, True), rto=True, R_=0.4)
    assert not bad["ok"] and bad["dur"] == pytest.approx(0.4 + 1.0)


def test_r7_v1_unchanged():
    a = m.attempt("D", lost=scripted(False, False, True), R_=0.1)
    assert not a["ok"] and a["dur"] == pytest.approx(0.1 + 1.0)


def test_r8_late_share_threshold_scales_with_R():
    z = m.simulate("D", fanout=10, episodes=50, seed=1, p_loss=0.0, R_=0.1, rto=True)
    assert z["median_ms"] == pytest.approx(150.0) and z["late_share"] == 0.0
    z2 = m.simulate("C", fanout=10, episodes=50, seed=1, p_loss=0.0, R_=0.2, rto=True)
    assert z2["median_ms"] == pytest.approx(500.0)


def test_r9_v2_matches_v1_at_degraded():
    """At R = 0.4 the RTO (1.2 s) exceeds the phase timeout: v2 and v1 must agree statistically (same medians within 5%, late share within 2 points)."""
    for arm in ("D", "C"):
        a = m.simulate(arm, 10, episodes=8000, seed=3)
        b = m.simulate(arm, 10, episodes=8000, seed=3, rto=True)
        assert abs(a["median_ms"] - b["median_ms"]) <= 0.05 * a["median_ms"]
        assert abs(a["late_share"] - b["late_share"]) <= 0.02
