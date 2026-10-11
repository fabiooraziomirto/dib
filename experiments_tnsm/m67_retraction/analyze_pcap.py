"""Header-only analysis of the degraded captures (questions Q1-Q8 of docs/audit/30_domande_pcap_degraded.md, committed BEFORE any pcap was
opened). Pure Python (struct); IPv4/TCP, Ethernet (DLT 1) or Linux cooked (DLT 113); only addresses, ports, flags, seq/ack, lengths and
timestamps are read: THE PAYLOAD IS NEVER READ OR PRINTED (arm D is clear text). The decision rules are those of audit 30; nothing is tuned here.
Usage: python3 analyze_pcap.py <pcap dir> <arm D|C> [--out file.md]   (expects dib_degraded_<arm>_{evidence,site0}.pcap)"""
from __future__ import annotations

import collections
import statistics as S
import struct
import sys
from pathlib import Path

PORT = 8000


def read_pcap(path: Path) -> list[dict]:
    b = path.read_bytes()
    magic = b[:4]
    if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
        e, nano = "<", magic == b"\x4d\x3c\xb2\xa1"
    elif magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
        e, nano = ">", magic == b"\xa1\xb2\x3c\x4d"
    else:
        raise ValueError("not a classic pcap file")
    link = struct.unpack(e + "I", b[20:24])[0]
    off, out = 24, []
    while off + 16 <= len(b):
        sec, frac, caplen, _wire = struct.unpack(e + "IIII", b[off:off + 16])
        off += 16
        data = b[off:off + caplen]
        off += caplen
        ts = sec + frac / (1e9 if nano else 1e6)
        p = parse_frame(data, link, ts)
        if p:
            out.append(p)
    return out


def parse_frame(d: bytes, link: int, ts: float):
    if link == 1:
        if len(d) < 14 or d[12:14] != b"\x08\x00":
            return None
        ip = 14
    elif link == 113:
        if len(d) < 16 or d[14:16] != b"\x08\x00":
            return None
        ip = 16
    else:
        return None
    if len(d) < ip + 20 or d[ip] >> 4 != 4 or d[ip + 9] != 6:
        return None
    ihl = (d[ip] & 15) * 4
    tot = struct.unpack(">H", d[ip + 2:ip + 4])[0]
    ipid = struct.unpack(">H", d[ip + 4:ip + 6])[0]
    src, dst = ".".join(map(str, d[ip + 12:ip + 16])), ".".join(map(str, d[ip + 16:ip + 20]))
    t = ip + ihl
    if len(d) < t + 20:
        return None
    sport, dport, seq, ack = struct.unpack(">HHII", d[t:t + 12])
    doff, flags = (d[t + 12] >> 4) * 4, d[t + 13]
    return {"ts": ts, "src": src, "dst": dst, "sport": sport, "dport": dport, "seq": seq, "ack": ack, "flags": flags,
            "plen": max(0, tot - ihl - doff), "ipid": ipid}


SYN, FIN, RST, ACK = 0x02, 0x01, 0x04, 0x10


def pure_ack(p):
    return p["flags"] & (SYN | FIN | RST) == 0 and p["plen"] == 0


def key(p):
    return (p["src"], p["dst"], p["sport"], p["dport"], p["flags"], p["seq"], p["ack"], p["plen"], p["ipid"])


def match(tx: list[dict], rx: list[dict], lo=-0.01, hi=0.6):
    """Greedy per-key matching: k-th tx with the earliest unmatched rx at t_rx - t_tx in [lo, hi]."""
    rxd = collections.defaultdict(list)
    for p in rx:
        rxd[key(p)].append(p["ts"])
    for v in rxd.values():
        v.sort()
    used = collections.defaultdict(int)
    deltas, unmatched = [], 0
    for p in sorted(tx, key=lambda x: x["ts"]):
        lst = rxd.get(key(p), [])
        i = used[key(p)]
        while i < len(lst) and lst[i] < p["ts"] + lo:
            i += 1
        if i < len(lst) and lst[i] - p["ts"] <= hi:
            deltas.append(lst[i] - p["ts"])
            used[key(p)] = i + 1
        else:
            unmatched += 1
            used[key(p)] = i
    rx_unmatched = sum(len(v) for v in rxd.values()) - len(deltas)
    return deltas, unmatched, rx_unmatched


def clopper(x, n, a=0.05):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import analyze_c
    return analyze_c.clopper_pearson(x, n, a)


def q1(ev, s0, ev_ip, s0_ip):
    out = []
    for name, tx_cap, rx_cap, src, dst in (("evidence -> site-0", ev, s0, ev_ip, s0_ip), ("site-0 -> evidence", s0, ev, s0_ip, ev_ip)):
        tx = [p for p in tx_cap if p["src"] == src and p["dst"] == dst]
        rx = [p for p in rx_cap if p["src"] == src and p["dst"] == dst]
        d, un, rxun = match(tx, rx)
        med = S.median(d) * 1000 if d else None
        frac = un / len(tx) if tx else None
        ci = clopper(un, len(tx)) if tx else None
        verdict = "undetermined"
        if med is not None and frac is not None:
            if frac <= 0.01 and med < 20:
                verdict = "tap AFTER the qdisc"
            elif 0.02 <= frac <= 0.09 and 180 <= med <= 220:
                verdict = "tap BEFORE the qdisc"
        out.append({"dir": name, "n_tx_seen_at_sender": len(tx), "n_rx_seen_at_receiver": len(rx), "matched": len(d), "tx_unmatched": un, "tx_unmatched_frac": frac,
                    "ci95": ci, "rx_unmatched": rxun, "delta_median_ms": med,
                    "delta_p05_p95_ms": (sorted(d)[int(0.05 * len(d))] * 1000, sorted(d)[min(len(d) - 1, int(0.95 * len(d)))] * 1000) if d else None, "verdict": verdict})
    return out


def flows(cap):
    f = collections.defaultdict(list)
    for p in cap:
        a, b = (p["src"], p["sport"]), (p["dst"], p["dport"])
        f[(a, b) if a > b else (b, a)].append(p)
    return f


def client_of(plist):
    s = [p for p in plist if p["flags"] & SYN and not p["flags"] & ACK]
    return (s[0]["src"], s[0]["sport"]) if s else None


def q3(cap, src_ip):
    iv = []
    for plist in flows(cap).values():
        syns = sorted(p["ts"] for p in plist if p["flags"] & SYN and not p["flags"] & ACK and p["src"] == src_ip)
        iv += [b - a for a, b in zip(syns, syns[1:])]
    return sorted(iv)


def q4(cap, src_ip):
    out = []
    for plist in flows(cap).values():
        seen = collections.defaultdict(list)
        for p in sorted(plist, key=lambda x: x["ts"]):
            if p["plen"] > 0:
                seen[(p["src"], p["seq"], p["plen"])].append(p["ts"])
        for v in seen.values():
            out += [b - a for a, b in zip(v, v[1:])]
    return sorted(out)


def q5_q6(cap, ev_ip):
    """Per evidence->site connection (client = ev_ip, dport PORT): flights, completion, SYN retransmissions, client aborts."""
    res = []
    for plist in flows(cap).values():
        plist = sorted(plist, key=lambda x: x["ts"])
        syn = [p for p in plist if p["flags"] & SYN and not p["flags"] & ACK]
        if not syn or syn[0]["src"] != ev_ip or syn[0]["dport"] != PORT:
            continue
        cl = syn[0]["src"]
        body = [p for p in plist if not pure_ack(p) and not p["flags"] & (FIN | RST)]
        flights, last = 0, None
        t_last = None
        for p in body:
            d = p["src"] == cl
            if last is None or d != last or (t_last is not None and p["ts"] - t_last > 0.1 and False):
                flights += 1
            last, t_last = d, p["ts"]
        server_payload = [p for p in plist if p["src"] != cl and p["plen"] > 0]
        client_end = [p for p in plist if p["src"] == cl and p["flags"] & (FIN | RST)]
        res.append({"flights": flights, "n_syn": len(syn), "completed": bool(server_payload), "client_closed": bool(client_end),
                    "dur": plist[-1]["ts"] - plist[0]["ts"], "t0": plist[0]["ts"]})
    return res


def q8(cap):
    """Capture gaps: ACKs that acknowledge bytes beyond the highest seq+len seen in the other direction of the same flow."""
    gaps = n = 0
    for plist in flows(cap).values():
        hi = {}
        for p in sorted(plist, key=lambda x: x["ts"]):
            hi[p["src"]] = max(hi.get(p["src"], 0), p["seq"] + p["plen"] + (1 if p["flags"] & (SYN | FIN) else 0))
        for p in plist:
            other = [k for k in hi if k != p["src"]]
            if p["flags"] & ACK and other:
                n += 1
                if p["ack"] > hi[other[0]] + 1:
                    gaps += 1
    return gaps, n


def fmt_q(xs, q):
    return f"{xs[min(len(xs) - 1, int(q * len(xs)))]:.3f}" if xs else "-"


def report(d: Path, arm: str) -> str:
    ev = read_pcap(d / f"dib_degraded_{arm}_evidence.pcap")
    s0 = read_pcap(d / f"dib_degraded_{arm}_site0.pcap")
    syn_dst = collections.Counter(p["dst"] for p in s0 if p["flags"] & SYN and not p["flags"] & ACK and p["dport"] == PORT)
    s0_ip = syn_dst.most_common(1)[0][0]
    ev_ip = collections.Counter(p["src"] for p in ev if p["dst"] == s0_ip and p["dport"] == PORT).most_common(1)[0][0]
    L = [f"## Arm {arm}: evidence {ev_ip}, site-0 {s0_ip}", f"packets: evidence capture {len(ev)}, site-0 capture {len(s0)}; time span evidence {min(p['ts'] for p in ev):.3f}-{max(p['ts'] for p in ev):.3f}, "
         f"site-0 {min(p['ts'] for p in s0):.3f}-{max(p['ts'] for p in s0):.3f}", "", "### Q1 tap side (matched header keys between the two namespaces)"]
    for r in q1(ev, s0, ev_ip, s0_ip):
        L.append(f"- {r['dir']}: sent-seen {r['n_tx_seen_at_sender']}, recv-seen {r['n_rx_seen_at_receiver']}, matched {r['matched']}, unmatched at receiver {r['tx_unmatched']} "
                 f"({r['tx_unmatched_frac']:.4f}, CP95 {tuple(round(x, 4) for x in r['ci95'])}), recv-seen not sent-seen {r['rx_unmatched']}, delta median {r['delta_median_ms']:.2f} ms "
                 f"(p05/p95 {r['delta_p05_p95_ms'][0]:.2f}/{r['delta_p05_p95_ms'][1]:.2f}) -> **{r['verdict']}**" if r["matched"] else f"- {r['dir']}: no matched packets")
    for who, cap, ip in (("evidence (sender)", ev, ev_ip),):
        iv = q3(cap, ip)
        L += ["", "### Q3 SYN retransmission intervals (s), client = evidence", f"- n = {len(iv)}; quantiles 5/50/95%: {fmt_q(iv, .05)} / {fmt_q(iv, .5)} / {fmt_q(iv, .95)}; sorted: {[round(x, 3) for x in iv[:30]]}"]
    for who, cap, ip in (("evidence", ev, ev_ip), ("site-0", s0, s0_ip)):
        iv = q4(cap, ip)
        L += ["", f"### Q4 data-segment retransmission delays (s), seen in the {who} capture (same seq+len repeated)", f"- n = {len(iv)}; sorted (first 40): {[round(x, 3) for x in iv[:40]]}"]
    rs = q5_q6(ev, ev_ip)
    comp = [r for r in rs if r["completed"]]
    fl = sorted(r["flights"] for r in comp)
    L += ["", "### Q5 flights per evidence->site connection (non-pure-ACK, non-FIN/RST packets, direction changes)",
          f"- connections evidence->site (with SYN): {len(rs)}; completed (server payload seen): {len(comp)}; flights per completed connection: median {S.median(fl) if fl else '-'}, "
          f"distribution {dict(collections.Counter(fl))}; connections per delivery cannot be derived from headers alone (see Q7)"]
    ns = collections.Counter(r["n_syn"] for r in rs)
    L += ["", "### Q6 phase timeouts (evidence->site)", f"- SYN count per connection: {dict(ns)} (connect phase not completed within the first RTO: {sum(v for k, v in ns.items() if k > 1)}/{len(rs)})",
          f"- connections with no server payload and a client FIN/RST (aborted by the client): {sum(1 for r in rs if not r['completed'] and r['client_closed'])}/{len(rs)}; "
          f"connections with no server payload at all: {sum(1 for r in rs if not r['completed'])}/{len(rs)}",
          f"- duration (s) of completed connections: 5/50/95% {fmt_q(sorted(r['dur'] for r in comp), .05)} / {fmt_q(sorted(r['dur'] for r in comp), .5)} / {fmt_q(sorted(r['dur'] for r in comp), .95)}"]
    L += ["", "### Q7 coverage", f"- evidence->site connections in the evidence capture: {len(rs)} (expected deliveries: 20 episodes x 10 sites = 200, plus retries)"]
    for who, cap in (("evidence", ev), ("site-0", s0)):
        g, n = q8(cap)
        L += ["", f"### Q8 capture-gap indicator, {who}: ACKs acknowledging bytes not seen: {g}/{n}"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    text = report(Path(sys.argv[1]), sys.argv[2])
    print(text)
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(text)
