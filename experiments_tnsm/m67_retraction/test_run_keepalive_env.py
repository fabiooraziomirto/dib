"""run.py passes the opt-in persistent-connection variables to the generated compose only when DIB_M67_KEEPALIVE=1 is set in the DRIVER's environment
(docs/audit/62; so auto_block.py / auto_b2k.py / calib need no change). Hypotheses (before the change; falsification = any assertion failing):
 E-1  default: the compose command carries neither DIB_DIST_FANOUT_KEEPALIVE nor DIB_DIST_FANOUT_WARM_INTERVAL;
 E-2  DIB_M67_KEEPALIVE=1: both appear, KEEPALIVE=1 and WARM_INTERVAL=2, in the env prefix that feeds generate_compose.py;
 E-3  any other value of DIB_M67_KEEPALIVE (0, empty, 'yes') leaves them out;
 E-4  the manifest field is built by keepalive_enabled(): True only for '1'.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


def _compose(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("DIB_M67_KEEPALIVE", raising=False)
    else:
        monkeypatch.setenv("DIB_M67_KEEPALIVE", value)
    return r.Env("/tmp/tree", "D", 10, 5.0, "/tmp/pki").compose()


def test_e1_default(monkeypatch):
    c = _compose(monkeypatch, None)
    assert "KEEPALIVE" not in c and "WARM_INTERVAL" not in c


def test_e2_on(monkeypatch):
    c = _compose(monkeypatch, "1")
    assert "DIB_DIST_FANOUT_KEEPALIVE=1" in c and "DIB_DIST_FANOUT_WARM_INTERVAL=2" in c
    assert c.index("DIB_DIST_FANOUT_KEEPALIVE=1") < c.index("python3 generate_compose.py")


@pytest.mark.parametrize("v", ["0", "", "yes"])
def test_e3_other_values(monkeypatch, v):
    c = _compose(monkeypatch, v)
    assert "KEEPALIVE" not in c


def test_e4_flag(monkeypatch):
    monkeypatch.setenv("DIB_M67_KEEPALIVE", "1")
    assert r.keepalive_enabled() is True
    monkeypatch.setenv("DIB_M67_KEEPALIVE", "true")
    assert r.keepalive_enabled() is False
    monkeypatch.delenv("DIB_M67_KEEPALIVE")
    assert r.keepalive_enabled() is False
