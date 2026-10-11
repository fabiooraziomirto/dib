# B1 analysis, profile `lan` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-244f1d0`, seed 20261014)
started 2026-10-11T13:02:29.699717+00:00, finished 2026-10-11T13:06:30.078311+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 10 | 0  | 76.34 [72.73; 85.16] (n=10) | 74.14 [70.90; 82.07] (n=10) | 2.00, 3.24 | 0.034 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| C | 10 | 10 | 0  | 25.83 [25.09; 29.44] (n=10) | 22.46 [20.29; 23.59] (n=10) | 4.69, 6.62 | 0.111 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |
| D | 1 | 10 | 0  | 47.13 [44.56; 56.72] (n=10) | 45.71 [43.11; 54.78] (n=10) | 1.51, 2.50 | 0.055 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 23.19 [21.52; 24.72] (n=10) | 20.71 [18.92; 22.63] (n=10) | 2.13, 3.71 | 0.121 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |

## Exclusions by cause (all cells)

| arm | FANOUT | client_timeout | queues_not_empty_at_start | transport_error_setup | transport_error_measured | flagged by discard rule |
|---|---|---|---|---|---|---|
| C | 1 | 0 | 0 | 0 | 0 | False |
| C | 10 | 0 | 0 | 0 | 0 | False |
| D | 1 | 0 | 0 | 0 | 0 | False |
| D | 10 | 0 | 0 | 0 | 0 | False |

## Exclusion by overlap with an unsettled netem profile (cause `profile_incoherent_overlap`)

Excluded episodes per cell: C/1: 0, C/10: 0, D/1: 0, D/10: 0

Intervals overlapping the block's time range, verbatim (UTC):

- watch2.log: 13:03:29.082 → 13:03:29.278
- watch2.log: 13:03:38.998 → 13:03:39.030
- watch2.log: 13:03:41.685 → 13:03:41.999
- watch2.log: 13:03:42.548 → 13:03:47.905
- watch2.log: 13:04:28.836 → 13:04:28.868
- watch2.log: 13:04:31.513 → 13:04:37.447
- watch2.log: 13:05:29.501 → 13:05:29.693
- watch2.log: 13:05:39.354 → 13:05:39.387
- watch2.log: 13:05:42.048 → 13:05:48.062

## Background and discard rule (other_cores > 1.0 or steal_pct > 2.0 flags a cell)

| arm | FANOUT | other_cores | steal_pct | flagged | generator proc cores mean/max | host busy % mean | near saturation |
|---|---|---|---|---|---|---|---|
| C | 1 | 0.1582 | 0.005 | False | 0.068/0.438 | 8.8 | False |
| C | 10 | 0.1649 | 0.01 | False | 0.066/0.389 | 9.1 | False |
| D | 1 | 0.169 | 0.01 | False | 0.044/0.120 | 8.4 | False |
| D | 10 | 0.1607 | 0.016 | False | 0.045/0.120 | 8.6 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 1.21 | 4.13 | True | None | False |
| C | 10 | 1.23 | 3.94 | True | None | False |
| D | 1 | 1.06 | 1.68 | True | True | False |
| D | 10 | 1.43 | 1.91 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) at `lan` (self-reference, degenerate)

| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x own median ms | threshold ms | verdict |
|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 74.14 [70.90; 81.95] (n=10) | 3.00 | 222.41 | 225.41 | not falsified |
| C | 10 | dispute-rtt | 25.83 [25.16; 29.44] (n=10) | 0.30 | 77.49 | 77.79 | not falsified |
| D | 1 | P-log-apply | 45.71 [43.11; 54.78] (n=10) | 2.00 | 137.12 | 139.12 | not falsified |
| D | 10 | dispute-rtt | 23.19 [21.52; 24.72] (n=10) | 0.20 | 69.58 | 69.78 | not falsified |

**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict carries no information.

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), last-site P-log: C - D = 28.43 ms [18.18; 37.16] -> CI crosses a bound of [15, 32]: criterio ambiguo, non conclusivo (point estimate inside the interval)
- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), dispute-rtt: C - D = 29.22 ms [18.09; 38.98]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 1.75 ms [-1.60; 4.13]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 2.64 ms [1.05; 6.46]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
