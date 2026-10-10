"""Launcher D (diagnostic, audit 18 s.1.1): plain HTTP (no TLS), same server launcher as the mTLS
arm (uvicorn.Server + PeerCertH11Protocol, as launcher B), and a PREBUILT SSL context passed to
every outgoing httpx call by setting service._HTTP_TLS FROM OUTSIDE, after importing service.py
and before serving. service.py and code/src are NOT modified; the file is mounted read-only into
the containers by a compose override and run with `python /launcher_d.py`.

Purpose: remove, in the plain arm, the per-call construction of httpx's default SSL context
(service.py:161,381; measured 6.15 ms vs 0.029 ms with a prebuilt context in the service image)
without adding TLS, to test whether that cost explains the M3/M4 anomaly.
"""
import ssl

import uvicorn

import service  # /app/service.py (PYTHONPATH=/app); same module object that uvicorn imports below

service._HTTP_TLS = {"verify": ssl.create_default_context()}
print("launcher_d: service._HTTP_TLS set from outside (prebuilt SSL context), no TLS on the listener", flush=True)

from dib.registry.distributed.mtls import PeerCertH11Protocol  # noqa: E402

uvicorn.Server(uvicorn.Config("service:app", host="0.0.0.0", port=8000, http=PeerCertH11Protocol)).run()
