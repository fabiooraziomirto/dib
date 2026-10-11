"""Rule (a) with the adjacent-lan reference (analyze_b1.rule_a / lan_reference). Hypotheses: R-a1 threshold = 10*n_RTT*R + 3 x reference
(night wan C/1: 4800 + 3 x 106 = 5118 ms; observed 5471 -> falsified only if the CI lower bound is above it); R-a2 the verdict is
"inconclusive" when the median is above the threshold but the CI crosses it, "not falsified" otherwise; R-a3 the HIGHER lan median is used.
Falsification: any assertion failing."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_b1 as a  # noqa: E402


def test_rule_a_verdicts():
    r = a.rule_a((5471.0, 5300.0, 5600.0, 9), 4800.0, 106.0)
    assert abs(r["threshold_ms"] - 5118.0) < 1e-9 and abs(r["excess_ms"] - 353.0) < 1e-9 and r["verdict"] == "falsified"
    assert a.rule_a((5471.0, 5000.0, 5600.0, 9), 4800.0, 106.0)["verdict"] == "inconclusive"
    assert a.rule_a((5100.0, 4900.0, 5300.0, 9), 4800.0, 106.0)["verdict"] == "not falsified"


def _cells(tmp, name, med_ms):
    d = tmp / name
    d.mkdir()
    rows = [{"excluded": False, "dispute_rtt_s": (med_ms + 3) / 1000, "withdrawn_plog_s": {str(i): med_ms / 1000 for i in range(10)},
             "pending_after_response": {str(i): 0 for i in range(10)}, "pending_left": {str(i): 0 for i in range(10)},
             "plog_ack_ts": {str(i): None for i in range(10)}} for _ in range(5)]
    (d / "cells.jsonl").write_text(json.dumps({"cell_spec": {"arm": "D", "fanout": 1}, "rows": rows}) + "\n")
    return d


def test_reference_uses_the_higher_median(tmp_path):
    ref = a.lan_reference([_cells(tmp_path, "before", 48.0), _cells(tmp_path, "after", 67.0)], random.Random(1))
    assert abs(ref[("D", 1, "last")][0] - 67.0) < 1e-9 and abs(ref[("D", 1, "rtt")][0] - 70.0) < 1e-9


def test_gp_reused_false_makes_prediction_a_not_evaluable():
    """Rule fixed 2026-10-11 before any `degraded` B1 datum (docstring of analyze_b1.py): at a non-lan profile a cell whose group-start
    generator_path_ms has reused_ok FALSE gets no verdict for (a) ('not evaluable'), its numbers stay in the report, it is not excluded and not re-run;
    fresh_ok false alone stays informational; at `lan` the flags are ignored; reused_ok None/True: normal."""
    cell = lambda gp: {"profile_timing": {"generator_path_ms": gp}}  # noqa: E731
    bad = cell({"reused_ms": 944.4, "fresh_ms": 403.6, "reused_ok": False, "fresh_ok": True})
    assert a.gp_not_evaluable(bad, "degraded") == "reused 944.4 ms outside +-20% of d (reused_ok false)"
    assert a.gp_not_evaluable(bad, "wan") and a.gp_not_evaluable(bad, "regional")
    assert a.gp_not_evaluable(bad, "lan") is None                                        # lan: flags carry no meaning (audit 22)
    assert a.gp_not_evaluable(cell({"reused_ms": 202.0, "fresh_ms": 600.0, "reused_ok": True, "fresh_ok": False}), "degraded") is None   # fresh alone: informational
    assert a.gp_not_evaluable(cell({"reused_ms": 202.0, "fresh_ms": None, "reused_ok": True, "fresh_ok": None}), "degraded") is None
    assert a.gp_not_evaluable({"profile_timing": {}}, "degraded") is None and a.gp_not_evaluable({}, "degraded") is None   # no data: not invented
    assert a.verdict_text({"verdict": "falsified"}, bad, "degraded") .startswith("not evaluable")
    assert a.verdict_text({"verdict": "falsified"}, cell({"reused_ok": True}), "degraded") == "falsified"
