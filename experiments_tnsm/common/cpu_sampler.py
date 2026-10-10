"""CPU sampler for the measurement hosts (audit 18; standard library only, /proc and cgroup v2).

Library use: s = Sampler(interval=1.0, project="dibtnsm", pid=os.getpid()); s.start(); ...; samples = s.stop().
CLI (e.g. over ssh on the node):  python3 cpu_sampler.py --seconds 70 --interval 1 [--project dibtnsm] [--pid N]
prints one JSON line per sample (flushed), so the caller can stop it early.

Each sample: t_unix (this host's clock), host_busy_cores (all vCPUs, from /proc/stat), host_busy_pct,
host_steal_pct, containers {name: cores} (cgroup v2 cpu.stat usage_usec of each container of the compose
project, 1.0 = one vCPU), proc_cores (CPU of one process incl. all its threads, from /proc/<pid>/stat).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time

DOCKER = "/snap/bin/docker" if os.path.exists("/snap/bin/docker") else "docker"


def parse_stat_line(line: str) -> tuple[int, int, int]:
    f = [int(x) for x in line.split()[1:]]
    total = sum(f[:8])
    idle = f[3] + f[4]
    return total - idle, total, f[7]


def cores_between(a: tuple, b: tuple, ncpu: int) -> float:
    dt = b[1] - a[1]
    return 0.0 if dt <= 0 else (b[0] - a[0]) / dt * ncpu


def container_cores(prev_usec: int, cur_usec: int, seconds: float) -> float:
    return max(0.0, (cur_usec - prev_usec) / 1e6 / max(seconds, 1e-9))


def read_cgroup_usage(path: str):
    try:
        with open(path) as fh:
            for line in fh:
                if line.startswith("usage_usec"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None


def proc_ticks(pid: int):
    try:
        raw = open(f"/proc/{pid}/stat").read()
    except OSError:
        return None
    rest = raw[raw.rindex(")") + 2:].split()
    return int(rest[11]) + int(rest[12])


def project_containers(project: str) -> dict[str, str]:
    out = subprocess.run([DOCKER, "ps", "--no-trunc", "--format", "{{.ID}} {{.Names}}", "--filter",
                          f"label=com.docker.compose.project={project}"], capture_output=True, text=True, check=True).stdout
    return {name: cid for cid, name in (l.split() for l in out.splitlines() if l.strip())}


def cgroup_path(cid: str) -> str | None:
    for tpl in (f"/sys/fs/cgroup/system.slice/docker-{cid}.scope/cpu.stat", f"/sys/fs/cgroup/docker/{cid}/cpu.stat"):
        if os.path.exists(tpl):
            return tpl
    return None


class Sampler:
    def __init__(self, interval: float = 1.0, project: str | None = None, pid: int | None = None):
        self.interval, self.pid = interval, pid
        self.ncpu = os.cpu_count() or 1
        self.paths = {}
        if project:
            for name, cid in project_containers(project).items():
                p = cgroup_path(cid)
                if p:
                    self.paths[name] = p
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self._th: threading.Thread | None = None

    def _read(self):
        with open("/proc/stat") as fh:
            st = parse_stat_line(fh.readline())
        return time.time(), st, {n: read_cgroup_usage(p) for n, p in self.paths.items()}, \
            (proc_ticks(self.pid) if self.pid else None)

    def _loop(self, emit):
        prev = self._read()
        while not self._stop.wait(self.interval):
            cur = self._read()
            dt = cur[0] - prev[0]
            s = {"t_unix": cur[0], "seconds": dt,
                 "host_busy_cores": cores_between(prev[1], cur[1], self.ncpu),
                 "host_busy_pct": 100 * cores_between(prev[1], cur[1], self.ncpu) / self.ncpu,
                 "host_steal_pct": 100 * (cur[1][2] - prev[1][2]) / max(cur[1][1] - prev[1][1], 1),
                 "containers": {n: container_cores(prev[2][n], cur[2][n], dt) for n in self.paths
                                if prev[2].get(n) is not None and cur[2].get(n) is not None},
                 "proc_cores": (((cur[3] - prev[3]) / os.sysconf("SC_CLK_TCK") / dt) if self.pid and cur[3] is not None and prev[3] is not None else None)}
            self.samples.append(s)
            if emit:
                emit(s)
            prev = cur

    def start(self, emit=None):
        self._th = threading.Thread(target=self._loop, args=(emit,), daemon=True)
        self._th.start()

    def stop(self) -> list[dict]:
        self._stop.set()
        if self._th:
            self._th.join(timeout=5)
        return self.samples


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--project", default=None)
    ap.add_argument("--pid", type=int, default=None)
    a = ap.parse_args()
    s = Sampler(a.interval, a.project, a.pid)
    s.start(emit=lambda x: print(json.dumps(x), flush=True))
    time.sleep(a.seconds)
    s.stop()
