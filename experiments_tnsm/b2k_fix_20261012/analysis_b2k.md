# B2-kill analysis (audit 45)

| profile | arm | T | k | n | converged | never | median s [CI] | bound s | (d-kill) | (e) violations | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lan | C | 5 | 1 | 10 | 10 | 0 | 0.64 [0.56; 0.71] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 1 | 10 | 10 | 0 | 1.17 [0.55; 1.65] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 10 | 10 | 10 | 0 | 0.63 [0.50; 0.76] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 10 | 10 | 10 | 0 | 1.19 [0.75; 1.57] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 50 | 10 | 10 | 0 | 0.77 [0.57; 0.84] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 50 | 10 | 10 | 0 | 0.92 [0.72; 1.69] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 1 | 10 | 10 | 0 | 0.70 [0.55; 0.76] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 1 | 10 | 10 | 0 | 0.94 [0.75; 1.38] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 10 | 8 | 8 | 0 | 0.66 [0.58; 0.78] (n=8) | 7.00 | not falsified | 0 | {'client_timeout': 2} |
| lan | D | 15 | 10 | 8 | 8 | 0 | 0.97 [0.70; 1.51] (n=8) | 8.00 | not falsified | 0 | {'client_timeout': 1, 'queues_not_empty_at_start': 1} |
| lan | D | 5 | 50 | 3 | 3 | 0 | 0.72 [0.67; 0.91] (n=3) | 7.00 | not falsified | 0 | {'client_timeout': 7} |
| lan | D | 15 | 50 | 1 | 1 | 0 | 1.91 [1.91; 1.91] (n=1) | 8.00 | not falsified | 0 | {'client_timeout': 2, 'queues_not_empty_at_start': 1, 'transport_error': 6} |

**(d-kill)** falsified in 0/12 cells; **(e)** not falsified (I1-I3 only through `final_all_monitor_only`; no other invariant checked).

## T15 - T5 (descriptive, decision Q9; no verdict)

- lan/C/k=1: 0.536 s [-0.106; 1.008] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/C/k=10: 0.556 s [0.115; 0.944] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/C/k=50: 0.152 s [-0.105; 0.975] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=1: 0.238 s [0.022; 0.695] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=10: 0.309 s [0.031; 0.728] (n15=8, n5=8); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=50: 1.198 s [1.009; 1.248] (n15=1, n5=3); reference interval [0; 1.5] s (a14:254-257), not a criterion
