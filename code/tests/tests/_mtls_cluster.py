"""Real-socket mTLS cluster for the tests (one evidence, two sites; audit 13 sez. 6).

Moved verbatim from test_mtls_authorization.py so the oracle test (T15) can reuse it.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from _mtls_ca import SAN_ADMIN, SAN_EVIDENCE, TestCA, san_operator, san_site, write_identities

SRC = Path(__file__).resolve().parents[2] / "src"
FACT = {"device_type": "camera", "protocol": "https", "port": 443}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _mapping(denylist=()):
    return {
        san_site("site-0"): {"site": "site-0", "role": "member", "device_types": ["camera"]},
        san_site("site-1"): {"site": "site-1", "role": "member", "device_types": ["camera", "plug"]},
        san_site("site-9"): {"site": "site-9", "role": "member", "device_types": ["camera"]},
        san_operator("site-0"): {"site": "site-0", "role": "operator"},
        san_operator("site-1"): {"site": "site-1", "role": "operator"},
        SAN_EVIDENCE: {"role": "evidence"},
        SAN_ADMIN: {"role": "consortium_admin"},
    }, list(denylist)


class MtlsCluster:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.ca = TestCA(root / "ca")
        self.ports = {"evidence": _free_port(), 0: _free_port(), 1: _free_port()}
        self.url = {k: f"https://127.0.0.1:{p}" for k, p in self.ports.items()}
        self.server = {
            "evidence": self.ca.server("evidence", SAN_EVIDENCE),
            0: self.ca.server("site0-svc", san_site("site-0")),
            1: self.ca.server("site1-svc", san_site("site-1")),
        }
        self.clients = {
            "op0": self.ca.client("op0", san_operator("site-0")),
            "op1": self.ca.client("op1", san_operator("site-1")),
            "member0": self.server[0],  # the site's own service certificate ("stolen" in A10)
            "member1": self.server[1],
            "member9": self.ca.client("member9", san_site("site-9")),
            "admin": self.ca.client("admin", SAN_ADMIN),
            "evidence": self.server["evidence"],
            "unmapped": self.ca.client("unmapped", "spiffe://dib.consortium/site/site-77"),
        }
        self.identities = root / "identities.json"
        self.set_denylist(())
        self.procs: list[subprocess.Popen] = []
        for key in ("evidence", 0, 1):
            self.procs.append(self._start(key))
        for key in ("evidence", 0, 1):
            self._wait(key)

    def set_denylist(self, denylist) -> None:
        identities, deny = _mapping(denylist)
        write_identities(self.identities, identities, deny)
        # mtime granularity guard: make sure a rewrite is seen as a change
        st = os.stat(self.identities)
        os.utime(self.identities, ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000))

    def _start(self, key) -> subprocess.Popen:
        leaf = self.server[key]
        env = {
            **os.environ,
            "PYTHONPATH": str(SRC),
            "DIB_DIST_ROLE": "evidence" if key == "evidence" else "site",
            "DIB_DIST_SITE_INDEX": "0" if key == "evidence" else str(key),
            "DIB_DIST_N_SITES": "2",
            "DIB_DIST_DATA_DIR": str(self.root / f"data-{key}"),
            "DIB_DIST_EVIDENCE_URL": self.url["evidence"],
            "DIB_DIST_SITE_URL_0": self.url[0],
            "DIB_DIST_SITE_URL_1": self.url[1],
            "DIB_DIST_MTLS": "1",
            "DIB_DIST_TYPE_LIST": "1",
            "DIB_DIST_TLS_CERT": str(leaf.cert),
            "DIB_DIST_TLS_KEY": str(leaf.key),
            "DIB_DIST_TLS_CA": str(self.ca.cert),
            "DIB_DIST_IDENTITIES": str(self.identities),
        }
        log = (self.root / f"log-{key}.txt").open("w")
        return subprocess.Popen(
            [sys.executable, "-m", "dib.registry.distributed.mtls",
             "--app", "dib.registry.distributed.service:app",
             "--host", "127.0.0.1", "--port", str(self.ports[key])],
            env=env, stdout=log, stderr=subprocess.STDOUT,
        )

    def client(self, who: str) -> httpx.Client:
        from dib.registry.distributed import mtls

        leaf = self.clients[who]
        return httpx.Client(verify=mtls.client_context(leaf.cert, leaf.key, self.ca.cert), timeout=10)

    def _wait(self, key) -> None:
        deadline = time.monotonic() + 20
        with self.client("admin") as c:
            while True:
                try:
                    if c.get(f"{self.url[key]}/health").status_code == 200:
                        return
                except httpx.TransportError:
                    pass
                if time.monotonic() > deadline:
                    log = (self.root / f"log-{key}.txt").read_text()
                    raise AssertionError(f"{key} did not start:\n{log[-3000:]}")
                time.sleep(0.1)

    def close(self) -> None:
        for p in self.procs:
            p.terminate()
        for p in self.procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


@pytest.fixture(scope="module")
def cl(tmp_path_factory):
    cluster = MtlsCluster(tmp_path_factory.mktemp("mtls"))
    yield cluster
    cluster.close()




class PkiServices:
    """Evidence + n sites as real mTLS processes using a make_dist_pki.py layout."""

    def __init__(self, root: Path, pki: Path, n_sites: int, *, type_list: bool = True) -> None:
        self.root, self.pki, self.n = root, pki, n_sites
        self.ports = {"evidence": _free_port(), **{i: _free_port() for i in range(n_sites)}}
        self.url = {k: f"https://127.0.0.1:{p}" for k, p in self.ports.items()}
        self.procs = []
        for key in ("evidence", *range(n_sites)):
            name = "evidence" if key == "evidence" else f"site-{key}"
            env = {
                **os.environ, "PYTHONPATH": str(SRC),
                "DIB_DIST_ROLE": "evidence" if key == "evidence" else "site",
                "DIB_DIST_SITE_INDEX": "0" if key == "evidence" else str(key),
                "DIB_DIST_N_SITES": str(n_sites), "DIB_DIST_DATA_DIR": str(root / f"data-{name}"),
                "DIB_DIST_EVIDENCE_URL": self.url["evidence"],
                **{f"DIB_DIST_SITE_URL_{i}": self.url[i] for i in range(n_sites)},
                "DIB_DIST_MTLS": "1", "DIB_DIST_TYPE_LIST": "1" if type_list else "0",
                "DIB_DIST_TLS_CERT": str(pki / f"{name}.crt"), "DIB_DIST_TLS_KEY": str(pki / f"{name}.key"),
                "DIB_DIST_TLS_CA": str(pki / "ca.crt"), "DIB_DIST_IDENTITIES": str(pki / "identities.json"),
            }
            log = (root / f"log-{name}.txt").open("w")
            self.procs.append(subprocess.Popen(
                [sys.executable, "-m", "dib.registry.distributed.mtls", "--app",
                 "dib.registry.distributed.service:app", "--host", "127.0.0.1", "--port", str(self.ports[key])],
                env=env, stdout=log, stderr=subprocess.STDOUT))
        from dib.registry.distributed import mtls

        ctx = mtls.client_context(pki / "admin.crt", pki / "admin.key", pki / "ca.crt")
        with httpx.Client(verify=ctx, timeout=5) as c:
            for key, url in self.url.items():
                deadline = time.monotonic() + 20
                while True:
                    try:
                        if c.get(f"{url}/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    assert time.monotonic() < deadline, f"{key} did not start"
                    time.sleep(0.1)

    def close(self) -> None:
        for p in self.procs:
            p.terminate()
        for p in self.procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
