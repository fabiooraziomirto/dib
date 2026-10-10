"""Generates docker-compose.yml for N_SITES site containers + 1 evidence
container. Regenerate with `python3 generate_compose.py > docker-compose.yml`
if N_SITES changes."""
import os

N_SITES = int(os.environ.get("DIB_DIST_N_SITES", "10"))
# Operational values of the new knobs (the service defaults are T=0, cap=1: unbounded staleness,
# sequential fan-out). Override from the environment when generating, e.g. for the measurements.
RECONCILE_INTERVAL = os.environ.get("DIB_DIST_RECONCILE_INTERVAL", "5")
RECONCILE_JITTER = os.environ.get("DIB_DIST_RECONCILE_JITTER", "0.5")
RECONCILE_TIMEOUT = os.environ.get("DIB_DIST_RECONCILE_TIMEOUT", "5.0")
FANOUT_CONCURRENCY = os.environ.get("DIB_DIST_FANOUT_CONCURRENCY", "8")

lines = ["services:", "  evidence:", "    build:", "      context: ../../../..",
         "      dockerfile: src/dib/registry/distributed/Dockerfile", "    environment:",
         "      - DIB_DIST_ROLE=evidence", f"      - DIB_DIST_N_SITES={N_SITES}",
         "      - DIB_DIST_DATA_DIR=/data", f"      - DIB_DIST_FANOUT_CONCURRENCY={FANOUT_CONCURRENCY}"]
for i in range(N_SITES):
    lines += [f"      - DIB_DIST_SITE_URL_{i}=http://site-{i}:8000"]
lines += ["    volumes:", "      - evidence_data:/data",
          "    ports:", "      - \"18100:8000\""]

for i in range(N_SITES):
    lines += [
        f"  site-{i}:", "    build:", "      context: ../../../..",
         "      dockerfile: src/dib/registry/distributed/Dockerfile", "    environment:",
        "      - DIB_DIST_ROLE=site", f"      - DIB_DIST_SITE_INDEX={i}",
        f"      - DIB_DIST_N_SITES={N_SITES}", "      - DIB_DIST_EVIDENCE_URL=http://evidence:8000",
        "      - DIB_DIST_DATA_DIR=/data",
        f"      - DIB_DIST_RECONCILE_INTERVAL={RECONCILE_INTERVAL}",
        f"      - DIB_DIST_RECONCILE_JITTER={RECONCILE_JITTER}",
        f"      - DIB_DIST_RECONCILE_TIMEOUT={RECONCILE_TIMEOUT}",
        "    volumes:", f"      - site_{i}_data:/data",
        "    depends_on:", "      - evidence",
        "    ports:", f"      - \"{18110 + i}:8000\"",
    ]

lines += ["volumes:", "  evidence_data:"]
for i in range(N_SITES):
    lines += [f"  site_{i}_data:"]

print("\n".join(lines))
