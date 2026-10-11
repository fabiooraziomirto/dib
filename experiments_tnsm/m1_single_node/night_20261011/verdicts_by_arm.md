# M1 per-arm verdicts (criteria of m1_single_node/run.py:12-30, verbatim)

- H-M1 [default, all, cells 30]: throughput (all ops) at 50 = 153.5 [140.4, 163.2], at 100 = 118.1 [111.9, 124.0] ops/s -> not falsified (falsified iff CI100 lower > CI50 upper)
- H-M1 [deploy, all, cells 30]: throughput (all ops) at 50 = 205.8 [193.0, 217.7], at 100 = 134.1 [127.5, 140.6] ops/s -> not falsified (falsified iff CI100 lower > CI50 upper)
- H-M1b [all, deploy cells 50]: deploy cells with unexpected errors = 27 -> FALSIFIED
- H-M1c [all, cells 40]: completed-ops throughput at 100: deploy 133.9 [127.2, 140.4] vs default 115.3 [109.0, 121.3] ops/s -> not falsified (falsified iff deploy CI upper < default CI lower)
- H-M1 [default, filtered, cells 30]: throughput (all ops) at 50 = 153.5 [140.2, 163.3], at 100 = 118.1 [111.9, 123.9] ops/s -> not falsified (falsified iff CI100 lower > CI50 upper)
- H-M1 [deploy, filtered, cells 29]: throughput (all ops) at 50 = 205.8 [193.0, 217.3], at 100 = 135.3 [128.9, 141.8] ops/s -> not falsified (falsified iff CI100 lower > CI50 upper)
- H-M1b [filtered, deploy cells 49]: deploy cells with unexpected errors = 26 -> FALSIFIED
- H-M1c [filtered, cells 39]: completed-ops throughput at 100: deploy 135.1 [128.4, 141.6] vs default 115.3 [109.2, 121.4] ops/s -> not falsified (falsified iff deploy CI upper < default CI lower)

# Pool-checkout censoring, reported separately (p99 >= 29.9 s with unexpected errors = ceiling of the 30 s checkout timeout, not a latency)

| arm | writers | cells | censored (p99 at the ceiling) | cells with unexpected errors | cells with a usable p99 |
|---|---|---|---|---|---|
| default | 1 | 10 | 0 | 0 | 10 |
| default | 10 | 10 | 0 | 1 | 10 |
| default | 50 | 10 | 1 | 10 | 9 |
| default | 100 | 20 | 20 | 20 | 0 |
| deploy | 1 | 10 | 0 | 0 | 10 |
| deploy | 10 | 10 | 0 | 0 | 10 |
| deploy | 50 | 10 | 0 | 7 | 10 |
| deploy | 100 | 20 | 0 | 20 | 20 |
