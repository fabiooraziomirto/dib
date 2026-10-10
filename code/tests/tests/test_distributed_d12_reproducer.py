"""Deterministic reproducer for audit D12 (outbox ack vs. events arriving after GET /pending).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-10).
Nessun codice di produzione e' modificato. Infrastruttura: _dist_harness.py.
DIST = code/src/dib/registry/distributed/service.py.

Ipotesi
-------
H1 (D12, da testare, non assunta). L'ack cancella TUTTE le righe del sito:
   `DELETE FROM pending_fanout WHERE site_id=?` (DIST:495), senza filtro su seq ne' su
   score_id. /reconcile legge la lista (DIST:259), applica gli item letti (DIST:262-267)
   e poi chiama l'ack (DIST:268-269). Se tra GET /pending e l'ack arriva un evento nuovo la
   cui consegna diretta al sito FALLISCE, _fan_out aggiorna/inserisce la riga in outbox
   (DIST:373-382) e l'ack la cancella: il sito non riceve mai quell'evento.
   H1 e' FALSIFICATA se, dopo l'interleaving, il sito converge (last_applied_seq ==
   fanout_seq dell'evidence) oppure l'outbox conserva ancora l'evento.
H0 = nessuna perdita.
H2. La perdita richiede il doppio guasto (consegna diretta fallita nella finestra): se la
   consegna diretta riesce, il sito converge e un item pendente stantio (seq 2 dopo seq 3)
   non fa regredire lo stato (guardia seq <= last_applied_seq, DIST:155-156).
H3 (severita'). Perdere un `restore` e' un problema di disponibilita' (sito bloccato in
   revoked/fanout con evidence Active; local_restore dà 409 perche' origin != local,
   DIST:239). Perdere un `dispute`/`revoke` e' un problema di SICUREZZA solo se il sito
   resta Active mentre l'evidence e' Disputed/Revoked. Attesa dalla lettura del codice:
   (a) nel caso a fatto singolo con restore pendente il sito passa a MonitorOnly (D6) e
   /commit e' bloccato dallo stato globale (DIST:196-197), quindi nessun ACE esportato;
   (b) la perdita diventa un'esposizione se l'item pendente riguarda un ALTRO fatto: l'ack
   e' per sito e non per fatto, quindi il `revoke` del fatto X viene cancellato mentre il
   sito resta Active su X (ACE esportato con evidence Revoked).
H4. Un nuovo evento globale successivo (seq piu' alto, consegnato) riporta il sito a
   convergenza: la finestra di perdita dura fino al prossimo evento sul fatto.
H-NC. Controllo negativo: su una COPIA in cui l'ack cancella solo `seq <= <max seq letto>`,
   lo scenario di perdita deve convergere (l'evento in outbox sopravvive all'ack e il
   reconcile successivo lo applica). Se H1 e' falsificata il controllo e' "n/a" e lo si
   riporta.

[fix-d12-ack, 2026-10-10] Il controllo negativo H-NC (ack `seq <= max letto` su una copia del
codice VECCHIO) e' stato rimosso da questo file: le sue ancore di testo non esistono piu' dopo la
correzione e fallirebbe per "anchor not found". Lo sostituiscono i controlli con bug reintrodotto
in test_distributed_ack_fix.py. Le asserzioni degli altri test di questo file sono invariate.

Due test per scenario: `*_observe_*` e' sempre verde (verifica solo che l'interleaving
sia avvenuto e registra lo stato finale), `*_converges` / `*_no_exposure` asserisce la
proprieta': se fallisce, e' il risultato (D12 confermato) e non va indebolito.
"""
from __future__ import annotations

import json

from _dist_harness import make_cluster  # noqa: F401

X = "api.vendor.com"
Y = "cdn.vendor.com"


# ---------------------------------------------------------------- scenarios

def _converged(c, sid: int, endpoint: str = X, site: int = 1) -> bool:
    state = c.state(site, sid)
    return state["last_applied_seq"] == c.evidence_score(endpoint)["fanout_seq"] or c.pending(site) != []


def _observation(c, sid: int, endpoint: str = X, site: int = 1) -> dict:
    return {
        "site_state": c.state(site, sid),
        "pending": c.pending(site),
        "evidence": {k: c.evidence_score(endpoint)[k] for k in ("status", "fanout_seq")},
    }


def _lost_restore(c, *, deliver_directly: bool = False, interleave: bool = True):
    """Sito 1 perde dispute+revoke (outbox seq2), rientra e fa /reconcile; tra GET /pending
    e l'ack l'evidence emette `restore` (seq3) con consegna diretta fallita (o riuscita)."""
    sid = c.seed()
    c.stage(0)
    c.stage(1)
    c.net.down.add(1)
    c.dispute("rep-a")
    c.dispute("rep-b")
    assert [p["seq"] for p in c.pending(1)] == [2]
    c.net.down.clear()
    fired: list[bool] = []

    def hook():
        fired.append(True)
        if not deliver_directly:
            c.net.down.add(1)
        assert c.restore().json() == {"applied": True}
        c.net.down.discard(1)

    if interleave:
        c.net.after("GET", "/pending/site-1", hook)
    assert c.reconcile(1).json() == {"reconciled": 1}
    assert fired == ([True] if interleave else [])
    return sid


def _lost_dispute_after_pending_restore(c):
    """Fatto singolo, sito 1 Active; pendente: restore (seq2). Nella finestra arriva una
    dispute (seq3) con consegna diretta fallita."""
    sid = c.seed()
    c.stage(0)
    c.stage(1)
    assert c.commit(1).status_code == 200
    c.net.down.add(1)
    c.dispute("rep-a")
    c.restore()
    assert [(p["seq"], p["event_type"]) for p in c.pending(1)] == [(2, "restore")]
    c.net.down.clear()
    fired: list[bool] = []

    def hook():
        fired.append(True)
        c.net.down.add(1)
        assert c.dispute("rep-c").json() == {"applied": True}
        c.net.down.discard(1)

    c.net.after("GET", "/pending/site-1", hook)
    assert c.reconcile(1).json() == {"reconciled": 1}
    assert fired == [True]
    return sid


def _lost_revoke_with_pending_on_other_fact(c):
    """Due fatti X, Y. Sito 1 Active su X. Pendente per Y. Nella finestra l'evidence
    dispute+revoke X con consegna diretta al sito 1 fallita; l'ack e' per sito."""
    sid_x = c.seed(X)
    sid_y = c.seed(Y)
    for endpoint in (X, Y):
        c.stage(0, endpoint)
        c.stage(1, endpoint)
    assert c.commit(1, X).status_code == 200
    c.net.down.add(1)
    c.dispute("rep-a", Y)
    assert [p["score_id"] for p in c.pending(1)] == [sid_y]
    c.net.down.clear()
    fired: list[bool] = []

    def hook():
        fired.append(True)
        c.net.down.add(1)
        assert c.dispute("rep-a", X).json() == {"applied": True}
        assert c.dispute("rep-b", X).json() == {"applied": True}
        c.net.down.discard(1)

    c.net.after("GET", "/pending/site-1", hook)
    assert c.reconcile(1).json() == {"reconciled": 1}
    assert fired == [True]
    return sid_x, sid_y


def _record(record_property, name: str, observation: dict) -> None:
    text = json.dumps(observation, sort_keys=True)
    record_property(name, text)
    print(f"D12 {name}: {text}")


# ------------------------------------------------- 1. lost restore (disponibilita')

def test_d12_observe_lost_restore(make_cluster, record_property) -> None:
    c = make_cluster(n_sites=2)
    sid = _lost_restore(c)
    seq3_attempts = [call for call in c.net.calls_to(1, "/apply_fanout") if call.json["seq"] == 3]
    assert len(seq3_attempts) == 3  # premessa: la consegna diretta di seq3 e' fallita 3 volte
    _record(record_property, "lost_restore", _observation(c, sid))


def test_d12_lost_restore_converges(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _lost_restore(c)
    assert _converged(c, sid), _observation(c, sid)


def test_d12_lost_restore_local_restore_is_409(make_cluster, record_property) -> None:
    """Severita' (H3, B1): sito in revoked/fanout con evidence Active -> local_restore 409."""
    c = make_cluster(n_sites=2)
    sid = _lost_restore(c)
    _record(record_property, "lost_restore_before_local_restore", _observation(c, sid))
    r = c.local_restore(1)
    assert r.status_code == 409, r.text
    assert "not locally revoked" in r.text  # origin != local (DIST:239-240)


# ---------------------------------------------- 2. lost dispute, fatto singolo (H3a)

def test_d12_observe_lost_dispute_single_fact(make_cluster, record_property) -> None:
    c = make_cluster(n_sites=2)
    sid = _lost_dispute_after_pending_restore(c)
    assert [call for call in c.net.calls_to(1, "/apply_fanout") if call.json["seq"] == 3]
    _record(record_property, "lost_dispute_single_fact", _observation(c, sid))


def test_d12_lost_dispute_single_fact_converges(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _lost_dispute_after_pending_restore(c)
    assert _converged(c, sid), _observation(c, sid)


def test_d12_lost_dispute_single_fact_no_exposure(make_cluster, record_property) -> None:
    """H3a: nessun ACE e nessun commit possibile con evidence Disputed."""
    c = make_cluster(n_sites=2)
    sid = _lost_dispute_after_pending_restore(c)
    obs = _observation(c, sid)
    obs["commit_status"] = c.commit(1).status_code
    obs["ace_count"] = c.ace_count(1)
    _record(record_property, "lost_dispute_single_fact_exposure", obs)
    assert obs["commit_status"] == 409
    assert obs["ace_count"] == 0


# --------------------------------------- 3. lost revoke, item pendente di altro fatto (H3b)

def test_d12_observe_lost_revoke_with_pending_on_other_fact(make_cluster, record_property) -> None:
    c = make_cluster(n_sites=2)
    sid_x, _sid_y = _lost_revoke_with_pending_on_other_fact(c)
    assert len([call for call in c.net.calls_to(1, "/apply_fanout") if call.json["score_id"] == sid_x]) == 6
    obs = _observation(c, sid_x, X)
    obs["ace_count"] = c.ace_count(1)
    _record(record_property, "lost_revoke_other_fact", obs)


def test_d12_lost_revoke_with_pending_on_other_fact_converges(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid_x, _sid_y = _lost_revoke_with_pending_on_other_fact(c)
    assert _converged(c, sid_x, X), _observation(c, sid_x, X)


def test_d12_lost_revoke_with_pending_on_other_fact_no_exposure(make_cluster) -> None:
    """H3b: con X Revoked sull'evidence, il sito 1 non deve esportare ACE per X."""
    c = make_cluster(n_sites=2)
    sid_x, _sid_y = _lost_revoke_with_pending_on_other_fact(c)
    assert c.evidence_score(X)["status"] == "revoked"
    assert c.ace_count(1) == 0, _observation(c, sid_x, X)


# --------------------------------------------------------------------- controlli

def test_d12_control_direct_delivery_converges(make_cluster) -> None:
    """H2: se la consegna diretta nella finestra riesce, nessuna perdita."""
    c = make_cluster(n_sites=2)
    sid = _lost_restore(c, deliver_directly=True)
    assert c.pending(1) == []
    assert c.state(1, sid)["last_applied_seq"] == c.evidence_score()["fanout_seq"] == 3
    assert _converged(c, sid)


def test_d12_stale_pending_seq2_after_direct_seq3_does_not_regress(make_cluster) -> None:
    """B3: l'item stantio seq2 applicato dopo seq3 non fa regredire lo stato."""
    c = make_cluster(n_sites=2)
    sid = _lost_restore(c, deliver_directly=True)
    assert c.state(1, sid) == {"state": "monitor-only", "origin": None, "last_applied_seq": 3}


def test_d12_control_no_interleaving_converges(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    sid = _lost_restore(c, interleave=False)
    assert c.pending(1) == []
    assert c.state(1, sid) == {"state": "revoked", "origin": "fanout", "last_applied_seq": 2}
    assert _converged(c, sid)
    assert c.evidence_score()["fanout_seq"] == 2


def test_d12_recovers_on_next_global_event(make_cluster) -> None:
    """H4: dopo la (eventuale) perdita, il prossimo evento consegnato riporta a convergenza."""
    c = make_cluster(n_sites=2)
    sid = _lost_restore(c)
    assert c.dispute("rep-c").json() == {"applied": True}  # evidence era Active: nuovo evento seq4
    assert c.state(1, sid)["last_applied_seq"] == c.evidence_score()["fanout_seq"] == 4
    assert c.state(1, sid)["state"] == "disputed"
