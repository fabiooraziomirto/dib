# B1 analysis, profile `lan` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-bf272e8`, seed 20261014)
started 2026-10-11T09:30:29.530666+00:00, finished 2026-10-11T09:34:20.464312+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 10 | 0  | 72.20 [67.86; 85.03] (n=10) | 70.38 [66.32; 83.33] (n=10) | 1.70, 2.09 | 0.036 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| C | 10 | 10 | 0  | 24.34 [23.69; 26.48] (n=10) | 20.19 [18.50; 22.81] (n=10) | 4.24, 6.05 | 0.124 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |
| D | 1 | 10 | 0  | 52.98 [49.37; 57.56] (n=10) | 50.94 [47.74; 55.88] (n=10) | 1.76, 2.71 | 0.049 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 21.43 [19.83; 22.80] (n=10) | 18.41 [17.87; 20.18] (n=10) | 2.91, 4.51 | 0.136 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |

## Exclusions by cause (all cells)

| arm | FANOUT | client_timeout | queues_not_empty_at_start | transport_error_setup | transport_error_measured | flagged by discard rule |
|---|---|---|---|---|---|---|
| C | 1 | 0 | 0 | 0 | 0 | False |
| C | 10 | 0 | 0 | 0 | 0 | False |
| D | 1 | 0 | 0 | 0 | 0 | False |
| D | 10 | 0 | 0 | 0 | 0 | False |

## Background and discard rule (other_cores > 1.0 or steal_pct > 2.0 flags a cell)

| arm | FANOUT | other_cores | steal_pct | flagged | generator proc cores mean/max | host busy % mean | near saturation |
|---|---|---|---|---|---|---|---|
| C | 1 | 0.1099 | 0.01 | False | 0.061/0.339 | 7.1 | False |
| C | 10 | 0.1091 | 0.016 | False | 0.068/0.488 | 7.8 | False |
| D | 1 | 0.1499 | 0.01 | False | 0.043/0.120 | 7.2 | False |
| D | 10 | 0.075 | 0.01 | False | 0.044/0.120 | 7.3 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 1.31 | 3.51 | True | None | False |
| C | 10 | 1.28 | 3.92 | True | None | False |
| D | 1 | 1.05 | 1.45 | True | True | False |
| D | 10 | 1.04 | 1.49 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) at `lan` (self-reference, degenerate)

| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x own median ms | threshold ms | verdict |
|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 70.38 [66.32; 83.33] (n=10) | 3.00 | 211.14 | 214.14 | not falsified |
| C | 10 | dispute-rtt | 24.34 [23.69; 26.48] (n=10) | 0.30 | 73.01 | 73.31 | not falsified |
| D | 1 | P-log-apply | 50.94 [47.48; 55.88] (n=10) | 2.00 | 152.82 | 154.82 | not falsified |
| D | 10 | dispute-rtt | 21.43 [19.83; 22.80] (n=10) | 0.20 | 64.30 | 64.50 | not falsified |

**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict carries no information.

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), last-site P-log: C - D = 19.44 ms [11.96; 31.17] -> CI crosses a bound of [15, 32]: criterio ambiguo, non conclusivo (point estimate inside the interval)
- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), dispute-rtt: C - D = 19.22 ms [11.31; 29.66]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 1.78 ms [-0.42; 4.53]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 2.90 ms [1.40; 5.56]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
