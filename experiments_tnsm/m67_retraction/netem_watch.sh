#!/usr/bin/env bash
# netem_watch.sh (PREPARED, NOT RUN; to be run BY THE USER with sudo, in a visible terminal, for the duration of ONE
# block, and stopped by the user with Ctrl-C at the end of the block).
#
# Why: netem lives in each container's network namespace and is destroyed with the container, while the driver
# (run.py) recreates the compose project whenever (arm, FANOUT, T) changes. This script keeps the profile in place.
#
# What it does, and ONLY this:
#   * every poll (0.5 s) it runs `docker ps --filter label=com.docker.compose.project=dibtnsm --format '{{.ID}} {{.Names}}'`
#     and nothing else against docker;
#   * when that list changes (a recreated cluster has new container IDs) it runs netem_apply.sh <profile>, which
#     validates the 11 containers (label AND exact name, see netem_common.sh) and applies
#     `nsenter -t <pid> -n tc qdisc replace dev eth0 root netem ...` in those namespaces and nowhere else;
#   * on Ctrl-C / TERM it runs netem_apply.sh lan, i.e. `tc qdisc del dev eth0 root` in the namespaces of the same
#     validated containers only, then exits.
# No other system command, no `docker network`, no sudoers rule, no daemon: it stops when the user stops it.
# The profile `partition` is not supported here. Poll interval for tests: NETEM_WATCH_POLL (default 0.5).
#
# Usage: sudo ./netem_watch.sh <profile>              profiles as in netem_apply.sh
#        ./netem_watch.sh --dry-run <profile>         prints what it would do once; applies nothing
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/netem_common.sh"
DRY=0
if [[ ${1:-} == --dry-run ]]; then DRY=1; shift; fi
PROFILE=${1:-}
[[ -n $PROFILE ]] || die "usage: $0 [--dry-run] <profile>"
[[ $PROFILE != partition ]] || die "'partition' is not supported"
[[ $DRY == 1 || $EUID == 0 ]] || die "must run as root (sudo)"
POLL=${NETEM_WATCH_POLL:-0.5}

signature() {  # "<id> <name>" of the containers of the project, sorted; the only docker call of the loop
  docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.ID}} {{.Names}}' | sort
}

if [[ $DRY == 1 ]]; then
  echo "netem_watch (dry run): profile=$PROFILE; containers of project $PROJECT right now (by name):"
  signature | awk '{print $2}' | sort | sed 's/^/  /'
  bash "$HERE/netem_apply.sh" --dry-run "$PROFILE" || true
  exit 0
fi

cleanup() {
  echo "$(date -u +%FT%TZ) netem_watch: stopping, removing the qdisc of the dibtnsm containers" >&2
  bash "$HERE/netem_apply.sh" lan || true
  exit 0
}
trap cleanup INT TERM

last=""
echo "$(date -u +%FT%TZ) netem_watch: profile=$PROFILE, polling every ${POLL}s (Ctrl-C to stop and clean)"
while true; do
  cur=$(signature)
  if [[ -n $cur && $cur != "$last" ]]; then
    echo "$(date -u +%FT%TZ) containers changed -> applying $PROFILE"
    bash "$HERE/netem_apply.sh" "$PROFILE" || echo "netem_watch: apply failed (will retry on the next change)" >&2
    last=$cur
  fi
  sleep "$POLL"
done
