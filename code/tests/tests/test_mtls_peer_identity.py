"""Step 1 of the mTLS design (audit 13 sez. 4, option B): does a custom uvicorn HTTP
protocol make the verified client certificate visible to the ASGI application?

Hypotheses (stated before running, tests written before dib.registry.distributed.mtls):
  P1. With PeerCertH11Protocol and ssl_cert_reqs=CERT_REQUIRED, a request authenticated
      with a certificate from the trusted CA reaches the app with
      scope["extensions"]["tls"]["dib_peer_san_uris"] equal to the certificate's SAN URIs
      (uvicorn 0.51.0 alone exposes nothing: h11_impl.py:205-219).
  P2. The TLS handshake (not the app) rejects: no client certificate (T2), a certificate
      from an unknown CA (T3), an expired certificate (T4), a certificate whose EKU is
      codeSigning only, i.e. a MUD signing certificate (T13).
  P3. The identity is per connection: two requests on one pooled client see the same SAN;
      a second client with another certificate sees its own.
  P4. The uvicorn version is pinned: mtls.UVICORN_VERSION == uvicorn.__version__.
Falsification: any assertion below failing. If P1 cannot be met, option B is abandoned
for the reverse proxy (option A), as decided by the user.
"""
from __future__ import annotations

import json
import socket
import ssl
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import uvicorn

from _mtls_ca import TestCA, requires_openssl, san_site

pytestmark = requires_openssl


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _echo_app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    tls = (scope.get("extensions") or {}).get("tls") or {}
    body = json.dumps({"sans": list(tls.get("dib_peer_san_uris", ())),
                       "chain_len": len(tls.get("client_cert_chain", ()))}).encode()
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})


@pytest.fixture(scope="module")
def pki(tmp_path_factory):
    root = tmp_path_factory.mktemp("pki")
    ca = TestCA(root / "ca")
    other = TestCA(root / "other", name="Unknown CA")
    now = datetime.now(timezone.utc)
    return {
        "ca": ca,
        "server": ca.server("server", f"spiffe://dib.consortium/evidence"),
        "site0": ca.client("site0", san_site("site-0")),
        "site1": ca.client("site1", san_site("site-1")),
        "expired": ca.client("expired", san_site("site-0"),
                             not_before=now - timedelta(days=2), not_after=now - timedelta(days=1)),
        "signing": ca.client("signing", san_site("site-0"), eku="codeSigning"),
        "foreign": other.client("foreign", san_site("site-0")),
    }


@pytest.fixture(scope="module")
def server(pki):
    from dib.registry.distributed import mtls

    port = _free_port()
    config = mtls.server_config(_echo_app, host="127.0.0.1", port=port,
                                certfile=pki["server"].cert, keyfile=pki["server"].key,
                                cafile=pki["ca"].cert, log_level="warning")
    srv = uvicorn.Server(config)
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not srv.started:
        assert time.monotonic() < deadline, "uvicorn did not start"
        time.sleep(0.05)
    yield f"https://127.0.0.1:{port}/"
    srv.should_exit = True
    thread.join(timeout=10)


def _ctx(pki, leaf=None) -> ssl.SSLContext:
    from dib.registry.distributed import mtls

    if leaf is None:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(pki["ca"].cert))
        return ctx
    return mtls.client_context(leaf.cert, leaf.key, pki["ca"].cert)


def test_p1_valid_client_identity_visible(pki, server):
    r = httpx.get(server, verify=_ctx(pki, pki["site0"]), timeout=5)
    assert r.status_code == 200
    assert r.json() == {"sans": ["spiffe://dib.consortium/site/site-0"], "chain_len": 1}


@pytest.mark.parametrize("case", ["none", "foreign", "expired", "signing"])
def test_p2_handshake_rejects(pki, server, case):
    leaf = None if case == "none" else pki[case]
    if case == "foreign":
        from dib.registry.distributed import mtls
        ctx = mtls.client_context(leaf.cert, leaf.key, pki["ca"].cert)  # trusts the server, own cert foreign
    else:
        ctx = _ctx(pki, leaf)
    with pytest.raises(httpx.TransportError):
        r = httpx.get(server, verify=ctx, timeout=5)
        # TLS 1.3 reports a rejected client certificate on the first read; a 200 here means
        # the handshake accepted the certificate, which falsifies P2.
        pytest.fail(f"request accepted with case={case}: {r.status_code} {r.text}")


def test_p3_identity_is_per_connection(pki, server):
    with httpx.Client(verify=_ctx(pki, pki["site0"]), timeout=5) as a, \
            httpx.Client(verify=_ctx(pki, pki["site1"]), timeout=5) as b:
        assert a.get(server).json()["sans"] == ["spiffe://dib.consortium/site/site-0"]
        assert b.get(server).json()["sans"] == ["spiffe://dib.consortium/site/site-1"]
        assert a.get(server).json()["sans"] == ["spiffe://dib.consortium/site/site-0"]


def test_p4_uvicorn_version_pinned():
    from dib.registry.distributed import mtls

    assert uvicorn.__version__ == mtls.UVICORN_VERSION == "0.51.0"
