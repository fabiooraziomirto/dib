"""Analysis of the gateway withdrawal campaigns (pre-registered in docs/audit/121).

Usage: python analyze.py RUN_DIR [RUN_DIR ...] --out OUT_DIR

Per episode (all times in seconds from t0s = send of POST /dispute, host CLOCK_MONOTONIC):
  d_t0     evidence shows 'disputed'         (receive time of the first poll showing it)
  d_t0r    POST /dispute response received
  d_t1     site-0 shows 'disputed'
  d_react  t1 -> export start (harness reaction: orchestration, not the system)
  d_export export request + file write
  d_cmd    reload command (docker exec kill + exec -d)
  d_flush  reload start -> chain without MUD accept rules
  d_apply  reload start -> chain equal to the exported policy (t2)
  d_t2     t0s -> t2
  d_t3     t0s -> start of the first failing NEW subject probe after which every
           subject probe up to window_end fails; res_t3 = gap to the last success
  t3e      first failure of the ESTABLISHED subject connection in [t0s, window_end]
           (censored at window_end if none)
  ctl_*    control flow tcp/9090: NEW-probe failures, outage per reload, failures
           outside the reload intervals [reload start, t2 + 0.6 s]
Quantiles: median and p95 with a distribution-free 95 % CI from binomial order
statistics; median also with a percentile bootstrap (10 000 resamples, seed 20261013).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
import statistics
from pathlib import Path

SLACK = 0.6  # probe timeout 0.5 s + 0.1 s


def load_lines(path: Path) -> list[dict]:
    if path.with_suffix(path.suffix + ".gz").exists():
        text = gzip.open(path.with_suffix(path.suffix + ".gz"), "rt").read()
    elif path.exists():
        text = path.read_text()
    else:
        return []
    out = []
    for line in text.splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def recv(obs):
    return None if not obs else obs[1]


def episode_metrics(ep: dict, probes: list[dict]) -> dict:
    m = {"episode": ep["episode"], "kind": ep["kind"], "profile": ep["profile"], "status": ep["status"],
         "reason": ep.get("reason")}
    if ep["status"] != "complete" and "t2_obs" not in ep:
        return m
    d = ep["dispute"]
    t0s = d["t0s"]
    m["dispute_http"] = d.get("status")
    m["dispute_error"] = d.get("error")
    m["d_t0r"] = d["t0r"] - t0s
    m["d_t0"] = recv(ep.get("t0_obs")) - t0s if ep.get("t0_obs") else None
    m["res_t0"] = (ep["t0_obs"][1] - ep["t0_obs"][0]) if ep.get("t0_obs") and ep["t0_obs"][0] else None
    t1 = recv(ep.get("t1_obs"))
    m["d_t1"] = t1 - t0s if t1 else None
    m["res_t1"] = (ep["t1_obs"][1] - ep["t1_obs"][0]) if ep.get("t1_obs") and ep["t1_obs"][0] else None
    m["t1_before_t0r"] = (ep["t1_obs"][0] or t0s) <= d["t0r"] if t1 else None
    if t1 and ep.get("export"):
        m["d_react"] = ep["export"][0] - t1
        m["d_export"] = ep["export"][1] - ep["export"][0]
        m["d_cmd"] = ep["reload"][1] - ep["reload"][0]
        m["export_ports"] = ep["export_ports"]
    rl_s = ep["reload"][0] if ep.get("reload") else None
    if ep.get("tf_obs") and rl_s:
        m["d_flush"] = ep["tf_obs"][1] - rl_s
    t2 = recv(ep.get("t2_obs"))
    if t2 is None:
        return m
    m["d_apply"] = t2 - rl_s
    m["d_t2"] = t2 - t0s
    m["res_t2"] = ep["t2_obs"][1] - ep["t2_obs"][0]
    wend = ep.get("window_end", t2)
    sub = [r for r in probes if r.get("k") == "new" and r.get("p") == 8080]
    ctl = [r for r in probes if r.get("k") == "new" and r.get("p") == 9090]
    # t3: first failure after which every subject probe up to the window end fails
    win = [r for r in sub if t0s <= r["s"] <= wend]
    t3, last_ok = None, None
    for r in win:
        if r["ok"]:
            t3, last_ok = None, r["s"]
        elif t3 is None:
            t3 = r["s"]
    m["d_t3"] = t3 - t0s if t3 is not None else None
    m["res_t3"] = (t3 - last_ok) if (t3 is not None and last_ok is not None) else None
    m["t3_before_t2"] = (t3 is not None and t3 <= t2)
    m["subject_blocked_after_t2"] = all(not r["ok"] for r in sub if t2 <= r["s"] <= wend) and any(t2 <= r["s"] <= wend for r in sub)
    m["subject_probes_after_t2"] = sum(1 for r in sub if t2 <= r["s"] <= wend)
    # established subject connection
    est = [r for r in probes if r.get("k") == "est" and r.get("p") == 8080]
    fails = [r for r in est if not r["ok"] and t0s <= r["s"] <= wend]
    m["t3e"] = fails[0]["s"] - t0s if fails else None
    m["t3e_censored_at"] = wend - t0s
    m["est_subject_survived_window"] = not fails and any(r["s"] >= wend - 0.2 for r in est)
    m["est_subject_survived_episode"] = all(r["ok"] for r in est) and bool(est)
    est_c = [r for r in probes if r.get("k") == "est" and r.get("p") == 9090]
    m["est_control_survived_episode"] = all(r["ok"] for r in est_c) and bool(est_c)
    # control: failures must lie inside reload intervals
    rec = ep.get("recovery", {})
    intervals = [(rl_s, t2 + SLACK)]
    if rec.get("restore_reload") and rec.get("restore_t2_obs"):
        intervals.append((rec["restore_reload"][0], rec["restore_t2_obs"][1] + SLACK))
    if rec.get("reload") and rec.get("t2_obs"):
        intervals.append((rec["reload"][0], rec["t2_obs"][1] + SLACK))
    cfail = [r for r in ctl if not r["ok"] and r["s"] >= t0s]
    m["ctl_failures"] = len(cfail)
    m["ctl_failures_outside_reloads"] = sum(1 for r in cfail if not any(a <= r["s"] <= b for a, b in intervals))
    dfail = [r for r in cfail if rl_s <= r["s"] <= t2 + SLACK]
    m["ctl_outage_dispute_reload"] = (dfail[-1]["e"] - dfail[0]["s"]) if dfail else 0.0
    m["ctl_ok_after_t2"] = all(r["ok"] for r in ctl if t2 + SLACK <= r["s"] <= wend) and any(t2 + SLACK <= r["s"] <= wend for r in ctl)
    # recovery
    if rec:
        sar = rec.get("subject_after_restore", {})
        m["restore_alone_blocked"] = (sar.get("probes", 0) > 0 and sar.get("ok", 1) == 0
                                      and 8080 not in rec.get("export_ports_after_restore", [8080]))
        m["reenabled"] = rec.get("reenabled_new_conn") is not None
        m["d_reenable"] = (rec["reenabled_new_conn"] - rec["t_commit"]) if rec.get("reenabled_new_conn") else None
        if ep["kind"] == "veto":
            m["veto_kept_after_restore"] = (rec.get("site0_state_after_restore") == "revoked"
                                            and rec.get("site0_origin_after_restore") == "local")
            m["commit_over_veto_refused"] = rec.get("commit_over_veto_status") == 409
            m["veto_export_without_subject"] = 8080 not in rec.get("export_ports_after_restore", [8080])
    return m


def order_ci(n: int, q: float, conf: float = 0.95):
    """Ranks (1-based) l, u with P(X_(l) <= x_q <= X_(u)) >= conf (binomial order statistics); None if n too small."""
    def cdf(k):
        return sum(math.comb(n, i) * q ** i * (1 - q) ** (n - i) for i in range(0, k + 1))
    best = None
    for l in range(1, n + 1):
        for u in range(l, n + 1):
            cov = cdf(u - 1) - cdf(l - 1)
            if cov >= conf and (best is None or u - l < best[1] - best[0]):
                best = (l, u)
                break
    return best


def quant(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f, c = math.floor(k), math.ceil(k)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def describe(xs: list[float]) -> dict:
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    if n == 0:
        return {"n": 0}
    out = {"n": n, "median": quant(xs, 0.5), "p95": quant(xs, 0.95), "min": xs[0], "max": xs[-1]}
    for q, name in ((0.5, "median"), (0.95, "p95")):
        ci = order_ci(n, q)
        out[f"{name}_ci95"] = [xs[ci[0] - 1], xs[ci[1] - 1]] if ci else None
    rng = random.Random(20261013)
    boots = sorted(statistics.median(rng.choices(xs, k=n)) for _ in range(10000))
    out["median_boot_ci95"] = [boots[249], boots[9749]]
    return out


METRICS = ["d_t0", "d_t0r", "d_t1", "d_react", "d_export", "d_cmd", "d_flush", "d_apply", "d_t2", "d_t3",
           "res_t0", "res_t1", "res_t2", "res_t3", "ctl_outage_dispute_reload", "d_reenable"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for run in a.runs:
        for ep_file in sorted(run.glob("ep*/episode.json")):
            ep = json.loads(ep_file.read_text())
            rows.append({"run": run.name, **episode_metrics(ep, load_lines(ep_file.parent / "probe.jsonl"))})
    keys = sorted({k for r in rows for k in r})
    with (a.out / "episodes.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    summary = {}
    for (profile, kind) in sorted({(r["profile"], r["kind"]) for r in rows}):
        grp = [r for r in rows if r["profile"] == profile and r["kind"] == kind]
        meas = [r for r in grp if r.get("d_t2") is not None]
        s = {"episodes": len(grp), "status": {st: sum(r["status"] == st for r in grp) for st in sorted({r["status"] for r in grp})},
             "reasons": sorted({r["reason"] for r in grp if r.get("reason")}),
             "dispute_non200": sum(1 for r in grp if r.get("dispute_http") not in (200, None) or r.get("dispute_error")),
             "metrics": {k: describe([r.get(k) for r in meas]) for k in METRICS}}
        b = lambda k: [r.get(k) for r in meas]
        s["checks"] = {
            "export_after_t1_is_control_only": sum(r.get("export_ports") == [9090] for r in meas),
            "subject_blocked_after_t2": sum(bool(x) for x in b("subject_blocked_after_t2")),
            "t1_before_t0r": sum(bool(x) for x in b("t1_before_t0r")),
            "t3_before_t2": sum(bool(x) for x in b("t3_before_t2")),
            "est_subject_survived_window": sum(bool(x) for x in b("est_subject_survived_window")),
            "est_subject_survived_episode": sum(bool(x) for x in b("est_subject_survived_episode")),
            "est_control_survived_episode": sum(bool(x) for x in b("est_control_survived_episode")),
            "ctl_failures_outside_reloads_total": sum(x or 0 for x in b("ctl_failures_outside_reloads")),
            "ctl_ok_after_t2": sum(bool(x) for x in b("ctl_ok_after_t2")),
            "restore_alone_blocked": sum(bool(x) for x in b("restore_alone_blocked")),
            "reenabled_after_commit": sum(bool(x) for x in b("reenabled")),
            "measured": len(meas),
        }
        if kind == "veto":
            for k in ("veto_kept_after_restore", "commit_over_veto_refused", "veto_export_without_subject"):
                s["checks"][k] = sum(bool(x) for x in b(k))
        t3e = [r for r in meas if r.get("t3e") is not None]
        s["established_cut"] = {"cut": len(t3e), "censored": len(meas) - len(t3e),
                                "window_s_min": min((r["t3e_censored_at"] for r in meas), default=None)}
        summary[f"{profile}/{kind}"] = s
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    lines = ["| Profile/kind | n meas. | t1 med [95% CI] | t2 med [CI] | t2 p95 [CI] | t3 med | apply med | ctl outage med |", "|---|---|---|---|---|---|---|---|"]
    fmt = lambda d, k="median": "-" if not d.get("n") else f"{d[k]:.3f}"
    ci = lambda d, k: "" if not d.get(f"{k}_ci95") else f" [{d[f'{k}_ci95'][0]:.3f}, {d[f'{k}_ci95'][1]:.3f}]"
    for key, s in summary.items():
        mm = s["metrics"]
        lines.append(f"| {key} | {s['checks']['measured']} | {fmt(mm['d_t1'])}{ci(mm['d_t1'], 'median')} | "
                     f"{fmt(mm['d_t2'])}{ci(mm['d_t2'], 'median')} | {fmt(mm['d_t2'], 'p95')}{ci(mm['d_t2'], 'p95')} | "
                     f"{fmt(mm['d_t3'])} | {fmt(mm['d_apply'])} | {fmt(mm['ctl_outage_dispute_reload'])} |")
    (a.out / "table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(json.dumps({k: {"status": v["status"], "checks": v["checks"], "established_cut": v["established_cut"]} for k, v in summary.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
