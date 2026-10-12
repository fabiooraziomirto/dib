#!/bin/sh
# Run TLC on one cfg of DIB_AE_NA.tla with OOM and disk guards (docs/audit/67).
# usage: run_tlc.sh <cfg-name-without-.cfg> [heap_gb=20] [workers=8]
#  - JVM heap capped (-Xmx), the host has 64 GB and no swap;
#  - watchdog: kills TLC if free space on / drops below MIN_FREE_GB (default 8; the disk is ~94% full);
#  - the TLC metadir (state queue on disk) lives in the session scratchpad and is deleted at the end;
#  - log in logs/<cfg>.log, one manifest line per run in logs/manifest.tsv
#    (UTC start/end, cfg, sha256 of module/cfg/jar, java, heap, workers, exit, result line).
set -u
cd "$(dirname "$0")"
CFG=$1; HEAP=${2:-20}; WORKERS=${3:-8}
JAR=${TLA_JAR:-/root/Desktop/BioDevOps/formal_methods/tla2tools.jar}
JAR_SHA=237332bdcc79a35c7d26efa7b82c77c85c2744591c5598673a8a45085ff2a4fb
MIN_FREE_GB=${MIN_FREE_GB:-8}
SCRATCH=${TLC_SCRATCH:?set TLC_SCRATCH to a scratch directory}
[ "$(sha256sum "$JAR" | cut -d' ' -f1)" = "$JAR_SHA" ] || { echo "jar sha256 mismatch"; exit 2; }
mkdir -p logs
WORK=$(mktemp -d "$SCRATCH/tlc_${CFG}_XXXX")
cp DIB_AE_NA.tla "$CFG.cfg" "$WORK/"
LOG=logs/$CFG.log
START=$(date -u +%FT%TZ)
( cd "$WORK" && exec java -Xmx${HEAP}g -XX:+UseParallelGC -cp "$JAR" tlc2.TLC -workers "$WORKERS" \
    -metadir "$WORK/meta" -config "$CFG.cfg" DIB_AE_NA ) > "$LOG" 2>&1 &
PID=$!
while kill -0 $PID 2>/dev/null; do
  FREE=$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
  if [ "$FREE" -lt "$MIN_FREE_GB" ]; then
    echo "WATCHDOG: free disk ${FREE}G < ${MIN_FREE_GB}G, TLC killed at $(date -u +%FT%TZ)" >> "$LOG"
    kill $PID; sleep 5; kill -9 $PID 2>/dev/null
  fi
  sleep 15
done
wait $PID; RC=$?
END=$(date -u +%FT%TZ)
RES=$(grep -E "distinct states found|is violated|Error:|No error has been found|WATCHDOG|OutOfMemory" "$LOG" | tr '\t' ' ' | tail -3 | tr '\n' ' ')
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$START" "$END" "$CFG" \
  "$(sha256sum DIB_AE_NA.tla | cut -c1-16)" "$(sha256sum "$CFG.cfg" | cut -c1-16)" "${JAR_SHA%${JAR_SHA#????????????????}}" \
  "$(java -version 2>&1 | head -1 | tr -d '"')" "heap=${HEAP}g workers=$WORKERS" "exit=$RC" "$RES" >> logs/manifest.tsv
rm -rf "$WORK"
echo "$CFG exit=$RC $RES"
