"""Tests of analyze_exploratory_degraded.py (definitions: docs/audit/35 section B, committed before any computation) on SYNTHETIC rows only.
Hypothesis: each function implements its definition exactly, including the corner cases of the definition (pending site, censored episode,
unmeasurable episode, non-monotone order, undefined estimate). Falsification: any assertion below fails."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_exploratory_degraded as ex  # noqa: E402


def row(t0=100.0, apply=None, ack=None, left=None, excluded=False, rtt=True, **kw):
    apply = apply if apply is not None else {i: t0 + 1.0 + i for i in range(10)}
    r = {"episode": 0, "excluded": excluded, "t0": t0, "t_resp": t0 + 20.0,
         "plog_apply_ts": {str(i): v for i, v in apply.items()},
         "plog_ack_ts": {str(i): (ack or {}).get(i) for i in range(10)},
         "pending_left": {str(i): (left or {}).get(i, 0) for i in range(10)},
         "pending_after_response": {str(i): 0 for i in range(10)},
         "withdrawn_plog_s": {str(i): (None if v is None else v - t0) for i, v in apply.items()}}
    if rtt:
        r["dispute_rtt_s"] = 20.0
    r.update(kw)
    return r


def test_b1_c_sensitivity_worst_cases_and_classification_change():
    """Synthetic baseline 0/960 (CI [0, 0.0038], entirely below 0.004: falsified): with 10 more deliveries of which 10 pending, 10/970 has a CI
    [0.005, 0.019] that crosses 0.015: the classification changes; with 0 pending (0/970) it does not."""
    out = ex.c_sensitivity_d(x=0, n=960, x_c=32, n_c=960, extra_n=10)
    assert [s["label"] for s in out] == ["S0", "S_a", "S_b"]
    assert [(s["x"], s["n"]) for s in out] == [(0, 960), (0, 970), (10, 970)]
    assert out[0]["class"].startswith("CI entirely outside") and out[1]["class"].startswith("CI entirely outside")
    assert out[2]["class"] == "CI crosses a bound: inconclusive"
    assert [s["changed"] for s in out] == [False, False, True]
    real = ex.c_sensitivity_d(x=9, n=960, x_c=32, n_c=960, extra_n=10)
    assert [(s["x"], s["n"]) for s in real] == [(9, 960), (9, 970), (19, 970)] and real[0]["class"] == "CI crosses a bound: inconclusive"


def test_b2_last_site_uses_ack_for_pending_and_apply_otherwise():
    r = row(apply={i: 101.0 + i for i in range(10)}, ack={4: 130.0})
    v = ex.last_site_all([r])
    assert v["values"] == [30.0] and v["unmeasurable"] == 0 and v["undrained"] == 0


def test_b2_unmeasurable_undrained_and_excluded():
    miss = row(apply={**{i: 101.0 + i for i in range(10)}, 3: None})                  # no apply, not pending
    und = row(left={2: 1})                                                            # pending at the deadline, no ack
    exc = row(excluded=True)
    norsp = row(rtt=False)
    v = ex.last_site_all([miss, und, exc, norsp, row()])
    assert v["values"] == [10.0] and v["unmeasurable"] == 1 and v["undrained"] == 1


def test_b3_gaps_f1_positions_and_order_violation():
    ok = row(apply={i: 101.0 + 0.8 * i for i in range(10)})
    bad = row(apply={**{i: 101.0 + 0.8 * i for i in range(10)}, 3: 150.0})            # site 3 later than 4..9: id order not monotone
    pend = row(ack={5: 120.0})
    g = ex.gaps_f1([ok, bad, pend])
    assert g["n_used"] == 1 and g["order_violations"] == 1 and g["with_pending"] == 1
    assert math.isclose(g["by_pos"][0][0], 1.0) and all(math.isclose(g["by_pos"][k][0], 0.8) for k in range(1, 10))
    assert sum(g["hist"].values()) == 9


def test_b3_f10_max_and_above_base():
    r1 = row(apply={i: 101.0 for i in range(10)})
    r2 = row(apply={**{i: 101.0 for i in range(10)}, 7: 103.5, 8: 101.2})            # one site 2.5 s above, one 0.2 s above (not counted)
    m = ex.f10_stats([r1, r2])
    assert m["max_values"] == [1.0, 3.5]
    assert math.isclose(m["base"], 1.0)
    assert m["sites_total"] == 20 and m["sites_above"] == 1 and m["per_episode_above"] == {0: 1, 1: 1}


def test_b4_pending_path_estimate_and_bonline():
    r = row(t0=100.0, apply={**{i: 101.0 + i for i in range(10)}, 6: None}, ack={6: 125.0})
    p = ex.pending_sites([r], fanout=1, b_online=10.5)
    s = p["sites"][0]
    assert s["u"] == 25.0 and s["e"] == 125.0 - 106.0                                  # predecessor (site 5) applied at t0 + 6
    assert p["n_exceed_u"] == 1 and p["n_exceed_e"] == 1
    r2 = row(t0=100.0, apply={**{i: 101.0 + i for i in range(10)}, 6: None, 7: None}, ack={7: 110.0})   # predecessor 6 has no apply: not estimable
    q = ex.pending_sites([r2], fanout=1, b_online=10.5)
    assert q["sites"][0]["e"] is None and q["n_estimable"] == 0 and q["n_exceed_u"] == 0
    z = ex.pending_sites([row(ack={0: 112.0})], fanout=1, b_online=10.5)
    assert z["sites"][0]["e"] == 112.0 - 100.0                                         # site 0: estimate starts at t0


def test_b4_f10_has_no_estimate():
    p = ex.pending_sites([row(ack={2: 130.0})], fanout=10, b_online=10.5)
    assert p["sites"][0]["e"] is None and p["n_exceed_u"] == 1 and p["n_estimable"] == 0


def test_b5_retry_arithmetic_closed_form_and_monte_carlo():
    a = ex.retry_arith(q=0.008)
    p = 0.008 ** (1 / 3)
    assert math.isclose(a["p"], p)
    assert math.isclose(a["ef"], p + p ** 2 + p ** 3)
    assert math.isclose(a["e_failed_f1"], 10 * (p + p ** 2 + p ** 3))
    pmf = [1 - p, p * (1 - p), p ** 2 * (1 - p), p ** 3]
    cdf = [sum(pmf[:k + 1]) for k in range(4)]
    em = sum(k * (cdf[k] ** 10 - (cdf[k - 1] ** 10 if k else 0.0)) for k in range(4))
    assert math.isclose(a["e_max_f10"], em)
    assert abs(ex.monte_carlo(p, n=100000, seed=1)["e_max_f10"] - em) < 0.03        # statistical check, loose tolerance
    assert ex.retry_arith(q=0.0)["e_failed_f1"] == 0.0


def _cell(arm, fanout, rows):
    return {"cell_spec": {"arm": arm, "fanout": fanout}, "rows": rows, "summary": {"plog_acceptable_rule_10pct": True}}


def test_b6_rows_use_the_shared_generator_of_analyze_b1():
    """B6 CIs must be those analyze_b1.py prints: one random.Random(SEED) shared by the cells in (arm, fanout) order, per cell first
    med_ci(dispute-rtt) then med_ci(last-site). A fresh generator per cell (the first version) gives different CIs for the second cell."""
    import random
    import analyze_b1 as ab
    mk = lambda base: [row(t0=100.0 + k, apply={i: 100.0 + k + base + 0.1 * ((i * 7 + k) % 5) for i in range(10)}) for k in range(12)]  # noqa: E731
    cells = [_cell("D", 1, mk(1.0)), _cell("C", 1, mk(2.0))]                           # given out of order: sorted to C/1, D/1
    got = ex.summary_rows(cells)
    rng = random.Random(ab.SEED)
    exp = {}
    for c in sorted(cells, key=lambda c: (c["cell_spec"]["arm"], c["cell_spec"]["fanout"])):
        rows = c["rows"]
        ab.med_ci([1000 * r["dispute_rtt_s"] for r in rows if not r.get("excluded") and "dispute_rtt_s" in r], rng)
        exp[(c["cell_spec"]["arm"], c["cell_spec"]["fanout"])] = ab.med_ci(ab.last_site(rows), rng)
    assert [g["median"] for g in got] == [exp[("C", 1)], exp[("D", 1)]]


def test_b6_row_excludes_pending_episodes_and_counts():
    ok = row()
    pend = row(ack={2: 118.0})
    exc = row(excluded=True)
    t = ex.summary_rows([_cell("C", 1, [ok, pend, exc])])[0]
    assert t["n_last"] == 1 and t["x"] == 1 and t["n"] == 20 and t["excluded"] == 1 and t["arm"] == "C" and t["fanout"] == 1
