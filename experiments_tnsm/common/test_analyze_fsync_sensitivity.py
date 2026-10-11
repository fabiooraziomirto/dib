"""Tests of analyze_fsync_sensitivity.py on SYNTHETIC cells (definitions: docs/audit/39, committed c3e3777 before any computation).
Hypothesis: each function implements its definition; Falsification: an assertion fails."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_fsync_sensitivity as fs  # noqa: E402


def cell(i, arm="default", n=50, thr=100.0, errors=0, t0=1000.0, disturbed=False):
    return {"cell": i, "mode": arm, "n_workers": n, "rep": i, "disturbed": disturbed, "disturbed_reasons": [], "t_start_unix": t0 + 10 * i,
            "monitor": {"during": {"other_cores": 0.1}},
            "result": {"throughput": thr, "wall_s": 200 / thr, "p50_ms": 5.0, "p95_ms": 9.0, "p99_ms": 50.0, "total_ops": 200, "unexpected_errors": errors}}


def test_spearman_known_values_and_ties():
    assert math.isclose(fs.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
    assert math.isclose(fs.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
    assert fs.spearman([1, 2, 3], [5, 5, 5]) is None                    # no variance in one variable: undefined
    r = fs.spearman([1, 2, 3, 4, 5], [1, 2, 2, 4, 5])                   # ties get mean ranks
    assert 0.95 < r < 1.0


def test_excluded_sets_by_position_and_by_time():
    cs = [cell(i) for i in range(30)]
    assert [c["cell"] for c in fs.excluded(cs, "E5", started_unix=1000.0)] == [0, 1, 2, 3, 4]
    assert len(fs.excluded(cs, "E10", started_unix=1000.0)) == 10 and len(fs.excluded(cs, "E20", started_unix=1000.0)) == 20
    et = fs.excluded(cs, "ET", started_unix=1000.0)                      # t - start < 600 s: cells 0..59 would, here 30 cells at 10 s spacing -> all 30
    assert len(et) == 30
    et2 = fs.excluded([cell(i, t0=1000.0) for i in range(30)], "ET", started_unix=1000.0 - 300.0)   # start 300 s earlier: only cells with t - start < 600
    assert [c["cell"] for c in et2] == list(range(0, 30)) and len(et2) == 30
    far = [cell(0, t0=1000.0), cell(1, t0=1700.0)]
    assert [c["cell"] for c in fs.excluded(far, "ET", started_unix=1000.0)] == [0]       # 700 s after the start: not excluded


def test_group_trend_uses_only_groups_with_enough_cells_and_reports_early_vs_rest():
    cs = [cell(i, thr=100 - i) for i in range(10)] + [cell(10 + i, arm="deploy", n=1, thr=50) for i in range(3)]
    rows = fs.group_trend(cs, min_cells=8, early=5)
    assert [(r["arm"], r["n_workers"]) for r in rows] == [("default", 50)]
    r = rows[0]
    assert r["cells"] == 10 and math.isclose(r["rho_throughput"], -1.0) and r["rho_errors"] is None
    assert r["early_n"] == 5 and r["rest_n"] == 5 and r["early_mean"] > r["rest_mean"]


def test_errors_by_arm_counts_early_and_rest_and_deploy_positions():
    cs = [cell(0, arm="deploy", errors=2), cell(1, arm="deploy"), cell(2, arm="default", errors=1), cell(11, arm="deploy", errors=3), cell(12, arm="default")]
    e = fs.errors_by_arm(cs, early=10)
    assert e["deploy"] == {"early_with_errors": 1, "early_cells": 2, "rest_with_errors": 1, "rest_cells": 1, "positions_with_errors": [0, 11]}
    assert e["default"]["early_with_errors"] == 1 and e["default"]["rest_cells"] == 1


def test_verdict_comparison_marks_changed_when_excluding_cells_flips_the_verdict():
    base = [cell(i, arm="default", n=50, thr=300 + 0.01 * i) for i in range(10)] + [cell(10 + i, arm="default", n=100, thr=300 + 0.01 * i) for i in range(10)]
    cmp = fs.compare_verdicts(base, "E5", started_unix=1000.0, seed=1, resamples=100)
    row = [x for x in cmp if x["id"] == "H-M1" and x["arm"] == "default" and x["subset"] == "all"][0]
    assert row["registered"] is False and row["excluded_set"] is False and row["changed"] is False
    # excluding every cell of the 50-writer group makes H-M1 not evaluable (None): reported as changed, never silently dropped
    cmp2 = fs.compare_verdicts(base, "E10", started_unix=1000.0, seed=1, resamples=100)
    row2 = [x for x in cmp2 if x["id"] == "H-M1" and x["arm"] == "default" and x["subset"] == "all"][0]
    assert row2["excluded_set"] is None and row2["changed"] is True
