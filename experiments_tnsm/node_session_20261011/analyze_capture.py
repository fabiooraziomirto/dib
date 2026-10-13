#!/usr/bin/env python3
"""Analysis of the in-container header captures (audit 116). Pure Python. Decision rules are those of docs/audit/116_prereg_cattura_container_mtls.md; nothing is tuned here.
Input: a directory with gen<N>/<container>.jsonl, one per sniffed container and cluster generation (sniff_in_container.py). Connections are those STARTED by the evidence service (SYN from the evidence ip to port 8000
of a site); per direction the data segments are counted from the SENDER's own outgoing tap (evidence tap for E->S, site tap for S->E).
Usage: python3 analyze_capture.py <capture dir> [--out file.md]"""
from __future__ import annotations

import collections
import json
import statistics
import sys
from pathlib import Path

PORT = 8000
SYN, ACK = 2, 16
MSS_EXPECTED = 1460
MSS_EFFECTIVE = 1448          # with TCP timestamps
THRESHOLD = 0.95
MIN_VALID = 90
EXPECTED_ES = {"D": 2, "C": 4}


def load(d: Path) -> dict:
    """{name: {"ip": ip, "rows": [packet rows]}} for every *.jsonl in the directory."""
    caps = {}
    for p in sorted(Path(d).glob("*.jsonl")):
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        if not rows or "hdr" not in rows[0]:
            continue
        h = rows[0]["hdr"]
        caps[h["name"]] = {"ip": h["ip"], "rows": rows[1:]}
    return caps


def load_all(root: Path) -> list[dict]:
    """Connections of every cluster generation: <root>/gen<N>/<container>.jsonl (the capture helper starts a new generation when the compose project is recreated); a root with
    *.jsonl directly is one generation."""
    root = Path(root)
    gens = sorted(p for p in root.glob("gen*") if p.is_dir()) or [root]
    out = []
    for g in gens:
        for c in connections(load(g)):
            out.append({**c, "gen": g.name})
    return out


def connections(caps: dict) -> list[dict]:
    ev = next((c for n, c in caps.items() if n.startswith("dibtnsm-evidence")), None)
    if ev is None:
        return []
    sites = {c["ip"]: c for n, c in caps.items() if not n.startswith("dibtnsm-evidence")}
    ev_ip = ev["ip"]
    out = []
    for r in ev["rows"]:
        if r["dir"] == "out" and r["src"] == ev_ip and r["dport"] == PORT and r["flags"] & SYN and not r["flags"] & ACK:
            sport, site_ip = r["sport"], r["dst"]
            es = sorted((x for x in ev["rows"] if x["dir"] == "out" and x["src"] == ev_ip and x["sport"] == sport and x["dst"] == site_ip and x["dport"] == PORT and x["len"] > 0
                         and x["t"] >= r["t"]), key=lambda x: x["t"])
            site = sites.get(site_ip)
            srows = [] if site is None else [x for x in site["rows"] if x["dir"] == "out" and x["src"] == site_ip and x["sport"] == PORT and x["dst"] == ev_ip and x["dport"] == sport
                                             and x["t"] >= r["t"]]
            rin = [] if site is None else sorted((x for x in site["rows"] if x["dir"] == "in" and x["src"] == ev_ip and x["sport"] == sport and x["dst"] == site_ip and x["dport"] == PORT
                                                  and x["len"] > 0 and x["t"] >= r["t"]), key=lambda x: x["t"])
            ev_synack = next((x for x in sorted(ev["rows"], key=lambda x: x["t"]) if x["dir"] == "in" and x["src"] == site_ip and x["dport"] == sport and x["sport"] == PORT
                              and x["flags"] & SYN and x["flags"] & ACK and x["t"] >= r["t"]), None)
            synack = next((x for x in sorted(srows, key=lambda x: x["t"]) if x["flags"] & SYN and x["flags"] & ACK), None)
            se = sorted((x for x in srows if x["len"] > 0), key=lambda x: x["t"])
            tls = bool(es) and es[0]["p0"].startswith("1603")
            t_cf = es[1]["t"] if tls and len(es) > 1 else None
            n_sf = sum(1 for x in se if t_cf is not None and x["t"] < t_cf)
            out.append({"sport": sport, "site_ip": site_ip, "tls": tls, "es_data": [(x["t"], x["len"]) for x in es], "se_data": [(x["t"], x["len"]) for x in se], "n_sf": n_sf,
                        "synack_in_t": None if ev_synack is None else ev_synack["t"], "es_in_lens": [x["len"] for x in rin], "syn_mss": r["mss"], "synack_mss": None if synack is None else synack["mss"], "valid": synack is not None and bool(es) and bool(se)})
    return out


def _mode(xs):
    return collections.Counter(xs).most_common(1)[0][0] if xs else None


def verdict(conns: list[dict]) -> dict:
    res: dict = {}
    for arm in ("D", "C"):
        cs = [c for c in conns if c["tls"] == (arm == "C")]
        valid = [c for c in cs if c["valid"]]
        res[arm] = {"connessioni": len(cs), "valide": len(valid), "non_valide": len(cs) - len(valid)}
        enough = len(valid) >= MIN_VALID
        if arm == "D":
            ok = [c for c in valid if len(c["es_data"]) == EXPECTED_ES["D"]]
            hyp = "H-P1b"
        else:
            ok = [c for c in valid if len(c["es_data"]) == EXPECTED_ES["C"] and c["n_sf"] == 1 and c["se_data"][0][1] < MSS_EFFECTIVE
                  and c["es_data"][0][1] < MSS_EFFECTIVE and c["es_data"][1][1] < MSS_EFFECTIVE]
            hyp = "H-P1c"
        quota = len(ok) / len(valid) if valid else 0.0
        v = "non valutabile" if not enough else ("confermata" if quota >= THRESHOLD else "falsificata")
        res[arm][hyp] = {"verdetto": v, "quota": quota, "attesi": len(ok), "valide": len(valid)}
        sig = collections.Counter((len(c["es_data"]), len(c["se_data"]), c["n_sf"]) for c in valid)
        res[arm]["firme (n E->S, n S->E, n volo server)"] = [[list(k), n] for k, n in sig.most_common()]
        mss = [m for c in valid for m in (c["syn_mss"], c["synack_mss"]) if m is not None]
        moda = _mode(mss)
        res[arm]["H-P1a"] = {"verdetto": "non valutabile" if not enough else ("confermata" if moda == MSS_EXPECTED else "falsificata"), "moda": moda,
                             "valori": dict(collections.Counter(mss))}
        for name, getter in (("lunghezze E->S (mediana per posizione)", lambda c: [x[1] for x in c["es_data"]]), ("lunghezze S->E (mediana per posizione)", lambda c: [x[1] for x in c["se_data"]])):
            pos = collections.defaultdict(list)
            for c in valid:
                for i, ln in enumerate(getter(c)):
                    pos[i].append(ln)
            res[arm][name] = [statistics.median(pos[i]) for i in sorted(pos)]
    return res


def units(conns: list[dict]) -> dict:
    """Addendum of audit 116 (post-hoc observation, not a pre-registered hypothesis of the first run): per arm, share of valid connections whose E->S data segments arrive at the SITE's ingress tap
    with the same lengths as they left the evidence tap (the segment is a single unit end to end), and the share whose first E->S data segment is larger than the MSS 1448 at the sender."""
    out = {}
    for arm in ("D", "C"):
        valid = [c for c in conns if c["tls"] == (arm == "C") and c["valid"]]
        intact = [c for c in valid if [x[1] for x in c["es_data"]] == c["es_in_lens"]]
        big = [c for c in valid if c["es_data"] and c["es_data"][0][1] > MSS_EFFECTIVE]
        split = [c for c in big if len(c["es_in_lens"]) > len(c["es_data"])]
        out[arm] = {"valide": len(valid), "ingresso_uguale_all_uscita": len(intact), "primo_segmento_E_S_oltre_MSS": len(big), "di_cui_arrivati_spezzati": len(split)}
    return out


BURST_S = 0.003
WIN = (0.03, 0.12)
MIN_BURSTS = 80


def clienthello_bursts(conns: list[dict]) -> dict:
    """Addendum 1 of audit 116 (H-P2a): first copy of the ClientHello of each C connection, seen in the sender tap between 0.03 s and 0.12 s after the SYN-ACK arrived at the evidence;
    its burst (rows within 3 ms) is a unit (one row longer than 1448) or split (two or more rows summing above 1448). Rows with data more than 0.3 s after the burst are listed by length."""
    cs = [c for c in conns if c["tls"] and c["es_data"] and c["synack_in_t"] is not None]
    unit = split = out = 0
    late: collections.Counter = collections.Counter()
    for c in cs:
        first_t = c["es_data"][0][0]
        if not WIN[0] <= first_t - c["synack_in_t"] <= WIN[1]:
            out += 1
            continue
        burst = [x for x in c["es_data"] if x[0] - first_t <= BURST_S]
        if len(burst) == 1 and burst[0][1] > MSS_EFFECTIVE:
            unit += 1
        elif len(burst) >= 2 and sum(x[1] for x in burst) > MSS_EFFECTIVE:
            split += 1
        for x in c["es_data"]:
            if x[0] - first_t > 0.3:
                late[str(x[1])] += 1
    n = unit + split
    quota = unit / n if n else 0.0
    verdetto = "non valutabile" if n < MIN_BURSTS else ("confermata" if quota >= THRESHOLD else "falsificata")
    return {"connessioni_C": len(cs), "valutabili": n, "unita": unit, "spezzate": split, "escluse_prima_copia_fuori_finestra": out, "quota_unita": quota, "H-P2a": verdetto,
            "lunghezze_righe_oltre_0.3s": dict(late)}


def to_md(res: dict) -> str:
    lines = ["| arm | connessioni | valide | ipotesi | verdetto | quota con la struttura attesa |", "|---|---|---|---|---|---|"]
    for arm in ("D", "C"):
        r = res[arm]
        for hyp in ("H-P1a", "H-P1b" if arm == "D" else "H-P1c"):
            h = r[hyp]
            q = f"{h['quota']:.3f} ({h['attesi']}/{h['valide']})" if "quota" in h else f"moda {h['moda']}, valori {h['valori']}"
            lines.append(f"| {arm} | {r['connessioni']} | {r['valide']} | {hyp} | **{h['verdetto']}** | {q} |")
    for arm in ("D", "C"):
        r = res[arm]
        lines += ["", f"### Arm {arm}: firme osservate (n segmenti E→S, n segmenti S→E, n segmenti del volo del server)", ""]
        lines += [f"- {k}: {n} connessioni" for k, n in r["firme (n E->S, n S->E, n volo server)"]]
        lines += [f"- lunghezze E→S (mediana per posizione): {r['lunghezze E->S (mediana per posizione)']}", f"- lunghezze S→E (mediana per posizione): {r['lunghezze S->E (mediana per posizione)']}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    d = Path(sys.argv[1])
    conns = load_all(d)
    md = to_md(verdict(conns)) + "\n### Unità osservate in ingresso al sito (osservazione, audit 116)\n\n" + json.dumps(units(conns), ensure_ascii=False) + "\n\n### Addendum 1 (H-P2a, ClientHello come unità o spezzato)\n\n" + json.dumps(clienthello_bursts(conns), ensure_ascii=False) + "\n"
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(md)
    print(md)


if __name__ == "__main__":
    main()
