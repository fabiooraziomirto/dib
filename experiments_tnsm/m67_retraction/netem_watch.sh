#!/usr/bin/env bash
# netem_watch.sh (PREPARED, NOT RUN; to be run BY THE USER with sudo for the duration of ONE block).
#
# Why: netem lives in each container's network namespace and is destroyed with the container, while the
# driver (run.py) recreates the compose project whenever (arm, FANOUT, T) changes. This script keeps the
# profile in place: it applies <profile> to every container of the compose project "dibtnsm" (through
# netem_apply.sh, which refuses any container whose label com.docker.compose.project is not dibtnsm, so
# k3s, wasmbed and anything else on the node are never touched), then polls every 0.5 s and re-applies
# the profile as soon as the set of (container, pid) changes, i.e. after a recreation (within ~1 s; the
# driver does not measure until the RTT check matches the profile, --profile-wait). On Ctrl-C / TERM it
# removes the qdisc of every container of the project (netem_apply.sh lan) and exits.
# It does NOT grant anything beyond what the user runs: no sudoers rule, no daemon, it stops when the
# user stops it. The profile `partition` is not supported here.
#
# Usage: sudo ./netem_watch.sh <profile>            profiles as in netem_apply.sh (wan, degraded, ...)
#        ./netem_watch.sh --dry-run <profile>       prints what it would do once, applies nothing
set -euo pipefail
export PATH=/snap/bin:$PATH
HERE=$(cd "$(dirname "$0")" && pwd)
DRY=0
if [[ ${1:-} == --dry-run ]]; then DRY=1; shift; fi
PROFILE=${1:-}
[[ -n $PROFILE ]] || { echo "usage: $0 [--dry-run] <profile>" >&2; exit 2; }
[[ $PROFILE != partition ]] || { echo "netem_watch: 'partition' is not supported" >&2; exit 2; }
[[ $DRY == 1 || $EUID == 0 ]] || { echo "netem_watch: must run as root (sudo)" >&2; exit 1; }

signature() {  # sorted "name:pid" of the containers of the project
  docker ps --filter "label=com.docker.compose.project=dibtnsm" --format '{{.Names}}' | sort |
    while read -r n; do echo "$n:$(docker inspect -f '{{.State.Pid}}' "$n")"; done
}

if [[ $DRY == 1 ]]; then
  echo "netem_watch (dry run): profile=$PROFILE; current containers of the project:"
  signature | sed 's/^/  /'
  bash "$HERE/netem_apply.sh" --dry-run "$PROFILE" || true
  exit 0
fi

cleanup() {
  echo "netem_watch: stopping, removing the qdisc of every dibtnsm container" >&2
  bash "$HERE/netem_apply.sh" lan || true
  exit 0
}
trap cleanup INT TERM

last=""
echo "netem_watch: profile=$PROFILE, polling every 0.5 s (Ctrl-C to stop and clean)"
while true; do
  cur=$(signature)
  if [[ -n $cur && $cur != "$last" ]]; then
    echo "$(date -u +%FT%TZ) containers changed -> applying $PROFILE"
    bash "$HERE/netem_apply.sh" "$PROFILE" || echo "netem_watch: apply failed (will retry on the next change)" >&2
    last=$cur
  fi
  sleep 0.5
done
