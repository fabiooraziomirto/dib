"""M6/M7 driver helpers (audit 18 s.1.4-1.6; written with run.py, offline only: the live part is NOT
integration-tested). Hypotheses: R-1 hard_limit_s / client_timeout_s reproduce the audit 18 table
(lan: 90/120 s hard limit at FANOUT 1, 9/12 at FANOUT 10, timeout = 2H; extreme: 30/30 and 3/3);
R-2 d_run_max, b_online, bound_kill give the frozen bounds (degraded with mTLS: D_run_max 5.6 s,
B_online(T=5) 11.1 s; extreme without mTLS B_online(5) 14.1 s); R-3 parse_post_lines extracts the
apply_fanout/ack lines of a real `docker logs -t` sample with the daemon timestamp, and
first_after picks the first 200 at or after t0; R-4 rtt_matches accepts the lan/wan/mixed
expectations and rejects a profile that was not applied; R-5 --dry-run prints the plan and calls
neither docker nor the network; R-6 plan() sizes match the design (B1: 2 FANOUT x arms; B2-kill:
arms x T x k).
Falsification: any assertion failing."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


def test_r1_timeouts():
    assert r.hard_limit_s("lan", "D", 1) == 90 and r.hard_limit_s("lan", "C", 1) == 120
    assert r.hard_limit_s("lan", "D", 10) == 9 and r.hard_limit_s("lan", "C", 10) == 12
    assert r.client_timeout_s("degraded", "D", 1) == 180 and r.client_timeout_s("degraded", "C", 10) == 24
    assert r.hard_limit_s("extreme", "D", 1) == 30 and r.hard_limit_s("extreme", "C", 10) == 3
    assert r.client_timeout_s("extreme", "C", 1) == 60
    assert r.hard_limit_s("lan", "D", 10, l_dns=5.0) == 15.0     # max(H, 3*L_dns)


def test_r2_bounds():
    assert abs(r.d_run_max("degraded", "C") - 5.6) < 1e-9 and abs(r.d_run_max("degraded", "D") - 4.4) < 1e-9
    assert abs(r.b_online("degraded", "C", 5) - 11.1) < 1e-9 and abs(r.b_online("lan", "D", 5) - 10.5) < 1e-9
    assert abs(r.b_online("extreme", "D", 5) - 14.1) < 1e-9 and abs(r.b_online("extreme", "C", 5) - 17.4) < 1e-9
    assert abs(r.bound_kill("lan", "D", 5) - (1.5 + 0.5 + 5.0)) < 1e-9


SAMPLE = (
    '2026-10-10T20:04:11.123456789Z INFO:     192.168.100.170:39666 - "POST /query HTTP/1.1" 200 OK\n'
    '2026-10-10T20:04:11.250000000Z INFO:     172.18.0.2:41000 - "POST /apply_fanout HTTP/1.1" 200 OK\n'
    '2026-10-10T20:04:12Z INFO:     172.18.0.2:41002 - "POST /apply_fanout HTTP/1.1" 500 Internal Server Error\n'
    '2026-10-10T20:04:15.500000000Z INFO:     172.18.0.3:41004 - "POST /pending/site-3/ack HTTP/1.1" 200 OK\n'
    'not a log line\n')


def test_r3_parse_and_first_after():
    ap = r.parse_post_lines(SAMPLE, "/apply_fanout")
    assert [s for _t, _p, s in ap] == [200, 500]
    t0 = r._ts("2026-10-10T20:04:11", ".2")
    assert abs(r.first_after(ap, t0) - r._ts("2026-10-10T20:04:11", ".25")) < 1e-6
    assert r.first_after(ap, t0 + 0.1) is None                       # the later line is a 500
    ack = r.parse_post_lines(SAMPLE, "/pending/")
    assert len(ack) == 1 and ack[0][1] == "/pending/site-3/ack"


def test_r4_rtt_matches():
    assert r.rtt_matches("lan", {i: 0.4 for i in range(10)})[0]
    assert r.rtt_matches("wan", {i: 161.0 for i in range(10)})[0]
    assert not r.rtt_matches("wan", {i: 0.4 for i in range(10)})[0]         # profile not applied
    mixed = {**{i: 0.5 for i in range(5)}, **{i: 81.0 for i in range(5, 10)}}
    assert r.rtt_matches("mixed", mixed)[0]
    assert not r.rtt_matches("mixed", {i: 81.0 for i in range(10)})[0]


def test_r5_dry_run_touches_nothing(monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("subprocess called in --dry-run")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(sys, "argv", ["run.py", "--block", "b1,b2kill", "--profile", "degraded", "--tree", "/x", "--out", "/nonexistent", "--dry-run"])
    assert r.main() == 0
    out = capsys.readouterr().out
    assert "DRY RUN profile=degraded" in out and "nothing is applied" in out
    assert not Path("/nonexistent").exists()


def test_r6_plan_sizes():
    assert len(r.plan("lan", ["b1"], ["D", "C"])) == 4                       # 2 arms x 2 FANOUT
    assert len(r.plan("lan", ["b2kill"], ["D", "C"])) == 2 * 2 * 3           # arms x T x k in {1,10,50}
    assert len(r.plan("degraded", ["b2kill"], ["D"])) == 1 * 2 * 2           # k in {1,10}
    assert [c["episodes"] for c in r.plan("degraded", ["b1"], ["D"])] == [50, 50]
    assert len(r.plan("degraded", ["tcpdump"], ["D", "C"])) == 2


def test_r7_group_cells_reuse_cluster():
    import random
    cells = r.plan("lan", ["b1", "b2kill"], ["D", "C"])
    groups = r.group_cells(cells, random.Random(1))
    assert sum(len(g) for _, g in groups) == len(cells)
    keys = [k for k, _ in groups]
    # B1: 2 arms x FANOUT {1, 10} at T = 5; B2-kill: 2 arms x T {5, 15} at FANOUT 10 (k loops inside the same cluster);
    # B1 (FANOUT 10, T = 5) and B2-kill (T = 5) share a key -> 6 cluster creations, not 8
    assert len(keys) == len(set(keys)) == 6
    for key, g in groups:
        assert all((c["arm"], c["fanout"], c["T"]) == key for c in g)
    assert sorted(len(g) for _, g in groups) == [1, 1, 3, 3, 4, 4]
