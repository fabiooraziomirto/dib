# Sensitivity of M1/M2 to the initial fsync stall (definitions: docs/audit/39, c3e3777)

## M1, order: first 20 cells (position: arm, writers, rep, throughput ops/s, unexpected errors)
- 0: default, 1, rep 1, 181.8, 0
- 1: deploy, 10, rep 3, 244.4, 0
- 2: deploy, 10, rep 8, 236.7, 0
- 3: default, 10, rep 2, 140.2, 0
- 4: default, 10, rep 4, 120.6, 5
- 5: deploy, 100, rep 12, 117.2, 10
- 6: default, 100, rep 13, 89.4, 615
- 7: default, 10, rep 8, 147.3, 0
- 8: deploy, 50, rep 9, 168.6, 2
- 9: deploy, 100, rep 10, 110.5, 13
- 10: deploy, 100, rep 17, 116.4, 10
- 11: default, 100, rep 16, 97.3, 527
- 12: default, 1, rep 9, 281.7, 0
- 13: default, 1, rep 3, 273.7, 0
- 14: deploy, 100, rep 7, 124.7, 105
- 15: default, 50, rep 8, 167.0, 35
- 16: default, 10, rep 5, 207.7, 0
- 17: deploy, 10, rep 1, 345.9, 0
- 18: default, 100, rep 0, 105.5, 605
- 19: default, 100, rep 18, 124.2, 444

## M1, trend per group (cells >= 8): Spearman of position with throughput / unexpected errors; throughput of cells at positions < 10 against the rest

| arm | writers | cells | mean position | rho(position, throughput) | rho(position, errors) | early n / mean | rest n / mean |
|---|---|---|---|---|---|---|---|
| default | 1 | 10 | 47.0 | 0.236 | n/a | 1 / 181.8 | 9 / 262.6 |
| default | 10 | 10 | 33.6 | 0.503 | -0.406 | 3 / 136.0 | 7 / 209.2 |
| default | 50 | 10 | 56.9 | -0.079 | 0.061 | 0 / n/a | 10 / 153.5 |
| default | 100 | 20 | 54.0 | 0.723 | -0.690 | 1 / 89.4 | 19 / 119.6 |
| deploy | 1 | 10 | 58.8 | 0.430 | n/a | 0 / n/a | 10 / 372.6 |
| deploy | 10 | 10 | 33.7 | 0.418 | n/a | 2 / 240.5 | 8 / 298.6 |
| deploy | 50 | 10 | 52.7 | -0.285 | 0.123 | 1 / 168.6 | 9 / 210.0 |
| deploy | 100 | 20 | 52.2 | 0.442 | -0.116 | 2 / 113.8 | 18 / 136.3 |

## M1, errors by arm: cells with unexpected errors among the first 10 cells and the rest; positions of all cells with errors

- default: first 10 cells 2/5 with errors; rest 29/45; positions with errors: [4, 6, 11, 15, 18, 19, 20, 28, 29, 32, 34, 36, 39, 40, 52, 56, 57, 58, 66, 67, 72, 75, 80, 86, 87, 90, 91, 93, 94, 98, 99]
- deploy: first 10 cells 3/5 with errors; rest 24/45; positions with errors: [5, 8, 9, 10, 14, 24, 26, 31, 33, 44, 46, 47, 49, 50, 61, 62, 64, 65, 73, 74, 76, 79, 82, 88, 89, 95, 97]

## M1, registered verdicts recomputed without the excluded cells (same criteria, seed and resamples as audit 38)

### E5: 5 cells excluded, 95 left

| hypothesis | arm | subset | registered | without the set | changes |
|---|---|---|---|---|---|
| H-M1 | default | all | not falsified | not falsified | unchanged |
| H-M1 | default | filtered | not falsified | not falsified | unchanged |
| H-M1 | deploy | all | not falsified | not falsified | unchanged |
| H-M1 | deploy | filtered | not falsified | not falsified | unchanged |
| H-M1b | deploy | all | FALSIFIED | FALSIFIED | unchanged |
| H-M1b | deploy | filtered | FALSIFIED | FALSIFIED | unchanged |
| H-M1c | deploy vs default | all | not falsified | not falsified | unchanged |
| H-M1c | deploy vs default | filtered | not falsified | not falsified | unchanged |

### E10: 10 cells excluded, 90 left

| hypothesis | arm | subset | registered | without the set | changes |
|---|---|---|---|---|---|
| H-M1 | default | all | not falsified | not falsified | unchanged |
| H-M1 | default | filtered | not falsified | not falsified | unchanged |
| H-M1 | deploy | all | not falsified | not falsified | unchanged |
| H-M1 | deploy | filtered | not falsified | not falsified | unchanged |
| H-M1b | deploy | all | FALSIFIED | FALSIFIED | unchanged |
| H-M1b | deploy | filtered | FALSIFIED | FALSIFIED | unchanged |
| H-M1c | deploy vs default | all | not falsified | not falsified | unchanged |
| H-M1c | deploy vs default | filtered | not falsified | not falsified | unchanged |

### E20: 20 cells excluded, 80 left

| hypothesis | arm | subset | registered | without the set | changes |
|---|---|---|---|---|---|
| H-M1 | default | all | not falsified | not falsified | unchanged |
| H-M1 | default | filtered | not falsified | not falsified | unchanged |
| H-M1 | deploy | all | not falsified | not falsified | unchanged |
| H-M1 | deploy | filtered | not falsified | not falsified | unchanged |
| H-M1b | deploy | all | FALSIFIED | FALSIFIED | unchanged |
| H-M1b | deploy | filtered | FALSIFIED | FALSIFIED | unchanged |
| H-M1c | deploy vs default | all | not falsified | not falsified | unchanged |
| H-M1c | deploy vs default | filtered | not falsified | not falsified | unchanged |

### ET: 9 cells excluded, 91 left

| hypothesis | arm | subset | registered | without the set | changes |
|---|---|---|---|---|---|
| H-M1 | default | all | not falsified | not falsified | unchanged |
| H-M1 | default | filtered | not falsified | not falsified | unchanged |
| H-M1 | deploy | all | not falsified | not falsified | unchanged |
| H-M1 | deploy | filtered | not falsified | not falsified | unchanged |
| H-M1b | deploy | all | FALSIFIED | FALSIFIED | unchanged |
| H-M1b | deploy | filtered | FALSIFIED | FALSIFIED | unchanged |
| H-M1c | deploy vs default | all | not falsified | not falsified | unchanged |
| H-M1c | deploy vs default | filtered | not falsified | not falsified | unchanged |

## M2 (control: no stall before M2), trend per group (cells >= 8): Spearman of position with throughput; throughput at positions < 10 against the rest

| mode | writers | cells | mean position | rho(position, throughput) | early n / mean | rest n / mean |
|---|---|---|---|---|---|---|
| null | 100 | 10 | 49.5 | -0.552 | 1 / 40327.0 | 9 / 37361.0 |
| processes | 10 | 10 | 39.4 | 0.139 | 0 / n/a | 10 / 460.6 |
| processes | 50 | 10 | 37.4 | -0.176 | 1 / 303.0 | 9 / 305.2 |
| processes | 100 | 10 | 53.2 | 0.309 | 1 / 219.2 | 9 / 218.6 |
| threads | 1 | 10 | 38.8 | -0.188 | 2 / 349.8 | 8 / 346.9 |
| threads | 10 | 10 | 34.9 | -0.091 | 2 / 322.9 | 8 / 334.8 |
| threads | 50 | 10 | 51.6 | -0.067 | 1 / 215.5 | 9 / 218.2 |
| threads | 100 | 20 | 47.9 | 0.511 | 2 / 142.5 | 18 / 153.2 |
