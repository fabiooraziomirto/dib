#!/usr/bin/env python3
"""M8: cost of signing and verifying exported MUD files with `openssl cms` (audit 55; hypothesis H-M8 and decision rules are there, committed before this code).
Stdlib only on the node (python3 >= 3.10); `make_mud_files` needs the repo's code/src and is run LOCALLY (files copied to the node).
Usage:
  local:  PYTHONPATH=code/src python3 experiments_tnsm/m8_mud_sig/run.py make-files --out <dir>
  node :  python3 run.py measure --files <dir> --out <dir> [--reps 10 --pairs 20 --warmup 5 --seed 20261011]
Nothing here interprets a result beyond the registered verdict."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SIZES = (5, 20, 100)
ALGS = ("ecdsa-p256", "rsa-2048")
SEED = 20261011
RES = 10000
LIMIT_MS = 10.0
OPENSSL = "openssl"


# ---- files ------------------------------------------------------------------------------------------------------------
def make_mud_files(out: Path, sizes=SIZES) -> dict:
    """MUD files from the production exporter on synthetic EndpointScore (FQDN, https/443, eligible class). Deterministic once `last-update` is fixed (declared)."""
    from dib.evaluation.dib import EndpointScore
    from dib.evaluation.mud_export import export_mud_file
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for n in sizes:
        scores = [EndpointScore(device_type="cam-a", endpoint=f"svc{i:03d}.vendor.example", protocol="https", port=443, site_confidence=1.0,
                                temporal_confidence=1.0, graph_confidence=0.0, score=1.0, accepted=True, supporting_sites=2, eligible_sites=2,
                                endpoint_class="vendor-cloud") for i in range(n)]
        res = export_mud_file("cam-a", scores, mud_url="https://dib.example.org/.well-known/mud/cam-a")
        assert res.exported_ace_count == n
        res.document["ietf-mud:mud"]["last-update"] = "2026-01-01T00:00:00+00:00"   # the exporter stamps the current time: fixed so that the bytes (and sha256) are reproducible
        p = out / f"mud_n{n:03d}.json"
        p.write_text(json.dumps(res.document, indent=1, sort_keys=True))
        paths[n] = p
    return paths


# ---- commands ---------------------------------------------------------------------------------------------------------
def sign_cmd(f, cert, key, sig) -> list[str]:
    return [OPENSSL, "cms", "-sign", "-binary", "-in", str(f), "-signer", str(cert), "-inkey", str(key), "-md", "sha256", "-outform", "DER", "-out", str(sig)]


def verify_cmd(f, sig, cert) -> list[str]:
    return [OPENSSL, "cms", "-verify", "-binary", "-inform", "DER", "-in", str(sig), "-content", str(f), "-CAfile", str(cert), "-purpose", "any",
            "-no_check_time", "-out", os.devnull]


def run_ok(cmd) -> bool:
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def make_keypair(d: Path, alg: str):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    key, cert = d / f"{alg}.key", d / f"{alg}.pem"
    gen = ["genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256"] if alg == "ecdsa-p256" else ["genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048"]
    subprocess.run([OPENSSL, *gen, "-out", str(key)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([OPENSSL, "req", "-x509", "-new", "-key", str(key), "-subj", "/CN=dib-m8", "-days", "2", "-out", str(cert),
                    "-addext", "keyUsage=digitalSignature", "-addext", "basicConstraints=CA:FALSE"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return key, cert


# ---- statistics -------------------------------------------------------------------------------------------------------
def p95(xs) -> float:
    s = sorted(xs)
    return s[math.ceil(0.95 * len(s)) - 1]


def boot_ci(xs, stat, rng, res=RES):
    vals = sorted(stat(rng.choices(xs, k=len(xs))) for _ in range(res))
    return vals[int(0.025 * res)], vals[int(0.975 * res) - 1]


def verdict(p95_ms: float, lo: float, hi: float) -> str:
    if lo > LIMIT_MS:
        return "falsified"
    return "inconclusive" if p95_ms > LIMIT_MS else "not falsified"


def global_verdict(verdicts: list[str]) -> dict:
    k = sum(1 for v in verdicts if v == "falsified")
    return {"verdict": "falsified" if k else "not falsified", "k": (k, len(verdicts))}


def cell_order(cells: list, seed: int) -> list:
    out = list(cells)
    random.Random(seed).shuffle(out)
    return out


# ---- measurement ------------------------------------------------------------------------------------------------------
def _t(cmd) -> tuple[float, bool]:
    t0 = time.perf_counter()
    ok = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    return 1000 * (time.perf_counter() - t0), ok


def run_cell(f, key, cert, work, reps=10, pairs=20, warmup=5) -> dict:
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    sig = work / "sig.der"
    out = {"pair_ms": [], "sign_ms": [], "verify_ms": [], "spawn_ms": [], "all_verified": True}
    for _ in range(reps):
        for _w in range(warmup):
            _t(sign_cmd(f, cert, key, sig))
            _t(verify_cmd(f, sig, cert))
        for _p in range(pairs):
            ts, ok1 = _t(sign_cmd(f, cert, key, sig))
            tv, ok2 = _t(verify_cmd(f, sig, cert))
            tn, _ = _t([OPENSSL, "version"])
            out["pair_ms"].append(ts + tv)
            out["sign_ms"].append(ts)
            out["verify_ms"].append(tv)
            out["spawn_ms"].append(tn)
            out["all_verified"] &= ok1 and ok2
    out["sig_bytes"] = sig.stat().st_size
    bad = work / "tampered"
    data = bytearray(Path(f).read_bytes())
    data[len(data) // 2] ^= 0x01
    bad.write_bytes(bytes(data))
    out["negative_control_ok"] = all(not run_ok(verify_cmd(bad, sig, cert)) for _ in range(5))
    return out


def _loadavg() -> dict:
    steal = None
    try:
        v = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
        steal = {"steal": v[7], "total": sum(v)}
    except (OSError, ValueError, IndexError):
        pass
    try:
        la = Path("/proc/loadavg").read_text().split()[:3]
    except OSError:
        la = None
    return {"loadavg": la, "cpu": steal, "utc": time.strftime("%FT%TZ", time.gmtime())}


def measure(files_dir: Path, out: Path, reps: int, pairs: int, warmup: int, seed: int) -> dict:
    files_dir, out = Path(files_dir), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = {n: files_dir / f"mud_n{n:03d}.json" for n in SIZES}
    assert all(p.is_file() for p in files.values()), "mud files missing: run make-files first and copy them"
    before = _loadavg()
    cells = [(alg, n) for alg in ALGS for n in SIZES]
    work = Path(tempfile.mkdtemp(prefix="m8_"))
    try:
        keys = {alg: make_keypair(work / "keys", alg) for alg in ALGS}
        acc = {c: {"pair_ms": [], "sign_ms": [], "verify_ms": [], "spawn_ms": [], "all_verified": True, "negative_control_ok": True} for c in cells}
        for rep in range(reps):
            for alg, n in cell_order(cells, seed + rep):
                r = run_cell(files[n], *keys[alg], work / f"{alg}_{n}", reps=1, pairs=pairs, warmup=warmup)
                a = acc[(alg, n)]
                for k in ("pair_ms", "sign_ms", "verify_ms", "spawn_ms"):
                    a[k] += r[k]
                a["all_verified"] &= r["all_verified"]
                a["negative_control_ok"] &= r["negative_control_ok"]
                a["sig_bytes"] = r["sig_bytes"]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    after = _loadavg()
    rng = random.Random(seed)
    rows, verdicts = [], []
    for (alg, n), a in acc.items():
        x = a["pair_ms"]
        p, lo_hi = p95(x), boot_ci(x, p95, rng)
        med, med_ci = statistics.median(x), boot_ci(x, statistics.median, rng)
        valid = a["all_verified"] and a["negative_control_ok"]
        v = verdict(p, *lo_hi) if valid else "cell invalid (validity control failed)"
        verdicts.append(v if valid else "invalid")
        rows.append({"alg": alg, "n_ace": n, "n_pairs": len(x), "valid": valid, "median_ms": med, "median_ci": med_ci, "p95_ms": p, "p95_ci": lo_hi,
                     "sign_median_ms": statistics.median(a["sign_ms"]), "verify_median_ms": statistics.median(a["verify_ms"]),
                     "spawn_median_ms": statistics.median(a["spawn_ms"]), "spawn_p95_ms": p95(a["spawn_ms"]), "sig_bytes": a["sig_bytes"], "verdict_H_M8": v})
    res = {"cells": rows, "global": global_verdict([v for v in verdicts if v != "invalid"]), "n_invalid": verdicts.count("invalid")}
    (out / "aggregates.json").write_text(json.dumps(res, indent=1))
    (out / "manifest.json").write_text(json.dumps({
        "argv": sys.argv, "python": sys.version, "platform": platform.platform(), "host": platform.node(),
        "cpu": next((l.split(":", 1)[1].strip() for l in Path("/proc/cpuinfo").read_text().splitlines() if l.startswith("model name")), None) if Path("/proc/cpuinfo").exists() else None,
        "openssl": subprocess.run([OPENSSL, "version"], capture_output=True, text=True).stdout.strip(), "seed": seed, "reps": reps, "pairs_per_rep": pairs, "warmup": warmup,
        "limit_ms": LIMIT_MS, "load_before": before, "load_after": after, "audit": "docs/audit/55_prereg_M8_firma_mud.md",
        "sha256_files": {str(p.name): hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()},
        "sha256_run_py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=1))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make-files")
    m.add_argument("--out", required=True)
    s = sub.add_parser("measure")
    s.add_argument("--files", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--reps", type=int, default=10)
    s.add_argument("--pairs", type=int, default=20)
    s.add_argument("--warmup", type=int, default=5)
    s.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args(argv)
    if a.cmd == "make-files":
        for n, p in make_mud_files(Path(a.out)).items():
            print(n, p, hashlib.sha256(p.read_bytes()).hexdigest())
        return 0
    res = measure(Path(a.files), Path(a.out), a.reps, a.pairs, a.warmup, a.seed)
    print(json.dumps(res["global"]), "invalid cells:", res["n_invalid"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
