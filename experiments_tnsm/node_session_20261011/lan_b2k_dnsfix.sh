#!/usr/bin/env bash
# H-D1 (audit 60 s.1): B2-kill at `lan` with the driver fix, NO watcher needed (lan = no netem). Detached, no sudo. Usage: lan_b2k_validation.sh <tree> <out-dir>
set -uo pipefail
export DIB_M67_DNS_NOSEARCH=1   # audit 72 H-N1: no search domains in the cluster
T=$1; OUT=$2
PY=$HOME/dib_tnsm/venv/bin/python
mkdir -p "$OUT"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/seq.log"; }
if docker ps --format '{{.Names}}' | grep -q dibtnsm; then log "dibtnsm container present: REFUSED"; touch "$OUT/REFUSED"; exit 1; fi
FREE=$(df --output=avail -B1 / | tail -1); if [ "$FREE" -lt 2000000000 ]; then log "disk below 2 GB: REFUSED"; touch "$OUT/REFUSED"; exit 1; fi
log "calibration lan (L_dns)"
timeout 3600 $PY $T/experiments_tnsm/m67_retraction/calib_profile.py --tree $T --out $OUT/calib --profile lan --profile-wait 90 > $OUT/calib.log 2>&1; log "calib rc=$?"
L=$($PY - <<PYEOF
import json,sys
sys.path.insert(0,"$T/experiments_tnsm/m67_retraction")
import night
t=open("$OUT/calib/calib_ldns_lan.txt").read()
d=night.parse_ldns(t); print(d["killed"]["p95_ms"]/1000.0)
PYEOF
)
log "L_dns p95 s=$L"
for ARM in D C; do
  log "b2kill arm $ARM"
  timeout 14400 $PY $T/experiments_tnsm/m67_retraction/run.py --block b2kill --profile lan --tree $T --out $OUT/b2kill_$ARM --arms $ARM --seed 20261014 --profile-wait 90 --l-dns $L > $OUT/b2kill_$ARM.log 2>&1; log "arm $ARM rc=$?"
done
docker ps --format '{{.Names}}' | grep -c dibtnsm > $OUT/containers_left.txt || true
date -u +%FT%TZ > "$OUT/DONE"
