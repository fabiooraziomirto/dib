"""Step 2 of the mTLS design (audit 13 sez. 3.3, sez. 6): authorization by certificate
identity in service.py, end to end over real TLS sockets on loopback.

One evidence and two site processes (``python -m dib.registry.distributed.mtls``, i.e.
uvicorn with PeerCertH11Protocol) run with DIB_DIST_MTLS=1 and DIB_DIST_TYPE_LIST=1, a
test CA (OpenSSL) and one server-side identity mapping. Each service presents its own
certificate on its outgoing calls (site -> evidence as ``member``, evidence -> site as
``evidence``). The test client presents operator, member, admin, unmapped and revoked
identities.

Hypotheses (stated before running, tests written before the service.py change):
  A1 (T1)  a mapped identity reaches the endpoints its role allows; the dispute fan-out
           and the site -> evidence reads work over mTLS (states change at both sites).
  A2 (T6)  a valid certificate whose SAN is not mapped gets 403.
  A3 (T5)  adding a SAN to the denylist revokes it on the next request (403), no restart.
  A4 (T7)  site-1's operator cannot query/commit/local_revoke/local_restore/reconcile on
           site-0 (403) and site-0's state is unchanged.
  A5 (T8)  only consortium_admin can /restore and /seed; a member or operator gets 403.
  A6 (T9)  a member disputing with a payload site_id of another site gets 403; nothing
           changes at the evidence.
  A7 (T10) the reporter is the certificate's site: a second dispute from the same SAN
           does not confirm; a dispute from another site's SAN does (revoked).
  A8 (T11) a member can read and ack only its own outbox (/pending/<own site>).
  A9 (T12) only the evidence identity can call /apply_fanout on a site.
  A10 (T14) a stolen site SERVICE certificate (member) can dispute as that site, but
           cannot create local authorization: /commit needs the site's operator.
  A11 (Q5) with DIB_DIST_TYPE_LIST=1, a member may attest/dispute only facts of device
           types listed for it in the mapping (403 otherwise).
Falsification: any assertion below failing.
"""
from __future__ import annotations

import pytest

from _mtls_ca import requires_openssl, san_site

pytestmark = requires_openssl

from _mtls_cluster import FACT, SRC, cl  # noqa: F401  (cl is a fixture)

_n = iter(range(10_000))


def _seed(cl, device_type="camera") -> dict:
    fact = {**FACT, "device_type": device_type, "endpoint": f"api{next(_n)}.vendor.test"}
    with cl.client("admin") as admin:
        r = admin.post(f"{cl.url['evidence']}/seed", json=fact)
        assert r.status_code == 200, r.text
        fact_id = r.json()["id"]
    return {**fact, "_id": fact_id}


def _body(fact: dict) -> dict:
    return {k: v for k, v in fact.items() if not k.startswith("_")}


def _state(cl, site: int, fact: dict):
    with cl.client(f"op{site}") as op:
        r = op.get(f"{cl.url[site]}/state/{fact['_id']}")
    return None if r.status_code == 404 else r.json()["state"]


def _stage_commit(cl, site: int, fact: dict) -> None:
    with cl.client(f"op{site}") as op:
        assert op.post(f"{cl.url[site]}/query", json=_body(fact)).json()["applied"] is True
        assert op.post(f"{cl.url[site]}/commit", json=_body(fact)).status_code == 200


def test_a1_valid_flow_and_fanout_over_mtls(cl):
    fact = _seed(cl)
    for site in (0, 1):
        _stage_commit(cl, site, fact)
        assert _state(cl, site, fact) == "active"
    with cl.client("member0") as m0:
        r = m0.post(f"{cl.url['evidence']}/dispute", json=_body(fact))
    assert r.status_code == 200 and r.json()["applied"] is True
    assert _state(cl, 0, fact) == "disputed" and _state(cl, 1, fact) == "disputed"


def test_a2_unmapped_san_forbidden(cl):
    with cl.client("unmapped") as c:
        r = c.get(f"{cl.url['evidence']}/scores", params={**FACT, "endpoint": "x"})
    assert r.status_code == 403


def test_a3_denylist_revokes_without_restart(cl):
    fact = _seed(cl)
    params = _body(fact)
    with cl.client("member9") as c:
        assert c.get(f"{cl.url['evidence']}/scores", params=params).status_code == 200
        cl.set_denylist([san_site("site-9")])
        try:
            assert c.get(f"{cl.url['evidence']}/scores", params=params).status_code == 403
        finally:
            cl.set_denylist(())


@pytest.mark.parametrize("path", ["/query", "/commit", "/local_revoke", "/local_restore", "/reconcile"])
def test_a4_other_sites_operator_forbidden(cl, path):
    fact = _seed(cl)
    _stage_commit(cl, 0, fact)
    with cl.client("op1") as op1:
        r = op1.post(f"{cl.url[0]}{path}", json=_body(fact))
    assert r.status_code == 403
    assert _state(cl, 0, fact) == "active"


@pytest.mark.parametrize("who", ["member0", "op0"])
def test_a5_restore_and_seed_admin_only(cl, who):
    fact = _seed(cl)
    with cl.client("member0") as m0:
        assert m0.post(f"{cl.url['evidence']}/dispute", json=_body(fact)).json()["applied"] is True
    with cl.client(who) as c:
        assert c.post(f"{cl.url['evidence']}/restore", json=_body(fact)).status_code == 403
        assert c.post(f"{cl.url['evidence']}/seed", json={**_body(fact), "endpoint": "new.test"}).status_code == 403
    with cl.client("admin") as admin:
        assert admin.post(f"{cl.url['evidence']}/restore", json=_body(fact)).status_code == 200


def test_a6_payload_site_id_of_another_site_forbidden(cl):
    fact = _seed(cl)
    with cl.client("member0") as m0:
        r = m0.post(f"{cl.url['evidence']}/dispute", json={**_body(fact), "site_id": "site-1"})
        assert r.status_code == 403
        score = m0.get(f"{cl.url['evidence']}/scores", params=_body(fact)).json()
    assert score["status"] == "active" and score["fanout_seq"] == 0


def test_a7_reporter_is_the_certificate_site(cl):
    fact = _seed(cl)
    url = f"{cl.url['evidence']}/dispute"
    with cl.client("member0") as m0, cl.client("member1") as m1:
        assert m0.post(url, json=_body(fact)).json()["applied"] is True
        assert m0.post(url, json={**_body(fact), "site_id": "site-0"}).json()["applied"] is False
        assert m0.get(f"{cl.url['evidence']}/scores", params=_body(fact)).json()["status"] == "disputed"
        assert m1.post(url, json=_body(fact)).json()["applied"] is True
        score = m1.get(f"{cl.url['evidence']}/scores", params=_body(fact)).json()
    assert score["status"] == "revoked" and score["disputed_by"] == "site-0"


def test_a8_own_outbox_only(cl):
    with cl.client("member0") as m0:
        assert m0.get(f"{cl.url['evidence']}/pending/site-0").status_code == 200
        assert m0.get(f"{cl.url['evidence']}/pending/site-1").status_code == 403
        assert m0.post(f"{cl.url['evidence']}/pending/site-1/ack", json={"applied": []}).status_code == 403


def test_a9_apply_fanout_evidence_only(cl):
    fact = _seed(cl)
    _stage_commit(cl, 0, fact)
    body = {"score_id": fact["_id"], "seq": 99, "event_type": "revoke", "target_state": "revoked"}
    for who in ("member1", "op0", "admin"):
        with cl.client(who) as c:
            assert c.post(f"{cl.url[0]}/apply_fanout", json=body).status_code == 403, who
    assert _state(cl, 0, fact) == "active"


def test_a10_stolen_service_certificate_cannot_authorize(cl):
    fact = _seed(cl)
    with cl.client("op0") as op0:
        assert op0.post(f"{cl.url[0]}/query", json=_body(fact)).json()["applied"] is True
    with cl.client("member0") as stolen:
        assert stolen.post(f"{cl.url[0]}/commit", json=_body(fact)).status_code == 403
        assert stolen.post(f"{cl.url[1]}/commit", json=_body(fact)).status_code == 403
        # what the stolen certificate CAN do, by design: dispute as site-0 (availability)
        assert stolen.post(f"{cl.url['evidence']}/dispute", json=_body(fact)).json()["applied"] is True
    assert _state(cl, 0, fact) == "disputed"


def test_a11_type_list_limits_attest_and_dispute(cl):
    plug = _seed(cl, device_type="plug")
    with cl.client("member0") as m0:  # site-0 declares only "camera"
        assert m0.post(f"{cl.url['evidence']}/attest", json=_body(plug)).status_code == 403
        assert m0.post(f"{cl.url['evidence']}/dispute", json=_body(plug)).status_code == 403
    with cl.client("member1") as m1:  # site-1 declares "plug"
        assert m1.post(f"{cl.url['evidence']}/attest", json=_body(plug)).status_code == 200
        assert m1.post(f"{cl.url['evidence']}/dispute", json=_body(plug)).json()["applied"] is True


def test_type_list_requires_mtls(tmp_path, monkeypatch):
    """A11 guard (added with the code, not before): the type list without verified
    identities would trust the payload site_id, so the service refuses to start."""
    import importlib.util

    source = SRC / "dib" / "registry" / "distributed" / "service.py"
    monkeypatch.setenv("DIB_DIST_ROLE", "evidence")
    monkeypatch.setenv("DIB_DIST_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DIB_DIST_MTLS", "0")
    monkeypatch.setenv("DIB_DIST_TYPE_LIST", "1")
    spec = importlib.util.spec_from_file_location("dib_dist_typelist_guard", source)
    module = importlib.util.module_from_spec(spec)
    with pytest.raises(ValueError, match="DIB_DIST_TYPE_LIST=1 requires DIB_DIST_MTLS=1"):
        spec.loader.exec_module(module)
