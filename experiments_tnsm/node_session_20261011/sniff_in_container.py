#!/usr/bin/env python3
"""Header-only sniffer that runs INSIDE a node container (audit 116): AF_PACKET (NET_RAW is a default Docker capability), stdlib only, no sudo.
Records, for TCP port 8000 only, one JSON line per packet: time (CLOCK_REALTIME), direction (out = PACKET_OUTGOING), addresses, ports, flags, seq, ack, payload length,
the MSS option of a SYN and the FIRST 5 PAYLOAD BYTES in hex (enough to tell a TLS record header from clear-text HTTP); no other payload is read or stored.
Note: the tap sees outgoing packets AFTER the netem queue (dropped packets are not seen) and incoming ones on arrival.
Usage: python3 sniff_in_container.py <out.jsonl> [--name <container name>] [--seconds N]   (first line: {"hdr": {"name", "ip", "t"}}; STOP: SIGTERM/SIGINT or a file <out>.STOP)"""
from __future__ import annotations

import json
import os
import signal
import socket
import struct
import sys
import time

PORT = 8000
PACKET_OUTGOING = 4


def parse_frame(b: bytes) -> dict | None:
    """Ethernet II / IPv4 / TCP headers of one frame -> dict, or None (not IPv4, not TCP, truncated)."""
    if len(b) < 14 + 20 + 20 or struct.unpack("!H", b[12:14])[0] != 0x0800:
        return None
    ip = b[14:]
    if ip[0] >> 4 != 4 or ip[9] != 6:
        return None
    ihl = (ip[0] & 15) * 4
    total = struct.unpack("!H", ip[2:4])[0]
    tcp = ip[ihl:total]
    if len(tcp) < 20:
        return None
    sport, dport, seq, ack, off_flags = struct.unpack("!HHIIH", tcp[:14])
    doff = (off_flags >> 12) * 4
    if doff < 20 or len(tcp) < doff:
        return None
    flags = off_flags & 0x3F
    payload = tcp[doff:]
    mss = None
    opts, i = tcp[20:doff], 0
    while i < len(opts):
        kind = opts[i]
        if kind == 0:
            break
        if kind == 1:
            i += 1
            continue
        if i + 1 >= len(opts) or opts[i + 1] < 2:
            break
        if kind == 2 and opts[i + 1] == 4 and i + 4 <= len(opts):
            mss = struct.unpack("!H", opts[i + 2:i + 4])[0]
        i += opts[i + 1]
    return {"src": socket.inet_ntoa(ip[12:16]), "sport": sport, "dst": socket.inet_ntoa(ip[16:20]), "dport": dport, "flags": flags, "seq": seq, "ack": ack,
            "len": len(payload), "mss": mss, "p0": payload[:5].hex()}


def keep(p: dict) -> bool:
    return p["sport"] == PORT or p["dport"] == PORT


def main() -> None:
    out = sys.argv[1]
    seconds = float(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else 7200.0
    stop = {"v": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(v=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(v=True))
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
    s.settimeout(0.2)
    ip = socket.gethostbyname(socket.gethostname())
    t_end, last_flush = time.time() + seconds, 0.0
    with open(out, "a") as f:
        name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else socket.gethostname()
        f.write(json.dumps({"hdr": {"name": name, "ip": ip, "t": time.time()}}) + "\n")
        f.flush()
        while not stop["v"] and time.time() < t_end and not os.path.exists(out + ".STOP"):
            try:
                b, addr = s.recvfrom(65535)
            except socket.timeout:
                b = None
            if b is not None:
                t = time.time()
                p = parse_frame(b)
                if p is not None and keep(p):
                    f.write(json.dumps({"t": t, "dir": "out" if addr[2] == PACKET_OUTGOING else "in", **p}) + "\n")
            if time.time() - last_flush > 0.2:
                f.flush()
                last_flush = time.time()
        f.flush()


if __name__ == "__main__":
    main()
