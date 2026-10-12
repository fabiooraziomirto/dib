"""Model v4 (audit 80): the HTTP request leaves in TWO TCP segments (headers and body, TCP_NODELAY). Both must arrive: the request reaches the server when the later of the two
(each retransmitted independently after the RTO) arrives. Hypotheses (before the code; falsification = any assertion failing):
 W-1  with req_segments=2 the request is lost-and-delayed if EITHER segment is lost: with a scripted pattern (first segment lost once) the delay is one RTO;
 W-2  two losses (one per segment) delay by the MAX of the two extras, not their sum: both lost once at R = 0.1: extra = rto(0.1) = 0.3 (not 0.6);
 W-3  req_segments=1 reproduces v3 exactly (same simulation, same seed);
 W-4  at the same loss rate, req_segments=2 never has a smaller per-site late share than req_segments=1 (monotone), strictly larger at p = 7 %;
 W-5  lossless behaviour is unchanged (median = nominal).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as m  # noqa: E402


def scripted(*flags):
    it = iter(flags)
    return lambda kind: next(it, False)


def test_w1_one_segment_lost_once():
    # syn, synack, request-1 lost, request-2 ok
    a = m.attempt("D", lost=scripted(False, False, True, False), rto=True, R_=0.1, req_segments=2)
    assert a["ok"] and a["apply"] == pytest.approx(0.1 + 0.3 + 0.05)


def test_w2_max_not_sum():
    a = m.attempt("D", lost=scripted(False, False, True, False, True, False), rto=True, R_=0.1, req_segments=2)   # seg1 lost once, then seg2 lost once
    assert a["apply"] == pytest.approx(0.1 + 0.3 + 0.05)


def test_w3_one_segment_is_v3():
    a = m.simulate("D", 10, episodes=800, seed=4, p_loss=0.07, R_=0.15, rto=True, reconcile=True)
    b = m.simulate("D", 10, episodes=800, seed=4, p_loss=0.07, R_=0.15, rto=True, reconcile=True, req_segments=1)
    assert a == b


def test_w4_monotone_in_segments():
    one = m.simulate("D", 10, episodes=4000, seed=4, p_loss=0.07, R_=0.15, rto=True, reconcile=True, req_segments=1)
    two = m.simulate("D", 10, episodes=4000, seed=4, p_loss=0.07, R_=0.15, rto=True, reconcile=True, req_segments=2)
    assert two["late_share"] > one["late_share"] + 0.02


def test_w5_lossless_unchanged():
    z = m.simulate("D", 10, episodes=100, seed=4, p_loss=0.0, R_=0.3, rto=True, reconcile=True, req_segments=2)
    assert z["median_ms"] == pytest.approx(450.0) and z["late_share"] == 0.0
