"""Tests of the D12 fix: ack per (score_id, seq) + bounded re-pull in /reconcile.

Scritto e committato PRIMA di essere eseguito (2026-10-10, branch fix-d12-ack).
DIST = code/src/dib/registry/distributed/service.py. seq e' per fatto (scores.fanout_seq,
DIST:327,444,451,470): non confrontabile tra fatti.

Ipotesi
-------
H-compat  Un ack senza corpo cancella tutte le righe del sito (comportamento legacy). Un ack
          con corpo {"applied": [{score_id, seq}]} cancella solo righe dello stesso score_id
          con seq <= quello indicato: una riga piu' nuova, di un altro fatto o di un altro
          sito sopravvive.
H-body    /reconcile invia nell'ack le coppie lette e applicate; il corpo JSON della risposta
          resta {"reconciled": n_primo_pull}; i giri che hanno applicato item sono
          nell'header X-Dib-Reconcile-Rounds (0 se non c'era nulla).
H-repull  Un evento accodato dopo il primo GET viene letto dal giro successivo e applicato
          nella stessa chiamata.
H-window  (characterization) Con eventi che arrivano dopo ciascuno dei 3 GET, l'ultimo evento
          resta in outbox e viene applicato solo dal /reconcile successivo. Finestra residua:
          il sito resta Active con 1 ACE su un fatto Revoked fino a quel secondo reconcile.
          Nessuno schedula /reconcile: il limite superiore della finestra e' deciso dal
          chiamante.
H-error   Un item il cui apply solleva un'eccezione NON e' incluso nell'ack e resta in outbox;
          gli item applicati prima dell'errore sono acked; un reconcile successivo senza
          errore converge.
H-NC      Controlli con bug reintrodotto, su COPIE del sorgente corretto:
          (a) `if req is None:` -> `if True:` (ack senza filtro): gli scenari D12 devono
              fallire per l'asserzione di convergenza / di esposizione, con il messaggio
              atteso (outbox vuoto, last_applied_seq vecchio; ACE = 1 con evidence Revoked);
          (b) `_RECONCILE_MAX_ROUNDS = 3` -> `1` (nessun ri-pull, ack per coppia intatto):
              nessuna perdita (converge) ma resta l'esposizione immediata (ACE = 1, revoke
              ancora in outbox).
          Un errore diverso da AssertionError, o un messaggio diverso, fa fallire il controllo.

[fix-d19, audit 06 §3 e addendum] Dopo D19 la mutazione (a) e' MASCHERATA dall'anti-entropia
(la riparazione dell'ultimo snapshot converge nella stessa chiamata). Il controllo (a) discrimina
ora la finestra: outbox dopo il primo ack (H-win; con ack senza filtro e' vuota); il controllo
composto (a + riparazione off, H-comp) conserva le asserzioni originali. Il numero di tick per
convergere e' 0 in entrambi i casi: non e' asserito, solo riportato nel messaggio.
"""
from __future__ import annotations

import pytest

from _dist_harness import make_cluster, make_source_copy  # noqa: F401
from test_distributed_d12_reproducer import (
    X,
    Y,
    _converged,
    _lost_restore,
    _lost_revoke_with_pending_on_other_fact,
    _observation,
)


def _pending_rows(c, site: int):
    return sorted((p["score_id"], p["seq"]) for p in c.pending(site))


def _two_pending_facts(c):
    sid_x = c.seed(X)
    sid_y = c.seed(Y)
    for endpoint in (X, Y):
        for site in range(c.n_sites):
            c.stage(site, endpoint)
    return sid_x, sid_y


# ------------------------------------------------------------------ H-compat

def test_ack_without_body_deletes_all_rows_of_the_site(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    _two_pending_facts(c)
    c.net.down.add(1)
    c.dispute("rep-a", X)
    c.dispute("rep-a", Y)
    assert len(c.pending(1)) == 2
    assert c.evidence.post("/pending/site-1/ack").status_code == 200
    assert c.pending(1) == []


def test_ack_with_body_deletes_only_matching_pairs(make_cluster) -> None:
    c = make_cluster(n_sites=3)
    sid_x, sid_y = _two_pending_facts(c)
    c.net.down.update({1, 2})
    c.dispute("rep-a", X)
    c.dispute("rep-a", Y)
    assert _pending_rows(c, 1) == [(sid_x, 1), (sid_y, 1)]

    def ack(pairs):
        body = {"applied": [{"score_id": s, "seq": q} for s, q in pairs]}
        assert c.evidence.post("/pending/site-1/ack", json=body).status_code == 200

    ack([(sid_x, 0)])  # seq piu' vecchio di quello in coda: la riga sopravvive
    assert _pending_rows(c, 1) == [(sid_x, 1), (sid_y, 1)]
    ack([(999, 5)])  # fatto sconosciuto: no-op
    assert _pending_rows(c, 1) == [(sid_x, 1), (sid_y, 1)]
    ack([(sid_x, 1)])  # solo X
    assert _pending_rows(c, 1) == [(sid_y, 1)]
    assert _pending_rows(c, 2) == [(sid_x, 1), (sid_y, 1)]  # altro sito intatto
    ack([(sid_y, 7)])  # seq acked >= riga: cancellata
    assert c.pending(1) == []


def test_row_updated_after_the_site_pull_survives_the_ack(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = c.seed()
    c.stage(0)
    c.stage(1)
    c.net.down.add(1)
    c.dispute("rep-a")
    c.dispute("rep-b")  # riga (site-1, sid) aggiornata a seq 2
    body = {"applied": [{"score_id": sid, "seq": 1}]}  # il sito aveva letto solo seq 1
    assert c.evidence.post("/pending/site-1/ack", json=body).status_code == 200
    assert _pending_rows(c, 1) == [(sid, 2)]


# ------------------------------------------------------------------- H-body

def test_reconcile_sends_ack_body_with_pairs_and_keeps_response_body(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = c.seed()
    c.stage(0)
    c.stage(1)
    c.net.down.add(1)
    c.dispute("rep-a")
    c.net.down.clear()
    r = c.reconcile(1)
    assert r.json() == {"reconciled": 1}
    assert r.headers["X-Dib-Reconcile-Rounds"] == "1"
    acks = [call for call in c.net.calls if call.path == "/pending/site-1/ack"]
    assert [call.json for call in acks] == [{"applied": [{"score_id": sid, "seq": 1}]}]


def test_reconcile_with_nothing_pending_reports_zero_rounds(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    c.seed()
    c.stage(1)
    r = c.reconcile(1)
    assert r.json() == {"reconciled": 0}
    assert r.headers["X-Dib-Reconcile-Rounds"] == "0"
    assert not any(call.path.endswith("/ack") for call in c.net.calls)


def test_reconcile_acks_every_pending_fact(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid_x, sid_y = _two_pending_facts(c)
    c.net.down.add(1)
    c.dispute("rep-a", X)
    c.dispute("rep-a", Y)
    c.net.down.clear()
    r = c.reconcile(1)
    assert r.json() == {"reconciled": 2}
    assert c.pending(1) == []
    assert c.state(1, sid_x)["state"] == "disputed" and c.state(1, sid_y)["state"] == "disputed"


# ------------------------------------------------------------------ H-repull

def test_repull_applies_event_queued_after_the_first_get(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _lost_restore(c)  # reconcile con restore (seq3) accodato tra GET e ack
    gets = [call for call in c.net.calls if call.method == "GET" and call.path == "/pending/site-1"]
    assert len(gets) == 3  # giro 1 (seq2), giro 2 (seq3), giro 3 vuoto
    assert c.state(1, sid) == {"state": "monitor-only", "origin": None, "last_applied_seq": 3}
    assert c.pending(1) == []


# ------------------------------------------------------------------ H-window

def test_residual_window_when_events_keep_arriving_characterization(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid_x, sid_y = _two_pending_facts(c)
    assert c.commit(1, X).status_code == 200
    c.net.down.add(1)
    c.dispute("rep-a", Y)  # pendente: (Y, seq1)
    c.net.down.clear()
    fired: list[int] = []

    def gone(action):
        def hook():
            fired.append(len(fired) + 1)
            c.net.down.add(1)
            action()
            c.net.down.discard(1)
        return hook

    c.net.after("GET", "/pending/site-1", gone(lambda: c.restore(Y)))  # dopo GET 1
    c.net.after("GET", "/pending/site-1", gone(lambda: c.dispute("rep-c", Y)))  # dopo GET 2

    def revoke_x():
        c.dispute("rep-a", X)
        c.dispute("rep-b", X)

    c.net.after("GET", "/pending/site-1", gone(revoke_x))  # dopo GET 3 (ultimo giro)
    r = c.reconcile(1)
    assert fired == [1, 2, 3]
    assert r.headers["X-Dib-Reconcile-Rounds"] == "3"
    # Finestra residua: il revoke di X e' in outbox ma non ancora applicato.
    assert _pending_rows(c, 1) == [(sid_x, 2)]
    assert c.evidence_score(X)["status"] == "revoked"
    assert c.state(1, sid_x)["state"] == "active"
    assert c.ace_count(1) == 1
    # Il reconcile successivo converge.
    r2 = c.reconcile(1)
    assert r2.json() == {"reconciled": 1} and r2.headers["X-Dib-Reconcile-Rounds"] == "1"
    assert c.pending(1) == []
    assert c.state(1, sid_x)["state"] == "revoked"
    assert c.ace_count(1) == 0


# ------------------------------------------------------------------- H-error

def test_item_whose_apply_raises_is_not_acked_and_converges_later(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    sid_x, sid_y = _two_pending_facts(c)
    c.net.down.add(1)
    c.dispute("rep-a", X)
    c.dispute("rep-a", Y)
    c.net.down.clear()
    site_mod = c.site_mods[1]
    real = site_mod._apply_fanout_row

    def flaky(con, score_id, seq, event_type, target_state):
        if score_id == sid_y:
            raise RuntimeError("injected apply failure")
        return real(con, score_id, seq, event_type, target_state)

    monkeypatch.setattr(site_mod, "_apply_fanout_row", flaky)
    with pytest.raises(RuntimeError, match="injected apply failure"):
        c.reconcile(1)
    assert c.state(1, sid_x)["state"] == "disputed"  # applicato prima dell'errore
    assert c.state(1, sid_y)["state"] == "monitor-only"  # non applicato
    assert _pending_rows(c, 1) == [(sid_y, 1)]  # X acked, Y resta in coda
    monkeypatch.setattr(site_mod, "_apply_fanout_row", real)
    assert c.reconcile(1).json() == {"reconciled": 1}
    assert c.state(1, sid_y)["state"] == "disputed"
    assert c.pending(1) == []


# ---------------------------------------------------------- H-NC (bug reintrodotto)

ACK_ANCHOR = "if req is None:"
ROUNDS_ANCHOR = "_RECONCILE_MAX_ROUNDS = 3"


REPAIR_ANCHOR = "repaired = _repair_from_snapshot(current, applied_seqs)"


def _record_outbox_after_first_ack(c) -> list:
    """Hook one-shot: outbox rows of site 1 right after the first ack (the evidence has
    already answered). Must be armed BEFORE the scenario helper runs the reconcile."""
    seen: list = []
    c.net.after("POST", "/pending/site-1/ack", lambda: seen.append(sorted(
        (p["score_id"], p["seq"]) for p in c.pending(1))))
    return seen


def _window(c, seen: list, expected: list) -> dict:
    gets = [call for call in c.net.calls if call.method == "GET" and call.path == "/pending/site-1"]
    return {
        "outbox_after_first_ack": seen[0] if seen else None,
        "expected": expected,
        "gets_pending": len(gets),
        "ticks_to_converge": 0,  # not asserted: the final repair runs in the same reconcile call
    }


def _assert_row_survives_first_ack(c, seen: list, expected: list) -> None:
    assert seen and seen[0] == expected, _window(c, seen, expected)


def _scenarios(c_factory):
    """(cluster, seen, expected, final-assert) for the two D12 scenarios; the scenario runs here."""
    c = c_factory()
    seen = _record_outbox_after_first_ack(c)
    sid = _lost_restore(c)
    yield c, seen, [(sid, 3)], lambda: _converged(c, sid), lambda: _observation(c, sid)
    c2 = c_factory()
    seen2 = _record_outbox_after_first_ack(c2)
    sid_x, _sid_y = _lost_revoke_with_pending_on_other_fact(c2)
    yield c2, seen2, [(sid_x, 2)], lambda: c2.ace_count(1) == 0, lambda: _observation(c2, sid_x, X)


def test_ack_keeps_the_row_queued_after_the_first_ack_d12_scenarios(make_cluster) -> None:
    """H-win (codice corretto): l'evento accodato fra GET e ack sopravvive all'ack."""
    for c, seen, expected, _final, _obs in _scenarios(lambda: make_cluster(n_sites=2)):
        _assert_row_survives_first_ack(c, seen, expected)


def test_negative_control_delete_all_ack_reintroduces_d12(make_cluster, tmp_path) -> None:
    """H-win/H-mask (riscritto dopo D19, audit 06 §3). Ack senza filtro, anti-entropia ATTIVA:
    la convergenza finale vale ancora (mascherata dalla riparazione, stessa chiamata, 0 tick),
    ma l'outbox dopo il primo ack e' vuota invece di contenere l'evento accodato."""
    source = make_source_copy(tmp_path, [(ACK_ANCHOR, "if True:")])
    for c, seen, expected, final, obs in _scenarios(lambda: make_cluster(n_sites=2, source=source)):
        assert final(), obs()  # masked by D19: converges anyway
        with pytest.raises(AssertionError) as window:
            _assert_row_survives_first_ack(c, seen, expected)
        message = str(window.value)
        assert "'outbox_after_first_ack': []" in message and "'expected': [(" in message, message
        assert "'gets_pending': 2" in message and "'ticks_to_converge': 0" in message, message


def test_negative_control_delete_all_ack_without_antientropy_reintroduces_d12(make_cluster, tmp_path) -> None:
    """H-comp: ack senza filtro + riparazione disattivata = controllo originale di audit 03 §4."""
    source = make_source_copy(tmp_path, [(ACK_ANCHOR, "if True:"), (REPAIR_ANCHOR, "repaired = 0")])
    c = make_cluster(n_sites=2, source=source)
    sid = _lost_restore(c)  # il setup completa senza errori: ci si aspetta solo la perdita
    with pytest.raises(AssertionError) as lost_restore:
        assert _converged(c, sid), _observation(c, sid)
    message = str(lost_restore.value)
    assert "'pending': []" in message and "'last_applied_seq': 2" in message and "'state': 'revoked'" in message

    c2 = make_cluster(n_sites=2, source=source)
    sid_x, _sid_y = _lost_revoke_with_pending_on_other_fact(c2)
    with pytest.raises(AssertionError) as exposure:
        assert c2.ace_count(1) == 0, _observation(c2, sid_x, X)
    message = str(exposure.value)
    assert "'pending': []" in message and "'state': 'active'" in message and "'status': 'revoked'" in message


def test_negative_control_without_repull_keeps_events_but_leaves_exposure(make_cluster, tmp_path) -> None:
    source = make_source_copy(tmp_path, [(ROUNDS_ANCHOR, "_RECONCILE_MAX_ROUNDS = 1")])
    c = make_cluster(n_sites=2, source=source)
    sid_x, _sid_y = _lost_revoke_with_pending_on_other_fact(c)
    assert _converged(c, sid_x, X)  # nessuna perdita: il revoke e' ancora in outbox
    with pytest.raises(AssertionError) as exposure:
        assert c.ace_count(1) == 0, _observation(c, sid_x, X)
    message = str(exposure.value)
    assert "'event_type': 'revoke'" in message and "'state': 'active'" in message
