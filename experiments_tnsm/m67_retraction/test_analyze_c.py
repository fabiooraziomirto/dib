"""Clopper-Pearson and the classification of (c) (hypothesis: exact two-sided 95% CIs match the textbook values to 1e-4; falsification: any assertion failing)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_c as c  # noqa: E402


def test_clopper_pearson_known_values():
    lo, hi = c.clopper_pearson(0, 100)
    assert lo == 0.0 and abs(hi - (1 - 0.025 ** (1 / 100))) < 1e-6          # 0.036216
    lo, hi = c.clopper_pearson(1, 10)
    assert abs(lo - 0.002529) < 1e-4 and abs(hi - 0.445016) < 1e-4
    lo, hi = c.clopper_pearson(5, 20)
    assert abs(lo - 0.08657) < 1e-4 and abs(hi - 0.49105) < 1e-4
    lo, hi = c.clopper_pearson(10, 10)
    assert hi == 1.0 and abs(lo - 0.025 ** (1 / 10)) < 1e-6          # two-sided: (alpha/2)^(1/n) = 0.6915 (0.7411 would be the one-sided 0.05^(1/10))


def test_large_n_runs_and_brackets_the_estimate():
    lo, hi = c.clopper_pearson(14, 2000)
    assert lo < 14 / 2000 < hi and hi - lo < 0.01


def test_classification_entirely_outside_only():
    assert c.classify((0.016, 0.03), (0.004, 0.015)) == "CI entirely outside: falsified"
    assert c.classify((0.0, 0.003), (0.004, 0.015)) == "CI entirely outside: falsified"
    assert c.classify((0.01, 0.02), (0.004, 0.015)) == "CI crosses a bound: inconclusive"
    assert c.classify((0.005, 0.012), (0.004, 0.015)) == "CI entirely inside"


def test_report_on_the_wan_rerun_counts_zero_pending():
    p = Path(__file__).resolve().parent / "wan_20261011" / "b1" / "cells.jsonl"
    cs = c.counts(p)
    assert cs["D"]["x"] == 0 and cs["C"]["x"] == 0 and cs["D"]["n"] == 200 and cs["C"]["n"] == 200
