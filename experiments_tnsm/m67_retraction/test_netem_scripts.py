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
    fmt="$3"; name="$4"
    line=$(awk -v n="$name" '$2==n' "$D/containers_$mode")
    [[ -n "$line" ]] || { echo "NOT-A-FILTERED-CONTAINER: docker $*" >> "$D/violations.log"; exit 98; }
    if [[ "$fmt" == *"Labels"* ]]; then echo "$line" | awk '{print $4}'; else echo "$line" | awk '{print $3}'; fi ;;
  *) echo "FORBIDDEN: docker $*" >> "$D/violations.log"; exit 97 ;;
esac
'''
FAKE_NSENTER = r'''#!/usr/bin/env bash
echo "nsenter $*" >> "$FAKE_DIR/nsenter.log"
if [[ "$*" == *"tc qdisc show"* ]]; then echo "qdisc netem 8001: root refcnt 2 limit 1000 delay 80ms"; fi
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
    assert w.returncode == 0 and all(f"  {n}" in w.stdout for n in NAMES)


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
               re.compile(r'^docker inspect -f \{\{(index \.Config\.Labels "com\.docker\.compose\.project"|\.State\.Pid)\}\} dibtnsm-(evidence|site-\d)-1$')]
    for k, args in enumerate([("--dry-run", "wan"), ("wan",), ("lan",), ("mixed",), ("degraded",)]):
        d = make_fake(tmp_path / f"s{k}")
        run(d, *args)
        run(d, "--dry-run", "wan", script="netem_watch.sh")
        run(d, script="netem_show.sh")
        assert lines(d, "violations.log") == []
        for l in lines(d, "docker.log"):
            assert any(a.match(l) for a in allowed), f"docker call outside the allowed shapes: {l}"
