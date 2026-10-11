"""Safety tests of netem_apply.sh / netem_watch.sh / netem_show.sh (user decision A, 2026-10-10), with a FAKE docker and a
FAKE nsenter put first in PATH: nothing real is touched, every call is logged and checked. Hypotheses (declared first):
N-1  --dry-run lists exactly the 11 expected container names and the exact commands, and calls neither nsenter nor
     any docker verb other than `ps --filter label=...dibtnsm` and `inspect -f ... <expected name>`;
N-2  applying a profile calls nsenter ONLY as `-t <pid> -n tc qdisc replace dev eth0 root netem <args>`, once for each of
     the validated pids and for no other pid; `lan` calls only `tc qdisc del dev eth0 root`, same pids;
N-3  any anomaly (unexpected container name, label different from dibtnsm, bad pid, unknown profile) aborts BEFORE any
     nsenter call (nothing applied partially);
N-4  the watcher re-applies after the set of containers changes (a recreated cluster has new IDs/pids) and on SIGINT
     removes the qdisc of exactly the validated containers of the current set and nothing else, exiting 0;
N-6  (user correction A1) the watcher retries a FAILED apply at the next poll even though the container list did not
     change (`last` is updated only on success);
N-7  (A2) if the cleanup on Ctrl-C fails (validation abort, or a `tc qdisc del` that fails while netem is still there)
     it prints the visible warning "ATTENZIONE: pulizia netem NON riuscita, verifica con netem_show.sh" on stderr and
     exits != 0; a `del` that fails because no qdisc exists (nothing to remove) is NOT a failure;
N-8  (A3) the signature includes the pid: same container IDs and names but new pids (compose kill/start gives a new
     namespace) => re-application; pids are read only for names matching the expected pattern, in ONE docker inspect;
     an unexpected name present in `docker ps` is never inspected and nothing is applied while it is there;
N-9  (A4) `--poll S` sets the poll interval (validated); the watcher prints millisecond UTC timestamps for "changed" and
     "applied" (parsed by run.py parse_watch_log);
N-5  across every scenario: no unfiltered `docker ps`, no docker verb other than ps/inspect (no network/exec/run/rm/kill),
     no decoy container (k3s, wasmbed, an unlabelled dibtnsm-lookalike) ever inspected or entered.
Falsification: any assertion failing. Requires uid 0 (the scripts refuse non-root outside --dry-run)."""
import os
import re
import signal
import subprocess
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
NAMES = ["dibtnsm-evidence-1"] + [f"dibtnsm-site-{i}-1" for i in range(10)]
FAKE_DOCKER = r'''#!/usr/bin/env bash
D="$FAKE_DIR"
echo "docker $*" >> "$D/docker.log"
mode=$(cat "$D/mode")
case "$1" in
  ps)
    [[ "$*" == *"--filter label=com.docker.compose.project=dibtnsm"* ]] || { echo "UNFILTERED: docker $*" >> "$D/violations.log"; exit 99; }
    f="$D/containers_$mode"
    if [[ "$*" == *"{{.ID}} {{.Names}}"* ]]; then awk '{print $1" "$2}' "$f"; else awk '{print $2}' "$f"; fi ;;
  inspect)
    fmt="$3"; shift 3
    for name in "$@"; do
      line=$(awk -v n="$name" '$2==n' "$D/containers_$mode")
      [[ -n "$line" ]] || { echo "NOT-A-FILTERED-CONTAINER: docker inspect $name" >> "$D/violations.log"; exit 98; }
      if [[ "$fmt" == *"Labels"* ]]; then echo "$line" | awk '{print $4}'; else echo "$line" | awk '{print $3}'; fi
    done ;;
  *) echo "FORBIDDEN: docker $*" >> "$D/violations.log"; exit 97 ;;
esac
'''
FAKE_NSENTER = r'''#!/usr/bin/env bash
echo "nsenter $*" >> "$FAKE_DIR/nsenter.log"
if [[ "$*" == *"tc qdisc show"* ]]; then
  if [[ -e "$FAKE_DIR/show_clean" ]]; then echo "qdisc noqueue 0: root refcnt 2"; else echo "qdisc netem 8001: root refcnt 2 limit 1000 delay 80ms"; fi
fi
if [[ "$*" == *"tc qdisc replace"* && -e "$FAKE_DIR/fail_once" ]]; then rm -f "$FAKE_DIR/fail_once"; echo "boom" >&2; exit 1; fi
if [[ "$*" == *"tc qdisc del"* && -e "$FAKE_DIR/fail_del" ]]; then echo "Error: Cannot delete qdisc with handle of zero." >&2; exit 2; fi
exit 0
'''
pytestmark = pytest.mark.skipif(os.geteuid() != 0, reason="the scripts refuse to run as non-root outside --dry-run")


def make_fake(tmp_path, mode_a=None, mode_b=None):
    d = tmp_path / "fake"
    d.mkdir(parents=True, exist_ok=True)
    (d / "docker").write_text(FAKE_DOCKER)
    (d / "nsenter").write_text(FAKE_NSENTER)
    for f in ("docker", "nsenter"):
        (d / f).chmod(0o755)
    def table(prefix, base_pid):
        return [f"{prefix}{i:02d} {n} {base_pid + i} dibtnsm" for i, n in enumerate(NAMES)]
    (d / "containers_a").write_text("\n".join(mode_a if mode_a is not None else table("aaaa", 3000)) + "\n")
    (d / "containers_b").write_text("\n".join(mode_b if mode_b is not None else table("bbbb", 7000)) + "\n")
    (d / "mode").write_text("a")
    for f in ("docker.log", "nsenter.log", "violations.log"):
        (d / f).write_text("")
    return d


def env_for(d, **extra):
    e = dict(os.environ)
    e["PATH"] = f"{d}:{e['PATH']}"
    e["FAKE_DIR"] = str(d)
    e.update(extra)
    return e


def run(d, *args, script="netem_apply.sh"):
    return subprocess.run(["bash", str(HERE / script), *args], env=env_for(d), capture_output=True, text=True, timeout=60)


def lines(d, f):
    return [l for l in (d / f).read_text().splitlines() if l.strip()]


def pids(d, mode):
    return [l.split()[2] for l in lines(d, f"containers_{mode}")]


def test_n1_dry_run_lists_11_names_and_exact_commands(tmp_path):
    d = make_fake(tmp_path)
    r = run(d, "--dry-run", "wan")
    assert r.returncode == 0, r.stderr
    for n in NAMES:
        assert f"{n} (pid " in r.stdout
    assert "11 of 11 expected containers" in r.stdout
    for p in pids(d, "a"):
        assert f"+ nsenter -t {p} -n tc qdisc replace dev eth0 root netem delay 80ms loss 1%" in r.stdout
    assert lines(d, "nsenter.log") == []                       # dry-run enters no namespace
    assert lines(d, "violations.log") == []
    w = run(d, "--dry-run", "wan", script="netem_watch.sh")
    assert w.returncode == 0 and all(w.stdout.splitlines().count(f"  {n}") == 1 for n in NAMES)   # each name exactly once


def test_n2_apply_uses_replace_only_on_validated_pids(tmp_path):
    d = make_fake(tmp_path)
    r = run(d, "degraded")
    assert r.returncode == 0, r.stderr
    got = lines(d, "nsenter.log")
    assert sorted(got) == sorted(f"nsenter -t {p} -n tc qdisc replace dev eth0 root netem delay 200ms loss 5%" for p in pids(d, "a"))
    d2 = make_fake(tmp_path / "b")
    r2 = run(d2, "lan")
    assert r2.returncode == 0
    assert sorted(lines(d2, "nsenter.log")) == sorted(f"nsenter -t {p} -n tc qdisc del dev eth0 root" for p in pids(d2, "a"))
    d3 = make_fake(tmp_path / "c")
    assert run(d3, "mixed").returncode == 0
    mixed = lines(d3, "nsenter.log")
    assert sum("replace" in l for l in mixed) == 5 and sum("qdisc del" in l for l in mixed) == 6   # sites 5-9 delayed; evidence and sites 0-4 cleared


@pytest.mark.parametrize("anomaly", ["name", "label", "pid", "profile"])
def test_n3_any_anomaly_aborts_before_any_nsenter(tmp_path, anomaly):
    rows = [f"aaaa{i:02d} {n} {3000 + i} dibtnsm" for i, n in enumerate(NAMES)]
    profile = "wan"
    if anomaly == "name":
        rows.append("aaaa99 dibtnsm-evil-1 3999 dibtnsm")
    elif anomaly == "label":
        rows[4] = f"aaaa04 {NAMES[4]} 3004 someother"
    elif anomaly == "pid":
        rows[2] = f"aaaa02 {NAMES[2]} 1 dibtnsm"
    elif anomaly == "profile":
        profile = "bogus"
    d = make_fake(tmp_path, mode_a=rows)
    r = run(d, profile)
    assert r.returncode != 0
    assert lines(d, "nsenter.log") == [], f"{anomaly}: something was applied before aborting"


def test_n4_watcher_reapplies_after_recreation_and_ctrl_c_cleans_only_project(tmp_path):
    d = make_fake(tmp_path)
    p = subprocess.Popen(["bash", str(HERE / "netem_watch.sh"), "wan"], env=env_for(d, NETEM_WATCH_POLL="0.1"),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        def n_replace():
            return sum("qdisc replace" in l for l in lines(d, "nsenter.log"))
        t0 = time.time()
        while n_replace() < 11 and time.time() - t0 < 20:
            time.sleep(0.1)
        assert n_replace() == 11
        (d / "mode").write_text("b")                                     # the cluster is recreated: new IDs and pids
        t0 = time.time()
        while n_replace() < 22 and time.time() - t0 < 20:
            time.sleep(0.1)
        assert n_replace() == 22
        p.send_signal(signal.SIGINT)
        out, err = p.communicate(timeout=30)
    finally:
        if p.poll() is None:
            p.kill()
    assert p.returncode == 0, err
    log = lines(d, "nsenter.log")
    replaced = {re.search(r"-t (\d+)", l).group(1) for l in log if "qdisc replace" in l}
    deleted = [re.search(r"-t (\d+)", l).group(1) for l in log if "qdisc del" in l]
    assert replaced == set(pids(d, "a")) | set(pids(d, "b"))
    assert sorted(deleted) == sorted(pids(d, "b"))                       # cleanup: exactly the CURRENT validated containers
    assert all("tc qdisc replace dev eth0 root netem delay 80ms loss 1%" in l for l in log if "replace" in l)
    assert not any(("qdisc" not in l) for l in log)                      # nsenter is only ever used for tc qdisc


def test_n5_docker_shapes_never_unfiltered_never_other_verbs(tmp_path):
    allowed = [re.compile(r"^docker ps --filter label=com\.docker\.compose\.project=dibtnsm --format (\{\{\.Names\}\}|\{\{\.ID\}\} \{\{\.Names\}\})$"),
               re.compile(r'^docker inspect -f \{\{(index \.Config\.Labels "com\.docker\.compose\.project"|\.State\.Pid)\}\}( dibtnsm-(evidence|site-\d)-1)+$')]
    for k, args in enumerate([("--dry-run", "wan"), ("wan",), ("lan",), ("mixed",), ("degraded",)]):
        d = make_fake(tmp_path / f"s{k}")
        run(d, *args)
        run(d, "--dry-run", "wan", script="netem_watch.sh")
        run(d, script="netem_show.sh")
        assert lines(d, "violations.log") == []
        for l in lines(d, "docker.log"):
            assert any(a.match(l) for a in allowed), f"docker call outside the allowed shapes: {l}"


ALLOWED_DOCKER = [re.compile(r"^docker ps --filter label=com\.docker\.compose\.project=dibtnsm --format (\{\{\.Names\}\}|\{\{\.ID\}\} \{\{\.Names\}\})$"),
                  re.compile(r'^docker inspect -f \{\{(index \.Config\.Labels "com\.docker\.compose\.project"|\.State\.Pid)\}\}( dibtnsm-(evidence|site-\d)-1)+$')]


def assert_docker_shapes(d):
    assert lines(d, "violations.log") == []
    for l in lines(d, "docker.log"):
        assert any(a.match(l) for a in ALLOWED_DOCKER), f"docker call outside the allowed shapes: {l}"


def start_watch(d, *args, poll="0.1"):
    return subprocess.Popen(["bash", str(HERE / "netem_watch.sh"), *args], env=env_for(d, NETEM_WATCH_POLL=poll),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def wait_for(cond, secs=20):
    t0 = time.time()
    while not cond() and time.time() - t0 < secs:
        time.sleep(0.05)
    return cond()


class Logged:
    """Popen of the watcher whose stdout/stderr are read by threads as they are produced, so that a test can WAIT FOR A LOG LINE (the watcher
    prints `applied` only after the last `tc qdisc replace`: waiting for the number of replace calls and then signalling races with that line)."""
    def __init__(self, d, *args, poll="0.1"):
        import threading
        self.p = subprocess.Popen(["bash", str(HERE / "netem_watch.sh"), *args], env=env_for(d, NETEM_WATCH_POLL=poll),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.out, self.err = [], []
        self.threads = [threading.Thread(target=lambda s, b: [b.append(l) for l in s], args=(self.p.stdout, self.out), daemon=True),
                        threading.Thread(target=lambda s, b: [b.append(l) for l in s], args=(self.p.stderr, self.err), daemon=True)]
        for t in self.threads:
            t.start()

    def text(self):
        return "".join(self.out)

    def stop(self):
        self.p.send_signal(signal.SIGINT)
        try:
            self.p.wait(timeout=30)
        finally:
            if self.p.poll() is None:
                self.p.kill()
        for t in self.threads:
            t.join(timeout=5)
        return "".join(self.out), "".join(self.err)


def n_replace(d):
    return sum("qdisc replace" in l for l in lines(d, "nsenter.log"))


def stop(p):
    p.send_signal(signal.SIGINT)
    try:
        out, err = p.communicate(timeout=30)
    finally:
        if p.poll() is None:
            p.kill()
    return out, err


def test_n6_failed_apply_is_retried_without_a_change_of_the_list(tmp_path):
    d = make_fake(tmp_path)
    (d / "fail_once").write_text("")                      # the first `tc qdisc replace` fails once
    w = Logged(d, "wan")
    try:
        assert wait_for(lambda: "applied wan" in w.text())          # the log line, not the number of replace calls
    finally:
        out, err = w.stop()
    p = w.p
    assert n_replace(d) >= 12                                       # 1 failed call + 11 on the retry: the list never changed
    assert p.returncode == 0, err
    assert "apply FAILED" in err and out.count("applied wan") == 1
    assert_docker_shapes(d)


def test_n7_cleanup_failures_are_loud_and_nonzero(tmp_path):
    msg = "ATTENZIONE: pulizia netem NON riuscita, verifica con netem_show.sh"
    # (a) validation abort at cleanup time: a container with a foreign label appears just before Ctrl-C
    bad = [f"bbbb{i:02d} {n} {7000 + i} dibtnsm" for i, n in enumerate(NAMES)]
    bad[4] = f"bbbb04 {NAMES[4]} 7004 someother"
    d = make_fake(tmp_path / "a", mode_b=bad)
    p = start_watch(d, "wan")
    try:
        assert wait_for(lambda: n_replace(d) >= 11)
        (d / "mode").write_text("b")
    finally:
        out, err = stop(p)
    assert p.returncode != 0 and msg in err
    # (b) `del` fails and netem is still there (show reports netem)
    d = make_fake(tmp_path / "b")
    (d / "fail_del").write_text("")
    p = start_watch(d, "wan")
    try:
        assert wait_for(lambda: n_replace(d) >= 11)
    finally:
        out, err = stop(p)
    assert p.returncode != 0 and msg in err
    # (c) `del` fails only because there was no qdisc (show is clean): not a failure
    d = make_fake(tmp_path / "c")
    (d / "fail_del").write_text("")
    (d / "show_clean").write_text("")
    p = start_watch(d, "wan")
    try:
        assert wait_for(lambda: n_replace(d) >= 11)
    finally:
        out, err = stop(p)
    assert p.returncode == 0 and msg not in err, err
    assert_docker_shapes(d)


def test_n8_same_id_new_pid_is_reapplied_and_unexpected_names_never_inspected(tmp_path):
    same_ids_new_pids = [f"aaaa{i:02d} {n} {9000 + i} dibtnsm" for i, n in enumerate(NAMES)]
    d = make_fake(tmp_path, mode_b=same_ids_new_pids)
    p = start_watch(d, "wan")
    try:
        assert wait_for(lambda: n_replace(d) >= 11)
        (d / "mode").write_text("b")                       # compose kill/start: same IDs, new namespaces
        assert wait_for(lambda: n_replace(d) >= 22)
    finally:
        out, err = stop(p)
    assert p.returncode == 0, err
    got = {re.search(r"-t (\d+)", l).group(1) for l in lines(d, "nsenter.log") if "qdisc replace" in l}
    assert got == set(pids(d, "a")) | set(pids(d, "b"))
    assert_docker_shapes(d)
    # an unexpected name in `docker ps`: never inspected, nothing applied while it is there
    rows = [f"aaaa{i:02d} {n} {3000 + i} dibtnsm" for i, n in enumerate(NAMES)] + ["aaaa99 dibtnsm-evil-1 3999 dibtnsm"]
    d = make_fake(tmp_path / "x", mode_a=rows)
    p = start_watch(d, "wan")
    try:
        time.sleep(1.5)
    finally:
        out, err = stop(p)
    assert n_replace(d) == 0 and not any("evil" in l for l in lines(d, "docker.log") if l.startswith("docker inspect"))
    assert "apply FAILED" in err


def test_n9_poll_option_and_timestamps(tmp_path):
    d = make_fake(tmp_path)
    bad = subprocess.run(["bash", str(HERE / "netem_watch.sh"), "--poll", "abc", "wan"], env=env_for(d), capture_output=True, text=True)
    assert bad.returncode != 0 and lines(d, "nsenter.log") == []
    w = Logged(d, "--poll", "0.1", "wan", poll="0.5")               # the option, not the env variable, sets the interval here
    try:
        assert wait_for(lambda: "applied wan" in w.text())          # the log line, not the number of replace calls
    finally:
        out, err = w.stop()
    p = w.p
    assert n_replace(d) >= 11
    assert p.returncode == 0, err
    assert re.search(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z netem_watch: containers changed -> applying wan$", out, re.M)
    assert re.search(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z netem_watch: applied wan \(\d+\.\d+ s\)$", out, re.M)
    assert "polling every 0.1s" in out
