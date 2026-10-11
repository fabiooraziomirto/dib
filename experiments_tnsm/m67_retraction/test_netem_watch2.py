"""Safety tests of netem_watch2.sh (watcher v2: request file, closed list, profile.applied), with a FAKE docker and a FAKE,
STATEFUL nsenter (it remembers the qdisc of every pid and prints it back on `tc qdisc show`) put first in PATH: nothing real is
touched, every call is logged and checked. Hypotheses (declared before the code was written):
W-1  every value of the closed list (lan, regional, wan, degraded, partition:site-N, restore) is accepted and applied with the
     SAME nsenter/tc commands as netem_apply.sh (the v1 script, reused unchanged), on the validated pids only;
W-2  any other value is rejected, logged, and applies NOTHING (no nsenter call): out-of-list text, trailing space or newline
     garbage, shell metacharacters, `partition:site-10`, `partition:site-01`, repeated `+fast`;
W-3  a symlink, a directory, a hard-linked file, a file owned by another uid and a file larger than 128 bytes are rejected;
W-4  `restore` re-applies the CURRENT BASE profile (never `lan` unless the base is `lan`); `partition:site-N` puts loss 100% on
     that site only and leaves the others at the base; a base request clears the partition;
W-5  after the cluster is recreated (new ids and pids) the current state (base and partition) is re-applied;
W-6  profile.applied carries the request, a UTC timestamp with milliseconds, and ONE `tc qdisc show` section per container;
W-7  SIGTERM, the STOP file and the deadline (--max-seconds, enforced by the script itself through `timeout`) all restore `lan`
     on the validated containers and exit 0; a failed cleanup prints the ATTENZIONE warning and exits != 0; with no cluster
     there is nothing to clean and the exit is 0;
W-8  `+fast` switches the poll interval to --fast-poll and its absence back to --poll (reported in profile.applied);
W-9  every request, accepted or rejected, is written to watch2.log with a UTC time; rejected content is logged escaped;
W-10 a request present when the watcher starts is ignored (stale); a request while no container exists is acknowledged
     (containers: 0) and applied when the cluster appears; a failed apply is retried without writing profile.applied;
W-11 the request directory must be a real directory owned by --owner and not writable by group/other, else the watcher refuses;
W-12 a heartbeat file is refreshed while it runs and says `stopped` at exit;
W-13 across every scenario: docker only as `ps --filter label=...dibtnsm` and `inspect -f ... <expected name>`, nsenter only
     as `-t <pid> -n tc qdisc (show|replace|del) dev eth0 ...`.
Falsification: any assertion failing. Requires uid 0 (netem_apply.sh refuses non-root)."""
import os
import re
import signal
import subprocess
import time
from pathlib import Path

import pytest

from test_netem_scripts import ALLOWED_DOCKER, FAKE_DOCKER, NAMES, env_for, lines

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "netem_watch2.sh"
pytestmark = pytest.mark.skipif(os.geteuid() != 0, reason="netem_apply.sh refuses to run as non-root")

FAKE_NSENTER = r'''#!/usr/bin/env bash
# stateful fake: qdisc of pid P is the file $FAKE_DIR/q_P
D="$FAKE_DIR"
echo "nsenter $*" >> "$D/nsenter.log"
pid=$2
if [[ "$*" == *"tc qdisc show"* ]]; then
  [[ -e "$D/fail_show" ]] && { echo "show failed" >&2; exit 1; }
  if [[ -e "$D/q_$pid" ]]; then cat "$D/q_$pid"; else echo "qdisc noqueue 0: root refcnt 2"; fi
elif [[ "$*" == *"tc qdisc replace"* ]]; then
  if [[ -e "$D/switch_on_replace" ]]; then cat "$D/switch_on_replace" > "$D/mode"; rm -f "$D/switch_on_replace"; fi   # a container appears DURING the application
  if [[ -e "$D/fail_once" ]]; then rm -f "$D/fail_once"; echo "boom" >&2; exit 1; fi
  args="${*#*netem }"
  echo "qdisc netem 8001: root refcnt 2 limit 1000 $args" > "$D/q_$pid"
elif [[ "$*" == *"tc qdisc del"* ]]; then
  if [[ -e "$D/fail_del" ]]; then echo "Error: cannot delete" >&2; exit 2; fi
  rm -f "$D/q_$pid"
fi
exit 0
'''


def make_fake(tmp_path, with_cluster=True):
    d = tmp_path / "fake"
    d.mkdir(parents=True, exist_ok=True)
    (d / "docker").write_text(FAKE_DOCKER)
    (d / "nsenter").write_text(FAKE_NSENTER)
    for f in ("docker", "nsenter"):
        (d / f).chmod(0o755)
    a = [f"aaaa{i:02d} {n} {3000 + i} dibtnsm" for i, n in enumerate(NAMES)]
    b = [f"bbbb{i:02d} {n} {7000 + i} dibtnsm" for i, n in enumerate(NAMES)]
    (d / "containers_a").write_text("\n".join(a) + "\n")
    (d / "containers_b").write_text("\n".join(b) + "\n")
    (d / "containers_none").write_text("")
    (d / "containers_ten").write_text("\n".join(a[:9] + a[10:]) + "\n")                   # site-9 not created yet
    (d / "mode").write_text("a" if with_cluster else "none")
    for f in ("docker.log", "nsenter.log", "violations.log"):
        (d / f).write_text("")
    rd = tmp_path / "req"
    rd.mkdir(mode=0o755)
    os.chmod(rd, 0o755)
    return d, rd


class Watch:
    def __init__(self, d, rd, *extra, owner="root", poll="0.1", fast="0.05", max_s=None):
        self.d, self.rd = d, rd
        args = ["bash", str(SCRIPT), "--dir", str(rd), "--owner", owner, "--poll", poll, "--fast-poll", fast, *extra]
        if max_s is not None:
            args += ["--max-seconds", str(max_s)]
        self.p = subprocess.Popen(args, env=env_for(d), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.out = self.err = None

    def request(self, value, raw=None, uid=None):
        tmp = self.rd / ".r.tmp"
        tmp.write_bytes(raw if raw is not None else (value + "\n").encode())
        if uid is not None:
            os.chown(tmp, uid, uid)
        os.replace(tmp, self.rd / "profile.request")

    def applied(self):
        f = self.rd / "profile.applied"
        return f.read_text() if f.exists() else ""

    def ask(self, value, secs=20):
        """Request `value` and wait for a profile.applied that is NEWER and shows this request."""
        before = self.applied()
        self.request(value)
        ok = wait_for(lambda: self.applied() != before and re.search(rf"^request: {re.escape(value)}$", self.applied(), re.M), secs)
        assert ok, f"no profile.applied for {value!r}; log:\n{self.log()}\nstderr:{self.p.poll()}"
        return self.applied()

    def log(self):
        f = self.rd / "watch2.log"
        return f.read_text() if f.exists() else ""

    def stop(self, sig=signal.SIGTERM, secs=40):
        if self.p.poll() is None:
            self.p.send_signal(sig)
        try:
            self.out, self.err = self.p.communicate(timeout=secs)
        finally:
            if self.p.poll() is None:
                self.p.kill()
        return self.p.returncode


def wait_for(cond, secs=20):
    t0 = time.time()
    while time.time() - t0 < secs:
        r = cond()
        if r:
            return r
        time.sleep(0.05)
    return cond()


def sections(applied):
    """{container name: [qdisc lines]} from profile.applied."""
    out, cur = {}, None
    for l in applied.splitlines():
        m = re.match(r"^== (\S+) pid (\d+)$", l)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(l)
    return out


def nsenter_cmds(d):
    return lines(d, "nsenter.log")


def check_global(d):
    """W-13."""
    assert lines(d, "violations.log") == []
    for l in lines(d, "docker.log"):
        assert any(a.match(l) for a in ALLOWED_DOCKER), f"docker call outside the allowed shapes: {l}"
    for l in nsenter_cmds(d):
        assert re.match(r"^nsenter -t \d+ -n tc qdisc (show|replace|del) dev eth0( root( netem .*)?)?$", l), l


@pytest.fixture
def env(tmp_path):
    d, rd = make_fake(tmp_path)
    ws = []

    def mk(*a, **k):
        w = Watch(d, rd, *a, **k)
        ws.append(w)
        assert wait_for(lambda: (rd / "watch2.heartbeat").exists(), 15), "watcher did not start"
        return w
    yield d, rd, mk
    for w in ws:
        if w.p.poll() is None:
            w.stop()


def qlines(applied):
    return {n: " ".join(v) for n, v in sections(applied).items()}


# ------------------------------------------------------------------------------------------------------------------ W-1, W-6
@pytest.mark.parametrize("prof,args", [("regional", "delay 20ms loss 0.1%"), ("wan", "delay 80ms loss 1%"), ("degraded", "delay 200ms loss 5%")])
def test_w1_netem_profiles_apply_exactly_like_netem_apply(env, prof, args):
    d, rd, mk = env
    w = mk()
    a = w.ask(prof)
    pids = [l.split()[2] for l in lines(d, "containers_a")]
    got = [l for l in nsenter_cmds(d) if "replace" in l]
    assert sorted(got) == sorted(f"nsenter -t {p} -n tc qdisc replace dev eth0 root netem {args}" for p in pids)
    s = qlines(a)
    assert sorted(s) == sorted(NAMES) and all(args in v for v in s.values())      # W-6: one section per container
    assert "containers: 11" in a and f"base: {prof}" in a and "partition: none" in a
    assert re.search(r"^applied_utc: \d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$", a, re.M)
    w.stop()
    check_global(d)


def test_w1_lan_removes_the_qdisc(env):
    d, rd, mk = env
    w = mk()
    w.ask("wan")
    a = w.ask("lan")
    assert all("netem" not in v for v in qlines(a).values()) and len(sections(a)) == 11
    assert not any(f.name.startswith("q_") for f in d.iterdir())
    w.stop()
    check_global(d)


# ------------------------------------------------------------------------------------------------------------------ W-4
def test_w4_partition_and_restore_keep_the_base(env):
    d, rd, mk = env
    w = mk()
    w.ask("degraded")
    a = w.ask("partition:site-3")
    s = qlines(a)
    assert "loss 100%" in s["dibtnsm-site-3-1"] and "delay" not in s["dibtnsm-site-3-1"]
    assert all("delay 200ms loss 5%" in v for n, v in s.items() if n != "dibtnsm-site-3-1")
    assert "base: degraded" in a and "partition: 3" in a
    n_before = len(nsenter_cmds(d))
    a = w.ask("restore")
    s = qlines(a)
    assert all("delay 200ms loss 5%" in v for v in s.values()) and "partition: none" in a     # base, NOT lan
    after = nsenter_cmds(d)[n_before:]
    assert not any("qdisc del" in l for l in after)
    a = w.ask("partition:site-9")
    a = w.ask("wan")                                                                        # a base request clears the partition
    assert "partition: none" in a and all("delay 80ms loss 1%" in v for v in qlines(a).values())
    w.stop()
    check_global(d)


def test_w4_restore_at_base_lan_is_lan(env):
    d, rd, mk = env
    w = mk()
    w.ask("lan")
    w.ask("partition:site-0")
    a = w.ask("restore")
    assert all("netem" not in v for v in qlines(a).values())
    w.stop()


def test_w4_partition_site_9_accepted_and_only_that_site(env):
    d, rd, mk = env
    w = mk()
    a = w.ask("partition:site-9")
    s = qlines(a)
    assert [n for n, v in s.items() if "netem" in v] == ["dibtnsm-site-9-1"]
    w.stop()
    check_global(d)


# ------------------------------------------------------------------------------------------------------------------ W-2, W-3, W-9
BAD = [b"bogus\n", b"WAN\n", b"wan \n", b" wan\n", b"wan\n\n", b"wan\nwan\n", b"wan;id\n", b"$(touch /tmp/pwn)\n", b"`id`\n", b"wan+fast+fast\n",
       b"wan+FAST\n", b"partition:site-10\n", b"partition:site-01\n", b"partition:site-a\n", b"partition:site-\n", b"partition:site--1\n",
       b"partition\n", b"extreme\n", b"mixed\n", b"restore now\n", b"\n", b"", b"wan\x00\n", b"\x1b[31mwan\n", b"wan" + b" " * 200 + b"\n",
       b"../wan\n"]


@pytest.mark.parametrize("raw", BAD)
def test_w2_out_of_list_values_are_rejected_and_apply_nothing(env, raw):
    d, rd, mk = env
    w = mk()
    w.request("", raw=raw)
    assert wait_for(lambda: "rejected" in w.log(), 10), w.log()
    time.sleep(0.4)
    assert nsenter_cmds(d) == [] and w.applied() == ""
    log = w.log()
    assert "\x1b" not in log and "\x00" not in log                  # W-9: escaped, never raw
    assert len([l for l in log.splitlines() if "rejected" in l]) == 1
    w.stop()
    check_global(d)


def test_w3_symlink_is_rejected(env, tmp_path):
    d, rd, mk = env
    w = mk()
    target = tmp_path / "elsewhere"
    target.write_text("wan\n")
    (rd / "profile.request").symlink_to(target)
    assert wait_for(lambda: "request rejected: symlink" in w.log(), 10), w.log()
    time.sleep(0.4)
    assert nsenter_cmds(d) == [] and w.applied() == ""
    w.stop()


def test_w3_directory_hardlink_other_owner_and_size(env, tmp_path):
    d, rd, mk = env
    w = mk()
    (rd / "profile.request").mkdir()
    assert wait_for(lambda: "request rejected: not a regular file" in w.log(), 10)
    (rd / "profile.request").rmdir()
    other = tmp_path / "other"
    other.write_text("wan\n")
    os.link(other, rd / "profile.request")
    assert wait_for(lambda: "request rejected: file has 2 hard links" in w.log(), 10)
    (rd / "profile.request").unlink()
    w.request("wan", uid=12345)
    assert wait_for(lambda: "request rejected: owner uid 12345" in w.log(), 10)
    w.request("", raw=b"wan" + b" " * 126 + b"\n")                  # 130 bytes
    assert wait_for(lambda: "request rejected: size 130 bytes > 128" in w.log(), 10)
    time.sleep(0.4)
    assert nsenter_cmds(d) == [] and w.applied() == ""
    w.stop()
    check_global(d)


def test_w9_every_request_is_logged_with_time(env):
    d, rd, mk = env
    w = mk()
    w.ask("wan")
    w.request("nope")
    assert wait_for(lambda: "rejected" in w.log(), 10)
    w.ask("lan")
    log = w.log().splitlines()
    assert any(re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z netem_watch: request accepted: wan", l) for l in log)
    assert any(re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z netem_watch: request rejected", l) for l in log)
    assert any("request accepted: lan" in l for l in log)
    w.stop()


# ------------------------------------------------------------------------------------------------------------------ W-5
def test_w5_recreation_reapplies_base_and_partition(env):
    d, rd, mk = env
    w = mk()
    w.ask("degraded")
    w.ask("partition:site-4")
    before = w.applied()
    (d / "mode").write_text("b")                                    # recreated cluster: new ids and pids
    assert wait_for(lambda: w.applied() != before and "pid 7004" in w.applied() and "trigger: recreate" in w.applied(), 20), w.applied()
    s = qlines(w.applied())
    assert "loss 100%" in s["dibtnsm-site-4-1"] and all("delay 200ms loss 5%" in v for n, v in s.items() if n != "dibtnsm-site-4-1")
    assert "request: partition:site-4" in w.applied()
    log = w.log()
    assert re.search(r"netem_watch: containers changed -> applying \S+$", log, re.M) and re.search(r"netem_watch: applied \S+ \(\d+\.\d+ s\)$", log, re.M)
    w.stop()
    check_global(d)


# ------------------------------------------------------------------------------------------------------------------ W-7
def test_w7_sigterm_and_stop_file_restore_lan_exit_zero(env):
    d, rd, mk = env
    w = mk()
    w.ask("degraded")
    assert w.stop(signal.SIGTERM) == 0, w.err
    assert not any(f.name.startswith("q_") for f in d.iterdir())    # lan on the current containers
    assert "stopped" in (rd / "watch2.heartbeat").read_text()
    d2, rd2 = make_fake(Path(str(d.parent) + "_x"))
    w2 = Watch(d2, rd2)
    assert wait_for(lambda: (rd2 / "watch2.heartbeat").exists(), 15)
    w2.ask("wan")
    (rd2 / "STOP").write_text("")
    assert w2.p.wait(timeout=30) == 0
    assert not any(f.name.startswith("q_") for f in d2.iterdir())
    check_global(d2)


def test_w7_deadline_is_enforced_by_the_script(tmp_path):
    d, rd = make_fake(tmp_path)
    w = Watch(d, rd, max_s=3)                                       # no external timeout: the script re-executes itself under one
    assert wait_for(lambda: (rd / "watch2.heartbeat").exists(), 15)
    w.ask("wan")
    t0 = time.time()
    assert w.p.wait(timeout=40) == 0 and time.time() - t0 < 30
    assert not any(f.name.startswith("q_") for f in d.iterdir())


def test_w7_failed_cleanup_is_loud_and_nonzero(tmp_path):
    msg = "ATTENZIONE: pulizia netem NON riuscita, verifica con netem_show.sh"
    d, rd = make_fake(tmp_path)
    w = Watch(d, rd)
    assert wait_for(lambda: (rd / "watch2.heartbeat").exists(), 15)
    w.ask("wan")
    (d / "fail_del").write_text("")                                 # `del` fails and netem is still there
    rc = w.stop()
    assert rc != 0 and msg in w.err
    d2, rd2 = make_fake(tmp_path / "b")
    w = Watch(d2, rd2)
    assert wait_for(lambda: (rd2 / "watch2.heartbeat").exists(), 15)
    w.ask("wan")
    bad = [f"cccc{i:02d} {n} {8000 + i} dibtnsm" for i, n in enumerate(NAMES)]
    bad[4] = f"cccc04 {NAMES[4]} 8004 someother"                    # validation fails at cleanup time: nothing is touched
    (d2 / "containers_b").write_text("\n".join(bad) + "\n")
    (d2 / "mode").write_text("b")
    rc = w.stop()
    assert rc != 0 and msg in w.err


def test_w7_no_cluster_at_exit_is_not_a_failure(tmp_path):
    d, rd = make_fake(tmp_path, with_cluster=False)
    w = Watch(d, rd)
    assert wait_for(lambda: (rd / "watch2.heartbeat").exists(), 15)
    assert w.stop() == 0 and "ATTENZIONE" not in w.err
    assert nsenter_cmds(d) == []


# ------------------------------------------------------------------------------------------------------------------ W-8
def test_w8_fast_suffix_changes_poll(env):
    d, rd, mk = env
    w = mk(poll="0.3", fast="0.05")
    a = w.ask("wan")
    assert "poll_s: 0.3" in a
    a = w.ask("wan+fast")
    assert "poll_s: 0.05" in a and "base: wan" in a
    a = w.ask("degraded")
    assert "poll_s: 0.3" in a
    w.stop()
    check_global(d)


# ------------------------------------------------------------------------------------------------------------------ W-10
def test_w10_stale_request_at_start_is_ignored(tmp_path):
    d, rd = make_fake(tmp_path)
    (rd / "profile.request").write_text("degraded\n")
    w = Watch(d, rd)
    assert wait_for(lambda: (rd / "watch2.heartbeat").exists(), 15)
    time.sleep(0.8)
    assert not any("replace" in l for l in nsenter_cmds(d)) and "stale" in w.log()
    w.stop()


def test_w10_request_without_cluster_is_acknowledged_then_applied(tmp_path):
    d, rd = make_fake(tmp_path, with_cluster=False)
    w = Watch(d, rd)
    assert wait_for(lambda: (rd / "watch2.heartbeat").exists(), 15)
    a = w.ask("degraded")
    assert "containers: 0" in a and nsenter_cmds(d) == []
    (d / "mode").write_text("a")
    assert wait_for(lambda: "containers: 11" in w.applied() and "trigger: recreate" in w.applied(), 20)
    assert all("delay 200ms loss 5%" in v for v in qlines(w.applied()).values())
    w.stop()
    check_global(d)


def test_w10_failed_apply_is_retried_without_applied_file(env):
    d, rd, mk = env
    w = mk()
    (d / "fail_once").write_text("")
    w.request("wan")
    assert wait_for(lambda: "request: wan" in w.applied(), 20)
    assert "apply FAILED" in w.log()
    assert len([l for l in nsenter_cmds(d) if "replace" in l]) >= 12       # 1 failed + 11
    assert all("delay 80ms loss 1%" in v for v in qlines(w.applied()).values())
    w.stop()


# ------------------------------------------------------------------------------------------------------------------ W-11, W-12
def test_w11_directory_checks(tmp_path):
    d, rd = make_fake(tmp_path)
    run = lambda *a: subprocess.run(["bash", str(SCRIPT), *a], env=env_for(d), capture_output=True, text=True, timeout=30)
    os.chmod(rd, 0o775)
    r = run("--dir", str(rd), "--owner", "root")
    assert r.returncode != 0 and "writable" in r.stderr
    os.chmod(rd, 0o755)
    r = run("--dir", str(rd), "--owner", "nobody")                     # the directory is not owned by that user
    assert r.returncode != 0 and "owner" in r.stderr
    r = run("--dir", str(rd), "--owner", "no_such_user_xyz")
    assert r.returncode != 0
    link = tmp_path / "lnk"
    link.symlink_to(rd)
    r = run("--dir", str(link), "--owner", "root")
    assert r.returncode != 0 and "symlink" in r.stderr
    r = run("--dir", str(rd))
    assert r.returncode != 0
    (rd / "STOP").write_text("")
    r = run("--dir", str(rd), "--owner", "root")
    assert r.returncode != 0 and "STOP" in r.stderr
    assert nsenter_cmds(d) == []


def test_w12_heartbeat_is_refreshed(env):
    d, rd, mk = env
    w = mk()
    h1 = (rd / "watch2.heartbeat").read_text()
    assert wait_for(lambda: (rd / "watch2.heartbeat").read_text() != h1, 10)
    h = (rd / "watch2.heartbeat").read_text()
    assert "state: running" in h and re.search(r"^epoch_ms: \d{13}$", h, re.M)
    w.stop()
    assert "state: stopped" in (rd / "watch2.heartbeat").read_text()


def test_dry_run_changes_nothing(tmp_path):
    d, rd = make_fake(tmp_path)
    r = subprocess.run(["bash", str(SCRIPT), "--dry-run", "--dir", str(rd), "--owner", "root"], env=env_for(d), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    for n in NAMES:
        assert n in r.stdout
    assert nsenter_cmds(d) == [] and not (rd / "watch2.heartbeat").exists()
    check_global(d)


# ------------------------------------------------------------------------------------------------------------------ W-14, W-15 (review of 2026-10-11)
def test_w14_no_orphan_children_after_exit(env):
    """`timeout --foreground` signals only the watcher: its background `sleep` must not outlive it (declared: after SIGTERM no `sleep <poll>`
    child of this watcher is left; the unusual poll value 7.77 identifies it)."""
    d, rd, mk = env
    w = mk(poll="7.77", fast="0.05")
    time.sleep(0.5)
    assert w.stop() == 0
    left = subprocess.run(["pgrep", "-f", "sleep 7.77"], capture_output=True, text=True).stdout.split()
    assert left == [], f"orphan sleep left: {left}"


def test_w15_failed_write_does_not_reapply_in_a_loop(env):
    """If the netem application succeeded but profile.applied cannot be written, only the WRITE is retried: no further `tc qdisc replace`."""
    d, rd, mk = env
    w = mk()
    (rd / "profile.applied").mkdir()                              # `mv -T` onto a directory fails
    w.request("wan")
    assert wait_for(lambda: "profile.applied NOT written" in w.log(), 10), w.log()
    time.sleep(1.0)                                              # ~10 polls
    assert len([l for l in nsenter_cmds(d) if "replace" in l]) == 11, "the state was re-applied while only the write failed"
    (rd / "profile.applied").rmdir()
    assert wait_for(lambda: "request: wan" in w.applied(), 10)
    assert len([l for l in nsenter_cmds(d) if "replace" in l]) == 11
    assert all("delay 80ms loss 1%" in v for v in qlines(w.applied()).values())
    w.stop()
    check_global(d)


def test_w16_container_appearing_during_the_application_is_never_reported_as_applied(tmp_path):
    """Smoke of 2026-10-11: site-8 appeared while the watcher was applying; profile.applied then listed 11 containers with site-8 WITHOUT netem.
    Declared: the watcher writes profile.applied only if the container set (names and pids) after the application equals the set it applied to;
    otherwise it re-applies. Every record ever visible has netem on every container it lists, and the final record has all 11."""
    d, rd = make_fake(tmp_path)
    (d / "mode").write_text("ten")
    w = Watch(d, rd)
    assert wait_for(lambda: (rd / "watch2.heartbeat").exists(), 15)
    (d / "switch_on_replace").write_text("a")                         # the first `replace` makes site-9 appear
    w.request("degraded")
    seen = []
    t0 = time.time()
    while time.time() - t0 < 20:
        a = w.applied()
        if a and (not seen or seen[-1] != a):
            seen.append(a)
        if "containers: 11" in a:
            break
        time.sleep(0.01)
    time.sleep(0.3)
    final = w.applied()
    assert "containers: 11" in final and all("delay 200ms loss 5%" in v for v in qlines(final).values()) and len(qlines(final)) == 11
    for a in seen:                                                    # no visible record lists a container without netem
        assert all("netem" in v for v in qlines(a).values()), a
    w.stop()
    check_global(d)
