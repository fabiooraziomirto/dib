# B2-kill analysis (audit 45)

| profile | arm | T | k | n | converged | never | median s [CI] | bound s | (d-kill) | (e) violations | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lan | C | 5 | 1 | 10 | 10 | 0 | 0.60 [0.51; 0.70] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 1 | 10 | 10 | 0 | 0.91 [0.63; 1.70] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 10 | 10 | 10 | 0 | 0.65 [0.52; 0.84] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 10 | 10 | 10 | 0 | 1.05 [0.78; 1.53] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 50 | 10 | 10 | 0 | 0.81 [0.72; 0.90] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 50 | 10 | 10 | 0 | 1.47 [1.11; 1.81] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 1 | 10 | 10 | 0 | 0.74 [0.62; 0.80] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 1 | 10 | 10 | 0 | 1.12 [0.67; 1.72] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 10 | 10 | 10 | 0 | 0.64 [0.59; 0.84] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 10 | 10 | 10 | 0 | 0.81 [0.63; 1.06] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 50 | 10 | 10 | 0 | 0.81 [0.76; 0.96] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 50 | 10 | 10 | 0 | 1.69 [1.06; 1.96] (n=10) | 8.00 | not falsified | 0 | 0 |

**(d-kill)** falsified in 0/12 cells; **(e)** not falsified (I1-I3 only through `final_all_monitor_only`; no other invariant checked).

## T15 - T5 (descriptive, decision Q9; no verdict)

- lan/C/k=1: 0.315 s [0.008; 1.122] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/C/k=10: 0.402 s [0.048; 0.905] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/C/k=50: 0.661 s [0.270; 0.997] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=1: 0.388 s [-0.072; 1.003] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=10: 0.168 s [-0.122; 0.425] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=50: 0.875 s [0.234; 1.147] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
