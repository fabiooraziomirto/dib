"""D1 and D2 of docs/audit/90 sez. 3 (written BEFORE the change; falsified by any failing assertion).
D1  site startup cleans the transient rows a crash can leave: a `staging` row (reserved by /query, never closed) is DELETED, a `committing` row (phase 1 of /commit, never finished) goes back to
    `monitor-only` keeping last_applied_seq and origin; every other state (monitor-only, active, disputed, revoked, with or without origin local) is left untouched. The two actions mirror the
    abort paths of the verified model (a query that cannot confirm Active deletes its reservation; a commit that cannot promote returns to monitor-only). After the cleanup a new /query and
    /commit of the fact work (200, active).
  D1-1 staging deleted; D1-2 committing -> monitor-only with seq kept; D1-3 other states untouched; D1-4 /query + /commit work after the cleanup; D1-5 the evidence role does nothing (no site.db).
D2  /query takes the reconcile lock with a timeout (DIB_DIST_RECONCILE_LOCK_TIMEOUT, default 60 s like /reconcile) and answers 503 instead of waiting forever; no staging row is left behind.
  D2-1 with the lock held elsewhere and the timeout 0.2 s the answer is 503 within 5 s and the fact has no local row; D2-2 after the lock is released the same /query works;
  D2-3 the default timeout is the one of /reconcile (RECONCILE_LOCK_TIMEOUT == 60.0 in the module); D2-4 /reconcile keeps its own 503 behaviour.
"""
import time

from _dist_harness import make_cluster  # noqa: F401

N = 2


def _rows(c, site=0):
    return c.site_mods[site]._site_db.run(lambda con: con.execute("SELECT score_id, state, origin, last_applied_seq FROM local_decisions ORDER BY score_id").fetchall())


def _insert(c, sid, state, origin=None, seq=0, site=0, ep="x.example"):
    c.site_mods[site]._site_db.run(lambda con: con.execute(
        "INSERT OR REPLACE INTO local_decisions (score_id, state, origin, last_applied_seq, device_type, endpoint, protocol, port) VALUES (?,?,?,?,?,?,?,?)",
        (sid, state, origin, seq, "camera", ep, "https", 443)))


def _restart_site(c, site=0):
    c.site_mods[site]._site_db.close() if hasattr(c.site_mods[site]._site_db, "close") else None
    mod, client = c._load("site", site, c.n_sites, 1)
    c.site_mods[site], c.sites[site] = mod, client
    c.net.clients[f"site{site}.test"] = client


def test_d1_1_and_2_transients_cleaned(make_cluster):
    c = make_cluster(n_sites=N)
    sid = c.seed()
    assert c.stage(0).json()["applied"] is True and c.commit(0).status_code == 200
    _insert(c, 900, "staging", seq=0, ep="stg.example")
    _insert(c, 901, "committing", origin=None, seq=5, ep="cmt.example")
    _restart_site(c)
    rows = {r[0]: r for r in _rows(c)}
    assert 900 not in rows
    assert rows[901][1:] == ("monitor-only", None, 5)
    assert rows[sid][1] == "active"


def test_d1_3_other_states_untouched(make_cluster):
    c = make_cluster(n_sites=N)
    for sid, st, org in ((910, "monitor-only", None), (911, "active", None), (912, "disputed", None), (913, "revoked", "local"), (914, "revoked", None)):
        _insert(c, sid, st, org, seq=3, ep=f"o{sid}.example")
    before = _rows(c)
    _restart_site(c)
    assert _rows(c) == before


def test_d1_4_fact_works_after_cleanup(make_cluster):
    c = make_cluster(n_sites=N)
    sid = c.seed()
    _insert(c, sid, "staging", seq=0, ep="x.example")   # the seeded fact's reservation left by a crash
    c.site_mods[0]._site_db.run(lambda con: con.execute("UPDATE local_decisions SET endpoint=(SELECT endpoint FROM local_decisions WHERE score_id=?) WHERE score_id=?", (sid, sid)))
    _restart_site(c)
    assert c.state(0, sid) is None
    assert c.stage(0).json()["applied"] is True and c.commit(0).status_code == 200
    assert c.state(0, sid)["state"] == "active"


def test_d1_5_evidence_role_untouched(make_cluster):
    c = make_cluster(n_sites=N)
    assert not hasattr(c.evidence_mod, "_site_db")


def test_d2_1_query_503_when_the_lock_is_held(make_cluster):
    c = make_cluster(n_sites=N, env={"DIB_DIST_RECONCILE_LOCK_TIMEOUT": "0.2"})
    sid = c.seed()
    lock = c.site_mods[0]._reconcile_lock
    lock.acquire()
    try:
        t = time.time()
        r = c.stage(0)
        assert r.status_code == 503 and time.time() - t < 5.0
        assert c.state(0, sid) is None
        assert _rows(c) == []
    finally:
        lock.release()
    assert c.stage(0).json()["applied"] is True        # D2-2
    assert c.commit(0).status_code == 200


def test_d2_3_default_timeout_is_the_reconcile_one(make_cluster):
    c = make_cluster(n_sites=N)
    assert c.site_mods[0].RECONCILE_LOCK_TIMEOUT == 60.0


def test_d2_4_reconcile_keeps_its_503(make_cluster):
    c = make_cluster(n_sites=N, env={"DIB_DIST_RECONCILE_LOCK_TIMEOUT": "0.2"})
    lock = c.site_mods[0]._reconcile_lock
    lock.acquire()
    try:
        assert c.reconcile(0).status_code == 503
    finally:
        lock.release()
