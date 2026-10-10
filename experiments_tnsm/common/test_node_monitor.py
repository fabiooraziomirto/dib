"""node_monitor extensions (audit 18, user decision 2026-10-10; written before the code).

Hypotheses: M-1 pids_in_cgroups(ids, proc_root) returns exactly the pids whose
/proc/<pid>/cgroup mentions one of the (full) container ids, and nothing for other pids;
M-2 with those pids excluded, window() attributes their CPU to no category (neither
other_cores nor kernel_cores) while another process still counts as other_cores;
M-3 idle_window() returns a window dict with the same keys as short_window().
Falsification: any assertion failing.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import node_monitor as nm  # noqa: E402


def _fake_proc(root, entries):
    for pid, cg in entries.items():
        d = root / str(pid)
        d.mkdir()
        (d / "cgroup").write_text(cg)


def test_m1_pids_in_cgroups(tmp_path):
    cid = "a" * 64
    other = "b" * 64
    _fake_proc(tmp_path, {
        101: f"0::/system.slice/docker-{cid}.scope\n",
        102: f"0::/system.slice/docker-{cid}.scope/sub\n",
        103: f"0::/system.slice/docker-{other}.scope\n",
        104: "0::/user.slice/session-1.scope\n",
    })
    (tmp_path / "self").mkdir()           # non-numeric entries are ignored
    assert nm.pids_in_cgroups([cid], str(tmp_path)) == {101, 102}
    assert nm.pids_in_cgroups([cid, other], str(tmp_path)) == {101, 102, 103}
    assert nm.pids_in_cgroups([], str(tmp_path)) == set()


def test_m2_excluded_pids_counted_nowhere():
    a = nm.Snapshot(nm.own_pids())
    b = nm.Snapshot(nm.own_pids())
    b.procs = dict(b.procs)
    a.procs = dict(a.procs)
    a.procs[900001] = ("dibsvc", 0, False)
    b.procs[900001] = ("dibsvc", 500, False)     # 5 s of CPU by an excluded process
    a.procs[900002] = ("noise", 0, False)
    b.procs[900002] = ("noise", 100, False)
    b.t = a.t + 10
    w_all = nm.window(a, b)
    assert abs(w_all["other_cores"] - (600 / nm.CLK / 10)) < 1e-3
    for snap in (a, b):
        snap.procs = {p: v for p, v in snap.procs.items() if p != 900001}
    w = nm.window(a, b)
    assert abs(w["other_cores"] - (100 / nm.CLK / 10)) < 1e-3 and w["kernel_cores"] == w["kernel_cores"]


def test_m3_idle_window_keys():
    w = nm.idle_window(0.2)
    assert set(w) == set(nm.short_window(0.1))
