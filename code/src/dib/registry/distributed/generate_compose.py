"""Generates docker-compose.yml for N_SITES site containers + 1 evidence
container. Regenerate with `python3 generate_compose.py > docker-compose.yml`
if N_SITES changes."""
import os

N_SITES = int(os.environ.get("DIB_DIST_N_SITES", "10"))
# Operational values of the new knobs (the service defaults are T=0 and cap=min(N_SITES, 16): unbounded staleness,
# fan-out as wide as the consortium). Override from the environment when generating, e.g. for the measurements.
RECONCILE_INTERVAL = os.environ.get("DIB_DIST_RECONCILE_INTERVAL", "5")
RECONCILE_JITTER = os.environ.get("DIB_DIST_RECONCILE_JITTER", "0.5")
RECONCILE_TIMEOUT = os.environ.get("DIB_DIST_RECONCILE_TIMEOUT", "5.0")
FANOUT_CONCURRENCY = os.environ.get("DIB_DIST_FANOUT_CONCURRENCY", str(min(N_SITES, 16)))
# opt-in persistent fan-out connections (docs/audit/62): passed to the evidence service only when set in the generator's environment
_KEEPALIVE_ENV = [f"      - {k}={os.environ[k]}" for k in ("DIB_DIST_FANOUT_KEEPALIVE", "DIB_DIST_FANOUT_WARM_INTERVAL") if k in os.environ]
# mTLS (docs/audit/13_mtls_design.md): DIB_DIST_MTLS=1 starts every service through
# dib.registry.distributed.mtls, mounts DIB_DIST_PKI_DIR read-only at /pki (expected files:
# ca.crt, identities.json, <service>.crt and <service>.key with service = evidence, site-<i>)
# and switches the peer URLs to https. Unset: the plain topology, byte-identical to before.
MTLS = os.environ.get("DIB_DIST_MTLS", "0") == "1"
TYPE_LIST = os.environ.get("DIB_DIST_TYPE_LIST", "0") == "1"
PKI_DIR = os.environ.get("DIB_DIST_PKI_DIR", "./pki")
SCHEME = "https" if MTLS else "http"


def _mtls_env(service):
    if not MTLS:
        return []
    return (["      - DIB_DIST_MTLS=1"] + (["      - DIB_DIST_TYPE_LIST=1"] if TYPE_LIST else [])
            + [f"      - DIB_DIST_TLS_CERT=/pki/{service}.crt", f"      - DIB_DIST_TLS_KEY=/pki/{service}.key",
               "      - DIB_DIST_TLS_CA=/pki/ca.crt", "      - DIB_DIST_IDENTITIES=/pki/identities.json"])


def _mtls_command():
    if not MTLS:
        return []
    return ['    command: ["python", "-m", "dib.registry.distributed.mtls", "--app", "service:app", "--port", "8000"]']


def _mtls_volume():
    return [f"      - {PKI_DIR}:/pki:ro"] if MTLS else []


lines = ["services:", "  evidence:", "    build:", "      context: ../../../..",
         "      dockerfile: src/dib/registry/distributed/Dockerfile", *_mtls_command(), "    environment:",
         "      - DIB_DIST_ROLE=evidence", f"      - DIB_DIST_N_SITES={N_SITES}",
         "      - DIB_DIST_DATA_DIR=/data", f"      - DIB_DIST_FANOUT_CONCURRENCY={FANOUT_CONCURRENCY}", *_KEEPALIVE_ENV]
for i in range(N_SITES):
    lines += [f"      - DIB_DIST_SITE_URL_{i}={SCHEME}://site-{i}:8000"]
lines += [*_mtls_env("evidence"), "    volumes:", "      - evidence_data:/data", *_mtls_volume(),
          "    ports:", "      - \"18100:8000\""]

for i in range(N_SITES):
    lines += [
        f"  site-{i}:", "    build:", "      context: ../../../..",
         "      dockerfile: src/dib/registry/distributed/Dockerfile", *_mtls_command(), "    environment:",
        "      - DIB_DIST_ROLE=site", f"      - DIB_DIST_SITE_INDEX={i}",
        f"      - DIB_DIST_N_SITES={N_SITES}", f"      - DIB_DIST_EVIDENCE_URL={SCHEME}://evidence:8000",
        "      - DIB_DIST_DATA_DIR=/data",
        f"      - DIB_DIST_RECONCILE_INTERVAL={RECONCILE_INTERVAL}",
        f"      - DIB_DIST_RECONCILE_JITTER={RECONCILE_JITTER}",
        f"      - DIB_DIST_RECONCILE_TIMEOUT={RECONCILE_TIMEOUT}",
        *_mtls_env(f"site-{i}"),
        "    volumes:", f"      - site_{i}_data:/data", *_mtls_volume(),
        "    depends_on:", "      - evidence",
        "    ports:", f"      - \"{18110 + i}:8000\"",
    ]

lines += ["volumes:", "  evidence_data:"]
for i in range(N_SITES):
    lines += [f"  site_{i}_data:"]

print("\n".join(lines))
