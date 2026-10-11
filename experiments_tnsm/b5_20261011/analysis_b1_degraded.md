# B1 analysis, profile `degraded` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-244f1d0`, seed 20261014)
started 2026-10-11T16:50:02.157210+00:00, finished 2026-10-11T18:11:22.505647+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 50 | 0  | 19578.37 [18774.34; 21132.53] (n=50) | 18516.02 [16816.64; 19702.65] (n=40) | 402.82, 3502.70 | 0.000 (accepted) | P-log-apply | 12/3/9 | 12/1 |
| C | 10 | 50 | 4 {'transport_error_setup': 4} | 4283.88 [3634.18; 4681.23] (n=46) | 2825.76 [2820.40; 2982.85] (n=38) | 856.44, 3525.66 | 0.001 (accepted) | P-log-apply | 9/9/0 | 9/1 |
| D | 1 | 50 | 0  | 11117.11 [10577.48; 12578.28] (n=50) | 10315.72 [9982.63; 11174.04] (n=46) | 403.12, 2208.12 | 0.000 (accepted) | P-log-apply | 4/1/3 | 4/1 |
| D | 10 | 50 | 0  | 2827.96 [2423.50; 3048.98] (n=50) | 1639.29 [1617.69; 2019.62] (n=49) | 655.66, 4063.13 | 0.002 (accepted) | P-log-apply | 1/1/0 | 1/1 |

## Exclusions by cause (all cells)

| arm | FANOUT | client_timeout | queues_not_empty_at_start | transport_error_setup | transport_error_measured | flagged by discard rule |
|---|---|---|---|---|---|---|
| C | 1 | 0 | 0 | 0 | 0 | False |
| C | 10 | 0 | 0 | 4 | 0 | False |
| D | 1 | 0 | 0 | 0 | 0 | False |
| D | 10 | 0 | 0 | 0 | 0 | False |

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

## Background and discard rule (other_cores > 1.0 or steal_pct > 2.0 flags a cell)

| arm | FANOUT | other_cores | steal_pct | flagged | generator proc cores mean/max | host busy % mean | near saturation |
|---|---|---|---|---|---|---|---|
| C | 1 | 0.2624 | 0.01 | False | 0.007/0.200 | 2.7 | False |
| C | 10 | 0.2515 | 0.016 | False | 0.012/0.170 | 3.2 | False |
| D | 1 | 0.1757 | 0.016 | False | 0.006/0.050 | 2.8 | False |
| D | 10 | 0.1607 | 0.01 | False | 0.009/0.040 | 3.3 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 203.80 | 608.15 | True | None | False |
| C | 10 | 202.40 | 606.65 | True | None | False |
| D | 1 | 203.18 | 403.32 | True | True | False |
| D | 10 | 203.30 | 403.29 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) with the adjacent `lan` reference (higher median over: b5_20261011/lan_before, b5_20261011/lan_after)

| arm | FANOUT | measure | median ms [CI] | 10 x n_RTT x R (FANOUT 1) / n_RTT x R ms | reference lan median ms | threshold ms | excess over threshold ms | verdict |
|---|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 18516.02 [16816.64; 19702.65] (n=40) | 12000.0 | 81.86 (b5_20261011/lan_before) | 12245.6 | 6270.4 | falsified |
| C | 10 | P-log-apply | 2825.76 [2820.40; 2982.85] (n=38) | 1200.0 | 20.57 (b5_20261011/lan_after) | 1261.7 | 1564.1 | falsified |
| D | 1 | P-log-apply | 10315.72 [9872.00; 11174.04] (n=46) | 8000.0 | 44.72 (b5_20261011/lan_after) | 8134.2 | 2181.6 | falsified |
| D | 10 | P-log-apply | 1639.29 [1617.69; 2019.62] (n=49) | 800.0 | 19.86 (b5_20261011/lan_before) | 859.6 | 779.7 | falsified |

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4 is registered for `lan` only: not applicable here; descriptive), last-site P-log: C - D = 8200.30 ms [6339.17; 9265.09]
- FANOUT 1 (P-a4 is registered for `lan` only: not applicable here; descriptive), dispute-rtt: C - D = 8461.26 ms [6845.88; 10255.78]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 1186.47 ms [803.94; 1312.88]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 1455.91 ms [806.25; 2004.22]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
