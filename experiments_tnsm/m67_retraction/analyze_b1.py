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
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out", default=None)
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
        L.append(f"| {sp['arm']} | {sp['fanout']} | {s['episodes']} | {s['excluded']} {s['excluded_by_cause'] or ''} | {fmt(med_ci(rtt, rng))} | {fmt(med_ci(last, rng))} | "
                 f"{g['median']:.2f}, {g['max_abs']:.2f} | {s['plog_acceptance_ratio']:.3f} ({'accepted' if accepted else 'NOT accepted'}) | {measure} | "
                 f"{s['n_pending_sites_log']}/{s['n_pending_sites_read']}/{s['read_undercount_sites']} | {s['ack_lines_total']}/{s['ack_lines_max_per_site_episode']} |")
    L += ["", "## Exclusions by cause (all cells)", "", "| arm | FANOUT | client_timeout | queues_not_empty_at_start | transport_error_setup | transport_error_measured | flagged by discard rule |", "|---|---|---|---|---|---|---|"]
    for key, v in sorted(by.items()):
        c = v["cell"]
        rows = c["rows"]
        n = lambda reason: sum(1 for r in rows if r.get("excluded_reason") == reason)  # noqa: E731
        L.append(f"| {key[0]} | {key[1]} | {sum(1 for r in rows if r.get('client_timeout'))} | {n('queues_not_empty_at_start')} | {n('transport_error_setup')} | {n('transport_error_measured')} | {c['flagged_pre']} |")
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
    L += ["", "## Prediction (a) at `lan` (rule: falsified if median > n_RTT*R*(10 if FANOUT 1) + 3 x median `lan` of the same arm, beyond the CI)", "",
          "| arm | FANOUT | measure | median ms [CI] | n_RTT*R*(x10) ms | 3 x lan median ms (same arm, same FANOUT) | threshold ms | CI lower > threshold? |", "|---|---|---|---|---|---|---|---|"]
    R = m67.PROFILES[prof]["R"]
    for key, v in sorted(by.items()):
        arm, fo = key
        t = med_ci(v["values"], rng)
        k = 10 if fo == 1 else 1
        pred = 1000 * m67.N_RTT[arm] * R * k
        thr = pred + 3 * t[0]
        L.append(f"| {arm} | {fo} | {v['measure']} | {fmt(t)} | {pred:.2f} | {3 * t[0]:.2f} | {thr:.2f} | {t[1] > thr} |")
    L += ["", "**Degenerate at `lan`**: the reference is the cell itself, so the threshold always exceeds the median; the verdict is False by construction and carries no information. "
          "Lan medians for both FANOUT values of each arm are in the table above, so the wan rule can be evaluated with either reading of 'same arm' (same FANOUT, or any FANOUT): "
          "the choice is open and must be declared before the wan block is analysed."]
    L += ["", "## Differences between arms (median difference, bootstrap CI over episodes)", ""]
    for fo, label in ((1, "FANOUT 1 (P-a4: +23.5 ms, falsified if CI outside [15, 32])"), (10, "FANOUT 10 (no registered interval; descriptive)")):
        for q, name in (("last", "last-site P-log"), ("rtt", "dispute-rtt")):
            cd, dd = by.get(("C", fo)), by.get(("D", fo))
            if cd and dd and cd[q] and dd[q]:
                x = diff_ci(cd[q], dd[q], rng)
                verdict = ""
                if fo == 1 and q == "last":
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
