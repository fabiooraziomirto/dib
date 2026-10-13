# Restoration-policy ablation — evaluated service

`results.json`: 18 deterministic cases (3 policies × 3 veto times × full delivery / site-2 missing the episode) produced by `code/scripts/v36_restore_ablation.py` (unchanged, sha `8387487e…`) on `service.py` `83d8c99a…` (audit 126). Provenance and the loaded module's hash: `manifest.json`. Traces are identical field by field to the run on `3ffa57ee…` (audit 120) and to the historical run on `31863043…` (`historical_31863043/`, with its original README describing the design of the alternatives).

| Policy | Subject ACEs without a fresh commit | Vetoes preserved |
|---|---|---|
| Persistent approval | 12/18 | 6/6 |
| Blanket review reset | 0/18 | 0/6 |
| DIB | 0/18 | 6/6 |

Counts of controlled cases, not failure rates. Reproduce: `PYTHONPATH=code/src python3 experiments_tnsm/lifecycle_rerun_20261013/run.py --out <dir>`.
