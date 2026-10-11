"""Analysis of B5, (a') at `degraded` (audit 46, rules left open closed in audit 50). Local only; reuses analyze_b1.py unchanged (medians/bootstrap,
last_site, lan_reference, rule R-gp, exclusion by overlap). Tests: test_analyze_b5.py (written first). Not run on data when this file was committed.
Usage: python3 analyze_b5.py <degraded block dir with b1_*/> --lan-ref <lan_before dir> --lan-ref <lan_after dir> [--profile-events <block>/profile_events.jsonl]
       [--watch-log watch2_stdout.log] [--out report.md]
(c) is NOT recomputed here: run analyze_c.py (unchanged) on the same dir."""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "m67_retraction"))
import analyze_b1 as b1  # noqa: E402
import blockdata  # noqa: E402
import run as m67  # noqa: E402

P_HI = {"D": 0.226, "C": 0.401}      # upper end of the registered range (audit 46 s.2 / a14:236-237): verdict 1 (audit 50 s.1)
P_LO = {"D": 0.185, "C": 0.302}      # lower end: descriptive only
N_RTT = {"D": 2, "C": 3}


def expected_failures(p: float) -> float:
    return p + p ** 2 + p ** 3


def physical_ms(arm: str, fanout: int, R: float) -> float:
    return 1000 * N_RTT[arm] * R * (10 if fanout == 1 else 1)


def threshold_ms(arm: str, fanout: int, R: float, ref_median_ms: float, p: float) -> float:
    return physical_ms(arm, fanout, R) + 1000 * expected_failures(p) + 3 * ref_median_ms


def verdicts(t, thr: float, phys: float) -> tuple[str, str]:
    """t = (median, lo, hi, n) ms. Verdict 1 against the threshold, verdict 2 against the physical bound (independent)."""
    v1 = "falsified" if t[1] > thr else ("inconclusive" if t[0] > thr else "not falsified")
    v2 = "base model falsified" if t[2] < phys else "ok"
    return v1, v2


def _has_pending(r: dict) -> bool:
    return any(n for n in (r.get("pending_after_response") or {}).values()) or any(n for n in (r.get("pending_left") or {}).values()) \
        or any(t is not None for t in (r.get("plog_ack_ts") or {}).values())


def completed_values(rows: list, measure: str) -> list:
    """Withdrawal times (ms) of COMPLETED episodes only: not excluded, with a recorded response, no pending delivery."""
    if measure == "last":
        return b1.last_site(rows)
    return [1000 * r["dispute_rtt_s"] for r in rows if not r.get("excluded") and "dispute_rtt_s" in r and not _has_pending(r)]


def global_verdict(cells: list[dict]) -> dict:
    ev = [c for c in cells if c["v1"] != "not evaluable"]
    n1 = sum(1 for c in ev if c["v1"] == "falsified")
    n2 = sum(1 for c in ev if c["v2"] == "base model falsified")
    return {"a_prime": "falsified" if n1 else "not falsified", "a_prime_k": (n1, len(ev)),
            "base": "base model falsified" if n2 else "ok", "base_k": (n2, len(ev)), "not_evaluable": len(cells) - len(ev)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--lan-ref", action="append", required=True)
    ap.add_argument("--profile-events", default=None)
    ap.add_argument("--watch-log", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cells, man = blockdata.load_block(Path(a.dir))
    prof = man["profile"]
    assert prof == "degraded", f"B5 is a `degraded` block, got {prof}"
    full = [c for c in cells if "rows" in c and "aborted" not in c]
    _, _, ov_text = b1.overlap_exclusion(full, a.profile_events, Path(a.watch_log).read_text() if a.watch_log else None)
    rng = random.Random(b1.SEED)
    refs = b1.lan_reference(a.lan_ref, rng)
    R = m67.PROFILES[prof]["R"]
    L = [f"# B5 analysis, (a') at `{prof}` (audits 46, 50); tree `{man['node_tree']}`, seed {man['seed']}, started {man['started_utc']}", "",
         "| arm | FANOUT | measure | n completed | median ms [CI] | physical bound ms | threshold ms (p hi) | threshold ms (p lo, descriptive) | verdict 1 | verdict 2 |", "|---|---|---|---|---|---|---|---|---|---|"]
    out = []
    for c in sorted(full, key=lambda c: (c["cell_spec"]["arm"], c["cell_spec"]["fanout"])):
        arm, fo = c["cell_spec"]["arm"], c["cell_spec"]["fanout"]
        measure = "last" if c["summary"]["plog_acceptable_rule_10pct"] and b1.last_site(c["rows"]) else "rtt"
        vals = completed_values(c["rows"], measure)
        t = b1.med_ci(vals, rng)
        if t is None:
            out.append({"arm": arm, "fanout": fo, "v1": "not evaluable", "v2": "not evaluable"})
            L.append(f"| {arm} | {fo} | {measure} | 0 | — | | | | not evaluable: no completed episode | not evaluable |")
            continue
        ref = refs[(arm, fo, measure if measure == "last" else "rtt")][0]
        phys = physical_ms(arm, fo, R)
        thr_hi, thr_lo = threshold_ms(arm, fo, R, ref, P_HI[arm]), threshold_ms(arm, fo, R, ref, P_LO[arm])
        v1, v2 = verdicts(t, thr_hi, phys)
        why = b1.gp_not_evaluable(c, prof)
        if why:
            v1 = "not evaluable"
        out.append({"arm": arm, "fanout": fo, "v1": v1, "v2": v2})
        L.append(f"| {arm} | {fo} | {measure} | {t[3]} | {b1.fmt(t)} | {phys:.1f} | {thr_hi:.1f} | {thr_lo:.1f} | {v1 if not why else 'not evaluable: ' + why} | {v2} |")
    g = global_verdict(out)
    L += ["", f"**Global (audit 46/50):** (a') {g['a_prime']} ({g['a_prime_k'][0]}/{g['a_prime_k'][1]} cells); base model {g['base']} "
          f"({g['base_k'][0]}/{g['base_k'][1]} cells); cells not evaluable (R-gp): {g['not_evaluable']}.",
          "Statute: replication on the same node and profile as the block that falsified (a); not an independent test."] + ov_text
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        Path(a.out).write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
