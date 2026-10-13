"""Judge A1-A7 of audit 119 sez. 4 from the two JSON results, independently of the
generators' own asserts (which abort a run, so a passing run already implies them;
this re-derives every count from the stored traces).

Writes summary.json and table.md next to the inputs. Exit code 0 iff every
criterion holds.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REFERENCE_SERVICE = "3ffa57ee549512e4d3341738c8ec052a86a3c11f4a05f37f82614868fc822af8"
EXPECTED = {  # policy -> (subject ACEs without fresh commit / 18, vetoes preserved / 6): audit 119 A1, A2
    "persistent_approval": (12, 6),
    "review_reset": (0, 0),
    "dib": (0, 6),
}


def judge_ablation(abl: dict) -> dict:
    out = {"service_sha256": abl["service_sha256"], "per_policy": {}, "criteria": {}}
    for policy, (exp_ace, exp_veto) in EXPECTED.items():
        cases = [c for c in abl["cases"] if c["policy"] == policy]
        finals = [next(t for t in c["trace"] if t["event"] == "restored_and_reconciled") for c in cases]
        aces = sum(sum(f["subject_aces"]) for f in finals)
        vetoes = sum(f["states"][0] == {"state": "revoked", "origin": "local", "last_applied_seq": f["states"][0]["last_applied_seq"]}
                     for f in finals)
        control_ok = all(t["control_aces"] == [1, 1, 1] for c in cases for t in c["trace"])
        offline_site2_exports = [f["subject_aces"][2] for c, f in zip(cases, finals) if c["disconnected"]]
        recovered = all(c["trace"][-1]["event"] == "explicit_recovery" and c["trace"][-1]["subject_aces"] == [1, 1, 1]
                        for c in cases)
        out["per_policy"][policy] = {
            "cases": len(cases), "subject_aces_without_fresh_commit": aces, "site_case_opportunities": 3 * len(cases),
            "vetoes_preserved": vetoes, "control_unchanged_every_step": control_ok,
            "disconnected_site2_subject_aces": offline_site2_exports, "explicit_recovery_all": recovered,
        }
        out["criteria"][f"A1 {policy}"] = aces == exp_ace
        out["criteria"][f"A2 {policy}"] = vetoes == exp_veto
        out["criteria"][f"A4 {policy}"] = control_ok
    out["criteria"]["A3 dib: disconnected site-2 exports nothing after reconcile"] = (
        out["per_policy"]["dib"]["disconnected_site2_subject_aces"] == [0, 0, 0])
    out["criteria"]["case count 18, distinct combinations 18"] = (
        len(abl["cases"]) == 18 and len({(c["policy"], c["veto_time"], c["disconnected"]) for c in abl["cases"]}) == 18)
    # A5/A6/A7 in the ablation are asserts inside case(); a completed case record means they held.
    out["criteria"]["A5/A6/A7 ablation asserts held (every case recorded)"] = all(
        c.get("stale_replay_ignored") and c.get("explicit_recovery_passed") for c in abl["cases"])
    return out


def judge_offline(ov: dict) -> dict:
    t = ov["trials"]
    n = len(t)
    counts = {
        "trials": n,
        "veto_local_after_restart": sum(x["after"]["veto"]["origin"] == "local" and x["after"]["veto"]["state"] == "revoked" for x in t),
        "stale_active_to_monitor_only": sum(x["after"]["active"]["state"] == "monitor-only" for x in t),
        "veto_and_stale_export_nothing": sum(x["exports_after_reconcile"]["veto"] == [0, 0, 0]
                                             and x["exports_after_reconcile"]["active"] == [0, 0, 0] for x in t),
        "unrelated_exports_everywhere": sum(x["exports_after_reconcile"]["unrelated"] == [1, 1, 1] for x in t),
        "repeated_reconcile_noop": sum(bool(x["repeated_reconcile_noop"]) for x in t),
        "stale_replay_ignored": sum(bool(x["stale_replay_ignored"]) for x in t),
        "direct_commit_over_veto_blocked": sum(bool(x["direct_commit_over_veto_blocked"]) for x in t),
        "explicit_recovery_passed": sum(bool(x["explicit_recovery_passed"]) for x in t),
        "pending_two_restores_seq3": sum(len(x["pending"]) == 2 and all(r["event_type"] == "restore" and r["seq"] == 3 for r in x["pending"]) for x in t),
    }
    crit = {
        "trials >= 30": n >= 30,
        "A2 veto preserved": counts["veto_local_after_restart"] == n,
        "A3 stale Active invalidated": counts["stale_active_to_monitor_only"] == n and counts["veto_and_stale_export_nothing"] == n,
        "A4 unrelated fact exported": counts["unrelated_exports_everywhere"] == n,
        "A5 idempotent reconcile": counts["repeated_reconcile_noop"] == n,
        "A6 stale replay ignored": counts["stale_replay_ignored"] == n,
        "A7 direct commit over veto blocked": counts["direct_commit_over_veto_blocked"] == n,
    }
    return {"service_sha256": ov["service_sha256"], "python": ov.get("python"), "counts": counts, "criteria": crit}


def main(directory: Path) -> int:
    abl = json.loads((directory / "restore_ablation.json").read_text())
    ov = json.loads((directory / "offline_veto.json").read_text())
    man = json.loads((directory / "manifest.json").read_text())
    a, o = judge_ablation(abl), judge_offline(ov)
    prov = {
        "ablation service = reference": abl["service_sha256"] == REFERENCE_SERVICE,
        "offline veto service = reference": ov["service_sha256"] == REFERENCE_SERVICE,
        "subprocess module = reference": man["subprocess_module_sha256"] == REFERENCE_SERVICE,
        "tree clean at run": man["dirty_files"] == [],
        "result hashes match manifest": all(
            hashlib.sha256((directory / f"{k}.json").read_bytes()).hexdigest() == v["result_sha256"]
            for k, v in man["runs"].items()),
        "generators exited 0": all(v["returncode"] == 0 for v in man["runs"].values()),
    }
    summary = {"provenance": prov, "ablation": a, "offline_veto": o}
    ok = all(prov.values()) and all(a["criteria"].values()) and all(o["criteria"].values())
    summary["all_criteria_hold"] = ok
    (directory / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    rows = ["| Policy | Subject ACEs without fresh commit | Vetoes preserved | Control fact unchanged |",
            "|---|---|---|---|"]
    for p, v in a["per_policy"].items():
        rows.append(f"| {p} | {v['subject_aces_without_fresh_commit']}/{v['site_case_opportunities']} | "
                    f"{v['vetoes_preserved']}/{v['cases']} | {'all steps' if v['control_unchanged_every_step'] else 'NO'} |")
    c = o["counts"]
    rows += ["", f"Offline veto ({c['trials']} trials, process kill/restart): " + ", ".join(
        f"{k} {v}/{c['trials']}" for k, v in c.items() if k != "trials")]
    (directory / "table.md").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))
    print("ALL CRITERIA HOLD" if ok else "SOME CRITERION FAILED: see summary.json")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent))
