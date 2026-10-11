"""Secondary analysis of 5.3b (audit 41 s.2 and the descriptive set comparison asked after the confirmatory run). POST-HOC.

Hypotheses (declared before running; toy data only, no real data):
  T1 delta_counts(C_DIB, C_B) returns |C_DIB|, |C_B|, |intersection|, |symmetric difference| as plain counts;
  T2 the paired bootstrap of all-equal differences (all zeros) has CI [0, 0] by construction, and the verdict is
     'non falsificata; nessuna differenza osservata, nessun potere' when n >= 10;
  T3 the paired bootstrap of a known difference (d around +0.10 on 18 units) has a 95% percentile CI that contains
     the sample mean and lies entirely above 0 -> 'falsificata'; around -0.10 -> 'non falsificata';
  T4 with n < 10 the verdict is descriptive, never a test (audit 41 s.2);
  T5 same seed -> same CI (B = 10 000, seed 20261012, percentile indices 250 and 9749);
  T6 the per-device differences are d = recall(B) - recall(DIB) and units with an empty reference are excluded.
Falsification: any assertion failing. Mutations to check that the tests bite: swap the sign of d, drop the
n < 10 rule, symmetric difference -> union, lo > 0 -> lo >= 0.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_secondary as sec  # noqa: E402


def test_delta_counts_on_toy_sets():
    a = {"k1", "k2", "k3", "k4"}
    b = {"k3", "k4", "k5"}
    assert sec.delta_counts(a, b) == {"dib": 4, "base": 3, "inter": 2, "symdiff": 3}
    assert sec.delta_counts(a, a) == {"dib": 4, "base": 4, "inter": 4, "symdiff": 0}
    assert sec.delta_counts(set(), b) == {"dib": 0, "base": 3, "inter": 0, "symdiff": 3}


def test_bootstrap_all_zero_is_degenerate_interval():
    diffs = [0.0] * 18
    assert sec.paired_bootstrap(diffs) == (0.0, 0.0)
    assert sec.secondary_verdict(diffs, 0.0, 0.0) == "non falsificata; nessuna differenza osservata, nessun potere"


def test_bootstrap_known_difference_contains_mean_and_sets_verdict():
    base = [0.02, -0.01, 0.03, 0.0, 0.01, -0.02, 0.02, 0.01, -0.01, 0.0, 0.03, -0.02, 0.01, 0.0, 0.02, -0.01, 0.0, 0.01]
    up = [0.10 + x for x in base]
    lo, hi = sec.paired_bootstrap(up)
    mean = sum(up) / len(up)
    assert lo < mean < hi and lo > 0 and hi < 0.2
    assert sec.secondary_verdict(up, lo, hi) == "falsificata"
    down = [-0.10 + x for x in base]
    lo, hi = sec.paired_bootstrap(down)
    assert lo < sum(down) / len(down) < hi and hi < 0
    assert sec.secondary_verdict(down, lo, hi) == "non falsificata"
    mixed = base
    lo, hi = sec.paired_bootstrap(mixed)
    assert lo <= 0 <= hi and sec.secondary_verdict(mixed, lo, hi) == "non falsificata"


def test_small_n_is_descriptive_not_a_test():
    d = [0.1] * 6
    lo, hi = sec.paired_bootstrap(d)
    assert "descrittivo" in sec.secondary_verdict(d, lo, hi) and "nessun verdetto" in sec.secondary_verdict(d, lo, hi)
    assert "descrittivo" in sec.secondary_verdict([0.0] * 9, 0.0, 0.0)
    assert "descrittivo" not in sec.secondary_verdict([0.0] * 10, 0.0, 0.0)


def test_bootstrap_is_reproducible_and_uses_registered_percentiles():
    d = [0.05, 0.0, -0.02, 0.1, 0.03, 0.0, 0.07, -0.01, 0.02, 0.04, 0.0, 0.06]
    assert sec.paired_bootstrap(d) == sec.paired_bootstrap(d)
    assert sec.paired_bootstrap(d, seed=1) != sec.paired_bootstrap(d, seed=2)
    assert (sec.B, sec.SEED, sec.LO_IDX, sec.HI_IDX) == (10000, 20261012, 250, 9749)


def test_unit_differences_sign_and_exclusion():
    # unit = (device, |observed|, recall_dib, recall_base)
    units = [("a", 5, 0.2, 0.3), ("b", 0, 0.0, 0.0), ("c", 4, 0.5, 0.4)]
    d = sec.unit_differences(units)
    assert [round(x, 12) for x in d] == [0.1, -0.1]              # d = base - dib; empty reference excluded


def test_lower_bound_exactly_zero_is_not_falsified():
    d = [0.0] * 9 + [0.1] * 9
    assert sec.secondary_verdict(d, 0.0, 0.1) == "non falsificata"      # 'entirely above 0' needs lo > 0
    assert sec.secondary_verdict(d, 1e-9, 0.1) == "falsificata"
