#!/bin/sh
# Smoke gateway on 83d8c99a (audit 126 addendum 1), then the site sweep (audit 123): one campaign at a time.
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PY=/opt/conda/envs/dib312/bin/python
PKI=$1
export PYTHONDONTWRITEBYTECODE=1
G=$ROOT/experiments_tnsm/gateway_withdrawal_20261013
for p in lan wan degraded; do
  $PY $G/gateway_bench.py --out $G/smoke_83d8c99a_$p --pki $PKI/smoke_$p --profile $p --episodes 5 --window 15
done
S=$ROOT/experiments_tnsm/site_sweep_20261013
$PY $S/sweep.py --out $S/http --transport http
$PY $S/sweep.py --out $S/mtls --transport mtls --pki $PKI/sweep_mtls
echo "all finished"
