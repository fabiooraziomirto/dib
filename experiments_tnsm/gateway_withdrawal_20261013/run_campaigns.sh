#!/bin/sh
# Gateway campaigns of audit 121, one at a time on this host, in the pre-registered order.
# Usage: run_campaigns.sh <pki_base_dir_outside_repo> <n_degraded>
set -u
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PY=/opt/conda/envs/dib312/bin/python
PKI=$1
NDEG=${2:-50}
export PYTHONDONTWRITEBYTECODE=1
$PY "$HERE/gateway_bench.py" --out "$HERE/lan_mtls" --pki "$PKI/lan" --profile lan --episodes 100 --veto-episodes 10 --window 15
$PY "$HERE/gateway_bench.py" --out "$HERE/wan_mtls" --pki "$PKI/wan" --profile wan --episodes 50 --window 15
$PY "$HERE/gateway_bench.py" --out "$HERE/degraded_mtls" --pki "$PKI/degraded" --profile degraded --episodes "$NDEG" --window 15
echo "campaigns finished"
