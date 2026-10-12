"""Confirmatory suite of audit 80. Hypotheses (before the code; falsification = any assertion failing):
 D-1  build_cells_v4: 6 loss cells (60/120/180 ms x 4/8 %, 60 episodes, P0) + 3 p=0 cells (20 episodes);
 D-2  T-W1 holds iff >= 5 of 6 cells satisfy late +-3 pts, slow +-10 pts, pending <= 2% and no cell exceeds late +-6 or slow +-20; T-W2 counts the cells v3 would have passed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v4 as v4  # noqa: E402
import testbed as tb  # noqa: E402


def test_d1_cells():
    cells = tb.build_cells_v4()
    assert len(cells) == 9 and {c["policy"] for c in cells} == {"P0"}
    loss = [c for c in cells if c["loss_pct"] > 0]
    assert {(c["d_ms"], c["loss_pct"]) for c in loss} == {(d, p) for d in (60, 120, 180) for p in (4, 8)} and all(c["episodes"] == 60 for c in loss)
    assert sorted(c["d_ms"] for c in cells if c["loss_pct"] == 0) == [60, 120, 180] and all(c["episodes"] == 20 for c in cells if c["loss_pct"] == 0)


def test_d2_rules():
    ok = {"late": 0.02, "slow": 0.05, "pending": 0.0}
    off = {"late": 0.04, "slow": 0.05, "pending": 0.0}          # outside 3 but inside 6
    big = {"late": 0.07, "slow": 0.05, "pending": 0.0}          # beyond double
    assert v4.t_w1([ok] * 5 + [off])["holds"] is True
    assert v4.t_w1([ok] * 4 + [off] * 2)["holds"] is False
    assert v4.t_w1([ok] * 5 + [big])["holds"] is False
    assert v4.t_w1([ok] * 6)["holds"] is True
    assert v4.t_w1([{"late": 0.0, "slow": 0.0, "pending": 0.03}] * 6)["holds"] is False
    assert v4.count_pass([{"late": 0.02, "slow": 0.05, "pending": 0.0}, {"late": 0.05, "slow": 0.05, "pending": 0.0}]) == 1
