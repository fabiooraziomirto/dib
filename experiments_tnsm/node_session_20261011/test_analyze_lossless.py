"""analyze_lossless.py (audit 113, node T-0 of the mTLS gap). Hypotheses (falsified by any failing assertion): L-1 per cell (profile z1 or z3, arm D or C) the late share uses nominal 1.5 R (D) / 2.5 R (C) + 0.75 R like analyze_node_oos.late_share;
L-2 median_shift = median per-site apply time - nominal (s), over non-excluded episodes, None values skipped; L-3 verdict_z: H-Z1 holds iff late share <= 0.02 in all four cells; the cells above 0.02 are listed."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_lossless as al  # noqa: E402


def row(vals, excluded=False):
    return {"excluded": excluded, "withdrawn_plog_s": {str(i): v for i, v in enumerate(vals)}}


def test_l1_l2():
    R = 0.12   # D nominal 0.18, late > 0.27 ; C nominal 0.30, late > 0.39
    rows = [row([0.19] * 10), row([0.19] * 9 + [0.5]), row([9.0] * 10, excluded=True), row([0.19] * 9 + [None])]
    assert al.cell(rows, R, "D")["late_share"] == pytest.approx(1 / 29)
    assert al.cell(rows, R, "D")["median_shift_s"] == pytest.approx(0.19 - 0.18)
    assert al.cell([row([0.35] * 10)], R, "C")["late_share"] == 0.0


def test_l3():
    ok = {("z1", "D"): {"late_share": 0.0}, ("z1", "C"): {"late_share": 0.01}, ("z3", "D"): {"late_share": 0.0}, ("z3", "C"): {"late_share": 0.02}}
    assert al.verdict_z(ok) == {"h_z1": True, "above": []}
    bad = {**ok, ("z1", "C"): {"late_share": 0.08}}
    v = al.verdict_z(bad)
    assert v["h_z1"] is False and v["above"] == [("z1", "C")]
