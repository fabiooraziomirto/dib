"""run.py can remove the node's DNS search domains from the cluster (docs/audit/72): with DIB_M67_DNS_NOSEARCH=1 in the driver's environment the compose command adds an
override file with `dns_search: .` for every service. Why: on the node resolv.conf has `search tail18eba5.ts.net proxmox`; the vanished name of a killed site is expanded with
those domains and forwarded upstream, so bursts of calls stall for 1-8 s (diag_dns_burst.py: 2000 resolutions 401.5 s; with `dns_search: .` 1.7 s).
Hypotheses (before the change; falsification = any assertion failing):
 N-1  default: no extra -f file and no dns_search anywhere;
 N-2  DIB_M67_DNS_NOSEARCH=1: the compose command carries `-f <override>` and the override lists dns_search `.` for evidence and site-0..site-9 and nothing else;
 N-3  any other value leaves it off; the manifest flag uses dns_nosearch_enabled() (True only for '1');
 N-4  the override file is written by Env.compose() itself (no other step needed) and is idempotent.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


def _env(monkeypatch, tmp_path, value):
    monkeypatch.setenv("HOME", str(tmp_path))
    if value is None:
        monkeypatch.delenv("DIB_M67_DNS_NOSEARCH", raising=False)
    else:
        monkeypatch.setenv("DIB_M67_DNS_NOSEARCH", value)
    return r.Env("/tmp/tree", "C", 10, 5.0, "/tmp/pki")


def test_n1_default(monkeypatch, tmp_path):
    c = _env(monkeypatch, tmp_path, None).compose()
    assert "dns_nosearch" not in c and "dns_search" not in c


def test_n2_on(monkeypatch, tmp_path):
    e = _env(monkeypatch, tmp_path, "1")
    c = e.compose()
    ov = tmp_path / "dib_tnsm" / "m67" / "dns_nosearch.yml"
    assert f"-f {ov}" in c and ov.is_file()
    text = ov.read_text()
    for name in ["evidence"] + [f"site-{i}" for i in range(10)]:
        assert f"  {name}:\n    dns_search: .\n" in text
    assert text.count("dns_search") == 11


@pytest.mark.parametrize("v", ["0", "", "true"])
def test_n3_other_values(monkeypatch, tmp_path, v):
    assert "dns_nosearch" not in _env(monkeypatch, tmp_path, v).compose()


def test_n3_flag(monkeypatch):
    monkeypatch.setenv("DIB_M67_DNS_NOSEARCH", "1")
    assert r.dns_nosearch_enabled() is True
    monkeypatch.setenv("DIB_M67_DNS_NOSEARCH", "yes")
    assert r.dns_nosearch_enabled() is False
    monkeypatch.delenv("DIB_M67_DNS_NOSEARCH")
    assert r.dns_nosearch_enabled() is False


def test_n4_idempotent(monkeypatch, tmp_path):
    e = _env(monkeypatch, tmp_path, "1")
    a = e.compose()
    b = e.compose()
    assert a == b
