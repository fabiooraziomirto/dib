### http

| Sites | Writers | attempted req/s | ok req/s | state-changing/s | p50 / p95 / p99 ms | 409 | unexpected | client cores | evidence cores | bottleneck |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 109.7 ± 6.6 | 66.9 | 18.1 | 8.2 / 14.8 / 23.0 | 1949 | 0 | 0.07 | 0.21 | not attributable |
| 1 | 10 | 248.6 ± 13.3 | 155.1 | 43.1 | 40.0 / 65.2 / 92.2 | 1881 | 0 | 0.25 | 0.58 | site service |
| 1 | 50 | 272.9 ± 6.5 | 150.1 | 13.6 | 202.5 / 262.6 / 285.9 | 2250 | 0 | 0.47 | 0.34 | site service |
| 1 | 100 | 271.8 ± 9.6 | 149.5 | 13.6 | 412.6 / 510.6 / 545.3 | 4500 | 0 | 0.53 | 0.34 | not attributable |
| 2 | 1 | 103.2 ± 4.6 | 63.0 | 17.0 | 8.5 / 16.9 / 23.8 | 1949 | 0 | 0.07 | 0.31 | not attributable |
| 2 | 10 | 267.1 ± 11.5 | 165.1 | 44.7 | 37.5 / 60.8 / 82.6 | 1910 | 0 | 0.31 | 0.84 | not attributable |
| 2 | 50 | 517.3 ± 14.8 | 284.5 | 25.9 | 90.7 / 178.2 / 204.6 | 2250 | 0 | 0.83 | 0.57 | site service |
| 2 | 100 | 522.5 ± 6.2 | 287.4 | 26.1 | 164.4 / 361.0 / 409.3 | 4500 | 0 | 0.93 | 0.58 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 5 | 1 | 85.2 ± 3.8 | 52.0 | 14.1 | 9.3 / 28.9 / 40.4 | 1949 | 0 | 0.07 | 0.60 | not attributable |
| 5 | 10 | 218.0 ± 4.8 | 134.9 | 36.6 | 45.5 / 78.4 / 105.2 | 1907 | 0 | 0.27 | 1.41 | not attributable |
| 5 | 50 | 656.7 ± 14.4 | 361.2 | 32.8 | 76.1 / 109.7 / 124.5 | 2250 | 0 | 1.18 | 0.71 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 5 | 100 | 682.7 ± 8.6 | 375.5 | 34.1 | 129.5 / 238.4 / 314.0 | 4499 | 1 | 1.19 | 0.72 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 10 | 1 | 67.4 ± 0.8 | 41.1 | 11.1 | 9.6 / 54.5 / 62.0 | 1949 | 0 | 0.06 | 1.05 | not attributable |
| 10 | 10 | 163.6 ± 5.8 | 101.6 | 27.9 | 58.1 / 115.2 / 141.7 | 1893 | 0 | 0.21 | 2.04 | not attributable |
| 10 | 50 | 680.2 ± 23.4 | 374.1 | 34.0 | 73.3 / 106.0 / 124.5 | 2250 | 0 | 1.17 | 0.73 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 10 | 100 | 670.2 ± 9.6 | 368.6 | 33.5 | 133.4 / 246.5 / 321.0 | 4500 | 1 | 1.18 | 0.71 | client-limited (load generator >= 0.85 core): not attributable to the service |

- N=2 vs N=1 at W=50: 1.90x [1.84, 1.95]
- N=2 vs N=1 at W=100: 1.92x [1.87, 1.98]
- N=5 vs N=1 at W=50: 2.41x [2.35, 2.47]
- N=5 vs N=1 at W=100: 2.51x [2.44, 2.58]
- N=10 vs N=1 at W=50: 2.49x [2.41, 2.57]
- N=10 vs N=1 at W=100: 2.47x [2.39, 2.54]

