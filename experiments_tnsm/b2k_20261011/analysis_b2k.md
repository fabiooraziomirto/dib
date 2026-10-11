# B2-kill analysis (audit 45)

| profile | arm | T | k | n | converged | never | median s [CI] | bound s | (d-kill) | (e) violations | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| degraded | C | 5 | 1 | 10 | 10 | 0 | 2.64 [2.33; 4.71] (n=10) | 7.60 | not falsified | 0 | 0 |
| degraded | C | 15 | 1 | 10 | 10 | 0 | 4.33 [3.30; 5.37] (n=10) | 8.60 | not falsified | 0 | 0 |
| degraded | C | 5 | 10 | 9 | 9 | 0 | 2.81 [2.04; 4.16] (n=9) | 7.60 | not falsified | 0 | {'transport_error': 1} |
| degraded | C | 15 | 10 | 9 | 9 | 0 | 3.26 [2.49; 3.59] (n=9) | 8.60 | not falsified | 0 | {'transport_error': 1} |
| degraded | D | 5 | 1 | 9 | 9 | 0 | 1.98 [1.57; 3.32] (n=9) | 7.00 | not falsified | 0 | {'client_timeout': 1} |
| degraded | D | 15 | 1 | 10 | 10 | 0 | 2.62 [1.64; 3.96] (n=10) | 8.00 | not falsified | 0 | 0 |
| degraded | D | 5 | 10 | 10 | 10 | 0 | 2.04 [1.49; 2.82] (n=10) | 7.00 | not falsified | 0 | 0 |
| degraded | D | 15 | 10 | 10 | 10 | 0 | 3.66 [2.79; 4.32] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 1 | 10 | 10 | 0 | 0.71 [0.62; 0.79] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 1 | 10 | 10 | 0 | 1.01 [0.57; 1.34] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 10 | 0 | 0 | 0 | — | 7.00 | not evaluable | 0 | {'queues_not_empty_at_start': 10} |
| lan | C | 15 | 10 | 7 | 7 | 0 | 0.98 [0.88; 1.38] (n=7) | 8.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 2} |
| lan | C | 5 | 50 | 1 | 1 | 0 | 0.69 [0.69; 0.69] (n=1) | 7.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 8} |
| lan | C | 15 | 50 | 0 | 0 | 0 | — | 8.00 | not evaluable | 0 | {'queues_not_empty_at_start': 10} |
| lan | D | 5 | 1 | 10 | 10 | 0 | 0.71 [0.56; 0.82] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 1 | 10 | 10 | 0 | 1.20 [0.93; 1.78] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 10 | 0 | 0 | 0 | — | 7.00 | not evaluable | 0 | {'queues_not_empty_at_start': 10} |
| lan | D | 15 | 10 | 6 | 6 | 0 | 0.91 [0.61; 1.59] (n=6) | 8.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 3} |
| lan | D | 5 | 50 | 1 | 1 | 0 | 0.64 [0.64; 0.64] (n=1) | 7.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 8} |
| lan | D | 15 | 50 | 0 | 0 | 0 | — | 8.00 | not evaluable | 0 | {'queues_not_empty_at_start': 10} |
| wan | C | 5 | 1 | 10 | 10 | 0 | 1.43 [1.24; 1.56] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | C | 15 | 1 | 10 | 10 | 0 | 1.35 [0.90; 2.29] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | C | 5 | 10 | 10 | 10 | 0 | 1.36 [1.22; 1.56] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | C | 15 | 10 | 10 | 10 | 0 | 2.01 [1.48; 2.34] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | D | 5 | 1 | 10 | 10 | 0 | 1.00 [0.82; 1.26] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | D | 15 | 1 | 10 | 10 | 0 | 2.06 [1.28; 2.25] (n=10) | 8.00 | not falsified | 0 | 0 |
| wan | D | 5 | 10 | 10 | 10 | 0 | 1.12 [0.90; 1.31] (n=10) | 7.00 | not falsified | 0 | 0 |
| wan | D | 15 | 10 | 10 | 10 | 0 | 1.50 [0.85; 1.78] (n=10) | 8.00 | not falsified | 0 | 0 |

**(d-kill)** falsified in 0/28 cells; **(e)** not falsified (I1-I3 only through `final_all_monitor_only`; no other invariant checked).

## T15 - T5 (descriptive, decision Q9; no verdict)

- degraded/C/k=1: 1.690 s [-1.115; 2.664] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- degraded/C/k=10: 0.453 s [-0.835; 1.440] (n15=9, n5=9); reference interval [0; 1.5] s (a14:254-257), not a criterion
- degraded/D/k=1: 0.640 s [-0.729; 1.808] (n15=10, n5=9); reference interval [0; 1.5] s (a14:254-257), not a criterion
- degraded/D/k=10: 1.623 s [0.446; 2.483] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/C/k=1: 0.301 s [-0.144; 0.646] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/C/k=10: not evaluable (a side has no converged trial)
- lan/C/k=50: not evaluable (a side has no converged trial)
- lan/D/k=1: 0.489 s [0.163; 1.102] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=10: not evaluable (a side has no converged trial)
- lan/D/k=50: not evaluable (a side has no converged trial)
- wan/C/k=1: -0.080 s [-0.540; 0.901] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- wan/C/k=10: 0.658 s [0.140; 0.995] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- wan/D/k=1: 1.064 s [0.249; 1.342] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- wan/D/k=10: 0.372 s [-0.353; 0.740] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
