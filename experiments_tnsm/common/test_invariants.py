"""common/invariants.py (audit 90 sez. 5). The FSM session's four tests, plus the failure modes below. Hypotheses (falsified by any failing assertion):
 I-1..I-4  as written in audit 90 (clean trial, stale commit, monitor-only caught up during an episode, the other checks);
 I-5  all_checks on a trial with TWO different violations returns both, in a list (no short circuit);
 I-6  a site whose /state was 404 (absent from rows) is never reported as a violation by itself.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from invariants import (all_checks, caught_up_is_coherent, confinement, export_safe, no_active_without_commit_after_restore,  # noqa: E402
                        no_transient_left, veto_preserved)

S = {7: {"status": "active", "fanout_seq": 2}}


def row(state, la=2, origin=None):
    return {"state": state, "origin": origin, "last_applied_seq": la}


def test_clean_trial_has_no_violation():
    rows = {(0, 7): row("active"), (1, 7): row("monitor-only"), (3, 7): row("revoked", origin="local")}
    ev = [{"t": 1, "op": "dispute", "site": None, "score_id": 7, "status": 200},
          {"t": 2, "op": "restore", "site": None, "score_id": 7, "status": 200},
          {"t": 3, "op": "commit", "site": 0, "score_id": 7, "status": 200},
          {"t": 0.5, "op": "local_revoke", "site": 3, "score_id": 7, "status": 200}]
    assert all_checks(rows, S, {}, ev) == []


def test_stale_commit_is_caught():
    ev = [{"t": 1, "op": "commit", "site": 0, "score_id": 7, "status": 200}, {"t": 2, "op": "restore", "site": None, "score_id": 7, "status": 200}]
    assert no_active_without_commit_after_restore({(0, 7): row("active")}, ev)[0][0] == "I3_StaleActiveAfterRestore"


def test_monitor_only_caught_up_during_episode_is_caught():
    assert caught_up_is_coherent({(0, 7): row("monitor-only", la=3)}, {7: {"status": "disputed", "fanout_seq": 3}})[0][0] == "CaughtUpIsCoherent"


def test_other_checks():
    sc = {7: {"status": "disputed", "fanout_seq": 1}}
    assert export_safe({(0, 7): row("active", la=0)}, sc, {(0, 7): 0}) == [("ExportSafe", 0, 7)]
    assert export_safe({(0, 7): row("active", la=0)}, sc, {(0, 7): 1}) == []
    assert no_transient_left({(0, 7): row("committing")}) == [("TransientLeft", 0, 7, "committing")]
    ev = [{"t": 1, "op": "local_revoke", "site": 0, "score_id": 7, "status": 200}]
    assert veto_preserved({(0, 7): row("monitor-only")}, ev)[0][0] == "I3_VetoLost"
    assert confinement({(1, 7): row("revoked", origin="local")}, ev)[0][0] == "I2_LocalOriginWithoutLocalRevoke"


def test_i5_two_violations_both_reported():
    rows = {(0, 7): row("staging", la=1), (1, 7): row("active", la=0)}
    sc = {7: {"status": "disputed", "fanout_seq": 1}}
    out = all_checks(rows, sc, {}, [])
    kinds = {v[0] for v in out}
    assert {"TransientLeft", "ExportSafe", "I1_ActiveWithoutCommit"} <= kinds


def test_i6_absent_site_is_not_a_violation():
    assert all_checks({}, S, {}, []) == []
