"""Test CA for the mTLS tests (audit 13 sez. 3.5): OpenSSL CLI only, no new dependency.

Every certificate is issued with ``openssl ca`` so that validity windows can be set
explicitly (an already expired certificate is one of the cases of plan sez. 6.4).
Identities are SAN URIs ``spiffe://dib.consortium/...``; server certificates also carry
``IP:127.0.0.1`` and ``DNS:localhost`` so hostname verification works on loopback.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

OPENSSL = shutil.which("openssl")
TRUST = "spiffe://dib.consortium"

requires_openssl = pytest.mark.skipif(OPENSSL is None, reason="openssl CLI not available")


def san_site(site: str) -> str:
    return f"{TRUST}/site/{site}"


def san_operator(site: str) -> str:
    return f"{TRUST}/site/{site}/operator"


SAN_EVIDENCE = f"{TRUST}/evidence"
SAN_ADMIN = f"{TRUST}/admin/ops-1"


@dataclass(frozen=True)
class Leaf:
    cert: Path
    key: Path


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%SZ")


def _run(*args: str, cwd: Path) -> None:
    subprocess.run([OPENSSL, *args], cwd=cwd, check=True, capture_output=True)


class TestCA:
    """A private CA in ``root`` (one directory per CA)."""

    __test__ = False  # not a pytest class

    def __init__(self, root: Path, name: str = "DIB test CA") -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        (root / "newcerts").mkdir(exist_ok=True)
        (root / "index.txt").write_text("")
        (root / "serial").write_text("1000\n")
        (root / "ca.cnf").write_text(
            "[ca]\ndefault_ca = CA_default\n"
            "[CA_default]\n"
            f"dir = {root}\ndatabase = $dir/index.txt\nnew_certs_dir = $dir/newcerts\n"
            "serial = $dir/serial\ndefault_md = sha256\npolicy = policy_any\n"
            "unique_subject = no\ncopy_extensions = none\n"
            "[policy_any]\ncommonName = supplied\n"
        )
        self.cert = root / "ca.crt"
        self.key = root / "ca.key"
        _run("req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
             "-keyout", str(self.key), "-out", str(self.cert), "-days", "2", "-subj", f"/CN={name}",
             "-addext", "basicConstraints=critical,CA:TRUE",
             "-addext", "keyUsage=critical,keyCertSign,cRLSign", cwd=root)

    def issue(self, name: str, sans: list[str], *, eku: str = "serverAuth,clientAuth",
              not_before: datetime | None = None, not_after: datetime | None = None) -> Leaf:
        now = datetime.now(timezone.utc)
        not_before = not_before or now - timedelta(minutes=5)
        not_after = not_after or now + timedelta(hours=24)  # short-lived by default
        key, csr, cert = (self.root / f"{name}.{ext}" for ext in ("key", "csr", "crt"))
        ext = self.root / f"{name}.ext"
        ext.write_text(
            "basicConstraints = critical,CA:FALSE\n"
            "keyUsage = critical,digitalSignature\n"
            f"extendedKeyUsage = {eku}\n"
            f"subjectAltName = {','.join(sans)}\n"
        )
        _run("req", "-new", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
             "-keyout", str(key), "-out", str(csr), "-subj", f"/CN={name}", cwd=self.root)
        _run("ca", "-batch", "-notext", "-config", str(self.root / "ca.cnf"), "-cert", str(self.cert),
             "-keyfile", str(self.key), "-in", str(csr), "-out", str(cert), "-extfile", str(ext),
             "-startdate", _ts(not_before), "-enddate", _ts(not_after), cwd=self.root)
        return Leaf(cert, key)

    def server(self, name: str, san_uri: str, dns: tuple[str, ...] = ()) -> Leaf:
        sans = [f"URI:{san_uri}", "IP:127.0.0.1", "DNS:localhost", *(f"DNS:{d}" for d in dns)]
        return self.issue(name, sans)

    def client(self, name: str, san_uri: str, **kw) -> Leaf:
        return self.issue(name, [f"URI:{san_uri}"], **kw)


def write_identities(path: Path, identities: dict[str, dict], denylist: list[str] | None = None) -> Path:
    path.write_text(json.dumps({"version": 1, "identities": identities, "denylist": denylist or []}))
    return path
