#!/usr/bin/env bash
# Show the egress qdisc of every container of the dibtnsm project (read-only; needs sudo for
# nsenter). Used after each netem_apply.sh to verify the profile actually applied.
set -euo pipefail
export PATH=/snap/bin:$PATH
docker ps --filter "label=com.docker.compose.project=dibtnsm" --format '{{.Names}}' | sort | while read -r name; do
  pid=$(docker inspect -f '{{.State.Pid}}' "$name")
  printf '%s: ' "$name"; nsenter -t "$pid" -n tc qdisc show dev eth0 | head -1
done
