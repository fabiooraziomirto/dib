#!/usr/bin/env python3
"""Exploratory / sensitivity analyses on the B1 `degraded` block (docs/audit/35, section B: the definitions were committed (55b29a3) BEFORE this code or any
computation). None of this changes the registered verdicts of (a) and (c) (audit 34). Input: data already copied (no node access). Everything is
descriptive or a sensitivity, with no cause proposed. Usage: python3 analyze_exploratory_degraded.py [--out file]  (paths are fixed below).
Hypothesis/falsification: see test_exploratory_degraded.py (synthetic rows, one assertion per definition)."""
from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_b1 as ab  # noqa: E402
import analyze_c as ac  # noqa: E402
import blockdata  # noqa: E402

HERE = Path(__file__).resolve().parent
BLK = HERE / "block_degraded_lan_after_20261011"
SOURCES = [("lan (before)", HERE / "block_lan_before_20261011" / "lan_before", HERE / "block_lan_before_20261011" / "analysis_lan_before.md"),
           ("lan (after)", BLK / "lan_after", BLK / "analysis_lan_after.md"),
           ("wan (rilancio)", HERE / "wan_20261011" / "b1", HERE / "wan_20261011" / "analysis_wan.md"),
           ("degraded", BLK / "degraded", BLK / "analysis_degraded.md")]
B_ONLINE = {"D": 10.5, "C": 11.1}                                           # audit 14:94,204-207 (T = 5; C with mTLS)
REGISTERED_THRESHOLD_MS = {("C", 1): 12240.1, ("C", 10): 1267.4, ("D", 1): 8146.3, ("D", 10): 862.1}   # analysis_degraded.md:68-71
PREDICTED_MS = {("C", 1): 12000.0, ("C", 10): 1200.0, ("D", 1): 8000.0, ("D", 10): 800.0}
BASE_MARGIN_S = 0.25                                                        # B3: "above the base plane" = value > base + 0.25 s
RETRIES, ATTEMPT_S = 3, 1.0                                                 # service.py:120-121


def valid(rows):
    return [r for r in rows if not r.get("excluded") and "dispute_rtt_s" in r]


def pending_set(r):
    acks = {int(i) for i, t in (r.get("plog_ack_ts") or {}).items() if t is not None}
    left = {int(i) for i, n in (r.get("pending_left") or {}).items() if n}
    return acks | left


def quant(v, qs=(0.25, 0.5, 0.75, 0.95)):
    v = sorted(v)
    out = []
    for p in qs:
        k = (len(v) - 1) * p
        f = int(k)
        c = min(f + 1, len(v) - 1)
        out.append(v[f] + (v[c] - v[f]) * (k - f))
    return out


def qline(v):
    if not v:
        return "n=0"
    q = quant(v)
    return f"n={len(v)} min {min(v):.3f} p25 {q[0]:.3f} med {q[1]:.3f} p75 {q[2]:.3f} p95 {q[3]:.3f} max {max(v):.3f}"


def hist(v, width):
    c = Counter(math.floor(x / width + 1e-9) for x in v)
    return {round(k * width, 3): c[k] for k in sorted(c)}


# B1 ---------------------------------------------------------------------------------------------------------------------------------------------
def c_sensitivity_d(x, n, x_c, n_c, extra_n):
    ci_c = ac.clopper_pearson(x_c, n_c)
    base = None
    out = []
    for label, xx, nn in (("S0", x, n), ("S_a", x, n + extra_n), ("S_b", x + extra_n, n + extra_n)):
        ci = ac.clopper_pearson(xx, nn)
        cl = ac.classify(ci, ac.INTERVALS["D"])
        base = cl if base is None else base
        out.append({"label": label, "x": xx, "n": nn, "share": xx / nn, "ci": ci, "class": cl, "changed": cl != base,
                    "second": ac.second_clause(ci, ci_c, xx / nn, x_c / n_c)})
    return out


# B2 ---------------------------------------------------------------------------------------------------------------------------------------------
def last_site_all(rows):
    values, unmeasurable, undrained = [], 0, 0
    for r in valid(rows):
        pend = pending_set(r)
        ts, bad = [], None
        for i in range(10):
            ack = (r.get("plog_ack_ts") or {}).get(str(i))
            if i in pend:
                if ack is None:
                    bad = "undrained"
                    break
                ts.append(ack - r["t0"])
            else:
                ap = (r.get("plog_apply_ts") or {}).get(str(i))
                if ap is None:
                    bad = "unmeasurable"
                    break
                ts.append(ap - r["t0"])
        if bad == "undrained":
            undrained += 1
        elif bad == "unmeasurable":
            unmeasurable += 1
        else:
            values.append(max(ts))
    return {"values": values, "unmeasurable": unmeasurable, "undrained": undrained}


# B3 ---------------------------------------------------------------------------------------------------------------------------------------------
def gaps_f1(rows):
    by_pos = [[] for _ in range(10)]
    used = viol = withp = 0
    for r in valid(rows):
        if pending_set(r):
            withp += 1
            continue
        ap = [(r.get("plog_apply_ts") or {}).get(str(i)) for i in range(10)]
        if any(a is None for a in ap):
            continue
        if any(ap[k] < ap[k - 1] for k in range(1, 10)):
            viol += 1
            continue
        used += 1
        by_pos[0].append(ap[0] - r["t0"])
        for k in range(1, 10):
            by_pos[k].append(ap[k] - ap[k - 1])
    allg = [g for k in range(1, 10) for g in by_pos[k]]
    return {"n_used": used, "order_violations": viol, "with_pending": withp, "by_pos": by_pos, "hist": hist(allg, 0.25)}


def f10_stats(rows):
    allv = [v for r in rows if not r.get("excluded") for v in (r.get("withdrawn_plog_s") or {}).values() if v is not None]
    base = statistics.median(allv)
    max_values = []
    for r in valid(rows):
        if pending_set(r):
            continue
        w = [v for v in (r.get("withdrawn_plog_s") or {}).values()]
        if len(w) == 10 and all(v is not None for v in w):
            max_values.append(max(w))
    per_ep, above, total = Counter(), 0, 0
    over = []
    for r in valid(rows):
        w = [v for v in (r.get("withdrawn_plog_s") or {}).values() if v is not None]
        k = sum(1 for v in w if v > base + BASE_MARGIN_S)
        per_ep[k] += 1
        above += k
        total += len(w)
        over += [v - base for v in w]
    return {"base": base, "max_values": max_values, "sites_total": total, "sites_above": above, "per_episode_above": dict(sorted(per_ep.items())),
            "hist_over": hist(over, 0.5)}


# B4 ---------------------------------------------------------------------------------------------------------------------------------------------
def pending_sites(rows, fanout, b_online):
    sites = []
    left_no_ack = 0
    for r in valid(rows):
        for i in sorted(pending_set(r)):
            ack = (r.get("plog_ack_ts") or {}).get(str(i))
            if ack is None:
                left_no_ack += 1
                continue
            e = None
            if fanout == 1:
                if i == 0:
                    e = ack - r["t0"]
                else:
                    prev = (r.get("plog_apply_ts") or {}).get(str(i - 1))
                    e = None if prev is None else ack - prev
            sites.append({"site": i, "u": ack - r["t0"], "e": e})
    est = [s for s in sites if s["e"] is not None]
    return {"sites": sites, "left_no_ack": left_no_ack, "n_estimable": len(est), "n_exceed_u": sum(1 for s in sites if s["u"] > b_online),
            "n_exceed_e": sum(1 for s in est if s["e"] > b_online)}


# B5 ---------------------------------------------------------------------------------------------------------------------------------------------
def _pmf(p):
    return [1 - p, p * (1 - p), p ** 2 * (1 - p), p ** 3]


def retry_arith(q):
    p = q ** (1 / RETRIES)
    ef = p + p ** 2 + p ** 3
    pmf = _pmf(p)
    cdf = [sum(pmf[:k + 1]) for k in range(4)]
    em = sum(k * (cdf[k] ** 10 - (cdf[k - 1] ** 10 if k else 0.0)) for k in range(4))
    return {"q": q, "p": p, "ef": ef, "e_failed_f1": 10 * ef, "e_max_f10": em}


def monte_carlo(p, n, seed):
    rng = random.Random(seed)
    tot, mx = 0, 0
    for _ in range(n):
        fs = []
        for _s in range(10):
            f = 0
            while f < RETRIES and rng.random() < p:
                f += 1
            fs.append(f)
        tot += sum(fs)
        mx += max(fs)
    return {"e_failed_f1": tot / n, "e_max_f10": mx / n}


# B6 ---------------------------------------------------------------------------------------------------------------------------------------------
def summary_rows(cells):
    """B6 rows. The CIs are those of analyze_b1.py: ONE random.Random(SEED) shared by the cells taken in (arm, fanout) order, and per cell first
    med_ci(dispute-rtt) then med_ci(last-site), exactly the call order of the per-cell table of analyze_b1.main (audit 35, 2026-10-11 decision)."""
    rng = random.Random(ab.SEED)
    out = []
    for c in sorted(cells, key=lambda c: (c["cell_spec"]["arm"], c["cell_spec"]["fanout"])):
        rows = c["rows"]
        v = valid(rows)
        ab.med_ci([1000 * r["dispute_rtt_s"] for r in v], rng)                 # consumed first, as in analyze_b1.main (not reported here)
        last = ab.last_site(rows)
        out.append({"arm": c["cell_spec"]["arm"], "fanout": c["cell_spec"]["fanout"], "median": ab.med_ci(last, rng), "n_last": len(last),
                    "x": sum(len(pending_set(r)) for r in v), "n": 10 * len(v), "excluded": sum(1 for r in rows if r.get("excluded"))})
    return out


def registered_last_site_cell(analysis_md: Path, arm: str, fanout: int):
    """The `last-site P-log ms` column text of the per-cell table of an analyze_b1 report (None if absent)."""
    for line in Path(analysis_md).read_text().splitlines():
        parts = [x.strip() for x in line.split("|")]
        if len(parts) > 7 and parts[1] == arm and parts[2] == str(fanout) and parts[3].isdigit():
            return parts[6]
    return None


# report -----------------------------------------------------------------------------------------------------------------------------------------
def fmt_ci(t):
    return "—" if t is None else f"{t[0]:.2f} [{t[1]:.2f}; {t[2]:.2f}]"


def report():
    L = ["# Exploratory / sensitivity analyses, B1 `degraded` (definitions: docs/audit/35 section B, committed 55b29a3 before any computation)", ""]
    cells, man = blockdata.load_block(BLK / "degraded")
    full = [c for c in cells if "rows" in c and "aborted" not in c]
    cell = {(c["cell_spec"]["arm"], c["cell_spec"]["fanout"]): c for c in full}
    cnt = ac.counts_from_cells(full)
    # B1
    extra = sum(10 for c in full if c["cell_spec"]["arm"] == "D" for r in c["rows"] if r.get("excluded") and r.get("client_timeout"))
    L += ["## B1. Sensitivity of (c) to the `client_timeout` episode of D/1 (registered D = %d/%d, C = %d/%d)" % (cnt["D"]["x"], cnt["D"]["n"], cnt["C"]["x"], cnt["C"]["n"]),
          f"Episodes excluded for `client_timeout` in D cells: {extra // 10} (counted as {extra} deliveries in n in the worst cases).", "",
          "| scenario | x/n | share | CP 95% CI | classification vs D [0.004, 0.015] | changed vs S0 | second clause |", "|---|---|---|---|---|---|---|"]
    for s in c_sensitivity_d(cnt["D"]["x"], cnt["D"]["n"], cnt["C"]["x"], cnt["C"]["n"], extra):
        L.append(f"| {s['label']} | {s['x']}/{s['n']} | {s['share']:.5f} | [{s['ci'][0]:.5f}; {s['ci'][1]:.5f}] | {s['class']} | {s['changed']} | {s['second']} |")
    # B2
    L += ["", "## B2. Sensitivity of (a) to the selection: last site over ALL valid episodes (pending sites by their ack time)",
          "No verdict: the registered one is in analysis_degraded.md:68-71. 'registered' = episodes without pending (analyze_b1.last_site).", "",
          "| cell | all valid, median ms [CI] (n) | unmeasurable / undrained | registered, median ms [CI] (n) | registered threshold ms | all-valid median − threshold ms (information) | all-valid median − registered median ms |", "|---|---|---|---|---|---|---|"]
    rng = random.Random(ab.SEED)
    for k in sorted(cell):
        rows = cell[k]["rows"]
        a = last_site_all(rows)
        ma = ab.med_ci([1000 * x for x in a["values"]], rng)
        mr = ab.med_ci(ab.last_site(rows), rng)
        L.append(f"| {k[0]}/{k[1]} | {ma[0]:.2f} [{ma[1]:.2f}; {ma[2]:.2f}] ({ma[3]}) | {a['unmeasurable']} / {a['undrained']} | {mr[0]:.2f} [{mr[1]:.2f}; {mr[2]:.2f}] ({mr[3]}) | "
                 f"{REGISTERED_THRESHOLD_MS[k]} | {ma[0] - REGISTERED_THRESHOLD_MS[k]:.1f} | {ma[0] - mr[0]:.1f} |")
    # B3
    L += ["", "## B3. Per-site times (descriptive)", "", "### FANOUT 1: delivery cost = gap between consecutive `plog_apply_ts` in id order (position 0: apply[0] − t0), seconds; episodes without pending, id order monotone"]
    for arm in ("D", "C"):
        g = gaps_f1(cell[(arm, 1)]["rows"])
        L += ["", f"**{arm}/1**: episodes used {g['n_used']}, with pending (left out) {g['with_pending']}, order violations {g['order_violations']}", "", "| position | stats (s) |", "|---|---|"]
        for k in range(10):
            L.append(f"| {k} | {qline(g['by_pos'][k])} |")
        L += ["", f"histogram of gaps at positions 1-9 (class width 0.25 s, left edge: count): {g['hist']}"]
    L += ["", "### FANOUT 10: maximum per episode (episodes without pending), base plane and sites above it (base + 0.25 s)"]
    for arm in ("D", "C"):
        m = f10_stats(cell[(arm, 10)]["rows"])
        L += ["", f"**{arm}/10**: max per episode {qline(m['max_values'])}; histogram (0.5 s): {hist(m['max_values'], 0.5)}",
              f"base plane (median of withdrawn_plog_s, all non-excluded sites with a value) {m['base']:.3f} s; sites total {m['sites_total']}, above the base {m['sites_above']}; "
              f"number of sites above per valid episode {{k: episodes}} {m['per_episode_above']}; histogram of (value − base) in 0.5 s classes {m['hist_over']}"]
    # B4
    L += ["", "## B4. Pending path against B_online (D 10.5 s, C 11.1 s): u = ack − t0 (upper bound); e = ack − apply of the previous site (FANOUT 1 only)", "",
          "| cell | pending sites (with ack) | in pending_left without ack | n_pending_undrained / unmeasured (cell summary) | exceed B_online with u | estimable e | exceed with e | max u | median u | max e | median e |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in sorted(cell):
        p = pending_sites(cell[k]["rows"], k[1], B_ONLINE[k[0]])
        s = cell[k]["summary"]
        us = [x["u"] for x in p["sites"]]
        es = [x["e"] for x in p["sites"] if x["e"] is not None]
        L.append(f"| {k[0]}/{k[1]} | {len(us)} | {p['left_no_ack']} | {s['n_pending_undrained_episodes']} / {s['n_pending_unmeasured_episodes']} | {p['n_exceed_u']} | {p['n_estimable']} | "
                 f"{p['n_exceed_e'] if k[1] == 1 else 'n/a'} | {max(us):.2f} | {statistics.median(us):.2f} | {('%.2f' % max(es)) if es else 'n/a'} | {('%.2f' % statistics.median(es)) if es else 'n/a'} |")
    L += ["", "Per-site list (cell, episode order not kept: site id, u s, e s):"]
    for k in sorted(cell):
        p = pending_sites(cell[k]["rows"], k[1], B_ONLINE[k[0]])
        L.append(f"- {k[0]}/{k[1]}: " + "; ".join(f"s{x['site']} u={x['u']:.2f}" + (f" e={x['e']:.2f}" if x["e"] is not None else "") for x in p["sites"]))
    # B5
    L += ["", "## B5. POST-HOC arithmetic (computed on the same data that falsified (a); independence of attempts assumed; 3 attempts of 1 s, service.py:120-121)", ""]
    L += ["| arm | pending share q (x/n) | p = q^(1/3) | E[failed attempts] per delivery | expected failed attempts per episode FANOUT 1 (10 deliveries) | E[max over 10 sites] failed attempts FANOUT 10 | MC check (seed 20261011, 200000) F1 / F10 |", "|---|---|---|---|---|---|---|"]
    qs = {}
    for arm in ("D", "C"):
        x, n = cnt[arm]["x"], cnt[arm]["n"]
        lo, hi = ac.clopper_pearson(x, n)
        for lab, q in (("point", x / n), ("CI low", lo), ("CI high", hi)):
            a = retry_arith(q)
            mc = monte_carlo(a["p"], 200000, ab.SEED)
            qs[(arm, lab)] = a
            L.append(f"| {arm} ({lab}) | {q:.5f} | {a['p']:.4f} | {a['ef']:.4f} | {a['e_failed_f1']:.3f} | {a['e_max_f10']:.3f} | {mc['e_failed_f1']:.3f} / {mc['e_max_f10']:.3f} |")
        for fo, (xx, nn) in sorted(cnt[arm]["cells"].items()):
            a = retry_arith(xx / nn)
            L.append(f"| {arm} FANOUT {fo} only | {xx}/{nn} = {xx / nn:.5f} | {a['p']:.4f} | {a['ef']:.4f} | {a['e_failed_f1']:.3f} | {a['e_max_f10']:.3f} | — |")
    L += ["", "Comparison with the observed excess (a), seconds; expected extra time = 1 s × expected failed attempts (point estimate of the pooled q):", "",
          "| cell | observed median − predicted (s) | registered excess over threshold (s) | expected extra time from the arithmetic (s) |", "|---|---|---|---|"]
    for k in sorted(cell):
        med = statistics.median(ab.last_site(cell[k]["rows"])) / 1000
        a = qs[(k[0], "point")]
        exp = a["e_failed_f1"] if k[1] == 1 else a["e_max_f10"]
        L.append(f"| {k[0]}/{k[1]} | {med - PREDICTED_MS[k] / 1000:.2f} | {(med * 1000 - REGISTERED_THRESHOLD_MS[k]) / 1000:.2f} | {exp * ATTEMPT_S:.2f} |")
    L += ["", "Limits: the observed medians are over episodes WITHOUT pending, the arithmetic is not; the cost of a failed attempt is assumed 1 s; no statement that the arithmetic explains or confirms the excess."]
    # B6
    L += ["", "## B6. Summary table (last-site P-log-apply, ONLY episodes without pending; pending share over all valid episodes; excluded per cell)", "",
          "| profile | arm | FANOUT | median last site ms [95% CI] | n (episodes without pending) | P-log accepted | pending x/n | excluded |", "|---|---|---|---|---|---|---|---|"]
    checks = []
    for name, d, md in SOURCES:
        cs, _m = blockdata.load_block(d)
        fl = [c for c in cs if "rows" in c and "aborted" not in c]
        accepted = {(c["cell_spec"]["arm"], c["cell_spec"]["fanout"]): c["summary"]["plog_acceptable_rule_10pct"] for c in fl}
        for t in summary_rows(fl):
            acc = accepted[(t["arm"], t["fanout"])]
            reg = registered_last_site_cell(md, t["arm"], t["fanout"])
            mine = ab.fmt(t["median"])
            checks.append((name, t["arm"], t["fanout"], mine == reg, mine, reg))
            L.append(f"| {name} | {t['arm']} | {t['fanout']} | {fmt_ci(t['median'])} | {t['n_last']} | {'yes' if acc else 'NO (not accepted)'} | {t['x']}/{t['n']} | {t['excluded']} |")
    L += ["", "Check against the registered analyses (the per-cell `last-site P-log ms` column of the analyze_b1 report of each source): "
          f"{sum(1 for c in checks if c[3])}/{len(checks)} cells identical (text `median [lo; hi] (n)`)."]
    L += [f"- DIFFERENT {c[0]} {c[1]}/{c[2]}: here `{c[4]}` registered `{c[5]}`" for c in checks if not c[3]]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    text = report()
    if a.out:
        Path(a.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
