"""Background-load monitor for the measurement node (audit 04 sez. 7.2, G4 not satisfied).

Standard library only (/proc). Measures, over a window:
  * steal_pct   share of CPU time stolen by the hypervisor (/proc/stat "steal");
  * busy_pct    share of non-idle CPU time over all vCPUs;
  * other_cores CPU used by user-space processes OTHER than the measuring process (and its
                threads), in cores (1.0 = one vCPU fully busy), from /proc/<pid>/stat
                utime+stime; kernel threads (kthreadd and its children) are excluded,
                because during a cell they mostly do I/O work caused by DIB itself;
  * kernel_cores CPU of kernel threads, reported separately (not used by the discard rule);
  * load1       1-minute load average at the end of the window;
  * top         the five non-DIB commands with the most CPU in the window.

Extensions (audit 18, 2026-10-10): idle_window() = background sample before a cell with
the system under test idle, excluding the containers of a compose project
(project_pids / pids_in_cgroups); `sample` subcommand for ssh. discard_rule.json is NOT
changed: its thresholds were fixed before the first M1/M2 cell.

Baseline mode (no DIB running), from the node:
    python3 node_monitor.py baseline --seconds 300 --interval 5 --out baseline.json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import time
from collections import defaultdict

CLK = os.sysconf("SC_CLK_TCK")


def cpu_times() -> list[int]:
    with open("/proc/stat") as fh:
        fields = fh.readline().split()[1:]
    return [int(x) for x in fields]  # user nice system idle iowait irq softirq steal guest guest_nice


def proc_ticks(exclude: set[int]) -> dict[int, tuple[str, int, bool]]:
    out = {}
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        if pid in exclude:
            continue
        try:
            with open(f"/proc/{pid}/stat") as fh:
                raw = fh.read()
        except OSError:
            continue
        comm = raw[raw.index("(") + 1:raw.rindex(")")]
        rest = raw[raw.rindex(")") + 2:].split()
        kernel = pid == 2 or int(rest[1]) == 2  # kthreadd or one of its children
        out[pid] = (comm, int(rest[11]) + int(rest[12]), kernel)  # utime + stime
    return out


class Snapshot:
    def __init__(self, exclude: set[int]):
        self.t = time.monotonic()
        self.cpu = cpu_times()
        self.procs = proc_ticks(exclude)


def window(a: Snapshot, b: Snapshot) -> dict:
    d = [y - x for x, y in zip(a.cpu, b.cpu)]
    total = sum(d[:8]) or 1  # guest time is already counted in user
    idle = d[3] + d[4]
    steal = d[7]
    per_comm: dict[str, int] = defaultdict(int)
    other = kernel_ticks = 0
    for pid, (comm, ticks, kernel) in b.procs.items():
        prev = a.procs.get(pid)
        delta = ticks - prev[1] if prev else 0  # new processes: not counted (no start value)
        if delta <= 0:
            continue
        if kernel:
            kernel_ticks += delta
        else:
            other += delta
            per_comm[comm] += delta
    secs = max(b.t - a.t, 1e-9)
    top = sorted(per_comm.items(), key=lambda kv: -kv[1])[:5]
    with open("/proc/loadavg") as fh:
        load1 = float(fh.read().split()[0])
    return {
        "seconds": round(secs, 3),
        "steal_pct": round(100 * steal / total, 3),
        "busy_pct": round(100 * (total - idle) / total, 3),
        "other_cores": round(other / CLK / secs, 4),
        "kernel_cores": round(kernel_ticks / CLK / secs, 4),
        "load1": load1,
        "top": [[c, round(t / CLK / secs, 4)] for c, t in top],
    }


def own_pids() -> set[int]:
    pid = os.getpid()
    return {pid} | {int(t) for t in os.listdir(f"/proc/{pid}/task")}


def short_window(seconds: float = 2.0, exclude: set[int] | None = None) -> dict:
    ex = own_pids() | (exclude or set())
    a = Snapshot(ex)
    time.sleep(seconds)
    b = Snapshot(ex)
    return window(a, b)


def pids_in_cgroups(container_ids: list[str], proc_root: str = "/proc") -> set[int]:
    """Pids whose /proc/<pid>/cgroup mentions one of the (full) container ids: the processes
    of the system under test, which must not count as background load (audit 18)."""
    found = set()
    if not container_ids:
        return found
    for name in os.listdir(proc_root):
        if not name.isdigit():
            continue
        try:
            with open(f"{proc_root}/{name}/cgroup") as fh:
                text = fh.read()
        except OSError:
            continue
        if any(cid in text for cid in container_ids):
            found.add(int(name))
    return found


def project_pids(project: str = "dibtnsm", docker: str = "/snap/bin/docker") -> set[int]:
    """Pids of every container of the compose project (label com.docker.compose.project)."""
    import subprocess

    exe = docker if os.path.exists(docker) else "docker"
    out = subprocess.run([exe, "ps", "--no-trunc", "-q", "--filter", f"label=com.docker.compose.project={project}"],
                         capture_output=True, text=True, check=True).stdout.split()
    return pids_in_cgroups(out)


def idle_window(seconds: float = 12.0, project: str | None = None) -> dict:
    """Background sample taken BEFORE a cell, with the system under test idle (audit 18):
    other_cores and steal_pct over ``seconds`` (10-15 s recommended), excluding the measuring
    process and, if ``project`` is given, every container of that compose project. Unlike
    load1, it does not include the previous cell."""
    return short_window(seconds, exclude=project_pids(project) if project else None)


def disk_free_mb(path: str = "/") -> int:
    return shutil.disk_usage(path).free // (1024 * 1024)


def fs_info(path: str = "/tmp") -> dict:
    """Filesystem of ``path`` (where the cell databases live) from /proc/self/mountinfo."""
    real = os.path.realpath(path)
    best = ("", "", "")
    with open("/proc/self/mountinfo") as fh:
        for line in fh:
            left, right = line.split(" - ", 1)
            mount = left.split()[4]
            fstype, source = right.split()[:2]
            if (real == mount or real.startswith(mount.rstrip("/") + "/")) and len(mount) > len(best[0]):
                best = (mount, fstype, source)
    usage = shutil.disk_usage(real)
    return {"path": path, "mount": best[0], "fstype": best[1], "source": best[2],
            "free_mb": usage.free // (1024 * 1024), "used_pct": round(100 * usage.used / usage.total, 1)}


def fsync_bench(directory: str, n: int = 500, size: int = 4096) -> dict:
    """Latency of write(size)+fsync, n times on one file in ``directory`` (removed after)."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "fsync_probe.bin")
    lat = []
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        block = b"\0" * size
        for _ in range(n):
            t = time.perf_counter()
            os.write(fd, block)
            os.fsync(fd)
            lat.append(time.perf_counter() - t)
    finally:
        os.close(fd)
        os.unlink(path)
    lat.sort()

    def q(p):
        return round(lat[min(n - 1, int(round(p * (n - 1))))] * 1000, 4)
    return {"n": n, "bytes": size, "p50_ms": q(0.5), "p95_ms": q(0.95), "p99_ms": q(0.99),
            "max_ms": round(lat[-1] * 1000, 4), "mean_ms": round(sum(lat) / n * 1000, 4)}


def host_info() -> dict:
    model = ""
    with open("/proc/cpuinfo") as fh:
        for line in fh:
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    with open("/proc/meminfo") as fh:
        mem_kb = int(fh.readline().split()[1])
    return {"hostname": platform.node(), "kernel": platform.release(), "platform": platform.platform(),
            "cpu_model": model, "nproc": os.cpu_count(), "mem_total_gib": round(mem_kb / 1024 / 1024, 2),
            "avx2": "avx2" in open("/proc/cpuinfo").read()}


def baseline(seconds: int, interval: float) -> dict:
    samples = []
    end = time.monotonic() + seconds
    prev = Snapshot(own_pids())
    while time.monotonic() < end:
        time.sleep(interval)
        cur = Snapshot(own_pids())
        samples.append({"t_end_unix": round(time.time(), 1), **window(prev, cur)})
        prev = cur
    return {"host": host_info(), "seconds": seconds, "interval": interval,
            "disk_free_mb": disk_free_mb(), "samples": samples}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sm = sub.add_parser("sample", help="one window, printed as JSON (e.g. over ssh)")
    sm.add_argument("--seconds", type=float, default=12.0)
    sm.add_argument("--exclude-project", default=None, help="compose project whose containers are excluded")
    b = sub.add_parser("baseline")
    b.add_argument("--seconds", type=int, default=300)
    b.add_argument("--interval", type=float, default=5.0)
    b.add_argument("--out", required=True)
    a = p.parse_args()
    if a.cmd == "sample":
        print(json.dumps(idle_window(a.seconds, a.exclude_project)))
        raise SystemExit(0)
    result = baseline(a.seconds, a.interval)
    with open(a.out, "w") as fh:
        json.dump(result, fh, indent=1)
    print(f"wrote {len(result['samples'])} samples to {a.out}")
