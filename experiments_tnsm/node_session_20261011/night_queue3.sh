#!/usr/bin/env bash
# Node T-0 of the mTLS gap (audit 113): lossless profiles z1 and z3, arms D,C, FANOUT 10, 30 episodes per cell. Detached, no sudo. Usage: night_queue3.sh <tree> <out-root>
set -uo pipefail
T=$1; ROOT=$2
log() { echo "$(date -u +%FT%TZ) $*" >> "$ROOT/queue3.log"; }
mkdir -p "$ROOT"
for X in z1 z3; do
  log "profile $X"
  bash $HOME/dib_tnsm/b2k/deploy_run.sh $T $ROOT/node_t0_$X $X default D,C 10 > /dev/null 2>&1; log "profile $X rc=$? tree $T"
done
date -u +%FT%TZ > "$ROOT/QUEUE3_DONE"
