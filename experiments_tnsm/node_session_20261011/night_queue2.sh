#!/usr/bin/env bash
# Night queue 2 (audit 107): after the first queue (second B2k series + R1f) the v5 (mTLS) validation on the REAL deployment at X1-X4, one profile at a time (deploy_run.sh: user-space applier,
# run.py b1, arms D,C, FANOUT 10, 50 episodes per cell by default). Detached, no sudo. Each run stops by itself with ImageMismatch if the containers do not run the tree's service.py.
# Runtime correction: each profile reads its tree from $HOME/dib_tnsm/CURRENT_TREE_OOS when it starts (falls back to <tree>).
# Usage: night_queue2.sh <tree> <first-queue-root> <out-root>
set -uo pipefail
T=$1; FIRSTROOT=$2; ROOT=$3
log() { echo "$(date -u +%FT%TZ) $*" >> "$ROOT/queue2.log"; }
mkdir -p "$ROOT"
log "waiting for $FIRSTROOT/QUEUE_DONE"
until [ -f "$FIRSTROOT/QUEUE_DONE" ]; do sleep 60; done
for X in x1 x2 x3 x4; do
  log "profile $X"
  T4=$(cat $HOME/dib_tnsm/CURRENT_TREE_OOS 2>/dev/null || echo $T)
  bash $HOME/dib_tnsm/b2k/deploy_run.sh $T4 $ROOT/node_oos_$X $X default D,C 10 > /dev/null 2>&1; log "profile $X rc=$? tree $T4"
done
date -u +%FT%TZ > "$ROOT/QUEUE2_DONE"
