"""Registry lifecycle gap closure: audit buchi B5-B9 (+ D4, D5, D15), docs/audit/01.

PRE-REGISTRAZIONE. Questo file e' stato scritto e committato PRIMA di essere
eseguito (2026-10-10). Nessun codice di produzione e' modificato.

Ipotesi dichiarate (attese e criterio di falsificazione)
--------------------------------------------------------
H-B5  Con una dispute aperta (status Disputed o Revoked) query_score non crea ne'
      restituisce record locali (services.py:439). Falsificata se un sito senza
      record ottiene un record MonitorOnly durante la dispute.
H-B6  operator_commit solleva InvalidStateTransition da Disputed, Revoked(dispute),
      Revoked(local) e dopo un rescore sotto soglia (services.py:471-480).
      Falsificata se uno di questi commit riesce o cambia lo stato.
H-B7  export_active_mud esclude i record Disputed, Revoked(dispute) e Revoked(local)
      (services.py:776). Falsificata se compare un ACE per uno di questi stati.
H-B8  Dispute dopo la revoca non aggiungono transizioni: stato dello score,
      disputed_by e storie (score e decisioni) restano invariate. Il numero di
      negative_attestations NON viene asserito: viene solo registrato (il codice
      esegue comunque _upsert_attestation a services.py:644).
H-B9  Le transizioni non definite sono rifiutate o lasciano il record invariato
      (local_restore fuori da Revoked, query su record esistente, restore ripetuto).
H-D5  restore_score ripristina i valori del punteggio (score, confidenze, accepted,
      tier) all'ultima versione con status Active (services.py:694-706),
      scartando un rescore avvenuto durante la dispute. Caratterizzazione: fissa il
      comportamento attuale, non lo approva.
H-NC  Controllo negativo: su una copia di services.py in cui export_active_mud ammette
      anche i record Disputed (analogo della mutazione TLA+ m3), lo stesso controllo
      di H-B7 deve fallire. Se non fallisce, il test non discrimina.

Test che documentano un comportamento diverso da paper/modello hanno il suffisso
_characterization (D4, D15, D5). Esclusi per duplicazione: local_revoke senza record
e doppio local_revoke (gia' in test_registry.py:382), restore su fact Active mai
disputato (test_registry.py:571).
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

import dib.registry.db as db
from dib.registry import services

CAMERA = ("camera", "api.vendor.com", "https", 443)


def _fresh_session():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DIB_DATABASE_URL"] = f"sqlite:///{path}"
    db._engine = None
    db._SessionLocal = None
    return db.get_session()


def _seeded_score(session) -> None:
    services.upsert_profile(
        session, "site-a", "camera",
        [{"fqdn": "api.vendor.com", "protocol": "https", "port": 443, "count": 5}],
    )
    services.upsert_score(session, {
        "device_type": "camera", "endpoint": "api.vendor.com", "protocol": "https", "port": 443,
        "site_confidence": 0.9, "temporal_confidence": 0.8, "graph_confidence": 0.7,
        "score": 0.85, "accepted": True,
    })
    session.commit()


def _query(session, site):
    decision = services.query_score(session, site, *CAMERA)
    session.commit()
    return decision


def _commit(session, site):
    decision = services.operator_commit(session, site, *CAMERA)
    session.commit()
    return decision


def _dispute(session, site):
    score = services.dispute_score(session, *CAMERA, site)
    session.commit()
    return score


def _score(session):
    return services.get_score(session, *CAMERA)


# ---------------------------------------------------------------- B5 (R1)

def test_query_after_open_dispute_returns_none() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        _dispute(session, "site-b")
        assert _score(session).status == db.STATUS_DISPUTED
        assert _query(session, "site-x") is None
        assert _score(session).local_decisions == []

        _dispute(session, "site-c")
        assert _score(session).status == db.STATUS_REVOKED
        assert _query(session, "site-y") is None
        assert _score(session).local_decisions == []

        services.restore_score(session, *CAMERA)
        session.commit()
        decision = _query(session, "site-x")
        assert decision is not None and decision.state == db.DECISION_MONITOR_ONLY
    finally:
        session.close()


def test_query_existing_record_during_dispute_returns_none_characterization() -> None:
    """D15: il paper dice 'returns its existing decision'; il codice (services.py:439)
    restituisce None anche se il sito ha gia' un record."""
    session = _fresh_session()
    try:
        _seeded_score(session)
        decision = _query(session, "site-a")
        _dispute(session, "site-b")
        assert decision.state == db.DECISION_DISPUTED
        assert _query(session, "site-a") is None
        assert decision.state == db.DECISION_DISPUTED
    finally:
        session.close()


# ---------------------------------------------------------------- B6 (R2, D4)

def _assert_commit_rejected(session, site, expected_state):
    with pytest.raises(services.InvalidStateTransition):
        services.operator_commit(session, site, *CAMERA)
    session.rollback()
    decision = services.get_local_decision(session, _score(session).id, site)
    assert decision.state == expected_state


def test_commit_from_disputed_raises() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        _query(session, "site-a")
        _dispute(session, "site-b")
        _assert_commit_rejected(session, "site-a", db.DECISION_DISPUTED)
    finally:
        session.close()


def test_commit_from_revoked_dispute_raises() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        _query(session, "site-a")
        _dispute(session, "site-b")
        _dispute(session, "site-c")
        _assert_commit_rejected(session, "site-a", db.DECISION_REVOKED)
    finally:
        session.close()


def test_commit_from_local_revoked_raises() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        _query(session, "site-a")
        services.local_revoke(session, "site-a", *CAMERA)
        session.commit()
        assert _score(session).status == db.STATUS_ACTIVE
        _assert_commit_rejected(session, "site-a", db.DECISION_REVOKED)
    finally:
        session.close()


def test_commit_after_rescore_below_threshold_raises_characterization() -> None:
    """D4: operator_commit richiede score.accepted (services.py:471); il modello TLA+ e
    Table II no."""
    session = _fresh_session()
    try:
        _seeded_score(session)
        _query(session, "site-a")
        services.upsert_score(session, {
            "device_type": "camera", "endpoint": "api.vendor.com", "protocol": "https", "port": 443,
            "site_confidence": 0.1, "temporal_confidence": 0.1, "graph_confidence": 0.0,
            "score": 0.2, "accepted": False,
        })
        session.commit()
        assert _score(session).status == db.STATUS_ACTIVE
        _assert_commit_rejected(session, "site-a", db.DECISION_MONITOR_ONLY)
    finally:
        session.close()


# ---------------------------------------------------------------- B7 (M3 / m3)

def _assert_export_excludes_disputed(export_fn) -> None:
    """Scenario condiviso tra il test vero e il controllo negativo (H-NC)."""
    session = _fresh_session()
    try:
        _seeded_score(session)
        _query(session, "site-a")
        _commit(session, "site-a")
        assert export_fn(session, "site-a", "camera").exported_ace_count == 1
        _dispute(session, "site-b")
        assert _score(session).status == db.STATUS_DISPUTED
        assert export_fn(session, "site-a", "camera").exported_ace_count == 0
    finally:
        session.close()


def test_export_excludes_disputed_record() -> None:
    _assert_export_excludes_disputed(services.export_active_mud)


def test_export_excludes_revoked_dispute_record_until_fresh_commit() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        _query(session, "site-a")
        _commit(session, "site-a")
        _dispute(session, "site-b")
        _dispute(session, "site-c")
        assert _score(session).status == db.STATUS_REVOKED
        assert services.export_active_mud(session, "site-a", "camera").exported_ace_count == 0
        services.restore_score(session, *CAMERA)
        session.commit()
        assert services.export_active_mud(session, "site-a", "camera").exported_ace_count == 0
        _commit(session, "site-a")
        assert services.export_active_mud(session, "site-a", "camera").exported_ace_count == 1
    finally:
        session.close()


def test_export_excludes_local_revoked_record() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        _query(session, "site-a")
        _commit(session, "site-a")
        assert services.export_active_mud(session, "site-a", "camera").exported_ace_count == 1
        services.local_revoke(session, "site-a", *CAMERA)
        session.commit()
        assert services.export_active_mud(session, "site-a", "camera").exported_ace_count == 0
    finally:
        session.close()


def _load_services_copy(tmp_path: Path, old: str, new: str, name: str):
    """Copia di services.py in tmp_path con UNA sostituzione di testo (mai in produzione)."""
    source = Path(services.__file__).read_text()
    assert source.count(old) == 1, f"la riga da mutare non corrisponde piu' ({source.count(old)} occorrenze)"
    path = tmp_path / f"{name}.py"
    path.write_text(source.replace(old, new))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def test_negative_control_export_admitting_disputed(tmp_path) -> None:
    """H-NC: analogo di m3. Il controllo condiviso deve fallire sulla copia mutata."""
    mutant = _load_services_copy(
        tmp_path,
        "    decisions = list_local_decisions(session, site_id, device_type, DECISION_ACTIVE)\n",
        "    decisions = (list_local_decisions(session, site_id, device_type, DECISION_ACTIVE)\n"
        "                 + list_local_decisions(session, site_id, device_type, DECISION_DISPUTED))\n",
        "services_mutant_export_disputed",
    )
    try:
        with pytest.raises(AssertionError):
            _assert_export_excludes_disputed(mutant.export_active_mud)
    finally:
        sys.modules.pop("services_mutant_export_disputed", None)


# ---------------------------------------------------------------- B8 (R4)

def _revoked_fact_with_committed_site(session):
    _seeded_score(session)
    decision = _query(session, "site-a")
    _commit(session, "site-a")
    _dispute(session, "site-b")
    _dispute(session, "site-c")
    score = _score(session)
    assert score.status == db.STATUS_REVOKED
    return score, decision


def _snapshot(session, score, decision):
    return (
        score.status, score.disputed_by, score.version,
        [e.event for e in services.get_score_history(session, score.id)],
        decision.state, decision.version,
        [e.event for e in services.get_local_decision_history(session, decision.id)],
    )


def _snapshot_without_version(session, score, decision):
    status, disputed_by, _version, score_events, state, dversion, dec_events = _snapshot(session, score, decision)
    return (status, disputed_by, score_events, state, dversion, dec_events)


def test_third_dispute_after_revoke_adds_no_transition() -> None:
    """Stato dello score, disputed_by, decisioni locali e storie (score e decisioni) restano
    invariati. score.version e negative_attestations sono nel test _characterization sotto."""
    session = _fresh_session()
    try:
        score, decision = _revoked_fact_with_committed_site(session)
        before = _snapshot_without_version(session, score, decision)
        _dispute(session, "site-d")
        score = _score(session)
        assert _snapshot_without_version(session, score, decision) == before
        assert before[2] == ["upsert", "dispute", "revoke"]
    finally:
        session.close()


def test_third_dispute_after_revoke_bumps_version_and_attestations_characterization(record_property) -> None:
    """Split di B8 (2026-10-10, su richiesta): una dispute dopo la revoca da un sito NUOVO non crea
    eventi ma aggiorna negative_attestations (services.py:644-646); l'UPDATE della riga Score
    fa avanzare il token di concorrenza ottimistica (db.py:117-124). Risultato: score.version
    (4) non coincide piu' con l'ultima versione in get_score_history (3). Fissa il
    comportamento osservato, non lo approva."""
    session = _fresh_session()
    try:
        score, decision = _revoked_fact_with_committed_site(session)
        version_before, neg_before = score.version, score.negative_attestations
        history_len = len(services.get_score_history(session, score.id))
        _dispute(session, "site-d")
        score = _score(session)
        record_property("score_version_before_after", f"{version_before}->{score.version}")
        record_property("negative_attestations_before_after", f"{neg_before}->{score.negative_attestations}")
        assert (version_before, score.version) == (3, 4)
        assert (neg_before, score.negative_attestations) == (2, 3)
        history = services.get_score_history(session, score.id)
        assert len(history) == history_len == 3
        assert history[-1].version == 3 != score.version
    finally:
        session.close()


def test_repeated_dispute_from_same_site_after_revoke_is_noop(record_property) -> None:
    session = _fresh_session()
    try:
        score, decision = _revoked_fact_with_committed_site(session)
        before = _snapshot(session, score, decision)
        neg_before = score.negative_attestations
        _dispute(session, "site-b")
        _dispute(session, "site-c")
        score = _score(session)
        assert _snapshot(session, score, decision) == before
        record_property("negative_attestations_before_repeats", neg_before)
        record_property("negative_attestations_after_repeats", score.negative_attestations)
        print(f"B8 repeats negative_attestations: before={neg_before} after={score.negative_attestations}")
    finally:
        session.close()


# ---------------------------------------------------------------- B9

def test_local_restore_on_non_revoked_raises() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        decision = _query(session, "site-a")
        for expected in (db.DECISION_MONITOR_ONLY, db.DECISION_ACTIVE):
            if expected == db.DECISION_ACTIVE:
                _commit(session, "site-a")
            with pytest.raises(services.InvalidStateTransition):
                services.local_restore(session, "site-a", *CAMERA)
            session.rollback()
            assert decision.state == expected
    finally:
        session.close()


def test_local_restore_without_local_record_returns_none() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        assert services.local_restore(session, "site-a", *CAMERA) is None
        assert services.local_restore(session, "site-a", "camera", "missing", "https", 443) is None
    finally:
        session.close()


def test_query_on_existing_record_is_noop() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        decision = _query(session, "site-a")
        _commit(session, "site-a")
        again = _query(session, "site-a")
        assert again is not None and again.id == decision.id and again.state == db.DECISION_ACTIVE
        events = [e.event for e in services.get_local_decision_history(session, decision.id)]
        assert events == ["query", "operator_commit"]

        services.local_revoke(session, "site-a", *CAMERA)
        session.commit()
        again = _query(session, "site-a")
        assert again.id == decision.id and again.state == db.DECISION_REVOKED
        events = [e.event for e in services.get_local_decision_history(session, decision.id)]
        assert events == ["query", "operator_commit", "local_revoke"]
    finally:
        session.close()


def test_restore_after_restore_raises() -> None:
    session = _fresh_session()
    try:
        _seeded_score(session)
        _dispute(session, "site-b")
        services.restore_score(session, *CAMERA)
        session.commit()
        assert _score(session).status == db.STATUS_ACTIVE
        with pytest.raises(services.InvalidStateTransition):
            services.restore_score(session, *CAMERA)
        session.rollback()
    finally:
        session.close()


# ---------------------------------------------------------------- D5

def test_restore_score_restores_score_values_characterization() -> None:
    """D5: un rescore avvenuto durante la dispute viene scartato dal restore, anche se
    rendeva il fact non ammissibile (services.py:694-706)."""
    session = _fresh_session()
    try:
        _seeded_score(session)
        before = _score(session)
        original = (before.site_confidence, before.temporal_confidence, before.graph_confidence,
                    before.score, before.accepted, before.tier)
        _dispute(session, "site-b")
        services.upsert_score(session, {
            "device_type": "camera", "endpoint": "api.vendor.com", "protocol": "https", "port": 443,
            "site_confidence": 0.1, "temporal_confidence": 0.1, "graph_confidence": 0.0,
            "score": 0.2, "accepted": False,
        })
        session.commit()
        during = _score(session)
        assert during.status == db.STATUS_DISPUTED
        assert (during.score, during.accepted) == (0.2, False)  # premessa: il rescore viene applicato

        services.restore_score(session, *CAMERA)
        session.commit()
        after = _score(session)
        assert (after.site_confidence, after.temporal_confidence, after.graph_confidence,
                after.score, after.accepted, after.tier) == original
        assert after.accepted is True
    finally:
        session.close()
