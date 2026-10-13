### mtls

| Sites | Writers | attempted req/s | ok req/s | state-changing/s | p50 / p95 / p99 ms | 409 | unexpected | client cores | evidence cores | bottleneck |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 200.9 ± 6.2 | 122.6 | 33.2 | 4.7 / 6.8 / 9.1 | 1949 | 0 | 0.13 | 0.46 | not attributable |
| 1 | 10 | 409.9 ± 12.0 | 251.9 | 67.2 | 23.8 / 36.0 / 50.9 | 1927 | 0 | 0.37 | 1.09 | evidence service |
| 1 | 50 | 335.0 ± 6.6 | 184.2 | 16.7 | 164.2 / 208.0 / 233.0 | 2250 | 0 | 0.98 | 0.80 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 1 | 100 | 315.6 ± 5.6 | 173.6 | 15.8 | 352.7 / 427.6 / 461.5 | 4500 | 0 | 1.00 | 0.75 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 2 | 1 | 187.1 ± 7.3 | 114.1 | 30.9 | 4.9 / 8.3 / 10.8 | 1949 | 0 | 0.13 | 0.50 | not attributable |
| 2 | 10 | 400.3 ± 10.4 | 245.5 | 65.2 | 24.4 / 37.3 / 52.2 | 1933 | 0 | 0.37 | 1.16 | not attributable |
| 2 | 50 | 499.2 ± 12.0 | 274.6 | 25.0 | 98.8 / 135.0 / 161.1 | 2250 | 0 | 1.32 | 1.04 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 2 | 100 | 486.6 ± 12.0 | 267.6 | 24.3 | 204.2 / 264.8 / 307.8 | 4500 | 0 | 1.50 | 1.05 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 5 | 1 | 166.9 ± 3.0 | 101.8 | 27.5 | 5.0 / 13.0 / 15.2 | 1949 | 0 | 0.13 | 0.67 | not attributable |
| 5 | 10 | 339.9 ± 6.9 | 215.5 | 62.3 | 28.5 / 47.4 / 62.7 | 1830 | 0 | 0.34 | 1.38 | not attributable |
| 5 | 50 | 511.1 ± 5.9 | 281.1 | 25.6 | 98.9 / 126.7 / 146.5 | 2250 | 0 | 0.83 | 1.06 | evidence service |
| 5 | 100 | 501.2 ± 9.5 | 275.6 | 25.1 | 199.8 / 248.7 / 283.3 | 4500 | 0 | 1.14 | 1.05 | client-limited (load generator >= 0.85 core): not attributable to the service |
| 10 | 1 | 137.1 ± 1.9 | 83.7 | 22.6 | 5.4 / 21.7 / 24.8 | 1949 | 0 | 0.11 | 0.89 | not attributable |
| 10 | 10 | 252.1 ± 9.6 | 160.7 | 47.1 | 39.8 / 69.1 / 84.1 | 1811 | 0 | 0.28 | 1.53 | not attributable |
| 10 | 50 | 525.0 ± 17.1 | 288.7 | 26.2 | 95.9 / 126.1 / 144.8 | 2250 | 0 | 0.84 | 1.06 | evidence service |
| 10 | 100 | 533.7 ± 3.7 | 293.5 | 26.7 | 191.2 / 233.9 / 263.5 | 4500 | 0 | 0.93 | 1.06 | client-limited (load generator >= 0.85 core): not attributable to the service |

- N=2 vs N=1 at W=50: 1.49x [1.46, 1.53]
- N=2 vs N=1 at W=100: 1.54x [1.51, 1.58]
- N=5 vs N=1 at W=50: 1.53x [1.50, 1.55]
- N=5 vs N=1 at W=100: 1.59x [1.56, 1.62]
- N=10 vs N=1 at W=50: 1.57x [1.52, 1.61]
- N=10 vs N=1 at W=100: 1.69x [1.67, 1.71]

