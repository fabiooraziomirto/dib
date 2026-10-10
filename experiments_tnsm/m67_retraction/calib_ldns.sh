#!/usr/bin/env bash
# L_dns calibration (V5, audit 14; audit 18). Runs ON THE NODE with the dibtnsm cluster up.
# No sudo. Measures, from INSIDE the evidence container, the duration of
# socket.getaddrinfo('site-3', 8000) - the call httpcore makes before connecting
# (httpcore/_backends/sync.py:208) - 50 times with site-3 alive (control), then after
# `docker compose kill site-3` (B2-kill), then restarts site-3.
# Declared before running: no hypothesis test; the result picks the B2 variant
# (<= 50 ms: both variants; >= 0.5 s: only B2-partition + kill-min; in between: user decides).
# Usage: calib_ldns.sh <compose-file> <project-dir> <label> [<override-compose-file>]
#   label = profile name, e.g. lan; the optional 4th argument is the arm-D override (launcher_d.py)
set -euo pipefail
export PATH=/snap/bin:$PATH
CF=$1; PD=$2; LABEL=$3; OV=${4:-}
DC="docker compose -p dibtnsm -f $CF ${OV:+-f $OV} --project-directory $PD"
probe() {
  docker exec dibtnsm-evidence-1 python -c '
import socket, time, json
r = []
for _ in range(50):
    t = time.perf_counter()
    try:
        socket.getaddrinfo("site-3", 8000); ok = True
    except OSError as e:
        ok = repr(e)
    r.append((time.perf_counter() - t, ok))
d = sorted(x for x, _ in r)
print(json.dumps({"n": len(d), "p50_ms": 1000 * d[len(d) // 2], "p95_ms": 1000 * d[int(0.95 * len(d)) - 1],
                  "max_ms": 1000 * d[-1], "outcomes": sorted({str(o) for _, o in r})}))'
}
echo "{\"label\": \"$LABEL\", \"alive\": $(probe),"
$DC kill site-3 >/dev/null 2>&1
echo " \"killed\": $(probe)}"
$DC start site-3 >/dev/null 2>&1
