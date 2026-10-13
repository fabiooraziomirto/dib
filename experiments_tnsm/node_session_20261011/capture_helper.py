#!/usr/bin/env python3
"""Starts sniff_in_container.py inside the evidence and site containers of the compose project `dibtnsm` as they appear (audit 116), without sudo and without touching the code under test:
`docker exec -d -u 0 <name> python /capture/sniff_in_container.py /capture/gen<N>/<name>.jsonl --name <name>`. /capture is a host directory bind-mounted by the extra compose file of
deploy_capture.sh. A new generation N starts when a container never seen before appears after >= GEN_QUIET_S seconds without new containers (the cluster is recreated per arm).
Usage: python3 capture_helper.py --capture-dir ~/dib_tnsm/m67/capture --log <file> [--poll 0.2]   (STOP file = <capture-dir>/HELPER.STOP)"""
from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

DOCKER = "docker"
GEN_QUIET_S = 20.0


def wanted(name: str) -> bool:
    return name.startswith("dibtnsm-evidence") or name.startswith("dibtnsm-site-")


def assign(state: dict, containers: list[tuple[str, str]], now: float) -> list[tuple[int, str, str]]:
    """New (generation, id, name) for the wanted containers not seen yet; state = {"gen", "last_new", "seen"}."""
    out = []
    for cid, name in containers:
        if cid in state["seen"] or not wanted(name):
            continue
        if now - state["last_new"] > GEN_QUIET_S:
            state["gen"] += 1
        state["last_new"] = now
        state["seen"].add(cid)
        out.append((state["gen"], cid, name))
    return out


def exec_cmd(name: str, gen: int) -> list[str]:
    return [DOCKER, "exec", "-d", "-u", "0", name, "python", "/capture/sniff_in_container.py", f"/capture/gen{gen}/{name}.jsonl", "--name", name]


def _list() -> list[tuple[str, str]]:
    r = subprocess.run([DOCKER, "ps", "--filter", "label=com.docker.compose.project=dibtnsm", "--format", "{{.ID}} {{.Names}}"], capture_output=True, text=True, timeout=20)
    return [tuple(l.split(None, 1)) for l in r.stdout.splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture-dir", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--poll", type=float, default=0.2)
    a = ap.parse_args()
    cd = Path(a.capture_dir)
    stop = cd / "HELPER.STOP"
    state = {"gen": 0, "last_new": float("-inf"), "seen": set()}
    with open(a.log, "a") as log:
        while not stop.exists():
            try:
                for gen, cid, name in assign(state, _list(), time.time()):
                    (cd / f"gen{gen}").mkdir(parents=True, exist_ok=True)
                    r = subprocess.run(exec_cmd(name, gen), capture_output=True, text=True, timeout=30)
                    log.write(f"{time.strftime('%FT%TZ', time.gmtime())} gen{gen} {name} {cid} rc={r.returncode} {r.stderr.strip()[:120]}\n")
                    log.flush()
            except Exception as exc:  # noqa: BLE001 -- the helper must survive a docker hiccup
                log.write(f"{time.strftime('%FT%TZ', time.gmtime())} error {exc!r}\n")
                log.flush()
            time.sleep(a.poll)


if __name__ == "__main__":
    main()
