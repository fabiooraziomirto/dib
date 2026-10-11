"""Tests of copy_block.py (workstation side of the block data copy) with a FAKE ssh that runs the remote command locally. Hypotheses (declared
first): C-1 the data are verified on the node (`sha256sum -c DATA.sha256`) BEFORE the copy and locally AFTER it against the same manifest;
C-2 *.pcap never reach the workstation (and a pcap found locally is a failure); C-3 a corrupted, missing or truncated file fails the copy with the
file name; C-4 a failed remote check copies nothing; C-5 an existing non-empty local block directory is never overwritten; C-6 a success writes
COPY_VERIFIED.json with the sha256 of DATA.sha256. Falsification: any assertion failing."""
import hashlib
import json
import os
import stat
from pathlib import Path

import pytest

import copy_block as cb

FAKE_SSH = '#!/usr/bin/env bash\nwhile [[ $1 == -* ]]; do if [[ $1 == -i || $1 == -o ]]; then shift 2; else shift; fi; done\nshift\nexec bash -c "$1"\n'


def sha(b): return hashlib.sha256(b).hexdigest()


def make_remote(tmp_path, files=None, pcap=True):
    remote = tmp_path / "node/out"
    blk = remote / "degraded"
    files = files or {"b1_D_f1/cells.jsonl": b"cells\n", "manifest.json": b"{}\n", "calib/x.json": b"x"}
    lines = []
    for rel, data in files.items():
        p = blk / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        lines.append(f"{sha(data)}  {rel}")
    (blk / "DATA.sha256").write_text("\n".join(lines) + "\n")
    if pcap:
        (blk / "cap.pcap").write_bytes(b"secret")
    return remote


@pytest.fixture
def ssh(tmp_path):
    f = tmp_path / "ssh"
    f.write_text(FAKE_SSH)
    f.chmod(0o755)
    return str(f)


def run(tmp_path, ssh, remote, **kw):
    return cb.copy_block(ssh_bin=ssh, host="u@h", key="k", remote_dir=str(remote), local_dir=tmp_path / "local", block="degraded", **kw)


def test_c1_c2_c6_good_copy(tmp_path, ssh):
    remote = make_remote(tmp_path)
    r = run(tmp_path, ssh, remote)
    loc = tmp_path / "local/degraded"
    assert r["ok"] and (loc / "b1_D_f1/cells.jsonl").read_bytes() == b"cells\n"
    assert not list(loc.rglob("*.pcap"))
    v = json.loads((loc / "COPY_VERIFIED.json").read_text())
    assert v["files"] == 3 and v["remote_check_ok"] and v["manifest_sha256"] == sha((loc / "DATA.sha256").read_bytes())


def test_c3_corruption_is_named(tmp_path, ssh):
    remote = make_remote(tmp_path)
    (remote / "degraded/manifest.json").write_bytes(b"CHANGED")           # changed on the node after the manifest: node check fails first
    r = run(tmp_path, ssh, remote)
    assert not r["ok"] and "manifest.json" in r["error"] and not (tmp_path / "local/degraded").exists()    # C-4: nothing copied


def test_c3_local_mismatch_after_copy(tmp_path, ssh, monkeypatch):
    remote = make_remote(tmp_path)
    orig = cb.fetch

    def corrupt(*a, **k):
        orig(*a, **k)
        (tmp_path / "local/degraded/calib/x.json").write_bytes(b"y")        # damaged in transit
    monkeypatch.setattr(cb, "fetch", corrupt)
    r = run(tmp_path, ssh, remote)
    assert not r["ok"] and "calib/x.json" in r["error"] and not (tmp_path / "local/degraded/COPY_VERIFIED.json").exists()


def test_c3_missing_file(tmp_path, ssh, monkeypatch):
    remote = make_remote(tmp_path)
    orig = cb.fetch
    monkeypatch.setattr(cb, "fetch", lambda *a, **k: (orig(*a, **k), (tmp_path / "local/degraded/manifest.json").unlink()))
    r = run(tmp_path, ssh, remote)
    assert not r["ok"] and "manifest.json" in r["error"]


def test_c2_pcap_found_locally_fails(tmp_path, ssh, monkeypatch):
    remote = make_remote(tmp_path)
    orig = cb.fetch
    monkeypatch.setattr(cb, "fetch", lambda *a, **k: (orig(*a, **k), (tmp_path / "local/degraded/z.pcap").write_bytes(b"p")))
    assert not run(tmp_path, ssh, remote)["ok"]


def test_c5_never_overwrites(tmp_path, ssh):
    remote = make_remote(tmp_path)
    (tmp_path / "local/degraded").mkdir(parents=True)
    (tmp_path / "local/degraded/old").write_text("keep")
    r = run(tmp_path, ssh, remote)
    assert not r["ok"] and "exists" in r["error"] and (tmp_path / "local/degraded/old").read_text() == "keep"


def test_c4_missing_manifest_on_node(tmp_path, ssh):
    remote = make_remote(tmp_path)
    (remote / "degraded/DATA.sha256").unlink()
    assert not run(tmp_path, ssh, remote)["ok"]
