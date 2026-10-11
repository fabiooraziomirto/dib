#!/usr/bin/env bash
# Starts the M8 measurement DETACHED on the node AFTER any auto_block.py / auto_b2k.py (B5, B2k) is gone. No sudo. Usage: launch_m8.sh <out-dir>
set -euo pipefail
OUT=$1
mkdir -p "$OUT"
setsid nohup bash -c '
  while pgrep -f "[a]uto_block.py|[a]uto_b2k.py|[l]aunch_auto_b2k" > /dev/null; do sleep 30; done
  sleep 60   # let the cluster teardown and the CPU settle
  if docker ps --format "{{.Names}}" | grep -q dibtnsm; then echo "dibtnsm container present: not measuring" > "$1/REFUSED"; exit 0; fi
  exec python3 "$HOME/dib_tnsm/m8/run.py" measure --files "$HOME/dib_tnsm/m8/files" --out "$1/result"
' bash "$OUT" > "$OUT/m8.stdout" 2>&1 < /dev/null &
echo $! > "$OUT/m8.waiter.pid"; echo "waiter started (pid $(cat "$OUT/m8.waiter.pid"))"
