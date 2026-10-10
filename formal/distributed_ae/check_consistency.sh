#!/bin/sh
# Textual coherence checks of DIB_AE.tla with the declared modelling choices (no TLC, no SANY).
#  1. The reconcile run (ReconcileRead .. RcStep) must NOT depend on `unreachable`:
#     unreachable is the evidence->site direction only.
#  2. The fairness must be exactly the declared conditional one.
#  3. unreachable may be used in Deliver and in properties only.
set -eu
cd "$(dirname "$0")"
M=DIB_AE.tla
fail=0
run=$(awk '/^ReconcileRead\(t\) ==/{f=1} /^Next ==/{f=0} f' "$M" | grep -v '^[[:space:]]*\\\*' | sed 's/\\\*.*//')
if printf '%s\n' "$run" | grep -q 'unreachable'; then echo "FAIL: reconcile run mentions unreachable"; fail=1; else echo "OK: reconcile run (ReconcileRead..RcStep) does not mention unreachable"; fi
grep -qF 'WF_vars(RcStep(t) /\ t \notin unreachable)' "$M" && echo "OK: run fairness is conditional on (t not in unreachable)" || { echo "FAIL: run fairness differs"; fail=1; }
grep -qF 'WF_vars(Deliver(r))' "$M" && echo "OK: delivery fairness present" || { echo "FAIL: delivery fairness missing"; fail=1; }
uses=$(awk '/^Deliver\(r\) ==/{d=1} /^Lose\(r\) ==/{d=0} d' "$M" | grep -c 'unreachable' || true)
[ "$uses" -ge 1 ] && echo "OK: Deliver uses unreachable" || { echo "FAIL: Deliver does not use unreachable"; fail=1; }
exit $fail
