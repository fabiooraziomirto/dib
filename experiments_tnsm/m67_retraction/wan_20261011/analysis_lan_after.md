# B1 analysis, profile `lan` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-bf272e8`, seed 20261014)
started 2026-10-11T09:21:12.149148+00:00, finished 2026-10-11T09:25:04.316442+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 10 | 0  | 71.66 [66.60; 77.14] (n=10) | 70.03 [64.72; 74.55] (n=10) | 1.85, 2.54 | 0.036 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| C | 10 | 10 | 0  | 26.52 [23.96; 28.48] (n=10) | 21.65 [18.43; 22.69] (n=10) | 5.61, 6.85 | 0.115 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |
| D | 1 | 10 | 0  | 49.07 [44.43; 50.85] (n=10) | 47.36 [42.98; 49.25] (n=10) | 1.53, 1.78 | 0.053 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 19.04 [18.25; 22.85] (n=10) | 17.09 [15.64; 20.32] (n=10) | 2.18, 4.12 | 0.146 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |

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
| C | 1 | 0.095 | 0.016 | False | 0.058/0.269 | 7.6 | False |
| C | 10 | 0.1083 | 0.005 | False | 0.065/0.359 | 7.8 | False |
| D | 1 | 0.1224 | 0.005 | False | 0.042/0.110 | 7.2 | False |
| D | 10 | 0.0908 | 0.01 | False | 0.040/0.120 | 7.2 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 1.27 | 3.60 | True | None | False |
| C | 10 | 1.24 | 4.00 | True | None | False |
| D | 1 | 1.02 | 1.50 | True | True | False |
| D | 10 | 1.04 | 1.54 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) at `lan` (self-reference, degenerate)

| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x own median ms | threshold ms | verdict |
|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 70.03 [64.72; 74.65] (n=10) | 3.00 | 210.09 | 213.09 | not falsified |
| C | 10 | dispute-rtt | 26.52 [23.96; 28.48] (n=10) | 0.30 | 79.57 | 79.87 | not falsified |
| D | 1 | P-log-apply | 47.36 [42.98; 49.25] (n=10) | 2.00 | 142.07 | 144.07 | not falsified |
| D | 10 | dispute-rtt | 19.04 [18.25; 22.85] (n=10) | 0.20 | 57.12 | 57.32 | not falsified |

**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict carries no information.

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), last-site P-log: C - D = 22.67 ms [16.92; 29.27] -> CI entirely inside [15, 32]
- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), dispute-rtt: C - D = 22.60 ms [17.18; 30.18]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 4.57 ms [0.27; 6.59]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 7.48 ms [3.05; 9.55]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
