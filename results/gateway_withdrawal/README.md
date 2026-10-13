# Withdrawal end to end to the OpenWrt/osMUD gateway (t0–t3)

Pre-registered in `docs/audit/121`, results in `docs/audit/122` (smoke on the final service: `docs/audit/127` §1). Per profile: `summary.json` (hypothesis checks and quantiles with order-statistic CIs), `episodes.csv` (one row per episode), `table.md`, `manifest.json` (commit, hashes of `service.py` inside the 11 containers at start and end, netem as applied, router file hashes, load average). Raw probes and polls: `experiments_tnsm/gateway_withdrawal_20261013/`.

Service: `3ffa57ee…` for lan/wan/degraded (before the target-state guard of audit 126, which changes no valid transition); `smoke_83d8c99a/` repeats 5 episodes per profile on `83d8c99a…` (medians within 1 %). mTLS between services; MUD files unsigned (osMUD `-i`).

| Profile | episodes | t1 site invalidated | t3 new connections refused | t2 policy installed |
|---|---|---|---|---|
| lan | 100 (+10 veto) | 24 ms | 0.38 s | 5.49 s (p95 5.54) |
| wan (80 ms, 1 % on the evidence link) | 50 | 0.42 s | 0.77 s | 5.88 s |
| degraded (200 ms, 5 %) | 50 | 1.02 s | 1.40 s | 6.50 s |

All episodes complete. Established connections never cut (conntrack). Unrelated authorized flow refused ~5.1 s per osMUD restart. Restore alone never re-enabled access; a fresh commit did; vetoes survived. One host (LXC, shared); not comparable with node timings.
