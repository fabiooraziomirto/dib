#!/usr/bin/env bash
# Audit 64: lan check of the opt-in persistent fan-out connections (DIB_M67_KEEPALIVE=1), no watcher needed. Detached, no sudo.
# Usage: lan_keepalive_check.sh <tree> <out-dir>
set -uo pipefail
T=$1; OUT=$2
PY=$HOME/dib_tnsm/venv/bin/python
mkdir -p "$OUT"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/seq.log"; }
if docker ps --format '{{.Names}}' | grep -q dibtnsm; then log "dibtnsm container present: REFUSED"; touch "$OUT/REFUSED"; exit 1; fi
FREE=$(df --output=avail -B1 / | tail -1); if [ "$FREE" -lt 2000000000 ]; then log "disk below 2 GB: REFUSED"; touch "$OUT/REFUSED"; exit 1; fi
export DIB_M67_KEEPALIVE=1
log "calibration lan (keepalive on)"
timeout 3600 $PY $T/experiments_tnsm/m67_retraction/calib_profile.py --tree $T --out $OUT/calib --profile lan --profile-wait 90 > $OUT/calib.log 2>&1; log "calib rc=$?"
L=$($PY - <<PYEOF
import sys
sys.path.insert(0,"$T/experiments_tnsm/m67_retraction")
import night
print(night.parse_ldns(open("$OUT/calib/calib_ldns_lan.txt").read())["killed"]["p95_ms"]/1000.0)
PYEOF
)
log "L_dns p95 s=$L"
for ARM in D C; do
  log "b1 arm $ARM fanout 10"
  timeout 7200 $PY $T/experiments_tnsm/m67_retraction/run.py --block b1 --profile lan --tree $T --out $OUT/b1_$ARM --arms $ARM --fanouts 10 --seed 20261014 --profile-wait 90 > $OUT/b1_$ARM.log 2>&1; log "b1 $ARM rc=$?"
done
for ARM in D C; do
  log "b2kill arm $ARM"
  timeout 14400 $PY $T/experiments_tnsm/m67_retraction/run.py --block b2kill --profile lan --tree $T --out $OUT/b2kill_$ARM --arms $ARM --seed 20261014 --profile-wait 90 --l-dns $L > $OUT/b2kill_$ARM.log 2>&1; log "b2kill $ARM rc=$?"
done
# warmer exceptions in the evidence log of the last cluster are gone with the teardown: keep a marker of what the run.py logs captured
grep -l "connection warmer failed" $OUT/*.log > $OUT/warmer_exception_logs.txt 2>/dev/null || true
docker ps --format '{{.Names}}' | grep -c dibtnsm > $OUT/containers_left.txt || true
date -u +%FT%TZ > "$OUT/DONE"
