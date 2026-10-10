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


def _ep(rtt, plog_s, pending=None, d_ack=None, t0=100.0):
    row = {"dispute_rtt_s": rtt, "t0": t0, "pending_after_response": pending or {i: 0 for i in range(10)},
           "withdrawn_plog_s": {i: v for i, v in enumerate(plog_s)}, "plog_ack_ts": {}}
    if d_ack:
        row["plog_ack_ts"] = {i: t0 + d_ack for i in range(10)}
    return row


def test_r8_summarize_rows_agreement_bias_and_acceptance():
    ok = [_ep(0.0100, [0.002 + 0.0007 * i for i in range(10)]) for _ in range(3)]       # last site 0.0083 s, response 0.0100 s
    s = r.summarize_rows(ok, "lan", plog_p95_ms=2.5)
    assert abs(s["median_direct_plog_s"] - 0.0083) < 1e-9 and s["n_direct"] == 3
    assert abs(s["plog_minus_response_gap_ms"]["median"] - 1.7) < 1e-6
    assert s["plog_rtt_agree"] is True                                  # |gap| 1.7 ms <= 3 ms
    assert abs(s["plog_acceptance_ratio"] - 0.0025 / 0.0083) < 1e-9 and s["plog_acceptable_rule_10pct"] is False
    assert s["dispute_rtt_bias_ratio"] == 0.0 and s["client_timeouts"] == 0
    bad = [_ep(0.0200, [0.001] * 10)]                                   # gap 19 ms: the two measures disagree
    assert r.summarize_rows(bad, "lan")["plog_rtt_agree"] is False
    wan = r.summarize_rows([_ep(0.5, [0.2] * 10)], "wan")
    assert abs(wan["dispute_rtt_bias_ratio"] - 0.08 / 0.5) < 1e-9       # d / median(dispute-rtt)
    pend = {i: (1 if i == 3 else 0) for i in range(10)}
    sp = r.summarize_rows([_ep(5.0, [0.2] * 10, pending=pend, d_ack=6.0)], "degraded")
    assert abs(sp["pending_bias_ratio"] - (0.2 + 0.05) / 6.0) < 1e-9 and sp["pending_bias_flag_gt10pct"] is False
    ex = r.summarize_rows([{"excluded": True, "client_timeout": "x"}] + ok, "lan")
    assert ex["excluded"] == 1 and ex["client_timeouts"] == 1 and ex["n_direct"] == 3


def test_r9_generator_load_flags():
    low = r.generator_load([{"proc_cores": 0.1, "host_busy_pct": 2.0} for _ in range(5)])
    assert low["near_saturation"] is False and abs(low["gen_proc_cores_mean"] - 0.1) < 1e-9
    high = r.generator_load([{"proc_cores": 0.9, "host_busy_pct": 10.0}] * 3)
    assert high["near_saturation"] is True


def test_r10_plan_overrides_and_event_log(tmp_path, monkeypatch, capsys):
    assert [c["fanout"] for c in r.plan("lan", ["b1"], ["D"], [10], 3)] == [10]
    assert r.plan("lan", ["b1"], ["D"], [10], 3)[0]["episodes"] == 3
    monkeypatch.setattr(sys, "argv", ["run.py", "--record-event", "applied", "--profile", "wan", "--out", str(tmp_path), "--note", "watcher started"])
    assert r.main() == 0
    ev = json.loads((tmp_path / "profile_events.jsonl").read_text().splitlines()[0])
    assert ev["event"] == "applied" and ev["profile"] == "wan" and "communicated by the user" in ev["source"]


def test_r11_watch_log_and_restart_bias():
    """A4: the watcher log (ms timestamps) joined to a site restart gives the delay between `compose start` and the netem
    re-application, and says whether the site's first reconcile pull (evidence access log) could have left unshaped."""
    text = (
        "2026-10-10T10:00:00.100Z netem_watch: profile=wan, polling every 0.1s (Ctrl-C to stop and clean)\n"
        "2026-10-10T10:00:00.300Z netem_watch: containers changed -> applying wan\n"
        "2026-10-10T10:00:00.900Z netem_watch: applied wan (0.600 s)\n"
        "2026-10-10T10:00:30.050Z netem_watch: containers changed -> applying wan\n"
        "2026-10-10T10:00:30.250Z netem_watch: applied wan (0.200 s)\n")
    ev = r.parse_watch_log(text)
    assert len(ev) == 2 and abs(ev[1]["t_applied"] - ev[1]["t_changed"] - 0.2) < 1e-6
    t_start = ev[1]["t_changed"] - 0.04            # `compose start` returned, the watcher noticed 40 ms later
    b = r.restart_netem_bias(t_start, ev, t_first_reconcile=t_start + 0.1)
    assert abs(b["netem_applied_after_start_s"] - 0.24) < 1e-6
    assert b["first_reconcile_before_netem"] is True and abs(b["first_reconcile_after_start_s"] - 0.1) < 1e-6
    b2 = r.restart_netem_bias(t_start, ev, t_first_reconcile=t_start + 0.9)
    assert b2["first_reconcile_before_netem"] is False
    assert r.restart_netem_bias(t_start, [], None)["netem_applied_after_start_s"] is None      # no watcher log: undeclared
    assert r.restart_netem_bias(t_start, ev, None)["first_reconcile_before_netem"] is None
    get = ('2026-10-10T10:00:30.350000000Z INFO:     10.0.0.5:4242 - "GET /pending/site-3 HTTP/1.1" 200 OK\n'
           '2026-10-10T10:00:31.350000000Z INFO:     10.0.0.5:4243 - "POST /pending/site-3/ack HTTP/1.1" 200 OK\n')
    got = r.parse_access_lines(get, "GET", "/pending/site-3")
    assert len(got) == 1 and got[0][1] == "/pending/site-3"
    assert r.parse_post_lines(get, "/pending/site-3/ack")[0][2] == 200


def test_r12_rtt_tolerance_plus_minus_20_percent():
    assert r.rtt_matches("degraded", {i: 401.0 for i in range(10)})[0]
    assert r.rtt_matches("degraded", {i: 321.0 for i in range(10)})[0]
    assert not r.rtt_matches("degraded", {i: 318.0 for i in range(10)})[0]
    one_syn_retransmit = {i: 401.0 for i in range(10)}
    one_syn_retransmit[4] = 1401.0                      # median of 3 hit twice: the probe fails and is retried, not an error
    assert not r.rtt_matches("degraded", one_syn_retransmit)[0]
    assert not r.rtt_matches("degraded", {i: 161.0 for i in range(10)})[0]     # wan applied instead of degraded


def test_r13_generator_path_is_d_not_2d():
    """User check A (2026-10-10): the generator (root namespace, no netem egress) reaches a container with the REQUEST leg
    unshaped; only the response leg crosses the container's qdisc. On a reused connection the path RTT is d; on a fresh
    connection the userland docker-proxy first dials the container (SYN-ACK delayed by d): ~2d. evidence<->site is 2d.
    In `mixed` evidence has no netem, so the generator->evidence path is ~0."""
    assert r.gen_path_d("wan") == 0.080 and r.gen_path_d("degraded") == 0.200 and r.gen_path_d("lan") == 0.0
    assert r.gen_path_d("mixed") == 0.0
    ok = r.generator_path_matches("wan", {"reused_ms": 81.0, "fresh_ms": 162.0}, mtls=False)
    assert ok == {"reused_ok": True, "fresh_ok": True}
    bad = r.generator_path_matches("wan", {"reused_ms": 161.0, "fresh_ms": 162.0}, mtls=False)   # 2d on a reused connection would be wrong
    assert bad["reused_ok"] is False and bad["fresh_ok"] is True
    assert r.generator_path_matches("wan", {"reused_ms": 81.0, "fresh_ms": 400.0}, mtls=True)["fresh_ok"] is None   # TLS fresh: no expectation
    assert r.generator_path_matches("mixed", {"reused_ms": 0.5, "fresh_ms": 1.0}, mtls=False)["reused_ok"] is True
    # the dispute-rtt bias uses the generator path, not the profile's evidence<->site d
    rows = [{"excluded": False, "dispute_rtt_s": 1.0, "withdrawn_plog_s": {i: 0.9 for i in range(10)}, "pending_after_response": {i: 0 for i in range(10)},
             "pending_left": {i: 0 for i in range(10)}} for _ in range(5)]
    assert r.summarize_rows(rows, "mixed", 2.5)["dispute_rtt_bias_ratio"] == 0.0
