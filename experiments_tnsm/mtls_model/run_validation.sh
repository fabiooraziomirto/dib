#!/usr/bin/env bash
# Audit 95: runs the four launches (eq C, eq D, oos C, oos D) of the out-of-sample validation of model v5, one after the other, ONLY on a quiet machine
# (testbed.py launch refuses while tlc2.TLC runs or load >= 4; this script waits and retries, 60 s). Output: $OUT/{eq_C,eq_D,oos_C,oos_D}, $OUT/seq.log, $OUT/DONE.
# Usage: run_validation.sh <out-dir> <pki-dir-outside-the-repo>
set -uo pipefail
OUT=$1; PKI=$2
REPO=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/seq.log"; }
if [ ! -f "$PKI/ca.crt" ]; then
  (cd "$REPO/code" && python3 scripts/make_dist_pki.py --out "$PKI" --n-sites 10 --not-before 2026-10-11T00:00:00Z --valid-hours 336 --extra-san-ip 127.0.0.1 >> "$OUT/seq.log" 2>&1)
fi
run() {  # name suite [--pki]
  local name=$1 suite=$2 pki=${3:-}
  while true; do
    if python3 "$REPO/experiments_tnsm/netns_testbed/testbed.py" launch --out "$OUT/$name" --workers 4 --suite "$suite" ${pki:+--pki "$PKI"} >> "$OUT/$name.launch.log" 2>&1; then
      log "$name done"; return 0
    fi
    if grep -q "refusing to start" "$OUT/$name.launch.log"; then
      log "$name refused ($(tail -1 "$OUT/$name.launch.log")); retry in 60 s"; sleep 60
    else
      log "$name FAILED (not a refusal): see $name.launch.log"; return 1
    fi
  done
}
run eq_C mtls_eq pki && run eq_D mtls_eq && run oos_C mtls_oos pki && run oos_D mtls_oos
log "all launches finished rc=$?"
date -u +%FT%TZ > "$OUT/DONE"
