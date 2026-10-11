# B1 analysis, profile `lan` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-bf272e8`, seed 20261014)
started 2026-10-11T07:51:49.565235+00:00, finished 2026-10-11T07:56:29.825958+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 10 | 0  | 109.72 [101.75; 120.40] (n=10) | 105.96 [98.69; 117.54] (n=10) | 3.06, 4.70 | 0.024 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| C | 10 | 10 | 0  | 36.44 [35.23; 50.70] (n=10) | 30.61 [29.27; 43.71] (n=10) | 6.29, 8.62 | 0.082 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 1 | 10 | 0  | 70.51 [64.64; 84.49] (n=10) | 67.31 [62.78; 82.06] (n=10) | 2.47, 4.08 | 0.037 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 29.91 [28.21; 35.12] (n=10) | 25.91 [23.85; 30.32] (n=10) | 4.72, 6.04 | 0.096 (accepted) | P-log-apply | 0/0/0 | 0/0 |

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
| C | 1 | 0.2164 | 0.401 | False | 0.064/0.318 | 9.6 | False |
| C | 10 | 0.169 | 0.229 | False | 0.064/0.298 | 9.4 | False |
| D | 1 | 0.2739 | 0.313 | False | 0.047/0.150 | 8.9 | False |
| D | 10 | 0.1482 | 0.359 | False | 0.049/0.160 | 9.3 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 2.37 | 5.63 | True | None | False |
| C | 10 | 2.29 | 5.58 | True | None | False |
| D | 1 | 1.57 | 6.31 | True | False | True |
| D | 10 | 1.66 | 4.25 | True | False | True |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) at `lan` (self-reference, degenerate)

| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x own median ms | threshold ms | verdict |
|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 105.96 [98.69; 117.54] (n=10) | 3.00 | 317.88 | 320.88 | not falsified |
| C | 10 | P-log-apply | 30.61 [29.27; 43.71] (n=10) | 0.30 | 91.83 | 92.13 | not falsified |
| D | 1 | P-log-apply | 67.31 [62.78; 82.06] (n=10) | 2.00 | 201.92 | 203.92 | not falsified |
| D | 10 | P-log-apply | 25.91 [23.85; 30.32] (n=10) | 0.20 | 77.72 | 77.92 | not falsified |

**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict carries no information.

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), last-site P-log: C - D = 38.65 ms [22.85; 49.69] -> CI crosses a bound of [15, 32]: criterio ambiguo, non conclusivo (point estimate outside the interval)
- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), dispute-rtt: C - D = 39.21 ms [22.81; 50.03]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 4.70 ms [0.02; 15.52]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 6.53 ms [1.64; 18.55]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
