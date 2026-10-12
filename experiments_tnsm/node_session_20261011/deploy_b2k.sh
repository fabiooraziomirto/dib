#!/usr/bin/env bash
# B2-kill on the REAL 11-container deployment with the user-space netem applier instead of the root watcher (audit 45 rules kept: L_dns p95 <= 50 ms with an applier
# poll <= 0.1 s, no threshold change, a profile that fails the rule is NOT run and is recorded). Detached, no sudo. Profiles lan,degraded,wan in this order (data of a profile are kept).
# Usage: deploy_b2k.sh <tree> <out-dir> [profiles=lan,degraded,wan]
set -uo pipefail
T=$1; OUT=$2; PROFILES=${3:-lan,degraded,wan}
TRIALS=${TRIALS:-10}; SEED=${SEED:-20261014}   # audit 99 addendum 2: second series = TRIALS=20 SEED=20261016
export DIB_M67_DNS_NOSEARCH=1          # audit 72: no search domains in the cluster
PY=$HOME/dib_tnsm/venv/bin/python; M=$HOME/dib_tnsm/m67
mkdir -p "$OUT" "$M"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/seq.log"; }
if docker ps --format '{{.Names}}' | grep -q dibtnsm; then log "dibtnsm container present: REFUSED"; touch "$OUT/REFUSED"; exit 1; fi
AV=$(awk '/MemAvailable/{print int($2/1024/1024)}' /proc/meminfo); [ "$AV" -lt 4 ] && { log "MemAvailable ${AV} GB < 4: REFUSED"; touch "$OUT/REFUSED"; exit 1; }
FREE=$(df --output=avail -B1 / | tail -1); [ "$FREE" -lt 2000000000 ] && { log "disk < 2 GB: REFUSED"; touch "$OUT/REFUSED"; exit 1; }
{ echo "services:"; for s in evidence site-0 site-1 site-2 site-3 site-4 site-5 site-6 site-7 site-8 site-9; do
  echo "  $s:"; echo "    cap_add: [NET_ADMIN]"; echo "    volumes:"; echo "      - /usr/sbin/tc:/hosttc:ro"; echo "      - /lib/x86_64-linux-gnu:/hostlib:ro"; done; } > "$M/extra_netadmin.yml"
export DIB_M67_EXTRA_COMPOSE="$M/extra_netadmin.yml"
echo lan > "$M/userspace_profile"; rm -f "$M/userspace_profile.STOP"
setsid nohup $PY $HOME/dib_tnsm/b2k/userspace_netem.py --profile-file "$M/userspace_profile" --log "$OUT/netem_applier.log" --poll 0.1 > /dev/null 2>&1 < /dev/null &
APID=$!; echo $APID > "$OUT/applier.pid"; log "applier pid $APID poll 0.1 s"
for PROF in ${PROFILES//,/ }; do
  echo "$PROF" > "$M/userspace_profile"; log "profile $PROF: calibration (L_dns)"
  timeout 3600 $PY $T/experiments_tnsm/m67_retraction/calib_profile.py --tree $T --out $OUT/calib_$PROF --profile $PROF --profile-wait 90 > $OUT/calib_$PROF.log 2>&1; log "calib $PROF rc=$?"
  RES=$($PY - <<PYEOF
import sys
sys.path.insert(0, "$T/experiments_tnsm/m67_retraction")
import night
try:
    d = night.parse_ldns(open("$OUT/calib_$PROF/calib_ldns_$PROF.txt").read())
    p95 = d["killed"]["p95_ms"]
except Exception as exc:
    p95 = None
dec, why = night.ldns_decision(p95, 0.1)
print(dec, (p95 / 1000.0 if p95 is not None else ""), why.replace(" ", "_"))
PYEOF
)
  DEC=$(echo $RES | cut -d' ' -f1); L=$(echo $RES | cut -d' ' -f2); WHY=$(echo $RES | cut -d' ' -f3-)
  log "L_dns decision $PROF: $DEC ($WHY)"
  echo "$RES" > "$OUT/ldns_decision_$PROF.txt"
  [ "$DEC" != "run" ] && { log "profile $PROF NOT run (rule of audit 45, no threshold change)"; continue; }
  for ARM in D C; do
    log "b2kill $PROF arm $ARM"
    timeout 21600 $PY $T/experiments_tnsm/m67_retraction/run.py --block b2kill --profile $PROF --tree $T --out $OUT/b2kill_${PROF}_$ARM --arms $ARM --seed $SEED --trials $TRIALS --profile-wait 90 --l-dns $L > $OUT/b2kill_${PROF}_$ARM.log 2>&1; log "$PROF arm $ARM rc=$?"
  done
done
touch "$M/userspace_profile.STOP"; sleep 2; kill $APID 2>/dev/null
echo lan > "$M/userspace_profile"
docker ps --format '{{.Names}}' | grep -c dibtnsm > "$OUT/containers_left.txt" || true
date -u +%FT%TZ > "$OUT/DONE"
