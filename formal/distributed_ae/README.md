# formal/distributed_ae — model of the real reconciliation protocol (audit 07)

`DIB_AE.tla` models the protocol of `code/src/dib/registry/distributed/service.py` (HEAD `b17cbab`):
state commit, direct delivery, outbox with latest-wins, `GET /pending` (rows + `current`), apply, ack
(per pair or delete-all), re-pull, state-based anti-entropy, site partitions, the D19 loss window.
It does not replace `formal/distributed/` (frozen: `verify_artifact.py` reads its logs).

**Status of this commit: nothing was run** (neither SANY nor TLC). Hypotheses are in the comments
of the module and of each `.cfg`; the run matrix and the reasoning are in `docs/audit/07_modello_ae.md`.
Results hold only within the bounds of each cfg (`MaxEvents`, `MaxLoss`, `MaxToggles`, 2 sites,
1 or 2 facts).

## Running (only with explicit permission, one run at a time)
TLC jar (not in the repo): sha256 `237332bdcc79a35c7d26efa7b82c77c85c2744591c5598673a8a45085ff2a4fb`,
build `2026-05-26T23:53:34Z` (TLC2 `2026.05.26.235334`). Same invocation as `scripts/run_formal.py`:

    tmp=$(mktemp -d); cp DIB_AE.tla <cfg> "$tmp"; cd "$tmp"
    java -Xmx4g -cp <tla2tools.jar> tlc2.TLC -workers 4 -metadir "$tmp/states" -config <cfg> DIB_AE.tla

Logs go to `logs/<cfg>.log` (new names, never the existing `formal/logs/`).

## Configurations
`s0_smoke` (semantics check) · `v0_conv`, `v0_outbox`, `v0_lag`, `v0_2facts_outbox` (D12) ·
`v1_conv`, `v1_lag` (D19), `v1_noloss`, `v1b_noreread` (controls) · `v2a`, `v2a_2facts`, `v2b_loss`,
`v2b_window` (with anti-entropy) · `v3_conv`, `v3_outbox` (masking) · `mut_ae1..5` (mutations by
constant flag) · `neg_nofairness` (the liveness must not be vacuous).
