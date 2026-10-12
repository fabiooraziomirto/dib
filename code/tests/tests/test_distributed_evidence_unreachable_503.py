"""Audit 102 (written BEFORE the change; falsified by any failing assertion). On the node, mTLS and 5 % loss, 7 of 50 setups got HTTP 500 because the service's call to the evidence
(`_evidence_get_score`, httpx timeout) was not caught. The evidence being unreachable or failing is a 503 ("evidence unreachable"), never an unhandled 500, and the local state is unchanged.
 E-1  /query with the evidence unreachable -> 503 (not an exception out of the app, not 500) and no local row is created;
 E-2  /commit with the evidence unreachable -> 503 and the site's record stays monitor-only (no committing/active);
 E-3  /local_restore with the evidence unreachable -> 503 and the record stays revoked/local (fail-closed as before: it was an unhandled error, now a clean refusal);
 E-4  /query whose SECOND read fails (the evidence answers the first, then becomes unreachable) -> 503 and the reservation is dropped (no staging row);
 E-5  the evidence answering normally is unchanged: /query + /commit -> 200 and active, and an unknown fact is still 404/applied False as before.
"""
from _dist_harness import DEFAULT_ENDPOINT, DEVICE, make_cluster  # noqa: F401
from fastapi.testclient import TestClient

N = 2


def _quiet(c, i=0):
    return TestClient(c.site_mods[i].app, raise_server_exceptions=False)


def _post(c, step, ep=DEFAULT_ENDPOINT):
    """The seeded fact by default: with another endpoint the FIRST read would answer 404 and the test would not reach the second read (a first version of E-4 did exactly that)."""
    return _quiet(c).post(f"/{step}", json={"device_type": DEVICE, "endpoint": ep, "protocol": "https", "port": 443})


def _rows(c):
    return c.site_mods[0]._site_db.run(lambda con: con.execute("SELECT score_id, state FROM local_decisions").fetchall())


def test_e1_query_503(make_cluster):
    c = make_cluster(n_sites=N)
    c.seed()
    c.net.evidence_down = True
    assert _post(c, "query").status_code == 503
    assert _rows(c) == []


def test_e2_commit_503(make_cluster):
    c = make_cluster(n_sites=N)
    sid = c.seed()
    assert c.stage(0).json()["applied"] is True
    c.net.evidence_down = True
    assert _post(c, "commit").status_code == 503
    assert _rows(c) == [(sid, "monitor-only")]


def test_e3_local_restore_503(make_cluster):
    c = make_cluster(n_sites=N)
    sid = c.seed()
    assert c.stage(0).json()["applied"] is True and c.commit(0).status_code == 200 and c.local_revoke(0).status_code == 200
    c.net.evidence_down = True
    assert _post(c, "local_restore").status_code == 503
    st = c.state(0, sid)
    assert (st["state"], st["origin"]) == ("revoked", "local")


def test_e4_second_read_failure_drops_the_reservation(make_cluster):
    c = make_cluster(n_sites=N)
    c.seed()
    c.net.after("GET", "/scores", lambda: setattr(c.net, "evidence_down", True))
    assert _post(c, "query").status_code == 503
    assert _rows(c) == []


def test_e5_normal_path_unchanged(make_cluster):
    c = make_cluster(n_sites=N)
    sid = c.seed()
    assert c.stage(0).json()["applied"] is True and c.commit(0).status_code == 200
    assert c.state(0, sid)["state"] == "active"
    assert _post(c, "query", ep="unknown.example").status_code in (200, 404)


# ---- review of 2026-10-12: only transport errors and 5xx are "unreachable" (503); a refusal by the evidence (4xx other than 404) or a body that is not JSON is a 502, so that a
# ---- misconfigured identity (403) is not reported as a network problem and not retried by the driver as one.
import httpx  # noqa: E402


def _evidence_answers(monkeypatch, status, content=b'{"id": 1}'):
    def get(url, **kw):
        return httpx.Response(status, content=content, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", get)


def test_e6_evidence_5xx_is_503(make_cluster, monkeypatch):
    c = make_cluster(n_sites=N)
    c.seed()
    _evidence_answers(monkeypatch, 500, b"boom")
    assert _post(c, "query").status_code == 503


def test_e7_evidence_4xx_is_502_not_503(make_cluster, monkeypatch):
    c = make_cluster(n_sites=N)
    c.seed()
    for status in (400, 401, 403, 429):
        _evidence_answers(monkeypatch, status, b"nope")
        r = _post(c, "query")
        assert r.status_code == 502, (status, r.status_code)
    assert _rows(c) == []


def test_e8_non_json_200_is_502(make_cluster, monkeypatch):
    c = make_cluster(n_sites=N)
    c.seed()
    _evidence_answers(monkeypatch, 200, b"<html>not json</html>")
    assert _post(c, "query").status_code == 502


def test_e9_404_unchanged(make_cluster, monkeypatch):
    c = make_cluster(n_sites=N)
    c.seed()
    _evidence_answers(monkeypatch, 404, b"{}")
    r = _post(c, "query")
    assert r.status_code == 200 and r.json() == {"applied": False}
