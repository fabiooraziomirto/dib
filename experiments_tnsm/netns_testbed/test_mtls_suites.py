"""Suites of the audit-95 validation (hypotheses fixed in docs/audit/95_prereg_v5_mtls_fuori_campione.md; falsified by any failing assertion):
 S-1  suite "mtls_eq": D=200 ms one way (R=0.4 s), p=5 %, FANOUT 10 (policy P0), 5 fresh blocks of 20 episodes + one T-0 cell at p=0 (20 episodes);
 S-2  suite "mtls_oos": conditions X1..X4 = (d, p) in {(60,6),(100,4),(150,6),(150,8)} (R = 2 d), 10 fresh blocks of 20 episodes each (P0), T-0 cells at p=0 for d in {60,100,150} (20 episodes),
      and sequential cells (S1) for X1 and X2 only: 3 fresh blocks of 20 episodes, max_wait 120;
 S-3  every non-T0 cell of a suite is "fresh" (independent blocks) and carries its condition id; episode totals: eq 100, oos 800 (P0) + 120 (S1);
 S-4  launch refuses to start while a tlc2.TLC process runs or the 1-minute load average is >= 4 (guard_load(procs, load) returns the refusal reason or None).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testbed as tb  # noqa: E402


def test_s1_eq():
    cells = tb.build_cells_mtls_eq()
    main = [c for c in cells if c["kind"] != "T0"]
    assert len(main) == 5 and all(c["d_ms"] == 200 and c["loss_pct"] == 5 and c["policy"] == "P0" and c["episodes"] == 20 and c["fresh"] for c in main)
    t0 = [c for c in cells if c["kind"] == "T0"]
    assert len(t0) == 1 and t0[0]["loss_pct"] == 0 and t0[0]["d_ms"] == 200 and t0[0]["episodes"] == 20


def test_s2_oos():
    cells = tb.build_cells_mtls_oos()
    p0 = [c for c in cells if c["kind"] == "oos" and c["policy"] == "P0"]
    assert sorted({(c["d_ms"], c["loss_pct"], c["cond"]) for c in p0}) == [(60, 6, "X1"), (100, 4, "X2"), (150, 6, "X3"), (150, 8, "X4")]
    assert all(sum(c["episodes"] for c in p0 if c["cond"] == x) == 200 and len([c for c in p0 if c["cond"] == x]) == 10 for x in ("X1", "X2", "X3", "X4"))
    s1 = [c for c in cells if c["policy"] == "S1"]
    assert sorted({c["cond"] for c in s1}) == ["X1", "X2"] and all(c["episodes"] == 20 and c["max_wait_s"] == 120 for c in s1)
    assert sum(1 for c in s1 if c["cond"] == "X1") == 3 and sum(1 for c in s1 if c["cond"] == "X2") == 3
    t0 = [c for c in cells if c["kind"] == "T0"]
    assert sorted(c["d_ms"] for c in t0) == [60, 100, 150] and all(c["loss_pct"] == 0 and c["episodes"] == 20 for c in t0)


def test_s3_fresh_and_totals():
    eq, oos = tb.build_cells_mtls_eq(), tb.build_cells_mtls_oos()
    assert all(c["fresh"] for c in eq + oos if c["kind"] != "T0")
    assert sum(c["episodes"] for c in eq if c["kind"] != "T0") == 100
    assert sum(c["episodes"] for c in oos if c["kind"] == "oos" and c["policy"] == "P0") == 800
    assert sum(c["episodes"] for c in oos if c["policy"] == "S1") == 120


def test_s4_guard():
    assert tb.guard_load(["python3 x.py"], 0.5) is None
    assert "TLC" in tb.guard_load(["java -cp x tlc2.TLC -workers 8"], 0.5)
    assert "load" in tb.guard_load([], 7.0)


def test_s5_stopped_processes_do_not_count():
    """A process in state T (SIGSTOP, the other session pausing its TLC for the validation window) uses no CPU and must not block the start; a running one does."""
    assert tb.proc_is_stopped("1234 (java) T 1 1 1 0 -1 4194304") is True
    assert tb.proc_is_stopped("1234 (java) S 1 1 1 0 -1 4194304") is False
    assert tb.proc_is_stopped("1234 (my (weird) name) T 1 1") is True
