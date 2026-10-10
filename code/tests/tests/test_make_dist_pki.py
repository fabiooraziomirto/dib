"""Step 1 before M3/M4 (audit 13 sez. 9, item 6): PKI for the Docker deployment.

Hypotheses (stated before running, written before scripts/make_dist_pki.py):
  K1. ``make_dist_pki.py --out D --n-sites N`` writes exactly the layout the Compose file
      expects (generate_compose.py: /pki/ca.crt, /pki/identities.json,
      /pki/<service>.crt|.key for evidence and site-<i>) plus the client identities used
      by the benchmark (op-site-<i>, admin) and a manifest.
  K2. Deterministic except key material: two runs with the same arguments give the same
      identities.json, the same serial numbers, SANs and validity window; certificates
      differ only because keys are random (declared in the manifest).
  K3. Certificates are short-lived (default 24 h from --not-before), server certificates
      carry DNS:<service>, DNS:localhost and IP:127.0.0.1, and identities.json maps every
      SAN to the role of audit 13 sez. 3.3, with the benchmark's device types per site.
  K4. The script refuses to write private keys inside the repository unless the target
      is ignored by git; the default target (next to docker-compose.yml) is ignored.
Falsification: any assertion below failing.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from _mtls_ca import requires_openssl

pytestmark = requires_openssl

CODE = Path(__file__).resolve().parents[2]
SCRIPT = CODE / "scripts" / "make_dist_pki.py"
DEFAULT_OUT = CODE / "src" / "dib" / "registry" / "distributed" / "pki"
NB = "2026-10-10T00:00:00Z"


def _run(*args, check=True):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          check=check, cwd=CODE)


def _x509(cert: Path, *opts: str) -> str:
    return subprocess.run(["openssl", "x509", "-in", str(cert), "-noout", *opts],
                          capture_output=True, text=True, check=True).stdout


def test_k1_layout(tmp_path):
    out = tmp_path / "pki"
    _run("--out", str(out), "--n-sites", "3", "--not-before", NB)
    names = {"evidence", "site-0", "site-1", "site-2", "op-site-0", "op-site-1", "op-site-2", "admin"}
    expected = {"ca.crt", "identities.json", "pki_manifest.json"} | {f"{n}.{e}" for n in names for e in ("crt", "key")}
    assert {p.name for p in out.iterdir()} == expected
    assert not (out / "ca.key").exists()  # the CA key never sits next to the deployment files


def test_k2_deterministic_except_keys(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for d in (a, b):
        _run("--out", str(d), "--n-sites", "2", "--not-before", NB)
    assert (a / "identities.json").read_text() == (b / "identities.json").read_text()
    for name in ("evidence", "site-0", "site-1", "op-site-0", "admin"):
        for args in (("-serial",), ("-dates",), ("-ext", "subjectAltName,extendedKeyUsage")):
            assert _x509(a / f"{name}.crt", *args) == _x509(b / f"{name}.crt", *args), (name, args)
    ma, mb = (json.loads((d / "pki_manifest.json").read_text()) for d in (a, b))
    assert ma["key_material"] == "random (openssl genpkey); everything else is a function of the arguments"
    assert [c["serial"] for c in ma["certificates"]] == [c["serial"] for c in mb["certificates"]]


def test_k3_short_lived_sans_and_mapping(tmp_path):
    out = tmp_path / "pki"
    _run("--out", str(out), "--n-sites", "2", "--not-before", NB)
    dates = _x509(out / "site-1.crt", "-dates")
    assert "notBefore=Oct 10 00:00:00 2026 GMT" in dates and "notAfter=Oct 11 00:00:00 2026 GMT" in dates
    san = _x509(out / "site-1.crt", "-ext", "subjectAltName")
    for part in ("URI:spiffe://dib.consortium/site/site-1", "DNS:site-1", "DNS:localhost", "IP Address:127.0.0.1"):
        assert part in san
    assert "URI:spiffe://dib.consortium/site/site-0/operator" in _x509(out / "op-site-0.crt", "-ext", "subjectAltName")
    ident = json.loads((out / "identities.json").read_text())
    types = ["cam-a", "cam-b", "cam-c"]
    assert ident == {"version": 1, "denylist": [], "identities": {
        "spiffe://dib.consortium/evidence": {"role": "evidence"},
        "spiffe://dib.consortium/admin/bench-admin": {"role": "consortium_admin"},
        "spiffe://dib.consortium/site/site-0": {"site": "site-0", "role": "member", "device_types": types},
        "spiffe://dib.consortium/site/site-1": {"site": "site-1", "role": "member", "device_types": types},
        "spiffe://dib.consortium/site/site-0/operator": {"site": "site-0", "role": "operator", "device_types": types},
        "spiffe://dib.consortium/site/site-1/operator": {"site": "site-1", "role": "operator", "device_types": types},
    }}


def test_k4_refuses_unignored_repo_path_and_default_is_ignored():
    target = CODE / "tests" / "tests" / "_pki_must_not_exist"
    r = _run("--out", str(target), "--n-sites", "1", "--not-before", NB, check=False)
    assert r.returncode != 0 and "not ignored by git" in r.stderr
    assert not target.exists()
    ignored = subprocess.run(["git", "check-ignore", "-q", str(DEFAULT_OUT / "ca.crt")], cwd=CODE)
    assert ignored.returncode == 0
