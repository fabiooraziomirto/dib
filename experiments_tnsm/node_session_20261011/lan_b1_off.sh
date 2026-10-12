#!/usr/bin/env bash
# Control of audit 70 H-L2: B1 FANOUT 10 at lan with the keep-alive OFF, same tree, same session. Detached, no sudo. Usage: lan_b1_off.sh <tree> <out-dir>
set -uo pipefail
T=$1; OUT=$2; PY=$HOME/dib_tnsm/venv/bin/python
mkdir -p "$OUT"; log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/seq.log"; }
if docker ps --format '{{.Names}}' | grep -q dibtnsm; then log "container present: REFUSED"; touch "$OUT/REFUSED"; exit 1; fi
unset DIB_M67_KEEPALIVE
for ARM in D C; do
  log "b1 arm $ARM fanout 10 (keepalive OFF)"
  timeout 7200 $PY $T/experiments_tnsm/m67_retraction/run.py --block b1 --profile lan --tree $T --out $OUT/b1_$ARM --arms $ARM --fanouts 10 --seed 20261014 --profile-wait 90 > $OUT/b1_$ARM.log 2>&1; log "b1 $ARM rc=$?"
done
date -u +%FT%TZ > "$OUT/DONE"
