# B1 analysis, profile `degraded` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-244f1d0`, seed 20261014)
started 2026-10-11T13:19:19.914620+00:00, finished 2026-10-11T14:39:15.320963+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 50 | 2 {'transport_error_setup': 2} | 19574.41 [17316.84; 20536.78] (n=48) | 17022.36 [15615.42; 19323.99] (n=31) | 402.90, 2718.01 | 0.000 (accepted) | P-log-apply | 18/7/11 | 18/1 |
| C | 10 | 50 | 2 {'transport_error_setup': 2} | 4327.94 [4083.38; 4758.17] (n=48) | 2824.58 [2422.25; 3418.70] (n=35) | 909.89, 4113.61 | 0.001 (accepted) | P-log-apply | 14/14/0 | 14/1 |
| D | 1 | 50 | 3 {'client_timeout': 1, 'transport_error_setup': 2} | 11468.47 [10770.56; 12084.74] (n=47) | 10669.83 [9769.59; 11177.69] (n=41) | 403.26, 2208.98 | 0.000 (accepted) | P-log-apply | 6/2/4 | 6/1 |
| D | 10 | 50 | 1 {'transport_error_setup': 1} | 2829.26 [2425.48; 3329.44] (n=49) | 2016.77 [1621.25; 2019.21] (n=46) | 403.86, 2711.42 | 0.001 (accepted) | P-log-apply | 3/3/0 | 3/1 |

## Exclusions by cause (all cells)

| arm | FANOUT | client_timeout | queues_not_empty_at_start | transport_error_setup | transport_error_measured | flagged by discard rule |
|---|---|---|---|---|---|---|
| C | 1 | 0 | 0 | 2 | 0 | False |
| C | 10 | 0 | 0 | 2 | 0 | False |
| D | 1 | 1 | 0 | 2 | 0 | False |
| D | 10 | 0 | 0 | 1 | 0 | False |

## Exclusion by overlap with an unsettled netem profile (cause `profile_incoherent_overlap`)

Excluded episodes per cell: C/1: 0, C/10: 0, D/1: 0, D/10: 0

Intervals overlapping the block's time range, verbatim (UTC):

- watch2.log: 13:37:20.539 → 13:37:21.681
- watch2.log: 13:37:22.243 → 13:37:23.281
- watch2.log: 13:37:32.618 → 13:37:32.857
- watch2.log: 13:37:42.516 → 13:37:42.551
- watch2.log: 13:37:45.204 → 13:37:45.453
- watch2.log: 13:37:46.003 → 13:37:51.030
- watch2.log: 13:56:42.062 → 13:56:42.108
- watch2.log: 13:56:44.773 → 13:56:45.106
- watch2.log: 13:56:45.659 → 13:56:50.877
- watch2.log: 14:26:16.868 → 14:26:17.945
- watch2.log: 14:26:18.513 → 14:26:19.583
- watch2.log: 14:26:29.054 → 14:26:29.243
- watch2.log: 14:26:41.696 → 14:26:47.853

## Background and discard rule (other_cores > 1.0 or steal_pct > 2.0 flags a cell)

| arm | FANOUT | other_cores | steal_pct | flagged | generator proc cores mean/max | host busy % mean | near saturation |
|---|---|---|---|---|---|---|---|
| C | 1 | 0.1741 | 0.026 | False | 0.007/0.200 | 2.6 | False |
| C | 10 | 0.1691 | 0.01 | False | 0.012/0.200 | 2.9 | False |
| D | 1 | 0.1624 | 0.016 | False | 0.006/0.050 | 2.7 | False |
| D | 10 | 0.1699 | 0.016 | False | 0.009/0.050 | 3.1 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 203.02 | 607.57 | True | None | False |
| C | 10 | 202.93 | 607.81 | True | None | False |
| D | 1 | 202.95 | 404.32 | True | True | False |
| D | 10 | 203.66 | 403.78 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) with the adjacent `lan` reference (higher median over: experiments_tnsm/m67_retraction/block_lan_before_20261011/lan_before, experiments_tnsm/m67_retraction/block_degraded_lan_after_20261011/lan_after)

| arm | FANOUT | measure | median ms [CI] | 10 x n_RTT x R (FANOUT 1) / n_RTT x R ms | reference lan median ms | threshold ms | excess over threshold ms | verdict |
|---|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 17022.36 [15615.42; 19323.99] (n=31) | 12000.0 | 80.04 (experiments_tnsm/m67_retraction/block_degraded_lan_after_20261011/lan_after) | 12240.1 | 4782.3 | falsified |
| C | 10 | P-log-apply | 2824.58 [2422.25; 3418.70] (n=35) | 1200.0 | 22.46 (experiments_tnsm/m67_retraction/block_lan_before_20261011/lan_before) | 1267.4 | 1557.2 | falsified |
| D | 1 | P-log-apply | 10669.83 [9769.59; 11177.69] (n=41) | 8000.0 | 48.76 (experiments_tnsm/m67_retraction/block_degraded_lan_after_20261011/lan_after) | 8146.3 | 2523.5 | falsified |
| D | 10 | P-log-apply | 2016.77 [1621.25; 2019.21] (n=46) | 800.0 | 20.71 (experiments_tnsm/m67_retraction/block_lan_before_20261011/lan_before) | 862.1 | 1154.6 | falsified |

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4 is registered for `lan` only: not applicable here; descriptive), last-site P-log: C - D = 6352.54 ms [4856.69; 8852.73]
- FANOUT 1 (P-a4 is registered for `lan` only: not applicable here; descriptive), dispute-rtt: C - D = 8105.93 ms [5762.65; 9097.56]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 807.81 ms [406.13; 1402.90]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 1498.67 ms [902.86; 2163.20]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
