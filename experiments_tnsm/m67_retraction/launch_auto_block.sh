#!/usr/bin/env bash
# Starts auto_block.py DETACHED (setsid nohup, PID file) on the node, from the frozen tree. No sudo. The watcher v2 must already be running.
# Usage: launch_auto_block.sh <tree> <out-dir> <end-utc> <hashes-file> [extra auto_block.py args, e.g. --blocks degraded --smoke]
#   hashes-file: lines "<sha256>  <path relative to the tree>" (sha256sum format), the table the user compared and confirmed.
# Check later:  kill -0 $(cat <out>/auto_block.pid) && echo running ; tail -n 20 <out>/auto_block.stdout ; tail -n 40 <out>/state.json
set -euo pipefail
TREE=$1; OUT=$2; END=$3; HASHES=$4
shift 4
die() { echo "launch_auto_block: $*" >&2; exit 1; }
[[ -d $TREE && -f $HASHES ]] || die "tree or hashes file missing"
mkdir -p "$OUT"
if [[ -f $OUT/auto_block.pid ]] && kill -0 "$(cat "$OUT/auto_block.pid")" 2>/dev/null; then die "already running (pid $(cat "$OUT/auto_block.pid"))"; fi
setsid nohup "$HOME/dib_tnsm/venv/bin/python" "$TREE/experiments_tnsm/m67_retraction/auto_block.py" --tree "$TREE" --out "$OUT" \
  --end-utc "$END" --hashes "$HASHES" "$@" > "$OUT/auto_block.stdout" 2>&1 < /dev/null &
echo $! > "$OUT/auto_block.pid"
sleep 2
kill -0 "$(cat "$OUT/auto_block.pid")" && echo "auto_block.py running, pid $(cat "$OUT/auto_block.pid"), out $OUT"
