#!/usr/bin/env bash
# Starts night.py DETACHED (setsid nohup, PID file) on the node, from the frozen tree. No sudo.
# Usage: launch_night.sh <tree> <out-dir> <end-utc> <watcher-poll> <hashes-file> [extra night.py args, e.g. --profile lan for a smoke]
#   hashes-file: lines "<sha256>  <path relative to the tree>" (sha256sum format), the table the user compared and confirmed.
# Check later:  kill -0 $(cat <out>/night.pid) && echo running ; tail -n 20 <out>/night.stdout ; cat <out>/state.json | tail -n 40
set -euo pipefail
TREE=$1; OUT=$2; END=$3; POLL=$4; HASHES=$5
shift 5
EXTRA=("$@")
die() { echo "launch_night: $*" >&2; exit 1; }
[[ -d $TREE && -f $HASHES ]] || die "tree or hashes file missing"
mkdir -p "$OUT"
if [[ -f $OUT/night.pid ]] && kill -0 "$(cat "$OUT/night.pid")" 2>/dev/null; then die "already running (pid $(cat "$OUT/night.pid"))"; fi
ARGS=()
while read -r sha rel; do [[ -n ${sha:-} ]] && ARGS+=(--expect "$rel=$sha"); done < "$HASHES"
setsid nohup "$HOME/dib_tnsm/venv/bin/python" "$TREE/experiments_tnsm/m67_retraction/night.py" --tree "$TREE" --out "$OUT" \
  --end-utc "$END" --watcher-poll "$POLL" "${ARGS[@]}" ${EXTRA[@]+"${EXTRA[@]}"} > "$OUT/night.stdout" 2>&1 < /dev/null &
echo $! > "$OUT/night.pid"
sleep 2
kill -0 "$(cat "$OUT/night.pid")" && echo "night.py running, pid $(cat "$OUT/night.pid"), out $OUT"
