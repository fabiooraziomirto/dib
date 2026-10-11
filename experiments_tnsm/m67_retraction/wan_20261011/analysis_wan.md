# B1 analysis, profile `wan` (run.py sha256 `022d97a6dc76`, tree `/home/ubuntu/dib_tnsm/tree-bf272e8`, seed 20261014)
started 2026-10-11T09:06:47.457873+00:00, finished 2026-10-11T09:15:02.776517+00:00, aborted: False

cells in file: 4; complete: 4; partial/aborted: 0

## Per cell

| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 1 | 10 | 0  | 5087.31 [4975.23; 5589.66] (n=10) | 4827.72 [4809.59; 5427.32] (n=10) | 162.92, 525.40 | 0.001 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| C | 10 | 10 | 0  | 862.66 [586.93; 1260.45] (n=10) | 429.26 [420.20; 1017.98] (n=10) | 167.00, 522.46 | 0.006 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 1 | 10 | 0  | 3355.28 [3338.00; 3987.06] (n=10) | 3191.84 [3174.33; 3824.47] (n=10) | 162.89, 163.98 | 0.001 (accepted) | P-log-apply | 0/0/0 | 0/0 |
| D | 10 | 10 | 0  | 521.96 [420.62; 1069.56] (n=10) | 258.97 [256.55; 591.89] (n=10) | 163.47, 807.32 | 0.009 (accepted) | P-log-apply | 0/0/0 | 0/0 |

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
| C | 1 | 0.1916 | 0.016 | False | 0.019/0.279 | 3.2 | False |
| C | 10 | 0.1533 | 0.026 | False | 0.032/0.377 | 4.5 | False |
| D | 1 | 0.1632 | 0.01 | False | 0.013/0.060 | 3.5 | False |
| D | 10 | 0.1566 | 0.021 | False | 0.022/0.050 | 4.8 | False |

## generator_path_ms (reused / fresh, ms) and flags

| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |
|---|---|---|---|---|---|---|
| C | 1 | 81.49 | 245.61 | True | None | False |
| C | 10 | 82.43 | 246.12 | True | None | False |
| D | 1 | 82.46 | 163.17 | True | True | False |
| D | 10 | 82.12 | 163.49 | True | True | False |

(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)

## Prediction (a) with the adjacent `lan` reference (higher median over: /root/Desktop/DIB_tnsm/experiments_tnsm/m67_retraction/lan_ref_20261011/before)

| arm | FANOUT | measure | median ms [CI] | 10 x n_RTT x R (FANOUT 1) / n_RTT x R ms | reference lan median ms | threshold ms | excess over threshold ms | verdict |
|---|---|---|---|---|---|---|---|---|
| C | 1 | P-log-apply | 4827.72 [4809.59; 5427.32] (n=10) | 4800.0 | 73.31 (/root/Desktop/DIB_tnsm/experiments_tnsm/m67_retraction/lan_ref_20261011/before) | 5019.9 | -192.2 | not falsified |
| C | 10 | P-log-apply | 429.26 [420.20; 926.43] (n=10) | 480.0 | 20.88 (/root/Desktop/DIB_tnsm/experiments_tnsm/m67_retraction/lan_ref_20261011/before) | 542.6 | -113.4 | not falsified |
| D | 1 | P-log-apply | 3191.84 [3174.33; 3824.47] (n=10) | 3200.0 | 45.85 (/root/Desktop/DIB_tnsm/experiments_tnsm/m67_retraction/lan_ref_20261011/before) | 3337.5 | -145.7 | not falsified |
| D | 10 | P-log-apply | 258.97 [256.55; 583.38] (n=10) | 320.0 | 17.82 (/root/Desktop/DIB_tnsm/experiments_tnsm/m67_retraction/lan_ref_20261011/before) | 373.5 | -114.5 | not falsified |

## Differences between arms (median difference, bootstrap CI over episodes)

- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), last-site P-log: C - D = 1635.88 ms [998.43; 2235.48] -> CI entirely outside [15, 32]: falsified under the strict reading
- FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32]), dispute-rtt: C - D = 1732.03 ms [1008.30; 2234.39]
- FANOUT 10 (no registered interval; descriptive), last-site P-log: C - D = 170.29 ms [-152.10; 662.28]
- FANOUT 10 (no registered interval; descriptive), dispute-rtt: C - D = 340.70 ms [-302.90; 548.01]
- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.
