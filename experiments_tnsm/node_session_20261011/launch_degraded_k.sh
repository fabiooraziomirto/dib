#!/usr/bin/env bash
# Starts auto_degraded_k.py DETACHED on the node (it waits by itself for the watcher heartbeat, until --not-after). No sudo.
# Usage: launch_degraded_k.sh <tree> <out-dir> <end-utc> <not-after-utc> <hashes-file>
set -euo pipefail
TREE=$1; OUT=$2; END=$3; NOTAFTER=$4; HASHES=$5
mkdir -p "$OUT"
if [[ -f $OUT/auto_degraded_k.pid ]] && kill -0 "$(cat "$OUT/auto_degraded_k.pid")" 2>/dev/null; then echo "already running" >&2; exit 1; fi
setsid nohup "$HOME/dib_tnsm/venv/bin/python" "$HOME/dib_tnsm/b2k/auto_degraded_k.py" --tree "$TREE" --out "$OUT" --end-utc "$END" --not-after "$NOTAFTER" --hashes "$HASHES" \
  > "$OUT/auto_degraded_k.stdout" 2>&1 < /dev/null &
echo $! > "$OUT/auto_degraded_k.launcher.pid"
sleep 1
echo "started (pid $(cat "$OUT/auto_degraded_k.launcher.pid")), waits for the watcher until $NOTAFTER"
