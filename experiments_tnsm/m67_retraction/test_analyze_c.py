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


# ---- revision of 2026-10-11 (before any degraded B1 datum)
import json  # noqa: E402


def _row(t0, pend_sites=0, excluded=False):
    return {"t0": t0, "t_resp": t0 + 0.4, "dispute_rtt_s": 0.4, "excluded": excluded,
            "plog_ack_ts": {str(i): (t0 + 1.0 if i < pend_sites else None) for i in range(10)},
            "pending_left": {str(i): 0 for i in range(10)}}


def test_counts_come_from_the_rows_and_match_the_run_summary_logic():
    rows = [_row(10.0, 1), _row(20.0, 0), _row(30.0, 2, excluded=True), _row(40.0, 0)]
    cs = c.counts_from_cells([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": rows, "summary": {"n_pending_sites_log": 99}}])
    assert cs["D"]["x"] == 1 and cs["D"]["n"] == 30 and cs["D"]["cells"] == {1: (1, 30)}       # the stored summary (99) is NOT used; excluded rows leave x and n
    assert c.row_pending_sites({"pending_left": {"3": 2}, "plog_ack_ts": {"3": None, "4": 1.0}}) == 2      # ack OR left, a site once


def test_second_clause_is_about_disjoint_cis():
    ci_d, ci_c = (0.004, 0.015), (0.001, 0.003)
    assert c.second_clause(ci_d, ci_c, 0.008, 0.002).startswith("FALSIFIED") and "point estimates C 0.00200, D 0.00800" in c.second_clause(ci_d, ci_c, 0.008, 0.002)
    assert c.second_clause((0.004, 0.015), (0.02, 0.06), 0.008, 0.04).startswith("satisfied")
    s = c.second_clause((0.004, 0.015), (0.010, 0.03), 0.008, 0.007)                          # overlapping CIs, C's point estimate BELOW D's: still not falsified
    assert s.startswith("inconclusive") and "NOT above" in s


def test_report_on_a_block_directory_with_overlap_exclusion(tmp_path):
    for g, arm, fo, pend in (("b1_C_f10", "C", 10, 3), ("b1_D_f10", "D", 10, 0)):
        d = tmp_path / g
        d.mkdir()
        rows = [_row(100.0 + 10 * i, pend if i == 0 else 0) for i in range(5)]
        (d / "cells.jsonl").write_text(json.dumps({"cell": 1, "cell_spec": {"arm": arm, "fanout": fo}, "rows": rows, "summary": {}}) + "\n")
        (d / "manifest.json").write_text(json.dumps({"profile": "degraded", "started_utc": "a", "finished_utc": "b", "cells_summary": []}))
    plain = c.report(tmp_path)
    assert "WARNING: exclusion by overlap NOT applied" in plain and "| C | 3 / 50 |" in plain and "| D | 0 / 50 |" in plain
    log = "2026-10-11T11:59:03.585Z netem_watch: containers changed -> applying degraded\n2026-10-11T11:59:04.465Z netem_watch: applied degraded (0.8 s)\n"
    import profile_exclusion as px
    t = px.parse_watch_log(log)[0][0]
    for g in ("b1_C_f10", "b1_D_f10"):                                                       # shift the data so that the FIRST episode of each overlaps the interval
        p = tmp_path / g / "cells.jsonl"
        cell = json.loads(p.read_text())
        for i, r in enumerate(cell["rows"]):
            r["t0"] = t + 0.1 + 10 * i
            r["t_resp"] = r["t0"] + 0.4
            r["plog_ack_ts"] = {k: (r["t0"] + 1.0 if v is not None else None) for k, v in r["plog_ack_ts"].items()}
        p.write_text(json.dumps(cell) + "\n")
    ex = c.report(tmp_path, None, log)
    assert "2 episode(s) excluded" in ex and "| C | 0 / 40 |" in ex and "| D | 0 / 40 |" in ex       # the pending episode of C is excluded with the others: x and n shrink


# ---- tests added to catch two mutations (2026-10-11, before the degraded data)
def test_mutation_second_clause_needs_DISJOINT_cis():
    """Mutation M1 = `ci_c[1] < ci_d[1]` instead of `ci_c[1] < ci_d[0]` (falsify when C's upper bound is merely below D's upper bound). C's CI [0.001, 0.010]
    overlaps D's [0.004, 0.015] (C's upper bound is inside D's CI): NOT falsified."""
    s = c.second_clause((0.004, 0.015), (0.001, 0.010), 0.008, 0.004)
    assert s.startswith("inconclusive"), s
    assert c.second_clause((0.004, 0.015), (0.001, 0.0039999), 0.008, 0.002).startswith("FALSIFIED")      # strictly below D's lower bound
    assert c.second_clause((0.004, 0.015), (0.001, 0.004), 0.008, 0.002).startswith("inconclusive")       # touching: not disjoint


def test_mutation_excluded_episodes_leave_numerator_and_denominator():
    """Mutation M2 = counting excluded rows (ignoring the `excluded` flag, i.e. the overlap exclusion would change nothing)."""
    rows = [_row(10.0, 3, excluded=True), _row(20.0, 0)]
    cs = c.counts_from_cells([{"cell_spec": {"arm": "C", "fanout": 10}, "rows": rows}])
    assert cs["C"]["x"] == 0 and cs["C"]["n"] == 10


def test_episodes_without_dispute_rtt_are_in_neither_x_nor_n_and_are_reported():
    """Declared 2026-10-11 (docstring): a non-excluded episode WITHOUT dispute_rtt_s (no response recorded) is counted in NEITHER the numerator nor the
    denominator, and its number is reported."""
    no_resp = {"t0": 50.0, "excluded": False, "plog_ack_ts": {"0": 51.0, "1": 51.0}, "pending_left": {}}
    rows = [_row(10.0, 1), no_resp, _row(20.0, 0)]
    cs = c.counts_from_cells([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": rows}])
    assert cs["D"]["x"] == 1 and cs["D"]["n"] == 20 and cs["D"]["no_rtt"] == 1
    out = c.report_from_cells([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": rows}])
    assert "without dispute_rtt_s" in out and ": 1" in out.split("without dispute_rtt_s")[1].splitlines()[0]


def test_report_says_when_the_profile_is_not_degraded():
    """(c) is a prediction AT `degraded`: at another profile the classification is printed but is NOT a test of (c) (it printed 'falsified' for C on lan data)."""
    rows = [_row(10.0, 0)]
    cells = [{"cell_spec": {"arm": "C", "fanout": 1}, "rows": rows}]
    assert "NOT a test of (c)" in c.report_from_cells(cells, profile="lan")
    assert "NOT a test of (c)" not in c.report_from_cells(cells, profile="degraded")
    assert "NOT a test of (c)" in c.report_from_cells(cells)                    # profile unknown: said, never assumed


# ---- 10 sites per episode, and the alternative definition when more than 3 episodes per arm lack dispute_rtt_s (2026-10-11, before B1)
import pytest  # noqa: E402


def test_every_counted_episode_has_exactly_ten_sites():
    """n = 10 x episodes presumes 10 sites per episode: assert it instead of assuming it."""
    bad = _row(10.0, 0)
    del bad["plog_ack_ts"]["9"]                                                   # 9 sites in the ack map
    with pytest.raises(ValueError, match="10 sites"):
        c.counts_from_cells([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": [_row(5.0, 0), bad]}])
    bad2 = _row(10.0, 0)
    bad2["pending_left"]["10"] = 0                                                # an 11th site
    with pytest.raises(ValueError, match="10 sites"):
        c.counts_from_cells([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": [bad2]}])
    c.counts_from_cells([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": [_row(5.0, 0)]}])   # a good episode passes
    ex = _row(10.0, 0, excluded=True)
    del ex["plog_ack_ts"]["9"]                                                    # an EXCLUDED malformed episode is not counted, so not asserted
    c.counts_from_cells([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": [ex]}])


def _no_resp(t0):
    return {"t0": t0, "excluded": False, "plog_ack_ts": {str(i): None for i in range(10)}, "pending_left": {str(i): 0 for i in range(10)}}


def test_alternative_definition_is_reported_when_an_arm_has_more_than_three_episodes_without_rtt():
    base = [_row(10.0 * i, 0) for i in range(20)]
    three = [{"cell_spec": {"arm": "D", "fanout": 1}, "rows": base + [_no_resp(900.0 + i) for i in range(3)]}]
    four = [{"cell_spec": {"arm": "D", "fanout": 1}, "rows": base + [_no_resp(900.0 + i) for i in range(4)]}]
    assert "ALTERNATIVE definition" not in c.report_from_cells(three, profile="degraded")                      # 3 is not > 3
    out = c.report_from_cells(four, profile="degraded")
    assert "ALTERNATIVE definition" in out and "0 / 200" in out and "0 / 240" in out                          # declared n = 200; alternative n = 240 (the 4 counted in n)


def test_alternative_definition_flags_a_disagreement_of_classification():
    """D with 2 pending of 10 x 20 = 200 sites under the declared definition (0.015);
    the alternative (n = 240 with 40 more deliveries and the same x) must be reported next to it, and a different classification is said explicitly."""
    rows = [_row(10.0 * i, 1 if i < 3 else 0) for i in range(20)] + [_no_resp(900.0 + i) for i in range(4)]
    cells = [{"cell_spec": {"arm": "D", "fanout": 1}, "rows": rows}]
    out = c.report_from_cells(cells, profile="degraded")
    assert "ALTERNATIVE definition" in out
    main_cls = c.classify(c.clopper_pearson(3, 200), c.INTERVALS["D"])
    alt_cls = c.classify(c.clopper_pearson(3, 240), c.INTERVALS["D"])
    assert ("DEFINITIONS DISAGREE" in out) == (main_cls != alt_cls)


def test_alternative_definition_disagreement_is_flagged_when_it_does_disagree():
    # x = 0 of 10 x 20 = 200 (declared): CI [0; 0.0183] crosses the lower bound 0.004 -> inconclusive; alternative with 75 non-responding episodes counted in n:
    # n = 950, CI upper 0.003876 < 0.004 -> entirely outside -> falsified: the definitions disagree and the report must say so.
    rows = [_row(10.0 * i, 0) for i in range(20)] + [_no_resp(2000.0 + i) for i in range(75)]
    out = c.report_from_cells([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": rows}], profile="degraded")
    m = c.classify(c.clopper_pearson(0, 200), c.INTERVALS["D"])
    a = c.classify(c.clopper_pearson(0, 950), c.INTERVALS["D"])
    assert m != a, (m, a)                                                      # the scenario is chosen so that the definitions disagree
    assert "DEFINITIONS DISAGREE" in out and "0 / 950" in out
