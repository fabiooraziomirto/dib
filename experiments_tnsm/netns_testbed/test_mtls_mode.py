"""mTLS mode of the netns testbed (audit 95). Hypotheses (falsified by any failing assertion):
 T-1  without DIB_TESTBED_MTLS_PKI nothing changes: site_url/EV_URL are http://127.0.0.1:port, _env has no DIB_DIST_MTLS (default path = the validated D arm);
 T-2  with DIB_TESTBED_MTLS_PKI=<dir>: URLs are https://127.0.0.1:port and every service env carries DIB_DIST_MTLS=1, DIB_DIST_IDENTITIES=<dir>/identities.json,
      DIB_DIST_TLS_CA=<dir>/ca.crt and the service's own certificate (evidence.crt/.key for the evidence, site-<i>.crt/.key for site i);
 T-3  the service launcher in mTLS mode is the PRODUCTION entry point (python -m dib.registry.distributed.mtls --host 127.0.0.1 --port <port>), not a custom one;
 T-4  MtlsClient picks the client identity by URL as the node driver does: site URLs -> op-site-<i>, evidence /dispute -> op-site-1, any other evidence URL -> admin;
 T-5  a cell with "fresh": true makes the worker restart sites and evidence (cell_needs_restart helper), others do not.
"""
import importlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load(monkeypatch, pki=None):
    if pki:
        monkeypatch.setenv("DIB_TESTBED_MTLS_PKI", str(pki))
    else:
        monkeypatch.delenv("DIB_TESTBED_MTLS_PKI", raising=False)
    import testbed
    return importlib.reload(testbed)


def test_t1_default_unchanged(monkeypatch, tmp_path):
    tb = load(monkeypatch)
    assert tb.site_url(3) == "http://127.0.0.1:18113" and tb.EV_URL == "http://127.0.0.1:18100"
    e = tb.Cluster(tmp_path)._env("site", 3, False)
    assert "DIB_DIST_MTLS" not in e


def test_t2_env(monkeypatch, tmp_path):
    tb = load(monkeypatch, tmp_path)
    assert tb.site_url(3) == "https://127.0.0.1:18113" and tb.EV_URL == "https://127.0.0.1:18100"
    c = tb.Cluster(tmp_path / "wd")
    es, ee = c._env("site", 3, False), c._env("evidence", 0, False)
    for e, name in ((es, "site-3"), (ee, "evidence")):
        assert e["DIB_DIST_MTLS"] == "1" and e["DIB_DIST_IDENTITIES"] == str(tmp_path / "identities.json")
        assert e["DIB_DIST_TLS_CA"] == str(tmp_path / "ca.crt")
        assert e["DIB_DIST_TLS_CERT"] == str(tmp_path / f"{name}.crt") and e["DIB_DIST_TLS_KEY"] == str(tmp_path / f"{name}.key")
    assert es["DIB_DIST_SITE_URL_2"] == "https://127.0.0.1:18112"
    load(monkeypatch)


def test_t3_launcher_is_production_entry(monkeypatch, tmp_path):
    tb = load(monkeypatch, tmp_path)
    assert tb.launcher_cmd(18113) == [sys.executable, "-m", "dib.registry.distributed.mtls", "--host", "127.0.0.1", "--port", "18113"]
    tb = load(monkeypatch)
    assert tb.launcher_cmd(18113) == [sys.executable, str(HERE / "launch_service.py")]


def test_t4_identity_routing(monkeypatch, tmp_path):
    tb = load(monkeypatch, tmp_path)
    assert tb.identity_for(tb.site_url(7) + "/query") == "op-site-7"
    assert tb.identity_for(tb.EV_URL + "/dispute") == "op-site-1"
    assert tb.identity_for(tb.EV_URL + "/seed") == "admin"
    assert tb.identity_for(tb.EV_URL + "/health") == "admin"
    load(monkeypatch)


def test_t5_fresh_cells(monkeypatch):
    tb = load(monkeypatch)
    assert tb.cell_needs_restart({"fresh": True}) and not tb.cell_needs_restart({}) and not tb.cell_needs_restart({"fresh": False})
