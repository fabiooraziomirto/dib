"""Synthetic-pcap tests of analyze_pcap (no real capture is opened). Hypotheses: the parser reads Ethernet/IPv4/TCP headers and ignores the payload;
match() pairs identical packets and measures the delta; a capture 'after the qdisc' (delta ~0, nothing unmatched) and 'before the qdisc'
(delta ~0.2 s, 5% unmatched) are classified as such by q1; SYN retransmission intervals are measured. Falsification: any assertion failing."""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_pcap as a  # noqa: E402


def frame(src, dst, sport, dport, flags, seq, ack, payload=b"", ipid=0):
    ip_s = bytes(int(x) for x in src.split("."))
    ip_d = bytes(int(x) for x in dst.split("."))
    tcp = struct.pack(">HHIIBBHHH", sport, dport, seq, ack, 5 << 4, flags, 1000, 0, 0) + payload
    iph = struct.pack(">BBHHHBBH", 0x45, 0, 20 + len(tcp), ipid, 0x4000, 64, 6, 0) + ip_s + ip_d
    return b"\x00" * 12 + b"\x08\x00" + iph + tcp


def write_pcap(path, pkts):
    out = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    for ts, fr in pkts:
        out += struct.pack("<IIII", int(ts), int((ts % 1) * 1e6), len(fr), len(fr)) + fr
    path.write_bytes(out)


def test_parse_ignores_payload(tmp_path):
    write_pcap(tmp_path / "x.pcap", [(10.5, frame("1.1.1.1", "2.2.2.2", 4000, 8000, 0x18, 100, 5, payload=b"SECRET" * 10))])
    p = a.read_pcap(tmp_path / "x.pcap")[0]
    assert p["plen"] == 60 and p["dport"] == 8000 and p["seq"] == 100 and abs(p["ts"] - 10.5) < 1e-6 and "SECRET" not in str(p)


def _pairs(n, delta, drop_every):
    tx, rx = [], []
    for i in range(n):
        t = 100.0 + i * 0.01
        fr = frame("1.1.1.1", "2.2.2.2", 4000 + i, 8000, 0x02, i, 0)
        tx.append((t, fr))
        if not (drop_every and i % drop_every == 0):
            rx.append((t + delta, fr))
    return tx, rx


def test_q1_after_and_before(tmp_path):
    for delta, drop, expect in ((0.0003, 0, "tap AFTER the qdisc"), (0.2, 20, "tap BEFORE the qdisc")):
        tx, rx = _pairs(400, delta, drop)
        write_pcap(tmp_path / "ev.pcap", tx)
        write_pcap(tmp_path / "s0.pcap", rx)
        ev, s0 = a.read_pcap(tmp_path / "ev.pcap"), a.read_pcap(tmp_path / "s0.pcap")
        r = a.q1(ev, s0, "1.1.1.1", "2.2.2.2")[0]
        assert r["verdict"] == expect, r


def test_syn_retransmission_interval(tmp_path):
    pk = [(10.0, frame("1.1.1.1", "2.2.2.2", 4000, 8000, 0x02, 7, 0)), (11.0, frame("1.1.1.1", "2.2.2.2", 4000, 8000, 0x02, 7, 0))]
    write_pcap(tmp_path / "x.pcap", pk)
    iv = a.q3(a.read_pcap(tmp_path / "x.pcap"), "1.1.1.1")
    assert len(iv) == 1 and abs(iv[0] - 1.0) < 1e-5


def test_flights_counts_direction_changes(tmp_path):
    c, s = "1.1.1.1", "2.2.2.2"
    pk = [(1.0, frame(c, s, 4000, 8000, 0x02, 0, 0)), (1.4, frame(s, c, 8000, 4000, 0x12, 0, 1)), (1.4, frame(c, s, 4000, 8000, 0x10, 1, 1)),
          (1.4, frame(c, s, 4000, 8000, 0x18, 1, 1, b"x" * 50)), (1.8, frame(s, c, 8000, 4000, 0x18, 1, 51, b"y" * 80)), (1.9, frame(c, s, 4000, 8000, 0x11, 51, 81))]
    write_pcap(tmp_path / "x.pcap", pk)
    r = a.q5_q6(a.read_pcap(tmp_path / "x.pcap"), c)[0]
    assert r["flights"] == 4 and r["completed"] and r["client_closed"] and r["n_syn"] == 1      # SYN, SYN-ACK, request, response


def test_capture_host_ip_is_the_address_in_every_packet(tmp_path):
    # a site-0 capture dominated by its OWN outgoing reconcile SYNs to evidence must still identify site-0, not evidence (bug of the first run)
    pk = [(1.0 + i, frame("10.0.0.5", "10.0.0.2", 5000 + i, 8000, 0x02, 0, 0)) for i in range(30)]
    pk += [(40.0 + i, frame("10.0.0.9", "10.0.0.5", 6000 + i, 8000, 0x02, 0, 0)) for i in range(5)]
    pk += [(60.0, frame("10.0.0.1", "10.0.0.5", 7000, 8000, 0x02, 0, 0))]
    write_pcap(tmp_path / "x.pcap", pk)
    assert a.capture_host_ip(a.read_pcap(tmp_path / "x.pcap")) == "10.0.0.5"


def test_flight_pause_rule_and_common_window(tmp_path):
    c, s_ = "1.1.1.1", "2.2.2.2"
    # two client packets 0.5 s apart in the same direction are two flights (declared rule: pause > 100 ms)
    pk = [(1.0, frame(c, s_, 4000, 8000, 0x02, 0, 0)), (1.2, frame(s_, c, 8000, 4000, 0x12, 0, 1)), (1.7, frame(c, s_, 4000, 8000, 0x18, 1, 1, b"x" * 10)),
          (2.3, frame(c, s_, 4000, 8000, 0x18, 11, 1, b"y" * 10)), (2.5, frame(s_, c, 8000, 4000, 0x18, 1, 21, b"z" * 10))]
    write_pcap(tmp_path / "x.pcap", pk)
    assert a.q5_q6(a.read_pcap(tmp_path / "x.pcap"), c)[0]["flights"] == 5
    tx = [{"ts": t} for t in (1.0, 2.0, 50.0, 99.5)]
    assert [p["ts"] for p in a.in_window(tx, 10.0, 99.0)] == [50.0]
