"""The cost model reproduces the published rows of audit 14 (docs/audit/14_priorita_esperimenti_tnsm.md:277-299).
Hypothesis: fast rows (L = 2.6 ms) and slow rows at lan/wan (L = 1.0 s) to 0.1 s. Falsification: any assertion failing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cost_table as c  # noqa: E402


def test_fast_episode_and_rows():
    assert [round(c.episode_s(p, 0.0026), 2) for p in ("lan", "wan", "degraded")] == [0.56, 1.70, 8.75]
    assert abs(c.trial_s("lan", "D", 5, 1, 0.0026) - 6.3) < 0.1 and abs(c.trial_s("lan", "D", 15, 1, 0.0026) - 6.8) < 0.1
    assert abs(c.trial_s("wan", "D", 5, 1, 0.0026) - 13.4) < 0.1 and abs(c.trial_s("wan", "C", 5, 1, 0.0026) - 13.8) < 0.1
    assert abs(c.trial_s("degraded", "C", 15, 10, 0.0026) - 107.3) < 0.15
    assert abs(c.trial_s("lan", "D", 5, 50, 0.0026) - 33.8) < 0.1
    assert abs(c.table(0.0026)[1] - 2.36) < 0.01


def test_slow_rows_lan_wan():
    assert abs(c.episode_s("lan", 1.0) - 9.5) < 0.05 and abs(c.episode_s("wan", 1.0) - 9.5) < 0.05
    assert abs(c.trial_s("lan", "D", 5, 1, 1.0) - 15.3) < 0.1 and abs(c.trial_s("wan", "C", 15, 10, 1.0) - 107.6) < 0.2
    assert abs(c.trial_s("lan", "D", 5, 50, 1.0) - 480.8) < 0.1


def test_degraded_slow_is_the_known_mismatch():
    # published 11.0 s, model 9.5 s: recorded, not hidden
    assert abs(c.episode_s("degraded", 1.0) - 9.5) < 0.05
