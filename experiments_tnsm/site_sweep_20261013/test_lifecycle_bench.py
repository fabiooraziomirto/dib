"""lifecycle_bench: each writer's requests are sequential and cycle commit/dispute/restore on its own fact.

Hypothesis: with W writers, every writer issues exactly the cycle in order on one fact, and
no two requests of the same writer overlap in time. Falsification: any assertion below.
"""
import threading
import time

import httpx

import lifecycle_bench as lb


def test_cycle_order_and_no_overlap(monkeypatch):
    seen, active, lock = [], {}, threading.Lock()

    class Client:
        def post(self, url, json):
            w = int(json["endpoint"].split("-w")[1].split(".")[0])
            with lock:
                assert not active.get(w), "two requests of one writer overlap"
                active[w] = True
                seen.append((w, url.rsplit("/", 1)[1], json["endpoint"]))
            time.sleep(0.001)
            with lock:
                active[w] = False
            return httpx.Response(200, json={"applied": True})

    monkeypatch.setattr(lb.base, "N_SITES", 2)
    monkeypatch.setattr(lb.base, "_client_for", lambda identity: Client())
    records, _ = lb.run_batch("t", 4, 6)
    assert len(records) == 24 and all(r["changed"] for r in records)
    for w in range(4):
        ops = [op for ww, op, _ in seen if ww == w]
        assert ops == ["commit", "dispute", "restore"] * 2
        assert len({ep for ww, _, ep in seen if ww == w}) == 1


def test_409_is_not_a_change(monkeypatch):
    monkeypatch.setattr(lb.base, "N_SITES", 1)
    monkeypatch.setattr(lb.base, "_client_for", lambda identity: type("C", (), {"post": lambda self, u, json: httpx.Response(409, json={})})())
    r = lb.worker(0, "t", 3, 0.0)
    assert [x["outcome"] for x in r] == ["rejected"] * 3 and not any(x["changed"] for x in r)
