"""In-process harness for dib/registry/distributed/service.py (no Docker, no sockets).

service.py fixes its role (site | evidence), database and URLs at import time from the
environment (service.py:67-74,111,321), so one module object cannot be both. The harness
therefore loads the file once per instance under a unique module name, with that
instance's environment set by monkeypatch and its SQLite database in tmp_path.

The service reaches its peers through the module-level functions ``httpx.get`` and
``httpx.post`` (service.py:137,259,269,362). ``FakeNet`` replaces those two names with a
router that dispatches by host to a ``fastapi.testclient.TestClient`` of the target
instance. Nothing is ever sent over a real network. Production code is never modified:
``source`` may point to a text-modified COPY of service.py (negative controls).
"""
from __future__ import annotations

import importlib.util
import itertools
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

DIST_SOURCE = (
    Path(__file__).resolve().parents[2] / "src" / "dib" / "registry" / "distributed" / "service.py"
)
EVIDENCE_HOST = "evidence.test"
DEFAULT_ENDPOINT = "api.vendor.com"
DEVICE = "camera"
_counter = itertools.count()


@dataclass
class Call:
    method: str
    host: str
    path: str
    json: dict | None
    params: dict | None
    timeout: float | None


@dataclass
class _Hook:
    method: str
    path: str
    fn: object


class FakeNet:
    """Router standing in for httpx.get/httpx.post."""

    MAX_CALLS = 400  # hard cap per test: a runaway loop fails loudly instead of hanging

    def __init__(self) -> None:
        self.clients: dict[str, TestClient] = {}
        self.site_index_by_host: dict[str, int] = {}
        self.down: set[int] = set()  # sites unreachable FROM other instances
        self.fail_next: dict[tuple[int, str], int] = {}  # (site, path) -> failures left
        self.calls: list[Call] = []
        self._hooks: list[_Hook] = []

    def after(self, method: str, path: str, fn) -> None:
        """One-shot hook: runs after the first call (method, exact path) has been answered
        and before its response is returned. It is disarmed BEFORE fn runs, so it can
        never fire twice, not even re-entrantly."""
        self._hooks.append(_Hook(method.upper(), path, fn))

    def calls_to(self, site_index: int, path: str | None = None) -> list[Call]:
        host = f"site{site_index}.test"
        return [c for c in self.calls if c.host == host and (path is None or c.path == path)]

    def _dispatch(self, method: str, url: str, *, json=None, params=None, timeout=None, **_ignored):
        if len(self.calls) >= self.MAX_CALLS:
            raise AssertionError(f"FakeNet call cap ({self.MAX_CALLS}) exceeded: probable runaway loop")
        parts = urlsplit(url)
        self.calls.append(Call(method, parts.netloc, parts.path, json, params, timeout))
        site = self.site_index_by_host.get(parts.netloc)
        request = httpx.Request(method, url)
        if site is not None:
            if site in self.down:
                raise httpx.ConnectError("site unreachable (FakeNet.down)", request=request)
            key = (site, parts.path)
            if self.fail_next.get(key, 0) > 0:
                self.fail_next[key] -= 1
                raise httpx.ConnectError("injected failure (FakeNet.fail_next)", request=request)
        response = self.clients[parts.netloc].request(method, parts.path, params=params, json=json)
        for hook in list(self._hooks):
            if hook.method == method and hook.path == parts.path:
                self._hooks.remove(hook)  # disarm first: one-shot
                hook.fn()
                break
        return response

    def get(self, url, **kw):
        return self._dispatch("GET", url, **kw)

    def post(self, url, **kw):
        return self._dispatch("POST", url, **kw)


class Cluster:
    """One evidence instance plus ``n_sites`` site instances wired through a FakeNet."""

    def __init__(self, tmp_path: Path, monkeypatch, *, n_sites: int = 2, quorum: int = 1,
                 source: Path | None = None) -> None:
        self.tmp_path = tmp_path
        self.monkeypatch = monkeypatch
        self.n_sites = n_sites
        self.source = Path(source) if source else DIST_SOURCE
        self.net = FakeNet()
        self._modules: list = []
        self._names: list[str] = []
        monkeypatch.setattr(httpx, "get", self.net.get)
        monkeypatch.setattr(httpx, "post", self.net.post)
        for i in range(n_sites):
            monkeypatch.setenv(f"DIB_DIST_SITE_URL_{i}", f"http://site{i}.test")
        self.evidence_mod, self.evidence = self._load("evidence", 0, n_sites, quorum)
        self.net.clients[EVIDENCE_HOST] = self.evidence
        self.sites: list[TestClient] = []
        self.site_mods: list = []
        for i in range(n_sites):
            mod, client = self._load("site", i, n_sites, quorum)
            self.sites.append(client)
            self.site_mods.append(mod)
            self.net.clients[f"site{i}.test"] = client
            self.net.site_index_by_host[f"site{i}.test"] = i

    def _load(self, role: str, index: int, n_sites: int, quorum: int):
        mp = self.monkeypatch
        name = f"dib_dist_{role}{index}_{next(_counter)}"
        data_dir = self.tmp_path / f"{role}{index}"
        mp.setenv("DIB_DIST_ROLE", role)
        mp.setenv("DIB_DIST_DATA_DIR", str(data_dir))
        mp.setenv("DIB_DIST_N_SITES", str(n_sites))
        mp.setenv("DIB_DIST_SITE_INDEX", str(index))
        mp.setenv("DIB_DIST_SUSPENSION_QUORUM", str(quorum))
        mp.setenv("DIB_DIST_EVIDENCE_URL", f"http://{EVIDENCE_HOST}")
        spec = importlib.util.spec_from_file_location(name, self.source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        self._names.append(name)
        spec.loader.exec_module(module)
        self._modules.append(module)
        return module, TestClient(module.app)

    def close(self) -> None:
        for module in self._modules:
            for attr in ("_site_db", "_evidence_db"):
                db = getattr(module, attr, None)
                if db is not None:
                    db._con.close()
        for name in self._names:
            sys.modules.pop(name, None)

    # ---- convenience wrappers (all go through the real HTTP handlers) ----
    def seed(self, endpoint: str = DEFAULT_ENDPOINT, device_type: str = DEVICE) -> int:
        r = self.evidence.post("/seed", json={"device_type": device_type, "endpoint": endpoint})
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def _fact(self, endpoint: str, device_type: str = DEVICE) -> dict:
        return {"device_type": device_type, "endpoint": endpoint, "protocol": "https", "port": 443}

    def stage(self, site: int, endpoint: str = DEFAULT_ENDPOINT):
        return self.sites[site].post("/query", json=self._fact(endpoint))

    def commit(self, site: int, endpoint: str = DEFAULT_ENDPOINT):
        return self.sites[site].post("/commit", json=self._fact(endpoint))

    def local_revoke(self, site: int, endpoint: str = DEFAULT_ENDPOINT):
        return self.sites[site].post("/local_revoke", json=self._fact(endpoint))

    def local_restore(self, site: int, endpoint: str = DEFAULT_ENDPOINT):
        return self.sites[site].post("/local_restore", json=self._fact(endpoint))

    def dispute(self, reporter: str, endpoint: str = DEFAULT_ENDPOINT):
        return self.evidence.post("/dispute", json={**self._fact(endpoint), "site_id": reporter})

    def restore(self, endpoint: str = DEFAULT_ENDPOINT):
        return self.evidence.post("/restore", json=self._fact(endpoint))

    def reconcile(self, site: int):
        return self.sites[site].post("/reconcile")

    def pending(self, site: int) -> list[dict]:
        return self.evidence.get(f"/pending/site-{site}").json()["pending"]

    def evidence_score(self, endpoint: str = DEFAULT_ENDPOINT, device_type: str = DEVICE) -> dict:
        r = self.evidence.get("/scores", params=self._fact(endpoint, device_type))
        assert r.status_code == 200, r.text
        return r.json()

    def state(self, site: int, score_id: int) -> dict | None:
        r = self.sites[site].get(f"/state/{score_id}")
        return None if r.status_code == 404 else r.json()

    def ace_count(self, site: int, device_type: str = DEVICE) -> int:
        doc = self.sites[site].get("/export_mud", params={"device_type": device_type}).json()
        acls = doc["ietf-access-control-list:access-lists"]["acl"]
        return len(acls[0]["aces"]["ace"])


@pytest.fixture
def make_cluster(tmp_path, monkeypatch):
    """Factory fixture: make_cluster(n_sites=..., quorum=..., source=...) -> Cluster."""
    made: list[Cluster] = []

    def _make(**kwargs) -> Cluster:
        cluster = Cluster(tmp_path / f"cluster{len(made)}", monkeypatch, **kwargs)
        made.append(cluster)
        return cluster

    yield _make
    for cluster in made:
        cluster.close()


def make_source_copy(tmp_path: Path, replacements: list[tuple[str, str]], name: str = "service_mutant.py") -> Path:
    """Write a text-modified COPY of service.py (never touches production). Every `old`
    string must occur exactly once, otherwise the control is invalid and fails loudly."""
    text = DIST_SOURCE.read_text()
    for old, new in replacements:
        assert text.count(old) == 1, f"negative-control anchor not found exactly once: {old!r}"
        text = text.replace(old, new)
    path = tmp_path / name
    path.write_text(text)
    return path
