"""Race, evidence-down and multi-site tests of the lifecycle FSM (audit 61 obiettivo 2, spec audit 63).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-12).
Nessun codice di produzione e' modificato. Infrastruttura: _dist_harness.py (rete finta, nessun
socket). S = code/src/dib/registry/distributed/service.py a 6e6d352
(sha256 0501b383043a44d4be2f9e0ac2dd9ce2db6ae585b04838a0f54bb1fba3d42a64). Le righe sono quelle
di docs/audit/63_fsm_specifica.md. Il harness fissa DIB_DIST_FANOUT_CONCURRENCY=1.

Tecnica per le finestre fra lettura dell'evidence e transazione locale (audit 63 D7): l'hook
one-shot ``net.after("GET", "/scores", fn)`` esegue ``fn`` dopo che l'evidence ha risposto alla
lettura del sito e prima che il sito apra la sua transazione (S:500->516, S:522->532,
S:560-564->575). Deterministico: nessun thread, nessun sleep.

Ipotesi (attesa; "ROSSO previsto" = ritengo che il codice attuale la falsifichi)
H-b3q-1  /query con una dispute committata fra lettura e INSERT non lascia un record
         monitor-only durante l'episodio: lo stato locale e' assente o disputed (precondizione
         "no open dispute" di main_wip.tex:320). Falsificata se lo stato e' monitor-only.
         ROSSO previsto: il fan-out trova la riga assente (S:476-478) e l'INSERT usa il seq letto
         prima (S:512).
H-b3q-2  Una /reconcile dopo la stessa corsa porta il record a disputed con last_applied_seq
         uguale al fanout_seq dell'evidence; /commit resta 409 e non ci sono ACE. Falsificata da
         uno qualunque dei tre. Verde previsto (anti-entropia, S:584-601).
H-b3c-1  /commit con una dispute committata fra lettura e transazione, il cui fan-out verso il
         sito fallisce (sito irraggiungibile solo per l'evidence), non crea un record active.
         Falsificata se lo stato dopo il commit e' active o se il sito esporta l'ACE.
         ROSSO previsto: la transazione controlla solo lo stato locale (S:528).
H-b3c-2  Dopo la stessa corsa, una /reconcile porta il record a disputed e a 0 ACE (I3 "upon
         reconciliation", main_wip.tex:340). Verde previsto.
H-b3c-3  Se invece il fan-out arriva prima della transazione, /commit risponde 409 e lo stato
         e' disputed. Verde previsto (S:528-529).
H-b3r-1  /local_restore con una dispute committata fra il controllo S:563 e la transazione non
         esce dal veto durante l'episodio: risposta 409 e stato revoked/local
         (main_wip.tex:326, :334 "Local restore remains blocked while a shared dispute is
         open"). ROSSO previsto: il fan-out avanza solo last_applied_seq (S:487-490), poi la
         transazione scrive monitor-only (S:570-573).
H-b3r-2  Dopo la stessa corsa, una /reconcile porta il record a disputed (stato dell'episodio).
         ROSSO previsto: il seq e' gia' allineato, l'anti-entropia salta il fatto (S:593).
H-b3r-3  Dopo la stessa corsa, /commit e' 409 e non ci sono ACE (nessuna violazione di
         export). Verde previsto (S:522-524).
H-b4-1   Con l'evidence irraggiungibile dal sito, /local_revoke su un record active riesce
         (200, stato revoked/local, 0 ACE): il veto locale non dipende dalla rete (modello
         DIB_AE.tla:264-271 senza lettura dell'evidence; main_wip.tex:547). Falsificata da un
         errore o da una risposta diversa da 200. ROSSO previsto: S:538 chiama
         _evidence_get_score senza try (S:461-470).
H-b4-2   Con l'evidence irraggiungibile, /local_restore NON si applica (fail-closed: senza
         evidence il sito non sa se l'episodio e' aperto); lo stato resta revoked/local.
         Verde previsto.
H-b4-3   Con l'evidence irraggiungibile, /export_mud continua a esportare gli active (export
         solo locale, S:682-709). Verde previsto.
H-b6-1   3 siti, tutti active. Dispute (seq 1). Il fan-out del restore (seq 2) verso site-2 e'
         parcheggiato (Gate); mentre e' fermo, una nuova dispute (seq 3) parte in un altro
         thread e anche il suo fan-out verso site-2 si ferma; poi il Gate si apre (ordine di
         consegna non controllato). Stato finale: ogni sito disputed con last_applied_seq = 3
         = fanout_seq, nessun ACE, outbox vuota. Falsificata da uno qualunque. Verde previsto
         (guardia seq S:480-481). Se il harness non regge due richieste concorrenti, lo riporto
         come limite del test, non del servizio.
H-b6-2   (characterization) Quorum 2, 3 siti: un voto isolato non sospende, il restore e'
         rifiutato (409, stato active, S:937-938) e il voto resta: una seconda segnalazione da
         un altro sito, anche molto dopo, sospende (i voti non scadono, S:908-911).
H-a10    (decisione dell'utente, 2026-10-12) Quorum 2, 3 siti: dopo la sospensione da site-0 e
         site-1, una nuova segnalazione di site-0 NON revoca (resta disputed, applied False);
         una segnalazione di site-2 revoca. ROSSO previsto: S:918 confronta solo con
         disputed_by (= site-1, S:914-915). test_distributed_service_inproc.py:108-122 resta
         invariato (caratterizzazione del comportamento attuale).

Regola (Fase 2): un'ipotesi falsificata resta con la sua asserzione originale, marcata
xfail(strict=True) DOPO l'esecuzione, con un test separato che fissa il comportamento osservato.
"""
from __future__ import annotations

import threading
import time

import httpx

from _dist_harness import make_cluster  # noqa: F401  (pytest fixture)

N3 = 3


def _setup(c, sites=(0,), commit=True) -> int:
    sid = c.seed()
    for i in sites:
        assert c.stage(i).json()["applied"] is True
        if commit:
            assert c.commit(i).status_code == 200
    return sid


# --------------------------------------------------------------------------- b3: /query
def _query_race(c):
    sid = c.seed()
    c.net.after("GET", "/scores", lambda: c.dispute("site-1"))
    r = c.stage(0)
    assert c.evidence_score()["status"] == "disputed"  # the injected dispute did happen
    return sid, r


def test_b3q_1_query_racing_dispute_does_not_stage_during_open_episode(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid, _r = _query_race(c)
    st = c.state(0, sid)
    assert st is None or st["state"] == "disputed", st


def test_b3q_2_reconcile_repairs_query_race(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid, _r = _query_race(c)
    assert c.reconcile(0).status_code == 200
    st = c.state(0, sid)
    assert st is not None and st["state"] == "disputed", st
    assert st["last_applied_seq"] == c.evidence_score()["fanout_seq"]
    assert c.commit(0).status_code == 409
    assert c.ace_count(0) == 0


# --------------------------------------------------------------------------- b3: /commit
def _commit_race(c, lose_fanout: bool):
    sid = _setup(c, sites=(0,), commit=False)

    def dispute_meanwhile():
        if lose_fanout:
            c.net.down.add(0)  # the evidence cannot reach site-0; site-0 still serves its operator
        c.dispute("site-1")
        c.net.down.discard(0)

    c.net.after("GET", "/scores", dispute_meanwhile)
    r = c.commit(0)
    assert c.evidence_score()["status"] == "disputed"
    return sid, r


def test_b3c_1_commit_racing_dispute_with_lost_fanout_creates_no_active(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid, _r = _commit_race(c, lose_fanout=True)
    assert c.state(0, sid)["state"] != "active"
    assert c.ace_count(0) == 0


def test_b3c_2_reconcile_withdraws_the_raced_commit(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid, _r = _commit_race(c, lose_fanout=True)
    assert c.reconcile(0).status_code == 200
    assert c.state(0, sid)["state"] == "disputed"
    assert c.ace_count(0) == 0


def test_b3c_3_commit_racing_delivered_dispute_is_refused(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid, r = _commit_race(c, lose_fanout=False)
    assert r.status_code == 409
    assert c.state(0, sid)["state"] == "disputed"
    assert c.ace_count(0) == 0


# --------------------------------------------------------------------------- b3: /local_restore
def _local_restore_race(c):
    sid = _setup(c, sites=(0,))
    assert c.local_revoke(0).status_code == 200
    c.net.after("GET", "/scores", lambda: c.dispute("site-1"))
    r = c.local_restore(0)
    assert c.evidence_score()["status"] == "disputed"
    return sid, r


def test_b3r_1_local_restore_racing_dispute_is_refused(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid, r = _local_restore_race(c)
    assert r.status_code == 409
    st = c.state(0, sid)
    assert (st["state"], st["origin"]) == ("revoked", "local"), st


def test_b3r_2_reconcile_repairs_local_restore_race(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid, _r = _local_restore_race(c)
    assert c.reconcile(0).status_code == 200
    assert c.state(0, sid)["state"] == "disputed"


def test_b3r_3_raced_local_restore_still_cannot_export(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    _sid, _r = _local_restore_race(c)
    assert c.commit(0).status_code == 409
    assert c.ace_count(0) == 0


# --------------------------------------------------------------------------- b4: evidence down
def test_b4_1_local_revoke_works_with_evidence_down(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid = _setup(c, sites=(0,))
    c.net.evidence_down = True
    try:
        ok = c.local_revoke(0).status_code == 200
    except httpx.HTTPError:  # TestClient re-raises the unhandled server error
        ok = False
    assert ok, "local veto refused while the evidence is unreachable"
    st = c.state(0, sid)
    assert (st["state"], st["origin"]) == ("revoked", "local")
    assert c.ace_count(0) == 0


def test_b4_2_local_restore_with_evidence_down_is_not_applied(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid = _setup(c, sites=(0,))
    assert c.local_revoke(0).status_code == 200
    c.net.evidence_down = True
    try:
        status = c.local_restore(0).status_code
    except httpx.HTTPError:
        status = None
    assert status != 200
    st = c.state(0, sid)
    assert (st["state"], st["origin"]) == ("revoked", "local")


def test_b4_3_export_works_with_evidence_down(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    _setup(c, sites=(0,))
    c.net.evidence_down = True
    assert c.ace_count(0) == 1


# --------------------------------------------------------------------------- b6: >= 3 sites
def test_b6_1_concurrent_restore_and_dispute_converge_on_three_sites(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid = _setup(c, sites=(0, 1, 2))
    assert c.dispute("site-1").json()["applied"] is True  # seq 1
    gate = c.net.gate(2, "/apply_fanout")
    results: dict[str, object] = {}

    def run(name, fn):
        try:
            results[name] = fn().status_code
        except Exception as exc:  # noqa: BLE001 - recorded and asserted below
            results[name] = exc

    t_restore = threading.Thread(target=run, args=("restore", c.restore))
    t_restore.start()
    assert gate.reached.wait(5), "restore fan-out never reached site-2"
    assert c.evidence_score()["status"] == "active"  # restore committed (seq 2) before its fan-out
    t_dispute = threading.Thread(target=run, args=("dispute", lambda: c.dispute("site-0")))
    t_dispute.start()
    deadline = time.monotonic() + 5
    while len(c.net.calls_to(2, "/apply_fanout")) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)  # seq 1 (delivered) + seq 2 (parked) + seq 3 (parked)
    gate.release()
    t_restore.join(10)
    t_dispute.join(10)
    assert not t_restore.is_alive() and not t_dispute.is_alive()
    assert results == {"restore": 200, "dispute": 200}, results
    ev = c.evidence_score()
    assert (ev["status"], ev["fanout_seq"]) == ("disputed", 3)
    for i in range(N3):
        st = c.state(i, sid)
        assert (st["state"], st["last_applied_seq"]) == ("disputed", 3), (i, st)
        assert c.ace_count(i) == 0
        assert c.pending(i) == []


def test_b6_2_quorum2_single_vote_persists_and_restore_refused_characterization(make_cluster) -> None:
    c = make_cluster(n_sites=N3, quorum=2)
    sid = _setup(c, sites=(0, 1, 2))
    assert c.dispute("site-1").json() == {"applied": False}
    assert c.restore().status_code == 409
    assert c.evidence_score()["status"] == "active"
    assert c.ace_count(0) == 1
    assert c.dispute("site-2").json() == {"applied": True}  # the old vote still counts
    assert c.evidence_score()["status"] == "disputed"
    assert c.state(0, sid)["state"] == "disputed"


def test_a10_quorum2_confirmation_needs_a_site_outside_the_suspending_voters(make_cluster) -> None:
    c = make_cluster(n_sites=N3, quorum=2)
    sid = _setup(c, sites=(0, 1, 2))
    assert c.dispute("site-0").json() == {"applied": False}
    assert c.dispute("site-1").json() == {"applied": True}
    assert c.evidence_score()["status"] == "disputed"
    assert c.dispute("site-0").json() == {"applied": False}  # a suspending voter cannot confirm
    assert c.evidence_score()["status"] == "disputed"
    assert c.dispute("site-2").json() == {"applied": True}
    assert c.evidence_score()["status"] == "revoked"
    assert c.state(0, sid)["state"] == "revoked"
