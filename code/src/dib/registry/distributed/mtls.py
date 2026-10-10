"""Mutual TLS for the distributed prototype (docs/audit/13_mtls_design.md, option B).

uvicorn 0.51.0 can require a client certificate (Config.ssl_cert_reqs) but does not put
the peer certificate in the ASGI scope (protocols/http/h11_impl.py:205-219), so the
application cannot tell WHICH site is calling. PeerCertH11Protocol closes that gap: on
each TLS connection it reads the verified peer certificate from the transport and wraps
the ASGI app so every request on that connection carries
scope["extensions"]["tls"] (shape of the ASGI TLS extension, plus
"dib_peer_san_uris"). It relies only on H11Protocol.connection_made and the
per-request lookup of ``self.app`` (h11_impl.py:232), and is guarded by an exact
uvicorn version pin (UVICORN_VERSION) checked at server start and in the tests.

Identities: the SAN URI is the identity; site and role come from a server-side JSON
mapping (Identities), never from the certificate alone or the request payload.
Revocation: short-lived certificates plus a denylist in the mapping, re-read when the
file changes. No CRL (user decision Q6; limit declared in audit 13).

Standard library plus uvicorn only: the service image installs nothing else.
"""
from __future__ import annotations

import json
import os
import ssl
import threading
from pathlib import Path

import uvicorn
from uvicorn.protocols.http.h11_impl import H11Protocol

UVICORN_VERSION = "0.51.0"

ROLE_MEMBER = "member"          # a site's service identity (site -> evidence calls)
ROLE_OPERATOR = "operator"      # a site's local operator tooling (site-local endpoints)
ROLE_EVIDENCE = "evidence"      # the evidence service (evidence -> site fan-out)
ROLE_ADMIN = "consortium_admin"  # global restore, seeding
ROLES = frozenset({ROLE_MEMBER, ROLE_OPERATOR, ROLE_EVIDENCE, ROLE_ADMIN})


def check_uvicorn_version() -> None:
    if uvicorn.__version__ != UVICORN_VERSION:
        raise RuntimeError(
            f"mtls.PeerCertH11Protocol is pinned to uvicorn {UVICORN_VERSION}, found "
            f"{uvicorn.__version__}: re-verify h11_impl before changing the pin (audit 13)"
        )


def san_uris(peercert: dict | None) -> tuple[str, ...]:
    if not peercert:
        return ()
    return tuple(value for kind, value in peercert.get("subjectAltName", ()) if kind == "URI")


class PeerCertH11Protocol(H11Protocol):
    """H11Protocol that exposes the verified client certificate to the ASGI app."""

    def connection_made(self, transport) -> None:  # type: ignore[override]
        super().connection_made(transport)
        ssl_object = transport.get_extra_info("ssl_object")
        if ssl_object is None:
            return
        der = ssl_object.getpeercert(binary_form=True)
        info = {
            "server_cert": None,
            "client_cert_chain": [ssl.DER_cert_to_PEM_cert(der)] if der else [],
            "client_cert_name": None,
            "client_cert_error": None,
            "tls_version": None,
            "cipher_suite": None,
            "dib_peer_san_uris": san_uris(ssl_object.getpeercert()),
        }
        app = self.app

        async def app_with_tls(scope, receive, send):
            if scope["type"] in ("http", "websocket"):
                extensions = dict(scope.get("extensions") or {})
                extensions["tls"] = info
                scope = {**scope, "extensions": extensions}
            await app(scope, receive, send)

        self.app = app_with_tls


def peer_sans(scope: dict) -> tuple[str, ...]:
    return tuple(((scope.get("extensions") or {}).get("tls") or {}).get("dib_peer_san_uris", ()))


def server_config(app, *, host: str, port: int, certfile, keyfile, cafile, **kwargs) -> uvicorn.Config:
    """uvicorn.Config that requires a client certificate from ``cafile`` and exposes it."""
    check_uvicorn_version()
    return uvicorn.Config(
        app, host=host, port=port, http=PeerCertH11Protocol,
        ssl_certfile=str(certfile), ssl_keyfile=str(keyfile), ssl_ca_certs=str(cafile),
        ssl_cert_reqs=ssl.CERT_REQUIRED, **kwargs,
    )


def client_context(certfile, keyfile, cafile) -> ssl.SSLContext:
    """Client side of mTLS: verify the server against ``cafile``, present our certificate."""
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(cafile))
    ctx.load_cert_chain(str(certfile), str(keyfile))
    return ctx


class Identities:
    """Server-side mapping SAN URI -> {site, role[, device_types]} with a denylist.

    The JSON file is re-read whenever its mtime changes, so a revocation (adding a SAN to
    ``denylist``) takes effect on the next request without a restart.
    """

    def __init__(self, path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._mtime: float | None = None
        self._identities: dict[str, dict] = {}
        self._denylist: frozenset[str] = frozenset()
        self._reload_if_changed()

    def _reload_if_changed(self) -> None:
        mtime = os.stat(self.path).st_mtime_ns
        if mtime == self._mtime:
            return
        with self._lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            identities = payload.get("identities", {})
            for san, entry in identities.items():
                if entry.get("role") not in ROLES:
                    raise ValueError(f"unknown role {entry.get('role')!r} for {san}")
            self._identities = identities
            self._denylist = frozenset(payload.get("denylist", ()))
            self._mtime = mtime

    def resolve(self, sans: tuple[str, ...]) -> dict | None:
        """The mapping entry of the first mapped, non-revoked SAN, or None."""
        self._reload_if_changed()
        for san in sans:
            if san in self._denylist:
                return None
            entry = self._identities.get(san)
            if entry is not None:
                return {"san": san, **entry}
        return None


def main() -> None:
    """Container entry point: ``python -m dib.registry.distributed.mtls`` (TLS on)."""
    import argparse

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--app", default=os.environ.get("DIB_DIST_APP", "service:app"))
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args()
    config = server_config(a.app, host=a.host, port=a.port,
                           certfile=os.environ["DIB_DIST_TLS_CERT"], keyfile=os.environ["DIB_DIST_TLS_KEY"],
                           cafile=os.environ["DIB_DIST_TLS_CA"])
    uvicorn.Server(config).run()


if __name__ == "__main__":
    main()
