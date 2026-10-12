"""Profiles X1-X4 of the out-of-sample validation of model v5 on the REAL deployment (audit 107). Same convention as `degraded` (d = one-way delay of every container egress, loss per side, R = 2d).
Hypotheses (falsified by any failing assertion): P-1 PROFILES has x1..x4 with (d, R, loss_rt) = (0.060, 0.12, 0.12), (0.100, 0.20, 0.08), (0.150, 0.30, 0.12), (0.150, 0.30, 0.16) (loss_rt = round trip = 1-(1-p)^2 rounded to 2 decimals
of the existing table convention 2p: 0.06->0.12, 0.04->0.08, 0.06->0.12, 0.08->0.16); P-2 the RTT bands are +-20% of 1000*R; P-3 B1 default episodes = 50; P-4 the profile-dependent helpers work for every x profile
(d_run_max, bound_kill, hard_limit_s, gen_path_d, dispute_rtt_bias_s = 2d); P-5 existing profiles unchanged (degraded still d 0.2, R 0.4, loss 0.10)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402

X = {"x1": (0.060, 0.12, 0.12), "x2": (0.100, 0.20, 0.08), "x3": (0.150, 0.30, 0.12), "x4": (0.150, 0.30, 0.16)}


@pytest.mark.parametrize("name", sorted(X))
def test_p1_to_p4(name):
    d, R, loss = X[name]
    assert r.PROFILES[name] == {"d": d, "R": R, "loss_rt": loss}
    lo, hi = r.RTT_EXPECT_MS[name][0]
    assert lo == pytest.approx(0.8 * 1000 * R) and hi == pytest.approx(1.2 * 1000 * R) and len(r.RTT_EXPECT_MS[name]) == 10
    assert r.B1_EPISODES[name] == 50
    cells = r.plan(name, ["b1"], ["D", "C"], [10])
    assert [(c["arm"], c["fanout"], c["episodes"]) for c in cells] == [("D", 10, 50), ("C", 10, 50)]
    assert r.d_run_max(name, "C") == pytest.approx(3 * 3 * R + 2.0)
    assert r.bound_kill(name, "D", 5.0) > 0 and r.hard_limit_s(name, "C", 10) == pytest.approx(12.0)
    assert r.gen_path_d(name) == d and r.dispute_rtt_bias_s(name) == pytest.approx(2 * d)


def test_p5_existing_unchanged():
    assert r.PROFILES["degraded"] == {"d": 0.200, "R": 0.400, "loss_rt": 0.10}
    assert r.B1_EPISODES["degraded"] == 50 and r.B1_EPISODES["lan"] == 10
