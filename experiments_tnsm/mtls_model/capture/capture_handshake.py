"""Step 1 of the mTLS model work (audit 92): capture of ONE cold mTLS connection and one /apply_fanout request, no loss, in a private netns on the local machine.
NOT a timing measurement and NOT a validation: it only records, for every TCP packet with payload, the direction, payload bytes and the TLS record/handshake types, so that the
flights (ClientHello, server flight, client flight, request, response, session tickets) and their sizes are OBSERVED instead of assumed.
Server = the production mTLS configuration (dib.registry.distributed.mtls.server_config, TLS context of uvicorn); client = httpx with mtls.client_context, the same call as
service._deliver_to_site (service.py:798) with the same JSON body. The server app is a minimal ASGI app that answers {"applied": true}: the response size is NOT that of the real service.
Capture on lo: the loopback MTU is 65536, so packet sizes show the application WRITES, not MSS segmentation; the number of wire segments is derived with a stated MSS (see audit 92).
Usage: unshare -n python3 capture_handshake.py <pki_dir> <out.json>   (the script brings lo up itself)."""
from __future__ import annotations

import json
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

PKI = Path(sys.argv[1])
OUT = Path(sys.argv[2])
PORT = 18443
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "code" / "src"))
import httpx  # noqa: E402
import uvicorn  # noqa: E402

from dib.registry.distributed import mtls  # noqa: E402

subprocess.run(["ip", "link", "set", "lo", "up"], check=True)
events: list[dict] = []
stop = threading.Event()
T0 = time.monotonic()


def tls_summary(payload: bytes) -> list[str]:
    out, i = [], 0
    names = {20: "ChangeCipherSpec", 21: "Alert", 22: "Handshake", 23: "ApplicationData"}
    hs = {1: "ClientHello", 2: "ServerHello", 4: "NewSessionTicket", 8: "EncryptedExtensions", 11: "Certificate", 13: "CertificateRequest", 15: "CertificateVerify", 20: "Finished"}
    while i + 5 <= len(payload):
        ct, ln = payload[i], struct.unpack("!H", payload[i + 3:i + 5])[0]
        name = names.get(ct, f"?{ct}")
        if ct == 22 and i + 5 < len(payload):
            name += ":" + hs.get(payload[i + 5], f"?{payload[i + 5]}")
        out.append(f"{name}[{ln}]")
        i += 5 + ln
    return out


def sniff() -> None:
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    s.bind(("lo", 0))
    s.settimeout(0.2)
    while not stop.is_set():
        try:
            pkt = s.recv(70000)
        except socket.timeout:
            continue
        ip = pkt[14:]
        if len(ip) < 20 or ip[9] != 6:
            continue
        ihl = (ip[0] & 15) * 4
        tcp = ip[ihl:]
        sport, dport = struct.unpack("!HH", tcp[:4])
        if PORT not in (sport, dport):
            continue
        off = (tcp[12] >> 4) * 4
        flags = tcp[13]
        payload = tcp[off:struct.unpack("!H", ip[2:4])[0] - ihl]
        events.append({"t_ms": round((time.monotonic() - T0) * 1000, 2), "dir": "C->S" if dport == PORT else "S->C", "flags": flags, "payload": len(payload),
                       "tls": tls_summary(payload) if payload else [], "mss_opt": (struct.unpack("!H", tcp[22:24])[0] if flags & 2 and off >= 24 and tcp[20] == 2 else None)})
    s.close()


async def app(scope, receive, send):
    if scope["type"] != "http":
        return
    while True:
        m = await receive()
        if not m.get("more_body"):
            break
    body = b'{"applied": true}'
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


cfg = mtls.server_config(app, host="127.0.0.1", port=PORT, certfile=PKI / "site-0.crt", keyfile=PKI / "site-0.key", cafile=PKI / "ca.crt", log_level="warning")
server = uvicorn.Server(cfg)
threading.Thread(target=server.run, daemon=True).start()
threading.Thread(target=sniff, daemon=True).start()
for _ in range(100):
    if server.started:
        break
    time.sleep(0.05)
assert server.started, "server did not start"
time.sleep(0.3)
ctx = mtls.client_context(PKI / "evidence.crt", PKI / "evidence.key", PKI / "ca.crt")
body = {"score_id": 1, "seq": 1, "event_type": "dispute", "target_state": "disputed"}
mark = len(events)
r = httpx.post(f"https://127.0.0.1:{PORT}/apply_fanout", json=body, timeout=1.0, verify=ctx)
time.sleep(0.5)
stop.set()
time.sleep(0.4)
info = {"status": r.status_code, "response_body_bytes": len(r.content), "request_json_bytes": len(json.dumps(body)),
        "events": events[mark:], "python": sys.version.split()[0], "uvicorn": uvicorn.__version__, "httpx": httpx.__version__,
        "client_cert_der_bytes": len(__import__("ssl").PEM_cert_to_DER_cert((PKI / "evidence.crt").read_text())),
        "server_cert_der_bytes": len(__import__("ssl").PEM_cert_to_DER_cert((PKI / "site-0.crt").read_text())),
        "ca_cert_der_bytes": len(__import__("ssl").PEM_cert_to_DER_cert((PKI / "ca.crt").read_text()))}
OUT.write_text(json.dumps(info, indent=1))
print(json.dumps({k: v for k, v in info.items() if k != "events"}))
for e in info["events"]:
    if e["payload"] or e["flags"] & 3:
        print(e["t_ms"], e["dir"], "flags", e["flags"], "payload", e["payload"], e["tls"], "mss", e["mss_opt"])
