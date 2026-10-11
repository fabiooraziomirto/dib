#!/usr/bin/env python3
"""Workstation side of the block data copy (the orchestrator on the node writes DATA.sha256 and does not copy). Run by the supervising
session, each ssh authorised by the user. Steps per block: (1) on the node `sha256sum -c DATA.sha256` (nothing is copied if it fails);
(2) `tar` over ssh, EXCLUDING *.pcap, into <local-dir>/<block> (never overwrites an existing non-empty directory); (3) local sha256 of every file
of DATA.sha256, a missing/different file or any pcap is a failure; (4) COPY_VERIFIED.json with the sha256 of DATA.sha256.
Usage: python3 copy_block.py --host ubuntu@192.168.100.57 --key ~/.ssh/id_ed25519_lab --remote-dir '~/dib_tnsm/out/<run>' --local-dir <dir> --blocks lan_before,degraded"""
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _ssh(ssh_bin, key, host, cmd, **kw):
    return subprocess.run([ssh_bin, "-i", key, host, cmd], capture_output=True, **kw)


def fetch(ssh_bin, key, host, remote_blk: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    src = subprocess.Popen([ssh_bin, "-i", key, host, f"tar -C {remote_blk} -cf - --exclude='*.pcap' ."], stdout=subprocess.PIPE)
    dst = subprocess.run(["tar", "-C", str(dest), "-xf", "-"], stdin=src.stdout, capture_output=True)
    src.stdout.close()
    if src.wait() != 0 or dst.returncode != 0:
        raise RuntimeError(f"tar transfer failed: {dst.stderr.decode(errors='replace')}")


def copy_block(ssh_bin, host, key, remote_dir, local_dir, block) -> dict:
    local_dir, blk = Path(local_dir), Path(local_dir) / block
    remote_blk = shlex.quote(f"{remote_dir}/{block}") if not remote_dir.startswith("~") else f"{remote_dir}/{shlex.quote(block)}"
    res = {"block": block, "ok": False, "error": None}
    if blk.exists() and any(blk.iterdir()):
        res["error"] = f"{blk} exists and is not empty: not overwritten"
        return res
    r = _ssh(ssh_bin, key, host, f"cd {remote_blk} && sha256sum -c DATA.sha256", text=True)
    if r.returncode != 0:
        res["error"] = f"node-side sha256sum -c failed: {(r.stdout + r.stderr).strip()[-500:]}"
        return res
    try:
        fetch(ssh_bin, key, host, remote_blk, blk)
    except RuntimeError as exc:
        res["error"] = str(exc)
        return res
    man = blk / "DATA.sha256"
    bad, n = [], 0
    for line in man.read_text().splitlines():
        if not line.strip():
            continue
        h, rel = line.split("  ", 1)
        n += 1
        f = blk / rel
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
            bad.append(rel)
    pcaps = [str(p.relative_to(blk)) for p in blk.rglob("*.pcap")]
    if bad or pcaps:
        res["error"] = f"local check failed: missing or different {bad}, pcap present {pcaps}"
        return res
    (blk / "COPY_VERIFIED.json").write_text(json.dumps({"block": block, "files": n, "remote_check_ok": True, "local_check_ok": True,
        "manifest_sha256": hashlib.sha256(man.read_bytes()).hexdigest(), "utc": datetime.now(timezone.utc).isoformat()}, indent=1))
    res["ok"] = True
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--remote-dir", required=True)
    ap.add_argument("--local-dir", required=True)
    ap.add_argument("--blocks", required=True)
    ap.add_argument("--ssh", default="ssh")
    a = ap.parse_args(argv)
    rc = 0
    for b in a.blocks.split(","):
        r = copy_block(a.ssh, a.host, a.key, a.remote_dir, a.local_dir, b)
        print(json.dumps(r))
        rc |= 0 if r["ok"] else 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
