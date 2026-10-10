"""Test CA for the mTLS tests (audit 13 sez. 3.5): OpenSSL CLI only, no new dependency.

Every certificate is issued with ``openssl ca`` (scripts/make_dist_pki.CA) so that validity windows can be set
explicitly (an already expired certificate is one of the cases of plan sez. 6.4).
Identities are SAN URIs ``spiffe://dib.consortium/...``; server certificates also carry
``IP:127.0.0.1`` and ``DNS:localhost`` so hostname verification works on loopback.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.make_dist_pki import CA, OPENSSL
TRUST = "spiffe://dib.consortium"

requires_openssl = pytest.mark.skipif(OPENSSL is None, reason="openssl CLI not available")


def san_site(site: str) -> str:
    return f"{TRUST}/site/{site}"


def san_operator(site: str) -> str:
    return f"{TRUST}/site/{site}/operator"


SAN_EVIDENCE = f"{TRUST}/evidence"
SAN_ADMIN = f"{TRUST}/admin/ops-1"


class TestCA(CA):
    """A private CA in ``root`` (one directory per CA): the CA of scripts/make_dist_pki.py,
    so tests and deployment share one implementation."""

    __test__ = False  # not a pytest class

    def __init__(self, root: Path, name: str = "DIB test CA") -> None:
        super().__init__(root, name)


def write_identities(path: Path, identities: dict[str, dict], denylist: list[str] | None = None) -> Path:
    path.write_text(json.dumps({"version": 1, "identities": identities, "denylist": denylist or []}))
    return path
