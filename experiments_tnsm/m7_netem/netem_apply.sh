#!/usr/bin/env bash
# M7 (audit 04): emulated network profiles for S7. PREPARED, NOT RUN: the user reviews it
# and runs it with sudo on the free node (192.168.100.57) only.
#
# Safety rules (user decision): netem only inside a dedicated network namespace on a
# dedicated veth pair; never on lo, never on a shared interface (ens18, docker0, cni0,
# flannel.1, tailscale0, tun0, ...). The script refuses any other device name.
#
#   veth-dib-h (root namespace, 10.203.0.1/30) <--> veth-dib-n (netns dibnet, 10.203.0.2/30)
#
# The DIB services under test run inside "dibnet" (ip netns exec dibnet ...) and the load
# generator reaches them at 10.203.0.2 through veth-dib-h, so every packet of the
# experiment crosses the emulated link and nothing else does.
#
# Usage:  sudo ./netem_apply.sh [--dry-run] <profile>
# Profiles (plan sez. 7.5): lan | regional | wan | degraded | partition-to-ns | partition-from-ns
#   lan            no qdisc (baseline; only creates the namespace and the veth pair)
#   regional       delay 20ms, loss 0.1%   (both directions)
#   wan            delay 80ms, loss 1%     (both directions)
#   degraded       delay 200ms, loss 5%    (both directions)
#   partition-to-ns    drop 100% host -> namespace only (asymmetric partition)
#   partition-from-ns  drop 100% namespace -> host only (asymmetric partition)
# Delay is applied per direction, so the RTT added is twice the value above.
set -euo pipefail

NS=dibnet
HOST_IF=veth-dib-h
NS_IF=veth-dib-n
HOST_IP=10.203.0.1/30
NS_IP=10.203.0.2/30
DRY=0

run() { if [[ $DRY == 1 ]]; then echo "+ $*"; else "$@"; fi; }
die() { echo "netem_apply: $*" >&2; exit 1; }

guard_dev() {  # the only devices this script may ever touch
  case "$1" in
    "$HOST_IF"|"$NS_IF") ;;
    *) die "refusing to touch device '$1' (only $HOST_IF / $NS_IF)";;
  esac
}

[[ ${1:-} == --dry-run ]] && { DRY=1; shift; }
PROFILE=${1:-}
[[ -n $PROFILE ]] || die "usage: $0 [--dry-run] lan|regional|wan|degraded|partition-to-ns|partition-from-ns"
[[ $DRY == 1 || $EUID == 0 ]] || die "must run as root (sudo)"
[[ $DRY == 1 ]] || modprobe -n sch_netem >/dev/null || die "sch_netem not available"

# namespace + veth pair (idempotent)
if ! ip netns list 2>/dev/null | grep -qw "$NS" || [[ $DRY == 1 ]]; then
  run ip netns add "$NS"
fi
if ! ip link show "$HOST_IF" >/dev/null 2>&1 || [[ $DRY == 1 ]]; then
  guard_dev "$HOST_IF"; guard_dev "$NS_IF"
  run ip link add "$HOST_IF" type veth peer name "$NS_IF"
  run ip link set "$NS_IF" netns "$NS"
  run ip addr add "$HOST_IP" dev "$HOST_IF"
  run ip link set "$HOST_IF" up
  run ip netns exec "$NS" ip addr add "$NS_IP" dev "$NS_IF"
  run ip netns exec "$NS" ip link set "$NS_IF" up
  run ip netns exec "$NS" ip link set lo up   # loopback INSIDE the namespace only, no qdisc on it
fi

qdisc_host() { guard_dev "$HOST_IF"; run tc qdisc replace dev "$HOST_IF" root netem "$@"; }
qdisc_ns()   { guard_dev "$NS_IF";   run ip netns exec "$NS" tc qdisc replace dev "$NS_IF" root netem "$@"; }

case "$PROFILE" in
  lan) ;;
  regional) qdisc_host delay 20ms loss 0.1%; qdisc_ns delay 20ms loss 0.1% ;;
  wan)      qdisc_host delay 80ms loss 1%;   qdisc_ns delay 80ms loss 1% ;;
  degraded) qdisc_host delay 200ms loss 5%;  qdisc_ns delay 200ms loss 5% ;;
  partition-to-ns)   qdisc_host loss 100% ;;
  partition-from-ns) qdisc_ns loss 100% ;;
  *) die "unknown profile '$PROFILE'";;
esac

echo "netem_apply: profile=$PROFILE applied (dry-run=$DRY)"
run tc qdisc show dev "$HOST_IF"
run ip netns exec "$NS" tc qdisc show dev "$NS_IF"
