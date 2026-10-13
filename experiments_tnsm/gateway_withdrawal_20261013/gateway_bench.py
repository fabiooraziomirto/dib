"""End-to-end withdrawal to the OpenWrt/osMUD gateway, with timestamps t0..t3
(pre-registration: docs/audit/121; hypotheses H-G1..H-G6 and validity rules there).

Topology (the existing testbed, not redesigned): the distributed service
(1 evidence + 10 site containers, code/src/dib/registry/distributed, mTLS by default)
and the openwrt/ compose (OpenWrt 23.05.5 router running osMUD 852918e with -i,
device, allowed-service, blocked-service, mud-server), linked with veth pairs exactly
as openwrt/run_distributed.sh. site-0 is the enforcing site (lab-a); the dispute is
reported by site-1 (its operator certificate under mTLS).

Facts (one device type `camera`, one MUD file): SUBJECT allowed.test tcp/8080 is
disputed; CONTROL allowed.test tcp/9090 is never disputed.

Clock: every timestamp is time.monotonic() of the host kernel (harness threads, the
prober started with nsenter in the device netns). The containers share the kernel and
no time namespace (checked: /proc/<pid>/ns/time identical) so all timestamps are on
one CLOCK_MONOTONIC.

Observation points (each poll records send and receive time; an event lies in
(send of the last poll showing the old value, receive of the first poll showing the
new one]):
  t0  evidence GET /scores shows status 'disputed'      (poller, admin identity)
      also t0s/t0r = send/receive of the POST /dispute itself
  t1  site-0 GET /state/{id} shows state 'disputed'      (poller, site-0 operator)
  ex  harness: GET /export_mud from site-0, file written  (orchestrated by THIS harness:
      the architecture has no push from the site to the gateway)
  rl  harness: osMUD killed and router-entrypoint.sh re-run (the prototype's reload:
      there is no native reload trigger, openwrt/README.md)
  tf  router nft chain forward_lan shows no MUD accept rule (the entrypoint flush)
  t2  router nft chain forward_lan shows exactly the accept rules of the exported MUD
  t3  new TCP connections to the subject start failing (prober, every 20 ms)
  t3e the subject's ESTABLISHED connection stops echoing (prober, every 50 ms)

Each episode then runs the recovery checks: global restore alone (subject must stay
blocked), fresh local commit (subject allowed again, time measured). Veto episodes add a
local revoke at site-0 before the restore: commit must be refused (409) after the
restore, the subject must stay blocked, and only local restore + commit re-enables it.

No retry of a measured operation. A setup step that fails is retried once
(repair()), then the episode is recorded as setup_invalid; 3 consecutive setup
failures stop the campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CODE = ROOT / "code"
DIST = CODE / "src/dib/registry/distributed"
OPENWRT = ROOT / "openwrt"
sys.path.insert(0, str(CODE / "src"))
sys.path.insert(0, str(CODE))

PY = sys.executable
SUBJECT = {"device_type": "camera", "endpoint": "allowed.test", "protocol": "tcp", "port": 8080}
CONTROL = {"device_type": "camera", "endpoint": "allowed.test", "protocol": "tcp", "port": 9090}
MUD_URL = "http://mud-server:8000/camera.json"
ALLOWED_IP = "172.31.0.10"
N_SITES = 10
CLUSTER_PROJECT = "dibgw"
ROUTER_PROJECT = "dibgwr"
NETEM = {"lan": None, "wan": (80.0, 1.0), "degraded": (200.0, 5.0)}  # as experiments_tnsm/m67_retraction/profile_ctl.py:22

RULE_RE = re.compile(r"tcp dport (\d+) .*jump accept_to_wan")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd, check=True, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True, **kw)


class SetupError(RuntimeError):
    pass


# ---------------------------------------------------------------------- infrastructure
class Testbed:
    def __init__(self, out: Path, pki: Path, mtls: bool, log):
        self.out, self.pki, self.mtls, self.log = out, pki, mtls, log
        self.gw = out / "gw"            # mounted at /artifacts in router and mud-server
        self.gw.mkdir(parents=True, exist_ok=True)
        self.scheme = "https" if mtls else "http"
        self.ev = f"{self.scheme}://localhost:18100"
        self.site0 = f"{self.scheme}://localhost:18110"
        self.clients: dict[str, httpx.Client] = {}
        self.cluster_compose = out / "cluster-compose.yml"
        self.router_env = dict(os.environ, ARTIFACT_DIR=str(self.gw), DOCKER_BUILDKIT="0")
        self.provenance: dict = {}
        self.ids: dict[str, int] = {}

    # -- clients
    def client(self, who: str, timeout: float = 30.0) -> httpx.Client:
        if not self.mtls:
            return httpx.Client(timeout=timeout, trust_env=False)
        from dib.registry.distributed import mtls
        ctx = mtls.client_context(self.pki / f"{who}.crt", self.pki / f"{who}.key", self.pki / "ca.crt")
        return httpx.Client(timeout=timeout, verify=ctx, trust_env=False)

    def c(self, who: str) -> httpx.Client:
        if who not in self.clients:
            self.clients[who] = self.client(who)
        return self.clients[who]

    # -- cluster
    def make_pki(self) -> None:
        from scripts.make_dist_pki import build
        nb = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta
        manifest = build(self.pki, N_SITES, nb - timedelta(minutes=10), 72.0, ["camera"])
        (self.out / "pki_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

    def up_cluster(self) -> None:
        env = dict(os.environ, DIB_DIST_N_SITES=str(N_SITES), DIB_DIST_MTLS="1" if self.mtls else "0",
                   DIB_DIST_PKI_DIR=str(self.pki))
        text = run([PY, str(DIST / "generate_compose.py")], env=env).stdout
        text = text.replace("context: ../../../..", f"context: {CODE}")
        self.cluster_compose.write_text(text)
        dc = ["docker", "compose", "-p", CLUSTER_PROJECT, "-f", str(self.cluster_compose)]
        run(dc + ["down", "-v", "--remove-orphans"], check=False)
        r = run(dc + ["up", "-d", "--build"], check=False)
        (self.out / "cluster_up.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            raise SetupError("cluster up failed")
        admin = self.c("admin")
        deadline = time.monotonic() + 90
        urls = [self.ev] + [f"{self.scheme}://localhost:{18110 + i}" for i in range(N_SITES)]
        pending = set(urls)
        while pending and time.monotonic() < deadline:
            for u in list(pending):
                try:
                    if admin.get(u + "/health").status_code == 200:
                        pending.discard(u)
                except httpx.HTTPError:
                    pass
            time.sleep(0.5)
        if pending:
            raise SetupError(f"cluster health timeout: {sorted(pending)}")

    def cluster_containers(self) -> dict[str, str]:
        names = run(["docker", "compose", "-p", CLUSTER_PROJECT, "-f", str(self.cluster_compose), "ps",
                     "--format", "{{.Service}} {{.Name}}"]).stdout.split("\n")
        return dict(x.split() for x in names if x.strip())

    def verify_cluster_images(self, label: str) -> dict:
        """sha256 of /app/service.py and mtls.py INSIDE every container vs the tree; raises on mismatch."""
        want = {"/app/service.py": sha(DIST / "service.py"), "/app/dib/registry/distributed/mtls.py": sha(DIST / "mtls.py")}
        seen = {}
        for svc, name in sorted(self.cluster_containers().items()):
            out = run(["docker", "exec", name, "sha256sum", *want]).stdout.split()
            got = dict(zip(out[1::2], out[0::2]))
            image = run(["docker", "inspect", "-f", "{{.Image}}", name]).stdout.strip()
            seen[svc] = {"container": name, "image": image, **got}
            if got != want:
                raise SetupError(f"{label}: image mismatch in {name}: {got} != {want}")
        self.provenance[f"cluster_{label}"] = seen
        return seen

    # -- router testbed
    def dcr(self, *args, check=True):
        return run(["docker", "compose", "-p", ROUTER_PROJECT, "-f", str(OPENWRT / "docker-compose.yml"), *args],
                   check=check, env=self.router_env)

    def cid(self, service: str) -> str:
        return self.dcr("ps", "-q", service).stdout.strip()

    def pid(self, service: str) -> int:
        return int(run(["docker", "inspect", "-f", "{{.State.Pid}}", self.cid(service)]).stdout.strip())

    def rexec(self, service: str, *cmd, detach=False, check=True):
        return run(["docker", "exec", *(["-d"] if detach else []), self.cid(service), *cmd], check=check)

    def up_router(self) -> None:
        self.dcr("down", "--remove-orphans", check=False)
        r = self.dcr("up", "-d", "--build", check=False)
        (self.out / "router_up.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            raise SetupError("router testbed up failed")
        rp = self.pid("router")

        def link(service, router_if, peer_if, router_cidr, peer_cidr, tag):
            pp = self.pid(service)
            a, b = f"dg{tag}r", f"dg{tag}p"
            run(["ip", "link", "add", a, "type", "veth", "peer", "name", b])
            run(["ip", "link", "set", a, "netns", str(rp)])
            run(["ip", "link", "set", b, "netns", str(pp)])
            run(["nsenter", "-t", str(rp), "-n", "ip", "link", "set", a, "name", router_if])
            run(["nsenter", "-t", str(pp), "-n", "ip", "link", "set", b, "name", peer_if])
            run(["nsenter", "-t", str(rp), "-n", "ip", "addr", "add", router_cidr, "dev", router_if])
            run(["nsenter", "-t", str(pp), "-n", "ip", "addr", "add", peer_cidr, "dev", peer_if])
            run(["nsenter", "-t", str(rp), "-n", "ip", "link", "set", router_if, "up"])
            run(["nsenter", "-t", str(pp), "-n", "ip", "link", "set", peer_if, "up"])

        link("device", "lan0", "eth0", "172.30.0.254/24", "172.30.0.2/24", "0")
        link("allowed-service", "wan0", "eth0", "172.31.0.9/30", "172.31.0.10/30", "1")
        link("blocked-service", "wan1", "eth0", "172.31.0.13/30", "172.31.0.14/30", "2")
        link("mud-server", "wan2", "eth0", "172.31.0.17/30", "172.31.0.18/30", "3")
        self.rexec("device", "sh", "-c", "ip route add default via 172.30.0.254; echo '172.31.0.10 allowed.test' >> /etc/hosts; echo '172.31.0.14 blocked.test' >> /etc/hosts")
        self.rexec("allowed-service", "ip", "route", "add", "default", "via", "172.31.0.9")
        self.rexec("blocked-service", "ip", "route", "add", "default", "via", "172.31.0.13")
        self.rexec("mud-server", "ip", "route", "add", "default", "via", "172.31.0.17")
        run(["docker", "cp", str(HERE / "echo_stream.py"), f"{self.cid('allowed-service')}:/echo_stream.py"])
        self.rexec("allowed-service", "python", "/echo_stream.py", "--tcp", "8080", "--tcp", "9090", detach=True)
        self.rexec("blocked-service", "python", "/echo_service.py", "--tcp", "8080", detach=True)
        self.rexec("mud-server", "python", "-m", "http.server", "8000", "--directory", "/artifacts", detach=True)
        self.rexec("router", "sh", "-c", "echo '172.31.0.10 allowed.test' >> /etc/hosts; echo '172.31.0.14 blocked.test' >> /etc/hosts; echo '172.31.0.18 mud-server' >> /etc/hosts")
        self.router_pid, self.device_pid = rp, self.pid("device")
        # one clock: no time namespace in the containers
        host_t = os.readlink("/proc/self/ns/time")
        self.provenance["time_namespace"] = {"host": host_t, **{s: os.readlink(f"/proc/{self.pid(s)}/ns/time")
                                                                for s in ("router", "device")}}
        if len(set(self.provenance["time_namespace"].values())) != 1:
            raise SetupError("containers use a separate time namespace")

    def verify_router(self, label: str) -> dict:
        files = ["/usr/sbin/osmud", "/usr/local/bin/router-entrypoint.sh", "/etc/osmud/commit_ip_fw_rules.sh",
                 "/etc/osmud/rollback_ip_fw_rules.sh", "/etc/osmud/create_ip_fw_rule.sh", "/etc/osmud/remove_ip_fw_rule.sh"]
        out = self.rexec("router", "sha256sum", *files).stdout.split()
        got = dict(zip(out[1::2], out[0::2]))
        tree = {"/usr/local/bin/router-entrypoint.sh": sha(OPENWRT / "router-entrypoint.sh"),
                "/etc/osmud/commit_ip_fw_rules.sh": sha(OPENWRT / "commit_ip_fw_rules.sh"),
                "/etc/osmud/rollback_ip_fw_rules.sh": sha(OPENWRT / "rollback_ip_fw_rules.sh")}
        for k, v in tree.items():
            if got[k] != v:
                raise SetupError(f"router {k} differs from the tree")
        image = run(["docker", "inspect", "-f", "{{.Image}}", self.cid("router")]).stdout.strip()
        self.provenance[f"router_{label}"] = {"image": image, **got}
        return got

    # -- lifecycle helpers
    def post(self, who: str, url: str, body: dict, expect=(200,)) -> httpx.Response:
        r = self.c(who).post(url, json=body)
        if r.status_code not in expect:
            raise SetupError(f"POST {url} as {who}: {r.status_code} {r.text[:200]}")
        return r

    def state(self, sid: int) -> str | None:
        r = self.c("op-site-0").get(f"{self.site0}/state/{sid}")
        return r.json()["state"] if r.status_code == 200 else None

    def score(self, fact: dict) -> dict:
        return self.c("admin").get(f"{self.ev}/scores", params=fact).json()

    def export(self) -> tuple[float, float, list[int], str]:
        s = time.monotonic()
        r = self.c("op-site-0").get(f"{self.site0}/export_mud", params={"device_type": "camera", "mud_url": MUD_URL})
        r.raise_for_status()
        doc = r.json()
        tmp = self.gw / "camera.json.tmp"
        tmp.write_text(json.dumps(doc, indent=2) + "\n")
        os.replace(tmp, self.gw / "camera.json")
        e = time.monotonic()
        ports = sorted(int(ace["matches"]["tcp"]["destination-port-range-or-operator"]["port"])
                       for acl in doc["ietf-access-control-list:access-lists"]["acl"] for ace in acl["aces"]["ace"]
                       if "tcp" in ace["matches"])
        return s, e, ports, hashlib.sha256((self.gw / "camera.json").read_bytes()).hexdigest()

    def reload(self) -> tuple[float, float]:
        s = time.monotonic()
        self.rexec("router", "sh", "-c", "test ! -f /run/osmud/osmud.pid || kill $(cat /run/osmud/osmud.pid)", check=False)
        self.rexec("router", "/usr/local/bin/router-entrypoint.sh", detach=True)
        return s, time.monotonic()

    def rules(self) -> frozenset | None:
        r = run(["nsenter", "-t", str(self.router_pid), "-m", "-n", "nft", "list", "chain", "inet", "fw4", "forward_lan"],
                check=False)
        if r.returncode:
            return None
        return frozenset(int(m.group(1)) for m in RULE_RE.finditer(r.stdout))

    def wait_rules(self, target: frozenset, after: float, timeout: float = 60.0, need_flush: bool = True):
        """Poll until the chain shows `target` (after a flush to no rule if need_flush). Returns (samples, tf, t2)."""
        samples, tf, t2 = [], None, None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            s = time.monotonic()
            v = self.rules()
            e = time.monotonic()
            samples.append((s, e, sorted(v) if v is not None else None))
            if s >= after:
                if tf is None and v is not None and len(v) == 0:
                    tf = (s, e)
                if v == target and (tf is not None or not need_flush):
                    t2 = (s, e)
                    break
            time.sleep(0.005)
        return samples, tf, t2

    # -- netem on the evidence container's link, both directions
    def evidence_ifaces(self) -> tuple[int, str]:
        name = self.cluster_containers()["evidence"]
        pid = int(run(["docker", "inspect", "-f", "{{.State.Pid}}", name]).stdout.strip())
        iflink = run(["nsenter", "-t", str(pid), "-n", "cat", "/sys/class/net/eth0/iflink"]).stdout.strip()
        host_if = next(l.split(":")[1].strip().split("@")[0] for l in run(["ip", "-o", "link"]).stdout.splitlines()
                       if l.split(":")[0].strip() == iflink)
        return pid, host_if

    def apply_profile(self, profile: str) -> dict:
        pid, host_if = self.evidence_ifaces()
        spec = NETEM[profile]
        for target in (["nsenter", "-t", str(pid), "-n", "tc"], ["tc"]):
            dev = "eth0" if target[0] == "nsenter" else host_if
            run(target + ["qdisc", "del", "dev", dev, "root"], check=False)
            if spec:
                run(target + ["qdisc", "add", "dev", dev, "root", "netem", "delay", f"{spec[0]}ms", "loss", f"{spec[1]}%"])
        shown = {"container_eth0": run(["nsenter", "-t", str(pid), "-n", "tc", "qdisc", "show", "dev", "eth0"]).stdout.strip(),
                 f"host_{host_if}": run(["tc", "qdisc", "show", "dev", host_if]).stdout.strip()}
        if spec and not all(f"delay {int(spec[0])}ms" in v for v in shown.values()):
            raise SetupError(f"netem not applied: {shown}")
        if not spec and any("netem" in v for v in shown.values()):
            raise SetupError(f"netem still present: {shown}")
        return shown

    def down(self) -> None:
        for c in self.clients.values():
            c.close()
        self.dcr("down", "--remove-orphans", check=False)
        run(["docker", "compose", "-p", CLUSTER_PROJECT, "-f", str(self.cluster_compose), "down", "-v", "--remove-orphans"],
            check=False)


# ---------------------------------------------------------------------- pollers / prober
class Poller(threading.Thread):
    """Polls fn() until stop; records (send, recv, value)."""

    def __init__(self, fn, period=0.005):
        super().__init__(daemon=True)
        self.fn, self.period, self.samples, self._stop_ev = fn, period, [], threading.Event()

    def run(self):
        while not self._stop_ev.is_set():
            s = time.monotonic()
            try:
                v = self.fn()
            except Exception as exc:  # noqa: BLE001 - recorded
                v = f"error:{type(exc).__name__}"
            self.samples.append((s, time.monotonic(), v))
            self._stop_ev.wait(self.period)

    def first(self, pred, after=0.0):
        """(send of last sample not matching, recv of first matching) for samples sent at/after `after`."""
        prev = None
        for s, e, v in self.samples:
            if s < after:
                continue
            if pred(v):
                return (prev, e)
            prev = s
        return None

    def stop(self):
        self._stop_ev.set()
        self.join(timeout=10)


class Prober:
    def __init__(self, tb: Testbed, path: Path):
        self.path = path
        self.proc = subprocess.Popen(
            ["nsenter", "-t", str(tb.device_pid), "-n", PY, str(HERE / "probe.py"), "--out", str(path),
             "--host", ALLOWED_IP, "--ports", "8080,9090"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return out

    def stop(self):
        self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def wait_traffic(prober: Prober, port: int, want_ok: bool, after: float, consecutive: int, timeout: float):
    """First time `consecutive` successive NEW probes to `port` started after `after` all have ok == want_ok.
    Returns the start time of the first of them, or None."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run_start, n = None, 0
        for r in prober.records():
            if r.get("k") != "new" or r.get("p") != port or r["s"] < after:
                continue
            if r["ok"] == want_ok:
                if n == 0:
                    run_start = r["s"]
                n += 1
                if n >= consecutive:
                    return run_start
            else:
                n = 0
        time.sleep(0.05)
    return None


def est_ok(prober: Prober) -> dict:
    opened = {r["p"]: r["ok"] for r in prober.records() if r.get("k") == "est_open"}
    return opened


# ---------------------------------------------------------------------- episode
def setup_post(tb: Testbed, who: str, url: str, fact: dict) -> None:
    """Setup-only request: up to 3 attempts, 1 s apart, on 5xx or transport errors (audit 121: setup retries)."""
    last = None
    for _ in range(3):
        try:
            r = tb.c(who).post(url, json=fact)
            if r.status_code < 500:
                if r.status_code != 200:
                    raise SetupError(f"POST {url}: {r.status_code} {r.text[:120]}")
                return
            last = f"{r.status_code}"
        except httpx.HTTPError as exc:
            last = type(exc).__name__
        time.sleep(1.0)
    raise SetupError(f"POST {url} failed 3 times ({last})")


def setup_active(tb: Testbed, ep_dir: Path) -> dict:
    """Bring both facts to Active at site-0 with the gateway enforcing them. Setup, not measured."""
    for fact in (SUBJECT, CONTROL):
        st = tb.state(tb.ids[fact["port"]])
        sc = tb.score(fact)
        if sc["status"] != "active":
            setup_post(tb, "admin", f"{tb.ev}/restore", fact)
            st = tb.state(tb.ids[fact["port"]])
        if st == "revoked":  # a local veto left by a failed episode
            setup_post(tb, "op-site-0", f"{tb.site0}/local_restore", fact)
            st = tb.state(tb.ids[fact["port"]])
        if st != "active":
            setup_post(tb, "op-site-0", f"{tb.site0}/commit", fact)
    s, e, ports, h = tb.export()
    if ports != [8080, 9090]:
        raise SetupError(f"setup export has ports {ports}")
    rs, re_ = tb.reload()
    _, tf, t2 = tb.wait_rules(frozenset({8080, 9090}), after=rs)
    if t2 is None:
        raise SetupError("setup: rules not applied")
    return {"export_ports": ports, "mud_sha256": h, "reload": [rs, re_], "tf_obs": tf, "t2_obs": t2}


def measure_withdrawal(tb: Testbed, ep: dict, ep_dir: Path, profile_wait: float) -> Prober:
    sid = tb.ids[8080]
    prober = Prober(tb, ep_dir / "probe.jsonl")
    pre = time.monotonic()
    ok_sub = wait_traffic(prober, 8080, True, pre, 5, 10)
    ok_ctl = wait_traffic(prober, 9090, True, pre, 5, 10)
    est = est_ok(prober)
    ep["precondition"] = {"subject_new_ok": ok_sub is not None, "control_new_ok": ok_ctl is not None,
                          "est_open": est}
    if ok_sub is None or ok_ctl is None or est.get(8080) is not True or est.get(9090) is not True:
        ep["status"] = "setup_invalid"
        ep["reason"] = "precondition: traffic not allowed before the dispute"
        return prober
    ev_client, s0_client = tb.client("admin", 10.0), tb.client("op-site-0", 10.0)
    ev_poll = Poller(lambda: ev_client.get(f"{tb.ev}/scores", params=SUBJECT).json()["status"])
    s0_poll = Poller(lambda: s0_client.get(f"{tb.site0}/state/{sid}").json()["state"])
    ev_poll.start(); s0_poll.start()
    time.sleep(0.3)  # both pollers have a baseline sample showing the old value
    dispute = {}

    def do_dispute():
        body = dict(SUBJECT, site_id="site-1")
        c = tb.client("op-site-1", 60.0) if tb.mtls else tb.client("x", 60.0)
        dispute["t0s"] = time.monotonic()
        try:
            r = c.post(f"{tb.ev}/dispute", json=body)
            dispute["status"], dispute["body"] = r.status_code, r.text[:200]
        except Exception as exc:  # noqa: BLE001 - a failure of the measured operation
            dispute["error"] = f"{type(exc).__name__}: {exc}"[:200]
        dispute["t0r"] = time.monotonic()
        c.close()

    th = threading.Thread(target=do_dispute, daemon=True)
    th.start()
    while "t0s" not in dispute:
        time.sleep(0.001)
    t0s = dispute["t0s"]
    deadline = time.monotonic() + 90
    t1 = None
    while time.monotonic() < deadline:
        t1 = s0_poll.first(lambda v: v == "disputed", after=t0s - 0.3)
        if t1:
            break
        time.sleep(0.002)
    ep["t_react"] = time.monotonic()
    if t1 is None:
        th.join(timeout=60)
        ev_poll.stop(); s0_poll.stop()
        ep.update(status="op_failed", reason="t1 not observed within 90 s", dispute=dispute)
        return prober
    ex_s, ex_e, ports, mud_h = tb.export()
    rl_s, rl_e = tb.reload()
    samples, tf, t2 = tb.wait_rules(frozenset({9090}), after=rl_s, timeout=60)
    th.join(timeout=90)
    t0 = ev_poll.first(lambda v: v == "disputed", after=t0s - 0.3)
    time.sleep(0.5)
    ev_poll.stop(); s0_poll.stop()
    ep.update(dispute=dispute, t0_obs=t0, t1_obs=t1, export=[ex_s, ex_e], export_ports=ports, export_mud_sha256=mud_h,
              reload=[rl_s, rl_e], tf_obs=tf, t2_obs=t2,
              poll_periods={"evidence": _gaps(ev_poll.samples), "site0": _gaps(s0_poll.samples), "rules": _gaps(samples)})
    (ep_dir / "polls.json").write_text(json.dumps({"evidence": ev_poll.samples, "site0": s0_poll.samples,
                                                    "rules": samples}) + "\n")
    if t2 is None:
        ep.update(status="op_failed", reason="t2 not observed within 60 s")
        return prober
    time.sleep(profile_wait)  # observation window after t2
    ep["window_end"] = time.monotonic()
    return prober


def _gaps(samples) -> dict:
    gaps = sorted(b[0] - a[0] for a, b in zip(samples, samples[1:]))
    if not gaps:
        return {}
    return {"n": len(samples), "median_s": gaps[len(gaps) // 2], "max_s": gaps[-1]}


def blocked_for(prober: Prober, port: int, start: float, seconds: float) -> dict:
    time.sleep(seconds)
    recs = [r for r in prober.records() if r.get("k") == "new" and r.get("p") == port and r["s"] >= start]
    return {"probes": len(recs), "ok": sum(r["ok"] for r in recs)}


def recovery(tb: Testbed, ep: dict, ep_dir: Path, prober: Prober, veto: bool) -> None:
    sid = tb.ids[8080]
    rec = ep["recovery"] = {}
    if veto:
        r = tb.c("op-site-0").post(f"{tb.site0}/local_revoke", json=SUBJECT)
        rec["local_revoke_status"] = r.status_code
    # R1: global restore alone
    t = time.monotonic()
    r = tb.c("admin").post(f"{tb.ev}/restore", json=SUBJECT)
    rec["restore_status"] = r.status_code
    want = "revoked" if veto else "monitor-only"
    deadline = time.monotonic() + 90
    st = None
    while time.monotonic() < deadline:
        st = tb.state(sid)
        if st == want:
            break
        time.sleep(0.05)
    rec["site0_state_after_restore"] = st
    rec["site0_origin_after_restore"] = tb.c("op-site-0").get(f"{tb.site0}/state/{sid}").json().get("origin")
    if veto:
        r = tb.c("op-site-0").post(f"{tb.site0}/commit", json=SUBJECT)
        rec["commit_over_veto_status"] = r.status_code
    _, _, ports, _ = tb.export()
    rec["export_ports_after_restore"] = ports
    rl_s, rl_e = tb.reload()
    _, tf, t2 = tb.wait_rules(frozenset({9090}), after=rl_s)
    rec["restore_rules_applied"] = t2 is not None
    rec["restore_reload"], rec["restore_tf_obs"], rec["restore_t2_obs"] = [rl_s, rl_e], tf, t2
    rec["subject_after_restore"] = blocked_for(prober, 8080, t2[0] if t2 else time.monotonic(), 3.0)
    # R2: (veto: local restore first) then fresh local commit
    if veto:
        r = tb.c("op-site-0").post(f"{tb.site0}/local_restore", json=SUBJECT)
        rec["local_restore_status"] = r.status_code
        _, _, ports2, _ = tb.export()
        rec["export_ports_after_local_restore"] = ports2
    t_commit = time.monotonic()
    r = tb.c("op-site-0").post(f"{tb.site0}/commit", json=SUBJECT)
    rec["commit_status"] = r.status_code
    ex_s, ex_e, ports, _ = tb.export()
    rec["export_ports_after_commit"] = ports
    rl_s, rl_e = tb.reload()
    _, tf, t2 = tb.wait_rules(frozenset({8080, 9090}), after=rl_s)
    first_ok = wait_traffic(prober, 8080, True, t_commit, 3, 60)
    rec.update(t_commit=t_commit, export=[ex_s, ex_e], reload=[rl_s, rl_e], tf_obs=tf, t2_obs=t2, reenabled_new_conn=first_ok)


# ---------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pki", type=Path, required=True, help="directory OUTSIDE the repository for the private keys")
    ap.add_argument("--profile", choices=sorted(NETEM), default="lan")
    ap.add_argument("--episodes", type=int, default=30)
    ap.add_argument("--veto-episodes", type=int, default=0)
    ap.add_argument("--window", type=float, default=15.0, help="observation window after t2 (s)")
    ap.add_argument("--no-mtls", action="store_true")
    ap.add_argument("--keep-up", action="store_true", help="leave the testbed running (pilot)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    logf = (a.out / "harness.log").open("a", buffering=1)

    def log(msg):
        line = f"{now_utc()} {msg}"
        print(line, flush=True)
        logf.write(line + "\n")

    tb = Testbed(a.out, a.pki, not a.no_mtls, log)
    manifest = {
        "prereg": "docs/audit/121", "started_utc": now_utc(), "profile": a.profile, "mtls": tb.mtls,
        "episodes_requested": a.episodes, "veto_episodes_requested": a.veto_episodes, "window_s": a.window,
        "commit": run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip(),
        "dirty": run(["git", "status", "--porcelain"], cwd=ROOT).stdout.splitlines(),
        "tree_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [DIST / "service.py", DIST / "mtls.py", DIST / "Dockerfile",
                         DIST / "generate_compose.py", OPENWRT / "Dockerfile.router", OPENWRT / "router-entrypoint.sh",
                         OPENWRT / "docker-compose.yml", HERE / "gateway_bench.py", HERE / "probe.py", HERE / "echo_stream.py"]},
        "python": sys.version.split()[0], "host": {"nproc": os.cpu_count(), "loadavg_start": os.getloadavg()},
        "clock": "CLOCK_MONOTONIC of the host kernel (time.monotonic), shared by containers (no time namespace)",
        "probes": {"new_conn_period_s": 0.02, "new_conn_timeout_s": 0.5, "est_period_s": 0.05, "est_timeout_s": 1.0,
                   "poll_sleep_s": 0.005},
        "reload": "kill osmud + docker exec -d router-entrypoint.sh (as openwrt/run_distributed.sh), orchestrated by the harness",
        "mud_signature": "unsigned MUD file; osMUD runs with -i (signature validation bypass), openwrt/README.md",
    }
    episodes = []
    try:
        if tb.mtls:
            tb.make_pki()
        log("cluster up"); tb.up_cluster(); tb.verify_cluster_images("start")
        log("router up"); tb.up_router(); tb.verify_router("start")
        manifest["netem"] = tb.apply_profile(a.profile)
        for fact in (SUBJECT, CONTROL):
            tb.post("admin", f"{tb.ev}/seed", fact)
            tb.ids[fact["port"]] = tb.score(fact)["id"]
            tb.post("op-site-0", f"{tb.site0}/query", fact)
            tb.post("op-site-0", f"{tb.site0}/commit", fact)
        s, e, ports, h = tb.export()
        (tb.gw / "dhcp_event.txt").write_text(
            "2026-08-08T12:00:00|NEW|OpenWRT.lan|DHCP|1,3,6,15|MUD|http://mud-server:8000/camera.json|-|02:42:ac:1e:00:02|172.30.0.2|camera|\n")
        tb.rexec("router", "sh", "-c", "i=0; until curl -fsS http://mud-server:8000/camera.json >/dev/null; do i=$((i+1)); test \"$i\" -lt 20; sleep 1; done")
        rs, _ = tb.reload()
        _, _, t2 = tb.wait_rules(frozenset({8080, 9090}), after=rs, need_flush=False)
        if t2 is None:
            raise SetupError("initial rules not applied")
        # gateway sanity, once: wrong port and wrong destination are refused
        sanity = {}
        for name, cmd in (("wrong_port_8081", "printf x | nc -w 2 allowed.test 8081"),
                          ("wrong_destination", "printf x | nc -w 2 blocked.test 8080"),
                          ("subject_8080", "printf x | nc -w 2 allowed.test 8080")):
            sanity[name] = tb.rexec("device", "sh", "-c", cmd, check=False).returncode == 0 and True or False
        manifest["gateway_sanity"] = sanity
        log(f"sanity {sanity}")
        plan = ["std"] * a.episodes + ["veto"] * a.veto_episodes
        consecutive_setup_fail = 0
        for i, kind in enumerate(plan):
            ep_dir = a.out / f"ep{i:03d}"
            ep_dir.mkdir()
            ep = {"episode": i, "kind": kind, "profile": a.profile, "started": time.monotonic(),
                  "loadavg": os.getloadavg(), "status": "running"}
            prober = None
            try:
                try:
                    ep["setup"] = setup_active(tb, ep_dir)
                except (SetupError, httpx.HTTPError) as exc:
                    log(f"ep{i}: setup failed once ({exc}); repair")
                    ep["setup_retry"] = str(exc)[:200]
                    ep["setup"] = setup_active(tb, ep_dir)
                prober = measure_withdrawal(tb, ep, ep_dir, a.window)
                if ep["status"] == "running":
                    recovery(tb, ep, ep_dir, prober, veto=(kind == "veto"))
                    ep["status"] = "complete"
                consecutive_setup_fail = 0 if ep["status"] != "setup_invalid" else consecutive_setup_fail + 1
            except (SetupError, httpx.HTTPError) as exc:
                ep.setdefault("status", "setup_invalid")
                if ep["status"] == "running":
                    ep["status"] = "setup_invalid"
                ep["reason"] = f"{type(exc).__name__}: {exc}"[:300]
                consecutive_setup_fail += 1
            finally:
                if prober:
                    prober.stop()
            ep["probe_records"] = len(prober.records()) if prober else 0
            ep["ended"] = time.monotonic()
            (ep_dir / "episode.json").write_text(json.dumps(ep, indent=1) + "\n")
            for f in ("probe.jsonl", "polls.json"):
                if (ep_dir / f).exists():
                    run(["gzip", "-n", str(ep_dir / f)])
            episodes.append({"episode": i, "kind": kind, "status": ep["status"], "reason": ep.get("reason")})
            log(f"ep{i} {kind}: {ep['status']} {ep.get('reason') or ''}")
            if consecutive_setup_fail >= 3:
                log("3 consecutive setup failures: campaign stopped")
                manifest["stopped"] = "3 consecutive setup failures"
                break
        tb.verify_cluster_images("end")
        tb.verify_router("end")
    except SetupError as exc:
        manifest["fatal"] = str(exc)
        log(f"FATAL {exc}")
    finally:
        manifest.update(episodes=episodes, provenance=tb.provenance, finished_utc=now_utc())
        manifest["host"]["loadavg_end"] = os.getloadavg()
        try:
            r = tb.dcr("logs", "router", check=False)
            (a.out / "router.log").write_text(r.stdout[-200000:])
        except Exception:  # noqa: BLE001
            pass
        (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        if not a.keep_up:
            try:
                tb.apply_profile("lan")
            except Exception:  # noqa: BLE001
                pass
            tb.down()
    return 0 if "fatal" not in manifest else 2


if __name__ == "__main__":
    raise SystemExit(main())
