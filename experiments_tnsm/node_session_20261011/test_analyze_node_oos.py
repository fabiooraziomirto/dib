"""analyze_node_oos.py: criteria of docs/audit/107 (fixed before data) for the v5 validation on the REAL deployment. Hypotheses (falsified by any failing assertion):
 N-1  late_share: a per-site P-log value is late iff it is > nominal + 0.75 R with nominal = 1.5 R (arm D) or 2.5 R (arm C); None values and excluded episodes are skipped; (share, lo, hi) bootstrap over episodes, deterministic;
 N-2  verdict(): H-N0 per condition |D - predD| <= 0.04; H-N1 per interpretable condition |C - v5| <= 0.05; H-N2 mean absolute error of v5 < that of v4 AND |mean(C - v5)| <= 0.04;
 N-3  a condition whose D control fails is NOT interpretable (excluded from N1/N2); >= 2 uninterpretable -> outcome inconclusive;
 N-4  outcome(): supports (N1 and N2) / coherent_not_preferred (N1 only) / not_confirmed (N1 fails) / inconclusive.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_node_oos as an  # noqa: E402


def row(vals, excluded=False):
    return {"excluded": excluded, "withdrawn_plog_s": {str(i): v for i, v in enumerate(vals)}}


def test_n1_late_share():
    R = 0.2     # D: nominal 0.3, late > 0.45 ; C: nominal 0.5, late > 0.65
    rows = [row([0.3] * 10), row([0.3] * 9 + [0.5]), row([9.0] * 10, excluded=True), row([0.3] * 9 + [None])]
    s, lo, hi = an.late_share(rows, R, "D")
    assert s == pytest.approx(1 / 29) and lo <= s <= hi
    s, _, _ = an.late_share([row([0.6] * 5 + [0.7] * 5)], R, "C")
    assert s == pytest.approx(0.5)
    assert an.late_share(rows, R, "D") == an.late_share(rows, R, "D")


PRED = an.PRED


def meas(c, d=None):
    d = d or {x: PRED[x]["D"] for x in PRED}
    return {x: {"C": c[x], "D": d[x]} for x in c}


def test_n2_verdict_supports():
    v = an.verdict(meas({x: PRED[x]["v5"] for x in PRED}))
    assert v["h_n0"] and v["h_n1"] and v["h_n2"] and v["interpretable"] == ["X1", "X2", "X3", "X4"]


def test_n2_v4_like_not_preferred():
    v = an.verdict(meas({x: PRED[x]["v4"] for x in PRED}))
    assert v["h_n2"] is False


def test_n3_uninterpretable():
    d = {x: PRED[x]["D"] for x in PRED}
    d["X4"] = 0.5
    v = an.verdict(meas({x: PRED[x]["v5"] for x in PRED}, d))
    assert v["uninterpretable"] == ["X4"] and v["h_n0"] is False
    d["X3"] = 0.5
    assert an.outcome(an.verdict(meas({x: PRED[x]["v5"] for x in PRED}, d))) == "inconclusive"


def test_n4_outcome():
    ok = an.verdict(meas({x: PRED[x]["v5"] for x in PRED}))
    assert an.outcome(ok) == "supports"
    assert an.outcome({**ok, "h_n2": False}) == "coherent_not_preferred"
    assert an.outcome({**ok, "h_n1": False, "h_n2": False}) == "not_confirmed"
