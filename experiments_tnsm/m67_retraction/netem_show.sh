#!/usr/bin/env bash
# Read-only: prints the egress qdisc of every container of the dibtnsm project, validated by the same guard as
# netem_apply.sh (label AND exact name). Needs sudo only for nsenter. Prints nothing if no container exists.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/netem_common.sh"
if ! docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}}' | grep -q .; then
  echo "no running container in project $PROJECT (no namespace, therefore no netem)"
  exit 0
fi
load_entries
while read -r name pid; do
  printf '%s: ' "$name"; nsenter -t "$pid" -n tc qdisc show dev eth0 | head -1
done <<< "$ENTRIES"
