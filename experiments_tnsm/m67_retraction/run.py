"""M6xM7 driver (plan rev. 5, audit 14 s.4 "Passo 4-5"; audit 18 s.1.5-1.6): retraction time and
reconciliation under emulated network, ONE factorial design. Runs ON THE NODE (generator and oracle
in the root network namespace, one CLOCK_REALTIME for t0 and for `docker logs -t`), from a pinned
tree copy (hash in the manifest), with the node's venv. NOT integration-tested before this commit:
only the pure functions (tests) and --dry-run were exercised, offline.

Arms. D = DIB_DIST_MTLS=0 + compose override running launcher_d.py (plain, same launcher as the
mTLS arm, prebuilt SSL context set from outside; service.py untouched); C = mTLS. The default
"as shipped" configuration appears only in a few reference B1 cells at `lan` (--arm default,
labelled reference, not an arm of the design). The generator is on the node: a deliberate
difference from M3/M4/M4-rerun (generator on another host); absolute latencies are not comparable.

Blocks (the user applies the netem profile by hand, with sudo, one block per profile; this script
never touches netem; it checks the profile through the TCP connect RTT evidence->site measured
from inside the evidence container, expected 2d, and aborts the block on a mismatch).
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
  tcpdump  20 fan-out episodes per arm for the user's tcpdump capture on `degraded`.
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
  (a)  withdrawal ~ n_RTT*R + service, n_RTT = 2 (D) or 3 (C), R = 2d (R = d for the `wan` sites of
       `mixed`); falsified if the median at regional/wan/mixed exceeds n_RTT*R + 3 x (median at
       `lan` of the SAME arm) beyond the CI. P-a1: default - D, last site, FANOUT 1, lan: +61.5 ms
       (falsified if the CI is outside [46, 77]); P-a2 (FANOUT 10): between +6 and +62 ms (outside
       [3, 75] falsifies); P-a4: C - D, last site, FANOUT 1, lan: +23.5 ms (outside [15, 32]).
  (c)  share of deliveries that end in pending, per profile/arm: regional ~8e-9, wan ~8-9e-6,
       mixed ~1e-6 (0 observed; >= 2 in the block falsifies), degraded D 0.0063-0.0115 (CP 95% CI
       outside [0.004, 0.015] falsifies), degraded C 0.028-0.064 (outside [0.025, 0.08] falsifies),
       extreme 1 (any direct delivery that succeeds falsifies). CONDITIONAL on the tcpdump
       calibration; frozen only after it.
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
# expected TCP connect RTT (ms) evidence -> site-i, as (lo, hi), per profile (profile check, no sudo needed)
RTT_EXPECT_MS = {
    "lan": {i: (0.0, 3.0) for i in range(N_SITES)},
    "regional": {i: (28.0, 55.0) for i in range(N_SITES)},
    "wan": {i: (110.0, 220.0) for i in range(N_SITES)},
    "degraded": {i: (280.0, 560.0) for i in range(N_SITES)},
    "extreme": {i: (800.0, 1500.0) for i in range(N_SITES)},
    "mixed": {**{i: (0.0, 3.0) for i in range(5)}, **{i: (55.0, 110.0) for i in range(5, 10)}},
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


_LOG = re.compile(r'^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z\s.*"POST (/[^ ]*) HTTP/1\.1" (\d{3})')


def _ts(date: str, frac: str | None) -> float:
    base = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    return base + (float(frac) if frac else 0.0)


def parse_post_lines(text: str, path_prefix: str) -> list[tuple[float, str, int]]:
    """(timestamp, path, status) of every access-log line of a POST whose path starts with
    path_prefix, from `docker logs -t` text (RFC3339Nano daemon timestamps, same clock as t0)."""
    out = []
    for line in text.splitlines():
        m = _LOG.match(line)
        if m and m.group(3).startswith(path_prefix):
            out.append((_ts(m.group(1), m.group(2)), m.group(3), int(m.group(4))))
    return out


def first_after(lines, t0: float, status: int = 200):
    for t, _p, s in sorted(lines):
        if t >= t0 and s == status:
            return t
    return None


def plan(profile: str, blocks: list[str], arms: list[str]) -> list[dict]:
    cells = []
    if "b1" in blocks:
        for arm in arms:
            for conc in FANOUTS:
                cells.append({"block": "b1", "arm": arm, "fanout": conc, "T": 5, "episodes": B1_EPISODES[profile]})
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


class ClientTimeout(Exception):
    """A client-side timeout: the episode/trial is EXCLUDED from the statistics, never counted as a service failure."""


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
        files = f"-f {gen}" + (f" -f {self.home}/dib_tnsm/m67/override_d.yml" if self.arm == "D" else "")
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

    def client(self, identity: str | None):
        import httpx
        import ssl
        key = identity if self.mtls else None
        if key not in self._clients:
            verify = True
            if self.mtls:
                ctx = ssl.create_default_context(cafile=str(self.pki / "ca.crt"))
                ctx.load_cert_chain(str(self.pki / f"{identity}.crt"), str(self.pki / f"{identity}.key"))
                verify = ctx
            self._clients[key] = httpx.Client(verify=verify)
        return self._clients[key]

    def req(self, method: str, url: str, identity: str | None, timeout: float, **kw):
        import httpx
        try:
            return self.client(identity).request(method, url, timeout=httpx.Timeout(connect=5.0, read=timeout, write=5.0, pool=5.0), **kw)
        except httpx.TimeoutException as exc:
            raise ClientTimeout(f"{method} {url}: {exc!r}") from exc

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
        env.req("POST", f"{env.site(i)}/query", f"op-site-{i}", timeout, json=body)
        env.req("POST", f"{env.site(i)}/commit", f"op-site-{i}", timeout, json=body)

    with ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(one, sites))
    return sid


def episode_b1(env: Env, profile: str, tag: str, e: int, setup: bool = True) -> dict:
    row = {"episode": e, "excluded": False}
    ep = f"m67-{tag}-{e}.example"
    tmo = client_timeout_s(profile, env.arm, env.fanout)
    try:
        if setup:
            sid = setup_fact(env, ep, list(range(N_SITES)), 30.0 if profile != "extreme" else 90.0)
        else:
            sid = env.req("POST", f"{env.ev}/seed", "admin", 30.0, json={"device_type": "cam-a", "endpoint": ep}).json()["id"]
        t0 = time.time()
        r = env.req("POST", f"{env.ev}/dispute", "op-site-1", tmo, json={"device_type": "cam-a", "endpoint": ep, "site_id": "site-1"})
        t_resp = time.time()
        row.update(t0=t0, t_resp=t_resp, status=r.status_code, dispute_rtt_s=t_resp - t0, score_id=sid)
        pend = {}
        for i in range(N_SITES):
            items = env.req("GET", f"{env.ev}/pending/site-{i}", f"site-{i}", 5.0).json()["pending"]
            pend[i] = sum(1 for it in items if it["score_id"] == sid)
        row["pending_after_response"] = pend
        deadline = t_resp + b_online(profile, env.arm, env.T) + 3.0
        while sum(pend.values()) and time.time() < deadline:
            time.sleep(0.5)
            for i in [i for i, n in pend.items() if n]:
                items = env.req("GET", f"{env.ev}/pending/site-{i}", f"site-{i}", 5.0).json()["pending"]
                pend[i] = sum(1 for it in items if it["score_id"] == sid)
        row["pending_left"] = dict(pend)
        applied, acked = {}, {}
        evlog = parse_post_lines(env.logs("dibtnsm-evidence-1", t0), "/pending/")
        for i in range(N_SITES):
            applied[i] = first_after(parse_post_lines(env.logs(f"dibtnsm-site-{i}-1", t0), "/apply_fanout"), t0)
            acked[i] = first_after([x for x in evlog if x[1] == f"/pending/site-{i}/ack"], t0)
        row["plog_apply_ts"], row["plog_ack_ts"] = applied, acked
        row["withdrawn_plog_s"] = {i: (None if t is None else t - t0) for i, t in applied.items()}
    except ClientTimeout as exc:
        row.update(excluded=True, client_timeout=str(exc)[:200])
    time.sleep(0.5)
    return row


def trial_b2kill(env: Env, profile: str, k: int, trial: int, l_dns: float | None) -> dict:
    row = {"trial": trial, "k": k, "excluded": False}
    tmo = client_timeout_s(profile, env.arm, env.fanout, l_dns)
    try:
        eps, ids = [f"m67-b2-{env.arm}-T{int(env.T)}-k{k}-t{trial}-{j}.example" for j in range(k)], []
        for ep in eps:
            sid = env.req("POST", f"{env.ev}/seed", "admin", 30.0, json={"device_type": "cam-a", "endpoint": ep}).json()["id"]
            ids.append(sid)
            body = {"device_type": "cam-a", "endpoint": ep}
            env.req("POST", f"{env.site(3)}/query", "op-site-3", 30.0, json=body)
            env.req("POST", f"{env.site(3)}/commit", "op-site-3", 30.0, json=body)
        env.sh(env.compose() + "kill site-3")
        t_kill = time.time()
        for ep in eps:
            body = {"device_type": "cam-a", "endpoint": ep}
            env.req("POST", f"{env.ev}/dispute", "op-site-1", tmo, json={**body, "site_id": "site-1"})
            env.req("POST", f"{env.ev}/dispute", "op-site-2", tmo, json={**body, "site_id": "site-2"})
            env.req("POST", f"{env.ev}/restore", "admin", tmo, json=body)
        pend = env.req("GET", f"{env.ev}/pending/site-3", "site-3", 5.0).json()["pending"]
        row["pending_queued_for_site3"] = len(pend)
        env.sh(env.compose() + "start site-3")
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
        row.update(t_up=t_up, t_withdrawn=t_withdrawn, bound_s=bound,
                   up_after_start_s=None if t_up is None else t_up - t_start,
                   convergence_s=None if t_withdrawn is None else t_withdrawn - t_start,
                   violation_over_bound=(t_withdrawn is None) or (t_withdrawn - t_start > bound))
        if t_withdrawn is not None:
            states = [env.req("GET", f"{env.site(3)}/state/{sid}", "op-site-3", 5.0).json()["state"] for sid in ids]
            row["final_states"] = {s: states.count(s) for s in set(states)}
            row["final_all_monitor_only"] = all(s == "monitor-only" for s in states)
    except ClientTimeout as exc:
        row.update(excluded=True, client_timeout=str(exc)[:200])
    return row


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


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
    manifest = {"started_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv, "profile": a.profile, "blocks": a.block,
                "seed": a.seed, "cell_order": cells, "node_tree": tree, "generator_host": platform.node(),
                "generator_is_node": True, "clock": "time.time() = CLOCK_REALTIME of the node (same clock as docker logs -t)",
                "plog_thresholds": thresholds, "measure_rule": "per profile from the thresholds file" if thresholds else "dispute-rtt (no P-log calibration applied)",
                "node_service_sha256": sha(Path(f"{tree}/code/src/dib/registry/distributed/service.py")),
                "launcher_d_sha256": sha(Path(f"{tree}/experiments_tnsm/m3_distributed/launcher_d.py")),
                "note_launcher_d": "_HTTP_TLS is set from outside by launcher_d.py; service.py unmodified",
                "run_py_sha256": sha(Path(__file__)), "discard_rule": rule,
                "disk_start": subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.splitlines()[-1]}
    log = (out / "cells.jsonl").open("a")
    for k, cell in enumerate(cells):
        arm, T, fo = cell["arm"], cell["T"], cell["fanout"]
        env = Env(tree, arm, fo, T, pki)
        env.up()
        try:
            ready = env.healthy()
            bg = nm.idle_window(12.0, project="dibtnsm")
            flagged = bg["other_cores"] > rule["max_other_cores"] or bg["steal_pct"] > rule["max_steal_pct"]
            rtt = env.measure_rtt_ms()
            ok, bad = rtt_matches(a.profile, rtt)
            rec = {"cell": k, "cell_spec": cell, "profile": a.profile, "ready_s": ready, "background_idle": bg, "flagged_pre": flagged,
                   "rtt_ms_evidence_to_site": rtt, "profile_check_ok": ok, "profile_check_bad": bad, "budget": cell_budget(cell, a.profile)}
            if not ok:
                rec["aborted"] = "profile check failed: the claimed netem profile does not match the measured RTT"
                log.write(json.dumps(rec) + "\n"); log.flush()
                print(f"[{k + 1}/{len(cells)}] ABORT profile check: {bad}", flush=True)
                break
            sampler = Sampler(interval=1.0, project="dibtnsm", pid=os.getpid())
            sampler.start()
            t_cell0 = time.time()
            rows = []
            tag = f"{a.profile}-{arm}-f{fo}-T{int(T)}"
            if cell["block"] in ("b1", "tcpdump"):
                if cell["block"] == "tcpdump":
                    print(f"CAPTURE_WINDOW_START {time.time():.3f} arm={arm}", flush=True)
                order = list(range(cell["episodes"]))
                for e in order:
                    rows.append(episode_b1(env, a.profile, tag, e, setup=(cell["block"] == "b1")))
                if cell["block"] == "tcpdump":
                    print(f"CAPTURE_WINDOW_END {time.time():.3f} arm={arm}", flush=True)
            else:
                for t in range(cell["trials"]):
                    rows.append(trial_b2kill(env, a.profile, cell["k"], t, a.l_dns))
            t_cell1 = time.time()
            samples = sampler.stop()
            rec.update(rows=rows, t_cell=[t_cell0, t_cell1], excluded=sum(1 for r in rows if r.get("excluded")),
                       generator_samples=samples)
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(f"[{k + 1}/{len(cells)}] {cell['block']} {arm} f={fo} T={T} rows={len(rows)} excluded={rec['excluded']} flagged={flagged} "
                  f"bg_other={bg['other_cores']} steal={bg['steal_pct']}", flush=True)
        finally:
            env.down()
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["disk_end"] = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.splitlines()[-1]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


def main() -> int:
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
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit; nothing is touched")
    a = ap.parse_args()
    blocks = a.block.split(",")
    arms = a.arms.split(",")
    cells = plan(a.profile, blocks, arms)
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
