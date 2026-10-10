"""Run a command and record wall time and peak RSS summed over its process tree.

Usage: python3 analysis_fs/measure.py <label> -- <command...>
Appends one row to analysis_fs/out/measurements.csv. Polls /proc every 0.5 s,
so short spikes between polls can be missed (peak is a lower bound).
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out" / "measurements.csv"


def tree_rss_kib(root: int) -> int:
    children: dict[int, list[int]] = {}
    rss: dict[int, int] = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/stat") as fh:
                ppid = int(fh.read().rsplit(")", 1)[1].split()[1])
            with open(f"/proc/{pid}/status") as fh:
                for line in fh:
                    if line.startswith("VmRSS:"):
                        rss[int(pid)] = int(line.split()[1])
                        break
            children.setdefault(ppid, []).append(int(pid))
        except (OSError, ValueError, IndexError):
            continue
    total, stack = 0, [root]
    while stack:
        p = stack.pop()
        total += rss.get(p, 0)
        stack += children.get(p, [])
    return total


def main() -> int:
    label, cmd = sys.argv[1], sys.argv[sys.argv.index("--") + 1:]
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd)
    peak = 0
    while proc.poll() is None:
        peak = max(peak, tree_rss_kib(proc.pid))
        time.sleep(0.5)
    wall = time.monotonic() - t0
    new = not OUT.exists()
    with OUT.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["label", "command", "returncode", "wall_s", "peak_rss_gib"])
        w.writerow([label, " ".join(cmd), proc.returncode, round(wall, 1), round(peak / 2**20, 2)])
    print(f"[measure] {label}: rc={proc.returncode} wall={wall:.0f}s peak_rss={peak / 2**20:.2f} GiB", flush=True)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
