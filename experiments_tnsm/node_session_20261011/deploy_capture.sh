#!/usr/bin/env bash
# Audit 116: B1 on the REAL 11-container deployment (user-space netem applier, no sudo) with header sniffers INSIDE the containers (capture_helper.py + sniff_in_container.py).
# Same as deploy_run.sh plus: a host directory ~/dib_tnsm/m67/capture bind-mounted at /capture in every container, the helper started detached and stopped at the end.
# Usage: deploy_capture.sh <tree> <out-dir> <profile> <episodes> <arms> <fanouts>
set -uo pipefail
T=$1; OUT=$2; PROF=$3; EPS=$4; ARMS=$5; FOS=$6
PY=$HOME/dib_tnsm/venv/bin/python; M=$HOME/dib_tnsm/m67; CAP=$M/capture
mkdir -p "$OUT"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/seq.log"; }
if docker ps --format '{{.Names}}' | grep -q dibtnsm; then log "dibtnsm container present: REFUSED"; touch "$OUT/REFUSED"; exit 1; fi
AV=$(awk '/MemAvailable/{print int($2/1024/1024)}' /proc/meminfo); [ "$AV" -lt 4 ] && { log "MemAvailable ${AV} GB < 4: REFUSED"; touch "$OUT/REFUSED"; exit 1; }
FREE=$(df --output=avail -B1 / | tail -1); [ "$FREE" -lt 2000000000 ] && { log "disk < 2 GB: REFUSED"; touch "$OUT/REFUSED"; exit 1; }
[ -d "$CAP" ] && [ -n "$(ls -A "$CAP" 2>/dev/null)" ] && { log "$CAP not empty: REFUSED (move it, never delete)"; touch "$OUT/REFUSED"; exit 1; }
mkdir -p "$M" "$CAP"
cp $HOME/dib_tnsm/b2k/sniff_in_container.py "$CAP/sniff_in_container.py"
{ echo "services:"; for s in evidence site-0 site-1 site-2 site-3 site-4 site-5 site-6 site-7 site-8 site-9; do
  echo "  $s:"; echo "    cap_add: [NET_ADMIN]"; echo "    volumes:"; echo "      - /usr/sbin/tc:/hosttc:ro"; echo "      - /lib/x86_64-linux-gnu:/hostlib:ro"; echo "      - $CAP:/capture"; done; } > "$M/extra_netadmin_capture.yml"
echo "$PROF" > "$M/userspace_profile"; rm -f "$M/userspace_profile.STOP" "$CAP/HELPER.STOP"
setsid nohup $PY $HOME/dib_tnsm/b2k/userspace_netem.py --profile-file "$M/userspace_profile" --log "$OUT/netem_applier.log" > /dev/null 2>&1 < /dev/null &
APID=$!; echo $APID > "$OUT/applier.pid"; log "applier pid $APID profile $PROF"
setsid nohup $PY $HOME/dib_tnsm/b2k/capture_helper.py --capture-dir "$CAP" --log "$OUT/capture_helper.log" > /dev/null 2>&1 < /dev/null &
HPID=$!; echo $HPID > "$OUT/helper.pid"; log "capture helper pid $HPID"
export DIB_M67_EXTRA_COMPOSE="$M/extra_netadmin_capture.yml"
EPSARG=""; [ "$EPS" != "default" ] && EPSARG="--episodes $EPS"
log "run.py b1 $PROF arms $ARMS fanouts $FOS episodes $EPS"
timeout 14400 $PY $T/experiments_tnsm/m67_retraction/run.py --block b1 --profile $PROF --tree $T --out "$OUT/b1" --arms $ARMS --fanouts $FOS --seed 20261014 --profile-wait 90 $EPSARG > "$OUT/run.log" 2>&1
log "run.py rc=$?"
touch "$M/userspace_profile.STOP" "$CAP/HELPER.STOP"; sleep 2; kill $APID $HPID 2>/dev/null
docker ps --format '{{.Names}}' | grep -c dibtnsm > "$OUT/containers_left.txt" || true
mv "$CAP" "$OUT/capture"      # moved, not copied: the next run needs an empty $CAP; the data stay in the out dir
date -u +%FT%TZ > "$OUT/DONE"
