# Dispute flood — evaluated service

Five repetitions of `code/scripts/dispute_flood.py --facts 100` (unchanged; 10 sites; plain HTTP, the generator has no mTLS), each on a fresh topology built from the tree, with `service.py` `83d8c99a…` verified inside all 11 containers before and after (`manifest.json`, which also counts HTTP status codes from the containers' access logs: only 200). Per repetition: `dispute_flood_summary_rep{0..4}.json`.

In 5/5: 100/100 disputes applied, exports 100 → 0 ACEs at all ten sites, back to 100 after recovery (11 requests per fact). Median over the repetitions: flood 5.16 s (4.77–5.63); concurrent reads 662 → 228 ops/s, p99 29.4 → 74.5 ms; recovery 23.9 s. Audits 123 (addendum 1) and 127. `historical_v43_import/` is the earlier single run (service version not recorded); do not compare.
