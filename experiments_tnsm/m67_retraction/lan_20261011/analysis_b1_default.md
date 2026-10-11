# B1 analysis, profile `lan` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-bf272e8`, seed 20261014)
started 2026-10-11T08:26:46.564385+00:00, finished 2026-10-11T08:30:09.002584+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| D | 1 | 10 | 0  | 50.69 [46.99; 54.10] (n=10) | 48.41 [45.44; 51.94] (n=10) | 1.86, 2.59 | 0.052 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 25.37 [20.54; 45.46] (n=10) | 21.99 [17.06; 40.88] (n=10) | 3.25, 6.91 | 0.114 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |
| default | 1 | 10 | 0  | 133.70 [125.11; 148.90] (n=10) | 128.26 [119.56; 146.67] (n=10) | 2.21, 13.94 | 0.019 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| default | 10 | 10 | 0  | 30.32 [27.91; 39.46] (n=10) | 27.35 [24.95; 35.00] (n=10) | 3.77, 4.46 | 0.091 (accepted) | P-log-apply | 0/0/0 | 0/0 |

## Exclusions by cause (all cells)

| arm | FANOUT | client_timeout | queues_not_empty_at_start | transport_error_setup | transport_error_measured | flagged by discard rule |
|---|---|---|---|---|---|---|
| D | 1 | 0 | 0 | 0 | 0 | False |
| D | 10 | 0 | 0 | 0 | 0 | False |
| default | 1 | 0 | 0 | 0 | 0 | False |
| default | 10 | 0 | 0 | 0 | 0 | False |

## Background and discard rule (other_cores > 1.0 or steal_pct > 2.0 flags a cell)

| arm | FANOUT | other_cores | steal_pct | flagged | generator proc cores mean/max | host busy % mean | near saturation |
|---|---|---|---|---|---|---|---|
| D | 1 | 0.1333 | 0.021 | False | 0.044/0.110 | 7.4 | False |
| D | 10 | 0.1472 | 0.317 | False | 0.046/0.150 | 8.5 | False |
| default | 1 | 0.1116 | 0.031 | False | 0.041/0.120 | 7.8 | False |
| default | 10 | 0.1366 | 0.01 | False | 0.041/0.110 | 8.1 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| D | 1 | 1.77 | 1.90 | True | True | False |
| D | 10 | 1.70 | 2.40 | True | True | False |
| default | 1 | 1.06 | 1.83 | True | True | False |
| default | 10 | 1.29 | 1.90 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) at `lan` (rule: falsified if median > n_RTT*R*(10 if FANOUT 1) + 3 x median `lan` of the same arm, beyond the CI)

| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x lan median ms (same arm, same FANOUT) | threshold ms | CI lower > threshold? |
|---|---|---|---|---|---|---|---|
| D | 1 | P-log-apply | 48.41 [45.50; 51.94] (n=10) | 2.00 | 145.22 | 147.22 | False |
| D | 10 | dispute-rtt | 25.37 [20.02; 45.46] (n=10) | 0.20 | 76.10 | 76.30 | False |
| default | 1 | P-log-apply | 128.26 [119.56; 146.67] (n=10) | 2.00 | 384.78 | 386.78 | False |
| default | 10 | P-log-apply | 27.35 [25.13; 35.00] (n=10) | 0.20 | 82.05 | 82.25 | False |

**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict is False by construction and carries no information. Lan medians for both FANOUT values of each arm are in the table above, so the wan rule can be evaluated with either reading of 'same arm' (same FANOUT, or any FANOUT): the choice is open and must be declared before the wan block is analysed.

## Differences between arms (median difference, bootstrap CI over episodes)

- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
