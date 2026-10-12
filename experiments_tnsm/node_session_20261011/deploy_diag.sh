#!/usr/bin/env bash
# Audit 101: diagnosis of the setup 500s on the 11-container deployment (arm C, degraded) with the user-space applier. Detached, no sudo. Usage: deploy_diag.sh <tree> <out-dir> [facts=50]
set -uo pipefail
T=$1; OUT=$2; FACTS=${3:-50}
PY=$HOME/dib_tnsm/venv/bin/python; M=$HOME/dib_tnsm/m67
mkdir -p "$OUT" "$M"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/seq.log"; }
if docker ps --format '{{.Names}}' | grep -q dibtnsm; then log "dibtnsm container present: REFUSED"; touch "$OUT/REFUSED"; exit 1; fi
AV=$(awk '/MemAvailable/{print int($2/1024/1024)}' /proc/meminfo); [ "$AV" -lt 4 ] && { log "MemAvailable ${AV} GB < 4: REFUSED"; touch "$OUT/REFUSED"; exit 1; }
FREE=$(df --output=avail -B1 / | tail -1); [ "$FREE" -lt 2000000000 ] && { log "disk < 2 GB: REFUSED"; touch "$OUT/REFUSED"; exit 1; }
{ echo "services:"; for s in evidence site-0 site-1 site-2 site-3 site-4 site-5 site-6 site-7 site-8 site-9; do
  echo "  $s:"; echo "    cap_add: [NET_ADMIN]"; echo "    volumes:"; echo "      - /usr/sbin/tc:/hosttc:ro"; echo "      - /lib/x86_64-linux-gnu:/hostlib:ro"; done; } > "$M/extra_netadmin.yml"
export DIB_M67_EXTRA_COMPOSE="$M/extra_netadmin.yml"
echo degraded > "$M/userspace_profile"; rm -f "$M/userspace_profile.STOP"
setsid nohup $PY $HOME/dib_tnsm/b2k/userspace_netem.py --profile-file "$M/userspace_profile" --log "$OUT/netem_applier.log" > /dev/null 2>&1 < /dev/null &
APID=$!; echo $APID > "$OUT/applier.pid"; log "applier pid $APID profile degraded"
log "diag_setup500 arm C facts $FACTS"
timeout 7200 $PY $HOME/dib_tnsm/b2k/diag_setup500.py $T $OUT/diag.json --facts $FACTS --arm C > $OUT/diag.log 2>&1; log "diag rc=$?"
touch "$M/userspace_profile.STOP"; sleep 2; kill $APID 2>/dev/null
echo lan > "$M/userspace_profile"
docker ps --format '{{.Names}}' | grep -c dibtnsm > "$OUT/containers_left.txt" || true
date -u +%FT%TZ > "$OUT/DONE"
