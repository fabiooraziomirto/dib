"""Tests of analyze_b2k.py (audit 45). Hypotheses (before the module; falsification = any assertion failing):
 K-1  per cell (profile, arm, T, k): trials not excluded; (d-kill) falsified iff the CI lower bound of the median convergence_s > the cell's bound_s
      (inconclusive iff median > bound with CI crossing; else not falsified); a trial that never converged (convergence_s None) counts as a violation of
      (e) and is NOT dropped from the median silently: the cell reports n_converged and n_never;
 K-2  (e) is violated by a trial with violation_over_bound True or final_all_monitor_only False; a single violation falsifies (e) globally;
      I1-I3 are NOT checked beyond final_all_monitor_only and the report says so;
 K-3  T15 - T5: median difference with bootstrap CI per (profile, arm, k), DESCRIPTIVE: no verdict (decision Q9);
 K-4  excluded trials are counted by cause, never replaced.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "m67_retraction"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_b2k as k2  # noqa: E402


def trial(conv, viol=False, monitor_only=True, excluded=False, cause=None):
    r = {"trial": 0, "k": 1, "excluded": excluded, "convergence_s": conv, "violation_over_bound": viol, "final_all_monitor_only": monitor_only}
    if cause:
        r["excluded_reason"] = cause
    return r


def test_cell_verdict_three_cases():
    far = [trial(5.0 + i * 0.01) for i in range(10)]
    near = [trial(1.0 + i * 0.01) for i in range(10)]
    mixed = [trial(1.0 if i < 5 else 3.0) for i in range(10)]   # median 2.0 > bound 1.5 but the CI reaches 1.0
    assert k2.cell_summary(far, 2.0)["d_kill"] == "falsified"
    assert k2.cell_summary(near, 2.0)["d_kill"] == "not falsified"
    assert k2.cell_summary(mixed, 1.5)["d_kill"] == "inconclusive"


def test_never_converged_counted_not_dropped():
    rows = [trial(1.0)] * 8 + [trial(None, viol=True)] * 2
    s = k2.cell_summary(rows, 2.0)
    assert s["n_never"] == 2 and s["n_converged"] == 8 and s["e_violations"] == 2


def test_e_violations():
    assert k2.cell_summary([trial(1.0, monitor_only=False)] * 3, 2.0)["e_violations"] == 3
    assert k2.cell_summary([trial(9.0, viol=True)], 2.0)["e_violations"] == 1
    assert k2.cell_summary([trial(1.0)] * 5, 2.0)["e_violations"] == 0
    assert k2.global_e([{"e_violations": 0}, {"e_violations": 0}]) == "not falsified"
    assert k2.global_e([{"e_violations": 0}, {"e_violations": 1}]) == "falsified"


def test_excluded_counted_by_cause():
    rows = [trial(1.0)] * 4 + [trial(None, excluded=True, cause="queues_not_empty_at_start")] * 2 + [trial(None, excluded=True, cause="transport_error")]
    s = k2.cell_summary(rows, 2.0)
    assert s["n"] == 4 and s["excluded_by_cause"] == {"queues_not_empty_at_start": 2, "transport_error": 1}


def test_t_difference_is_descriptive():
    t5 = [trial(1.0 + 0.01 * i) for i in range(10)]
    t15 = [trial(2.0 + 0.01 * i) for i in range(10)]
    d = k2.t_difference(t15, t5)
    assert d["diff_s"] == pytest.approx(1.0, abs=0.02) and "verdict" not in d and d["lo"] <= d["diff_s"] <= d["hi"]
