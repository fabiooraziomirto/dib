"""Test of launch_auto_block.sh with a FAKE python (HOME points to a temp dir): it passes the arguments through, refuses a second launch while the
first one is alive, and refuses a missing hashes file. Nothing real is started."""
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def setup(tmp_path):
    home = tmp_path / "home"
    (home / "dib_tnsm/venv/bin").mkdir(parents=True)
    py = home / "dib_tnsm/venv/bin/python"
    py.write_text('#!/usr/bin/env bash\necho "$@" > "$HOME/args.txt"\nsleep 5\n')
    py.chmod(0o755)
    tree = tmp_path / "tree"
    tree.mkdir()
    h = tmp_path / "hashes.txt"
    h.write_text("0" * 64 + "  x\n")
    return home, tree, h


def run(home, *args):
    return subprocess.run(["bash", str(HERE / "launch_auto_block.sh"), *map(str, args)], env={**os.environ, "HOME": str(home)}, capture_output=True, text=True, timeout=30)


def test_launcher(tmp_path):
    home, tree, h = setup(tmp_path)
    out = tmp_path / "out"
    assert run(home, tree, out, "2026-10-14T06:00:00Z", tmp_path / "missing").returncode != 0
    r = run(home, tree, out, "2026-10-14T06:00:00Z", h, "--blocks", "degraded", "--smoke")
    assert r.returncode == 0 and "running" in r.stdout, r.stderr
    time.sleep(0.3)
    args = (home / "args.txt").read_text()
    assert str(tree) + "/experiments_tnsm/m67_retraction/auto_block.py" in args and "--end-utc 2026-10-14T06:00:00Z" in args
    assert f"--hashes {h}" in args and "--blocks degraded --smoke" in args
    r2 = run(home, tree, out, "2026-10-14T06:00:00Z", h)
    assert r2.returncode != 0 and "already running" in r2.stderr
    os.kill(int((out / "auto_block.pid").read_text()), 15)
