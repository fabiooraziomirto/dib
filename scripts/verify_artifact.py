#!/usr/bin/env python3
"""Recompute every headline number of the paper from the stored evidence.

Each check reads a file under results/ or formal/ and asserts the value printed
for v42.0. Checks cover the indexed headline evidence, not every sentence.

Usage:  python scripts/verify_artifact.py [--with-tests]
"""
from __future__ import annotations

import argparse
import csv
import json
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASSED: list[str] = []
FAILED: list[str] = []


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="") as handle:
        return list(csv.DictReader(handle))


def text(relative: str) -> str:
    return (ROOT / relative).read_text(errors="replace")


def check(label: str, actual, expected, tol=0.0):
    try:
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            ok = abs(float(actual) - float(expected)) <= tol
        else:
            ok = actual == expected
    except (TypeError, ValueError):
        ok = False
    (PASSED if ok else FAILED).append(f"{label}: got {actual!r}, expected {expected!r}")
    print(("  ok   " if ok else "  FAIL ") + label + f"  [{actual}]")


# --- RQ1: formal model and lifecycle -------------------------------------
def check_formal() -> None:
    print("\nRQ1 finite model and registry")
    base = text("formal/logs/full_lifecycle.log")
    states = int(re.search(r"([\d,]+) states generated, ([\d,]+) distinct", base).group(2).replace(",", ""))
    check("base model distinct reachable states", states, 4311852)
    check("base model has no counterexample", "No error has been found" in base, True)

    ev = text("formal/logs/evidence_only.log")
    ev_states = int(re.search(r"([\d,]+) states generated, ([\d,]+) distinct", ev).group(2).replace(",", ""))
    check("no-commit model distinct states", ev_states, 2076196)
    check("no-commit model has no counterexample", "No error has been found" in ev, True)

    dist = text("formal/logs/distributed_extension.log")
    gen, distinct = re.search(r"([\d,]+) states generated, ([\d,]+) distinct", dist).groups()
    check("distributed extension states generated", int(gen.replace(",", "")), 815335)
    check("distributed extension distinct states", int(distinct.replace(",", "")), 48960)
    check("distributed extension depth", int(re.search(r"depth of the complete state graph search is (\d+)", dist).group(1)), 18)
    check("distributed extension has no counterexample", "No error has been found" in dist, True)

    for i, prop in enumerate(("AuthorizationStateCoherence", "I2_SiteConfinement", "ExportRequiresActive",
                             "DisputeSuspendsEverywhere", "I2_LocalRevokeConfinement",
                             "I3_GlobalRestorePreservesLocalRevoke"), 1):
        log = text(f"formal/mutations/m{i}/result.log")
        check(f"mutation m{i} violates {prop}", f"{prop} is violated" in log, True)

    check("focused registry/rescoring regression passes", "39 passed" in text("results/lifecycle_v35/regression.log"), True)

    campaign = json.loads(text("results/openwrt/campaign-10runs/campaign_summary.json"))
    check("OpenWrt campaign completed runs", campaign["completed_runs"], 10)
    check("OpenWrt campaign all pass", all(r["status"] == "pass" for r in campaign["runs"]), True)


# --- RQ2: coverage and proposal volume -----------------------------------
def check_utility() -> None:
    print("\nRQ2 coverage and proposal volume")
    funnel = {r["stage"]: r for r in rows("results/recall/recall_funnel.csv")}
    observed = float(funnel["observed_in_capture"]["macro_share"])
    staged = float(funnel["staged_by_dib"]["macro_share"])
    check("observable macro retention (%)", round(100 * staged / observed, 1), 63.2, 0.05)
    check("complete-profile macro recall (%)", round(100 * staged, 1), 7.9, 0.05)
    check("reference ACEs observable after filtering", int(funnel["observed_in_capture"]["matched_aces"]), 55)
    check("reference ACEs staged", int(funnel["staged_by_dib"]["matched_aces"]), 36)
    check("reference ACE base", int(funnel["all_reference_aces"]["total_aces"]), 564)

    abl = [r for r in rows("results/ablation_multiseed/summary.csv")
           if r["config"] == "graph_free" and r["variant"] == "full"]
    accepted = next(r for r in abl if r["metric"] == "accepted_count")
    f1 = next(r for r in abl if r["metric"] == "mean_f1_vs_ground_truth")
    check("graph-free accepted facts (20 seeds)", round(float(accepted["mean"]), 2), 344.55, 0.005)
    check("graph-free macro F1 (20 seeds)", round(float(f1["mean"]), 3), 0.104, 0.0005)

    cold = rows("results/cold_start/cold_start_local_vs_registry_detail.csv")
    mean = lambda k: sum(float(r[k]) for r in cold) / len(cold)
    check("DIB day-0 macro F1", round(mean("dib_day0_f1"), 3), 0.112, 0.0005)
    check("local-only 30-day macro F1", round(mean("local_only_30day_f1"), 3), 0.022, 0.0005)
    check("DIB + 30 days local macro F1", round(mean("dib_plus_30day_local_f1"), 3), 0.114, 0.0005)

    cost = {(r["receiver"], r["stage"]): r for r in rows("results/review_cost/review_cost.csv")}
    for receiver, union_cost, dib_cost in (("US", 5.46, 1.03), ("UK", 4.31, 1.16), ("YT", 28.31, 2.89)):
        check(f"{receiver} union entries per confirmed endpoint",
              round(float(cost[(receiver, "union")]["reviews_per_confirmed"]), 2), union_cost, 0.005)
        check(f"{receiver} DIB entries per confirmed endpoint",
              round(float(cost[(receiver, "DIB")]["reviews_per_confirmed"]), 2), dib_cost, 0.005)
    budget = {(r["receiver"], r["stage"]): r for r in rows("results/review_cost/fixed_budget.csv")}
    ratios = []
    for receiver in ("US", "UK", "YT"):
        dib = float(budget[(receiver, "DIB")]["expected_confirmed_at_budget"])
        union = float(budget[(receiver, "union")]["expected_confirmed_at_budget"])
        ratios.append(dib / union)
    check("equal-budget yield ratio, minimum", round(min(ratios), 1), 3.7, 0.05)
    check("equal-budget yield ratio, maximum", round(max(ratios), 1), 9.8, 0.05)

    ranked = {r["receiver"]: r for r in rows("results/union_ranked/union_ranked_budget.csv")}
    concentration = []
    for receiver, exp_ranked, exp_dib, exp_gap in (("US", 35.0, 35, 0), ("UK", 39.0, 37, 2), ("YT", 40.0, 37, 22)):
        row = ranked[receiver]
        check(f"{receiver} score-ranked union yield at budget",
              float(row["union_ranked_expected"]), exp_ranked, 0.05)
        check(f"{receiver} score-ranked union tie-breaking is determinate",
              float(row["union_ranked_best"]) == float(row["union_ranked_worst"]), True)
        check(f"{receiver} full-DIB confirmed at budget", int(row["dib_confirmed"]), exp_dib)
        check(f"{receiver} DIB queue minus shortest ranked prefix at equal yield",
              int(row["dib_queue_minus_ranked_depth"]), exp_gap)
        concentration.append(float(row["union_ranked_expected"]) / float(row["union_arbitrary_expected"]))
    check("score-ranked over arbitrary order, minimum", round(min(concentration), 1), 3.9, 0.05)
    check("score-ranked over arbitrary order, maximum", round(max(concentration), 1), 10.6, 0.05)

    comp = rows("results/union_ranked/ranked_prefix_composition.csv")
    shares = []
    for receiver in ("US", "UK", "YT"):
        pref = {r["stage"]: r for r in comp if r["receiver"] == receiver}
        shares.append(100 * float(pref["admitted by DIB"]["share_of_prefix"]))
        check(f"{receiver} ranked prefix: entries below theta", int(pref["below threshold"]["entries"]), 0)
        check(f"{receiver} ranked prefix: entries failing quorum", int(pref["fails quorum"]["entries"]), 0)
        check(f"{receiver} ranked prefix: single-reporter entries",
              int(pref["single-reporter (subset)"]["entries"]), 0)
    check("ranked prefix admitted by DIB, minimum (%)", round(min(shares), 1), 86.9, 0.05)
    check("ranked prefix admitted by DIB, maximum (%)", round(max(shares), 1), 90.7, 0.05)

    marg = {r["receiver"]: r for r in rows("results/union_ranked/ranked_marginal_return.csv")}
    for receiver, drop in (("US", 1.4), ("UK", 1.4), ("YT", 6.7)):
        check(f"{receiver} marginal drop past the DIB cut",
              round(float(marg[receiver]["marginal_drop_factor"]), 1), drop, 0.05)

    matched = rows("results/three_lab_matched/matched_ablation.csv")
    for receiver, expected_reduction, expected_n in (("US", 96.4, 36), ("UK", 94.4, 43), ("YT", 92.3, 107)):
        row = next(r for r in matched if r["receiver"] == receiver and r["stage"] == "DIB")
        check(f"{receiver} full-DIB candidates", int(row["candidates"]), expected_n)
        check(f"{receiver} reduction vs union (%)", round(100 * float(row["reduction"]), 1), expected_reduction, 0.05)


# --- RQ3: adversarial admission ------------------------------------------
def check_security() -> None:
    print("\nRQ3 adversarial admission")
    masq = rows("results/masquerade/service_masquerade.csv")
    worst_030 = max(float(r["score"]) for r in masq if r["malicious_fraction"] == "0.3" and r["class_eligible"] == "True")
    check("largest quorum-clearing score at f_s=0.30", round(worst_030, 3), 0.562, 0.0005)
    check("rejected at f_s=0.30", worst_030 < 0.65, True)
    staged_050 = [r for r in masq if r["malicious_fraction"] == "0.5" and r["accepted"] == "True"]
    check("stages at f_s=0.50 (outside the assumed region)", len(staged_050) > 0, True)

    quorum = [r for r in rows("results/quorum/site_quorum_sensitivity_rerun.csv") if r["site_count"] == "10"]
    check("quorums tested at N=10", sorted(int(r["quorum"]) for r in quorum), [1, 2, 3, 5])
    check("accepted facts identical across quorums at N=10", len({r["accepted_facts"] for r in quorum}), 1)
    check("accepted facts at N=10", int(quorum[0]["accepted_facts"]), 346)
    check("observable retention at N=10 (%)", float(quorum[0]["observable_retention_pct"]), 63.17, 0.005)

    drift = rows("results/drift/nonstationarity_time_to_admission_summary.csv")[0]
    check("drift cases admitted within horizon", int(drift["n_cases_admitted_within_horizon"]), 69)
    check("drift cases total", int(drift["n_cases_total"]), 162)
    check("median days to admission", float(drift["median_days_to_admission"]), 7.0)


# --- Management path -----------------------------------------------------
def check_scalability() -> None:
    print("\nManagement-path feasibility and reconciliation")
    single = {r["n_workers"]: r for r in rows("results/concurrency/throughput_v28_performance.csv")}
    check("single-node throughput at 100 writers", round(float(single["100"]["throughput_ops_per_sec_mean"]), 1), 317.5, 0.05)
    check("single-node p99 at 100 writers (ms)", round(1000 * float(single["100"]["p99_latency_s_mean"]), 1), 5895.5, 0.05)
    check("single-node p99 at 1 writer (ms)", round(1000 * float(single["1"]["p99_latency_s_mean"]), 1), 5.3, 0.05)
    check("no unexpected errors", all(int(r["unexpected_errors"]) == 0 for r in single.values()), True)

    sweep = {(int(r["n_sites"]), int(r["n_workers"])): r
             for r in rows("results/site_count/site_count_summary.csv")}
    check("one site container saturates (ops/s at 100 writers)",
          round(float(sweep[(1, 100)]["throughput_ops_per_sec"]), 1), 320.9, 0.05)
    check("one site container gains nothing from 50 to 100 writers",
          float(sweep[(1, 100)]["throughput_ops_per_sec"]) - float(sweep[(1, 50)]["throughput_ops_per_sec"]) < 5.0, True)
    speedups = [float(sweep[(n, w)]["speedup_vs_1_site"]) for n in (2, 5, 10) for w in (50, 100)]
    check("distribution speed-up at 50/100 writers, minimum", round(min(speedups), 2), 1.63, 0.005)
    check("distribution speed-up at 50/100 writers, maximum", round(max(speedups), 2), 1.75, 0.005)
    check("whole gain realized at two sites",
          float(sweep[(2, 100)]["throughput_ops_per_sec"]) >= float(sweep[(10, 100)]["throughput_ops_per_sec"]), True)
    check("ten sites are slower than one at a single writer (%)",
          round(100 * (1 - float(sweep[(10, 1)]["throughput_ops_per_sec"])
                       / float(sweep[(1, 1)]["throughput_ops_per_sec"])), 1), 20.6, 0.05)
    check("sweep unexpected errors", sum(int(r["unexpected_errors"]) for r in
          rows("results/site_count/site_count_summary.csv")), 6)

    inv = rows("results/concurrency/invariants_v28_correctness.csv")
    check("correctness trials", sum(int(r["trials"]) for r in inv), 1825)
    check("invariant violations", sum(int(r["violations"]) for r in inv), 0)

    dist = {r["n_workers"]: r for r in rows("results/distributed/throughput_distributed_5rep.csv")}
    check("distributed throughput at 100 writers", round(float(dist["100"]["throughput_ops_per_sec_mean"]), 1), 530.3, 0.05)
    check("distributed p99 at 100 writers (ms)", round(1000 * float(dist["100"]["p99_latency_s_mean"]), 1), 454.8, 0.05)

    fault = rows("results/fault_injection/results.csv")
    check("fault-injection trials", sum(int(r["trials"]) for r in fault), 40)
    check("all trials converge", all(r["trials"] == r["consistent_trials"] for r in fault), True)
    single_event = [r for r in fault if r["scenario"] != "dispute_and_restore"]
    mean_conv = sum(float(r["total_convergence_s_mean"]) * int(r["trials"]) for r in single_event) / 30
    check("single-event convergence (s)", round(mean_conv, 2), 0.48, 0.005)
    compound = next(r for r in fault if r["scenario"] == "dispute_and_restore")
    check("compound-outage convergence (s)", round(float(compound["total_convergence_s_mean"]), 2), 0.51, 0.005)
    trials = rows("results/fault_injection/trials.csv")
    check("fault-injection per-trial rows", len(trials), 40)
    restart = [float(r["health_check_after_restart_s"]) for r in trials]
    reconcile = [float(r["reconcile_call_s"]) for r in trials]
    check("process restart, mean over 40 trials (s)", round(sum(restart) / len(restart), 3), 0.416, 0.0005)
    check("reconcile call, mean over 40 trials (s)", round(sum(reconcile) / len(reconcile), 3), 0.071, 0.0005)
    check("reconcile call, maximum over 40 trials (s)", round(max(reconcile), 3), 0.105, 0.0005)


def check_claims_index() -> None:
    print("\nClaim index")
    claims = json.loads(text("claims.json"))
    check("paper version", claims["paper_version"], "v42.0")
    check("selected configuration is graph-free", "gamma: 0" in text(claims["selected_configuration"]), True)
    missing = [p for c in claims["claims"] for p in (x.strip() for x in c["result"].split(","))
               if not (ROOT / p).exists()]
    check("every claim resolves to a stored evidence file", missing, [])


def run_unit_tests() -> None:
    print("\nUnit suite")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "code/tests", "-q"],
        cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "code" / "src")},
        capture_output=True, text=True,
    )
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr[-200:]
    check("pytest exits cleanly", result.returncode, 0)
    print("  " + tail)


def check_new_lifecycle() -> None:
    print("\nRestoration-policy and suspension campaigns")
    result = json.loads(text("results/restore_ablation/results.json"))
    check("ablation source matches packaged service", result["service_sha256"],
          hashlib.sha256((ROOT / "code/src/dib/registry/distributed/service.py").read_bytes()).hexdigest())
    check("ablation cases identical to the historical run (31863043)",
          result["cases"] == json.loads(text("results/restore_ablation/historical_31863043/results.json"))["cases"], True)
    check("ablation script matches packaged generator", result["script_sha256"],
          hashlib.sha256((ROOT / "code/scripts/v36_restore_ablation.py").read_bytes()).hexdigest())
    check("distinct policy/scenario combinations", len({(c['policy'], c['veto_time'], c['disconnected']) for c in result['cases']}), 18)
    check("case count", len(result['cases']), 18)
    for policy, ace_count, veto_count in (("persistent_approval", 12, 6), ("review_reset", 0, 0), ("dib", 0, 6)):
        cases = [c for c in result['cases'] if c['policy'] == policy]
        check(f"{policy}: six sequences", len(cases), 6)
        check(f"{policy}: subject ACEs without new commit", sum(c['exports_without_fresh_commit'] for c in cases), ace_count)
        check(f"{policy}: vetoes preserved", sum(c['local_veto_preserved'] for c in cases), veto_count)
        for c in cases:
            final = next(t for t in c['trace'] if t['event'] == 'restored_and_reconciled')
            check(f"{policy}/{c['veto_time']}/{c['disconnected']}: export trace", sum(final['subject_aces']), c['exports_without_fresh_commit'])
            check(f"{policy}/{c['veto_time']}/{c['disconnected']}: control trace", all(t['control_aces'] == [1, 1, 1] for t in c['trace']), True)
    api = json.loads(text('results/lifecycle_v35/api_campaign.json'))
    for p in api['policies']:
        q = p['suspension_quorum']
        check(f'q={q}: first reporter', p['aces_after_one_reporter_per_site'], [0 if q == 1 else 100] * 10)
        check(f'q={q}: second reporter', p['aces_after_two_reporters_per_site'], [0] * 10)
        check(f'q={q}: local vetoes', p['local_vetoes_preserved'], 100)
        check(f'q={q}: duplicate votes', p['duplicate_reports_add_votes'], False)
        check(f'q={q}: fresh commits', p['restoration_requires_new_commits'], True)
        check(f'q={q}: old votes cleared', p['old_votes_cleared'], True)
    # historical single run (v43 import, service hash not recorded), kept under its new path; the
    # evaluated-service reruns are checked in check_sweep_flood_20261013 and below
    flood = json.loads(text('results/dispute_flood/historical_v43_import/dispute_flood_summary.json'))
    check('flood: authorizations suspended', flood['attacker']['site_records_suspended'], 1000)
    check('flood: withdrawal seconds', round(flood['attacker']['wall_s'], 1), 11.3)
    check('flood: recovery seconds', round(flood['recovery']['wall_s'], 1), 21.6)
    check('flood: recovery requests per fact', flood['recovery']['requests_per_fact'], 11)


# --- v42.0 additions: A1 resolved-peer counterfactual, Pareto frontier,
# and local veto across a process outage --------------------------------
def check_v42_additions() -> None:
    print("\nv42.0 additions")

    a1 = rows("results/a1_resolvable/a1_resolvable_counterfactual.csv")
    ip_literal = [r for r in a1 if r["peer_form"] == "ip_literal"]
    resolved = [r for r in a1 if r["peer_form"] == "resolved_fqdn"]
    check("A1 counterfactual: ip-literal cells", len(ip_literal), 150)
    check("A1 counterfactual: resolved-name cells", len(resolved), 150)
    check("A1 counterfactual: ip-literal admitted", sum(r["accepted"] == "True" for r in ip_literal), 0)
    check("A1 counterfactual: resolved-name admitted", sum(r["accepted"] == "True" for r in resolved), 21)
    first_admit = min(
        (r for r in resolved if r["accepted"] == "True"),
        key=lambda r: (int(r["k"]), int(r["spread_days"])),
    )
    check("A1 counterfactual: first admission k", int(first_admit["k"]), 7)
    check("A1 counterfactual: first admission spread_days", int(first_admit["spread_days"]), 120)
    check("A1 counterfactual: first admission score", round(float(first_admit["score"]), 3), 0.679)
    a1_manifest = json.loads(text("results/a1_resolvable/manifest.json"))
    check("A1 counterfactual: raw captured packets are IP-literal",
          a1_manifest["format_check"]["ip_literal_destinations"], 354)
    check("A1 counterfactual: total captured packets",
          a1_manifest["format_check"]["total_captured_packets"], 354)

    sweep = rows("results/pareto_frontier/sweep.csv")
    operating = {r["receiver"]: r for r in sweep if r["is_operating_point"] == "True"}
    check("Pareto frontier: sweep cells", len(sweep), 78)
    expected_operating = {
        "US": (36, 0.065, 0.116),
        "UK": (43, 0.064, 0.115),
        "YT": (107, 0.223, 0.247),
    }
    for receiver, (n, recall, f1) in expected_operating.items():
        r = operating[receiver]
        check(f"Pareto frontier {receiver}: operating-point queue size", int(r["queue_size"]), n)
        check(f"Pareto frontier {receiver}: operating-point recall", round(float(r["recall"]), 3), recall, 0.001)
        check(f"Pareto frontier {receiver}: operating-point F1", round(float(r["f1"]), 3), f1, 0.001)

    ov = json.loads(text("results/offline_veto/results.json"))
    check("offline veto: script matches packaged generator", ov["script_sha256"],
          hashlib.sha256((ROOT / "code/scripts/offline_veto_reconciliation.py").read_bytes()).hexdigest())
    check("offline veto: service matches packaged distributed service", ov["service_sha256"],
          hashlib.sha256((ROOT / "code/src/dib/registry/distributed/service.py").read_bytes()).hexdigest())
    # 30 trials since the promotion of 2026-10-13 (audit 129; the 10-trial run is historical_31863043/)
    check("offline veto: trial count", len(ov["trials"]), 30)
    check("offline veto: vetoes preserved", ov["summary"]["vetoes_preserved"], 30)
    check("offline veto: stale approvals cleared", ov["summary"]["stale_approvals_cleared"], 30)
    check("offline veto: unrelated facts preserved", ov["summary"]["unrelated_facts_preserved"], 30)
    check("offline veto: explicit recoveries passed", ov["summary"]["explicit_recoveries_passed"], 30)
    old = json.loads(text("results/offline_veto/historical_31863043/results.json"))
    check("offline veto: first 10 trials identical to the historical run", ov["trials"][:10] == old["trials"], True)
    for t in ov["trials"]:
        check(f"offline veto trial {t['trial']}: veto survives with local origin",
              t["after"]["veto"]["origin"], "local")
        check(f"offline veto trial {t['trial']}: stale Active returns to MonitorOnly",
              t["after"]["active"]["state"], "monitor-only")
        check(f"offline veto trial {t['trial']}: neither vetoed nor stale fact exports",
              t["exports_after_reconcile"]["veto"] == [0, 0, 0] and t["exports_after_reconcile"]["active"] == [0, 0, 0], True)
        check(f"offline veto trial {t['trial']}: unrelated fact exports everywhere",
              t["exports_after_reconcile"]["unrelated"], [1, 1, 1])
        check(f"offline veto trial {t['trial']}: repeated reconcile is a no-op",
              t["repeated_reconcile_noop"], True)
        check(f"offline veto trial {t['trial']}: stale replay ignored",
              t["stale_replay_ignored"], True)
        check(f"offline veto trial {t['trial']}: direct commit over veto blocked",
              t["direct_commit_over_veto_blocked"], True)


# --- 2026-10-13 reruns on the reference service (docs/audit/119-120) --------
# The packaged results/restore_ablation and results/offline_veto were produced by
# service.py 31863043 (commit 9413c20). Their provenance checks above are KEPT and
# still fail: they state a fact about that evidence. The reruns below are checked
# against the service in this tree; promoting them into results/ is a separate,
# user-approved step.
SUPERSEDED = {
    "ablation source matches packaged service": "experiments_tnsm/lifecycle_rerun_20261013_g3fix (audits 120, 126)",
    "offline veto: service matches packaged distributed service": "experiments_tnsm/lifecycle_rerun_20261013_g3fix (audits 120, 126)",
}


def check_lifecycle_rerun_superseded_3ffa57ee() -> None:
    """Audit 120 rerun, on service 3ffa57ee (before the audit-126 guard). Checked for internal
    consistency only: it is NOT claimed to match the service in this tree."""
    print("\nRerun on service 3ffa57ee (audit 120; superseded by audit 126, internal consistency only)")
    d = "experiments_tnsm/lifecycle_rerun_20261013"
    man = json.loads(text(f"{d}/manifest.json"))
    for name, run in man["runs"].items():
        check(f"3ffa57ee rerun: {name} result sha256 = manifest", hashlib.sha256(text(f"{d}/{name}.json").encode()).hexdigest(),
              run["result_sha256"])
        check(f"3ffa57ee rerun: {name} records service 3ffa57ee", json.loads(text(f"{d}/{name}.json"))["service_sha256"],
              "3ffa57ee549512e4d3341738c8ec052a86a3c11f4a05f37f82614868fc822af8")


def check_lifecycle_rerun_20261013() -> None:
    print("\nRerun on the service in this tree (audit 119-120, 126)")
    d = "experiments_tnsm/lifecycle_rerun_20261013_g3fix"
    service = hashlib.sha256((ROOT / "code/src/dib/registry/distributed/service.py").read_bytes()).hexdigest()
    man = json.loads(text(f"{d}/manifest.json"))
    abl = json.loads(text(f"{d}/restore_ablation.json"))
    ov = json.loads(text(f"{d}/offline_veto.json"))
    check("rerun: ablation service = this tree", abl["service_sha256"], service)
    check("rerun: offline veto service = this tree", ov["service_sha256"], service)
    check("rerun: module loaded by the uvicorn subprocesses = this tree", man["subprocess_module_sha256"], service)
    check("rerun: ablation generator = this tree", abl["script_sha256"],
          hashlib.sha256((ROOT / "code/scripts/v36_restore_ablation.py").read_bytes()).hexdigest())
    check("rerun: offline veto generator = this tree", ov["script_sha256"],
          hashlib.sha256((ROOT / "code/scripts/offline_veto_reconciliation.py").read_bytes()).hexdigest())
    for name, run in man["runs"].items():
        check(f"rerun: {name} result sha256 = manifest", hashlib.sha256(text(f"{d}/{name}.json").encode()).hexdigest(),
              run["result_sha256"])
        check(f"rerun: {name} exit code", run["returncode"], 0)
    check("rerun: ablation cases", len(abl["cases"]), 18)
    for policy, ace_count, veto_count in (("persistent_approval", 12, 6), ("review_reset", 0, 0), ("dib", 0, 6)):
        cases = [c for c in abl["cases"] if c["policy"] == policy]
        finals = [next(t for t in c["trace"] if t["event"] == "restored_and_reconciled") for c in cases]
        check(f"rerun {policy}: subject ACEs without fresh commit (trace)", sum(sum(f["subject_aces"]) for f in finals), ace_count)
        check(f"rerun {policy}: vetoes preserved", sum(c["local_veto_preserved"] for c in cases), veto_count)
        check(f"rerun {policy}: control fact exported at every step",
              all(t["control_aces"] == [1, 1, 1] for c in cases for t in c["trace"]), True)
    t = ov["trials"]
    check("rerun offline veto: trials", len(t), 30)
    check("rerun offline veto: veto local after restart", sum(x["after"]["veto"] == dict(state="revoked", origin="local", last_applied_seq=3) for x in t), 30)
    check("rerun offline veto: stale Active -> MonitorOnly", sum(x["after"]["active"]["state"] == "monitor-only" for x in t), 30)
    check("rerun offline veto: neither vetoed nor stale fact exports",
          sum(x["exports_after_reconcile"]["veto"] == [0, 0, 0] and x["exports_after_reconcile"]["active"] == [0, 0, 0] for x in t), 30)
    check("rerun offline veto: unrelated fact exports everywhere", sum(x["exports_after_reconcile"]["unrelated"] == [1, 1, 1] for x in t), 30)
    for key in ("repeated_reconcile_noop", "stale_replay_ignored", "direct_commit_over_veto_blocked", "explicit_recovery_passed"):
        check(f"rerun offline veto: {key}", sum(bool(x[key]) for x in t), 30)


def check_gateway_20261013() -> None:
    """Gateway withdrawal campaigns (audits 121-122) on service 3ffa57ee, before the audit-126 guard;
    the guard does not change any valid transition. Counts re-read from summary.json, provenance
    from each manifest (hash inside the 11 containers at start and end)."""
    print("\nGateway withdrawal t0-t3 (audits 121-122; service 3ffa57ee)")
    d = "experiments_tnsm/gateway_withdrawal_20261013"
    for run, n_std, n_veto in (("lan_mtls", 100, 10), ("wan_mtls", 50, 0), ("degraded_mtls", 50, 0)):
        man = json.loads(text(f"{d}/{run}/manifest.json"))
        check(f"gateway {run}: no fatal error", man.get("fatal"), None)
        check(f"gateway {run}: mTLS", man["mtls"], True)
        for when in ("cluster_start", "cluster_end"):
            check(f"gateway {run}: {when} service hash in all 11 containers",
                  sorted({c["/app/service.py"] for c in man["provenance"][when].values()}),
                  ["3ffa57ee549512e4d3341738c8ec052a86a3c11f4a05f37f82614868fc822af8"])
            check(f"gateway {run}: {when} container count", len(man["provenance"][when]), 11)
        summ = json.loads(text(f"{d}/analysis_{run.split('_')[0]}/summary.json"))
        for kind, n in (("std", n_std), ("veto", n_veto)):
            if not n:
                continue
            s = summ[f"{run.split('_')[0]}/{kind}"]
            c = s["checks"]
            check(f"gateway {run}/{kind}: episodes", s["episodes"], n)
            for key in ("export_after_t1_is_control_only", "subject_blocked_after_t2", "restore_alone_blocked",
                        "reenabled_after_commit", "ctl_ok_after_t2", "est_control_survived_episode"):
                check(f"gateway {run}/{kind}: {key} (of measured)", c[key], c["measured"])
            check(f"gateway {run}/{kind}: control failures outside reloads", c["ctl_failures_outside_reloads_total"], 0)
            if kind == "veto":
                for key in ("veto_kept_after_restore", "commit_over_veto_refused", "veto_export_without_subject"):
                    check(f"gateway {run}/veto: {key}", c[key], n)
            check(f"gateway {run}/{kind}: established subject connections cut", s["established_cut"]["cut"], 0)
    headline = {"lan": (0.024, 5.494, 0.382), "wan": (0.418, 5.875, 0.766), "degraded": (1.020, 6.504, 1.398)}
    for prof, (t1, t2, t3) in headline.items():
        m = json.loads(text(f"{d}/analysis_{prof}/summary.json"))[f"{prof}/std"]["metrics"]
        check(f"gateway {prof}: median t1 (s)", round(m["d_t1"]["median"], 3), t1, 0.0005)
        check(f"gateway {prof}: median t2 (s)", round(m["d_t2"]["median"], 3), t2, 0.0005)
        check(f"gateway {prof}: median t3 new connections (s)", round(m["d_t3"]["median"], 3), t3, 0.0005)


def check_sweep_flood_20261013() -> None:
    """Site sweep and dispute flood on the evaluated service (audits 123, 127)."""
    print("\nSite sweep and dispute flood (audits 123, 127; service in this tree)")
    service = hashlib.sha256((ROOT / "code/src/dib/registry/distributed/service.py").read_bytes()).hexdigest()
    d = "experiments_tnsm/site_sweep_20261013"
    for tr in ("http", "mtls"):
        man = json.loads(text(f"{d}/{tr}/manifest.json"))
        check(f"sweep {tr}: no fatal error", man.get("fatal"), None)
        check(f"sweep {tr}: cells", len(man["cells"]), 16)
        for when in ("containers", "containers_end"):
            check(f"sweep {tr}: {when} service hash", sorted({c["/app/service.py"] for n in man[when].values() for c in n.values()}), [service])
        summ = json.loads(text(f"{d}/analysis_{tr}/summary.json"))
        check(f"sweep {tr}: requests", sum(c["requests"] for c in summ["cells"]), 100000)
        check(f"sweep {tr}: unexpected errors", sum(c["error"] + c["timeout"] + c["transport_err"] for c in summ["cells"]), {"http": 2, "mtls": 0}[tr])
        check(f"sweep {tr}: every N>1 vs N=1 ratio CI above 1 at W=50,100", all(r["ci95_lo"] > 1 for r in summ["ratios"]), True)
    r = {(x["transport"], x["n_sites"], x["n_workers"]): x for x in json.loads(text(f"{d}/analysis_http/summary.json"))["ratios"]}
    check("sweep http: N=2 vs N=1 at W=100", round(r[("http", 2, 100)]["ratio_vs_n1"], 2), 1.92, 0.005)
    f = "experiments_tnsm/dispute_flood_20261013"
    man = json.loads(text(f"{f}/manifest.json"))
    check("flood: repetitions", len(man["reps"]), 5)
    check("flood: service in containers", sorted({h for r in man["reps"] for h in r["service_in_containers"]}), [service])
    check("flood: only HTTP 200 in access logs", sorted({c for r in man["reps"] for v in r["status_codes"].values() for c in v}), ["200"])
    for i in range(5):
        s = json.loads(text(f"{f}/rep{i}/dispute_flood_summary.json"))
        check(f"flood rep{i}: disputes applied", s["attacker"]["disputes_applied"], 100)
        check(f"flood rep{i}: exports withdrawn at all sites", s["blast_radius"]["exported_aces_per_site_after"], [0] * 10)
        check(f"flood rep{i}: exports recovered", s["blast_radius"]["exported_aces_per_site_after_recovery"], [100] * 10)
        check(f"flood rep{i}: recovery requests per fact", s["recovery"]["requests_per_fact"], 11.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-tests", action="store_true", help="also run the unit suite")
    args = parser.parse_args()

    check_claims_index()
    check_formal()
    check_utility()
    check_security()
    check_scalability()
    check_new_lifecycle()
    check_v42_additions()
    check_lifecycle_rerun_superseded_3ffa57ee()
    check_lifecycle_rerun_20261013()
    check_gateway_20261013()
    check_sweep_flood_20261013()
    if args.with_tests:
        run_unit_tests()

    print(f"\n{len(PASSED)} checks passed, {len(FAILED)} failed")
    for line in FAILED:
        print("  FAILED " + line)
        label = line.split(": got ", 1)[0]
        if label in SUPERSEDED:
            print(f"         (historical evidence, superseded by {SUPERSEDED[label]}; still counted as failed)")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
