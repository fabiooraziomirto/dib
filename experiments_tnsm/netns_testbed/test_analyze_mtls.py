"""analyze_mtls.py applies the criteria of docs/audit/95 (fixed before data). Hypotheses (falsified by any failing assertion):
 A-1  verdict(): H-V0 per condition |D - predD| <= 0.04; H-V1 per interpretable condition |C - v5| <= 0.04; H-V2 |mean(C - v5)| <= 0.02 and mean(C - v4) > 0.02 over interpretable conditions;
 A-2  a condition whose D control fails H-V0 is NOT interpretable: it is excluded from H-V1/H-V2 and listed;
 A-3  H-V3: eq D within 0.04 of 0.176 and eq C within 0.05 of 0.309;
 A-4  outcome(): the paper wording class follows the table of audit 95: supports (all four) / coherent_not_preferred (V1 ok, V2 not) / not_confirmed (V1 or V3 falsified) / inconclusive (H-V0 fails in >= 2 conditions).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_mtls as am  # noqa: E402


def meas(c_vals, d_vals=None):
    d = d_vals or {"X1": 0.217, "X2": 0.150, "X3": 0.210, "X4": 0.265}
    return {x: {"C": c_vals[x], "D": d[x]} for x in c_vals}


V5 = {"X1": 0.348, "X2": 0.248, "X3": 0.319, "X4": 0.388}
V4 = {"X1": 0.307, "X2": 0.217, "X3": 0.288, "X4": 0.353}


def test_a1_supports():
    v = am.verdict(meas(V5))
    assert v["h_v0"] and v["h_v1"] and v["interpretable"] == ["X1", "X2", "X3", "X4"]
    assert v["h_v2"]                # measured == v5: eps5 = 0 and eps4 = v5 - v4 = ~0.03 > 0.02
    v = am.verdict(meas({x: V5[x] + 0.001 for x in V5}))
    assert v["h_v2"]


def test_a1_v4_like_data_not_preferred():
    v = am.verdict(meas(V4))
    assert v["h_v1"] is True and v["h_v2"] is False          # within 0.04 of v5 everywhere but eps4 = 0 -> v5 not preferred


def test_a1_v1_falsified():
    v = am.verdict(meas({**V5, "X4": V5["X4"] + 0.05}))
    assert v["h_v1"] is False


def test_a2_uninterpretable_condition():
    v = am.verdict(meas(V5, {"X1": 0.217, "X2": 0.150, "X3": 0.210, "X4": 0.40}))
    assert v["interpretable"] == ["X1", "X2", "X3"] and v["uninterpretable"] == ["X4"] and v["h_v0"] is False


def test_a3_eq():
    assert am.eq_verdict(0.17, 0.30) == {"h_v3a": True, "h_v3b": True, "h_v3": True}
    assert am.eq_verdict(0.17, 0.37)["h_v3b"] is False and am.eq_verdict(0.23, 0.30)["h_v3a"] is False


def test_a4_outcome():
    assert am.outcome(True, {"h_v0": True, "h_v1": True, "h_v2": True, "uninterpretable": []}) == "supports"
    assert am.outcome(True, {"h_v0": True, "h_v1": True, "h_v2": False, "uninterpretable": []}) == "coherent_not_preferred"
    assert am.outcome(True, {"h_v0": True, "h_v1": False, "h_v2": False, "uninterpretable": []}) == "not_confirmed"
    assert am.outcome(False, {"h_v0": True, "h_v1": True, "h_v2": True, "uninterpretable": []}) == "not_confirmed"
    assert am.outcome(True, {"h_v0": False, "h_v1": True, "h_v2": True, "uninterpretable": ["X1", "X4"]}) == "inconclusive"
