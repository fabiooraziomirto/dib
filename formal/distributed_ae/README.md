# formal/distributed_ae — model of the real reconciliation protocol (audit 07)

`DIB_AE.tla` models the protocol of `code/src/dib/registry/distributed/service.py` (HEAD `b17cbab`):
state commit, direct delivery, outbox with latest-wins, `GET /pending` (rows + `current`), apply, ack
(per pair or delete-all), re-pull, state-based anti-entropy, site partitions, the D19 loss window.
It does not replace `formal/distributed/` (frozen: `verify_artifact.py` reads its logs).

**Status:** SANY clean; TLC runs are listed in `docs/audit/07_modello_ae.md` ("Esecuzioni"); the first `s0_smoke` run falsified a property as written (fixed in `a8dd759`). Hypotheses are in the comments
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

## Declared limits and conventions
- **Reporters** are abstract identifiers (`Reporters = {r1, r2}`), separate from the sites, as in the tests
  (`rep-a`, `rep-b`). With 2 sites this covers most of the D12 space, including a lagging site that is **not** a
  reporter; the case with **three real sites** is NOT covered by the main configurations, only by the robustness
  runs `v0_3sites_conv` and `v1_3sites_conv`.
- **One network flag.** `unreachable` = evidence -> site direction only (used in `Deliver`); the site's pull never
  depends on it, but the fairness on the site's run steps is conditional on `t \notin unreachable`: conservative
  (weaker liveness than the code, where a partitioned-but-alive site keeps pulling). A stopped process (no trigger)
  is out of guarantee and is modelled as unreachable for ever. Separating delivery and pull flags is a later option.
  `./check_consistency.sh` checks textually that the reconcile run does not mention `unreachable` and that the
  fairness is the declared one.
- **Symmetry** is not used. It may be used only in safety-only runs (never with temporal properties) and only after
  comparing one run with and without it for the same outcome.
- **Logs** in `logs/` are ignored by `.gitignore` (`*.log`): add them with `git add -f`, as for `formal/logs/`.
- **Memory** is measured on the JVM process (`pgrep -x java`), not on the `timeout` wrapper.
- E1 (surrogate of the `T+J+2*d_run` bound) is out of the first cycle.
