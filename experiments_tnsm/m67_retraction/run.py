"""M6xM7 driver (plan rev. 5, audit 14 s.4 "Passo 4-5"; audit 18 s.1.5-1.6): retraction time and
reconciliation under emulated network, ONE factorial design. Runs ON THE NODE (generator and oracle
in the root network namespace, one CLOCK_REALTIME for t0 and for `docker logs -t`), from a pinned
tree copy (hash in the manifest), with the node's venv. NOT integration-tested before this commit:
only the pure functions (tests) and --dry-run were exercised, offline.

Paths and RTTs (user check, 2026-10-10). evidence<->site: netem on both egresses, RTT 2d: that is what the profile probe
(wait_profile, calib_profile.py, VERIFY_NOW) checks, +-20%. generator->container: the generator is in the root namespace with
no qdisc on its egress, so only the response leg is delayed: ~d on a reused connection, ~2d on a fresh one (the userland
docker-proxy dials the container at accept time). The driver therefore warms the connection right before t0 (Env.warm) and
records the measured generator path per cluster (Env.measure_generator_path_ms, informational, never aborts).
dispute-rtt bias (CORRECTED 2026-10-11, after the night data; the earlier text "bias <= d" was wrong): dispute-rtt exceeds the true
withdrawal (last P-log site) by ~2d, = exit delay of the last site + exit delay of evidence towards the generator (night, wan:
163 ms measured vs 2d = 160). Per profile (dispute_rtt_bias_s): lan 0; regional/wan/degraded/extreme 2d; mixed d (only the wan
sites delay, evidence does not); partition not applicable. It changes neither the thresholds nor the measures already taken.
gen_path_d (the generator<->evidence path check, informational) is unchanged.
Client connections (2026-10-11): uvicorn 0.51.0 closes an idle keep-alive connection after 5 s (Config.timeout_keep_alive default;
no override in the service Dockerfile CMD, in mtls.main/server_config or in launcher_d.py: same value in plain and mTLS mode). The
night's two failed FANOUT 10 groups died on `RemoteProtocolError: Server disconnected` in setup_fact (a connection the server had
closed while the FIN was still in flight at d = 80 ms). The client now expires idle connections after KEEPALIVE_EXPIRY_S = 2 s, so
it discards before the server does; keep-alive is KEPT (the t0 bias analysis needs a reused connection after the warm). Transport
errors are excluded per episode with cause `transport_error_setup` (before t0) or `transport_error_measured` (after t0) and the
exception type; they never kill the invocation. Episodes are appended to episodes.jsonl one by one, and a cell interrupted by an
unexpected exception leaves a partial record in cells.jsonl.

Arms. D = DIB_DIST_MTLS=0 + compose override running launcher_d.py (plain, same launcher as the
mTLS arm, prebuilt SSL context set from outside; service.py untouched); C = mTLS. The default
"as shipped" configuration appears only in a few reference B1 cells at `lan` (--arm default,
labelled reference, not an arm of the design). The generator is on the node: a deliberate
difference from M3/M4/M4-rerun (generator on another host); absolute latencies are not comparable.

Blocks (the user applies the netem profile by hand, with sudo, one block per profile; this script
never touches netem; it checks the profile through the TCP connect RTT evidence->site measured
from inside the evidence container, expected 2d, and aborts the block on a mismatch).
  NOTE (netem and cluster recreation): the qdisc lives in each container's network namespace and is lost
  when the cluster is recreated. Cells with the same (arm, FANOUT, T) therefore share one cluster, and
  the cluster is recreated only when that key changes; after each (re)creation the driver waits
  (--profile-wait) for the claimed profile to appear in the measured RTT, so that the user's watcher
  (netem_watch.sh, run by the user with sudo for the duration of a block) or a manual application can
  catch the new containers. If the profile does not appear in time, the block aborts.
  b1      B1, all sites online (k = 0): per cell (arm, FANOUT in {1,10}), T = 5 s; episodes: 10
          (50 at `degraded`). An episode = fresh fact, setup (seed, query+commit at every site, not
          measured), t0 = time.time() just before POST /dispute (site-1), response time, P-log
          (docker logs -t: `POST /apply_fanout 200` of every site) and GET /pending/site-i after
          the response; if some pending is non-empty, wait for it to drain (bound B_online) and
          record the ack time (`POST /pending/<site>/ack 200` in the evidence log).
  b2kill  B2-kill (FANOUT 10): per cell (arm, T in {5,15}, k): 10 trials; a trial = k facts
          committed at site-3 (Active), `compose kill site-3`, k episodes (dispute site-1, dispute
          site-2 -> revoked, restore) while it is down, `compose start site-3`, poll site-3
          /health and /export_mud (P = 50 ms) until none of the k endpoints is exported; the
          convergence is checked on /state of the k facts (target monitor-only) once.
  tcpdump  20 fan-out episodes per arm for the user's tcpdump capture on `degraded`. TWO captures in parallel per arm
          (evidence and site-0 namespaces, the user starts both, noting the clock at start and end; the window is
          also printed as CAPTURE_WINDOW_START/END). The tap side is NOT assumed: by the kernel source (dev_hard_start_xmit
          -> xmit_one -> dev_queue_xmit_nit, after the qdisc dequeue) an egress capture on eth0 should see packets AFTER
          netem, i.e. without the ones netem dropped; TO CONFIRM in the first `degraded` capture: packets seen by the
          sender and not by the receiver would mean the tap is before the qdisc; none in either direction (with 5% loss
          over thousands of packets) means after. If after the qdisc, a lost SYN is invisible at the sender and the 1 s RTO
          (a1) is read from the connect time in the driver rows and from the retransmitted SYN at the receiver, not from
          the sender's capture. pcap files stay OUTSIDE the repository (arm D carries clear-text payload).
Measures recorded for every episode: dispute-rtt (response - t0) and the P-log timestamps; the
analysis applies the per-profile acceptance rule (P-log if its calibrated p95 latency < 10% of
the profile's median direct withdrawal, else dispute-rtt; thresholds file committed after the
calibration, --plog-thresholds). Every client call has an explicit timeout; a call that times
out on the CLIENT side is recorded as `client_timeout` and the episode/trial is EXCLUDED from the
statistics (never counted as a service failure). The generator host (= the node) is sampled by
cpu_sampler (/proc/stat, per-container CPU, generator process) during every cell; an idle
background sample (node_monitor.sample, containers excluded) precedes each cell; the discard rule
(other_cores > 1.0 or steal_pct > 2.0, thresholds unchanged) FLAGS cells, never drops them.

Predictions (declared before launch; prediction (a) re-frozen in audit 18 s.1.5 B3, commit 6c11e48,
NOT modified here; (c) and (d) unchanged until the tcpdump capture says otherwise):
  (a)  [reading for FANOUT 1, added 2026-10-11 AFTER seeing the night data, supported by the text of rev. 3 ("with concurrency 1
       the duration of /dispute is ~ 10*n_RTT*R"): the quantity is the withdrawal of the LAST site, predicted as 10 x n_RTT x R plus
       the service time (V6); the rule is unchanged: falsified if the median exceeds n_RTT*R (x10 for FANOUT 1) + 3 x (`lan` median
       of the same arm, same session) beyond the CI. If for arm C the rule is violated because the `lan` median is very low, it is
       reported as falsified with the observed excess; the model is not adapted.]
  (a)  withdrawal ~ n_RTT*R + service, n_RTT = 2 (D) or 3 (C), R = 2d (R = d for the `wan` sites of
       `mixed`); falsified if the median at regional/wan/mixed exceeds n_RTT*R + 3 x (median at
       `lan` of the SAME arm) beyond the CI. P-a1: default - D, last site, FANOUT 1, lan: +61.5 ms
       (falsified if the CI is outside [46, 77]); P-a2 (FANOUT 10): between +6 and +62 ms (outside
       [3, 75] falsifies); P-a4: C - D, last site, FANOUT 1, lan: +23.5 ms (outside [15, 32]).
  (c)  share of deliveries that end in pending, per profile/arm: regional ~8e-9, wan ~8-9e-6,
       mixed ~1e-6 (0 observed; >= 2 in the block falsifies), degraded D 0.0063-0.0115 (CP 95% CI
       outside [0.004, 0.015] falsifies), degraded C 0.028-0.064 (outside [0.025, 0.08] falsifies),
       extreme 1 (any direct delivery that succeeds falsifies). CONDITIONAL on the tcpdump
       calibration; frozen only after it. SUPERSEDED AS TO THE OBSERVABLE by prediction_c_observable.md (written before any
       B1 data): the count is per site and episode (pending collapses per (site, fact)); with k = 1 fan-out per fact in B1 the
       intervals above are unchanged; ack lines per site-episode are recorded to check that no collapse happens.
  (d)  B2-kill convergence after start <= 1.5 + 0.1T + max(5, D_run_max); T=15 minus T=5 median
       difference in [0, 1.5] s; test on the two arms POOLED only if a preliminary same-T
       comparison of the arms shows no difference, otherwise stop and ask (user decision C3).
  (e)  correctness: no invariant violation; no disputed rule exportable beyond the bound.
       Falsified by one violation (rule E: stop, report, no change to service.py without the user).
Usage: python3 run.py --block b1|b2kill|tcpdump --profile lan|regional|wan|degraded|extreme|mixed
         --tree <pinned tree> --out <dir> [--arms D,C] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import platform
import random
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))

N_SITES = 10
# profile: d per side (s), p per side, R = evidence<->site RTT (s)
PROFILES = {
    "lan": {"d": 0.0, "R": 0.0001, "loss_rt": 0.0},
    "regional": {"d": 0.020, "R": 0.040, "loss_rt": 0.002},
    "wan": {"d": 0.080, "R": 0.160, "loss_rt": 0.02},
    "degraded": {"d": 0.200, "R": 0.400, "loss_rt": 0.10},
    "extreme": {"d": 0.550, "R": 1.100, "loss_rt": 0.0},
    "mixed": {"d": 0.080, "R": 0.080, "loss_rt": 0.01},   # only sites 5-9 are delayed (their egress): R = d
}
# Expected TCP connect RTT (ms) evidence -> site-i, as (lo, hi), per profile (profile check, no sudo needed).
# Tolerance (declared 2026-10-10, before the wan block): +-20% of the expected RTT R = 2d, applied to the MEDIAN of 3 connections per
# site (all 10 sites must match). Bands of neighbouring profiles (R = 40, 160, 400, 1100 ms) are far apart, so +-20% cannot confuse
# them. Known risk at `degraded` (p = 5% per side, ~10% per connection): a lost SYN or SYN-ACK is retransmitted after 1 s, so such a
# connection takes ~1.4 s; the median of 3 survives one such sample (fails when >= 2 of 3 are hit: ~2.8% per site, so ~25% of the 10-site
# probes fail at degraded, ~1% at wan). A failed probe is not an error: the driver retries every second up to --profile-wait (90 s)
# and only then aborts the block (probability of 90 s of consecutive failures at degraded ~ 0.25^45, negligible).
def _band(r_ms: float) -> tuple[float, float]:
    return (0.8 * r_ms, 1.2 * r_ms)


# NOTE: these bands are for the path EVIDENCE <-> SITE (probe run from inside the evidence container; both ends have netem on
# their egress, hence 2d). The generator's path to the containers is a different one (~d reused, ~2d fresh, see gen_path_d,
# generator_path_matches, Env.measure_generator_path_ms) and is NOT part of this check.
RTT_EXPECT_MS = {
    "lan": {i: (0.0, 3.0) for i in range(N_SITES)},
    "regional": {i: _band(40.0) for i in range(N_SITES)},
    "wan": {i: _band(160.0) for i in range(N_SITES)},
    "degraded": {i: _band(400.0) for i in range(N_SITES)},
    "extreme": {i: _band(1100.0) for i in range(N_SITES)},
    "mixed": {**{i: (0.0, 3.0) for i in range(5)}, **{i: _band(80.0) for i in range(5, 10)}},
}
ARMS = {"D": {"mtls": 0}, "C": {"mtls": 1}, "default": {"mtls": 0}}   # `default` = reference only (B1 at lan)
N_RTT = {"D": 2, "default": 2, "C": 3}
ATTEMPT_HARD_S = {"D": 3.0, "default": 3.0, "C": 4.0}   # sum of per-phase 1 s timeouts of one attempt (audit 14 V1)
B1_EPISODES = {"lan": 10, "regional": 10, "wan": 10, "degraded": 50, "extreme": 10, "mixed": 10}
B2_KS = {"lan": [1, 10, 50], "wan": [1, 10], "degraded": [1, 10], "regional": [1, 10], "mixed": [1, 10], "extreme": [1]}
B2_TS = [5, 15]
FANOUTS = [1, 10]


def d_run_max(profile: str, arm: str) -> float:
    return 3 * N_RTT[arm] * PROFILES[profile]["R"] + 2.0


def b_online(profile: str, arm: str, T: float) -> float:
    return 1.1 * T + max(5.0, d_run_max(profile, arm))


def bound_kill(profile: str, arm: str, T: float) -> float:
    return 1.5 + 0.1 * T + max(5.0, d_run_max(profile, arm))


def hard_limit_s(profile: str, arm: str, conc: int, l_dns: float | None = None) -> float:
    """Hard limit H of one POST /dispute (sync fan-out), audit 18 s.1.4 table; `extreme`: every attempt
    ends at the 1 s connect timeout. B2-kill: max(H, 3*L_dns) when L_dns is given."""
    per = 1.0 if profile == "extreme" else ATTEMPT_HARD_S[arm]
    h = (N_SITES if conc == 1 else 1) * 3 * per
    if l_dns is not None:
        h = max(h, 3 * l_dns)
    return h


def client_timeout_s(profile: str, arm: str, conc: int, l_dns: float | None = None) -> float:
    return 2 * hard_limit_s(profile, arm, conc, l_dns)


def rtt_matches(profile: str, measured_ms: dict[int, float]) -> tuple[bool, list[str]]:
    bad = []
    for i, (lo, hi) in RTT_EXPECT_MS[profile].items():
        v = measured_ms.get(i)
        if v is None or not (lo <= v <= hi):
            bad.append(f"site-{i}: {v} ms not in [{lo}, {hi}]")
    return (not bad), bad


def gen_path_d(profile: str) -> float:
    """One-way netem delay on the container egress that the GENERATOR's path to evidence crosses (response leg only: the
    generator is in the root namespace, no qdisc on its egress). Equals the profile's d, except in `mixed`, where evidence
    has no netem (only sites 5-9 are delayed)."""
    return 0.0 if profile == "mixed" else PROFILES[profile]["d"]


def dispute_rtt_bias_s(profile: str) -> float | None:
    """Excess of dispute-rtt over the true withdrawal (last P-log site), in s: exit delay of the last site + exit delay of
    evidence towards the generator (corrected 2026-10-11). lan 0; mixed: only the wan sites delay, evidence does not -> d;
    partition: not applicable (None); every other profile 2d."""
    if profile == "partition":
        return None
    d = PROFILES[profile]["d"]
    return d if profile == "mixed" else 2.0 * d


def generator_path_matches(profile: str, gp: dict, mtls: bool) -> dict:
    """Informational check (never aborts) of the measured generator->evidence GET /health time, in ms: on a REUSED connection
    ~d; on a FRESH connection the userland docker-proxy first dials the container, so ~2d (no expectation with TLS: the
    handshake adds round trips). +-20% like the evidence<->site probe; below 3 ms for d = 0."""
    d = gen_path_d(profile) * 1000.0

    def inside(v, x):
        return (0.0 <= v <= 3.0) if x == 0 else (0.8 * x <= v <= 1.2 * x)
    return {"reused_ok": inside(gp["reused_ms"], d), "fresh_ok": None if mtls else inside(gp["fresh_ms"], 2 * d if d else 0)}


def wait_queues_empty(read_fn, timeout: float, sleep=time.sleep, now=time.time, poll: float = 0.5) -> tuple[bool, float]:
    """Poll read_fn() -> {site: items} (ALL scores) until every queue is empty or `timeout` passes. Returns (clean, waited_s)."""
    t0 = now()
    while True:
        if not any(read_fn().values()):
            return True, now() - t0
        if now() - t0 >= timeout:
            return False, now() - t0
        sleep(poll)


def generator_path_flag(gp: dict) -> bool:
    """True if a measured generator-path value is outside its +-20% expectation (informational, never aborts)."""
    return gp.get("reused_ok") is False or gp.get("fresh_ok") is False


_LOG = re.compile(r'^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z\s.*"(POST|GET) (/[^ ]*) HTTP/1\.1" (\d{3})')


def _ts(date: str, frac: str | None) -> float:
    base = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    return base + (float(frac) if frac else 0.0)


def parse_access_lines(text: str, method: str, path_prefix: str) -> list[tuple[float, str, int]]:
    """(timestamp, path, status) of every access-log line of `method` whose path starts with path_prefix, from
    `docker logs -t` text (RFC3339Nano daemon timestamps, same clock as t0)."""
    out = []
    for line in text.splitlines():
        m = _LOG.match(line)
        if m and m.group(3) == method and m.group(4).startswith(path_prefix):
            out.append((_ts(m.group(1), m.group(2)), m.group(4), int(m.group(5))))
    return out


def parse_post_lines(text: str, path_prefix: str) -> list[tuple[float, str, int]]:
    return parse_access_lines(text, "POST", path_prefix)


_WATCH = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z netem_watch: (containers changed -> applying|applied) (\S+)")


def parse_watch_log(text: str) -> list[dict]:
    """Events of netem_watch.sh output (user-saved with tee): each `containers changed` paired with the next `applied`."""
    out, cur = [], None
    for line in text.splitlines():
        m = _WATCH.match(line)
        if not m:
            continue
        t = _ts(m.group(1), m.group(2))
        if m.group(3).startswith("containers"):
            cur = {"t_changed": t, "profile": m.group(4)}
        elif cur is not None:
            cur["t_applied"] = t
            out.append(cur)
            cur = None
    return out


def restart_netem_bias(t_start: float, events: list[dict], t_first_reconcile: float | None) -> dict:
    """Delay between `compose start site` and the netem re-application (first watcher `applied` after t_start), and whether
    the site's first reconcile pull (first `GET /pending/<site>` in the evidence access log after t_start) came before it:
    that first attempt may then have left the site without netem (bias, declared)."""
    applied = next((e["t_applied"] for e in sorted(events, key=lambda e: e["t_applied"]) if e["t_applied"] > t_start), None)
    out = {"netem_applied_after_start_s": None if applied is None else applied - t_start,
           "first_reconcile_after_start_s": None if t_first_reconcile is None else t_first_reconcile - t_start,
           "first_reconcile_before_netem": None}
    if applied is not None and t_first_reconcile is not None:
        out["first_reconcile_before_netem"] = t_first_reconcile < applied
    return out


def first_after(lines, t0: float, status: int = 200):
    for t, _p, s in sorted(lines):
        if t >= t0 and s == status:
            return t
    return None


def plan(profile: str, blocks: list[str], arms: list[str], fanouts: list[int] | None = None, episodes: int | None = None) -> list[dict]:
    cells = []
    fanouts = fanouts or FANOUTS
    if "b1" in blocks:
        for arm in arms:
            for conc in fanouts:
                cells.append({"block": "b1", "arm": arm, "fanout": conc, "T": 5, "episodes": episodes or B1_EPISODES[profile]})
    if "b2kill" in blocks:
        for arm in arms:
            for T in B2_TS:
                for k in B2_KS[profile]:
                    cells.append({"block": "b2kill", "arm": arm, "fanout": 10, "T": T, "k": k, "trials": 10})
    if "tcpdump" in blocks:
        for arm in arms:
            cells.append({"block": "tcpdump", "arm": arm, "fanout": 1, "T": 5, "episodes": 20})
    return cells


def cell_budget(cell: dict, profile: str) -> dict:
    arm = cell["arm"]
    conc = cell["fanout"]
    return {"client_timeout_s": client_timeout_s(profile, arm, conc),
            "hard_limit_H_s": hard_limit_s(profile, arm, conc),
            "B_online_s": round(b_online(profile, arm, cell["T"]), 2),
            "bound_kill_s": round(bound_kill(profile, arm, cell["T"]), 2),
            "D_run_max_s": round(d_run_max(profile, arm), 2)}


AGREE_MS = 3.0            # P-log vs dispute-rtt agreement tolerance (lan calibration: p95 2-2.5 ms, relative order ~2-3 ms)
PLOG_P95_MS_DEFAULT = 2.5  # calibrated p95 latency of docker logs -t at lan (audit 18 s.1.9)
GEN_SAT_PROC, GEN_SAT_HOST_PCT = 0.85, 80.0


def _median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def excluded_by_cause(rows: list[dict]) -> dict:
    out: dict = {}
    for r in rows:
        if r.get("excluded"):
            c = r.get("excluded_reason") or ("client_timeout" if r.get("client_timeout") else "other")
            out[c] = out.get(c, 0) + 1
    return out


def summarize_rows(rows: list[dict], profile: str, plog_p95_ms: float = PLOG_P95_MS_DEFAULT) -> dict:
    """Per-cell summary of B1/tcpdump episodes: median dispute-rtt, median direct withdrawal by P-log (last site), their
    agreement, the acceptance ratio of the log probe, and the bias ratios of the manifest (user decision B/A4)."""
    d = PROFILES[profile]["d"]
    bias = dispute_rtt_bias_s(profile)   # exit delay of the last site + exit delay of evidence (not gen_path_d)
    ok = [r for r in rows if not r.get("excluded") and "dispute_rtt_s" in r]
    direct, rtt, diffs, pend = [], [], [], []
    n_read = n_log = undercount = unmeasured = undrained = 0
    ack_total, ack_max = 0, 0
    for r in ok:
        rtt.append(r["dispute_rtt_s"])
        for n_ack in (r.get("plog_ack_count") or {}).values():
            ack_total += n_ack
            ack_max = max(ack_max, n_ack)
        # Pending count from the evidence LOG (an ack line after t0, or still pending at the deadline); the generator's GET reads are
        # late by up to ~d..2d per read and can miss a drain, so they are only a cross-check (read_undercount_sites).
        read_sites = {i for i, n in (r.get("pending_after_response") or {}).items() if n}
        acks = {i: t - r["t0"] for i, t in (r.get("plog_ack_ts") or {}).items() if t is not None}
        left_sites = {i for i, n in (r.get("pending_left") or {}).items() if n}
        log_sites = set(acks) | left_sites
        n_read += len(read_sites)
        n_log += len(log_sites)
        undercount += len(log_sites - read_sites)
        plog = [v for v in (r.get("withdrawn_plog_s") or {}).values() if v is not None]
        if not (read_sites or log_sites):
            if len(plog) == N_SITES:
                last = max(plog)
                direct.append(last)
                diffs.append((r["dispute_rtt_s"] - last) * 1000.0)
        elif left_sites:
            undrained += 1                                   # not drained within the deadline: no time
        elif read_sites - set(acks):
            unmeasured += 1                                  # left pending without an ack (snapshot repair or unknown): NOT measured, not mixed
        elif acks:
            pend.append(max(acks.values()))
    med_direct, med_rtt, med_pend = _median(direct), _median(rtt), _median(pend)
    out = {"episodes": len(rows), "excluded": sum(1 for r in rows if r.get("excluded")), "client_timeouts": sum(1 for r in rows if r.get("client_timeout")),
           "median_dispute_rtt_s": med_rtt, "median_direct_plog_s": med_direct, "n_direct": len(direct),
           "plog_minus_response_gap_ms": {"median": _median(diffs), "max_abs": max((abs(x) for x in diffs), default=None)},
           "plog_rtt_agree_within_ms": AGREE_MS,
           "plog_rtt_agree": (bool(diffs) and all(abs(x) <= AGREE_MS for x in diffs)),
           "plog_p95_ms_used": plog_p95_ms,
           "plog_acceptance_ratio": (plog_p95_ms / 1000.0 / med_direct) if med_direct else None,
           "plog_acceptable_rule_10pct": bool(med_direct and plog_p95_ms / 1000.0 / med_direct < 0.10),
           "excluded_by_cause": excluded_by_cause(rows),
           "dispute_rtt_bias_s": bias,
           "dispute_rtt_bias_ratio": (bias / med_rtt) if (med_rtt and bias) else (0.0 if (med_rtt is not None and bias is not None) else None),
           "median_pending_withdrawal_s": med_pend, "n_pending_episodes": len(pend),
           "n_queue_not_clean": sum(1 for r in rows if r.get("excluded_reason") == "queues_not_empty_at_start"),
           "ack_lines_total": ack_total, "ack_lines_max_per_site_episode": ack_max,
           "n_pending_sites_read": n_read, "n_pending_sites_log": n_log, "read_undercount_sites": undercount,
           "n_pending_unmeasured_episodes": unmeasured, "n_pending_undrained_episodes": undrained,
           "pending_bias_ratio": ((d + 0.05) / med_pend) if med_pend else None}
    out["pending_bias_flag_gt10pct"] = bool(out["pending_bias_ratio"] and out["pending_bias_ratio"] > 0.10)
    return out


def generator_load(samples: list[dict]) -> dict:
    """Load of the generator host (= the node) during a cell, from cpu_sampler samples (user decision D): flags a load that
    approaches the thresholds fixed in diag_cpu100 (0.85 cores for the generator process, 80% of the host)."""
    procs = [s["proc_cores"] for s in samples if s.get("proc_cores") is not None]
    host = [s["host_busy_pct"] for s in samples]
    out = {"samples": len(samples), "gen_proc_cores_mean": (statistics.mean(procs) if procs else None),
           "gen_proc_cores_max": max(procs, default=None),
           "host_busy_pct_mean": (statistics.mean(host) if host else None), "host_busy_pct_max": max(host, default=None)}
    out["near_saturation"] = bool((out["gen_proc_cores_mean"] or 0) >= GEN_SAT_PROC or (out["host_busy_pct_mean"] or 0) >= GEN_SAT_HOST_PCT)
    return out


def group_cells(cells: list[dict], rng: random.Random) -> list[tuple[tuple, list[dict]]]:
    """Cells that share (arm, FANOUT, T) run on the SAME cluster: netem lives in each container's
    network namespace and is lost when the cluster is recreated, so the cluster is recreated only when
    this key changes. Group order and cell order inside a group are shuffled (seed) and recorded."""
    groups: dict[tuple, list[dict]] = {}
    for c in cells:
        groups.setdefault((c["arm"], c["fanout"], c["T"]), []).append(c)
    keys = list(groups)
    rng.shuffle(keys)
    out = []
    for k in keys:
        rng.shuffle(groups[k])
        out.append((k, groups[k]))
    return out


def extra_compose() -> str | None:
    """Path of an extra compose file from DIB_M67_EXTRA_COMPOSE (docs/audit/85), or None."""
    return os.environ.get("DIB_M67_EXTRA_COMPOSE") or None


def dns_nosearch_enabled() -> bool:
    """True only when DIB_M67_DNS_NOSEARCH=1 in the driver's environment (docs/audit/72): the cluster gets `dns_search: .` (no search domains)."""
    return os.environ.get("DIB_M67_DNS_NOSEARCH", "0") == "1"


def keepalive_enabled() -> bool:
    """True only when DIB_M67_KEEPALIVE=1 in the driver's environment (docs/audit/62)."""
    return os.environ.get("DIB_M67_KEEPALIVE", "0") == "1"


class ClientTimeout(Exception):
    """A client-side timeout: the episode/trial is EXCLUDED from the statistics, never counted as a service failure."""


class SetupFailed(Exception):
    """D5 (audit 90): a /query or /commit of the episode setup was refused (status != 200 or applied != true): the episode/trial is EXCLUDED with the step, the site and
    the answer, it is not a service failure of the measured operation and it must not start with sites that are not Active."""

    def __init__(self, site: int, step: str, status, body):
        super().__init__(f"setup {step} at site-{site}: status {status}, body {str(body)[:120]}")
        self.site, self.step, self.status, self.body = site, step, status, body


def check_step(resp, site: int, step: str) -> None:
    body = resp.json()
    if resp.status_code != 200 or not isinstance(body, dict) or body.get("applied") is not True:
        raise SetupFailed(site, step, resp.status_code, body)


class TransportFailure(Exception):
    """A non-timeout transport error (e.g. httpx.RemoteProtocolError on a connection the server closed): the episode/trial is
    EXCLUDED with the cause and the exception type, the invocation goes on."""

    def __init__(self, exc_type: str, msg: str):
        super().__init__(f"{exc_type}: {msg}")
        self.exc_type = exc_type


SERVER_KEEPALIVE_S = 5        # uvicorn 0.51.0 Config.timeout_keep_alive default; not overridden anywhere (plain and mTLS)
KEEPALIVE_EXPIRY_S = 2.0      # client side: discard idle connections before the server does (keep-alive KEPT)


class Env:
    """Node-local environment: compose helpers, HTTP clients with explicit timeouts, log reading."""

    def __init__(self, tree: str, arm: str, fanout: int, T: float, pki: Path):
        self.tree, self.arm, self.fanout, self.T, self.pki = tree, arm, fanout, T, pki
        self.home = str(Path.home())
        self.mtls = ARMS[arm]["mtls"]
        self.scheme = "https" if self.mtls else "http"
        self.ev = f"{self.scheme}://localhost:18100"
        self._clients: dict = {}

    def site(self, i: int) -> str:
        return f"{self.scheme}://localhost:{18110 + i}"

    def compose(self) -> str:
        dist = f"{self.tree}/code/src/dib/registry/distributed"
        gen = f"{self.home}/dib_tnsm/m67/gen_{self.arm}_f{self.fanout}_T{int(self.T)}.yml"
        env = (f"DIB_DIST_FANOUT_CONCURRENCY={self.fanout} DIB_DIST_MTLS={self.mtls} DIB_DIST_PKI_DIR={self.pki} "
               f"DIB_DIST_RECONCILE_INTERVAL={self.T} DIB_DIST_RECONCILE_JITTER={0.1 * self.T}")
        if keepalive_enabled():   # docs/audit/62: opt-in persistent fan-out connections, switched on from the DRIVER's environment
            env += " DIB_DIST_FANOUT_KEEPALIVE=1 DIB_DIST_FANOUT_WARM_INTERVAL=2"
        files = f"-f {gen}" + (f" -f {self.home}/dib_tnsm/m67/override_d.yml" if self.arm == "D" else "")
        if dns_nosearch_enabled():   # docs/audit/72: the node's search domains stall the resolution of a killed site's name (1-8 s in bursts)
            ov = Path(self.home) / "dib_tnsm" / "m67" / "dns_nosearch.yml"
            ov.parent.mkdir(parents=True, exist_ok=True)
            ov.write_text("services:\n" + "".join(f"  {n}:\n    dns_search: .\n" for n in ["evidence"] + [f"site-{i}" for i in range(N_SITES)]))
            files += f" -f {ov}"
        if extra_compose():     # docs/audit/85: NET_ADMIN + host tc for the user-space netem applier
            files += f" -f {extra_compose()}"
        return (f"export PATH=/snap/bin:$PATH && cd {dist} && mkdir -p {self.home}/dib_tnsm/m67 && {env} "
                f"python3 generate_compose.py > {gen} && docker compose -p dibtnsm {files} --project-directory {dist} ")

    def sh(self, cmd: str, check: bool = True, timeout: float = 300) -> str:
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout)
        if check and r.returncode != 0:
            raise RuntimeError(f"command failed ({r.returncode}): {cmd}\n{r.stdout}\n{r.stderr}")
        return r.stdout + r.stderr

    def up(self):
        self.sh(self.compose() + "down -v --remove-orphans", check=False)
        self.sh(self.compose() + "up -d")

    def down(self):
        self.sh(self.compose() + "down -v --remove-orphans", check=False)

    def _make_client(self, identity: str | None):
        import httpx
        import ssl
        verify = True
        if self.mtls:
            ctx = ssl.create_default_context(cafile=str(self.pki / "ca.crt"))
            ctx.load_cert_chain(str(self.pki / f"{identity}.crt"), str(self.pki / f"{identity}.key"))
            verify = ctx
        return httpx.Client(verify=verify, limits=httpx.Limits(keepalive_expiry=KEEPALIVE_EXPIRY_S))

    def client(self, identity: str | None):
        key = identity if self.mtls else None
        if key not in self._clients:
            self._clients[key] = self._make_client(identity)
        return self._clients[key]

    def warm(self, identity: str | None, url: str | None = None) -> None:
        """Unmeasured GET /health on the connection the next call will reuse. The generator reaches containers through the
        userland docker-proxy, which dials the container when a client connection is accepted: a FRESH connection costs
        one extra d before the request reaches the service (keep-alive expires after ~5 s, and the mTLS arm uses one
        client per identity). Warming right before t0 makes the measured calls run on a reused connection, so the
        generator path is ~d (response leg only) in every episode."""
        self.req("GET", (url or self.ev) + "/health", identity, 5.0)

    def warm_many(self, identities: list[str]) -> None:
        """Warm one connection per identity concurrently (before t0)."""
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(identities)) as ex:
            list(ex.map(self.warm, identities))

    def read_pending(self, sites: list[int]) -> dict[int, list]:
        """GET /pending/site-i for all `sites` CONCURRENTLY (ten sequential reads at ~d..2d each would be late by seconds and miss
        drains). One thread per site, identity site-i."""
        from concurrent.futures import ThreadPoolExecutor

        def one(i):
            return i, self.req("GET", f"{self.ev}/pending/site-{i}", f"site-{i}", 5.0).json()["pending"]
        with ThreadPoolExecutor(max_workers=len(sites)) as ex:
            return dict(ex.map(one, sites))

    def queues_clean(self, timeout: float) -> tuple[bool, float]:
        return wait_queues_empty(lambda: self.read_pending(list(range(N_SITES))), timeout)

    def measure_generator_path_ms(self, n: int = 5) -> dict:
        """Median GET /health time from the generator (root namespace) to evidence on a reused and on a fresh connection."""
        import statistics
        ident = "admin"
        c = self._make_client(ident)
        c.get(f"{self.ev}/health", timeout=10.0)
        reused = []
        for _ in range(n):
            t = time.perf_counter()
            c.get(f"{self.ev}/health", timeout=10.0)
            reused.append((time.perf_counter() - t) * 1000.0)
        c.close()
        fresh = []
        for _ in range(n):
            f = self._make_client(ident)
            t = time.perf_counter()
            f.get(f"{self.ev}/health", timeout=10.0)
            fresh.append((time.perf_counter() - t) * 1000.0)
            f.close()
        return {"reused_ms": statistics.median(reused), "fresh_ms": statistics.median(fresh), "n": n}

    def req(self, method: str, url: str, identity: str | None, timeout: float, **kw):
        import httpx
        try:
            return self.client(identity).request(method, url, timeout=httpx.Timeout(connect=5.0, read=timeout, write=5.0, pool=5.0), **kw)
        except httpx.TimeoutException as exc:
            raise ClientTimeout(f"{method} {url}: {exc!r}") from exc
        except httpx.TransportError as exc:
            raise TransportFailure(type(exc).__name__, f"{method} {url}: {exc}") from exc

    def logs(self, container: str, since: float) -> str:
        return self.sh(f"/snap/bin/docker logs -t --since {since - 1.0:.3f} {container} 2>&1", check=False, timeout=60)

    def healthy(self, timeout: float = 90.0) -> float:
        t0 = time.time()
        urls = [f"{self.ev}/health"] + [f"{self.site(i)}/health" for i in range(N_SITES)]
        ok: set = set()
        while time.time() - t0 < timeout and len(ok) < len(urls):
            for u in urls:
                if u in ok:
                    continue
                try:
                    if self.req("GET", u, "admin", 2.0).status_code == 200:
                        ok.add(u)
                except Exception:  # noqa: BLE001 -- not up yet
                    pass
            time.sleep(0.2)
        if len(ok) < len(urls):
            raise RuntimeError(f"cluster not healthy after {timeout}s: {len(ok)}/{len(urls)}")
        return time.time() - t0

    RTT_SCRIPT = (
        "import socket,time,json\n"
        "r={}\n"
        "for i in range(10):\n"
        " a=socket.getaddrinfo('site-'+str(i),8000,type=socket.SOCK_STREAM)[0][4]\n"
        " v=[]\n"
        " for _ in range(__N__):\n"
        "  t=time.perf_counter();s=socket.create_connection(a,timeout=5);v.append(time.perf_counter()-t);s.close()\n"
        " r[i]=sorted(v)[len(v)//2]*1000\n"
        "print(json.dumps(r))\n")

    def measure_rtt_ms(self, n: int = 3) -> dict[int, float]:
        """TCP connect time evidence -> site-i, measured from inside the evidence container (script on stdin,
        address resolved first so that DNS is not included): ~ the RTT, expected 2d by the netem profile."""
        r = subprocess.run(["bash", "-c", "/snap/bin/docker exec -i dibtnsm-evidence-1 python -"], input=self.RTT_SCRIPT.replace("__N__", str(n)),
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise RuntimeError(f"RTT probe failed: {r.stderr}")
        return {int(k): v for k, v in json.loads(r.stdout.strip().splitlines()[-1]).items()}


def setup_fact(env: Env, ep: str, sites: list[int], timeout: float) -> int:
    from concurrent.futures import ThreadPoolExecutor
    r = env.req("POST", f"{env.ev}/seed", "admin", timeout, json={"device_type": "cam-a", "endpoint": ep})
    sid = r.json()["id"]

    def one(i):
        body = {"device_type": "cam-a", "endpoint": ep}
        check_step(env.req("POST", f"{env.site(i)}/query", f"op-site-{i}", timeout, json=body), i, "query")
        check_step(env.req("POST", f"{env.site(i)}/commit", f"op-site-{i}", timeout, json=body), i, "commit")

    with ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(one, sites))
    return sid


def episode_b1(env: Env, profile: str, tag: str, e: int, setup: bool = True) -> dict:
    row = {"episode": e, "excluded": False}
    ep = f"m67-{tag}-{e}.example"
    tmo = client_timeout_s(profile, env.arm, env.fanout)
    phase = "setup"      # until t0 is taken: transport_error_setup; after: transport_error_measured
    try:
        clean, waited = env.queues_clean(b_online(profile, env.arm, env.T) + 3.0)
        row["queue_wait_before_s"] = waited
        if not clean:
            row.update(excluded=True, excluded_reason="queues_not_empty_at_start")
            return row
        if setup:
            sid = setup_fact(env, ep, list(range(N_SITES)), 30.0 if profile != "extreme" else 90.0)
        else:
            sid = env.req("POST", f"{env.ev}/seed", "admin", 30.0, json={"device_type": "cam-a", "endpoint": ep}).json()["id"]
        env.warm_many(["op-site-1"] + [f"site-{i}" for i in range(N_SITES)])   # connections the dispute and the pending reads will reuse
        t0 = time.time()
        phase = "measured"
        r = env.req("POST", f"{env.ev}/dispute", "op-site-1", tmo, json={"device_type": "cam-a", "endpoint": ep, "site_id": "site-1"})
        t_resp = time.time()
        row.update(t0=t0, t_resp=t_resp, status=r.status_code, dispute_rtt_s=t_resp - t0, score_id=sid)
        pend = {}
        for i, items in env.read_pending(list(range(N_SITES))).items():
            pend[i] = sum(1 for it in items if it["score_id"] == sid)
        row["pending_read_delay_s"] = time.time() - t_resp           # how late the (concurrent) read is: bias of the READ count
        row["pending_after_response"] = {i: pend[i] for i in sorted(pend)}
        deadline = t_resp + b_online(profile, env.arm, env.T) + 3.0
        while sum(pend.values()) and time.time() < deadline:
            time.sleep(0.5)
            for i, items in env.read_pending([i for i, n in pend.items() if n]).items():
                pend[i] = sum(1 for it in items if it["score_id"] == sid)
        row["pending_left"] = dict(pend)
        applied, acked = {}, {}
        evlog = parse_post_lines(env.logs("dibtnsm-evidence-1", t0), "/pending/")
        for i in range(N_SITES):
            applied[i] = first_after(parse_post_lines(env.logs(f"dibtnsm-site-{i}-1", t0), "/apply_fanout"), t0)
            acked[i] = first_after([x for x in evlog if x[1] == f"/pending/site-{i}/ack"], t0)
        row["plog_apply_ts"], row["plog_ack_ts"] = applied, acked
        row["plog_ack_count"] = {i: sum(1 for x in evlog if x[1] == f"/pending/site-{i}/ack" and x[0] >= t0 and x[2] == 200) for i in range(N_SITES)}
        row["withdrawn_plog_s"] = {i: (None if t is None else t - t0) for i, t in applied.items()}
    except SetupFailed as exc:
        row.update(excluded=True, excluded_reason="setup_failed", setup_failed=str(exc)[:200])
    except ClientTimeout as exc:
        row.update(excluded=True, client_timeout=str(exc)[:200])
    except TransportFailure as exc:
        row.update(excluded=True, excluded_reason=f"transport_error_{phase}", exception_type=exc.exc_type, exception=str(exc)[:200])
    time.sleep(0.5)
    return row


def run_episodes(env, profile: str, tag: str, n: int, setup: bool, rows: list, sink) -> None:
    """Run n B1 episodes; every finished row is appended to `rows` and handed to `sink` (episodes.jsonl) at once, so an
    unexpected exception in a later episode loses nothing already measured."""
    for e in range(n):
        row = episode_b1(env, profile, tag, e, setup=setup)
        rows.append(row)
        sink(row)


def trial_b2kill(env: Env, profile: str, k: int, trial: int, l_dns: float | None) -> dict:
    row = {"trial": trial, "k": k, "excluded": False}
    killed = False
    tmo = client_timeout_s(profile, env.arm, env.fanout, l_dns)
    try:
        clean, waited = env.queues_clean(bound_kill(profile, env.arm, env.T) + 3.0)
        row["queue_wait_before_s"] = waited
        if not clean:
            row.update(excluded=True, excluded_reason="queues_not_empty_at_start")
            return row
        eps, ids = [f"m67-b2-{env.arm}-T{int(env.T)}-k{k}-t{trial}-{j}.example" for j in range(k)], []
        for ep in eps:
            sid = env.req("POST", f"{env.ev}/seed", "admin", 30.0, json={"device_type": "cam-a", "endpoint": ep}).json()["id"]
            ids.append(sid)
            body = {"device_type": "cam-a", "endpoint": ep}
            check_step(env.req("POST", f"{env.site(3)}/query", "op-site-3", 30.0, json=body), 3, "query")
            check_step(env.req("POST", f"{env.site(3)}/commit", "op-site-3", 30.0, json=body), 3, "commit")
        env.sh(env.compose() + "kill site-3")
        killed = True
        t_kill = time.time()
        for ep in eps:
            body = {"device_type": "cam-a", "endpoint": ep}
            env.warm("op-site-1")
            env.req("POST", f"{env.ev}/dispute", "op-site-1", tmo, json={**body, "site_id": "site-1"})
            env.warm("op-site-2")
            env.req("POST", f"{env.ev}/dispute", "op-site-2", tmo, json={**body, "site_id": "site-2"})
            env.warm("admin")
            env.req("POST", f"{env.ev}/restore", "admin", tmo, json=body)
        pend = env.req("GET", f"{env.ev}/pending/site-3", "site-3", 5.0).json()["pending"]
        row["pending_queued_for_site3"] = len(pend)
        env.sh(env.compose() + "start site-3")
        killed = False
        t_start = time.time()
        row.update(t_kill=t_kill, t_start=t_start)
        bound = bound_kill(profile, env.arm, env.T)
        t_up = t_withdrawn = None
        while time.time() - t_start < bound + 30.0:
            try:
                r = env.req("GET", f"{env.site(3)}/export_mud", "op-site-3", 2.0, params={"device_type": "cam-a"})
            except ClientTimeout:
                r = None
            except Exception:  # noqa: BLE001 -- site still down
                r = None
            if r is not None and r.status_code == 200:
                if t_up is None:
                    t_up = time.time()
                text = json.dumps(r.json())
                if not any(ep in text for ep in eps):
                    t_withdrawn = time.time()
                    break
            time.sleep(0.05)
        ev_logs = env.logs("dibtnsm-evidence-1", t_start)
        pulls = [t for t, _p, st in parse_access_lines(ev_logs, "GET", "/pending/site-3") if t >= t_start and st == 200]
        row["t_first_reconcile_pull"] = min(pulls) if pulls else None   # evidence access log, same clock as t_start
        row["site3_started_at"] = env.sh("/snap/bin/docker inspect -f '{{.State.StartedAt}}' dibtnsm-site-3-1", check=False, timeout=30).strip()
        row.update(t_up=t_up, t_withdrawn=t_withdrawn, bound_s=bound,
                   up_after_start_s=None if t_up is None else t_up - t_start,
                   convergence_s=None if t_withdrawn is None else t_withdrawn - t_start,
                   violation_over_bound=(t_withdrawn is None) or (t_withdrawn - t_start > bound))
        if t_withdrawn is not None:
            states = [env.req("GET", f"{env.site(3)}/state/{sid}", "op-site-3", 5.0).json()["state"] for sid in ids]
            row["final_states"] = {s: states.count(s) for s in set(states)}
            row["final_all_monitor_only"] = all(s == "monitor-only" for s in states)
    except SetupFailed as exc:
        row.update(excluded=True, excluded_reason="setup_failed", setup_failed=str(exc)[:200])
    except ClientTimeout as exc:
        row.update(excluded=True, client_timeout=str(exc)[:200])
    except TransportFailure as exc:
        row.update(excluded=True, excluded_reason="transport_error", exception_type=exc.exc_type, exception=str(exc)[:200])
    finally:
        if killed:   # audit 57: an excluded trial used to leave site-3 dead and every later trial of the cluster failed queues_not_empty_at_start
            try:
                env.sh(env.compose() + "start site-3")
                row["site3_restarted_after_exception"] = True
            except Exception as exc:  # noqa: BLE001 -- best effort: the original cause of the exclusion is kept
                row["site3_restarted_after_exception"] = False
                row["site3_restart_error"] = str(exc)[:200]
    return row


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wait_profile(env: "Env", profile: str, wait_s: float) -> tuple[bool, dict, list, dict]:
    """Profile check with a wait: a watcher run by the user (netem_watch.sh) applies the profile to a freshly created
    container within ~1-2 s; the cluster is measured only once the TCP connect RTT evidence->site matches the claimed
    profile. No sudo here: it only reads timings. Returns the timing of the confirmation for the manifest: during a
    recreation the cluster runs WITHOUT netem until the watcher applies it (the window recorded here)."""
    t_created = time.time()
    first = None
    attempts = 0
    while True:
        rtt = env.measure_rtt_ms()
        attempts += 1
        first = first if first is not None else dict(rtt)
        ok, bad = rtt_matches(profile, rtt)
        if ok or time.time() - t_created > wait_s:
            return ok, rtt, bad, {"t_created": t_created, "t_profile_confirmed": time.time() if ok else None,
                                  "profile_apply_delay_s": (time.time() - t_created) if ok else None,
                                  "rtt_attempts": attempts, "first_rtt_ms": first}
        time.sleep(1.0)


def live(a, cells, rng) -> int:
    import node_monitor as nm
    from cpu_sampler import Sampler
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tree = a.tree if a.tree.startswith("/") else str(Path.home()) + a.tree[1:]
    pki = Path(a.pki)
    rule = json.loads((HERE.parent / "common/discard_rule.json").read_text())
    thresholds = json.loads(Path(a.plog_thresholds).read_text()) if a.plog_thresholds else None
    home = str(Path.home())
    Path(f"{home}/dib_tnsm/m67").mkdir(parents=True, exist_ok=True)
    override = "services:\n" + "".join(
        f"  {s}:\n    command: [\"python\", \"/launcher_d.py\"]\n    volumes:\n"
        f"      - {tree}/experiments_tnsm/m3_distributed/launcher_d.py:/launcher_d.py:ro\n"
        for s in ["evidence"] + [f"site-{i}" for i in range(N_SITES)])
    assert Path(f"{tree}/experiments_tnsm/m3_distributed/launcher_d.py").is_file()   # a missing bind source would become a directory
    Path(f"{home}/dib_tnsm/m67/override_d.yml").write_text(override)
    groups = group_cells(cells, rng)
    manifest = {"started_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv, "profile": a.profile, "blocks": a.block,
                "seed": a.seed, "group_order": [[list(k), len(v)] for k, v in groups],
                "cell_order": [c for _, g in groups for c in g], "node_tree": tree, "generator_host": platform.node(),
                "generator_is_node": True, "clock": "time.time() = CLOCK_REALTIME of the node (same clock as docker logs -t)",
                "cluster_recreations": len(groups), "plog_thresholds": thresholds,
                "measure_rule": "per profile from the thresholds file" if thresholds else "dispute-rtt (no P-log calibration applied)",
                "node_service_sha256": sha(Path(f"{tree}/code/src/dib/registry/distributed/service.py")), "fanout_keepalive": keepalive_enabled(), "dns_nosearch": dns_nosearch_enabled(), "extra_compose": extra_compose(),
                "launcher_d_sha256": sha(Path(f"{tree}/experiments_tnsm/m3_distributed/launcher_d.py")),
                "note_launcher_d": "_HTTP_TLS is set from outside by launcher_d.py; service.py unmodified",
                "run_py_sha256": sha(Path(__file__)), "discard_rule": rule,
                "disk_start": subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.splitlines()[-1]}
    log = (out / "cells.jsonl").open("a")
    eplog = (out / "episodes.jsonl").open("a")     # one line per finished episode/trial (sidecar of cells.jsonl)
    manifest["cells_summary"] = []
    n_cell = 0
    total = len(cells)
    aborted = False
    for (arm, fo, T), group in groups:
        env = Env(tree, arm, fo, T, pki)
        env.up()
        try:
            ready = env.healthy()
            ok, rtt, bad, timing = wait_profile(env, a.profile, a.profile_wait)
            if ok:
                gp = env.measure_generator_path_ms()
                timing["generator_path_ms"] = {**gp, **generator_path_matches(a.profile, gp, env.mtls)}
                print(f"generator path (ms): {timing['generator_path_ms']}", flush=True)
            if not ok:
                log.write(json.dumps({"group": [arm, fo, T], "aborted": "profile check failed: the claimed netem profile does not match the measured RTT",
                                      "rtt_ms_evidence_to_site": rtt, "profile_check_bad": bad, "timing": timing}) + "\n")
                log.flush()
                print(f"ABORT group {arm} f={fo} T={T}: profile check failed after {a.profile_wait}s: {bad}", flush=True)
                aborted = True
                break
            for cell in group:
                n_cell += 1
                bg = nm.idle_window(12.0, project="dibtnsm")
                flagged = bg["other_cores"] > rule["max_other_cores"] or bg["steal_pct"] > rule["max_steal_pct"]
                rec = {"cell": n_cell, "cell_spec": cell, "profile": a.profile, "ready_s": ready, "background_idle": bg, "flagged_pre": flagged,
                       "rtt_ms_evidence_to_site": rtt, "profile_check_ok": ok, "profile_timing": timing, "budget": cell_budget(cell, a.profile)}
                tag = f"{a.profile}-{arm}-f{fo}-T{int(T)}"
                if cell["block"] == "tcpdump":
                    flag = Path(f"{home}/dib_tnsm/m67/tcpdump_ready_{arm}")
                    flag.unlink(missing_ok=True)
                    pid = env.sh("/snap/bin/docker inspect -f '{{.State.Pid}}' dibtnsm-evidence-1").strip()
                    pid_s0 = env.sh("/snap/bin/docker inspect -f '{{.State.Pid}}' dibtnsm-site-0-1").strip()
                    print(f"TCPDUMP_WAIT arm={arm} evidence_pid={pid} site0_pid={pid_s0}: start TWO captures in parallel (evidence and site-0 namespaces), "
                          f"then `touch {flag}` (waiting up to 600 s)", flush=True)
                    t_w = time.time()
                    while not flag.exists() and time.time() - t_w < 600:
                        time.sleep(1.0)
                    if not flag.exists():
                        rec["aborted"] = "tcpdump flag not created within 600 s"
                        log.write(json.dumps(rec) + "\n")
                        log.flush()
                        continue
                    rec["capture_pid"] = pid
                    rec["capture_pids"] = {"evidence": pid, "site-0": pid_s0}
                sampler = Sampler(interval=1.0, project="dibtnsm", pid=os.getpid())
                sampler.start()
                t_cell0 = time.time()
                rows = []

                def sink(row, _cell=n_cell, _arm=arm, _fo=fo, _T=T):
                    eplog.write(json.dumps({"cell": _cell, "arm": _arm, "fanout": _fo, "T": _T, "row": row}) + "\n")
                    eplog.flush()
                try:
                    if cell["block"] in ("b1", "tcpdump"):
                        if cell["block"] == "tcpdump":
                            print(f"CAPTURE_WINDOW_START {time.time():.3f} arm={arm}", flush=True)
                        run_episodes(env, a.profile, tag, cell["episodes"], cell["block"] == "b1", rows, sink)
                        if cell["block"] == "tcpdump":
                            print(f"CAPTURE_WINDOW_END {time.time():.3f} arm={arm}", flush=True)
                    else:
                        for t in range(cell["trials"]):
                            rows.append(trial_b2kill(env, a.profile, cell["k"], t, a.l_dns))
                            sink(rows[-1])
                except BaseException as exc:   # partial cell: the rows measured so far are kept, then the exception goes on
                    sampler.stop()
                    log.write(json.dumps({**rec, "rows": rows, "aborted": f"exception {type(exc).__name__}: {exc}"[:300]}) + "\n")
                    log.flush()
                    raise
                t_cell1 = time.time()
                samples = sampler.stop()
                rec.update(rows=rows, t_cell=[t_cell0, t_cell1], excluded=sum(1 for r in rows if r.get("excluded")), generator_samples=samples,
                           generator_load=generator_load(samples))
                if cell["block"] in ("b1", "tcpdump"):
                    rec["summary"] = summarize_rows(rows, a.profile, a.plog_p95_ms)
                if rec["generator_load"]["near_saturation"]:
                    print("WARNING: generator load near saturation during this cell", flush=True)
                manifest["cells_summary"].append({"cell": n_cell, "spec": cell, "profile_timing": timing, "flagged_pre": flagged,
                                                  "excluded": rec["excluded"], "generator_load": rec["generator_load"],
                                                  "generator_path_flag": generator_path_flag((timing or {}).get("generator_path_ms") or {}),
                                                  "summary": rec.get("summary")})
                log.write(json.dumps(rec) + "\n")
                log.flush()
                print(f"[{n_cell}/{total}] {cell['block']} {arm} f={fo} T={T} rows={len(rows)} excluded={rec['excluded']} flagged={flagged} "
                      f"bg_other={bg['other_cores']} steal={bg['steal_pct']} gen_proc={rec['generator_load']['gen_proc_cores_mean']:.2f}", flush=True)
        finally:
            env.down()
    if a.watch_log and Path(a.watch_log).is_file():
        wev = parse_watch_log(Path(a.watch_log).read_text())
        manifest["watch_log"] = {"path": a.watch_log, "sha256": sha(Path(a.watch_log)), "events": len(wev)}
        manifest["site_restarts"] = [
            {"cell": c["cell"], "trial": r.get("trial"), "t_start": r["t_start"], **restart_netem_bias(r["t_start"], wev, r.get("t_first_reconcile_pull"))}
            for c in map(json.loads, (out / "cells.jsonl").read_text().splitlines()) for r in c.get("rows", []) if "t_start" in r]
        manifest["restart_bias_note"] = ("the first reconcile pull of a restarted site (U(0, 0.1T) + ~0.45 s after start) may leave before the "
                                         "watcher re-applies netem: rows with first_reconcile_before_netem=true carry this bias")
    elif "b2kill" in a.block:
        manifest["restart_bias_note"] = "no watcher log supplied (--watch-log): the netem re-application delay after site restarts is NOT measured"
    ev = out / "profile_events.jsonl"
    manifest["profile_events"] = [json.loads(l) for l in ev.read_text().splitlines()] if ev.exists() else []
    manifest["aborted"] = aborted
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["disk_end"] = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.splitlines()[-1]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return 1 if aborted else 0


def record_event(argv) -> int:
    """`run.py --record-event applied|removed --profile P --out DIR [--note TEXT]`: appends the time of a profile change, as
    COMMUNICATED by the user (logged when the message is received, not when sudo ran: an upper bound on the delay)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--record-event", required=True, choices=["applied", "removed"])
    ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
    ap.add_argument("--out", required=True)
    ap.add_argument("--note", default="")
    a, _ = ap.parse_known_args(argv)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    row = {"event": a.record_event, "profile": a.profile, "t_epoch": time.time(), "t_utc": datetime.now(timezone.utc).isoformat(),
           "source": "communicated by the user, logged on receipt", "note": a.note}
    with (Path(a.out) / "profile_events.jsonl").open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(json.dumps(row))
    return 0


def main() -> int:
    if "--record-event" in sys.argv:
        return record_event(sys.argv[1:])
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--block", required=True, help="comma list of b1,b2kill,tcpdump")
    ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arms", default="D,C")
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--pki", default=str(Path.home() / "dib_tnsm/pki"))
    ap.add_argument("--plog-thresholds", default=None)
    ap.add_argument("--l-dns", type=float, default=None, help="calibrated L_dns (s), for the B2-kill client timeout")
    ap.add_argument("--profile-wait", type=float, default=90.0, help="seconds to wait for the claimed netem profile to show up in the measured RTT")
    ap.add_argument("--fanouts", default="1,10", help="B1 FANOUT values (smoke: 10)")
    ap.add_argument("--episodes", type=int, default=None, help="override the B1 episode count (smoke: 3)")
    ap.add_argument("--plog-p95-ms", type=float, default=PLOG_P95_MS_DEFAULT, help="calibrated p95 of the docker logs -t latency")
    ap.add_argument("--watch-log", default=None, help="saved output of netem_watch.sh (tee), joined to the B2-kill site restarts")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit; nothing is touched")
    a = ap.parse_args()
    blocks = a.block.split(",")
    arms = a.arms.split(",")
    cells = plan(a.profile, blocks, arms, [int(x) for x in a.fanouts.split(",")], a.episodes)
    rng = random.Random(a.seed)
    rng.shuffle(cells)  # order of the cells inside the block, recorded in the manifest
    if a.dry_run:
        prof = PROFILES[a.profile]
        print(f"DRY RUN profile={a.profile} (d={prof['d']*1000:.0f} ms/side, R={prof['R']*1000:.1f} ms, loss on the round trip ~{prof['loss_rt']*100:.1f}%)")
        print(f"blocks={blocks} arms={arms} seed={a.seed} cells={len(cells)}  (nothing is applied or contacted)")
        print("expected TCP connect RTT evidence->site (ms), profile check: " + json.dumps({i: v for i, v in RTT_EXPECT_MS[a.profile].items()}))
        for k, c in enumerate(cells):
            print(f"  [{k + 1}/{len(cells)}] {json.dumps(c)}  {json.dumps(cell_budget(c, a.profile))}")
        return 0
    return live(a, cells, rng)


if __name__ == "__main__":
    raise SystemExit(main())
