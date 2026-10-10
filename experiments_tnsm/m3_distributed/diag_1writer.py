"""Diagnosis of the M3/M4 anomaly (audit 18 s.1; user decision 2026-10-10): with mTLS the
throughput at 1 and 10 writers was HIGHER (209-213 vs 112-116 ops/s at 1 writer), which a TLS
cost cannot explain. Time-boxed to ~1 hour. Diagnostic, NOT a confirmatory measurement.

Three server configurations, FANOUT 10, same image, same compose generator, same benchmark:
  A  plain, container CMD `uvicorn service:app` (as in M3)               [DIB_DIST_MTLS=0]
  B  plain, SAME LAUNCHER AS THE mTLS ARM without TLS: uvicorn.Server(uvicorn.Config(
     'service:app', http=PeerCertH11Protocol)) via a compose override `command:`
     (mtls.py:91-95,158; PeerCertH11Protocol returns early without ssl_object, mtls.py:59-62)
     [DIB_DIST_MTLS=0, override file]
  C  mTLS (as in M3)                                                      [DIB_DIST_MTLS=1]
Per cell: writers 1 and 10, 200 timed ops + 20 warm-up per worker; the latency PER OPERATION
TYPE (the benchmark computes it, run_one_batch, but the CSV discards it) and the number of
uvicorn access-log lines on site-0 and evidence (P-log requirement: the access log must exist
in every mode). Idle background sample (other_cores, steal_pct, 12 s, containers excluded)
on the node before each cell. 5 repetitions, configurations shuffled per repetition.

Hypotheses (stated before running, from the code reading in audit 18; falsifiable):
  H-D1  The launcher explains the gap: throughput of B at 1 writer is closer to C than to A.
        Falsified if B's 95% bootstrap CI at 1 writer overlaps A's and not C's... precisely:
        |mean(B) - mean(A)| < |mean(B) - mean(C)|  -> NOT launcher; otherwise launcher.
  H-D2  The access log is present in all three configurations (>= 90% of the requests that
        reach site-0 appear as `"POST /...` lines). Falsified otherwise.
Reading: if B ~ A (and C differs), the launcher is excluded and the cause is TLS-path or
app-path (service.py MTLS branch) related; if B ~ C, the launcher is the cause and the plain
arms of M3 must be rerun with the identical launcher (~20 cells).
Usage: python3 diag_1writer.py --out <dir> --pki-local <dir> --tree '~/dib_tnsm/tree-<c>'
