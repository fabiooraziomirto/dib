"""Manifest of every block records the service settings that decide how an experiment must be read (audit 90 sez. 4). Hypotheses (falsified by any failing assertion):
 M-1  service_settings(groups) returns {"reconcile_interval_s": sorted distinct T of the cells, "suspension_quorum": 1 and "quorum_source": ...} for groups keyed (arm, fanout, T);
 M-2  with DIB_DIST_SUSPENSION_QUORUM=2 in the generator's environment the quorum is still reported as 1 (run.py never passes it to the containers) and the note says so: the manifest must not claim a setting the cluster did not receive;
 M-3  T = 0 (no periodic reconcile) is flagged: reconcile_unbounded_window True (audit 90: without T > 0 the window of a lost event has no bound).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


def test_m1():
    s = r.service_settings([(("D", 10, 5), []), (("C", 1, 5), []), (("D", 1, 15), [])])
    assert s["reconcile_interval_s"] == [5, 15] and s["suspension_quorum"] == 1 and "default" in s["quorum_source"] and s["reconcile_unbounded_window"] is False


def test_m2(monkeypatch):
    monkeypatch.setenv("DIB_DIST_SUSPENSION_QUORUM", "2")
    s = r.service_settings([(("D", 10, 5), [])])
    assert s["suspension_quorum"] == 1 and "not passed" in s["quorum_source"]


def test_m3():
    assert r.service_settings([(("D", 10, 0), [])])["reconcile_unbounded_window"] is True
