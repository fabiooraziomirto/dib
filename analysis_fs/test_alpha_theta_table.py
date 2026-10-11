"""Audit 42: descriptive (alpha, theta) table. No hypothesis, no falsification criterion; tests check the exact arithmetic
columns (expected values written in audit 42 s.3 before any computation) and the coverage rules of audit 42 s.4.

Run: PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -m pytest analysis_fs/test_alpha_theta_table.py -q -p no:cacheprovider
Module under test: analysis_fs/alpha_theta_table.py.
"""
import sys
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alpha_theta_table as T  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PAIRS = [(F(6, 10), F(65, 100)), (F(7, 10), F(65, 100)), (F(6, 10), F(7, 10)), (F(55, 100), F(6, 10))]


def test_arithmetic_columns_match_audit42():
    exp = {PAIRS[0]: (F(5, 12), F(5, 7), F(7, 60)), PAIRS[1]: (F(1, 2), F(1), F(1, 5)),
           PAIRS[2]: (F(1, 2), F(1), F(1, 5)), PAIRS[3]: (F(3, 11), F(3, 8), F(-3, 110))}
    for (a, th), (fstar, r, margin) in exp.items():
        assert (T.fstar(a, th), T.ratio(a, th), T.margin(a, th)) == (fstar, r, margin)


def test_pair_not_satisfying_criterion_is_flagged():
    assert [T.satisfies_criterion(a, th) for a, th in PAIRS] == [True, True, True, False]


def test_coverage_rules():
    cov = {p: T.coverage(*p) for p in PAIRS}
    assert cov[PAIRS[0]] == ("alpha_sweep", "theta_sweep")
    assert cov[PAIRS[1]] == ("alpha_sweep",)
    assert cov[PAIRS[2]] == ("theta_sweep",)
    assert cov[PAIRS[3]] == ()


def test_uncovered_pair_has_no_recall():
    rows = T.build_rows(ROOT / "results" / "sensitivity")
    r = [x for x in rows if x["alpha"] == F(55, 100) and x["theta"] == F(6, 10)]
    assert r and all(x["recall"] == "non disponibile" for x in r)
    assert {x["corpus"] for x in r} == {"moniotr", "yourthings"}


def test_baseline_pair_rows_agree_between_sweeps():
    """(0.6, 0.65) is in both sweeps: same admitted count (same config, same scoring)."""
    rows = [x for x in T.build_rows(ROOT / "results" / "sensitivity") if x["alpha"] == F(6, 10) and x["theta"] == F(65, 100)]
    for corpus in ("moniotr", "yourthings"):
        vals = {x["admitted"] for x in rows if x["corpus"] == corpus}
        assert len(vals) == 1, (corpus, vals)
