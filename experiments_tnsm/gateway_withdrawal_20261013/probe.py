"""Traffic prober, run in the DEVICE's network namespace with the host interpreter:

    nsenter -t <device pid> -n python probe.py --out F --host 172.31.0.10 --ports 8080,9090

Clock: time.monotonic() = CLOCK_MONOTONIC of the host kernel; the containers share the
kernel and no time namespace is used (checked by the harness), so these timestamps are
on the same clock as the harness and the pollers.

Two probe kinds per port, written as JSON lines (flushed per line):
  new  every --period s: a NEW TCP connection, send 1 byte, expect it echoed
       (timeout --timeout). ok=false with the errno name otherwise.
  est  one connection opened at start (kind est_open); every --est-period s send 1
       byte on it and wait for the echo (timeout --est-timeout). After the first
       failure the socket is not reused and no reconnection is made: a later
       success would be a NEW connection, which is what `new` measures.
Stops on SIGTERM/SIGINT.
"""
from __future__ import annotations

import argparse
import errno
import json
import signal
import socket
import threading
import time

stop = threading.Event()
lock = threading.Lock()


def emit(out, rec: dict) -> None:
    with lock:
        out.write(json.dumps(rec, separators=(",", ":")) + "\n")
        out.flush()


def err_name(exc: BaseException) -> str:
    if isinstance(exc, socket.timeout):
        return "timeout"
    if isinstance(exc, OSError) and exc.errno:
        return errno.errorcode.get(exc.errno, str(exc.errno))
    return type(exc).__name__


def new_loop(out, host: str, port: int, period: float, timeout: float) -> None:
    while not stop.is_set():
        s = time.monotonic()
        ok, err = False, None
        try:
            with socket.create_connection((host, port), timeout=timeout) as c:
                c.settimeout(timeout)
                c.sendall(b"n")
                ok = c.recv(1) == b"n"
                if not ok:
                    err = "short"
        except Exception as exc:  # noqa: BLE001 - every outcome is data
            err = err_name(exc)
        e = time.monotonic()
        emit(out, {"k": "new", "p": port, "s": s, "e": e, "ok": ok, "err": err})
        stop.wait(max(0.0, period - (e - s)))


def est_loop(out, host: str, port: int, period: float, timeout: float) -> None:
    s = time.monotonic()
    try:
        c = socket.create_connection((host, port), timeout=timeout)
        c.settimeout(timeout)
        emit(out, {"k": "est_open", "p": port, "s": s, "e": time.monotonic(), "ok": True, "err": None})
    except Exception as exc:  # noqa: BLE001
        emit(out, {"k": "est_open", "p": port, "s": s, "e": time.monotonic(), "ok": False, "err": err_name(exc)})
        return
    with c:
        while not stop.is_set():
            s = time.monotonic()
            ok, err = False, None
            try:
                c.sendall(b"e")
                ok = c.recv(1) == b"e"
                if not ok:
                    err = "closed"
            except Exception as exc:  # noqa: BLE001
                err = err_name(exc)
            e = time.monotonic()
            emit(out, {"k": "est", "p": port, "s": s, "e": e, "ok": ok, "err": err})
            if not ok:
                return
            stop.wait(max(0.0, period - (e - s)))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--host", required=True)
    p.add_argument("--ports", required=True)
    p.add_argument("--period", type=float, default=0.02)
    p.add_argument("--timeout", type=float, default=0.5)
    p.add_argument("--est-period", type=float, default=0.05)
    p.add_argument("--est-timeout", type=float, default=1.0)
    a = p.parse_args()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    ports = [int(x) for x in a.ports.split(",")]
    with open(a.out, "a", buffering=1) as out:
        emit(out, {"k": "start", "s": time.monotonic(), "ports": ports, "period": a.period, "timeout": a.timeout,
                   "est_period": a.est_period, "est_timeout": a.est_timeout})
        threads = []
        for port in ports:
            threads.append(threading.Thread(target=est_loop, args=(out, a.host, port, a.est_period, a.est_timeout), daemon=True))
            threads.append(threading.Thread(target=new_loop, args=(out, a.host, port, a.period, a.timeout), daemon=True))
        for t in threads:
            t.start()
        while not stop.wait(0.1):
            pass
        for t in threads:
            t.join(timeout=2)
        emit(out, {"k": "stop", "s": time.monotonic()})


if __name__ == "__main__":
    main()
