"""In-process tests of distributed/service.py (audit buco B4, + D6, D8, D11), no Docker.

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-10).
Nessun codice di produzione e' modificato; i controlli negativi usano una COPIA del
sorgente in tmp_path con una sostituzione di testo. Infrastruttura: _dist_harness.py
(istanze caricate per ruolo, rete finta al posto di httpx.get/post, nessun socket).
DIST = code/src/dib/registry/distributed/service.py.

Ipotesi dichiarate (attese e criterio di falsificazione)
--------------------------------------------------------
H-fanout  Una dispute raggiunge tutti i siti con record (DIST:356-382, 147-170), crea
          record in nessun sito senza riga (DIST:151-153), la seconda segnalazione di un
          sito distinto revoca con origin "fanout" (DIST:450-453,166), segnalazioni
          ripetute o successive alla revoca non producono evento (DIST:438-454).
H-D8      (characterization) Con SUSPENSION_QUORUM=2 la prima segnalazione non sospende
          (DIST:439-443). Il paper non lo dice. NOTA: l'audit (D8) sostiene che la revoca
          richieda poi "un terzo sito distinto"; la mia lettura di DIST:450 e' diversa:
          dopo la sospensione causata da B, una segnalazione di A (gia' contata nelle
          suspension_reports ma != disputed_by) revoca, quindi bastano DUE siti distinti.
          Il test asserisce la lettura del codice; se fallisce, e' l'audit ad avere
          ragione e lo si riporta.
H-D11     (characterization) Il fan-out fa 3 tentativi per sito, in sequenza sui siti,
          timeout 1,0 s, senza pause (DIST:64-65,360-371). Si contano le chiamate, non il
          tempo.
H-retry   Consegna al 3o tentativo: outbox vuoto. Tre tentativi falliti: una riga
          (site, score) con seq/event_type/target_state dell'evento (DIST:372-382).
H-outbox  Per (site, score) resta una sola riga, con il seq piu' alto; un insert con seq
          inferiore non sovrascrive (DIST:377-379).
H-reconcile  /reconcile applica gli item pendenti con la stessa guardia idempotente
          (DIST:254-270), poi fa ack solo se c'era qualcosa; k episodi saltati collassano
          in un solo target pendente; un secondo reconcile non fa nulla; un apply_fanout
          con seq <= last_applied_seq e' un no-op (DIST:155-156).
H-D6 (_spec)  Un sito rimasto Active per un intero episodio dispute->restore torna a
          MonitorOnly dopo il reconcile (DIST:157-161): e' la semantica voluta. Il
          modello TLA+ (Reconcile) lascerebbe Active; qui non e' verificato.
H-origin  Un veto locale (revoked/local) non viene sovrascritto da dispute, revoke e
          restore globali, ne' da un restore pendente al reconcile: avanza solo
          last_applied_seq (DIST:157-165). local_restore e' rifiutato (409) se la
          revoca e' di origine fanout o se un episodio e' aperto (DIST:229-247);
          local_revoke e' consentito su revoked/fanout (DIST:216-219).
H-cmd     /commit e' bloccato se l'evidence non e' accepted+active (DIST:196-197) e se lo
          stato locale non e' monitor-only (DIST:201); /export_mud esporta solo Active.
H-NC      Controllo negativo (analogo di m6): su una copia in cui le due guardie di
          origine di _apply_fanout_row sono neutralizzate, lo stesso scenario del veto
          locale deve fallire. Se non fallisce, il test non discrimina.
"""
from __future__ import annotations

import time

import pytest

from _dist_harness import Cluster, make_cluster, make_source_copy  # noqa: F401

FACT = "api.vendor.com"


def _setup(c: Cluster, staged=None) -> int:
    sid = c.seed()
    for site in (range(c.n_sites) if staged is None else staged):
        assert c.stage(site).json()["applied"] is True
    return sid


def _episode(c: Cluster, a: str = "rep-a", b: str = "rep-b") -> None:
    assert c.dispute(a).json()["applied"] is True
    assert c.dispute(b).json()["applied"] is True
    assert c.restore().json()["applied"] is True


# ------------------------------------------------------------------ fan-out

def test_dispute_fans_out_to_all_sites_with_records(make_cluster) -> None:
    c = make_cluster(n_sites=3)
    sid = _setup(c, staged=[0, 1])
    assert c.dispute("rep-a").json() == {"applied": True}
    for site in (0, 1):
        assert c.state(site, sid) == {"state": "disputed", "origin": None, "last_applied_seq": 1}
    assert c.state(2, sid) is None  # nessun record: nulla da propagare (DIST:151-153)
    assert c.evidence_score()["status"] == "disputed"
    assert c.evidence_score()["fanout_seq"] == 1


def test_second_distinct_site_revokes_with_origin_fanout(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.dispute("rep-a")
    assert c.dispute("rep-a").json() == {"applied": False}  # stesso sito: nessun voto
    assert c.evidence_score()["fanout_seq"] == 1
    assert c.dispute("rep-b").json() == {"applied": True}
    for site in (0, 1):
        assert c.state(site, sid) == {"state": "revoked", "origin": "fanout", "last_applied_seq": 2}
    assert c.evidence_score()["status"] == "revoked"


def test_third_dispute_after_revoke_is_noop(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.dispute("rep-a")
    c.dispute("rep-b")
    fanouts_before = len(c.net.calls_to(0, "/apply_fanout"))
    assert c.dispute("rep-c").json() == {"applied": False}
    assert c.evidence_score()["fanout_seq"] == 2
    assert len(c.net.calls_to(0, "/apply_fanout")) == fanouts_before
    assert c.state(0, sid)["last_applied_seq"] == 2


@pytest.mark.xfail(strict=True, reason="comportamento osservato sul codice PRIMA della correzione (tnsm-fixes): il difetto e' stato corretto, il test documenta il vecchio comportamento")
def test_suspension_quorum_2_two_distinct_sites_suffice_characterization(make_cluster) -> None:
    """D8 (vedi docstring del modulo per la divergenza dall'audit)."""
    c = make_cluster(n_sites=2, quorum=2)
    sid = _setup(c)
    assert c.dispute("rep-a").json() == {"applied": False}  # prima segnalazione: nessuna sospensione
    assert c.evidence_score()["status"] == "active"
    assert c.state(0, sid)["state"] == "monitor-only"
    assert c.dispute("rep-b").json() == {"applied": True}  # secondo sito distinto: sospende
    assert c.evidence_score()["status"] == "disputed"
    assert c.evidence_score()["disputed_by"] == "rep-b"
    assert c.dispute("rep-b").json() == {"applied": False}  # stessa segnalatrice che ha sospeso
    assert c.evidence_score()["status"] == "disputed"
    assert c.dispute("rep-a").json() == {"applied": True}  # rep-a != disputed_by: conferma la revoca
    assert c.evidence_score()["status"] == "revoked"
    assert c.state(0, sid)["state"] == "revoked"


def test_fanout_makes_three_attempts_per_down_site_sequentially_characterization(
    make_cluster, monkeypatch
) -> None:
    """D11: si contano i tentativi (non il tempo), l'ordine tra siti e le pause."""
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
    c = make_cluster(n_sites=3)
    sid = _setup(c, staged=[0])
    c.net.down.update({1, 2})
    assert c.dispute("rep-a").json() == {"applied": True}  # risponde dopo il giro completo
    fanout = [(call.host, call.timeout) for call in c.net.calls if call.path == "/apply_fanout"]
    assert [host for host, _ in fanout] == (
        ["site0.test"] + ["site1.test"] * 3 + ["site2.test"] * 3
    )
    assert {timeout for _, timeout in fanout} == {1.0}
    assert slept == []  # nessuna pausa tra i tentativi
    assert {item["score_id"] for item in c.pending(1)} == {sid}
    assert {item["score_id"] for item in c.pending(2)} == {sid}


# --------------------------------------------------------------- retry / outbox

def test_fanout_succeeds_on_third_attempt(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.net.fail_next[(1, "/apply_fanout")] = 2
    c.dispute("rep-a")
    assert len(c.net.calls_to(1, "/apply_fanout")) == 3
    assert c.pending(1) == []
    assert c.state(1, sid)["state"] == "disputed"


def test_fanout_exhausts_attempts_and_enqueues(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.net.down.add(1)
    c.dispute("rep-a")
    assert len(c.net.calls_to(1, "/apply_fanout")) == 3
    assert c.pending(1) == [{"score_id": sid, "seq": 1, "event_type": "dispute", "target_state": "disputed"}]
    assert c.state(0, sid)["state"] == "disputed"  # gli altri siti sono consegnati
    assert c.state(1, sid)["state"] == "monitor-only"
    assert c.pending(0) == []


def test_outbox_keeps_latest_seq_per_site_score(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.net.down.add(1)
    _episode(c)  # dispute seq1, revoke seq2, restore seq3
    expected = [{"score_id": sid, "seq": 3, "event_type": "restore", "target_state": "monitor-only"}]
    assert c.pending(1) == expected
    c.evidence_mod._fan_out(sid, 1, "dispute", "disputed")  # evento vecchio, sito ancora giu'
    assert c.pending(1) == expected


# ------------------------------------------------------------------ reconcile

def test_reconcile_applies_pending_and_acks(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.net.down.add(1)
    c.dispute("rep-a")
    c.dispute("rep-b")
    assert [p["seq"] for p in c.pending(1)] == [2]
    c.net.down.clear()
    assert c.reconcile(1).json() == {"reconciled": 1}
    assert c.state(1, sid) == {"state": "revoked", "origin": "fanout", "last_applied_seq": 2}
    assert c.pending(1) == []
    assert any(call.method == "POST" and call.path == "/pending/site-1/ack" for call in c.net.calls)


def test_reconcile_with_nothing_pending_does_not_ack(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    _setup(c)
    assert c.reconcile(1).json() == {"reconciled": 0}
    assert not any(call.path.endswith("/ack") for call in c.net.calls)


@pytest.mark.parametrize("episodes", [1, 3])
def test_reconcile_after_skipped_episodes_collapses_to_single_target(make_cluster, episodes) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.net.down.add(1)
    for _ in range(episodes):
        _episode(c)
    pending = c.pending(1)
    assert pending == [
        {"score_id": sid, "seq": 3 * episodes, "event_type": "restore", "target_state": "monitor-only"}
    ]
    c.net.down.clear()
    assert c.reconcile(1).json() == {"reconciled": 1}
    assert c.state(1, sid) == {"state": "monitor-only", "origin": None, "last_applied_seq": 3 * episodes}
    assert c.evidence_score()["status"] == "active"
    assert c.pending(1) == []


def test_reconcile_is_idempotent_and_stale_seq_is_noop(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.net.down.add(1)
    c.dispute("rep-a")
    c.dispute("rep-b")
    c.net.down.clear()
    c.reconcile(1)
    after_first = c.state(1, sid)
    assert c.reconcile(1).json() == {"reconciled": 0}
    assert c.state(1, sid) == after_first
    for seq in (1, 2):  # seq < e == last_applied_seq (2)
        stale = {"score_id": sid, "seq": seq, "event_type": "restore", "target_state": "monitor-only"}
        assert c.sites[1].post("/apply_fanout", json=stale).status_code == 200
        assert c.state(1, sid) == after_first


def test_offline_active_site_goes_monitor_only_after_reconcile_spec(make_cluster) -> None:
    """D6, semantica voluta (DIST:157-161). Il modello TLA+ (Reconcile) la lascerebbe Active."""
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    assert c.commit(1).status_code == 200
    assert c.state(1, sid)["state"] == "active"
    c.net.down.add(1)
    c.dispute("rep-a")
    c.restore()
    c.net.down.clear()
    assert c.state(1, sid)["state"] == "active"  # ancora Active prima del reconcile
    c.reconcile(1)
    assert c.state(1, sid) == {"state": "monitor-only", "origin": None, "last_applied_seq": 2}
    assert c.ace_count(1) == 0


# --------------------------------------------------------------------- origin

def _scenario_local_veto_survives(c: Cluster) -> None:
    """Scenario condiviso col controllo negativo (H-NC)."""
    sid = _setup(c)
    assert c.local_revoke(1).status_code == 200
    assert c.state(1, sid) == {"state": "revoked", "origin": "local", "last_applied_seq": 0}
    c.dispute("rep-a")
    c.dispute("rep-b")
    c.restore()
    assert c.state(1, sid) == {"state": "revoked", "origin": "local", "last_applied_seq": 3}
    assert c.state(0, sid)["state"] == "monitor-only"


def test_local_revoke_survives_dispute_revoke_and_global_restore(make_cluster) -> None:
    _scenario_local_veto_survives(make_cluster(n_sites=2))


def test_local_veto_during_outage_survives_reconciled_restore(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.net.down.add(1)  # irraggiungibile dall'evidence; il sito opera comunque localmente
    assert c.local_revoke(1).status_code == 200
    _episode(c)
    c.net.down.clear()
    assert c.reconcile(1).json() == {"reconciled": 1}
    assert c.state(1, sid) == {"state": "revoked", "origin": "local", "last_applied_seq": 3}
    assert c.pending(1) == []


def test_local_restore_refused_on_fanout_origin_while_restore_is_pending(make_cluster) -> None:
    """Il sito resta bloccato (409) finche' non arriva un evento globale (B1, D12)."""
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.dispute("rep-a")
    c.dispute("rep-b")  # entrambi revoked/fanout
    r = c.local_restore(1)
    assert r.status_code == 409 and "dispute episode is open" in r.text  # episodio aperto (DIST:234-235)
    c.net.down.add(1)
    c.restore()  # il restore non raggiunge il sito 1: pendente
    assert c.evidence_score()["status"] == "active"
    assert c.state(1, sid) == {"state": "revoked", "origin": "fanout", "last_applied_seq": 2}
    r = c.local_restore(1)
    assert r.status_code == 409 and "not locally revoked" in r.text  # origin fanout (DIST:239-240)
    c.net.down.clear()
    c.reconcile(1)
    assert c.state(1, sid)["state"] == "monitor-only"


def test_local_revoke_allowed_on_fanout_revoked(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.dispute("rep-a")
    c.dispute("rep-b")
    assert c.state(1, sid)["origin"] == "fanout"
    assert c.local_revoke(1).status_code == 200
    assert c.state(1, sid)["origin"] == "local" and c.state(1, sid)["state"] == "revoked"


def test_local_restore_after_global_restore_allowed(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    c.local_revoke(1)
    c.dispute("rep-a")
    assert c.local_restore(1).status_code == 409  # episodio aperto
    c.dispute("rep-b")
    c.restore()
    assert c.local_restore(1).status_code == 200
    assert c.state(1, sid)["state"] == "monitor-only" and c.state(1, sid)["origin"] is None


# ---------------------------------------------------------------- commit/export

def test_commit_blocked_by_global_state_and_local_state(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = c.seed()
    assert c.commit(0).status_code == 409  # nessun record locale
    c.stage(0)
    c.dispute("rep-a")
    r = c.commit(0)
    assert r.status_code == 409 and "not admissible" in r.text  # evidence disputed (DIST:196-197)
    c.restore()
    assert c.commit(0).status_code == 200
    assert c.state(0, sid)["state"] == "active"
    r = c.commit(0)
    assert r.status_code == 409 and "cannot commit" in r.text  # DIST:201-202
    c.evidence_mod._evidence_db.run(lambda con: con.execute("UPDATE scores SET accepted=0"))
    assert c.commit(0).status_code == 409  # non piu' accepted


def test_export_mud_only_active_records(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    _setup(c)
    assert c.ace_count(0) == 0
    c.commit(0)
    assert c.ace_count(0) == 1 and c.ace_count(1) == 0
    c.dispute("rep-a")
    assert c.ace_count(0) == 0


# ------------------------------------------------------------ negative control

def test_negative_control_apply_fanout_ignoring_origin(make_cluster, tmp_path) -> None:
    """H-NC: analogo di m6. Le due guardie di origine sono neutralizzate nella copia."""
    source = make_source_copy(
        tmp_path,
        [
            ('if event_type == "restore" and state == DECISION_REVOKED and origin == ORIGIN_LOCAL:', "if False:"),
            ('if event_type in ("dispute", "revoke") and state == DECISION_REVOKED and origin == ORIGIN_LOCAL:',
             "if False:"),
        ],
    )
    c = make_cluster(n_sites=2, source=source)
    with pytest.raises(AssertionError):
        _scenario_local_veto_survives(c)
