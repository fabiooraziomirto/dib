# Sensitivity of rule (a) to the lan reference (descriptive; the pre-registered verdict is the adjacent 'before' session)

| arm | FANOUT | wan median ms [CI] | 10xn_RTTxR or n_RTTxR ms | reference | lan median ms | threshold ms | excess ms | verdict |
|---|---|---|---|---|---|---|---|---|
| C | 1 | 4827.7 [4809.6; 5427.3] | 4800 | 07:52 (b1) | 105.96 | 5117.9 | -290.2 | not falsified |
| C | 1 | 4827.7 [4809.6; 5427.3] | 4800 | 08:40 (before, adjacent) | 73.31 | 5019.9 | -192.2 | not falsified |
| C | 1 | 4827.7 [4809.6; 5427.3] | 4800 | max of sessions | 105.96 | 5117.9 | -290.2 | not falsified |
| C | 10 | 429.3 [420.2; 1018.0] | 480 | 07:52 (b1) | 30.61 | 571.8 | -142.6 | not falsified |
| C | 10 | 429.3 [420.2; 1018.0] | 480 | 08:40 (before, adjacent) | 20.88 | 542.6 | -113.4 | not falsified |
| C | 10 | 429.3 [420.2; 1018.0] | 480 | max of sessions | 30.61 | 571.8 | -142.6 | not falsified |
| D | 1 | 3191.8 [3174.3; 3824.5] | 3200 | 07:52 (b1) | 67.31 | 3401.9 | -210.1 | not falsified |
| D | 1 | 3191.8 [3174.3; 3824.5] | 3200 | 08:27 (b1_default) | 48.41 | 3345.2 | -153.4 | not falsified |
| D | 1 | 3191.8 [3174.3; 3824.5] | 3200 | 08:40 (before, adjacent) | 45.85 | 3337.5 | -145.7 | not falsified |
| D | 1 | 3191.8 [3174.3; 3824.5] | 3200 | max of sessions | 67.31 | 3401.9 | -210.1 | not falsified |
| D | 10 | 259.0 [256.6; 591.9] | 320 | 07:52 (b1) | 25.91 | 397.7 | -138.8 | not falsified |
| D | 10 | 259.0 [256.6; 591.9] | 320 | 08:27 (b1_default) | 21.99 | 386.0 | -127.0 | not falsified |
| D | 10 | 259.0 [256.6; 591.9] | 320 | 08:40 (before, adjacent) | 17.82 | 373.5 | -114.5 | not falsified |
| D | 10 | 259.0 [256.6; 591.9] | 320 | max of sessions | 25.91 | 397.7 | -138.8 | not falsified |

- C FANOUT 1: median 4827.7 vs pred 4800 (diff +27.7 ms): verdict would become 'inconclusive' only for a lan reference below 9.24 ms and 'falsified' below 3.20 ms (lan medians of the day: 73.3-106.0 ms)
- C FANOUT 10: median 429.3 vs pred 480 (diff -50.7 ms): the median is below the network term alone: no non-negative reference can make it exceed the threshold
- D FANOUT 1: median 3191.8 vs pred 3200 (diff -8.2 ms): the median is below the network term alone: no non-negative reference can make it exceed the threshold
- D FANOUT 10: median 259.0 vs pred 320 (diff -61.0 ms): the median is below the network term alone: no non-negative reference can make it exceed the threshold
