"""Discriminating controls that complete three pre-registered tests (audit 06, point 4).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-10, branch fix-d19).
Verificato solo con py_compile. I test esistenti NON sono modificati: questi li affiancano.
DIST = code/src/dib/registry/distributed/service.py (numeri di riga di 2f4d618).

Perche'
-------
T4b  Il commit 3e61d9e ha indebolito T4 (test_distributed_reconcile_trigger.py:270-278) da
     "nessun thread nuovo" a "nessun thread chiamato dib-*": un thread con un altro nome, o creato
     nel lifespan senza passare da `_trigger`, non verrebbe visto. T4b non guarda i nomi dei
     thread: sostituisce _ReconcileTrigger.start con una spia e conta le chiamate durante il
     lifespan. H-T4b: con T = 0 zero chiamate; con T > 0 almeno una. Controllo negativo su COPIA:
     `if RECONCILE_INTERVAL > 0:` (DIST:483) -> `>= 0`: con T = 0 la spia registra una chiamata,
     messaggio "start() called 1 time(s) with T=0".
T5d  T5c (test_distributed_reconcile_trigger.py:380-407) e' lasco: la chiamata manuale dura
     2*D = 6 s, piu' della ripianificazione min(1, T) = 1 s, quindi il termine min(1, T) del bound
     non viene mai raggiunto. T5d usa GET da 0,25 s: la chiamata manuale dura 0,5 s, il tick
     annidato ripianifica a +1 s dall'istante di scadenza, e il run parte ESATTAMENTE a +1,0 s
     (passo di 0,25 s). H-T5d: started - t_due == min(1, T) = 1,0 (+-1e-9).
F4b  F4 (test_distributed_fanout_parallel.py:224-229) non discrimina: l'executor finto non viene
     mai usato dal codice pre-D11, quindi passa con e senza il pool. F4b ripete lo scenario D12
     `_lost_restore` con cap 8 e in piu' (i) asserisce che l'executor ha eseguito i task di
     entrambi i siti per ciascuno dei 3 eventi (3 x 2 = 6 esecuzioni; fallisce sul codice
     pre-D11, dove sono 0), (ii) ha un controllo negativo su COPIA con ack senza filtro
     (`if req is None:` -> `if True:`, audit 03 §4): la convergenza deve fallire con outbox vuota,
     last_applied_seq 2 e stato revoked. LIMITE dichiarato: l'executor e' inline (FakeExecutor),
     quindi F4b prova che D12 resta chiuso sul percorso del pool, non l'interleaving reale dei
     thread (coperto solo da F6 con executor parcheggiante).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from _dist_harness import FakeClock, make_cluster, make_source_copy  # noqa: F401
from test_distributed_d12_reproducer import _converged, _lost_restore, _observation
from test_distributed_ack_fix import (  # noqa: F401
    REPAIR_ANCHOR,
    _assert_row_survives_first_ack,
    _record_outbox_after_first_ack,
)
from test_distributed_fanout_parallel import FakeExecutor, _install
from test_distributed_reconcile_trigger import D, ENV, FixedRng, J, T, _pending_dispute  # noqa: F401

START_ANCHOR = "if RECONCILE_INTERVAL > 0:"
ACK_ANCHOR = "if req is None:"


# ------------------------------------------------------------------ T4b

def _starts_during_lifespan(c, monkeypatch) -> int:
    mod = c.site_mods[1]
    starts: list[int] = []
    monkeypatch.setattr(mod._ReconcileTrigger, "start", lambda self: starts.append(1))
    with TestClient(mod.app):  # lifespan startup + shutdown
        pass
    return len(starts)


def _assert_no_start_with_t0(c, monkeypatch) -> None:
    n = _starts_during_lifespan(c, monkeypatch)
    assert n == 0, f"start() called {n} time(s) with T=0"


def test_t4b_with_t_zero_the_lifespan_never_starts_a_trigger(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2, env={"DIB_DIST_RECONCILE_INTERVAL": "0", "DIB_DIST_RECONCILE_JITTER": "2"})
    _assert_no_start_with_t0(c, monkeypatch)


def test_t4b_with_t_positive_the_lifespan_starts_the_trigger(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    assert _starts_during_lifespan(c, monkeypatch) >= 1


def test_negative_control_t4b_a_trigger_created_with_t_zero_is_started(make_cluster, monkeypatch, tmp_path) -> None:
    source = make_source_copy(tmp_path, [(START_ANCHOR, "if RECONCILE_INTERVAL >= 0:")])
    c = make_cluster(n_sites=2, env={"DIB_DIST_RECONCILE_INTERVAL": "0"}, source=source)
    with pytest.raises(AssertionError) as started:
        _assert_no_start_with_t0(c, monkeypatch)
    assert "start() called 1 time(s) with T=0" in str(started.value), str(started.value)


# ------------------------------------------------------------------ T5d

def test_t5d_manual_call_shorter_than_the_reschedule_delays_the_run_by_min_1_t(make_cluster) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = _pending_dispute(c)
    c.net.down.discard(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("hi"))
    trig = c.trigger(1)
    trig.arm()
    clock.advance(J)  # the trigger is due now
    t_due = clock.now()
    seen: dict = {}
    state = {"n": 0}

    def hook():  # every GET of site 1 lasts 0.25 fake seconds; the first one also runs a nested tick
        state["n"] += 1
        if state["n"] == 1:
            seen["nested"] = trig.tick()  # due, but the manual call holds the lock
            seen["resched"] = trig.next_due - clock.now()
        clock.advance(0.25)
        c.net.after("GET", "/pending/site-1", hook)

    c.net.after("GET", "/pending/site-1", hook)
    assert c.reconcile(1).json() == {"reconciled": 1}  # two GETs: 0.5 s of hold
    assert seen["nested"] is False and seen["resched"] == pytest.approx(min(1.0, T)), seen
    assert c.state(1, sid)["state"] == "disputed"
    started = None
    for _ in range(40):
        before = clock.now()
        if c.tick(1):
            started = before
            break
        clock.advance(0.25)
    assert started is not None
    assert started - t_due == pytest.approx(min(1.0, T), abs=1e-9), (started - t_due, min(1.0, T))


# ------------------------------------------------------------------ F4b

def test_f4b_d12_lost_restore_with_parallel_fanout_really_uses_the_pool(make_cluster) -> None:
    c = make_cluster(n_sites=2, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"})
    ex = _install(c, FakeExecutor(max_workers=8))
    sid = _lost_restore(c)
    assert _converged(c, sid), _observation(c, sid)
    runs = sorted(s for kind, s in ex.events if kind == "run")
    assert runs == [0, 0, 0, 1, 1, 1], ex.events  # 3 events x 2 sites went through the executor


def _f4b_cluster(make_cluster, source=None):
    c = make_cluster(n_sites=2, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"}, source=source)
    _install(c, FakeExecutor(max_workers=8))
    return c


def test_f4b_ack_keeps_the_row_queued_after_the_first_ack_with_parallel_fanout(make_cluster) -> None:
    c = _f4b_cluster(make_cluster)
    seen = _record_outbox_after_first_ack(c)
    sid = _lost_restore(c)
    _assert_row_survives_first_ack(c, seen, [(sid, 3)])


def test_negative_control_f4b_delete_all_ack_with_parallel_fanout_reintroduces_d12(make_cluster, tmp_path) -> None:
    """Riscritto dopo D19 (audit 06 §3): D19 maschera la mutazione, si discrimina la finestra."""
    source = make_source_copy(tmp_path, [(ACK_ANCHOR, "if True:")])
    c = _f4b_cluster(make_cluster, source)
    seen = _record_outbox_after_first_ack(c)
    sid = _lost_restore(c)
    assert _converged(c, sid), _observation(c, sid)  # masked by D19
    with pytest.raises(AssertionError) as window:
        _assert_row_survives_first_ack(c, seen, [(sid, 3)])
    message = str(window.value)
    assert "'outbox_after_first_ack': []" in message and "'expected': [(" in message, message
    assert "'gets_pending': 2" in message and "'ticks_to_converge': 0" in message, message


def test_negative_control_f4b_delete_all_ack_without_antientropy_reintroduces_d12(make_cluster, tmp_path) -> None:
    source = make_source_copy(tmp_path, [(ACK_ANCHOR, "if True:"), (REPAIR_ANCHOR, "repaired = 0")])
    c = _f4b_cluster(make_cluster, source)
    sid = _lost_restore(c)  # setup completes; only the convergence assertion may fail
    with pytest.raises(AssertionError) as lost:
        assert _converged(c, sid), _observation(c, sid)
    message = str(lost.value)
    assert "'pending': []" in message and "'last_applied_seq': 2" in message and "'state': 'revoked'" in message, message
