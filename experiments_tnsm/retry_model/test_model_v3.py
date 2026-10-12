"""Model v3 (audit 78): the anti-entropy (reconcile) path. A site applies the event when EITHER the fan-out delivery OR its next periodic pull (every T = 5 s, jitter J,
random phase phi ~ U(0, T + J) after the evidence commit) brings it: apply = min(fan-out apply, phi + 2R), the pull being a connect (R) + request/response (R) exchange.
Hypotheses (before the code; falsification = any assertion failing):
 V-1  with reconcile=True a site whose fan-out delivery is pending (3 failed attempts) is NOT pending: it applies at phi + 2R, and an episode with such sites is complete;
 V-2  apply = min(fan-out, reconcile) per site; a fan-out faster than the pull is unchanged;
 V-3  sequential fan-out (FANOUT 1): the last site's apply never exceeds max over sites of (phi_i + 2R), i.e. the pull bounds the tail;
 V-4  reconcile=False reproduces v2 exactly (same outputs for the same seed);
 V-5  with p = 0 and parallel fan-out the median is the lossless nominal (the pull (>= 2R = 0.8 s at R = 0.4) never beats 1.5 R = 0.6 s for phi > 0 small? it can: phi ~ U(0, 5.5) and phi + 2R < 1.5R is impossible since 2R > 1.5R): unchanged;
 V-6  at p = 0 the sequential median with reconcile is <= the v2 sequential median (the pull only helps).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as m  # noqa: E402


def lost_never(kind):
    return False


def test_v1_pending_site_recovers_by_pull():
    flags = {i: (m.always_lost if i == 3 else lost_never) for i in range(10)}
    ep = m.episode("D", fanout=10, lost_by_site=flags, R_=0.4, rto=True, reconcile=True, phases={i: 3.0 for i in range(10)})
    assert not ep["pending"] and ep["apply_last"] == pytest.approx(3.0 + 0.8)
    ep2 = m.episode("D", fanout=10, lost_by_site={i: (m.always_lost if i == 3 else lost_never) for i in range(10)}, R_=0.4, rto=True, reconcile=False)
    assert ep2["pending"]


def test_v2_min_of_paths():
    flags = {i: lost_never for i in range(10)}
    ep = m.episode("D", fanout=10, lost_by_site=flags, R_=0.4, rto=True, reconcile=True, phases={i: 0.0 for i in range(10)})
    assert ep["apply_last"] == pytest.approx(0.6)       # fan-out 0.6 < pull 0.8
    ep = m.episode("D", fanout=10, lost_by_site=flags, R_=0.4, rto=True, reconcile=True, phases={**{i: 0.0 for i in range(10)}, 4: -1.0})
    assert min(a for a in ep["applies"] if a is not None) >= 0.0


def test_v3_sequential_tail_is_bounded_by_the_pull():
    flags = {i: lost_never for i in range(10)}
    phases = {i: 1.0 for i in range(10)}
    ep = m.episode("D", fanout=1, lost_by_site=flags, R_=0.4, rto=True, reconcile=True, phases=phases)
    assert ep["apply_last"] <= 1.0 + 0.8 + 1e-9
    ep0 = m.episode("D", fanout=1, lost_by_site={i: lost_never for i in range(10)}, R_=0.4, rto=True, reconcile=False)
    assert ep0["apply_last"] == pytest.approx(9 * 0.8 + 0.6)


def test_v4_reconcile_off_is_v2():
    a = m.simulate("D", 10, episodes=500, seed=5, R_=0.2, rto=True)
    b = m.simulate("D", 10, episodes=500, seed=5, R_=0.2, rto=True, reconcile=False)
    assert a == b


def test_v5_v6_lossless():
    a = m.simulate("D", 10, episodes=200, seed=5, p_loss=0.0, R_=0.4, rto=True, reconcile=True)
    assert a["median_ms"] == pytest.approx(600.0) and a["pending_fraction"] == 0.0
    s2 = m.simulate("D", 1, episodes=300, seed=5, p_loss=0.0, R_=0.4, rto=True, reconcile=False)["median_ms"]
    s3 = m.simulate("D", 1, episodes=300, seed=5, p_loss=0.0, R_=0.4, rto=True, reconcile=True)["median_ms"]
    assert s3 <= s2 + 1e-6 and s3 < s2


def test_v7_pending_fraction_is_zero_with_reconcile():
    r = m.simulate("D", 10, episodes=3000, seed=2, p_loss=0.10, R_=0.4, rto=True, reconcile=True)
    assert r["pending_fraction"] == 0.0
    r2 = m.simulate("D", 10, episodes=3000, seed=2, p_loss=0.10, R_=0.4, rto=True, reconcile=False)
    assert r2["pending_fraction"] > 0.1
