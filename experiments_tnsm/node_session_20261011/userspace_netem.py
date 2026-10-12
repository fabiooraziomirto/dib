#!/usr/bin/env python3
"""User-space stand-in for the root watcher (docs/audit/85): applies netem on the eth0 of every container of the compose project `dibtnsm` from INSIDE the container
(docker exec -u 0, NET_ADMIN granted by the extra compose file, the host's tc run through the host's dynamic loader), which is what netem_apply.sh does from outside with
nsenter. Same specs as the watcher; a container is (re)configured when it appears or the requested profile changes. Runs detached on the node, no sudo.
Usage: python3 userspace_netem.py --profile-file ~/dib_tnsm/m67/userspace_profile --log <file> [--poll 0.3]   (profile file holds lan|wan|degraded; STOP file = stop)"""
from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

DOCKER = "docker"
SPEC = {"lan": None, "wan": "delay 80ms loss 1%", "degraded": "delay 200ms loss 5%"}
LOADER = ["/hostlib/ld-linux-x86-64.so.2", "--library-path", "/hostlib", "/hosttc"]


def apply_cmd(name: str, spec: str | None) -> list[str]:
    tail = ["qdisc", "del", "dev", "eth0", "root"] if spec is None else ["qdisc", "replace", "dev", "eth0", "root", "netem", *spec.split()]
    return [DOCKER, "exec", "-u", "0", name, *LOADER, *tail]


def decide(containers: list[tuple[str, str]], profile: str, applied: dict) -> list[tuple[str, str]]:
    return [(cid, name) for cid, name in containers if applied.get(cid) != profile]


def forget_vanished(containers: list[tuple[str, str]], applied: dict) -> None:
    alive = {cid for cid, _ in containers}
    for cid in list(applied):
        if cid not in alive:
            del applied[cid]


def apply_all(containers, profile: str, applied: dict, runner) -> list[tuple[str, int]]:
    out = []
    for cid, name in decide(containers, profile, applied):
        rc = runner(apply_cmd(name, SPEC[profile]))
        out.append((name, rc))
        if rc == 0 or SPEC[profile] is None:     # `tc qdisc del` fails when there is nothing to delete: not an error for lan
            applied[cid] = profile
    return out


def _list() -> list[tuple[str, str]]:
    r = subprocess.run([DOCKER, "ps", "--filter", "label=com.docker.compose.project=dibtnsm", "--format", "{{.ID}} {{.Names}}"], capture_output=True, text=True, timeout=20)
    return [tuple(l.split(None, 1)) for l in r.stdout.splitlines() if l.strip()]


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, capture_output=True, timeout=30).returncode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile-file", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--poll", type=float, default=0.3)
    a = ap.parse_args()
    pf, stop = Path(a.profile_file), Path(a.profile_file + ".STOP")
    applied: dict = {}
    with open(a.log, "a") as log:
        while not stop.exists():
            try:
                profile = pf.read_text().strip() or "lan"
                cs = _list()
                forget_vanished(cs, applied)
                for name, rc in apply_all(cs, profile, applied, _run):
                    log.write(f"{time.strftime('%FT%T', time.gmtime())}.{int(time.time() * 1000) % 1000:03d}Z applied {profile} {name} rc={rc}\n")
                    log.flush()
            except Exception as exc:  # noqa: BLE001 -- the applier must survive a docker hiccup
                log.write(f"{time.strftime('%FT%TZ', time.gmtime())} error {exc!r}\n")
                log.flush()
            time.sleep(a.poll)


if __name__ == "__main__":
    main()
