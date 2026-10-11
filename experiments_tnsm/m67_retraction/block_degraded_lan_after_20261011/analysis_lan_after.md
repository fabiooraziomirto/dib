# B1 analysis, profile `lan` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-244f1d0`, seed 20261014)
started 2026-10-11T14:39:17.338798+00:00, finished 2026-10-11T14:43:19.296612+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 10 | 0  | 82.70 [78.14; 89.70] (n=10) | 80.04 [75.56; 86.62] (n=10) | 2.49, 3.22 | 0.031 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| C | 10 | 10 | 0  | 25.04 [23.60; 27.19] (n=10) | 19.65 [19.20; 22.01] (n=10) | 4.80, 6.05 | 0.127 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |
| D | 1 | 10 | 0  | 50.51 [45.55; 58.04] (n=10) | 48.76 [43.93; 55.76] (n=10) | 1.65, 2.44 | 0.051 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 21.65 [20.38; 26.01] (n=10) | 18.86 [17.53; 22.12] (n=10) | 2.90, 5.09 | 0.133 (NOT accepted) | dispute-rtt | 0/0/0 | 0/0 |

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

- watch2.log: 14:40:16.857 → 14:40:17.074
- watch2.log: 14:40:26.756 → 14:40:26.794
- watch2.log: 14:40:29.440 → 14:40:29.636
- watch2.log: 14:40:30.201 → 14:40:30.635
- watch2.log: 14:40:31.206 → 14:40:35.502
- watch2.log: 14:41:17.443 → 14:41:17.478
- watch2.log: 14:41:20.127 → 14:41:26.129
- watch2.log: 14:42:18.370 → 14:42:18.582
- watch2.log: 14:42:28.249 → 14:42:28.285
- watch2.log: 14:42:30.945 → 14:42:37.285

## Background and discard rule (other_cores > 1.0 or steal_pct > 2.0 flags a cell)

| arm | FANOUT | other_cores | steal_pct | flagged | generator proc cores mean/max | host busy % mean | near saturation |
|---|---|---|---|---|---|---|---|
| C | 1 | 0.1632 | 0.016 | False | 0.070/0.488 | 9.2 | False |
| C | 10 | 0.1657 | 0.037 | False | 0.066/0.437 | 8.8 | False |
| D | 1 | 0.1756 | 0.016 | False | 0.043/0.120 | 8.5 | False |
| D | 10 | 0.1632 | 0.021 | False | 0.042/0.120 | 8.7 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 1.93 | 3.71 | True | None | False |
| C | 10 | 1.34 | 3.62 | True | None | False |
| D | 1 | 1.27 | 1.98 | True | True | False |
| D | 10 | 1.17 | 1.92 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) at `lan` (self-reference, degenerate)

| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x own median ms | threshold ms | verdict |
|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 80.04 [75.56; 86.62] (n=10) | 3.00 | 240.11 | 243.11 | not falsified |
| C | 10 | dispute-rtt | 25.04 [23.60; 27.19] (n=10) | 0.30 | 75.13 | 75.43 | not falsified |
| D | 1 | P-log-apply | 48.76 [43.80; 55.76] (n=10) | 2.00 | 146.28 | 148.28 | not falsified |
| D | 10 | dispute-rtt | 21.65 [20.38; 26.01] (n=10) | 0.20 | 64.96 | 65.16 | not falsified |

**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict carries no information.

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), last-site P-log: C - D = 31.27 ms [22.79; 40.25] -> CI crosses a bound of [15, 32]: criterio ambiguo, non conclusivo (point estimate inside the interval)
- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), dispute-rtt: C - D = 32.20 ms [23.05; 41.64]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 0.80 ms [-2.18; 3.11]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 3.39 ms [-1.17; 5.47]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
