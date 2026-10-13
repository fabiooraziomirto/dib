"""Echo server for the gateway campaign: one thread per TCP port, one thread per
connection, echoes every byte until the peer closes. Unlike openwrt/echo_service.py
(one recv per connection) it keeps a connection open, so an ESTABLISHED flow can be
observed across a policy change. Runs inside the allowed-service container."""
import argparse
import socket
import threading


def serve_conn(conn: socket.socket) -> None:
    with conn:
        while True:
            try:
                data = conn.recv(4096)
            except OSError:
                return
            if not data:
                return
            try:
                conn.sendall(data)
            except OSError:
                return


def listen(port: int) -> None:
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(256)
    while True:
        conn, _ = s.accept()
        threading.Thread(target=serve_conn, args=(conn,), daemon=True).start()


p = argparse.ArgumentParser()
p.add_argument("--tcp", type=int, action="append", required=True)
a = p.parse_args()
for port in a.tcp[1:]:
    threading.Thread(target=listen, args=(port,), daemon=True).start()
listen(a.tcp[0])
