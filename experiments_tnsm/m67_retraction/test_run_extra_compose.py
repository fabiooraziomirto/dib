"""run.py can add an extra compose file (docs/audit/85): with DIB_M67_EXTRA_COMPOSE=<path> the compose command carries `-f <path>` after the other files; unset or empty adds nothing.
Used to give the project's containers NET_ADMIN and the host's tc so that a user-space applier can do what the root watcher does (netem on each container's eth0).
Hypotheses (before the change; falsification = any assertion failing): X-1 default: no extra file; X-2 set: `-f <path>` present and AFTER the generated file; X-3 empty string: nothing; X-4 manifest flag via extra_compose().
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


def _c(monkeypatch, tmp_path, v):
    monkeypatch.setenv("HOME", str(tmp_path))
    if v is None:
        monkeypatch.delenv("DIB_M67_EXTRA_COMPOSE", raising=False)
    else:
        monkeypatch.setenv("DIB_M67_EXTRA_COMPOSE", v)
    return r.Env("/tmp/tree", "C", 10, 5.0, "/tmp/pki").compose()


def test_x1_default(monkeypatch, tmp_path):
    assert "extra" not in _c(monkeypatch, tmp_path, None) and _c(monkeypatch, tmp_path, None).count(" -f ") == 1


def test_x2_set(monkeypatch, tmp_path):
    c = _c(monkeypatch, tmp_path, "/x/extra_netadmin.yml")
    assert c.count(" -f ") == 2 and c.index("-f /x/extra_netadmin.yml") > c.index("gen_C_f10_T5.yml")


def test_x3_empty(monkeypatch, tmp_path):
    assert _c(monkeypatch, tmp_path, "").count(" -f ") == 1


def test_x4_flag(monkeypatch):
    monkeypatch.setenv("DIB_M67_EXTRA_COMPOSE", "/a.yml")
    assert r.extra_compose() == "/a.yml"
    monkeypatch.delenv("DIB_M67_EXTRA_COMPOSE")
    assert r.extra_compose() is None
