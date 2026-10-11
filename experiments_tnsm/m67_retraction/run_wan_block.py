#!/usr/bin/env python3
"""Orchestrator of the `wan` block, run by the USER on the workstation (not on the node). New file, NOT one of the 18 frozen files, no change to
run.py or to any measuring script; it only calls the frozen ones on the node from tree-bf272e8 through ssh. No sudo: the watcher
(netem_watch.sh) and netem_show.sh stay with the user, in other terminals.

Hypotheses (declared before running): H-flow the sequence W1 (calibration with a long hold) -> user verification -> W2 (copy + sha256)
-> thresholds committed BEFORE any B1 datum -> W3 (B1, four groups, seed 20261014, 10 episodes) -> W4 (copy + sha256 + analysis with the
adjacent-lan reference) runs without manual steps; H-guard every node command stops by itself on any of: dibtnsm container, run.py running,
watcher missing (absent for the optional lan-after block), < 2 GB free, PKI expiring in < 2 h; the guard strings never contain the
contiguous names they look for (a pgrep -f would find its own shell). Falsification: any step failing aborts the whole run with the reason;
nothing is retried silently, nothing is deleted on the node.
Steps:
  1. preflight (read-only guard);
  2. W1: calib_profile.py --profile wan --hold 240 in the background on the node (out calib_wan_b); the script waits for VERIFY_NOW and ASKS YOU:
     run `sudo bash /usr/local/lib/dib-netem/netem_show.sh` now (11 namespaces, delay 80ms loss 1%) and answer s/N. Anything but `s` aborts;
  3. W2: copies calib_wan_b, compares sha256 on both sides, requires rtt_check_ok, writes plog_thresholds_wan.json with the night's rule
     (make_plog_thresholds.py), COMMITS it (git commit -- <paths>, only those paths), copies it to the node;
  4. W3: B1 in the background (all four groups in one invocation) with the new thresholds file and p95; the script prints progress;
  5. W4: copies b1 with sha256, runs analyze_b1.py with --lan-ref lan_ref_20261011/before, commits data and analysis (only those paths);
  6. with --lan-dopo: asks you to stop the watcher and to check netem_show clean, then runs the four lan cells and the L_dns at lan ("after"),
     copies them with sha256 and analyses them (descriptive).
Usage: python3 run_wan_block.py [--dry-run] [--lan-dopo | --only-lan-dopo]   (watcher `wan` already running in the tmux session, poll 0.5)"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

HOST = "ubuntu@192.168.100.57"
KEY = str(Path.home() / ".ssh/id_ed25519_lab")
TREE = "$HOME/dib_tnsm/tree-bf272e8"
OUT = "$HOME/dib_tnsm/out/wan_20261011"
PY = "$HOME/dib_tnsm/venv/bin/python"
LOCAL = HERE / "wan_20261011"
LAN_REF = HERE / "lan_ref_20261011" / "before"
HOLD_S = 240


def guard(watcher: str) -> str:
    """Remote guard; watcher in {"required", "absent"}. The names are split so that pgrep -f cannot find its own shell."""
    g = ('set -e; export PATH=/snap/bin:$PATH; P="m67_retr""action/run.py"; W="netem_wa""tch"; '
         '[ -z "$(docker ps -a -q --filter label=com.docker.compose.project=dibtnsm)" ]; '
         'if pgrep -f "$P" >/dev/null; then echo "run.py in esecuzione"; exit 1; fi; ')
    if watcher == "required":
        g += 'if ! pgrep -f "$W" >/dev/null; then echo "watcher assente"; exit 1; fi; '
    else:
        g += 'if pgrep -f "$W" >/dev/null; then echo "watcher attivo"; exit 1; fi; '
    g += ('df -h / | tail -1; [ "$(df --output=avail -B1 / | tail -1)" -gt 2000000000 ]; '
          'openssl x509 -in ~/dib_tnsm/pki/ca.crt -noout -checkend 7200; '
          f'T={TREE}; OUT={OUT}; R="experiments_tnsm/m67_retr""action/run.py"; mkdir -p $OUT; export T OUT R; ')
    return g


def background(name: str, inner: str, watcher: str) -> str:
    """Start `inner` (no double quotes in it) detached on the node; its exit status goes to $OUT/<name>.rc."""
    return guard(watcher) + (f'rm -f $OUT/{name}.rc; setsid nohup bash -c "{inner}; echo \\$? > $OUT/{name}.rc" '
                             '> /dev/null 2>&1 < /dev/null & echo avviato')


def calib_cmd(profile: str, sub: str, hold: int) -> str:
    return f'{PY} $T/experiments_tnsm/m67_retraction/calib_profile.py --tree $T --out $OUT/{sub} --profile {profile} --hold {hold} > $OUT/{sub}.stdout 2>&1'


def b1_cmd(p95: float) -> str:
    return (f'cd $T && {PY} $R --block b1 --profile wan --tree $T --out $OUT/b1 --arms D,C --fanouts 1,10 --seed 20261014 '
            f'--profile-wait 90 --plog-thresholds $OUT/plog_thresholds_wan.json --plog-p95-ms {p95!r} > $OUT/b1.stdout 2>&1')


def lan_cmd() -> str:
    return (f'cd $T && {PY} $R --block b1 --profile lan --tree $T --out $OUT/lan_after --arms D,C --fanouts 1,10 --seed 20261014 '
            '> $OUT/lan_after.stdout 2>&1')


def plan() -> list[tuple[str, str]]:
    return [("preflight", guard("required") + 'echo preflight ok'),
            ("W1 calibrazione wan (background)", background("calib_wan_b", calib_cmd("wan", "calib_wan_b", HOLD_S), "required")),
            ("W3 B1 wan (background)", background("b1", b1_cmd(0.0), "required")),
            ("lan dopo, celle", background("lan_after", lan_cmd(), "absent")),
            ("lan dopo, L_dns", background("ldns_after", calib_cmd("lan", "ldns_after", 0), "absent"))]


class Abort(Exception):
    pass


def ssh(cmd: str, timeout: float = 120.0) -> str:
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-i", KEY, HOST, cmd], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise Abort(f"ssh rc={r.returncode}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def scp(src_remote: str, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["scp", "-q", "-r", "-i", KEY, f"{HOST}:dib_tnsm/out/wan_20261011/{src_remote}", str(dst)], capture_output=True, text=True)
    if r.returncode != 0:
        raise Abort(f"scp {src_remote}: {r.stderr}")


def scp_to_node(local: Path, remote: str) -> None:
    r = subprocess.run(["scp", "-q", "-i", KEY, str(local), f"{HOST}:dib_tnsm/out/wan_20261011/{remote}"], capture_output=True, text=True)
    if r.returncode != 0:
        raise Abort(f"scp to node: {r.stderr}")


def sha_local(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def copy_verified(sub: str, files: list[str]) -> None:
    """scp OUT/<sub> into LOCAL and require the sha256 of every listed file to match the node's."""
    if (LOCAL / sub).exists():
        raise Abort(f"{LOCAL / sub} already exists locally: move it away first (nothing is overwritten)")
    out = ssh("cd ~/dib_tnsm/out/wan_20261011 && sha256sum " + " ".join(f"{sub}/{f}" for f in files))
    remote = {ln.split()[1]: ln.split()[0] for ln in out.splitlines() if ln.strip()}
    scp(sub, LOCAL)
    for f in files:
        h = sha_local(LOCAL / sub / f)
        if remote.get(f"{sub}/{f}") != h:
            raise Abort(f"sha256 mismatch on {sub}/{f}: node {remote.get(f'{sub}/{f}')} local {h}")
        print(f"  sha256 ok {sub}/{f} {h[:12]}")


def wait_rc(name: str, label: str, max_s: float, tail: str | None = None, every: float = 20.0) -> int:
    t0, seen = time.time(), ""
    while time.time() - t0 < max_s:
        time.sleep(every)
        try:
            rc = ssh(f"cat ~/dib_tnsm/out/wan_20261011/{name}.rc 2>/dev/null || true").strip()
            if tail:
                cur = ssh(f"tail -n 3 ~/dib_tnsm/out/wan_20261011/{tail} 2>/dev/null || true")
                if cur != seen:
                    print(cur.rstrip())
                    seen = cur
        except Abort as exc:
            print(f"  (poll failed, retrying: {exc})")
            continue
        if rc:
            print(f"{label}: finished, rc={rc}")
            return int(rc)
    raise Abort(f"{label}: not finished within {max_s:.0f} s (the job keeps running on the node; nothing was killed)")


def git_commit(paths: list[Path], msg: str) -> None:
    rel = [str(p.relative_to(REPO)) for p in paths]
    subprocess.run(["git", "-C", str(REPO), "add", "--", *rel], check=True)
    print(subprocess.run(["git", "-C", str(REPO), "status", "--short", "--", *rel], capture_output=True, text=True).stdout)
    subprocess.run(["git", "-C", str(REPO), "commit", "-q", "-m", msg, "--", *rel], check=True)


def analyze(args: list[str]) -> None:
    r = subprocess.run([sys.executable, str(HERE / "analyze_b1.py"), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise Abort(f"analyze_b1.py failed:\n{r.stderr[-1500:]}")


def lan_dopo() -> None:
    """The `lan` session AFTER the wan block: 4 cells + L_dns at lan, then wan rule (a) re-analysed with before+after (higher median)."""
    print("lan dopo")
    print("\n>>> Ferma il watcher (Ctrl-C nel tmux, aspetta la pulizia) e verifica netem_show.sh PULITO (nessun namespace con netem).")
    if not ask("watcher fermato e netem_show pulito?"):
        raise Abort("lan-after not confirmed")
    print(ssh(background("lan_after", lan_cmd(), "absent")).strip())          # the guard also refuses if the watcher is still running
    if wait_rc("lan_after", "lan after", 1200, tail="lan_after.stdout", every=30) != 0:
        raise Abort("lan-after run.py failed")
    print(ssh(background("ldns_after", calib_cmd("lan", "ldns_after", 0), "absent")).strip())
    if wait_rc("ldns_after", "L_dns lan after", 600) != 0:
        raise Abort("L_dns lan-after failed")
    copy_verified("lan_after", ["cells.jsonl", "manifest.json", "episodes.jsonl"])
    copy_verified("ldns_after", ["calib_ldns_lan.txt"])
    print("  L_dns lan after:", (LOCAL / "ldns_after" / "calib_ldns_lan.txt").read_text().strip())
    an2, an3 = LOCAL / "analysis_lan_after.md", LOCAL / "analysis_wan_before_after.md"
    analyze([str(LOCAL / "lan_after"), "--out", str(an2)])
    analyze([str(LOCAL / "b1"), "--lan-ref", str(LAN_REF), "--lan-ref", str(LOCAL / "lan_after"), "--out", str(an3)])
    git_commit([LOCAL / "lan_after", LOCAL / "ldns_after", an2, an3], "experiments: lan session after the wan block (4 cells + L_dns), copied with matching sha256; wan rule (a) with before+after reference")


def ask(q: str) -> bool:
    if not sys.stdin.isatty():
        raise Abort("interactive confirmation needed (no tty)")
    return input(q + " [s/N] ").strip().lower() == "s"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lan-dopo", action="store_true")
    ap.add_argument("--only-lan-dopo", action="store_true", help="only the lan-after session (the wan block was already run)")
    a = ap.parse_args()
    if a.dry_run:
        for label, cmd in plan():
            print(f"### {label}\nssh {HOST} '{cmd}'\n")
        return 0
    try:
        if a.only_lan_dopo:
            lan_dopo()
            print("\nFINE (solo lan dopo).")
            return 0
        import make_plog_thresholds as mt
        print("1. preflight:\n" + ssh(guard("required") + "echo preflight ok"))
        print(f"2. W1: calibration wan with hold {HOLD_S} s, in the background...")
        print(ssh(background("calib_wan_b", calib_cmd("wan", "calib_wan_b", HOLD_S), "required")).strip())
        t0 = time.time()
        while "VERIFY_NOW" not in ssh("cat ~/dib_tnsm/out/wan_20261011/calib_wan_b.stdout 2>/dev/null || true"):
            if ssh("cat ~/dib_tnsm/out/wan_20261011/calib_wan_b.rc 2>/dev/null || true").strip():
                raise Abort("calibration ended before VERIFY_NOW (profile not confirmed by the RTT? watcher not applying?): see calib_wan_b.stdout on the node")
            if time.time() - t0 > 240:
                raise Abort("VERIFY_NOW not seen in 240 s (profile not confirmed by the RTT? see calib_wan_b.stdout on the node)")
            time.sleep(3)
        print(f"\n>>> VERIFY_NOW ({HOLD_S} s di hold): in un altro terminale lancia\n    ssh -t -i ~/.ssh/id_ed25519_lab {HOST} 'sudo bash /usr/local/lib/dib-netem/netem_show.sh'\n"
              "    devono comparire 11 namespace con delay 80ms loss 1%.")
        if not ask("netem_show.sh conferma il profilo wan?"):
            raise Abort("verification not confirmed by the user: stop (the cluster is torn down by the calibration at the end of the hold)")
        rc = wait_rc("calib_wan_b", "W1", 600)
        if rc != 0:
            raise Abort(f"calibration rc={rc}")
        print("3. W2: copy and sha256")
        copy_verified("calib_wan_b", ["calib_logs_wan.json", "calib_wan_result.json", "calib_ldns_wan.txt"])
        res = json.loads((LOCAL / "calib_wan_b" / "calib_wan_result.json").read_text())
        if not res.get("rtt_check_ok"):
            raise Abort("rtt_check_ok is not true in calib_wan_result.json")
        print("  L_dns wan:", (LOCAL / "calib_wan_b" / "calib_ldns_wan.txt").read_text().strip())
        thr = mt.build(LOCAL / "calib_wan_b", "wan")
        tf = LOCAL / "plog_thresholds_wan.json"
        tf.write_text(json.dumps(thr, indent=1))
        print(f"  thresholds sha256 {sha_local(tf)}  p95 {thr['calibrated_p95_ms']} ms  {[(k, v['threshold_ms'], v['accepted']) for k, v in thr['cells'].items()]}")
        git_commit([tf, LOCAL / "calib_wan_b"], f"experiments: wan calibration (verified by the user) and P-log thresholds {sha_local(tf)[:12]} committed before B1")
        scp_to_node(tf, "plog_thresholds_wan.json")
        out = ssh("sha256sum ~/dib_tnsm/out/wan_20261011/plog_thresholds_wan.json")
        if out.split()[0] != sha_local(tf):
            raise Abort("thresholds file differs on the node")
        print("4. W3: B1 wan (four groups) in the background")
        print(ssh(background("b1", b1_cmd(thr["calibrated_p95_ms"]), "required")).strip())
        rc = wait_rc("b1", "B1", 3000, tail="b1.stdout", every=30)
        if rc != 0:
            raise Abort(f"run.py rc={rc} (the partial data stay on the node; copy them with scp before anything else)")
        print("5. W4: copy and sha256, analysis")
        copy_verified("b1", ["cells.jsonl", "manifest.json", "episodes.jsonl"])
        an = LOCAL / "analysis_wan.md"
        analyze([str(LOCAL / "b1"), "--lan-ref", str(LAN_REF), "--out", str(an)])
        git_commit([LOCAL / "b1", an], "experiments: B1 wan rerun (tree bf272e8), copied with matching sha256, analysed with the adjacent lan reference")
        print(f"  analysis: {an}")
        if a.lan_dopo:
            lan_dopo()
        print("\nFINE. Dati copiati e committati; mandami: 'wan finito' (il watcher lo ferma l'utente quando vuole).")
        return 0
    except Abort as exc:
        print(f"\nABORT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
