#!/usr/bin/env bash
# M7 (audit 04): remove the netem qdiscs set by netem_apply.sh. PREPARED, NOT RUN.
# Touches only veth-dib-h / veth-dib-n. With --teardown it also deletes the veth pair and
# the "dibnet" namespace (stop the services running in the namespace first).
#
# Usage:  sudo ./netem_clear.sh [--dry-run] [--teardown]
set -euo pipefail

NS=dibnet
HOST_IF=veth-dib-h
NS_IF=veth-dib-n
DRY=0
TEARDOWN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1;;
    --teardown) TEARDOWN=1;;
    *) echo "usage: $0 [--dry-run] [--teardown]" >&2; exit 1;;
  esac
done
run() { if [[ $DRY == 1 ]]; then echo "+ $*"; else "$@"; fi; }
[[ $DRY == 1 || $EUID == 0 ]] || { echo "netem_clear: must run as root (sudo)" >&2; exit 1; }

if ip link show "$HOST_IF" >/dev/null 2>&1 || [[ $DRY == 1 ]]; then
  run tc qdisc del dev "$HOST_IF" root 2>/dev/null || true
fi
if ip netns list 2>/dev/null | grep -qw "$NS" || [[ $DRY == 1 ]]; then
  run ip netns exec "$NS" tc qdisc del dev "$NS_IF" root 2>/dev/null || true
fi
if [[ $TEARDOWN == 1 ]]; then
  run ip link del "$HOST_IF" 2>/dev/null || true   # deleting one end removes the pair
  run ip netns del "$NS" 2>/dev/null || true
fi
echo "netem_clear: done (dry-run=$DRY, teardown=$TEARDOWN)"
[[ $DRY == 1 ]] || { tc qdisc show dev "$HOST_IF" 2>/dev/null || echo "($HOST_IF absent)"; }
