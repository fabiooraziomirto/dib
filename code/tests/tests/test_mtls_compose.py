"""Step 3 of the mTLS design (audit 13 sez. 5, point 5): Docker image and Compose topology.

Hypotheses (stated before running, tests written before the Dockerfile and generator change):
  C1. Without DIB_DIST_MTLS the generator output is byte-identical to the committed
      docker-compose.yml: the plain topology used by the existing results is unchanged.
  C2. With DIB_DIST_MTLS=1 every service (evidence and each site) is started through
      ``python -m dib.registry.distributed.mtls``, gets DIB_DIST_MTLS=1, its own
      certificate and key, the CA, the identity mapping from a read-only /pki mount, and
      reaches its peers over https; DIB_DIST_TYPE_LIST is passed through when set.
  C3. The image pins uvicorn to mtls.UVICORN_VERSION and contains mtls.py where
      ``dib.registry.distributed.mtls`` resolves (PYTHONPATH=/app).
Falsification: any assertion below failing. Nothing is built or run.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

DIST = Path(__file__).resolve().parents[2] / "src" / "dib" / "registry" / "distributed"


def _generate(**env) -> str:
    clean = {k: v for k, v in os.environ.items() if not k.startswith("DIB_DIST_")}
    out = subprocess.run([sys.executable, str(DIST / "generate_compose.py")], env={**clean, **env},
                         capture_output=True, text=True, check=True, cwd=DIST)
    return out.stdout


def _services(text: str) -> dict[str, str]:
    body = text.split("\nvolumes:\n")[0]
    blocks = re.split(r"\n  (?=[a-z][\w-]*:\n)", body.split("services:\n", 1)[1])
    return {b.split(":", 1)[0].strip(): b for b in blocks}


def test_c1_plain_output_unchanged():
    assert _generate() == (DIST / "docker-compose.yml").read_text()


def test_c2_mtls_topology():
    text = _generate(DIB_DIST_N_SITES="3", DIB_DIST_MTLS="1", DIB_DIST_TYPE_LIST="1",
                     DIB_DIST_PKI_DIR="./pki")
    services = _services(text)
    assert set(services) == {"evidence", "site-0", "site-1", "site-2"}
    for name, block in services.items():
        assert 'command: ["python", "-m", "dib.registry.distributed.mtls", "--app", "service:app", "--port", "8000"]' in block, name
        assert "- DIB_DIST_MTLS=1" in block and "- DIB_DIST_TYPE_LIST=1" in block, name
        assert f"- DIB_DIST_TLS_CERT=/pki/{name}.crt" in block and f"- DIB_DIST_TLS_KEY=/pki/{name}.key" in block, name
        assert "- DIB_DIST_TLS_CA=/pki/ca.crt" in block and "- DIB_DIST_IDENTITIES=/pki/identities.json" in block, name
        assert "- ./pki:/pki:ro" in block, name
        assert "http://" not in block, name
    assert "- DIB_DIST_SITE_URL_2=https://site-2:8000" in services["evidence"]
    assert "- DIB_DIST_EVIDENCE_URL=https://evidence:8000" in services["site-1"]


def test_c3_image_pins_uvicorn_and_ships_mtls():
    from dib.registry.distributed import mtls

    dockerfile = (DIST / "Dockerfile").read_text()
    assert f"uvicorn=={mtls.UVICORN_VERSION}" in dockerfile
    assert "COPY src/dib/registry/distributed/mtls.py /app/dib/registry/distributed/mtls.py" in dockerfile
    assert "COPY src/dib/registry/__init__.py /app/dib/registry/__init__.py" in dockerfile


def test_c4_base_image_python312_pinned_by_digest():
    """C4 (pre-M3/M4 step 3, user decision G1 = Python 3.12): the service image is
    python:3.12-slim pinned by digest (index digest on Docker Hub, 2026-10-10: amd64
    image built 2026-10-06 with PYTHON_VERSION=3.12.15, as /opt/conda/envs/dib312)."""
    first = (DIST / "Dockerfile").read_text().splitlines()[0]
    assert re.fullmatch(r"FROM python:3\.12-slim@sha256:[0-9a-f]{64}", first), first
    assert first.endswith("a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1")
