# B1 analysis, profile `lan` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-bf272e8`, seed 20261014)
started 2026-10-11T08:40:04.223001+00:00, finished 2026-10-11T08:44:00.655526+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 10 | 0  | 75.08 [74.18; 79.43] (n=10) | 73.31 [72.20; 77.06] (n=10) | 1.91, 2.70 | 0.034 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| C | 10 | 10 | 0  | 25.92 [24.34; 27.71] (n=10) | 20.88 [20.22; 21.70] (n=10) | 5.32, 7.03 | 0.120 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |
| D | 1 | 10 | 0  | 47.58 [44.07; 50.45] (n=10) | 45.85 [43.11; 48.77] (n=10) | 1.69, 1.99 | 0.055 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 20.69 [19.32; 21.34] (n=10) | 17.82 [16.43; 19.40] (n=10) | 2.62, 3.77 | 0.140 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |

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
| C | 1 | 0.1024 | 0.021 | False | 0.065/0.358 | 7.8 | False |
| C | 10 | 0.1341 | 0.016 | False | 0.070/0.437 | 8.0 | False |
| D | 1 | 0.1333 | 0.01 | False | 0.043/0.120 | 7.4 | False |
| D | 10 | 0.199 | 0.016 | False | 0.042/0.120 | 7.4 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 1.24 | 3.67 | True | None | False |
| C | 10 | 1.35 | 3.82 | True | None | False |
| D | 1 | 0.96 | 1.53 | True | True | False |
| D | 10 | 1.17 | 2.00 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) at `lan` (self-reference, degenerate)

| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x own median ms | threshold ms | verdict |
|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 73.31 [72.20; 77.06] (n=10) | 3.00 | 219.93 | 222.93 | not falsified |
| C | 10 | dispute-rtt | 25.92 [24.34; 27.71] (n=10) | 0.30 | 77.77 | 78.07 | not falsified |
| D | 1 | P-log-apply | 45.85 [43.11; 48.77] (n=10) | 2.00 | 137.54 | 139.54 | not falsified |
| D | 10 | dispute-rtt | 20.69 [19.37; 21.35] (n=10) | 0.20 | 62.07 | 62.27 | not falsified |

**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict carries no information.

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), last-site P-log: C - D = 27.46 ms [25.34; 32.38] -> CI crosses a bound of [15, 32]: criterio ambiguo, non conclusivo (point estimate inside the interval)
- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), dispute-rtt: C - D = 27.50 ms [25.73; 32.85]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 3.06 ms [1.23; 4.85]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 5.23 ms [3.20; 7.78]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
