"""Tests of analyze_m1_arms.py on SYNTHETIC cells. The criteria are those registered in experiments_tnsm/m1_single_node/run.py:12-30 (committed
c23d1e3 / a90b27a, before the night run): H-M1 per arm (falsified if the CI of the mean throughput at 100 writers lies entirely above the CI at 50),
H-M1b (deploy: no cell with unexpected errors), H-M1c (completed-ops throughput at 100: falsified if the deploy CI lies entirely below the default CI).
Reason for the script: analyze.py looks for mode 'threads' in M1, but the night cells carry mode = arm ('default'/'deploy'), so its built-in H-M1
verdict does not fire and H-M1b/H-M1c are not implemented there. Falsification of these tests: any assertion fails."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_m1_arms as am  # noqa: E402


def cell(arm, n, thr, errors=0, p99=50.0, disturbed=False, ops=200 * 1):
    return {"mode": arm, "n_workers": n, "disturbed": disturbed, "disturbed_reasons": [], "monitor": {"during": {"other_cores": 0.1}},
            "result": {"throughput": thr, "wall_s": ops / thr, "p50_ms": 5.0, "p95_ms": 9.0, "p99_ms": p99, "total_ops": ops, "unexpected_errors": errors}}


def many(arm, n, thr, k=10, **kw):
    return [cell(arm, n, thr + 0.01 * i, **kw) for i in range(k)]


def test_h_m1_saturation_not_falsified_and_falsified():
    flat = many("default", 50, 300) + many("default", 100, 300)
    rising = many("default", 50, 100) + many("default", 100, 300)
    v_flat = am.verdicts(flat, seed=1, resamples=200)
    v_rise = am.verdicts(rising, seed=1, resamples=200)
    assert [x for x in v_flat if x["id"] == "H-M1" and x["arm"] == "default" and x["subset"] == "all"][0]["falsified"] is False
    assert [x for x in v_rise if x["id"] == "H-M1" and x["arm"] == "default" and x["subset"] == "all"][0]["falsified"] is True


def test_h_m1b_one_deploy_cell_with_errors_falsifies_and_default_errors_do_not():
    clean = many("deploy", 100, 300)
    v = am.verdicts(clean + many("default", 100, 300, errors=5), seed=1, resamples=100)
    assert [x for x in v if x["id"] == "H-M1b" and x["subset"] == "all"][0]["falsified"] is False
    dirty = clean[:-1] + [cell("deploy", 100, 300, errors=1)]
    v = am.verdicts(dirty, seed=1, resamples=100)
    b = [x for x in v if x["id"] == "H-M1b" and x["subset"] == "all"][0]
    assert b["falsified"] is True and b["cells_with_errors"] == 1


def test_h_m1c_deploy_entirely_below_default_falsifies():
    low = many("default", 100, 300) + many("deploy", 100, 100)
    same = many("default", 100, 300) + many("deploy", 100, 300)
    f = lambda cs: [x for x in am.verdicts(cs, seed=1, resamples=200) if x["id"] == "H-M1c" and x["subset"] == "all"][0]["falsified"]  # noqa: E731
    assert f(low) is True and f(same) is False


def test_filtered_subset_drops_disturbed_cells_and_reports_count():
    cs = many("default", 50, 300) + many("default", 100, 300) + [cell("default", 100, 900, disturbed=True)]
    v = [x for x in am.verdicts(cs, seed=1, resamples=100) if x["id"] == "H-M1" and x["arm"] == "default"]
    assert {x["subset"] for x in v} == {"all", "filtered"}
    assert [x for x in v if x["subset"] == "filtered"][0]["cells_used"] == 20 and [x for x in v if x["subset"] == "all"][0]["cells_used"] == 21


def test_censoring_report_counts_only_cells_with_errors_and_p99_at_the_pool_timeout():
    cs = [cell("default", 100, 30, errors=3, p99=30001.0), cell("default", 100, 30, errors=0, p99=30001.0), cell("default", 100, 300, errors=2, p99=500.0),
          cell("deploy", 100, 300)]
    rep = {(r["arm"], r["n_workers"]): r for r in am.censoring_report(cs)}
    assert rep[("default", 100)]["cells"] == 3 and rep[("default", 100)]["censored"] == 1 and rep[("default", 100)]["with_errors"] == 2
    assert rep[("deploy", 100)]["censored"] == 0 and rep[("default", 100)]["p99_uncensored_cells"] == 2


def spread(arm, n, base, k=10, step=20):
    return [cell(arm, n, base + step * i) for i in range(k)]


def test_h_m1_requires_ci100_lower_above_ci50_UPPER_not_lower():
    """CI at 100 entirely above the LOWER bound of CI at 50 but inside its range: overlapping CIs -> not falsified (survived the first version)."""
    cs = spread("default", 50, 100) + [cell("default", 100, 215 + 0.01 * i) for i in range(10)]
    v = [x for x in am.verdicts(cs, seed=1, resamples=400) if x["id"] == "H-M1" and x["subset"] == "all"][0]
    assert v["ci100"][1] > v["ci50"][1] and v["ci100"][1] <= v["ci50"][2] and v["falsified"] is False


def test_h_m1c_requires_entirely_below_not_just_a_lower_mean():
    """Deploy mean lower than default but the CIs overlap -> not falsified (survived the first version)."""
    cs = spread("default", 100, 100) + spread("deploy", 100, 90)
    v = [x for x in am.verdicts(cs, seed=1, resamples=400) if x["id"] == "H-M1c" and x["subset"] == "all"][0]
    assert v["ci_deploy"][0] < v["ci_default"][0] and v["falsified"] is False
