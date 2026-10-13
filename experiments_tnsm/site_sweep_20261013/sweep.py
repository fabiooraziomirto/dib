"""Site-count sweep on the reference service (pre-registration: docs/audit/123).

For each transport (http, then mtls) and each N in 1, 2, 5, 10: generate the compose
file with generate_compose.py into the run directory (project `dibsweep`; the
checked-in compose under code/src is not touched), build and start 1 evidence + N
site containers, verify sha256 of /app/service.py and mtls.py INSIDE every container
(mismatch = stop), seed as the old benchmark, run the cells W in 1, 10, 50, 100
(warm-up discarded, 5 repetitions), tear down with volumes. One campaign at a time
on this host; load average and host CPU busy fraction are recorded per repetition.

Resources per repetition: CPU seconds of every container (cgroup v2 cpu.stat
usage_usec delta), memory.current sampled every 0.5 s (max), memory.peak at the
end (since container start), CPU seconds of the load-generator process, host-wide
busy CPU fraction (/proc/stat), load average.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CODE = ROOT / "code"
DIST = CODE / "src/dib/registry/distributed"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CODE))
import mgmt_bench  # noqa: E402

PROJECT = "dibsweep"
PY = sys.executable


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cmd, check=True, **kw):
    return subprocess.run(cmd, check=check, capture_output=True, text=True, **kw)


def host_cpu() -> tuple[int, int]:
    f = [int(x) for x in Path("/proc/stat").read_text().split("\n", 1)[0].split()[1:]]
    idle = f[3] + f[4]
    return sum(f), idle


class Sampler:
    def __init__(self, containers: dict[str, str]):
        self.cg = {svc: Path(f"/sys/fs/cgroup/system.slice/docker-{cid}.scope") for svc, cid in containers.items()}
        self._stop = threading.Event()

    def _cpu(self) -> dict[str, int]:
        out = {}
        for svc, p in self.cg.items():
            line = next(l for l in (p / "cpu.stat").read_text().splitlines() if l.startswith("usage_usec"))
            out[svc] = int(line.split()[1])
        return out

    def _mem_loop(self):
        while not self._stop.is_set():
            for svc, p in self.cg.items():
                try:
                    v = int((p / "memory.current").read_text())
                    self.mem_max[svc] = max(self.mem_max.get(svc, 0), v)
                except OSError:
                    pass
            self._stop.wait(0.5)

    def begin(self):
        self.mem_max = {}
        self._stop.clear()
        self.t = threading.Thread(target=self._mem_loop, daemon=True)
        self.t.start()
        self.cpu0, self.host0, self.wall0 = self._cpu(), host_cpu(), time.monotonic()

    def end(self) -> dict:
        cpu1, host1, wall = self._cpu(), host_cpu(), time.monotonic() - self.wall0
        self._stop.set()
        self.t.join(timeout=2)
        tot, idle = host1[0] - self.host0[0], host1[1] - self.host0[1]
        return {"container_cpu_s": {s: (cpu1[s] - self.cpu0[s]) / 1e6 for s in cpu1},
                "container_mem_max_bytes": self.mem_max,
                "container_mem_peak_bytes": {s: int((p / "memory.peak").read_text()) for s, p in self.cg.items()},
                "host_busy_fraction": (tot - idle) / tot if tot else None,
                "loadavg": os.getloadavg(), "sampler_wall_s": wall}


def up(n: int, mtls: bool, pki: Path, out: Path) -> dict[str, str]:
    env = dict(os.environ, DIB_DIST_N_SITES=str(n), DIB_DIST_MTLS="1" if mtls else "0", DIB_DIST_PKI_DIR=str(pki))
    text = run([PY, str(DIST / "generate_compose.py")], env=env).stdout.replace("context: ../../../..", f"context: {CODE}")
    compose = out / f"compose_n{n}.yml"
    compose.write_text(text)
    dc = ["docker", "compose", "-p", PROJECT, "-f", str(compose)]
    run(dc + ["down", "-v", "--remove-orphans"], check=False)
    r = run(dc + ["up", "-d", "--build"], check=False)
    (out / f"up_n{n}.log").write_text(r.stdout + r.stderr)
    if r.returncode:
        raise RuntimeError(f"compose up failed for N={n}")
    names = dict(l.split() for l in run(dc + ["ps", "--format", "{{.Service}} {{.ID}}"]).stdout.splitlines() if l.strip())
    ids = {svc: run(["docker", "inspect", "-f", "{{.Id}}", cid]).stdout.strip() for svc, cid in names.items()}
    import httpx
    scheme = "https" if mtls else "http"
    if mtls:
        from dib.registry.distributed import mtls as m
        client = httpx.Client(timeout=5, verify=m.client_context(pki / "admin.crt", pki / "admin.key", pki / "ca.crt"))
    else:
        client = httpx.Client(timeout=5, trust_env=False)
    urls = [f"{scheme}://localhost:18100"] + [f"{scheme}://localhost:{18110 + i}" for i in range(n)]
    deadline = time.monotonic() + 120
    while urls and time.monotonic() < deadline:
        for u in list(urls):
            try:
                if client.get(u + "/health").status_code == 200:
                    urls.remove(u)
            except httpx.HTTPError:
                pass
        time.sleep(0.5)
    client.close()
    if urls:
        raise RuntimeError(f"health timeout {urls}")
    return ids


def verify(ids: dict[str, str]) -> dict:
    want = {"/app/service.py": sha(DIST / "service.py"), "/app/dib/registry/distributed/mtls.py": sha(DIST / "mtls.py")}
    seen = {}
    for svc, cid in sorted(ids.items()):
        out = run(["docker", "exec", cid, "sha256sum", *want]).stdout.split()
        got = dict(zip(out[1::2], out[0::2]))
        seen[svc] = {"image": run(["docker", "inspect", "-f", "{{.Image}}", cid]).stdout.strip(), **got}
        if got != want:
            raise RuntimeError(f"image mismatch in {svc}: {got}")
    return seen


def down(out: Path, n: int) -> None:
    run(["docker", "compose", "-p", PROJECT, "-f", str(out / f"compose_n{n}.yml"), "down", "-v", "--remove-orphans"], check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--transport", choices=["http", "mtls"], required=True)
    ap.add_argument("--pki", type=Path, help="directory OUTSIDE the repository (mtls)")
    ap.add_argument("--sites", default="1,2,5,10")
    ap.add_argument("--workers", default="1,10,50,100")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--min-requests", type=int, default=1000, help="ops_per_worker = max(20, min_requests // W)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    mtls = a.transport == "mtls"
    if mtls:
        from scripts.make_dist_pki import build
        nb = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)
        (a.out / "pki_manifest.json").write_text(json.dumps(build(a.pki, 10, nb, 72.0, ["cam-a", "cam-b", "cam-c"]), indent=1) + "\n")
    manifest = {"prereg": "docs/audit/123", "transport": a.transport, "started_utc": datetime.now(timezone.utc).isoformat(),
                "commit": run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip(),
                "dirty": run(["git", "status", "--porcelain"], cwd=ROOT).stdout.splitlines(),
                "tree_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [DIST / "service.py", DIST / "mtls.py", DIST / "Dockerfile",
                                DIST / "generate_compose.py", HERE / "mgmt_bench.py", HERE / "sweep.py",
                                CODE / "scripts/distributed_concurrency_benchmark.py"]},
                "python": sys.version.split()[0], "nproc": os.cpu_count(), "mix": mgmt_bench.MIX,
                "client": "one process, ThreadPoolExecutor(W); shared httpx.Client timeout 5 s (http) or one client per identity (mtls)",
                "cells": []}
    try:
        for n in [int(x) for x in a.sites.split(",")]:
            ids = up(n, mtls, a.pki, a.out)
            manifest.setdefault("containers", {})[str(n)] = verify(ids)
            scheme = "https" if mtls else "http"
            mgmt_bench.base.configure(evidence_url=f"{scheme}://localhost:18100",
                                      site_urls=[f"{scheme}://localhost:{18110 + i}" for i in range(n)],
                                      pki_dir=a.pki if mtls else None)
            mgmt_bench.base.seed_all()
            sampler = Sampler(ids)
            for w in [int(x) for x in a.workers.split(",")]:
                opw = max(20, a.min_requests // w)
                cell = mgmt_bench.run_cell(w, opw, a.repeats, 20, a.out / f"raw_n{n}_w{w}.csv.gz", sampler)
                cell.update(n_sites=n, transport=a.transport)
                manifest["cells"].append(cell)
                r = cell["repeats"]
                print(f"N={n} W={w}: " + ", ".join(f"{x['requests'] / x['wall_s']:.0f} req/s ok={x['ok']} rej={x['rejected']} "
                                                  f"err={x['error'] + x['timeout'] + x['transport']}" for x in r), flush=True)
                (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
            manifest.setdefault("containers_end", {})[str(n)] = verify(ids)
            down(a.out, n)
    except Exception as exc:  # noqa: BLE001
        manifest["fatal"] = f"{type(exc).__name__}: {exc}"
        print("FATAL", manifest["fatal"], flush=True)
    finally:
        manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        for n in [int(x) for x in a.sites.split(",")]:
            if (a.out / f"compose_n{n}.yml").exists():
                down(a.out, n)
    return 0 if "fatal" not in manifest else 2


if __name__ == "__main__":
    raise SystemExit(main())
