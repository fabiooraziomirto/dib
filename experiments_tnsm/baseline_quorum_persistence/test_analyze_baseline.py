"""Baseline B(m, tau) 'quorum + persistence, no score' (audit 40, items 1, 3, 4, 5).

Hypotheses (declared before running; synthetic rows, no real data):
  T1 admission needs |S_e| >= m, active_day_ratio >= tau and an eligible class, all three;
  T2 the decision does not depend on alpha, beta, theta or on the 0.7/0.3 split (they are not parameters);
  T3 the key table counts days and sites over the SOURCES only, as score_keys does (receiver excluded);
  T4 tau_match picks the grid tau whose count is closest to the target, ties to the smaller tau;
  T5 r_B(m) = sum_{k >= m} hist[k] / trials, from the histogram format of k_hist.json;
  T6 the verdicts follow the thresholds of audit 40 s.4 (H-B1 majority of receivers; H-B2 > 0.02; H-B3 per point).
Falsification: any assertion failing. Mutations to check that the tests bite: quorum '>=' -> '>',
persistence '>=' -> '>', class filter dropped, tie-break to the larger tau, H-B2 threshold 0.02 -> 0.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "code" / "scripts"))
import analyze_baseline as ab  # noqa: E402
from moniotr_cross_lab import Aggregate  # noqa: E402

D = [date(2019, 4, i) for i in range(1, 9)]          # 8 device days


def test_admit_requires_all_three_conditions():
    assert ab.admit(2, 0.5, True, m=2, tau=0.5)                 # equality on both thresholds admits
    assert not ab.admit(1, 0.9, True, m=2, tau=0.0)             # quorum
    assert not ab.admit(3, 0.49, True, m=2, tau=0.5)            # persistence
    assert not ab.admit(3, 0.9, False, m=2, tau=0.0)            # class
    assert ab.admit(1, 0.0, True, m=1, tau=0.0)


def test_admit_has_no_score_parameters():
    import inspect
    names = set(inspect.signature(ab.admit).parameters)
    assert names == {"n_sites", "active_day_ratio", "eligible", "m", "tau"}


def _data():
    a = Aggregate()
    dev = "cam"
    eligible = (dev, "pool.ntp.org", "ntp", 123)
    other = (dev, "192.0.2.1", "tcp", 9999)
    for site, days in (("A", D[:4]), ("B", D[2:6]), ("R", D)):
        a.device_sites[dev].add(site)
        for d in days:
            a.site_device_days[(site, dev)].add(d)
    for key, rep in ((eligible, {"A": D[:2], "B": D[2:4], "R": D}), (other, {"A": D[:4], "B": D[:4]})):
        for site, days in rep.items():
            a.endpoints[key].add(site)
            for d in days:
                a.site_endpoint_days[(site, key)].add(d)
    return a, eligible, other


def test_key_table_counts_over_sources_only():
    a, eligible, other = _data()
    t = ab.key_table(a, {"A", "B"}, ["cam"])
    n, adr, ok = t[eligible]
    assert n == 2                       # R reports it too but is not a source
    assert abs(adr - 4 / 6) < 1e-12     # endpoint days 1..4 over device days of A and B (1..6): R's days ignored
    assert ok is True and t[other][2] is False


def test_select_by_quorum_persistence_class():
    a, eligible, other = _data()
    t = ab.key_table(a, {"A", "B"}, ["cam"])
    assert ab.select(t, m=2, tau=0.0) == {eligible}              # other is not eligible
    assert ab.select(t, m=2, tau=4 / 6) == {eligible}
    assert ab.select(t, m=2, tau=0.67) == set()
    assert ab.select(t, m=3, tau=0.0) == set()


def test_tau_match_closest_count_ties_to_smaller_tau():
    table = {("d", str(i), "tcp", 1): (2, i / 10, True) for i in range(1, 11)}   # adr 0.1 .. 1.0
    grid = [i / 100 for i in range(101)]
    # target 5: count(tau) = #{adr >= tau}; 5 candidates for tau in (0.5, 0.6]; the smallest tau on the grid is 0.51
    tau, n = ab.tau_match(table, 2, 5, grid)
    assert n == 5 and tau == 0.51
    # target 4.5 is not integer-valued: use 5 and 4 equidistant (target 4.5) -> ties go to the smaller tau (5 candidates)
    tau, n = ab.tau_match(table, 2, 4.5, grid)
    assert n == 5 and tau == 0.51
    tau, n = ab.tau_match(table, 2, 100, grid)
    assert n == 10 and tau == 0.0


def test_rate_from_histogram():
    hist = {"0": 19047, "1": 941, "2": 12}
    assert ab.rate_from_hist(hist, 20000, 1) == (953, 953 / 20000)
    assert ab.rate_from_hist(hist, 20000, 2) == (12, 12 / 20000)
    assert ab.rate_from_hist(hist, 20000, 3) == (0, 0.0)


def test_verdicts_follow_registered_thresholds():
    prec = lambda dib, base: [{"prec_dib": d, "prec_base": b} for d, b in zip(dib, base)]   # noqa: E731
    assert ab.verdict_hb1(prec([.8, .8, .5], [.7, .7, .6])) == "not falsified"   # DIB better in 2 of 3
    assert ab.verdict_hb1(prec([.8, .5, .5], [.7, .7, .6])) == "falsified"       # DIB <= baseline in 2 of 3
    assert ab.verdict_hb1(prec([.7, .5, .5], [.7, .7, .6])) == "falsified"       # equality counts as not better
    rec = lambda dib, base: [{"rec_dib": d, "rec_base": b} for d, b in zip(dib, base)]       # noqa: E731
    assert ab.verdict_hb2(rec([.1, .1, .1], [.12, .1, .1])) == "not falsified"   # exactly 0.02 is not 'more than'
    assert ab.verdict_hb2(rec([.1, .1, .1], [.1201, .1, .1])) == "falsified"
    # H-B3 as registered: tested at points with p* < 1e-3; falsified if r_B(2) <= r_DIB at one of them
    pts = [{"p_star": 5e-4, "r_B": 0.01, "r_dib": 0.001}, {"p_star": 2e-3, "r_B": 0.0, "r_dib": 0.0}]
    assert ab.verdict_hb3(pts) == "not falsified"                                 # second point is outside the registered set
    pts.append({"p_star": 5e-4, "r_B": 0.001, "r_dib": 0.001})
    assert ab.verdict_hb3(pts) == "falsified"                                     # equality: r_B <= r_DIB
    assert ab.verdict_hb3([{"p_star": 2e-3, "r_B": 0.0, "r_dib": 0.1}]) == "not falsified"
    # the reading 'powered points' (p* >= 1e-3) is available as a sensitivity via the predicate
    assert ab.verdict_hb3([{"p_star": 2e-3, "r_B": 0.0, "r_dib": 0.1}], testable=lambda p: p >= 1e-3) == "falsified"
