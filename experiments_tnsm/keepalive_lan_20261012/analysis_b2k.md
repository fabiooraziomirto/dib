# B2-kill analysis (audit 45)

| profile | arm | T | k | n | converged | never | median s [CI] | bound s | (d-kill) | (e) violations | excluded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lan | C | 5 | 1 | 10 | 10 | 0 | 0.70 [0.57; 0.81] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 1 | 10 | 10 | 0 | 1.38 [1.04; 1.73] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | C | 5 | 10 | 10 | 10 | 0 | 0.74 [0.64; 0.81] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 10 | 9 | 9 | 0 | 0.88 [0.79; 1.40] (n=9) | 8.00 | not falsified | 0 | {'client_timeout': 1} |
| lan | C | 5 | 50 | 10 | 10 | 0 | 0.77 [0.64; 0.87] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | C | 15 | 50 | 10 | 10 | 0 | 1.03 [0.72; 1.91] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 1 | 10 | 10 | 0 | 0.65 [0.58; 0.84] (n=10) | 7.00 | not falsified | 0 | 0 |
| lan | D | 15 | 1 | 10 | 10 | 0 | 0.99 [0.61; 1.72] (n=10) | 8.00 | not falsified | 0 | 0 |
| lan | D | 5 | 10 | 9 | 9 | 0 | 0.62 [0.58; 0.82] (n=9) | 7.00 | not falsified | 0 | {'client_timeout': 1} |
| lan | D | 15 | 10 | 7 | 7 | 0 | 1.04 [0.83; 1.84] (n=7) | 8.00 | not falsified | 0 | {'client_timeout': 3} |
| lan | D | 5 | 50 | 3 | 3 | 0 | 1.01 [0.99; 1.05] (n=3) | 7.00 | not falsified | 0 | {'client_timeout': 5, 'transport_error': 2} |
| lan | D | 15 | 50 | 3 | 3 | 0 | 1.46 [1.27; 1.88] (n=3) | 8.00 | not falsified | 0 | {'client_timeout': 7} |

**(d-kill)** falsified in 0/12 cells; **(e)** not falsified (I1-I3 only through `final_all_monitor_only`; no other invariant checked).

## T15 - T5 (descriptive, decision Q9; no verdict)

- lan/C/k=1: 0.674 s [0.294; 1.061] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/C/k=10: 0.146 s [0.020; 0.659] (n15=9, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/C/k=50: 0.263 s [-0.066; 1.161] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=1: 0.344 s [-0.126; 1.071] (n15=10, n5=10); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=10: 0.428 s [0.105; 1.256] (n15=7, n5=9); reference interval [0; 1.5] s (a14:254-257), not a criterion
- lan/D/k=50: 0.450 s [0.214; 0.890] (n15=3, n5=3); reference interval [0; 1.5] s (a14:254-257), not a criterion
