"""Driver side of netem_watch2.sh: request a netem profile WITHOUT sudo and check, from the watcher's own record, that it is in place.
No docker, no ssh, no sudo, no change to netem: it writes DIR/profile.request (atomically, closed list) and reads DIR/profile.applied,
DIR/watch2.heartbeat and DIR/watch2.log, all written by the watcher. Used by the block orchestrator (auto_block.py); not part of run.py.

request(value) returns only when profile.applied
  * shows the same request string, written at or after the request time (a stale record with the same string is not accepted);
  * lists ALL 11 expected containers (or, with allow_no_cluster, `containers: 0`: acknowledged, applied when the cluster appears);
  * has, for EVERY container, a `tc qdisc show` coherent with the expected profile: lan -> no netem; regional/wan/degraded -> delay and
    loss of the profile (20 ms/0.1%, 80 ms/1%, 200 ms/5%); partition:site-N -> loss 100% without delay on that site and the base on the other ten;
  * reports the expected base and partition (restore expects the CURRENT base, never lan unless the base is lan).
Errors are explicit: ProfileTimeout, ProfileMismatch, WatcherDown, StaleApplied (all ProfileError); the message says what was expected
and what was found and attaches the tail of the watcher's log (which holds its own rejection reason)."""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

NAMES = ["dibtnsm-evidence-1"] + [f"dibtnsm-site-{i}-1" for i in range(10)]
NETEM = {"lan": None, "regional": (20.0, 0.1), "wan": (80.0, 1.0), "degraded": (200.0, 5.0)}   # base -> (delay ms, loss %), as netem_apply.sh
BASES = tuple(NETEM)
_REQ = re.compile(r"^(lan|regional|wan|degraded|restore|partition:site-[0-9])(\+fast)?$")
HEARTBEAT_MAX_AGE_S = 15.0


class ProfileError(Exception):
    pass


class ProfileTimeout(ProfileError):
    pass


class ProfileMismatch(ProfileError):
    pass


class WatcherDown(ProfileError):
    pass


class StaleApplied(ProfileError):
    pass


@dataclass
class Applied:
    request: str
    trigger: str
    applied_utc: str
    epoch_ms: int
    base: str
    partition: int | None
    poll_s: float
    containers: int
    sections: dict = field(default_factory=dict)       # name -> (pid, [qdisc lines])


def parse_request(value: str) -> tuple[str, int | None, bool]:
    """(kind, site, fast): kind in lan/regional/wan/degraded/restore/partition. Raises ProfileError outside the closed list."""
    m = _REQ.match(value) if isinstance(value, str) and "\n" not in value else None
    if not m:
        raise ProfileError(f"request {value!r} is not in the closed list (lan, regional, wan, degraded, restore, partition:site-0..9, optional +fast)")
    v = m.group(1)
    if v.startswith("partition:"):
        return "partition", int(v[-1]), bool(m.group(2))
    return v, None, bool(m.group(2))


def parse_applied(text: str) -> Applied:
    if not text.strip():
        raise ProfileError("profile.applied is empty")
    hdr, sections, cur = {}, {}, None
    for line in text.splitlines():
        m = re.match(r"^== (\S+) pid (\d+)$", line)
        if m:
            cur = m.group(1)
            sections[cur] = (int(m.group(2)), [])
        elif cur is not None:
            sections[cur][1].append(line)
        else:
            k, _, v = line.partition(": ")
            hdr[k] = v
    try:
        part = hdr["partition"]
        return Applied(hdr["request"], hdr["trigger"], hdr["applied_utc"], int(hdr["epoch_ms"]), hdr["base"],
                       None if part == "none" else int(part), float(hdr["poll_s"]), int(hdr["containers"]), sections)
    except (KeyError, ValueError) as exc:
        first = "\n".join(f"  | {l[:200]}" for l in text.splitlines()[:5])
        raise ProfileError(f"profile.applied is not in the netem_watch2/1 format ({exc!r}); first 5 lines of what was found:\n{first}") from exc


def parse_qdisc(lines: list[str]) -> dict:
    text = " ".join(lines)
    out = {"netem": "netem" in text, "delay_ms": None, "loss_pct": None}
    m = re.search(r"\bdelay\s+([\d.]+)\s*(us|ms|s)\b", text)
    if m:
        out["delay_ms"] = float(m.group(1)) * {"us": 0.001, "ms": 1.0, "s": 1000.0}[m.group(2)]
    m = re.search(r"\bloss\s+([\d.]+)%", text)
    if m:
        out["loss_pct"] = float(m.group(1))
    return out


def expected_qdisc(base: str, partition: int | None, name: str) -> dict:
    if partition is not None and name == f"dibtnsm-site-{partition}-1":
        return {"netem": True, "delay_ms": None, "loss_pct": 100.0}
    p = NETEM[base]
    return {"netem": False, "delay_ms": None, "loss_pct": None} if p is None else {"netem": True, "delay_ms": p[0], "loss_pct": p[1]}


def _same(a: dict, b: dict) -> bool:
    def eq(x, y):
        return (x is None and y is None) or (x is not None and y is not None and abs(x - y) < 1e-6)
    return a["netem"] == b["netem"] and eq(a["delay_ms"], b["delay_ms"]) and eq(a["loss_pct"], b["loss_pct"])


def fmt_q(q: dict) -> str:
    if not q["netem"]:
        return "no netem"
    return "netem " + " ".join(x for x in (None if q["delay_ms"] is None else f"delay {q['delay_ms']:g}ms",
                                           None if q["loss_pct"] is None else f"loss {q['loss_pct']:g}%") if x)


def check_coherent(a: Applied, base: str, partition: int | None, names=NAMES) -> list[str]:
    """Problems of a profile.applied record against the expected state; empty list = coherent for ALL containers."""
    probs = []
    if a.base != base:
        probs.append(f"watcher reports base {a.base!r}, expected {base!r}")
    if a.partition != partition:
        probs.append(f"watcher reports partition {a.partition!r}, expected {partition!r}")
    missing = [n for n in names if n not in a.sections]
    if missing:
        probs.append(f"{len(a.sections)} of {len(names)} containers present, missing {missing}")
    extra = [n for n in a.sections if n not in names]
    if extra:
        probs.append(f"unexpected containers {extra}")
    if a.containers != len(a.sections):
        probs.append(f"header says {a.containers} containers, {len(a.sections)} sections found")
    for n in names:
        if n in a.sections:
            got, want = parse_qdisc(a.sections[n][1]), expected_qdisc(base, partition, n)
            if not _same(got, want):
                probs.append(f"{n}: expected {fmt_q(want)}, found {fmt_q(got)} ({' '.join(a.sections[n][1]).strip()!r})")
    return probs


class ProfileCtl:
    def __init__(self, directory, clock=time.time, sleep=time.sleep, names=NAMES):
        self.dir, self.clock, self.sleep, self.names = Path(directory), clock, sleep, list(names)
        self.expected_base: str | None = None
        self.expected_partition: int | None = None

    # ---- watcher files
    def log_tail(self, n: int = 5) -> str:
        try:
            return "\n".join((self.dir / "watch2.log").read_text(errors="replace").splitlines()[-n:])
        except OSError:
            return "(no watch2.log)"

    def heartbeat_age(self) -> float:
        try:
            txt = (self.dir / "watch2.heartbeat").read_text()
        except OSError as exc:
            raise WatcherDown(f"no heartbeat file in {self.dir}: the watcher is not running ({exc})") from exc
        h = dict(l.split(": ", 1) for l in txt.splitlines() if ": " in l)
        if h.get("state") != "running":
            raise WatcherDown(f"watcher heartbeat says state {h.get('state')!r}")
        try:
            return self.clock() - int(h["epoch_ms"]) / 1000.0
        except (KeyError, ValueError) as exc:
            raise WatcherDown(f"unreadable heartbeat: {txt!r}") from exc

    def check_alive(self, max_age_s: float = HEARTBEAT_MAX_AGE_S) -> float:
        age = self.heartbeat_age()
        if age > max_age_s:
            raise WatcherDown(f"watcher heartbeat is {age:.1f} s old, older than the declared {max_age_s} s")
        return age

    def read_applied(self, max_age_s: float | None = None) -> Applied:
        try:
            a = parse_applied((self.dir / "profile.applied").read_text())
        except OSError as exc:
            raise ProfileError(f"no profile.applied in {self.dir} ({exc})") from exc
        age = self.clock() - a.epoch_ms / 1000.0
        if max_age_s is not None and age > max_age_s:
            raise StaleApplied(f"profile.applied is {age:.0f} s old, older than the declared {max_age_s} s (request {a.request!r}, {a.applied_utc})")
        return a

    # ---- request
    def _expected_after(self, kind: str, site: int | None) -> tuple[str, int | None]:
        if kind in BASES:
            return kind, None
        if self.expected_base is None:
            raise ProfileError(f"'{kind}' needs a known base profile: request lan/regional/wan/degraded first")
        return self.expected_base, (site if kind == "partition" else None)

    def request(self, value: str, timeout_s: float = 60.0, allow_no_cluster: bool = False, poll_s: float = 0.2,
                heartbeat_max_age_s: float = HEARTBEAT_MAX_AGE_S) -> Applied:
        kind, site, _fast = parse_request(value)                         # closed list, before anything is written
        base, part = self._expected_after(kind, site)
        self.check_alive(heartbeat_max_age_s)
        t_req_ms = int(self.clock() * 1000)
        tmp = self.dir / f".req.{os.getpid()}.tmp"
        try:
            tmp.write_text(value + "\n")
            os.replace(tmp, self.dir / "profile.request")                # new inode, never partially visible
        finally:
            tmp.unlink(missing_ok=True)
        t0, last = self.clock(), "no profile.applied for this request yet"
        while True:
            a = None
            try:
                a = self.read_applied()
            except ProfileError as exc:
                last = f"profile.applied unreadable: {exc}"
            if a is not None and a.request == value and a.epoch_ms >= t_req_ms:
                if a.containers == 0 and allow_no_cluster:
                    self.expected_base, self.expected_partition = base, part
                    return a
                probs = check_coherent(a, base, part, self.names)
                if not probs:
                    self.expected_base, self.expected_partition = base, part
                    return a
                last = "; ".join(probs)
                mismatch = True
            else:
                mismatch = False
                if a is not None:
                    last = f"last profile.applied shows request {a.request!r} at {a.applied_utc}, expected {value!r}"
            if self.clock() - t0 >= timeout_s:
                tail = self.log_tail()
                if mismatch:
                    raise ProfileMismatch(f"request {value!r}: profile.applied does not match after {timeout_s:.0f} s: {last}\nwatcher log:\n{tail}")
                raise ProfileTimeout(f"request {value!r}: no matching profile.applied after {timeout_s:.0f} s ({last})\nwatcher log:\n{tail}")
            self.check_alive(heartbeat_max_age_s)
            self.sleep(poll_s)
