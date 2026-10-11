"""Tests of profile_ctl.py (driver side of netem_watch2.sh) with FAKE files only: no docker, no watcher, no network.
Hypotheses (declared before the module was written):
P-1  the request is written atomically (new inode, exact content `<value>\\n`, never partially visible) and only values of the
     closed list are ever written; anything else raises BEFORE touching the file;
P-2  request() returns only when profile.applied shows the SAME request, written at or after the request time, with ALL 11
     containers present and each `tc qdisc show` coherent with the expected profile (netem absent for lan; delay/loss of the
     profile for the others; loss 100% without delay on the partitioned site and the base on the other ten);
P-3  a stale profile.applied (older record with the same request string) is NOT accepted;
P-4  errors are explicit: ProfileTimeout (nothing / wrong request), ProfileMismatch (11 of 11 present but one qdisc wrong, or
     fewer than 11 containers), WatcherDown (heartbeat missing, stopped or older than the declared age); the message says what
     was expected and what was found; the log tail of the watcher is attached;
P-5  read_applied(max_age_s) raises StaleApplied when profile.applied is older than the declared value;
P-6  restore / partition need a known base: asking before any base request raises; restore expects the CURRENT base;
P-7  with allow_no_cluster a `containers: 0` acknowledgement is accepted (the cluster does not exist yet), otherwise it is a mismatch.
Falsification: any assertion failing."""
import os
import threading
import time
from pathlib import Path

import pytest

import profile_ctl as pc

NAMES = pc.NAMES
NETEM = {"regional": "delay 20ms loss 0.1%", "wan": "delay 80ms loss 1%", "degraded": "delay 200ms loss 5%"}


def qdisc_for(base, partition, name):
    if partition is not None and name == f"dibtnsm-site-{partition}-1":
        return "qdisc netem 8001: root refcnt 2 limit 1000 loss 100%"
    if base == "lan":
        return "qdisc noqueue 0: root refcnt 2"
    return f"qdisc netem 8001: root refcnt 2 limit 1000 {NETEM[base]}"


def applied_text(request, base, partition=None, trigger="request", epoch_ms=None, names=NAMES, override=None, containers=None):
    epoch_ms = int(time.time() * 1000) if epoch_ms is None else epoch_ms
    n = len(names) if containers is None else containers
    out = ["format: netem_watch2/1", f"request: {request}", f"trigger: {trigger}", "applied_utc: 2026-10-12T10:00:00.000Z",
           f"epoch_ms: {epoch_ms}", f"base: {base}", f"partition: {'none' if partition is None else partition}", "poll_s: 0.5", f"containers: {n}"]
    for i, nm in enumerate(names):
        out += [f"== {nm} pid {3000 + i}", (override or {}).get(nm, qdisc_for(base, partition, nm))]
    return "\n".join(out) + "\n"


def heartbeat(d, age=0.0, state="running"):
    (d / "watch2.heartbeat").write_text(f"pid: 1\nutc: x\nepoch_ms: {int((time.time() - age) * 1000)}\nstate: {state}\nbase: lan\npartition: none\npoll_s: 0.5\n")


class FakeWatcher(threading.Thread):
    """Answers every new profile.request after `delay` s with the callable `make(request_text) -> applied text or None`."""
    def __init__(self, d, make, delay=0.05):
        super().__init__(daemon=True)
        self.d, self.make, self.delay, self.stop_, self.seen = d, make, delay, False, []

    def run(self):
        last = None
        while not self.stop_:
            f = self.d / "profile.request"
            if f.exists():
                st = os.stat(f)
                key = (st.st_ino, st.st_mtime_ns)
                if key != last:
                    last = key
                    req = f.read_text().rstrip("\n")
                    self.seen.append(req)
                    time.sleep(self.delay)
                    t = self.make(req)
                    if t is not None:
                        (self.d / "profile.applied.tmp").write_text(t)
                        os.replace(self.d / "profile.applied.tmp", self.d / "profile.applied")
            time.sleep(0.01)


@pytest.fixture
def d(tmp_path):
    heartbeat(tmp_path)
    return tmp_path


def start(d, make, **kw):
    w = FakeWatcher(d, make, **kw)
    w.start()
    return w


def test_p1_request_is_atomic_exact_and_closed(d):
    w = start(d, lambda r: applied_text(r, "wan"))
    ctl = pc.ProfileCtl(d)
    ctl.request("wan", timeout_s=5)
    assert (d / "profile.request").read_text() == "wan\n"
    ino0 = os.stat(d / "profile.request").st_ino
    for bad in ["bogus", "WAN", "wan ", "partition:site-10", "partition:site-01", "extreme", "mixed", "wan;id", "", "wan+fast+fast", "wan\n"]:
        with pytest.raises(pc.ProfileError):
            ctl.request(bad, timeout_s=1)
    assert os.stat(d / "profile.request").st_ino == ino0 and (d / "profile.request").read_text() == "wan\n"    # untouched
    assert w.seen == ["wan"]
    assert not [f for f in d.iterdir() if f.name.startswith(".req")]                                         # no temp file left
    w.stop_ = True


def test_p2_all_closed_list_values_with_coherent_qdisc(d):
    state = {"base": None, "part": None}

    def make(r):
        v = r.split("+")[0]
        if v in ("lan", "regional", "wan", "degraded"):
            state["base"], state["part"] = v, None
        elif v.startswith("partition:site-"):
            state["part"] = int(v[-1])
        else:
            state["part"] = None
        return applied_text(r, state["base"], state["part"])
    w = start(d, make)
    ctl = pc.ProfileCtl(d)
    for v in ["lan", "regional", "wan", "degraded", "partition:site-3", "restore", "wan+fast", "partition:site-9", "lan"]:
        a = ctl.request(v, timeout_s=5)
        assert a.request == v and a.containers == 11
    assert w.seen == ["lan", "regional", "wan", "degraded", "partition:site-3", "restore", "wan+fast", "partition:site-9", "lan"]
    assert ctl.expected_base == "lan" and ctl.expected_partition is None
    w.stop_ = True


def test_p3_stale_applied_with_same_request_is_not_accepted(d):
    (d / "profile.applied").write_text(applied_text("wan", "wan", epoch_ms=int((time.time() - 3600) * 1000)))
    w = start(d, lambda r: None)                                      # the watcher never answers
    ctl = pc.ProfileCtl(d)
    with pytest.raises(pc.ProfileTimeout) as e:
        ctl.request("wan", timeout_s=1)
    assert "wan" in str(e.value)
    w.stop_ = True


def test_p4_wrong_qdisc_is_a_mismatch_with_names(d):
    bad = {"dibtnsm-site-4-1": "qdisc noqueue 0: root refcnt 2", "dibtnsm-site-7-1": "qdisc netem 8001: root refcnt 2 limit 1000 delay 80ms loss 1%"}
    w = start(d, lambda r: applied_text(r, "degraded", override=bad))
    with pytest.raises(pc.ProfileMismatch) as e:
        pc.ProfileCtl(d).request("degraded", timeout_s=1)
    msg = str(e.value)
    assert "dibtnsm-site-4-1" in msg and "dibtnsm-site-7-1" in msg and "delay 200" in msg
    w.stop_ = True


def test_p4_fewer_than_11_containers(d):
    w = start(d, lambda r: applied_text(r, "wan", names=NAMES[:10]))
    with pytest.raises(pc.ProfileMismatch) as e:
        pc.ProfileCtl(d).request("wan", timeout_s=1)
    assert "10 of 11" in str(e.value) or "missing" in str(e.value)
    w.stop_ = True


def test_p4_wrong_base_reported_by_the_watcher(d):
    w = start(d, lambda r: applied_text(r, "wan"))                    # asked degraded, watcher says wan everywhere
    with pytest.raises(pc.ProfileMismatch):
        pc.ProfileCtl(d).request("degraded", timeout_s=1)
    w.stop_ = True


def test_p4_nothing_at_all_times_out_with_log_tail(d):
    (d / "watch2.log").write_text("2026-10-12T10:00:00.000Z netem_watch: request rejected: not in the closed list: x\n")
    with pytest.raises(pc.ProfileTimeout) as e:
        pc.ProfileCtl(d).request("wan", timeout_s=0.5)
    assert "not in the closed list" in str(e.value)                    # the watcher's own reason is attached


def test_p4_watcher_down(tmp_path):
    ctl = pc.ProfileCtl(tmp_path)
    with pytest.raises(pc.WatcherDown):
        ctl.check_alive()                                              # no heartbeat file
    heartbeat(tmp_path, age=100)
    with pytest.raises(pc.WatcherDown) as e:
        ctl.check_alive(max_age_s=15)
    assert "100" in str(e.value) or "older" in str(e.value)
    heartbeat(tmp_path, state="stopped")
    with pytest.raises(pc.WatcherDown):
        ctl.check_alive()
    heartbeat(tmp_path)
    assert ctl.check_alive() < 5
    heartbeat(tmp_path, age=100)                                       # request() fails fast, without waiting for the timeout
    t0 = time.time()
    with pytest.raises(pc.WatcherDown):
        ctl.request("wan", timeout_s=30)
    assert time.time() - t0 < 5 and not (tmp_path / "profile.request").exists()


def test_p5_read_applied_staleness(d):
    (d / "profile.applied").write_text(applied_text("wan", "wan", epoch_ms=int((time.time() - 500) * 1000)))
    ctl = pc.ProfileCtl(d)
    assert ctl.read_applied().request == "wan"
    with pytest.raises(pc.StaleApplied) as e:
        ctl.read_applied(max_age_s=120)
    assert "500" in str(e.value) or "older" in str(e.value)
    (d / "profile.applied").write_text(applied_text("wan", "wan"))
    assert ctl.read_applied(max_age_s=120).base == "wan"
    (d / "profile.applied").unlink()
    with pytest.raises(pc.ProfileError):
        ctl.read_applied()


def test_p6_restore_and_partition_need_a_base(d):
    w = start(d, lambda r: applied_text(r, "degraded", partition=2 if r.startswith("partition") else None))
    ctl = pc.ProfileCtl(d)
    with pytest.raises(pc.ProfileError):
        ctl.request("restore", timeout_s=1)
    with pytest.raises(pc.ProfileError):
        ctl.request("partition:site-2", timeout_s=1)
    assert w.seen == []
    ctl.request("degraded", timeout_s=5)
    ctl.request("partition:site-2", timeout_s=5)
    a = ctl.request("restore", timeout_s=5)                            # fake answers degraded without partition
    assert a.base == "degraded" and a.partition is None
    w.stop_ = True


def test_p6_restore_answered_as_lan_is_a_mismatch(d):
    def make(r):
        return applied_text(r, "lan" if r == "restore" else "degraded")
    w = start(d, make)
    ctl = pc.ProfileCtl(d)
    ctl.request("degraded", timeout_s=5)
    with pytest.raises(pc.ProfileMismatch):
        ctl.request("restore", timeout_s=1)
    w.stop_ = True


def test_p7_no_cluster_ack(d):
    w = start(d, lambda r: applied_text(r, "degraded", names=[], containers=0))
    with pytest.raises(pc.ProfileMismatch):
        pc.ProfileCtl(d).request("degraded", timeout_s=1)
    a = pc.ProfileCtl(d).request("degraded", timeout_s=5, allow_no_cluster=True)
    assert a.containers == 0
    w.stop_ = True


def test_parse_qdisc_variants():
    assert pc.parse_qdisc(["qdisc noqueue 0: root refcnt 2"]) == {"netem": False, "delay_ms": None, "loss_pct": None}
    q = pc.parse_qdisc(["qdisc netem 8001: root refcnt 2 limit 1000 delay 200ms  loss 5%"])
    assert q == {"netem": True, "delay_ms": 200.0, "loss_pct": 5.0}
    assert pc.parse_qdisc(["qdisc netem 8001: root refcnt 2 limit 1000 delay 20.0ms loss 0.1%"])["loss_pct"] == 0.1
    assert pc.parse_qdisc(["qdisc netem 8001: root refcnt 2 limit 1000 loss 100%"]) == {"netem": True, "delay_ms": None, "loss_pct": 100.0}
    assert pc.parse_qdisc(["qdisc netem 1: root delay 1s loss 1%"])["delay_ms"] == 1000.0


def test_parse_applied_roundtrip():
    a = pc.parse_applied(applied_text("partition:site-3", "wan", partition=3, trigger="recreate"))
    assert a.request == "partition:site-3" and a.trigger == "recreate" and a.base == "wan" and a.partition == 3 and a.containers == 11
    assert sorted(a.sections) == sorted(NAMES) and a.sections["dibtnsm-site-3-1"][0] == 3004
    with pytest.raises(pc.ProfileError):
        pc.parse_applied("garbage\n")
