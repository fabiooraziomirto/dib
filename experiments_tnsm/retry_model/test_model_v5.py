"""Model v5 (audit 94/95): the mTLS client flight (Certificate+CertificateVerify+Finished, ONE segment, audit 94 row 5) is sent in the same burst as the two request segments, so the arm C
request reaches the service when the later of THREE segments arrives. v5 = v4 with req_segments=3 in C and 2 in D; nothing is fitted.
Hypotheses (falsified by any failing assertion):
 V-1  model.py is untouched: v4 defaults reproduce the audit-85 predictions (C/10 0.251, median 2800 ms; D/10 0.179) with the same seed;
 V-2  v5 simulate("D") == v4 simulate("D", req_segments=2) exactly (same stream, same numbers); v5 simulate("C") == v4 simulate("C", req_segments=3) exactly;
 V-3  without loss the arm C request arrives at 2.5 R (cold) for both models (the extra segment costs nothing when nothing is lost): median_ms = 1000 * 2.5 R;
 V-4  monotone: at the same seed and loss, v5 C late share >= v4 C late share, strictly larger at p = 6 %;
 V-5  the version switch is explicit: kwargs_for("C") == {"req_segments": 3, "rto": True}, kwargs_for("D") == {"req_segments": 2, "rto": True}, unknown arm raises.
"""
import pytest

import model as m
import model_v5 as v5


def test_v1_v4_untouched():
    c = m.simulate("C", 10, episodes=20000, R_=0.4, rto=True, req_segments=2)
    d = m.simulate("D", 10, episodes=20000, R_=0.4, rto=True, req_segments=2)
    assert round(c["late_share"], 3) == 0.251 and c["median_ms"] == 2800
    assert round(d["late_share"], 3) == 0.179


def test_v2_v5_is_v4_with_segments():
    a = v5.simulate("D", 10, episodes=3000, R_=0.4)
    b = m.simulate("D", 10, episodes=3000, R_=0.4, rto=True, req_segments=2)
    assert a == b
    a = v5.simulate("C", 10, episodes=3000, R_=0.4)
    b = m.simulate("C", 10, episodes=3000, R_=0.4, rto=True, req_segments=3)
    assert a == b


def test_v3_no_loss_cold_request_at_2_5_R():
    for R in (0.12, 0.4):
        for sim in (lambda **k: v5.simulate("C", 10, **k), lambda **k: m.simulate("C", 10, rto=True, req_segments=2, **k)):
            r = sim(episodes=200, R_=R, p_loss=0.0)
            assert r["median_ms"] == pytest.approx(2500 * R) and r["late_share"] == 0.0


def test_v4_monotone_and_strict_at_6_percent():
    a = v5.simulate("C", 10, episodes=6000, R_=0.12, p_loss=0.06)["late_share"]
    b = m.simulate("C", 10, episodes=6000, R_=0.12, p_loss=0.06, rto=True, req_segments=2)["late_share"]
    assert a >= b and a > b + 0.02


def test_v5_explicit_switch():
    assert v5.kwargs_for("C") == {"req_segments": 3, "rto": True}
    assert v5.kwargs_for("D") == {"req_segments": 2, "rto": True}
    with pytest.raises(ValueError):
        v5.kwargs_for("X")
