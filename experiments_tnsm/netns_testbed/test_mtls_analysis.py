"""mTLS arm in the netns analysis (audit 95). Hypotheses (falsified by any failing assertion):
 M-1  nominal(R, warm=False, arm="C") = 2.5 R (SYN R, hello flight R, request R/2); arm "D" (default) stays 1.5 R; a warm connection is 0.5 R in both arms;
 M-2  is_late uses nominal + 0.75 R of the ARM: for R=0.4 an apply at 1.7 s is late for D (1.5*0.4+0.3=0.9) and for C (2.5*0.4+0.3=1.3) alike, 1.2 s is late for D but not for C;
 M-3  cell_summary(..., arm="C") counts late with the C nominal; the default call is unchanged (same numbers as before the change);
 M-4  late_share_ci(eps, R, arm) returns (share, lo, hi) with share = late/sites over setup_ok episodes, lo <= share <= hi, resampling EPISODES, deterministic for a fixed seed;
 M-5  t0_valid(arm="C") accepts a lossless median of 2.5 R and rejects 1.5 R.
"""
import pytest

import analysis as an


def _eps(vals_by_ep):
    return [{"setup_ok": True, "applies": {str(i): v for i, v in enumerate(vs)}} for vs in vals_by_ep]


def test_m1_nominal_by_arm():
    assert an.nominal(0.4, False) == pytest.approx(0.6)
    assert an.nominal(0.4, False, arm="D") == pytest.approx(0.6)
    assert an.nominal(0.4, False, arm="C") == pytest.approx(1.0)
    assert an.nominal(0.4, True, arm="C") == pytest.approx(0.2) and an.nominal(0.4, True) == pytest.approx(0.2)


def test_m2_late_by_arm():
    assert an.is_late(1.2, 0.4, False) and not an.is_late(1.2, 0.4, False, arm="C")
    assert an.is_late(1.7, 0.4, False) and an.is_late(1.7, 0.4, False, arm="C")


def test_m3_cell_summary_arm():
    eps = _eps([[0.6] * 9 + [1.2], [1.0] * 10])
    d = an.cell_summary(eps, 0.4, False)
    c = an.cell_summary(eps, 0.4, False, arm="C")
    assert d["late_share"] == pytest.approx(11 / 20) and c["late_share"] == pytest.approx(0 / 20)


def test_m4_late_share_ci():
    eps = _eps([[0.6] * 10] * 6 + [[0.6] * 5 + [1.7] * 5] * 4)
    s, lo, hi = an.late_share_ci(eps, 0.4, "D", res=500, seed=1)
    assert s == pytest.approx(20 / 100) and lo <= s <= hi and 0 < lo and hi < 1
    assert an.late_share_ci(eps, 0.4, "D", res=500, seed=1) == (s, lo, hi)


def test_m5_t0_arm():
    ok = _eps([[1.0] * 10] * 3)
    assert an.t0_valid(ok, 0.4, False, arm="C")["valid"] and not an.t0_valid(ok, 0.4, False)["valid"]
