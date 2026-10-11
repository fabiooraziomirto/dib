# B5 analysis, (a') at `degraded` (audits 46, 50); tree `/home/ubuntu/dib_tnsm/tree-244f1d0`, seed 20261014, started 2026-10-11T16:50:02.157210+00:00

| arm | FANOUT | measure | n completed | median ms [CI] | physical bound ms | threshold ms (p hi) | threshold ms (p lo, descriptive) | verdict 1 | verdict 2 |
|---|---|---|---|---|---|---|---|---|---|
| C | 1 | last | 40 | 18516.02 [16816.64; 19702.65] (n=40) | 12000.0 | 12871.9 | 12666.3 | falsified | ok |
| C | 10 | last | 38 | 2825.76 [2820.40; 2981.58] (n=38) | 1200.0 | 1888.0 | 1682.5 | falsified | ok |
| D | 1 | last | 46 | 10315.72 [9872.00; 11174.04] (n=46) | 8000.0 | 8422.8 | 8359.7 | falsified | ok |
| D | 10 | last | 49 | 1639.29 [1617.69; 2019.62] (n=49) | 800.0 | 1148.2 | 1085.1 | falsified | ok |

**Global (audit 46/50):** (a') falsified (4/4 cells); base model ok (0/4 cells); cells not evaluable (R-gp): 0.
Statute: replication on the same node and profile as the block that falsified (a); not an independent test.

## Exclusion by overlap with an unsettled netem profile (cause `profile_incoherent_overlap`)

Excluded episodes per cell: C/1: 0, C/10: 0, D/1: 0, D/10: 0

Intervals overlapping the block's time range, verbatim (UTC):

- watch2.log: 17:07:10.149 → 17:07:11.575
- watch2.log: 17:07:12.154 → 17:07:13.282
- watch2.log: 17:07:22.335 → 17:07:22.570
- watch2.log: 17:07:32.218 → 17:07:32.259
- watch2.log: 17:07:34.909 → 17:07:36.112
- watch2.log: 17:07:36.672 → 17:07:40.750
- watch2.log: 17:27:44.550 → 17:27:44.587
- watch2.log: 17:27:47.243 → 17:27:53.364
- watch2.log: 17:58:05.633 → 17:58:06.825
- watch2.log: 17:58:07.415 → 17:58:10.391
- watch2.log: 17:58:11.244 → 17:58:11.570
- watch2.log: 17:58:12.426 → 17:58:12.679
- watch2.log: 17:58:13.241 → 17:58:13.481
- watch2.log: 17:58:22.921 → 17:58:22.959
- watch2.log: 17:58:25.619 → 17:58:25.828
- watch2.log: 17:58:26.384 → 17:58:26.791
- watch2.log: 17:58:27.348 → 17:58:31.452
