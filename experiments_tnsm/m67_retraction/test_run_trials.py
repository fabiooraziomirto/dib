"""run.py --trials N (B2-kill trials per cell; default 10 = the pre-registration of audit 45/99; 20 for the second series of the overnight 30-trial design, audit 99 addendum 2).
Hypotheses (falsified by any failing assertion): T-1 plan(...) without the argument keeps "trials": 10 in every b2kill cell (nothing changes by default); T-2 plan(..., trials=20) sets 20 in every b2kill cell and
does not touch b1 episodes; T-3 the cell list (arms, T, k) is identical with and without the argument."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


def test_t1_default_10():
    cells = r.plan("lan", ["b2kill"], ["D", "C"])
    assert cells and all(c["trials"] == 10 for c in cells)


def test_t2_trials_20_and_b1_untouched():
    cells = r.plan("degraded", ["b1", "b2kill"], ["D"], trials=20)
    assert all(c["trials"] == 20 for c in cells if c["block"] == "b2kill")
    assert all("trials" not in c for c in cells if c["block"] == "b1")


def test_t3_same_cells():
    a = [(c["arm"], c["T"], c["k"]) for c in r.plan("lan", ["b2kill"], ["D", "C"])]
    b = [(c["arm"], c["T"], c["k"]) for c in r.plan("lan", ["b2kill"], ["D", "C"], trials=20)]
    assert a == b
