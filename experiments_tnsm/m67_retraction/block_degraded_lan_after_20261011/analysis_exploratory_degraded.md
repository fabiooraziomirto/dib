# Exploratory / sensitivity analyses, B1 `degraded` (definitions: docs/audit/35 section B, committed 55b29a3 before any computation)

## B1. Sensitivity of (c) to the `client_timeout` episode of D/1 (registered D = 9/960, C = 32/960)
Episodes excluded for `client_timeout` in D cells: 1 (counted as 10 deliveries in n in the worst cases).

| scenario | x/n | share | CP 95% CI | classification vs D [0.004, 0.015] | changed vs S0 | second clause |
|---|---|---|---|---|---|---|
| S0 | 9/960 | 0.00937 | [0.00430; 0.01772] | CI crosses a bound: inconclusive | False | satisfied: the CI of C lies entirely above the CI of D (point estimates C 0.03333, D 0.00937) |
| S_a | 9/970 | 0.00928 | [0.00425; 0.01754] | CI crosses a bound: inconclusive | False | satisfied: the CI of C lies entirely above the CI of D (point estimates C 0.03333, D 0.00928) |
| S_b | 19/970 | 0.01959 | [0.01183; 0.03042] | CI crosses a bound: inconclusive | False | inconclusive for this clause: the CIs overlap (point estimates C 0.03333, D 0.01959; point estimate of C above D, information only) |

## B2. Sensitivity of (a) to the selection: last site over ALL valid episodes (pending sites by their ack time)
No verdict: the registered one is in analysis_degraded.md:68-71. 'registered' = episodes without pending (analyze_b1.last_site).

| cell | all valid, median ms [CI] (n) | unmeasurable / undrained | registered, median ms [CI] (n) | registered threshold ms | all-valid median − threshold ms (information) | all-valid median − registered median ms |
|---|---|---|---|---|---|---|
| C/1 | 19322.36 [16964.61; 20584.00] (48) | 0 / 0 | 17022.36 [15615.42; 19323.99] (31) | 12240.1 | 7082.3 | 2300.0 |
| C/10 | 3420.38 [2733.97; 3825.86] (48) | 0 / 0 | 2824.58 [2422.25; 3418.70] (35) | 1267.4 | 2153.0 | 595.8 |
| D/1 | 10783.83 [10164.55; 11672.11] (47) | 0 / 0 | 10669.83 [9769.59; 11177.69] (41) | 8146.3 | 2637.5 | 114.0 |
| D/10 | 2016.93 [1621.59; 2020.18] (49) | 0 / 0 | 2016.77 [1621.25; 2019.21] (46) | 862.1 | 1154.8 | 0.2 |

## B3. Per-site times (descriptive)

### FANOUT 1: delivery cost = gap between consecutive `plog_apply_ts` in id order (position 0: apply[0] − t0), seconds; episodes without pending, id order monotone

**D/1**: episodes used 41, with pending (left out) 6, order violations 0

| position | stats (s) |
|---|---|
| 0 | n=41 min 0.609 p25 0.611 med 0.613 p75 0.618 p95 1.613 max 2.617 |
| 1 | n=41 min 0.804 p25 0.807 med 0.807 p75 0.808 p95 2.613 max 3.119 |
| 2 | n=41 min 0.803 p25 0.806 med 0.807 p75 0.809 p95 2.208 max 2.611 |
| 3 | n=41 min 0.803 p25 0.804 med 0.805 p75 0.809 p95 2.210 max 4.011 |
| 4 | n=41 min 0.804 p25 0.805 med 0.807 p75 1.310 p95 2.171 max 2.210 |
| 5 | n=41 min 0.804 p25 0.805 med 0.805 p75 1.807 p95 2.610 max 4.014 |
| 6 | n=41 min 0.803 p25 0.804 med 0.805 p75 0.806 p95 2.207 max 2.609 |
| 7 | n=41 min 0.803 p25 0.804 med 0.805 p75 0.808 p95 3.118 max 4.014 |
| 8 | n=41 min 0.803 p25 0.804 med 0.805 p75 0.806 p95 1.807 max 3.715 |
| 9 | n=41 min 0.804 p25 0.804 med 0.805 p75 0.805 p95 2.208 max 4.925 |

histogram of gaps at positions 1-9 (class width 0.25 s, left edge: count): {0.75: 285, 1.25: 18, 1.5: 2, 1.75: 26, 2.0: 13, 2.25: 2, 2.5: 10, 2.75: 1, 3.0: 6, 3.5: 1, 4.0: 4, 4.75: 1}

**C/1**: episodes used 31, with pending (left out) 17, order violations 0

| position | stats (s) |
|---|---|
| 0 | n=31 min 1.012 p25 1.015 med 1.017 p75 1.022 p95 2.421 max 2.927 |
| 1 | n=31 min 1.207 p25 1.209 med 1.211 p75 3.014 p95 5.526 max 7.229 |
| 2 | n=31 min 1.207 p25 1.210 med 1.212 p75 2.413 p95 3.419 max 3.422 |
| 3 | n=31 min 1.207 p25 1.208 med 1.210 p75 2.211 p95 3.768 max 4.821 |
| 4 | n=31 min 1.208 p25 1.208 med 1.210 p75 2.411 p95 3.419 max 3.520 |
| 5 | n=31 min 1.207 p25 1.209 med 1.209 p75 1.716 p95 3.771 max 4.418 |
| 6 | n=31 min 1.207 p25 1.209 med 1.210 p75 1.913 p95 3.014 max 6.228 |
| 7 | n=31 min 1.208 p25 1.209 med 1.715 p75 2.611 p95 3.568 max 4.027 |
| 8 | n=31 min 1.207 p25 1.209 med 1.209 p75 1.891 p95 3.868 max 5.731 |
| 9 | n=31 min 1.207 p25 1.208 med 1.209 p75 1.710 p95 3.089 max 3.419 |

histogram of gaps at positions 1-9 (class width 0.25 s, left edge: count): {1.0: 175, 1.5: 22, 2.0: 20, 2.5: 16, 3.0: 19, 3.25: 7, 3.5: 7, 3.75: 1, 4.0: 3, 4.25: 3, 4.75: 2, 5.5: 1, 6.0: 2, 7.0: 1}

### FANOUT 10: maximum per episode (episodes without pending), base plane and sites above it (base + 0.25 s)

**D/10**: max per episode n=46 min 0.615 p25 1.618 med 2.017 p75 2.101 p95 3.018 max 3.421; histogram (0.5 s): {0.5: 1, 1.0: 6, 1.5: 13, 2.0: 16, 2.5: 6, 3.0: 4}
base plane (median of withdrawn_plog_s, all non-excluded sites with a value) 0.617 s; sites total 490, above the base 101; number of sites above per valid episode {k: episodes} {0: 1, 1: 18, 2: 12, 3: 13, 4: 5}; histogram of (value − base) in 0.5 s classes {-0.5: 245, 0.0: 145, 0.5: 38, 1.0: 50, 1.5: 5, 2.0: 6, 2.5: 1}

**C/10**: max per episode n=35 min 1.023 p25 2.421 med 2.825 p75 3.624 p95 4.266 max 4.634; histogram (0.5 s): {1.0: 1, 1.5: 1, 2.0: 13, 2.5: 5, 3.0: 6, 3.5: 6, 4.0: 2, 4.5: 1}
base plane (median of withdrawn_plog_s, all non-excluded sites with a value) 1.021 s; sites total 474, above the base 127; number of sites above per valid episode {k: episodes} {0: 3, 1: 8, 2: 14, 3: 12, 4: 5, 5: 5, 10: 1}; histogram of (value − base) in 0.5 s classes {-0.5: 237, 0.0: 119, 0.5: 32, 1.0: 41, 1.5: 18, 2.0: 15, 2.5: 7, 3.0: 4, 3.5: 1}

## B4. Pending path against B_online (D 10.5 s, C 11.1 s): u = ack − t0 (upper bound); e = ack − apply of the previous site (FANOUT 1 only)

| cell | pending sites (with ack) | in pending_left without ack | n_pending_undrained / unmeasured (cell summary) | exceed B_online with u | estimable e | exceed with e | max u | median u | max e | median e |
|---|---|---|---|---|---|---|---|---|---|---|
| C/1 | 18 | 0 | 0 / 0 | 15 | 18 | 5 | 31.46 | 18.43 | 17.78 | 9.32 |
| C/10 | 14 | 0 | 0 / 0 | 6 | 0 | n/a | 16.00 | 10.49 | n/a | n/a |
| D/1 | 6 | 0 | 0 / 0 | 4 | 6 | 0 | 17.96 | 11.61 | 8.89 | 8.01 |
| D/10 | 3 | 0 | 0 / 0 | 0 | 0 | n/a | 9.67 | 8.82 | n/a | n/a |

Per-site list (cell, episode order not kept: site id, u s, e s):
- C/1: s6 u=31.46 e=17.78; s6 u=19.60 e=8.30; s1 u=9.64 e=8.62; s9 u=23.25 e=8.24; s9 u=30.42 e=9.60; s3 u=16.52 e=6.97; s0 u=15.37 e=15.37; s0 u=5.36 e=5.36; s2 u=11.30 e=8.67; s4 u=17.25 e=9.20; s7 u=23.63 e=9.34; s8 u=25.28 e=10.57; s1 u=13.75 e=12.23; s9 u=23.93 e=10.02; s8 u=23.63 e=12.25; s0 u=9.23 e=9.23; s4 u=16.01 e=11.36; s6 u=20.56 e=9.29
- C/10: s0 u=15.93; s6 u=9.97; s6 u=9.97; s4 u=12.60; s2 u=7.89; s2 u=11.59; s4 u=16.00; s2 u=13.09; s1 u=9.70; s1 u=11.01; s8 u=9.19; s9 u=13.09; s2 u=6.24; s6 u=8.04
- D/1: s2 u=12.12 e=8.89; s8 u=17.96 e=8.49; s2 u=7.32 e=5.91; s1 u=8.22 e=7.61; s5 u=11.10 e=6.46; s8 u=16.96 e=8.40
- D/10: s7 u=9.67; s9 u=8.44; s0 u=8.82

## B5. POST-HOC arithmetic (computed on the same data that falsified (a); independence of attempts assumed; 3 attempts of 1 s, service.py:120-121)

| arm | pending share q (x/n) | p = q^(1/3) | E[failed attempts] per delivery | expected failed attempts per episode FANOUT 1 (10 deliveries) | E[max over 10 sites] failed attempts FANOUT 10 | MC check (seed 20261011, 200000) F1 / F10 |
|---|---|---|---|---|---|---|
| D (point) | 0.00937 | 0.2109 | 0.2647 | 2.647 | 1.362 | 2.651 / 1.365 |
| D (CI low) | 0.00430 | 0.1626 | 0.1933 | 1.933 | 1.107 | 1.936 / 1.111 |
| D (CI high) | 0.01772 | 0.2607 | 0.3464 | 3.464 | 1.620 | 3.469 / 1.622 |
| D FANOUT 1 only | 6/470 = 0.01277 | 0.2337 | 0.3011 | 3.011 | 1.481 | — |
| D FANOUT 10 only | 3/490 = 0.00612 | 0.1829 | 0.2225 | 2.225 | 1.215 | — |
| C (point) | 0.03333 | 0.3218 | 0.4587 | 4.587 | 1.932 | 4.593 / 1.931 |
| C (CI low) | 0.02291 | 0.2840 | 0.3876 | 3.876 | 1.740 | 3.881 / 1.742 |
| C (CI high) | 0.04673 | 0.3602 | 0.5367 | 5.367 | 2.120 | 5.370 / 2.120 |
| C FANOUT 1 only | 18/480 = 0.03750 | 0.3347 | 0.4843 | 4.843 | 1.996 | — |
| C FANOUT 10 only | 14/480 = 0.02917 | 0.3078 | 0.4317 | 4.317 | 1.861 | — |

Comparison with the observed excess (a), seconds; expected extra time = 1 s × expected failed attempts (point estimate of the pooled q):

| cell | observed median − predicted (s) | registered excess over threshold (s) | expected extra time from the arithmetic (s) |
|---|---|---|---|
| C/1 | 5.02 | 4.78 | 4.59 |
| C/10 | 1.62 | 1.56 | 1.93 |
| D/1 | 2.67 | 2.52 | 2.65 |
| D/10 | 1.22 | 1.15 | 1.36 |

Limits: the observed medians are over episodes WITHOUT pending, the arithmetic is not; the cost of a failed attempt is assumed 1 s; no statement that the arithmetic explains or confirms the excess.

## B6. Summary table (last-site P-log-apply, ONLY episodes without pending; pending share over all valid episodes; excluded per cell)

| profile | arm | FANOUT | median last site ms [95% CI] | n (episodes without pending) | P-log accepted | pending x/n | excluded |
|---|---|---|---|---|---|---|---|
| lan (before) | C | 1 | 74.14 [70.90; 82.07] | 10 | yes | 0/100 | 0 |
| lan (before) | C | 10 | 22.46 [20.29; 23.59] | 10 | NO (not accepted) | 0/100 | 0 |
| lan (before) | D | 1 | 45.71 [43.11; 54.78] | 10 | yes | 0/100 | 0 |
| lan (before) | D | 10 | 20.71 [18.86; 22.63] | 10 | NO (not accepted) | 0/100 | 0 |
| lan (after) | C | 1 | 80.04 [75.56; 86.62] | 10 | yes | 0/100 | 0 |
| lan (after) | C | 10 | 19.65 [19.20; 22.05] | 10 | NO (not accepted) | 0/100 | 0 |
| lan (after) | D | 1 | 48.76 [43.80; 55.76] | 10 | yes | 0/100 | 0 |
| lan (after) | D | 10 | 18.86 [17.63; 22.12] | 10 | NO (not accepted) | 0/100 | 0 |
| wan (rilancio) | C | 1 | 4827.72 [4809.59; 5427.32] | 10 | yes | 0/100 | 0 |
| wan (rilancio) | C | 10 | 429.26 [420.20; 1017.98] | 10 | yes | 0/100 | 0 |
| wan (rilancio) | D | 1 | 3191.84 [3174.33; 3824.47] | 10 | yes | 0/100 | 0 |
| wan (rilancio) | D | 10 | 258.97 [256.75; 591.89] | 10 | yes | 0/100 | 0 |
| degraded | C | 1 | 17022.36 [15615.42; 19323.99] | 31 | yes | 18/480 | 2 |
| degraded | C | 10 | 2824.58 [2422.25; 3418.70] | 35 | yes | 14/480 | 2 |
| degraded | D | 1 | 10669.83 [9769.59; 11177.69] | 41 | yes | 6/470 | 3 |
| degraded | D | 10 | 2016.77 [1621.25; 2019.21] | 46 | yes | 3/490 | 1 |
