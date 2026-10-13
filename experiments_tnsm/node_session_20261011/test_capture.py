"""sniff_in_container.py and analyze_capture.py (audit 116, header capture inside the node containers). Hypotheses (falsified by any failing assertion):
S-1 parse_frame reads Ethernet/IPv4/TCP headers only: addresses, ports, flags, seq, ack, payload length, the MSS option of a SYN and the FIRST 5 payload bytes (hex), nothing else of the payload;
S-2 non-IPv4, non-TCP and truncated frames give None; keep() retains only TCP port 8000 in either direction;
A-1 connections() pairs the evidence tap (outgoing E->S) with the site tap (outgoing S->E) by (evidence ip, evidence source port, site ip), and counts data segments per direction from the SENDER's outgoing tap;
A-2 an arm is TLS iff the first E->S data segment starts with a TLS record header (1603); D expects 2 E->S data segments, C expects 4 with exactly one S data segment before the client flight and every flight below the effective MSS 1448;
A-3 the verdict of each hypothesis is 'confermata' iff >= 95% of the VALID connections have the expected structure (MSS: the mode is 1460), 'falsificata' otherwise, 'non valutabile' with fewer than 90 valid connections;
A-4 a connection without SYN-ACK in the site tap, or without data, is not valid and is counted apart."""
import json
import socket
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_capture as ac  # noqa: E402
import sniff_in_container as sn  # noqa: E402

EV, S0 = "172.19.0.2", "172.19.0.3"


def frame(src, dst, sport, dport, flags, seq=1, ack=0, payload=b"", mss=None, proto=6, eth=0x0800):
    opts = b"\x02\x04" + struct.pack("!H", mss) if mss else b""
    doff = (20 + len(opts)) // 4
    tcp = struct.pack("!HHIIHHHH", sport, dport, seq, ack, (doff << 12) | flags, 65535, 0, 0) + opts + payload
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp), 0, 0, 64, proto, 0, socket.inet_aton(src), socket.inet_aton(dst))
    return b"\x00" * 12 + struct.pack("!H", eth) + ip + tcp


SYN, ACK, PSH = 2, 16, 8


def test_parse_syn_with_mss():
    p = sn.parse_frame(frame(EV, S0, 40000, 8000, SYN, seq=100, mss=1460))
    assert (p["src"], p["sport"], p["dst"], p["dport"]) == (EV, 40000, S0, 8000)
    assert p["flags"] == SYN and p["len"] == 0 and p["mss"] == 1460 and p["seq"] == 100


def test_parse_data_keeps_only_five_payload_bytes():
    p = sn.parse_frame(frame(EV, S0, 40000, 8000, ACK | PSH, payload=b"\x16\x03\x01\x02\x00" + b"SECRET" * 50))
    assert p["len"] == 305 and p["p0"] == "1603010200"
    assert "SECRET" not in json.dumps(p)


def test_parse_rejects_non_tcp_non_ipv4_truncated():
    assert sn.parse_frame(frame(EV, S0, 1, 2, 0, proto=17)) is None
    assert sn.parse_frame(frame(EV, S0, 1, 2, 0, eth=0x0806)) is None
    assert sn.parse_frame(b"\x00" * 20) is None


def test_keep_only_port_8000():
    assert sn.keep({"sport": 8000, "dport": 40000}) and sn.keep({"sport": 40000, "dport": 8000})
    assert not sn.keep({"sport": 22, "dport": 40000})


def pk(t, src, sport, dst, dport, flags, ln=0, mss=None, p0="", d="out"):
    return {"t": t, "dir": d, "src": src, "sport": sport, "dst": dst, "dport": dport, "flags": flags, "seq": 1, "ack": 1, "len": ln, "mss": mss, "p0": p0}


def conn(sport, tls, es_lens=None, sf_before=1, mss=1460, with_synack=True, t0=0.0):
    """Evidence tap rows and site tap rows of one connection."""
    ev, st = [], []
    ev.append(pk(t0, EV, sport, S0, 8000, SYN, mss=mss))
    if with_synack:
        st.append(pk(t0 + .06, S0, 8000, EV, sport, SYN | ACK, mss=mss))
    if tls:
        lens = es_lens or [517, 1066, 240, 93]
        ev.append(pk(t0 + .12, EV, sport, S0, 8000, ACK | PSH, lens[0], p0="1603010200"))
        for k in range(sf_before):
            st.append(pk(t0 + .18 + k * .001, S0, 8000, EV, sport, ACK | PSH, 1288 if sf_before == 1 else 700, p0="1603030000"))
        for k, ln in enumerate(lens[1:]):
            ev.append(pk(t0 + .30 + k * .001, EV, sport, S0, 8000, ACK | PSH, ln, p0="1703030000"))
        st.append(pk(t0 + .42, S0, 8000, EV, sport, ACK | PSH, 147, p0="1703030000"))
    else:
        lens = es_lens or [240, 93]
        for k, ln in enumerate(lens):
            ev.append(pk(t0 + .12 + k * .001, EV, sport, S0, 8000, ACK | PSH, ln, p0="504f535400"))
        st.append(pk(t0 + .30, S0, 8000, EV, sport, ACK | PSH, 147, p0="4854545000"))
    return ev, st


def write_captures(tmp_path, conns):
    ev = [{"hdr": {"name": "dibtnsm-evidence-1", "ip": EV}}]
    st = [{"hdr": {"name": "dibtnsm-site-0-1", "ip": S0}}]
    for e, s in conns:
        ev += e
        st += s
    for name, rows in (("dibtnsm-evidence-1.jsonl", ev), ("dibtnsm-site-0-1.jsonl", st)):
        (tmp_path / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_connections_pair_and_count(tmp_path):
    write_captures(tmp_path, [conn(40001, True), conn(40002, False, t0=5.0)])
    cs = {c["sport"]: c for c in ac.connections(ac.load(tmp_path))}
    assert cs[40001]["tls"] and len(cs[40001]["es_data"]) == 4 and cs[40001]["n_sf"] == 1 and cs[40001]["valid"]
    assert (not cs[40002]["tls"]) and len(cs[40002]["es_data"]) == 2 and cs[40002]["valid"]
    assert cs[40001]["syn_mss"] == 1460 and cs[40001]["synack_mss"] == 1460


def test_connection_without_synack_not_valid(tmp_path):
    write_captures(tmp_path, [conn(40001, True, with_synack=False)])
    (c,) = ac.connections(ac.load(tmp_path))
    assert not c["valid"]


def many(n, **kw):
    return [conn(40000 + i, **kw, t0=i * 2.0) for i in range(n)]


def test_verdict_all_expected(tmp_path):
    write_captures(tmp_path, many(100, tls=True)[:100] + [conn(41000 + i, False, t0=300 + i) for i in range(100)])
    v = ac.verdict(ac.connections(ac.load(tmp_path)))
    assert v["D"]["H-P1b"]["verdetto"] == "confermata" and v["C"]["H-P1c"]["verdetto"] == "confermata"
    assert v["D"]["H-P1a"]["verdetto"] == "confermata" and v["C"]["H-P1a"]["verdetto"] == "confermata"


def test_verdict_falsified_when_flight_split(tmp_path):
    cs = many(100, tls=True, sf_before=2) + [conn(41000 + i, False, t0=300 + i) for i in range(100)]
    write_captures(tmp_path, cs)
    v = ac.verdict(ac.connections(ac.load(tmp_path)))
    assert v["C"]["H-P1c"]["verdetto"] == "falsificata" and v["C"]["H-P1c"]["quota"] == 0.0
    assert v["D"]["H-P1b"]["verdetto"] == "confermata"


def test_verdict_falsified_on_extra_request_segment(tmp_path):
    cs = [conn(41000 + i, False, es_lens=[240, 90, 3], t0=300 + i) for i in range(100)] + many(100, tls=True)
    write_captures(tmp_path, cs)
    v = ac.verdict(ac.connections(ac.load(tmp_path)))
    assert v["D"]["H-P1b"]["verdetto"] == "falsificata"


def test_verdict_threshold_95_percent(tmp_path):
    good = [conn(41000 + i, False, t0=300 + i) for i in range(95)]
    bad = [conn(42000 + i, False, es_lens=[240, 90, 3], t0=500 + i) for i in range(5)]
    bad4 = [conn(43000 + i, False, es_lens=[240, 90, 3], t0=700 + i) for i in range(1)]
    write_captures(tmp_path, good + bad + many(100, tls=True))
    assert ac.verdict(ac.connections(ac.load(tmp_path)))["D"]["H-P1b"]["verdetto"] == "confermata"   # exactly 95/100
    write_captures(tmp_path, good + bad + bad4 + many(100, tls=True))
    assert ac.verdict(ac.connections(ac.load(tmp_path)))["D"]["H-P1b"]["verdetto"] == "falsificata"   # 95/101 < 0.95


def test_not_evaluable_below_90_valid(tmp_path):
    write_captures(tmp_path, many(50, tls=True) + [conn(41000 + i, False, t0=300 + i) for i in range(100)])
    v = ac.verdict(ac.connections(ac.load(tmp_path)))
    assert v["C"]["H-P1c"]["verdetto"] == "non valutabile" and v["D"]["H-P1b"]["verdetto"] == "confermata"


def test_mss_mode_other_than_1460_falsifies(tmp_path):
    write_captures(tmp_path, many(100, tls=True, mss=1440) + [conn(41000 + i, False, t0=300 + i) for i in range(100)])
    v = ac.verdict(ac.connections(ac.load(tmp_path)))
    assert v["C"]["H-P1a"]["verdetto"] == "falsificata" and v["C"]["H-P1a"]["moda"] == 1440
    assert v["D"]["H-P1a"]["verdetto"] == "confermata"


def test_load_all_reads_generations(tmp_path):
    for g, tls in (("gen1", False), ("gen2", True)):
        d = tmp_path / g
        d.mkdir()
        write_captures(d, many(3, tls=tls))
    cs = ac.load_all(tmp_path)
    assert {c["gen"] for c in cs} == {"gen1", "gen2"} and sum(c["tls"] for c in cs) == 3 and len(cs) == 6


import capture_helper as ch  # noqa: E402


def test_helper_new_generation_after_quiet_period():
    st = {"gen": 0, "last_new": float("-inf"), "seen": set()}
    first = ch.assign(st, [("a1", "dibtnsm-evidence-1"), ("b1", "dibtnsm-site-0-1"), ("x", "other")], 100.0)
    assert [(g, n) for g, _, n in first] == [(1, "dibtnsm-evidence-1"), (1, "dibtnsm-site-0-1")]
    assert ch.assign(st, [("a1", "dibtnsm-evidence-1"), ("b1", "dibtnsm-site-0-1")], 101.0) == []          # nothing new
    assert [g for g, _, _ in ch.assign(st, [("c1", "dibtnsm-site-1-1")], 102.0)] == [1]                   # same cluster, within 20 s
    second = ch.assign(st, [("a2", "dibtnsm-evidence-1"), ("b2", "dibtnsm-site-0-1")], 400.0)             # recreated cluster
    assert {g for g, _, _ in second} == {2}


def test_helper_exec_cmd_runs_as_root_detached():
    c = ch.exec_cmd("dibtnsm-site-3-1", 2)
    assert c[:5] == ["docker", "exec", "-d", "-u", "0"] and "/capture/gen2/dibtnsm-site-3-1.jsonl" in c and c[-2:] == ["--name", "dibtnsm-site-3-1"]


def test_units_intact_and_split(tmp_path):
    ev, st = conn(40001, True)
    st_in = [pk(r["t"], r["src"], r["sport"], r["dst"], r["dport"], r["flags"], r["len"], p0=r["p0"], d="in") for r in ev if r["len"] > 0]
    write_captures(tmp_path, [(ev, st + st_in)])
    cs = ac.connections(ac.load(tmp_path))
    u = ac.units(cs)
    assert u["C"]["valide"] == 1 and u["C"]["ingresso_uguale_all_uscita"] == 1 and u["C"]["primo_segmento_E_S_oltre_MSS"] == 0   # 517 byte ClientHello
    ev2, st2 = conn(40002, True, es_lens=[1537, 853, 226, 93])
    st2_in = [pk(r["t"], r["src"], r["sport"], r["dst"], r["dport"], r["flags"], r["len"], p0=r["p0"], d="in") for r in ev2 if r["len"] > 0]
    st2_in = [x if x["len"] != 1537 else {**x, "len": 1448} for x in st2_in] + [pk(1.0, EV, 40002, S0, 8000, 24, 89, p0="00", d="in")]
    write_captures(tmp_path, [(ev2, st2 + st2_in)])
    u2 = ac.units(ac.connections(ac.load(tmp_path)))
    assert u2["C"]["primo_segmento_E_S_oltre_MSS"] == 1 and u2["C"]["di_cui_arrivati_spezzati"] == 1 and u2["C"]["ingresso_uguale_all_uscita"] == 0
