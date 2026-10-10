"""Private test PKI for the mTLS deployment of the distributed prototype (audit 13).

OpenSSL CLI only (Q3: no step-ca dependency). Writes the layout generate_compose.py mounts
at /pki (ca.crt, identities.json, <service>.crt|.key for evidence and site-<i>), the
client identities the benchmark uses (op-site-<i> = each site's operator, admin) and
pki_manifest.json. The CA key and the CA database go to ``<out>.ca/``, never into the
directory mounted into the containers.

Deterministic except key material: serial numbers, SANs, extensions, validity window
(--not-before + --valid-hours, default 24 h: short-lived certificates, audit 13 sez. 3.5)
and identities.json are functions of the arguments; keys come from ``openssl genpkey``
and are random. Private keys are refused inside the repository unless the target is
ignored by git (the default, next to docker-compose.yml, is).

Usage (from code/):
    python3 scripts/make_dist_pki.py --n-sites 10 --not-before 2026-10-11T00:00:00Z
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TRUST = "spiffe://dib.consortium"
CODE = Path(__file__).resolve().parents[1]
DEFAULT_OUT = CODE / "src" / "dib" / "registry" / "distributed" / "pki"
BENCH_DEVICE_TYPES = ["cam-a", "cam-b", "cam-c"]  # distributed_concurrency_benchmark.do_op
OPENSSL = shutil.which("openssl")


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%d%H%M%SZ")


def _run(*args: str, cwd: Path) -> None:
    subprocess.run([OPENSSL, *args], cwd=cwd, check=True, capture_output=True)


class CA:
    """A private CA whose database lives in ``root``; leaves are written to ``out``."""

    def __init__(self, root: Path, name: str = "DIB test CA", *, out: Path | None = None,
                 not_before: datetime | None = None, not_after: datetime | None = None,
                 first_serial: int = 0x1000) -> None:
        if OPENSSL is None:
            raise RuntimeError("openssl CLI not found")
        now = datetime.now(timezone.utc)
        self.not_before = not_before or now - timedelta(minutes=5)
        self.not_after = not_after or now + timedelta(hours=48)
        self.root = root
        self.out = out or root
        root.mkdir(parents=True, exist_ok=True)
        self.out.mkdir(parents=True, exist_ok=True)
        (root / "newcerts").mkdir(exist_ok=True)
        (root / "index.txt").write_text("")
        (root / "serial").write_text(f"{first_serial:X}\n")
        (root / "ca.cnf").write_text(
            "[ca]\ndefault_ca = CA_default\n"
            "[CA_default]\n"
            f"dir = {root}\ndatabase = $dir/index.txt\nnew_certs_dir = $dir/newcerts\n"
            "serial = $dir/serial\ndefault_md = sha256\npolicy = policy_any\n"
            "unique_subject = no\ncopy_extensions = none\n"
            "[policy_any]\ncommonName = supplied\n"
        )
        self.key = root / "ca.key"
        self.cert = self.out / "ca.crt"
        _run("genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", str(self.key), cwd=root)
        csr, ext = root / "ca.csr", root / "ca.ext"
        ext.write_text("basicConstraints = critical,CA:TRUE\nkeyUsage = critical,keyCertSign,cRLSign\n")
        _run("req", "-new", "-key", str(self.key), "-out", str(csr), "-subj", f"/CN={name}", cwd=root)
        _run("ca", "-batch", "-notext", "-selfsign", "-config", str(root / "ca.cnf"), "-keyfile", str(self.key),
             "-in", str(csr), "-out", str(self.cert), "-extfile", str(ext),
             "-startdate", _ts(self.not_before), "-enddate", _ts(self.not_after), cwd=root)

    def issue(self, name: str, sans: list[str], *, eku: str = "serverAuth,clientAuth",
              not_before: datetime | None = None, not_after: datetime | None = None):
        from types import SimpleNamespace

        now = datetime.now(timezone.utc)
        not_before = not_before or now - timedelta(minutes=5)
        not_after = not_after or now + timedelta(hours=24)
        key, cert = self.out / f"{name}.key", self.out / f"{name}.crt"
        csr, ext = self.root / f"{name}.csr", self.root / f"{name}.ext"
        ext.write_text(
            "basicConstraints = critical,CA:FALSE\n"
            "keyUsage = critical,digitalSignature\n"
            f"extendedKeyUsage = {eku}\n"
            f"subjectAltName = {','.join(sans)}\n"
        )
        _run("genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", str(key), cwd=self.root)
        _run("req", "-new", "-key", str(key), "-out", str(csr), "-subj", f"/CN={name}", cwd=self.root)
        _run("ca", "-batch", "-notext", "-config", str(self.root / "ca.cnf"), "-cert", str(self.cert),
             "-keyfile", str(self.key), "-in", str(csr), "-out", str(cert), "-extfile", str(ext),
             "-startdate", _ts(not_before), "-enddate", _ts(not_after), cwd=self.root)
        return SimpleNamespace(cert=cert, key=key)

    def server(self, name: str, san_uri: str, dns: tuple[str, ...] = (), **kw):
        sans = [f"URI:{san_uri}", *(f"DNS:{d}" for d in dns), "DNS:localhost", "IP:127.0.0.1"]
        return self.issue(name, sans, **kw)

    def client(self, name: str, san_uri: str, **kw):
        return self.issue(name, [f"URI:{san_uri}"], **kw)


def _refuse_unignored(paths: list[Path]) -> None:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=CODE, capture_output=True, text=True)
    if top.returncode != 0:
        return
    root = Path(top.stdout.strip()).resolve()
    for path in paths:
        p = path.resolve()
        if root in p.parents or p == root:
            probe = p / "probe.key"
            if subprocess.run(["git", "check-ignore", "-q", str(probe)], cwd=root).returncode != 0:
                sys.exit(f"refusing to write private keys to {path}: not ignored by git")


def build(out: Path, n_sites: int, not_before: datetime, valid_hours: float,
          device_types: list[str]) -> dict:
    ca_dir = out.with_name(out.name + ".ca")
    _refuse_unignored([out, ca_dir])
    for d in (out, ca_dir):
        if d.exists():
            shutil.rmtree(d)
    not_after = not_before + timedelta(hours=valid_hours)
    ca = CA(ca_dir, out=out, not_before=not_before, not_after=not_after)
    window = {"not_before": not_before, "not_after": not_after}
    identities: dict[str, dict] = {}
    plan = [("evidence", "server", f"{TRUST}/evidence", ("evidence",), {"role": "evidence"})]
    plan.append(("admin", "client", f"{TRUST}/admin/bench-admin", (), {"role": "consortium_admin"}))
    for i in range(n_sites):
        site = f"site-{i}"
        plan.append((site, "server", f"{TRUST}/site/{site}", (site,),
                     {"site": site, "role": "member", "device_types": device_types}))
    for i in range(n_sites):
        site = f"site-{i}"
        plan.append((f"op-{site}", "client", f"{TRUST}/site/{site}/operator", (),
                     {"site": site, "role": "operator", "device_types": device_types}))
    certs = []
    for name, kind, san, dns, entry in plan:
        leaf = ca.server(name, san, dns, **window) if kind == "server" else ca.client(name, san, **window)
        identities[san] = entry
        serial = subprocess.run([OPENSSL, "x509", "-in", str(leaf.cert), "-noout", "-serial"],
                                capture_output=True, text=True, check=True).stdout.strip().split("=", 1)[1]
        certs.append({"name": name, "san_uri": san, "dns": list(dns), "serial": serial,
                      "sha256": hashlib.sha256(leaf.cert.read_bytes()).hexdigest()})
    (out / "identities.json").write_text(
        json.dumps({"version": 1, "identities": identities, "denylist": []}, indent=1) + "\n")
    version = subprocess.run([OPENSSL, "version"], capture_output=True, text=True).stdout.strip()
    manifest = {
        "generator": "code/scripts/make_dist_pki.py",
        "openssl": version,
        "n_sites": n_sites,
        "not_before": _ts(not_before), "not_after": _ts(not_after), "valid_hours": valid_hours,
        "device_types_per_site": device_types,
        "ca_dir": str(ca_dir),
        "key_material": "random (openssl genpkey); everything else is a function of the arguments",
        "ca_sha256": hashlib.sha256(ca.cert.read_bytes()).hexdigest(),
        "certificates": certs,
    }
    (out / "pki_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--n-sites", type=int, default=10)
    p.add_argument("--not-before", required=True,
                   help="UTC start of validity, e.g. 2026-10-11T00:00:00Z (explicit for determinism)")
    p.add_argument("--valid-hours", type=float, default=24.0)
    p.add_argument("--device-types", default=",".join(BENCH_DEVICE_TYPES))
    a = p.parse_args()
    nb = datetime.fromisoformat(a.not_before.replace("Z", "+00:00"))
    manifest = build(a.out, a.n_sites, nb, a.valid_hours, [t for t in a.device_types.split(",") if t])
    print(f"wrote {len(manifest['certificates'])} certificates to {a.out} "
          f"(valid {manifest['not_before']} - {manifest['not_after']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
