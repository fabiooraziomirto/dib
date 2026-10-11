"""Tests of analyze_b5.py (audit 46 + 50). Hypotheses (written before the module; falsification = any assertion failing):
 B-1  E[F] = p + p^2 + p^3; the verdict-1 p is the UPPER end of the registered range (D 0.226, C 0.401), the lower ends are descriptive (audit 50 s.1);
 B-2  threshold = n_RTT*R*(x10 at FANOUT 1) + E[F]*1000 ms + 3 x reference; physical bound = n_RTT*R*(x10 at FANOUT 1) (audit 50 s.2-3), n_RTT D 2, C 3;
 B-3  verdict 1: falsified iff CI lower > threshold; inconclusive iff median > threshold and CI crosses; else not falsified;
      verdict 2: base model falsified iff CI upper < physical bound; the two are independent;
 B-4  completed episodes only: excluded rows, rows without dispute_rtt_s and rows with any pending (pending_after_response, pending_left, plog_ack_ts) are out;
 B-5  global: (a') falsified iff >= 1 cell with verdict 1; base model falsified iff >= 1 cell with verdict 2; counts k/n; cells not evaluable (R-gp) are
      reported apart and are neither falsified nor 'not falsified'.
"""
import sys
from pathlib import Path

import pytest

M67 = Path(__file__).resolve().parent.parent / "m67_retraction"
sys.path.insert(0, str(M67))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_b5 as b5  # noqa: E402


def test_expected_failures():
    assert b5.expected_failures(0.5) == pytest.approx(0.5 + 0.25 + 0.125)
    assert b5.P_HI == {"D": 0.226, "C": 0.401} and b5.P_LO == {"D": 0.185, "C": 0.302}


@pytest.mark.parametrize("arm,n", [("D", 2), ("C", 3)])
def test_physical_and_threshold(arm, n):
    R = 0.2
    assert b5.physical_ms(arm, 10, R) == pytest.approx(1000 * n * R)
    assert b5.physical_ms(arm, 1, R) == pytest.approx(1000 * n * R * 10)
    p = b5.P_HI[arm]
    ef = p + p ** 2 + p ** 3
    assert b5.threshold_ms(arm, 10, R, 50.0, p) == pytest.approx(1000 * n * R + 1000 * ef + 150.0)
    assert b5.threshold_ms(arm, 1, R, 50.0, p) == pytest.approx(1000 * n * R * 10 + 1000 * ef + 150.0)


def test_verdicts():
    thr, phys = 1000.0, 600.0
    assert b5.verdicts((1500, 1100, 1900, 40), thr, phys) == ("falsified", "ok")
    assert b5.verdicts((1200, 900, 1500, 40), thr, phys) == ("inconclusive", "ok")
    assert b5.verdicts((800, 700, 900, 40), thr, phys) == ("not falsified", "ok")
    assert b5.verdicts((500, 450, 590, 40), thr, phys) == ("not falsified", "base model falsified")
    assert b5.verdicts((500, 450, 600, 40), thr, phys) == ("not falsified", "ok")        # hi == bound: not below
    assert b5.verdicts((1050, 1000, 1100, 40), thr, phys)[0] == "inconclusive"          # lo == threshold is not above; median > threshold


def test_completed_values_filters():
    ok = {"dispute_rtt_s": 1.0, "withdrawn_plog_s": {str(i): 1.0 for i in range(10)}, "pending_after_response": {}, "pending_left": {}, "plog_ack_ts": {}}
    rows = [ok,
            {**ok, "excluded": True},
            {k: v for k, v in ok.items() if k != "dispute_rtt_s"},
            {**ok, "pending_left": {"3": 1}},
            {**ok, "pending_after_response": {"2": 2}},
            {**ok, "plog_ack_ts": {"4": 12.3}}]
    assert b5.completed_values(rows, "rtt") == [1000.0]
    assert len(b5.completed_values(rows, "last")) == 1


def test_global_verdict():
    cells = [{"v1": "falsified", "v2": "ok"}, {"v1": "not falsified", "v2": "ok"}, {"v1": "inconclusive", "v2": "base model falsified"},
             {"v1": "not evaluable", "v2": "not evaluable"}]
    g = b5.global_verdict(cells)
    assert g["a_prime"] == "falsified" and g["a_prime_k"] == (1, 3) and g["base"] == "base model falsified" and g["base_k"] == (1, 3)
    assert g["not_evaluable"] == 1
    g2 = b5.global_verdict([{"v1": "not falsified", "v2": "ok"}] * 4)
    assert g2["a_prime"] == "not falsified" and g2["base"] == "ok" and g2["a_prime_k"] == (0, 4)
