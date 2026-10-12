"""Confirmatory suite of audit 78. Hypotheses (before the code; falsification = any assertion failing):
 C-1  build_cells_v3: 4 P0 loss cells (75/150 ms x 3/7 %, 60 episodes), 2 P0 p=0 cells (20 episodes), 4 S1 cells (40 episodes, 120 s cap);
 C-2  verdict rules: T-V1 holds iff >= 3 of 4 cells satisfy late +-4 points, slow +-12 points and pending <= 2%; T-V2 iff >= 3 of 4 within +-25%; the model is validated iff T-V0, T-V1, T-V2 all hold.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_v3 as v3  # noqa: E402
import testbed as tb  # noqa: E402


def test_c1_cells():
    cells = tb.build_cells_v3()
    p0 = [c for c in cells if c["policy"] == "P0"]
    s1 = [c for c in cells if c["policy"] == "S1"]
    assert len(p0) == 6 and len(s1) == 4
    assert sorted((c["d_ms"], c["loss_pct"]) for c in p0 if c["loss_pct"] == 0) == [(75, 0), (150, 0)] and all(c["episodes"] == 20 for c in p0 if c["loss_pct"] == 0)
    assert all(c["episodes"] == 60 for c in p0 if c["loss_pct"] > 0)
    assert {(c["d_ms"], c["loss_pct"]) for c in s1} == {(75, 3), (75, 7), (150, 3), (150, 7)}
    assert all(c["episodes"] == 40 and c["max_wait_s"] == 120 for c in s1)


def test_c2_verdicts():
    good = [{"late": 0.01, "slow": 0.05, "pending": 0.0}] * 3 + [{"late": 0.10, "slow": 0.05, "pending": 0.0}]     # 1 of 4 outside the late tolerance
    assert v3.t_v1(good)["holds"] is True
    bad = [{"late": 0.01, "slow": 0.05, "pending": 0.0}] * 2 + [{"late": 0.10, "slow": 0.05, "pending": 0.0}] * 2
    assert v3.t_v1(bad)["holds"] is False
    pend = [{"late": 0.0, "slow": 0.0, "pending": 0.03}] * 4
    assert v3.t_v1(pend)["holds"] is False
    assert v3.t_v2([0.0, 0.1, 0.24, 0.26])["holds"] is True       # 3 of 4 within 25%
    assert v3.t_v2([0.0, 0.3, 0.24, 0.26])["holds"] is False
    assert v3.overall(True, True, True) == "VALIDATO" and v3.overall(True, True, False) == "NON VALIDATO"
