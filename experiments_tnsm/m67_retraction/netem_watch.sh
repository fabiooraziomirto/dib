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
# Corrections of 2026-10-10 (user review): (1) `last` is updated only if the apply succeeded, a failed apply is retried at
# the next poll; (2) if the cleanup on Ctrl-C fails, a loud warning on stderr and exit status 1; (3) the signature
# includes the pid of every expected container (compose kill/start keeps the ID but creates a new namespace), read with
# ONE `docker inspect -f '{{.State.Pid}}' <expected names>` and only for names matching the expected pattern;
# (4) `--poll S` (use 0.1 in B2-kill blocks, 0.5 default for B1); millisecond timestamps for "changed" and "applied",
# which the driver joins to the container restarts (run.py parse_watch_log).
#
# Usage: sudo ./netem_watch.sh [--poll S] <profile>   profiles as in netem_apply.sh
#        ./netem_watch.sh --dry-run <profile>         prints what it would do once; applies nothing
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/netem_common.sh"
DRY=0
POLL=${NETEM_WATCH_POLL:-0.5}
while [[ ${1:-} == --* ]]; do
  case $1 in
    --dry-run) DRY=1; shift;;
    --poll) POLL=${2:-}; shift 2 || die "--poll needs a value";;
    *) die "unknown option $1";;
  esac
done
[[ $POLL =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk "BEGIN{exit !($POLL >= 0.05)}" || die "bad poll interval '$POLL' (seconds, >= 0.05)"
PROFILE=${1:-}
[[ -n $PROFILE ]] || die "usage: $0 [--dry-run] <profile>"
[[ $PROFILE != partition ]] || die "'partition' is not supported"
[[ $DRY == 1 || $EUID == 0 ]] || die "must run as root (sudo)"

ts() { date -u +%FT%T.%3NZ; }
signature() {  # "<id> <name>" lines, then "pid <name> <pid>" lines for the expected names only; non-zero if docker fails
  local psout id n pids i
  local -a names=()
  psout=$(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.ID}} {{.Names}}' | sort) || return 1
  while read -r id n; do
    [[ -n ${n:-} && $n =~ $EXPECTED_RE ]] && names+=("$n")
  done <<< "$psout"
  echo "$psout"
  if (( ${#names[@]} )); then
    pids=$(docker inspect -f '{{.State.Pid}}' "${names[@]}") || return 1   # a container vanished meanwhile: no signature this poll
    i=0
    while read -r id; do echo "pid ${names[$i]} $id"; i=$((i + 1)); done <<< "$pids"
  fi
}

if [[ $DRY == 1 ]]; then
  echo "netem_watch (dry run): profile=$PROFILE; containers of project $PROJECT right now (by name):"
  signature | awk '{print $2}' | sort | sed 's/^/  /'
  bash "$HERE/netem_apply.sh" --dry-run "$PROFILE" || true
  exit 0
fi

cleanup() {
  trap '' INT TERM
  echo "$(ts) netem_watch: stopping, removing the qdisc of the dibtnsm containers" >&2
  if bash "$HERE/netem_apply.sh" lan; then
    echo "$(ts) netem_watch: cleanup done" >&2
    exit 0
  fi
  echo "$(ts) ATTENZIONE: pulizia netem NON riuscita, verifica con netem_show.sh" >&2
  exit 1
}
trap cleanup INT TERM

last=""; fails=0
echo "$(ts) netem_watch: profile=$PROFILE, polling every ${POLL}s (Ctrl-C to stop and clean)"
while true; do
  if cur=$(signature) && [[ -n $cur ]] && [[ $cur != "$last" ]]; then
    (( fails )) || echo "$(ts) netem_watch: containers changed -> applying $PROFILE"
    t0=$(date +%s.%N)
    if bash "$HERE/netem_apply.sh" "$PROFILE" >/dev/null; then
      last=$cur; fails=0
      printf '%s netem_watch: applied %s (%.3f s)\n' "$(ts)" "$PROFILE" "$(awk "BEGIN{print $(date +%s.%N) - $t0}")"
    else
      fails=$((fails + 1))
      if (( fails == 1 || fails % 20 == 0 )); then
        echo "$(ts) netem_watch: apply FAILED (attempt $fails), retrying every ${POLL}s" >&2
      fi
    fi
  fi
  sleep "$POLL"
done
