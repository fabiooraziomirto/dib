#!/usr/bin/env bash
# Starts auto_b2k.py DETACHED on the node, AFTER waiting for any running auto_block.py (B5) to finish. No sudo. The watcher v2 must be running.
# Usage: launch_auto_b2k.sh <tree> <out-dir> <end-utc> <hashes-file>
set -euo pipefail
TREE=$1; OUT=$2; END=$3; HASHES=$4
mkdir -p "$OUT"
if [[ -f $OUT/auto_b2k.pid ]] && kill -0 "$(cat "$OUT/auto_b2k.pid")" 2>/dev/null; then echo "already running" >&2; exit 1; fi
setsid nohup bash -c '
  while pgrep -f "[a]uto_block.py" > /dev/null; do sleep 30; done
  exec "$HOME/dib_tnsm/venv/bin/python" "$HOME/dib_tnsm/b2k/auto_b2k.py" --tree "$0" --out "$1" --end-utc "$2" --hashes "$3"
' "$TREE" "$OUT" "$END" "$HASHES" > "$OUT/auto_b2k.stdout" 2>&1 < /dev/null &
echo $! > "$OUT/auto_b2k.waiter.pid"
sleep 1; echo "waiter started (pid $(cat "$OUT/auto_b2k.waiter.pid")); auto_b2k.py starts when auto_block.py is gone"
