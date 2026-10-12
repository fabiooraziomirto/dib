#!/usr/bin/env python3
"""Netns testbed (audit 75): the REAL service.py (evidence + 10 sites, plain HTTP, FANOUT_CONCURRENCY=10) inside a private network namespace with netem on `lo`.
Timing is measured out of band: the instant the evidence DB row of the fact becomes `disputed` (t0) and the instants the 10 site DB rows become `disputed`
(read-only SQLite polling every 5 ms), so the emulated network never touches the measurement. The driver uses 127.0.0.2, exempt from netem (analysis.netem_cmds).
Usage:  python3 testbed.py launch --out DIR [--workers 4] [--episodes 60]      (spawns `unshare -n ... worker` processes)
        python3 testbed.py smoke                                                (one lossless cell, 5 episodes: T-0 check)"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import platform
import random
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analysis as an  # noqa: E402

REPO = HERE.parents[1]
SVC_DIR = REPO / "code" / "src" / "dib" / "registry" / "distributed"
N = 10
EV_PORT, SITE_PORT0 = 18100, 18110
HOST, DRIVER_IP = "127.0.0.1", "127.0.0.2"
EV_URL = f"http://{HOST}:{EV_PORT}"
SEED = 20261012


def site_url(i: int) -> str:
    return f"http://{HOST}:{SITE_PORT0 + i}"


def tc(cmds: list[list[str]]) -> None:
    for c in cmds:
        subprocess.run(c, check=True, capture_output=True)


class Cluster:
    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.procs: dict[str, subprocess.Popen] = {}
        atexit.register(self.stop_all)

    def _env(self, role: str, idx: int, keepalive: bool) -> dict:
        e = dict(os.environ)
        e["PYTHONPATH"] = str(REPO / "code" / "src") + os.pathsep + e.get("PYTHONPATH", "")
        e.update({"DIB_DIST_ROLE": role, "DIB_DIST_N_SITES": str(N), "DIB_DIST_SITE_INDEX": str(idx), "DIB_DIST_EVIDENCE_URL": EV_URL,
                  "DIB_DIST_DATA_DIR": str(self.workdir / (f"site{idx}" if role == "site" else "evidence")),
                  "DIB_DIST_RECONCILE_INTERVAL": "5", "DIB_DIST_RECONCILE_JITTER": "0.5", "DIB_DIST_RECONCILE_TIMEOUT": "5.0"})
        for i in range(N):
            e[f"DIB_DIST_SITE_URL_{i}"] = site_url(i)
        if role == "evidence":
            e["DIB_DIST_FANOUT_CONCURRENCY"] = str(getattr(self, "concurrency", 10))
            if keepalive:
                e["DIB_DIST_FANOUT_KEEPALIVE"] = "1"
                e["DIB_DIST_FANOUT_WARM_INTERVAL"] = "2"
        return e

    def _start(self, name: str, role: str, idx: int, port: int, keepalive: bool) -> None:
        (self.workdir / (f"site{idx}" if role == "site" else "evidence")).mkdir(parents=True, exist_ok=True)
        log = open(self.workdir / f"{name}.log", "ab")
        env = self._env(role, idx, keepalive)
        env["DIB_TESTBED_PORT"] = str(port)
        env["PYTHONPATH"] = str(SVC_DIR) + os.pathsep + env["PYTHONPATH"]
        self.procs[name] = subprocess.Popen([sys.executable, str(HERE / "launch_service.py")], env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL)

    def start_sites(self) -> None:
        for i in range(N):
            self._start(f"site{i}", "site", i, SITE_PORT0 + i, False)

    def start_evidence(self, keepalive: bool, concurrency: int = 10) -> None:
        self.concurrency = concurrency
        self._start("evidence", "evidence", 0, EV_PORT, keepalive)

    def stop(self, name: str) -> None:
        p = self.procs.pop(name, None)
        if p is not None:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()

    def stop_all(self) -> None:
        for n in list(self.procs):
            self.stop(n)

    def wait_healthy(self, client: httpx.Client, timeout: float = 60.0) -> None:
        t0 = time.time()
        urls = [EV_URL] + [site_url(i) for i in range(N)]
        while True:
            ok = 0
            for u in urls:
                try:
                    ok += client.get(u + "/health", timeout=2.0).status_code == 200
                except httpx.HTTPError:
                    pass
            if ok == len(urls):
                return
            if time.time() - t0 > timeout:
                raise RuntimeError(f"cluster not healthy: {ok}/{len(urls)}")
            time.sleep(0.5)


def ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1.0)


def run_episode(cl: Cluster, client: httpx.Client, tag: str, k: int, max_wait: float = 30.0) -> dict:
    out = {"episode": k, "setup_ok": False, "applies": {}, "t0": None}
    ep = f"{tag}-{k}.example"
    body = {"device_type": "cam-a", "endpoint": ep}
    try:
        sid = client.post(EV_URL + "/seed", json=body, timeout=30).json()["id"]
    except Exception:  # noqa: BLE001
        return out

    def setup(i: int) -> bool:
        for _ in range(4):
            try:
                a = client.post(site_url(i) + "/query", json=body, timeout=30)
                b = client.post(site_url(i) + "/commit", json=body, timeout=30)
                if a.status_code == 200 and b.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass
        return False
    with ThreadPoolExecutor(N) as ex:
        if not all(ex.map(setup, range(N))):
            return out
    out["setup_ok"] = True
    stop = threading.Event()
    state = {"t0": None, "applied": {}}
    evdb = ro(cl.workdir / "evidence" / "evidence.db")          # main thread: used only for the final drain wait

    def poll():
        pev = ro(cl.workdir / "evidence" / "evidence.db")        # SQLite connections must be created in the thread that uses them
        sdbs = [ro(cl.workdir / f"site{i}" / "site.db") for i in range(N)]
        while not stop.is_set():
            try:
                state["n_polls"] = state.get("n_polls", 0) + 1
                if state["t0"] is None:
                    r = pev.execute("SELECT status FROM scores WHERE id=?", (sid,)).fetchone()
                    if r and r[0] == "disputed":
                        state["t0"] = time.time()
                for i, c in enumerate(sdbs):
                    if i not in state["applied"]:
                        r = c.execute("SELECT state FROM local_decisions WHERE score_id=?", (sid,)).fetchone()
                        if r and r[0] == "disputed":
                            state["applied"][i] = time.time()
            except Exception as exc:  # noqa: BLE001 -- a failing poller must be visible, not silent
                state["poll_error"] = repr(exc)[:100]
            time.sleep(0.005)
        for c in sdbs + [pev]:
            c.close()
    th = threading.Thread(target=poll, daemon=True)
    th.start()
    res = {}

    def dispute():
        try:
            res["r"] = client.post(EV_URL + "/dispute", json={**body, "site_id": "site-1"}, timeout=120).status_code
        except Exception as exc:  # noqa: BLE001
            res["err"] = repr(exc)[:80]
    dt = threading.Thread(target=dispute)
    t_send = time.time()
    dt.start()
    while True:
        if len(state["applied"]) == N:
            break
        if state["t0"] is not None and time.time() - state["t0"] > max_wait:
            break
        if time.time() - t_send > max_wait + 100:
            break
        time.sleep(0.01)
    stop.set()
    th.join(timeout=2)
    dt.join(timeout=10)
    t0 = state["t0"]
    out["t0"] = t0
    out["dispute"] = res
    out["applies"] = {str(i): (max(0.0, state["applied"][i] - t0) if (i in state["applied"] and t0) else None) for i in range(N)}
    # drain pending rows of this fact before the next episode
    t_d = time.time()
    while time.time() - t_d < 25:
        try:
            if evdb.execute("SELECT count(*) FROM pending_fanout WHERE score_id=?", (sid,)).fetchone()[0] == 0:
                break
        except sqlite3.Error:
            pass
        time.sleep(0.25)
    evdb.close()
    out["poll_debug"] = {k: state.get(k) for k in ("n_polls", "poll_error")}
    return out


def worker(cells: list[dict], episodes: int, warmup: int, out_path: Path, workdir: Path) -> None:
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True)
    cl = Cluster(workdir)
    client = httpx.Client(transport=httpx.HTTPTransport(local_address=DRIVER_IP), timeout=30)
    first = cells[0]
    tc(an.netem_cmds(first["d_ms"], first["loss_pct"], initial=True))
    cl.start_sites()
    current_policy = None
    fh = out_path.open("a")
    try:
        for ci, cell in enumerate(cells):
            warm = cell["policy"] == "P1"
            tc(an.netem_cmds(cell["d_ms"], cell["loss_pct"], initial=False))
            if current_policy != cell["policy"]:
                cl.stop("evidence")
                cl.start_evidence(warm, concurrency=1 if cell["policy"] == "S1" else 10)
                current_policy = cell["policy"]
                cl.wait_healthy(client)
                time.sleep(8 if warm else 3)       # let the warmers open their connections
            n_ep = cell.get("episodes", episodes)
            tag = f"c{ci}-{cell['d_ms']}-{cell['loss_pct']}-{cell['policy']}"
            for k in range(-warmup, n_ep):
                e = run_episode(cl, client, tag, k, max_wait=cell.get("max_wait_s", 30.0))
                if k < 0:
                    continue
                fh.write(json.dumps({"cell": cell, **e}) + "\n")
                fh.flush()
    finally:
        cl.stop_all()
        fh.close()


def build_cells(episodes: int, seed: int) -> list[dict]:
    cells = []
    for d in (50, 100, 200):
        for pol in ("P0", "P1"):
            cells.append({"d_ms": d, "loss_pct": 0, "policy": pol, "episodes": 20, "kind": "T0"})
            for p in (2, 5, 10):
                cells.append({"d_ms": d, "loss_pct": p, "policy": pol, "episodes": episodes, "kind": "grid"})
    random.Random(seed).shuffle(cells)
    return cells


def build_cells_s1(episodes: int) -> list[dict]:
    """Audit 77: sequential fan-out (DIB_DIST_FANOUT_CONCURRENCY=1) on the 9 conditions; long episodes need a longer wait cap."""
    return [{"d_ms": d, "loss_pct": p, "policy": "S1", "episodes": episodes, "kind": "s1", "max_wait_s": 120} for d in (50, 100, 200) for p in (2, 5, 10)]


def build_cells_v3() -> list[dict]:
    """Audit 78: confirmatory conditions NOT used to build or check the model: 75/150 ms x 3/7 % loss, P0 (parallel) and S1 (sequential), plus P0 at p = 0 for validity."""
    cells = [{"d_ms": d, "loss_pct": 0, "policy": "P0", "episodes": 20, "kind": "T0"} for d in (75, 150)]
    cells += [{"d_ms": d, "loss_pct": p, "policy": "P0", "episodes": 60, "kind": "v3"} for d in (75, 150) for p in (3, 7)]
    cells += [{"d_ms": d, "loss_pct": p, "policy": "S1", "episodes": 40, "kind": "v3", "max_wait_s": 120} for d in (75, 150) for p in (3, 7)]
    return cells


def launch(out_dir: Path, workers: int, episodes: int, suite: str = "grid") -> None:
    avail = int([l for l in open("/proc/meminfo") if l.startswith("MemAvailable")][0].split()[1]) / 1e6
    if avail < 16:
        raise SystemExit(f"refusing to start: MemAvailable {avail:.1f} GB < 16 GB")
    out_dir.mkdir(parents=True, exist_ok=True)
    cells = build_cells(episodes, SEED) if suite == "grid" else (build_cells_s1(episodes) if suite == "s1" else build_cells_v3())
    random.Random(SEED).shuffle(cells)
    parts = [cells[i::workers] for i in range(workers)]
    procs = []
    for i, part in enumerate(parts):
        # within a worker order cells so that the policy changes as rarely as possible (evidence restarts), keeping the shuffled order between workers
        part.sort(key=lambda c: c["policy"])
        wd = Path(tempfile.mkdtemp(prefix=f"nsbed{i}_"))
        spec = out_dir / f"worker{i}_cells.json"
        spec.write_text(json.dumps(part))
        procs.append((subprocess.Popen(["unshare", "-n", sys.executable, str(HERE / "testbed.py"), "worker", "--cells", str(spec), "--episodes", str(episodes),
                                        "--out", str(out_dir / f"episodes_{i}.jsonl"), "--workdir", str(wd)], stdout=open(out_dir / f"worker{i}.log", "ab"),
                                       stderr=subprocess.STDOUT), wd))
    for p, wd in procs:
        p.wait()
        shutil.rmtree(wd, ignore_errors=True)
    svc = SVC_DIR / "service.py"
    (out_dir / "manifest.json").write_text(json.dumps({
        "audit": "docs/audit/75_prereg_banco_netns_modello_v2.md (suite grid) / 77 (suite s1)", "suite": suite, "python": sys.version, "kernel": platform.release(), "host": platform.node(), "seed": SEED,
        "workers": workers, "episodes_per_cell": episodes, "cells": cells, "service_py_sha256": hashlib.sha256(svc.read_bytes()).hexdigest(),
        "testbed_py_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "finished_utc": time.strftime("%FT%TZ", time.gmtime())}, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("launch")
    l.add_argument("--out", required=True)
    l.add_argument("--workers", type=int, default=4)
    l.add_argument("--episodes", type=int, default=60)
    l.add_argument("--suite", choices=("grid", "s1", "v3"), default="grid")
    w = sub.add_parser("worker")
    w.add_argument("--cells", required=True)
    w.add_argument("--episodes", type=int, default=60)
    w.add_argument("--out", required=True)
    w.add_argument("--workdir", required=True)
    w.add_argument("--warmup", type=int, default=3)
    sub.add_parser("smoke")
    a = ap.parse_args()
    if a.cmd == "launch":
        launch(Path(a.out), a.workers, a.episodes, a.suite)
    elif a.cmd == "worker":
        worker(json.loads(Path(a.cells).read_text()), a.episodes, a.warmup, Path(a.out), Path(a.workdir))
    else:
        d = Path(tempfile.mkdtemp(prefix="nsbed_smoke_"))
        spec = d / "cells.json"
        spec.write_text(json.dumps([{"d_ms": 50, "loss_pct": 0, "policy": "P0", "episodes": 5}]))
        subprocess.run(["unshare", "-n", sys.executable, str(HERE / "testbed.py"), "worker", "--cells", str(spec), "--out", str(d / "ep.jsonl"), "--workdir", str(d / "wd"),
                        "--warmup", "1"], check=True)
        eps = [json.loads(l) for l in (d / "ep.jsonl").read_text().splitlines()]
        print(json.dumps(an.t0_valid(eps, 0.1, False)), json.dumps(an.cell_summary(eps, 0.1, False)))
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
