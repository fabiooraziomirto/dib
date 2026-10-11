"""Analysis of a B1 run of run.py (one profile), local only. Written 2026-10-11 BEFORE it was run on the `lan` data
(`lan_20261011/b1/`, tree bf272e8, copy verified by sha256 of cells.jsonl on both sides).
Hypotheses, declared first:
  H-lan-degenerate: at `lan` the rule of prediction (a) (falsified if median > n_RTT*R*(10 if FANOUT 1) + 3 x median of `lan` of the
     same arm) cannot be falsified, because the cell is its own reference (threshold = 0.2-0.3 ms (x10) + 3 x median > median).
     The script reports the threshold and the verdict mechanically and flags the degeneracy; it does not tune anything.
  P-a4 (frozen, 6c11e48): C - D, last site, FANOUT 1, lan: +23.5 ms; falsified if the bootstrap CI of the difference of medians is
     outside [15, 32] ms. P-a1/P-a2 (default - D) cannot be evaluated: no `default` cells in this run (reported as such).
     C - D at FANOUT 10 has no registered interval: descriptive only.
Rules FIXED 2026-10-11 AFTER seeing the `lan` data, and with the `wan` data of the night (first run, tree 6b8a6fa) already seen:
  - (a) at `wan`: the reference is the median at `lan` of the SAME arm AND the SAME FANOUT (same session of the rerun); this script already
    pairs them that way. Written here and in docs/audit/25 and not in run.py (run.py and its sha256 are frozen: no new tree).
  - Criteria written "falsified if the CI is outside [a, b]" are ambiguous (not inside vs entirely outside). Reading from now on, as in (c):
    FALSIFIED only if the CI is ENTIRELY outside [a, b]; a CI that crosses a bound is reported "inconclusive" with point estimate and CI.
    For P-a4 as registered (6c11e48) the text is ambiguous: reported "criterio ambiguo, non conclusivo".
Reference for rule (a) at `wan` (decided 2026-10-11 BEFORE any `wan` data of the rerun; chosen AFTER seeing that two `lan` sessions of the
same day gave different D values: D FANOUT 1 P-log 67.3 [62.8; 82.1] ms at 07:52 UTC vs 48.4 [45.4; 51.9] ms at 08:27 UTC, CIs not overlapping;
a drift of the node of the same order as the sought signal, so neither of those sessions is the reference; both stay in the report as "two lan sessions"):
  reference = the `lan` cells ADJACENT to the `wan` block, same session: D and C, FANOUT 1 and 10, 10 episodes, mixed order, run immediately
  BEFORE `wan` (watcher stopped, netem_show.sh clean, checked by the user) and, if time allows, immediately AFTER. Same arm, same FANOUT.
  If the before/after sessions differ, the HIGHER median is used (the reference most favourable to the prediction: if the prediction is violated
  anyway, the conclusion is robust). Pass them with --lan-ref <dir> (repeatable). Threshold = n_RTT*R*(10 if FANOUT 1) + 3 x reference median;
  verdict "falsified" if the median exceeds it with the CI lower bound above it, "inconclusive" if the median exceeds it but the CI crosses it,
  "not falsified" otherwise; the observed excess is always reported; the model is not adapted.
Note: the criterion is applied by this script (analyze_b1.py); its pre-registered version is commit 8b7b45e, which predates the `wan` data of
the rerun. run.py is not touched.
Rule R-gp FIXED 2026-10-11, AFTER the two `degraded` smokes (second smoke: calibration `generator_path_ms` reused 944.4 ms with reused_ok False, first smoke 202.3 ms ok,
unexplained) and BEFORE any `degraded` B1 datum: at a non-`lan` profile, a cell whose group-start generator_path_ms (the manifest/cell field written by run.py)
has reused_ok FALSE gets NO verdict for prediction (a): the table says "not evaluable: reused X ms outside +-20% of d (reused_ok false)"; its medians and CIs stay
in the report; the cell is NOT excluded, NOT re-run (a group that produced data is never relaunched) and no threshold or other rule changes. Why `reused`: the
generator measures on a kept-alive connection, which is the path reused_ok describes. fresh_ok False alone stays informational (the C arm has no fresh expectation).
At `lan` the flags carry no meaning and are ignored. A flag raised only in the CALIBRATION (calib_profile.py) is recorded and does not stop a block: the thresholds
come from the log-latency p95, not from the generator path. Prediction (c) (pending counts) does not use timing and is evaluated regardless.
Rule FIXED 2026-10-11, AFTER the `degraded` smoke and BEFORE any `degraded` B1 datum (the smoke data are not analysed): EXCLUSION BY OVERLAP WITH A
TRANSIENT INCOHERENCE OF THE NETEM PROFILE. The monitor of auto_block.py writes, in `<block>/profile_events.jsonl`, one `transient` row for every stretch in
which profile.applied listed all 11 containers but one or more did not carry the expected qdisc (smoke: site-8 without netem for ~1.4 s while the cluster
was being created); `from_ms` = epoch (ms) of the record BEFORE the incoherent one (the qdisc was missing from some point after it), `end_ms` = epoch of the
first coherent record after it (clock of the node, the same as t0). An EPISODE is excluded, cause `profile_incoherent_overlap`, if its window
[t0, t_end] (t_end = the largest of t_resp, plog_apply_ts of every site, plog_ack_ts when present) intersects [from_ms/1000, end_ms/1000] (closed interval,
no margin, no tolerance). Excluded episodes are counted apart from the other causes, never replaced and never re-run; the intervals are listed verbatim
in the report; a cell with no episode left is reported as such. The same stretches are NOT used to change thresholds, measure types or any other rule.
Related stop rules of the orchestrator (not exclusions): an incoherence lasting more than 10 s without a coherent record, or more than 3 transient
incoherences within 60 s, stops the block.
EXTENSION (same date, still before any `degraded` B1 datum): the intervals of the WATCHER'S OWN LOG count too. From watch2.log, an UNSETTLED-PROFILE interval
starts at a line `containers changed -> applying`, `request accepted`, `apply FAILED`, `the set of containers changed during the application` or
`profile.applied NOT written`, and ends at the next `applied ...` (or `profile.applied written after ...`) line; start lines with no `applied` between them
make one interval from the first; with no end the interval is open. An episode whose window overlaps such an interval is excluded with the same cause
(`profile_incoherent_overlap`, the source `monitor` or `watch2.log` is recorded per episode). The watcher's times are the node's UTC ms, the same clock as t0.
Both inputs are passed with --profile-events <block>/profile_events.jsonl and --watch-log <watch2.log>; without them at a non-`lan` profile the report
carries a WARNING line and no episode is excluded for this rule.
STATUS: the rule (profile_exclusion.py, the helper overlap_exclusion here, the report section and the two options) is written and tested on SYNTHETIC rows
(test_profile_exclusion.py); it has NOT been run on any real data.
Method: medians with 95% percentile bootstrap CI over EPISODES (10000 resamples, seed 20261011); with n = 10 the CI is coarse.
"last site" = max over the 10 sites of the P-log withdrawal (withdrawn_plog_s) of an episode without pending deliveries;
dispute-rtt = response - t0 (bias 0 at lan, run.dispute_rtt_bias_s). Measure type per cell by the recorded rule: P-log (apply)
if the calibrated p95 (default 2.5 ms, audit 18 s.1.9; --plog-p95-ms was not passed) is < 10% of the cell's median direct
withdrawal, else dispute-rtt. Nothing is explained beyond the data.
Falsification of the script: it must reproduce the per-cell summaries recorded in cells.jsonl (medians, counts).
Usage: python3 analyze_b1.py <dir with cells.jsonl and manifest.json> [--out analysis.md]"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import profile_exclusion as px  # noqa: E402
import run as m67  # noqa: E402

RES, SEED = 10000, 20261011


def med_ci(xs, rng):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    ms = sorted(statistics.median(rng.choices(xs, k=len(xs))) for _ in range(RES))
    return statistics.median(xs), ms[int(0.025 * RES)], ms[int(0.975 * RES) - 1], len(xs)


def diff_ci(a, b, rng):
    """median(a) - median(b), independent bootstrap of each sample."""
    ds = sorted(statistics.median(rng.choices(a, k=len(a))) - statistics.median(rng.choices(b, k=len(b))) for _ in range(RES))
    return statistics.median(a) - statistics.median(b), ds[int(0.025 * RES)], ds[int(0.975 * RES) - 1]


def ms(t):
    return None if t is None else tuple(1000 * x if i < 3 else x for i, x in enumerate(t))


def fmt(t):
    return "—" if t is None else f"{t[0]:.2f} [{t[1]:.2f}; {t[2]:.2f}] (n={t[3]})"


def last_site(rows):
    out = []
    for r in rows:
        if r.get("excluded") or "dispute_rtt_s" not in r:
            continue
        pend = any(n for n in (r.get("pending_after_response") or {}).values()) or any(n for n in (r.get("pending_left") or {}).values()) \
            or any(t is not None for t in (r.get("plog_ack_ts") or {}).values())
        v = [x for x in (r.get("withdrawn_plog_s") or {}).values() if x is not None]
        if not pend and len(v) == m67.N_SITES:
            out.append(1000 * max(v))
    return out


def overlap_exclusion(full_cells, profile_events, watch_log_text):
    """Applies the exclusion-by-overlap rule of the docstring to the rows of the complete cells (in place). Returns (labelled intervals, {(arm, fanout):
    newly excluded}, report text). With no input the report says so explicitly."""
    labelled = []
    if profile_events:
        labelled += [("monitor", iv) for iv in px.monitor_intervals(profile_events)]
    if watch_log_text:
        labelled += [("watch2.log", iv) for iv in px.watch_unsettled_intervals(watch_log_text)]
    if not profile_events and not watch_log_text:
        return [], {}, ["", "## Exclusion by overlap with an unsettled netem profile", "",
                        "**NOT applied**: neither --profile-events nor --watch-log was given (the rule is in the docstring; no episode was excluded for it)."]
    per_cell, used_all, lo, hi = {}, [], float("inf"), float("-inf")
    for c in full_cells:
        n, used = px.mark_overlaps(c["rows"], labelled)
        per_cell[(c["cell_spec"]["arm"], c["cell_spec"]["fanout"])] = n
        used_all += [u for u in used if u not in used_all]
        for r in c["rows"]:
            if "t0" in r:
                w = px.episode_window(r)
                lo, hi = min(lo, w[0]), max(hi, w[1])
    shown = [(lab, iv) for lab, iv in labelled if px.overlaps((lo, hi), [iv])]
    fmt_t = lambda x: "open" if x == float("inf") else datetime.fromtimestamp(x, timezone.utc).strftime("%H:%M:%S.%f")[:-3]  # noqa: E731
    text = ["", "## Exclusion by overlap with an unsettled netem profile (cause `profile_incoherent_overlap`)", "",
            "Excluded episodes per cell: " + (", ".join(f"{k[0]}/{k[1]}: {v}" for k, v in sorted(per_cell.items())) or "none"),
            "", "Intervals overlapping the block's time range, verbatim (UTC):", ""]
    text += [f"- {lab}: {fmt_t(iv[0])} → {fmt_t(iv[1])}{'  **excluded at least one episode**' if (lab, iv) in used_all else ''}" for lab, iv in shown] or ["- none"]
    return labelled, per_cell, text


def gp_not_evaluable(cell, profile):
    """Rule R-gp (docstring): None, or the reason (text) when prediction (a) must be reported `not evaluable` for this cell: non-lan profile and the
    group-start generator_path_ms of the cell has reused_ok False."""
    if profile == "lan":
        return None
    gp = ((cell.get("profile_timing") or {}).get("generator_path_ms")) or {}
    if gp.get("reused_ok") is False:
        return f"reused {gp.get('reused_ms'):.1f} ms outside +-20% of d (reused_ok false)"
    return None


def verdict_text(ra, cell, profile):
    why = gp_not_evaluable(cell, profile)
    return f"not evaluable: {why}" if why else ra["verdict"]


def rule_a(t, pred_ms, ref_median_ms):
    """t = (median, lo, hi, n) in ms. Threshold = pred + 3 x reference median; excess = median - threshold."""
    thr = pred_ms + 3 * ref_median_ms
    verdict = "falsified" if t[1] > thr else ("inconclusive" if t[0] > thr else "not falsified")
    return {"threshold_ms": thr, "excess_ms": t[0] - thr, "verdict": verdict}


def lan_reference(dirs, rng):
    """{(arm, fanout, measure): highest lan median over the reference sessions} for measure in {last, rtt}."""
    ref = {}
    for d in dirs:
        for line in (Path(d) / "cells.jsonl").read_text().splitlines():
            c = json.loads(line)
            if "rows" not in c or "aborted" in c:
                continue
            sp, rows = c["cell_spec"], c["rows"]
            vals = {"last": last_site(rows), "rtt": [1000 * r["dispute_rtt_s"] for r in rows if not r.get("excluded") and "dispute_rtt_s" in r]}
            for q, v in vals.items():
                if v:
                    k = (sp["arm"], sp["fanout"], q)
                    ref.setdefault(k, []).append((statistics.median(v), str(d)))
    return {k: max(v) for k, v in ref.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--profile-events", default=None, help="<block>/profile_events.jsonl of auto_block.py (transient incoherences of the monitor)")
    ap.add_argument("--watch-log", default=None, help="watch2.log of the watcher v2 (unsettled-profile intervals)")
    ap.add_argument("--lan-ref", action="append", default=[], help="adjacent `lan` session dir(s) for rule (a) at a non-lan profile (higher median used)")
    a = ap.parse_args()
    d = Path(a.dir)
    cells = [json.loads(x) for x in (d / "cells.jsonl").read_text().splitlines()]
    man = json.loads((d / "manifest.json").read_text())
    prof = man["profile"]
    rule = man["discard_rule"]
    rng = random.Random(SEED)
    L = ["# B1 analysis, profile `%s` (run.py sha256 `%s`, tree `%s`, seed %s)" % (prof, man["run_py_sha256"][:12], man["node_tree"], man["seed"]),
         f"started {man['started_utc']}, finished {man.get('finished_utc')}, aborted: {man.get('aborted')}", ""]
    full = [c for c in cells if "rows" in c and "aborted" not in c]
    L.append(f"cells in file: {len(cells)}; complete: {len(full)}; partial/aborted: {len(cells) - len(full)}")
    labelled, per_cell_ov, ov_text = overlap_exclusion(full, a.profile_events, Path(a.watch_log).read_text() if a.watch_log else None)
    if prof != "lan" and not (a.profile_events or a.watch_log):
        L.append("**WARNING: exclusion by overlap NOT applied (no --profile-events / --watch-log)**")
    by = {}
    L += ["", "## Per cell", "", "| arm | FANOUT | n | excl. | dispute-rtt ms | last-site P-log ms | gap rtt - P-log ms (med, max) | P-log ratio | measure | pending sites (log/read/undercount) | ack lines (tot/max) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in sorted(full, key=lambda c: (c["cell_spec"]["arm"], c["cell_spec"]["fanout"])):
        s, sp = c["summary"], c["cell_spec"]
        key = (sp["arm"], sp["fanout"])
        rows = c["rows"]
        rtt = [1000 * r["dispute_rtt_s"] for r in rows if not r.get("excluded") and "dispute_rtt_s" in r]
        last = last_site(rows)
        by[key] = {"rtt": rtt, "last": last, "cell": c}
        accepted = s["plog_acceptable_rule_10pct"]
        measure = "P-log-apply" if (accepted and last) else "dispute-rtt"
        by[key]["measure"] = measure
        by[key]["values"] = last if measure == "P-log-apply" else rtt
        g = s["plog_minus_response_gap_ms"]
        L.append(f"| {sp['arm']} | {sp['fanout']} | {s['episodes']} | {s['excluded']} {s.get('excluded_by_cause') or ''} | {fmt(med_ci(rtt, rng))} | {fmt(med_ci(last, rng))} | "
                 f"{g['median']:.2f}, {g['max_abs']:.2f} | {s['plog_acceptance_ratio']:.3f} ({'accepted' if accepted else 'NOT accepted'}) | {measure} | "
                 f"{s['n_pending_sites_log']}/{s['n_pending_sites_read']}/{s['read_undercount_sites']} | {s['ack_lines_total']}/{s['ack_lines_max_per_site_episode']} |")
    L += ["", "## Exclusions by cause (all cells)", "", "| arm | FANOUT | client_timeout | queues_not_empty_at_start | transport_error_setup | transport_error_measured | flagged by discard rule |", "|---|---|---|---|---|---|---|"]
    for key, v in sorted(by.items()):
        c = v["cell"]
        rows = c["rows"]
        n = lambda reason: sum(1 for r in rows if r.get("excluded_reason") == reason)  # noqa: E731
        L.append(f"| {key[0]} | {key[1]} | {sum(1 for r in rows if r.get('client_timeout'))} | {n('queues_not_empty_at_start')} | {n('transport_error_setup')} | {n('transport_error_measured')} | {c['flagged_pre']} |")
    L += ov_text
    L += ["", f"## Background and discard rule (other_cores > {rule['max_other_cores']} or steal_pct > {rule['max_steal_pct']} flags a cell)", "",
          "| arm | FANOUT | other_cores | steal_pct | flagged | generator proc cores mean/max | host busy % mean | near saturation |", "|---|---|---|---|---|---|---|---|"]
    for key, v in sorted(by.items()):
        c = v["cell"]
        bg, gl = c["background_idle"], c["generator_load"]
        L.append(f"| {key[0]} | {key[1]} | {bg['other_cores']} | {bg['steal_pct']} | {c['flagged_pre']} | {gl['gen_proc_cores_mean']:.3f}/{gl['gen_proc_cores_max']:.3f} | {gl['host_busy_pct_mean']:.1f} | {gl['near_saturation']} |")
    L += ["", "## generator_path_ms (reused / fresh, ms) and flags", "", "| arm | FANOUT | reused | fresh | reused_ok | fresh_ok | generator_path_flag |", "|---|---|---|---|---|---|---|"]
    flags = {x["cell"]: x["generator_path_flag"] for x in man["cells_summary"]}
    for key, v in sorted(by.items()):
        c = v["cell"]
        gp = c["profile_timing"]["generator_path_ms"]
        L.append(f"| {key[0]} | {key[1]} | {gp['reused_ms']:.2f} | {gp['fresh_ms']:.2f} | {gp['reused_ok']} | {gp['fresh_ok']} | {flags.get(c['cell'])} |")
    L += ["", "(at `lan` d = 0: the +-20% band is replaced by 0-3 ms; `fresh_ok` False/None carries no meaning here, audit 22.)"]
    if a.lan_ref and prof != "lan":
        refs = lan_reference(a.lan_ref, rng)
        L += ["", "## Prediction (a) with the adjacent `lan` reference (higher median over: %s)" % ", ".join(a.lan_ref), "",
              "| arm | FANOUT | measure | median ms [CI] | 10 x n_RTT x R (FANOUT 1) / n_RTT x R ms | reference lan median ms | threshold ms | excess over threshold ms | verdict |", "|---|---|---|---|---|---|---|---|---|"]
        R = m67.PROFILES[prof]["R"]
        for key, v in sorted(by.items()):
            arm, fo = key
            q = "last" if v["measure"] == "P-log-apply" else "rtt"
            t = med_ci(v["values"], rng)
            pred = 1000 * m67.N_RTT[arm] * R * (10 if fo == 1 else 1)
            rm = refs[(arm, fo, q)]
            ra = rule_a(t, pred, rm[0])
            L.append(f"| {arm} | {fo} | {v['measure']} | {fmt(t)} | {pred:.1f} | {rm[0]:.2f} ({rm[1]}) | {ra['threshold_ms']:.1f} | {ra['excess_ms']:.1f} | {verdict_text(ra, v['cell'], prof)} |")
    else:
        L += ["", "## Prediction (a) at `lan` (self-reference, degenerate)", "",
              "| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x own median ms | threshold ms | verdict |", "|---|---|---|---|---|---|---|---|"]
        R = m67.PROFILES[prof]["R"]
        for key, v in sorted(by.items()):
            arm, fo = key
            t = med_ci(v["values"], rng)
            pred = 1000 * m67.N_RTT[arm] * R * (10 if fo == 1 else 1)
            ra = rule_a(t, pred, t[0])
            L.append(f"| {arm} | {fo} | {v['measure']} | {fmt(t)} | {pred:.2f} | {3 * t[0]:.2f} | {ra['threshold_ms']:.2f} | {ra['verdict']} |")
        L += ["", "**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict carries no information."]
    L += ["", "## Differences between arms (median difference, bootstrap CI over episodes)", ""]
    for fo, label in ((1, "FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32])" if prof == "lan" else "FANOUT 1 (P-a4 is registered for `lan` only: not applicable here; descriptive)"), (10, "FANOUT 10 (no registered interval; descriptive)")):
        for q, name in (("last", "last-site P-log"), ("rtt", "dispute-rtt")):
            cd, dd = by.get(("C", fo)), by.get(("D", fo))
            if cd and dd and cd[q] and dd[q]:
                x = diff_ci(cd[q], dd[q], rng)
                verdict = ""
                if fo == 1 and q == "last" and prof == "lan":   # P-a4 is registered for `lan` only; at other profiles the difference is descriptive
                    inside = 15 <= x[1] and x[2] <= 32
                    outside = x[2] < 15 or x[1] > 32
                    verdict = " -> " + ("CI entirely inside [15, 32]" if inside else "CI entirely outside [15, 32]: falsified under the strict reading" if outside
                                         else "CI crosses a bound of [15, 32]: criterio ambiguo, non conclusivo (point estimate %s the interval)" % ("outside" if not 15 <= x[0] <= 32 else "inside"))
                L.append(f"- {label}, {name}: C - D = {x[0]:.2f} ms [{x[1]:.2f}; {x[2]:.2f}]{verdict}")
    L.append("- default - D (P-a1 +61.5 ms at FANOUT 1; P-a2 between +6 and +62 ms at FANOUT 10): **not evaluable**, no `default` cells in this run.")
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
