#!/usr/bin/env bash
# M6xM7 (plan rev. 5; audit 14, 18): per-container netem for the dibtnsm compose project. PREPARED; the user
# runs it (or netem_watch.sh) with sudo on the node 192.168.100.57 only. See netem_common.sh for the guard:
# the 11 containers of the project, by label AND exact name, validated BEFORE anything is applied.
#
# Each container gets a netem qdisc on the egress of its own eth0 inside its own network namespace
# (nsenter -t <pid> -n tc qdisc replace ...). A packet from X to Y crosses only X's egress qdisc, so
# evidence<->site RTT = 2d and the round-trip loss ~ 2p. Nothing is applied in the root namespace.
#
# Usage:  sudo ./netem_apply.sh [--dry-run] <profile> [<site-index>]
#   lan        removes the qdisc of every container (`tc qdisc del`, the only deletion; errors ignored if none)
#   regional   every container: delay 20ms loss 0.1%
#   wan        every container: delay 80ms loss 1%
#   degraded   every container: delay 200ms loss 5%
#   extreme    every container: delay 550ms (no loss)
#   mixed      evidence and sites 0-4 none; sites 5-9 delay 80ms loss 1%
#   partition  site <site-index> only: loss 100% (its egress); the others are left as they are
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=netem_common.sh
source "$HERE/netem_common.sh"

DRY=0
run() { if [[ $DRY == 1 ]]; then echo "+ $*"; else "$@"; fi; }
[[ ${1:-} == --dry-run ]] && { DRY=1; shift; }
PROFILE=${1:-}; SITE=${2:-}
[[ -n $PROFILE ]] || die "usage: $0 [--dry-run] lan|regional|wan|degraded|extreme|mixed|partition [site]"
[[ $DRY == 1 || $EUID == 0 ]] || die "must run as root (sudo)"

profile_args() {  # container name -> netem args ("" = remove, KEEP = leave untouched)
  local name=$1
  case $PROFILE in
    lan) echo "";;
    regional) echo "delay 20ms loss 0.1%";;
    wan) echo "delay 80ms loss 1%";;
    degraded) echo "delay 200ms loss 5%";;
    extreme) echo "delay 550ms";;
    mixed) [[ $name =~ site-([5-9])- ]] && echo "delay 80ms loss 1%" || echo "";;
    partition) [[ -n $SITE ]] || die "partition needs a site index"
               [[ $name == "$PROJECT-site-$SITE-1" ]] && echo "loss 100%" || echo "KEEP";;
    *) die "unknown profile $PROFILE";;
  esac
}

# Validate the whole list and every profile argument BEFORE touching any namespace.
load_entries
plan=()
while read -r name pid; do
  args=$(profile_args "$name") || exit 1
  plan+=("$name $pid $args")
done <<< "$ENTRIES"
echo "netem_apply: profile=$PROFILE, ${#plan[@]} of $NODE_N_EXPECTED expected containers of project $PROJECT"

for line in "${plan[@]}"; do
  read -r name pid args <<< "$line"
  [[ $args == KEEP ]] && continue
  echo "$name (pid $pid): ${args:-no qdisc}"
  if [[ -z $args ]]; then
    run nsenter -t "$pid" -n tc qdisc del dev eth0 root 2>/dev/null || true
  else
    run nsenter -t "$pid" -n tc qdisc replace dev eth0 root netem $args
  fi
done
