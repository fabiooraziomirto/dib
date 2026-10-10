#!/usr/bin/env bash
# M6xM7 (plan rev. 5, Passo 4-5; audit 14): per-container netem for the dibtnsm compose
# project. Supersedes experiments_tnsm/m7_netem/ (one namespace for all services, so the
# evidence<->site fan-out never crossed the emulated link). PREPARED; the user runs it with
# sudo on the node 192.168.100.57 only.
#
# Each container of the compose project "dibtnsm" (and ONLY those: guard on the label
# com.docker.compose.project=dibtnsm) gets a netem qdisc on the egress of its own eth0,
# inside its own network namespace (nsenter -t <pid> -n). A packet from X to Y crosses
# only X's egress qdisc, so evidence<->site RTT = 2d and round-trip loss ~ 2p.
# Nothing is applied in the root namespace (generator/oracle there: RTT generator<->service = d).
#
# Usage:  sudo ./netem_apply.sh [--dry-run] <profile> [<site-index>]
#   lan        no qdisc on any container (removes existing ones)
#   regional   every container: delay 20ms loss 0.1%
#   wan        every container: delay 80ms loss 1%
#   degraded   every container: delay 200ms loss 5%
#   extreme    every container: delay 550ms (no loss)            [to be confirmed]
#   mixed      evidence none; sites 0-4 none; sites 5-9 delay 80ms loss 1%
#   partition  site <site-index> only: loss 100% (asymmetric: its egress); others unchanged
set -euo pipefail

PROJECT=dibtnsm
DRY=0
run() { if [[ $DRY == 1 ]]; then echo "+ $*"; else "$@"; fi; }
die() { echo "netem_apply: $*" >&2; exit 1; }
export PATH=/snap/bin:$PATH   # the node's /usr/bin/docker lacks compose; same daemon

[[ ${1:-} == --dry-run ]] && { DRY=1; shift; }
PROFILE=${1:-}; SITE=${2:-}
[[ -n $PROFILE ]] || die "usage: $0 [--dry-run] lan|regional|wan|degraded|extreme|mixed|partition [site]"
[[ $DRY == 1 || $EUID == 0 ]] || die "must run as root (sudo)"

containers() {  # name pid, only containers of the project
  docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}}' | sort |
  while read -r name; do
    proj=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$name")
    [[ $proj == "$PROJECT" ]] || die "refusing container $name (project '$proj')"
    echo "$name $(docker inspect -f '{{.State.Pid}}' "$name")"
  done
}

set_qdisc() {  # pid "netem args" | ""
  local pid=$1 args=$2
  [[ $pid =~ ^[0-9]+$ && $pid -gt 1 ]] || die "bad pid '$pid'"
  run nsenter -t "$pid" -n tc qdisc del dev eth0 root 2>/dev/null || true
  [[ -z $args ]] || run nsenter -t "$pid" -n tc qdisc add dev eth0 root netem $args
}

profile_args() {  # container-name -> netem args for the profile
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

found=0
while read -r name pid; do
  [[ -n ${name:-} ]] || continue
  found=1
  args=$(profile_args "$name")
  [[ $args == KEEP ]] && continue
  echo "$name (pid $pid): ${args:-no qdisc}"
  set_qdisc "$pid" "$args"
done < <(containers)
[[ $found == 1 ]] || die "no running container in project $PROJECT"
