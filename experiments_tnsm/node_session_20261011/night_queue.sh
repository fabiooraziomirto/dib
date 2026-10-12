#!/usr/bin/env bash
# Night queue (audit 99 addendum 2, audit 104): waits for the first B2k series, then runs the second series (20 trials per cell, seed 20261016) and then R1f (replica of R1e). Detached, no sudo.
# Each step is guarded by its own checks (deploy_b2k.sh / deploy_run.sh refuse with containers present, low memory or disk; run.py stops with ImageMismatch). Usage: night_queue.sh <tree> <b2k-first-out-dir> <out-root>
set -uo pipefail
T=$1; FIRST=$2; ROOT=$3
log() { echo "$(date -u +%FT%TZ) $*" >> "$ROOT/queue.log"; }
mkdir -p "$ROOT"
log "waiting for $FIRST/DONE"
until [ -f "$FIRST/DONE" ]; do sleep 60; done
log "first B2k series done; second series (TRIALS=20 SEED=20261016)"
TRIALS=20 SEED=20261016 bash $HOME/dib_tnsm/b2k/deploy_b2k_v2.sh $T $ROOT/final_B2k_b_20261012 lan,degraded,wan > /dev/null 2>&1; log "second series rc=$?"
log "R1f"
bash $HOME/dib_tnsm/b2k/deploy_run.sh $T $ROOT/final_R1f_20261012 degraded default D,C 10,1 > /dev/null 2>&1; log "R1f rc=$?"
date -u +%FT%TZ > "$ROOT/QUEUE_DONE"
