"""Sequential-vs-parallel suite of the netns testbed (audit 77). Hypotheses (before the code; falsification = any assertion failing):
 S-1  build_cells_s1: 9 cells (d in 50/100/200 x loss 2/5/10 %), policy S1, kind 's1', a 120 s wait cap, the requested episode count;
 S-2  sequentiality: sorted apply times of an episode with 10 sites 0.8 s apart have median gap 0.8; a parallel episode (all at 0.3 s) has gap 0;
 S-3  verdict rules: T-S1 valid iff >= 7/9 within +-25% of the prediction; T-S2 falsified iff any ratio < 2.0; T-S0 falsified iff more than 2 cells have median gap < 0.75 R.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis as an  # noqa: E402
import testbed as tb  # noqa: E402
import analyze_s1 as s1  # noqa: E402


def test_s1_cells():
    cells = tb.build_cells_s1(40)
    assert len(cells) == 9 and {c["policy"] for c in cells} == {"S1"} and {c["kind"] for c in cells} == {"s1"}
    assert {(c["d_ms"], c["loss_pct"]) for c in cells} == {(d, p) for d in (50, 100, 200) for p in (2, 5, 10)}
    assert all(c["episodes"] == 40 and c["max_wait_s"] == 120 for c in cells)


def _ep(times):
    return {"setup_ok": True, "applies": {str(i): t for i, t in enumerate(times)}}


def test_s2_median_gap():
    seq = [_ep([0.3 + 0.8 * i for i in range(10)]) for _ in range(5)]
    par = [_ep([0.3] * 10) for _ in range(5)]
    assert s1.median_gap(seq) == pytest.approx(0.8)
    assert s1.median_gap(par) == pytest.approx(0.0)
    assert s1.median_gap([{"setup_ok": True, "applies": {"0": None}}]) is None


def test_s3_verdicts():
    pred = {i: 1000.0 for i in range(9)}
    ok = {i: 1100.0 for i in range(9)}
    assert s1.t_s1_verdict(ok, pred)["valid"] is True
    bad = {**ok, **{i: 1400.0 for i in range(3)}}                     # 3 cells off by 40%
    assert s1.t_s1_verdict(bad, pred)["valid"] is False
    edge = {**ok, **{i: 1250.0 for i in range(2)}}                    # exactly +25% is within
    assert s1.t_s1_verdict(edge, pred)["valid"] is True
    assert s1.t_s2_verdict([2.8, 4.0, 2.0])["falsified"] is False
    assert s1.t_s2_verdict([2.8, 1.99])["falsified"] is True
    assert s1.t_s0_verdict([0.9, 0.9, 0.2, 0.2, 0.2], R=[0.4] * 5)["falsified"] is True     # 3 cells below 0.75 R = 0.3
    assert s1.t_s0_verdict([0.9, 0.9, 0.2, 0.2, 0.9], R=[0.4] * 5)["falsified"] is False
