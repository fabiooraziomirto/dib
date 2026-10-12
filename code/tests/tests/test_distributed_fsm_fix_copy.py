"""Candidate correction of the FSM races, applied to a COPY of service.py (audit 67 sez. 7).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-12, notte).
service.py NON e' modificato (congelato per hash): la correzione e' una sostituzione di testo su una
copia in tmp_path (``make_source_copy``), come i controlli negativi. Traduce nel codice la correzione
verificata nel modello experiments_tnsm/tla_fsm/v2/DIB_AE_NA.tla (FixRace + FixQuery) e la regola
a10 decisa dall'utente:
  FQ  /query: prima lettura solo per lo score_id (immutabile), poi RISERVA una riga 'staging' (non
      esportabile: /export_mud seleziona solo 'active'), poi seconda lettura, poi chiusura:
      staging -> monitor-only se la seconda lettura e' Active, altrimenti la riga e' cancellata; se un
      fan-out ha gia' spostato la riga, la si lascia com'e'.
  FC  /commit in due fasi: monitor-only -> 'committing' solo se last_applied_seq <= seq letto; seconda
      lettura; promozione ad active solo se lo stato e' ancora 'committing', l'evidence e' Active e il
      seq e' invariato; altrimenti torna monitor-only e risponde 409.
  FR  /local_restore: 409 se last_applied_seq > seq letto (un evento piu' nuovo e' arrivato).
  FV  /local_revoke risolve il fatto dalla riga locale (device_type, endpoint, protocol, port), senza
      chiamare l'evidence (b4).
  FQ2 quorum 2: la conferma richiede un segnalante fuori da suspension_reports (a10).

Ipotesi
H-F1  Sulla copia corretta valgono le ipotesi ORIGINALI dei test rossi di
      test_distributed_fsm_races.py: H-b3q-1, H-b3c-1, H-b3r-1, H-b4-1, H-a10.
      Falsificata se una di esse fallisce sulla copia.
H-F2  H-b3r-2 era formulata male (audit 64, nota): dopo la corsa il record deve restare
      revoked/local (veto), non disputed. Sulla copia: revoked/local prima e dopo /reconcile.
H-F3  Sulla copia valgono anche tutte le ipotesi verdi di quel file (H-b3q-2, H-b3c-2, H-b3c-3,
      H-b3r-3, H-b4-2, H-b4-3, H-b6-1, H-b6-2), riformulate dove la correzione cambia la risposta
      attesa (indicato nel test).
H-F4  Senza corsa la copia si comporta come l'originale sul ciclo base: stage, commit (200, active, 1
      ACE), dispute (disputed, 0 ACE), restore (monitor-only), nuovo commit (active).
H-F5  (aggiunta 2026-10-12 dopo il modello v5, prima di rieseguire) con la riserva presa sotto
      _reconcile_lock (come QueryReserve con rc idle nel modello v5) tutti i test di questo file
      restano verdi.
Falsificazione complessiva: un qualunque test di questo file rosso.
"""
from __future__ import annotations

import httpx
import pytest

from _dist_harness import make_cluster, make_source_copy  # noqa: F401  (fixture)

N3 = 3

FQ = (
    '''        score = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        if score is None or not score["accepted"] or score["status"] != STATUS_ACTIVE:
            return {"applied": False}

        def txn(con):
            existing = con.execute("SELECT 1 FROM local_decisions WHERE score_id=?", (score["id"],)).fetchone()
            if existing is not None:
                return
            con.execute(
                "INSERT INTO local_decisions"
                " (score_id, state, origin, last_applied_seq, device_type, endpoint, protocol, port)"
                " VALUES (?, ?, NULL, ?, ?, ?, ?, ?)",
                (score["id"], DECISION_MONITOR_ONLY, score["fanout_seq"],
                 req.device_type, req.endpoint, req.protocol, req.port),
            )

        _site_db.run(txn)
        return {"applied": True, "score_id": score["id"]}''',
    '''        score = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        if score is None or not score["accepted"] or score["status"] != STATUS_ACTIVE:
            return {"applied": False}
        sid = score["id"]

        def reserve(con):
            if con.execute("SELECT 1 FROM local_decisions WHERE score_id=?", (sid,)).fetchone() is not None:
                return False
            con.execute(
                "INSERT INTO local_decisions"
                " (score_id, state, origin, last_applied_seq, device_type, endpoint, protocol, port)"
                " VALUES (?, 'staging', NULL, 0, ?, ?, ?, ?)",
                (sid, req.device_type, req.endpoint, req.protocol, req.port),
            )
            return True

        with _reconcile_lock:  # v5: no reservation between a reconcile apply and its ack
            reserved = _site_db.run(reserve)
        if not reserved:
            return {"applied": True, "score_id": sid}
        try:
            again = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        except Exception:
            _site_db.run(lambda con: con.execute(
                "DELETE FROM local_decisions WHERE score_id=? AND state='staging'", (sid,)))
            raise
        ok = again is not None and again["accepted"] and again["status"] == STATUS_ACTIVE

        def finish(con):
            row = con.execute(
                "SELECT state, last_applied_seq FROM local_decisions WHERE score_id=?", (sid,)).fetchone()
            if row is None or row[0] != "staging":
                return
            if ok:
                con.execute("UPDATE local_decisions SET state=?, last_applied_seq=? WHERE score_id=?",
                            (DECISION_MONITOR_ONLY, max(row[1], again["fanout_seq"]), sid))
            else:
                con.execute("DELETE FROM local_decisions WHERE score_id=?", (sid,))

        _site_db.run(finish)
        return {"applied": ok, "score_id": sid}''',
)

FC = (
    '''        def txn(con):
            row = con.execute("SELECT state FROM local_decisions WHERE score_id=?", (score["id"],)).fetchone()
            if row is None or row[0] != DECISION_MONITOR_ONLY:
                raise HTTPException(409, f"cannot commit: state is {row[0] if row else None!r}")
            con.execute("UPDATE local_decisions SET state=? WHERE score_id=?", (DECISION_ACTIVE, score["id"]))

        _site_db.run(txn)
        return {"applied": True}''',
    '''        sid, seq0 = score["id"], score["fanout_seq"]

        def phase1(con):
            row = con.execute(
                "SELECT state, last_applied_seq FROM local_decisions WHERE score_id=?", (sid,)).fetchone()
            if row is None or row[0] != DECISION_MONITOR_ONLY or row[1] > seq0:
                raise HTTPException(409, f"cannot commit: state is {row[0] if row else None!r}")
            con.execute("UPDATE local_decisions SET state='committing' WHERE score_id=?", (sid,))

        _site_db.run(phase1)
        try:
            again = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        except Exception:
            again = None
        promote = (again is not None and again["accepted"] and again["status"] == STATUS_ACTIVE
                   and again["fanout_seq"] == seq0)

        def phase2(con):
            row = con.execute("SELECT state FROM local_decisions WHERE score_id=?", (sid,)).fetchone()
            if row is None or row[0] != "committing":
                return False
            con.execute("UPDATE local_decisions SET state=? WHERE score_id=?",
                        (DECISION_ACTIVE if promote else DECISION_MONITOR_ONLY, sid))
            return promote

        if not _site_db.run(phase2):
            raise HTTPException(409, "the evidence changed during the commit")
        return {"applied": True}''',
)

FR = (
    '''            row = con.execute("SELECT state, origin FROM local_decisions WHERE score_id=?", (score["id"],)).fetchone()
            if row is None or row[0] != DECISION_REVOKED or row[1] != ORIGIN_LOCAL:
                raise HTTPException(409, "not locally revoked")''',
    '''            row = con.execute("SELECT state, origin, last_applied_seq FROM local_decisions WHERE score_id=?",
                              (score["id"],)).fetchone()
            if row is None or row[0] != DECISION_REVOKED or row[1] != ORIGIN_LOCAL:
                raise HTTPException(409, "not locally revoked")
            if row[2] > score["fanout_seq"]:
                raise HTTPException(409, "a newer lifecycle event arrived during the local restore")''',
)

FV = (
    '''        score = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        if score is None:
            raise HTTPException(404, "unknown fact")

        def txn(con):
            row = con.execute("SELECT state, origin FROM local_decisions WHERE score_id=?", (score["id"],)).fetchone()
            if row is None or not (
                row[0] in (DECISION_MONITOR_ONLY, DECISION_ACTIVE, DECISION_DISPUTED)''',
    '''        def txn(con):
            found = con.execute(
                "SELECT state, origin, score_id FROM local_decisions"
                " WHERE device_type=? AND endpoint=? AND protocol=? AND port=?",
                (req.device_type, req.endpoint, req.protocol, req.port)).fetchone()
            row = found[:2] if found else None
            score = {"id": found[2]} if found else None
            if row is None or not (
                row[0] in (DECISION_MONITOR_ONLY, DECISION_ACTIVE, DECISION_DISPUTED, "committing")''',
)

FQ2 = (
    '''            if status == STATUS_DISPUTED and req.site_id != disputed_by:''',
    '''            if status == STATUS_DISPUTED and req.site_id != disputed_by and (
                SUSPENSION_QUORUM == 1 or con.execute(
                    "SELECT 1 FROM suspension_reports WHERE score_id=? AND site_id=?",
                    (score_id, req.site_id)).fetchone() is None):''',
)

FIXES = [FQ, FC, FR, FV, FQ2]


@pytest.fixture
def fixed(tmp_path):
    return make_source_copy(tmp_path, FIXES, name="service_fixed.py")


def _setup(c, sites=(0,), commit=True) -> int:
    sid = c.seed()
    for i in sites:
        assert c.stage(i).json()["applied"] is True
        if commit:
            assert c.commit(i).status_code == 200
    return sid


def test_f4_base_cycle_unchanged(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, source=fixed)
    sid = _setup(c, sites=(0, 1))
    assert c.state(0, sid)["state"] == "active" and c.ace_count(0) == 1
    assert c.dispute("site-1").json() == {"applied": True}
    assert c.state(0, sid)["state"] == "disputed" and c.ace_count(0) == 0
    assert c.restore().status_code == 200
    assert c.state(0, sid)["state"] == "monitor-only" and c.ace_count(0) == 0
    assert c.commit(0).status_code == 200
    assert c.state(0, sid)["state"] == "active" and c.ace_count(0) == 1


# ---- H-F1 / H-F2 / H-F3: the scenarios of test_distributed_fsm_races.py on the corrected copy
def test_f1_b3q_query_race_stages_nothing_during_the_episode(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, source=fixed)
    sid = c.seed()
    c.net.after("GET", "/scores", lambda: c.dispute("site-1"))
    c.stage(0)
    assert c.evidence_score()["status"] == "disputed"
    st = c.state(0, sid)
    assert st is None or st["state"] == "disputed", st          # H-b3q-1
    assert c.commit(0).status_code == 409
    assert c.ace_count(0) == 0


def test_f1_b3q_dispute_after_reservation_is_applied(make_cluster, fixed) -> None:
    """The dispute lands between the reservation and the second read: the fan-out finds the
    staging row and applies, the finish leaves the row as the fan-out set it."""
    c = make_cluster(n_sites=N3, source=fixed)
    sid = c.seed()
    # the dispute is injected right after the local reservation transaction, before the second GET
    original_run = c.site_mods[0]._site_db.run
    state = {"done": False}

    def run_and_dispute(fn):
        out = original_run(fn)
        if not state["done"] and getattr(fn, "__name__", "") == "reserve":
            state["done"] = True
            c.dispute("site-1")
        return out

    c.site_mods[0]._site_db.run = run_and_dispute
    c.stage(0)
    c.site_mods[0]._site_db.run = original_run
    st = c.state(0, sid)
    assert st is not None and st["state"] == "disputed" and st["last_applied_seq"] == 1, st
    assert c.ace_count(0) == 0


def test_f1_b3c_commit_race_with_lost_fanout_creates_no_active(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, source=fixed)
    sid = _setup(c, sites=(0,), commit=False)

    def dispute_meanwhile():
        c.net.down.add(0)
        c.dispute("site-1")
        c.net.down.discard(0)

    c.net.after("GET", "/scores", dispute_meanwhile)
    r = c.commit(0)
    assert r.status_code == 409                                    # H-F3: the commit is refused
    assert c.state(0, sid)["state"] != "active"                    # H-b3c-1
    assert c.ace_count(0) == 0
    assert c.reconcile(0).status_code == 200                       # H-b3c-2
    assert c.state(0, sid)["state"] == "disputed"


def test_f3_b3c_commit_racing_delivered_dispute_is_refused(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, source=fixed)
    sid = _setup(c, sites=(0,), commit=False)
    c.net.after("GET", "/scores", lambda: c.dispute("site-1"))
    assert c.commit(0).status_code == 409                          # H-b3c-3
    assert c.state(0, sid)["state"] == "disputed"
    assert c.ace_count(0) == 0


def test_f1_f2_b3r_local_restore_race_is_refused_and_keeps_the_veto(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, source=fixed)
    sid = _setup(c, sites=(0,))
    assert c.local_revoke(0).status_code == 200
    c.net.after("GET", "/scores", lambda: c.dispute("site-1"))
    r = c.local_restore(0)
    assert r.status_code == 409                                    # H-b3r-1
    st = c.state(0, sid)
    assert (st["state"], st["origin"]) == ("revoked", "local")
    assert c.reconcile(0).status_code == 200                       # H-F2 (corrected H-b3r-2)
    st = c.state(0, sid)
    assert (st["state"], st["origin"]) == ("revoked", "local")
    assert c.commit(0).status_code == 409 and c.ace_count(0) == 0  # H-b3r-3


def test_f1_b4_local_revoke_works_with_evidence_down(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, source=fixed)
    sid = _setup(c, sites=(0,))
    c.net.evidence_down = True
    assert c.local_revoke(0).status_code == 200                    # H-b4-1
    st = c.state(0, sid)
    assert (st["state"], st["origin"]) == ("revoked", "local")
    assert c.ace_count(0) == 0                                     # H-b4-3 (export is local)


def test_f3_b4_local_restore_with_evidence_down_is_not_applied(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, source=fixed)
    sid = _setup(c, sites=(0,))
    assert c.local_revoke(0).status_code == 200
    c.net.evidence_down = True
    try:
        status = c.local_restore(0).status_code
    except httpx.HTTPError:
        status = None
    assert status != 200                                           # H-b4-2
    st = c.state(0, sid)
    assert (st["state"], st["origin"]) == ("revoked", "local")


def test_f3_b6_quorum2_single_vote_persists(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, quorum=2, source=fixed)
    sid = _setup(c, sites=(0, 1, 2))
    assert c.dispute("site-1").json() == {"applied": False}
    assert c.restore().status_code == 409
    assert c.dispute("site-2").json() == {"applied": True}         # H-b6-2
    assert c.state(0, sid)["state"] == "disputed"


def test_f1_a10_quorum2_confirmation_needs_an_outsider(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, quorum=2, source=fixed)
    sid = _setup(c, sites=(0, 1, 2))
    assert c.dispute("site-0").json() == {"applied": False}
    assert c.dispute("site-1").json() == {"applied": True}
    assert c.dispute("site-0").json() == {"applied": False}        # H-a10
    assert c.evidence_score()["status"] == "disputed"
    assert c.dispute("site-2").json() == {"applied": True}
    assert c.evidence_score()["status"] == "revoked"
    assert c.state(0, sid)["state"] == "revoked"


def test_f1_a10_quorum1_unchanged(make_cluster, fixed) -> None:
    c = make_cluster(n_sites=N3, quorum=1, source=fixed)
    _setup(c, sites=(0,))
    assert c.dispute("site-0").json() == {"applied": True}
    assert c.dispute("site-1").json() == {"applied": True}
    assert c.evidence_score()["status"] == "revoked"
