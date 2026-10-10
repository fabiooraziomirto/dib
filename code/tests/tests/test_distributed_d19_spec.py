"""Spec tests for D19 (event lost between the evidence state commit and _fan_out) and for the
visibility of reconcile-trigger failures (audit 06).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-10, branch fix-d19,
da fix-reconcile-trigger-fanout, tag d19-confirmed-pre-fix = 2f4d618). Verificato solo con
py_compile. Sul codice attuale falliranno quasi tutti: vanno riportati cosi' come sono. DIST =
code/src/dib/registry/distributed/service.py (numeri di riga di 2f4d618: commit di stato
DIST:697 / 719, _fan_out DIST:699 / 720, _reconcile_once DIST:425-462, /health del sito
DIST:526-528). Piano approvato: docs/audit/06_d19.md (copia del piano in
/root/.claude/plans/pasted-content-id-7173-contesto-leggi-purrfect-jellyfish.md).

Problema (D19). Una eccezione tra il commit di stato dell'evidence e _fan_out lascia scores
(status, fanout_seq) aggiornato e NESSUNA riga in pending_fanout: /reconcile non recupera
(test_w_..._characterization, test_distributed_reconcile_trigger.py:450). Un 500 da /dispute o
/restore NON implica che lo stato non sia stato modificato; il ritentativo del client non
ripara (S10).

Contratto d'interfaccia (opzione A, anti-entropia basata sullo stato; i test lo assumono)
-----------------------------------------------------------------------------------------
Evidence. GET /pending/{site} restituisce, oltre a "pending" (invariato), la chiave "current":
  per ogni fatto con fanout_seq > 0 un item {score_id, seq, event_type, target_state} derivato
  dallo status (disputed -> dispute/disputed, revoked -> revoke/revoked, active ->
  restore/monitor-only), letto nella STESSA transazione delle righe di outbox.
Sito. _reconcile_once() -> (first_pull, rounds, repaired). Dopo il ciclo dei giri, sull'ultimo
  snapshot, per ogni item di "current" con seq > last_applied_seq locale chiama
  _apply_fanout_row (stessa funzione dell'outbox: eredita guardie di seq, veto locale e origin),
  senza ack. `repaired` = numero di item cosi' passati a _apply_fanout_row. La riparazione gira
  anche con "pending" vuoto. Riga esatta (ancora dei controlli negativi, una sola occorrenza):
      repaired = _repair_from_snapshot(current, applied_seqs)
  /reconcile: corpo JSON invariato {"reconciled": n_primo_pull}; header X-Dib-Reconcile-Repaired
  = repaired (stringa).
Osservabilita'. GET /health del sito: {"status": "ok", "site_id": ..., "reconcile": {
  "enabled": bool, "consecutive_failures": int, "last_error": str | None,
  "seconds_since_last_success": float | None, "thread_alive": bool, "next_due_in": float | None}}.
  Legge solo lo stato in memoria del trigger (nessun DB, nessuna rete). consecutive_failures e'
  _ReconcileTrigger.failures; l'ancora `self.failures += 1` compare una sola volta. last_error e'
  repr() troncato a 200 caratteri. Un WARNING ("reconcile attempt %d failed: %r") per tentativo
  fallito del logger "dib.distributed", mai uno per tick non scaduto; un WARNING con
  "recovered after N failures" al primo successo dopo N fallimenti. _loop avvolge tick() in
  try/except: logga ERROR ("reconcile loop error") e ripianifica next_due >= clock() + 1.0 invece
  di morire.

Ipotesi (attese e criterio di falsificazione)
---------------------------------------------
H-S1   Dopo l'iniezione di W (crash di _fan_out dopo il commit, 500) ogni sito converge SENZA
       alcuna chiamata a POST /reconcile entro T + J + 2*d_run_max dal commit, per ogni fase del
       periodo. Falsificata se un sito resta monitor-only oltre il bound (messaggio: stato del
       sito e outbox vuota).
H-S1b  Lo stesso recupero avviene con /reconcile manuale (header Repaired == "1").
H-S2   Un'eccezione NON HTTP in _deliver_to_site prima dell'inserimento in outbox (cap 1 e cap 8)
       lascia site-1 senza riga in outbox; converge comunque entro il bound.
H-S3   Un sito con veto locale (revoked/origin local) che perde revoke e restore resta
       revoked/local con last_applied_seq pari al seq dell'evidence; nessun ACE.
H-S4   origin: un revoke perso approda a revoked/fanout, un restore perso a monitor-only/None.
H-S5   I1/I3: un sito Active che perde dispute+restore finisce in monitor-only, mai Active.
H-S6   Uno snapshot piu' vecchio di un evento gia' consegnato non regredisce lo stato (Repaired 0).
H-S7   Con l'evidence irraggiungibile nessun recupero e nessuna eccezione; al ritorno recupera.
H-S8   Idempotenza: un secondo reconcile non applica nulla (Repaired 0, nessuna chiamata).
H-S10  Il ritentativo del client dopo il 500 non ripara: /dispute -> applied False, /restore ->
       409, nessun /apply_fanout; solo la riparazione dello stato recupera.
H-S9   Controllo negativo su COPIA: con la riparazione disattivata (`repaired = 0`) S1 fallisce
       perche' il sito resta monitor-only con outbox vuota.
H-O1..O7  Un errore persistente del trigger e' visibile: contatore consecutivo e last_error in
       /health, un WARNING per tentativo, recupero loggato, /health senza DB ne' rete, _loop
       sopravvive a un'eccezione; H-O5 controllo negativo (contatore non incrementato).
"""
from __future__ import annotations

import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from _dist_harness import FakeClock, make_cluster, make_source_copy  # noqa: F401
from test_distributed_fanout_parallel import FakeExecutor, _install
from test_distributed_reconcile_trigger import D, ENV, FixedRng, J, T, _pending_dispute, _script_gets

REPAIR_ANCHOR = "repaired = _repair_from_snapshot(current, applied_seqs)"
FAILURES_ANCHOR = "self.failures += 1"
HEALTH_LOGGER = "dib.distributed"


# ------------------------------------------------------------------ helpers

def _obs(c, sid, site=1):
    return {"state": c.state(site, sid), "pending": c.pending(site)}


def _lose(c, monkeypatch, call) -> None:
    """Same injection as the W test: _fan_out crashes after the state commit (HTTP 500)."""
    real = c.evidence_mod._fan_out

    def crash(*args, **kwargs):
        raise RuntimeError("simulated evidence crash between state commit and fan-out")

    monkeypatch.setattr(c.evidence_mod, "_fan_out", crash)
    try:
        response = call(TestClient(c.evidence_mod.app, raise_server_exceptions=False))
    finally:
        monkeypatch.setattr(c.evidence_mod, "_fan_out", real)
    assert response.status_code == 500, response.text


def _lose_dispute(c, monkeypatch, reporter: str) -> None:
    _lose(c, monkeypatch, lambda q: q.post("/dispute", json={**c._fact("api.vendor.com"), "site_id": reporter}))


def _lose_restore(c, monkeypatch) -> None:
    _lose(c, monkeypatch, lambda q: q.post("/restore", json=c._fact("api.vendor.com")))


def _setup(c, sites=(0, 1)) -> int:
    sid = c.seed()
    for s in sites:
        assert c.stage(s).json()["applied"] is True
    return sid


def _repaired(response) -> str | None:
    return response.headers.get("X-Dib-Reconcile-Repaired")


def _health(c, site=1) -> dict:
    response = c.sites[site].get("/health")
    assert response.status_code == 200
    return response.json()


def _fanout_calls(c) -> list:
    return [call for call in c.net.calls if call.path == "/apply_fanout"]


# ------------------------------------------------------------------ S1 / S9 bound with the trigger

def _w_scenario(c, monkeypatch, phase: float) -> int:
    """W injection, then both sites recover through their trigger only (fake clock, no thread)."""
    sid = _setup(c)
    clocks = [FakeClock(), FakeClock()]
    for s in (0, 1):
        c.install_clock(s, clocks[s], FixedRng("hi"))
        c.trigger(s).arm()
    mod = c.site_mods[1]
    applied_at: list[float] = []
    real = mod._apply_fanout_row
    monkeypatch.setattr(mod, "_apply_fanout_row", lambda *a, **k: (applied_at.append(clocks[1].now()), real(*a, **k))[1])
    _script_gets(c, clocks[1], D)  # every GET /pending of site 1 lasts D fake seconds
    runs: list[tuple[float, float]] = []

    def step(dt=0.25):
        for clock in clocks:
            clock.advance(dt)
        start = clocks[1].now()
        c.tick(0)
        if c.tick(1):
            runs.append((start, clocks[1].now()))

    while not runs:
        step()
    target = runs[0][1] + phase * (T + J)  # the event is committed `phase` of a period after run 0
    while clocks[1].now() + 0.25 <= target:
        step()
    clocks[1].advance(target - clocks[1].now())
    _lose_dispute(c, monkeypatch, "rep-a")
    t_event = clocks[1].now()
    score = c.evidence_score()
    assert (score["status"], score["fanout_seq"]) == ("disputed", 1)  # the state change was committed
    assert c.pending(0) == [] and c.pending(1) == []  # ...and nothing was queued
    limit = t_event + 3 * (T + J + 4 * D)
    while (c.state(1, sid)["state"] != "disputed" or c.state(0, sid)["state"] != "disputed") and clocks[1].now() < limit:
        step()
    assert c.state(1, sid)["state"] == "disputed", (T, J, _obs(c, sid))
    assert c.state(0, sid)["state"] == "disputed", (T, J, _obs(c, sid, 0))
    assert c.state(1, sid)["last_applied_seq"] == 1
    d_run_max = max(end - start for start, end in runs)
    delay = applied_at[0] - t_event
    assert delay <= T + J + 2 * d_run_max + 1e-9, f"staleness {delay} > T+J+2*d_run: T={T} J={J} d_run={d_run_max}"
    assert [call for call in c.net.calls if call.path == "/reconcile"] == []  # no external /reconcile
    return sid


@pytest.mark.parametrize("phase", [0.0, 0.5, 0.999])
def test_w_spec_lost_event_between_commit_and_fanout_is_recovered_within_bound(make_cluster, monkeypatch, phase) -> None:
    _w_scenario(make_cluster(n_sites=2, env=ENV), monkeypatch, phase)


def test_negative_control_without_repair_the_lost_event_is_never_recovered(make_cluster, monkeypatch, tmp_path) -> None:
    source = make_source_copy(tmp_path, [(REPAIR_ANCHOR, "repaired = 0")])
    c = make_cluster(n_sites=2, env=ENV, source=source)
    with pytest.raises(AssertionError) as lost:
        _w_scenario(c, monkeypatch, 0.5)  # setup completes; only the convergence assertion may fail
    message = str(lost.value)
    assert "'state': 'monitor-only'" in message and "'pending': []" in message, message


def test_s1b_manual_reconcile_recovers_the_lost_event(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    _lose_dispute(c, monkeypatch, "rep-a")
    for site in (0, 1):
        r = c.reconcile(site)
        assert r.json() == {"reconciled": 0}
        assert _repaired(r) == "1", (site, r.headers)
        assert c.state(site, sid) == {"state": "disputed", "origin": None, "last_applied_seq": 1}, _obs(c, sid, site)


# ------------------------------------------------------------------ S2 non-HTTP before the outbox insert

@pytest.mark.parametrize("cap", [1, 8])
def test_s2_non_http_failure_before_the_outbox_insert_is_recovered(make_cluster, monkeypatch, cap) -> None:
    c = make_cluster(n_sites=3, env={**ENV, "DIB_DIST_FANOUT_CONCURRENCY": str(cap)})
    if cap > 1:
        _install(c, FakeExecutor(max_workers=cap))
    sid = _setup(c, (0, 1, 2))
    real_post = c.net.post

    def post(url, **kw):
        if url.startswith("http://site1.test") and url.endswith("/apply_fanout"):
            raise RuntimeError("non-HTTP failure in a fan-out task, before the outbox insert")
        return real_post(url, **kw)

    monkeypatch.setattr(httpx, "post", post)
    quiet = TestClient(c.evidence_mod.app, raise_server_exceptions=False)
    assert quiet.post("/dispute", json={**c._fact("api.vendor.com"), "site_id": "rep-a"}).status_code == 500
    monkeypatch.setattr(httpx, "post", real_post)
    assert c.pending(1) == []  # the exception skipped the outbox insert
    assert c.state(0, sid)["state"] == "disputed"  # delivered before the failure
    assert c.state(1, sid)["state"] == "monitor-only"
    clocks = {s: FakeClock() for s in (1, 2)}
    for s, clock in clocks.items():
        c.install_clock(s, clock, FixedRng("hi"))
        c.trigger(s).arm()
    elapsed = 0.0
    while elapsed < 3 * (T + J) and any(c.state(s, sid)["state"] != "disputed" for s in (1, 2)):
        for s, clock in clocks.items():
            clock.advance(0.25)
            c.tick(s)
        elapsed += 0.25
    assert c.state(1, sid)["state"] == "disputed", (cap, _obs(c, sid, 1))
    assert c.state(2, sid)["state"] == "disputed", (cap, _obs(c, sid, 2))
    assert elapsed <= T + J, elapsed  # d_run = 0 on a frozen-duration fake clock


# ------------------------------------------------------------------ S3 / S4 / S5 veto, origin, I1/I3

def test_s3_local_veto_survives_lost_revoke_and_lost_restore(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    assert c.commit(1).status_code == 200 and c.ace_count(1) == 1
    assert c.local_revoke(1).status_code == 200
    _lose_dispute(c, monkeypatch, "rep-a")  # seq 1
    _lose_dispute(c, monkeypatch, "rep-b")  # seq 2, revoke
    r = c.reconcile(1)
    assert _repaired(r) == "1", r.headers
    assert c.state(1, sid) == {"state": "revoked", "origin": "local", "last_applied_seq": 2}, _obs(c, sid)
    _lose_restore(c, monkeypatch)  # seq 3
    r = c.reconcile(1)
    assert _repaired(r) == "1", r.headers
    assert c.state(1, sid) == {"state": "revoked", "origin": "local", "last_applied_seq": 3}, _obs(c, sid)
    assert c.evidence_score()["status"] == "active" and c.ace_count(1) == 0


def test_s4_origin_of_a_repaired_revoke_and_of_a_repaired_restore(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    _lose_dispute(c, monkeypatch, "rep-a")
    _lose_dispute(c, monkeypatch, "rep-b")  # revoke, seq 2
    assert _repaired(c.reconcile(1)) == "1"
    assert c.state(1, sid) == {"state": "revoked", "origin": "fanout", "last_applied_seq": 2}
    _lose_restore(c, monkeypatch)  # seq 3
    assert _repaired(c.reconcile(1)) == "1"
    assert c.state(1, sid) == {"state": "monitor-only", "origin": None, "last_applied_seq": 3}


def test_s5_an_active_site_that_misses_dispute_and_restore_never_stays_or_becomes_active(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    assert c.commit(1).status_code == 200 and c.ace_count(1) == 1
    _lose_dispute(c, monkeypatch, "rep-a")  # seq 1
    _lose_restore(c, monkeypatch)  # seq 2
    assert c.ace_count(1) == 1  # still exposed before the repair: the setup is meaningful
    assert _repaired(c.reconcile(1)) == "1"
    assert c.state(1, sid) == {"state": "monitor-only", "origin": None, "last_applied_seq": 2}
    assert c.ace_count(1) == 0


# ------------------------------------------------------------------ S6 / S7 / S8

def test_s6_a_snapshot_older_than_a_delivered_event_does_not_regress_the_state(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    _lose_dispute(c, monkeypatch, "rep-a")  # seq 1, nobody got it

    def newer_event_delivered_directly():
        assert c.dispute("rep-b").json() == {"applied": True}  # revoke, seq 2, delivered to both sites

    c.net.after("GET", "/pending/site-1", newer_event_delivered_directly)  # after the snapshot (seq 1)
    r = c.reconcile(1)
    assert r.json() == {"reconciled": 0}
    assert _repaired(r) == "0", r.headers  # seq 1 <= last_applied_seq 2: nothing to repair
    assert c.state(1, sid) == {"state": "revoked", "origin": "fanout", "last_applied_seq": 2}


def test_s7_no_recovery_while_evidence_is_down_then_recovery(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = _setup(c)
    _lose_dispute(c, monkeypatch, "rep-a")
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    trig = c.trigger(1)
    trig.arm()
    c.net.evidence_down = True
    assert c.tick(1) is True  # an attempt was made; it must not propagate
    assert c.state(1, sid)["state"] == "monitor-only" and trig.failures == 1
    c.net.evidence_down = False
    clock.advance(1.0)  # first backoff
    assert c.tick(1) is True
    assert c.state(1, sid)["state"] == "disputed", _obs(c, sid)
    assert trig.failures == 0


def test_s8_repair_is_idempotent(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    _setup(c)
    _lose_dispute(c, monkeypatch, "rep-a")
    mod = c.site_mods[1]
    seen: list[tuple] = []
    real = mod._apply_fanout_row
    monkeypatch.setattr(mod, "_apply_fanout_row", lambda *a, **k: (seen.append(a[1:3]), real(*a, **k))[1])
    first = c.reconcile(1)
    assert _repaired(first) == "1" and len(seen) == 1
    second = c.reconcile(1)
    assert _repaired(second) == "0" and len(seen) == 1, seen


# ------------------------------------------------------------------ S10 client retry after a 500

def test_s10_client_retry_after_a_500_dispute_does_not_repair(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    _lose_dispute(c, monkeypatch, "rep-a")
    retry = c.dispute("rep-a")  # the client retries the same report
    assert retry.json() == {"applied": False}  # status already disputed: not a new transition
    assert _fanout_calls(c) == []  # and no fan-out was redone
    assert c.state(1, sid)["state"] == "monitor-only" and c.pending(1) == []
    assert _repaired(c.reconcile(1)) == "1"
    assert c.state(1, sid)["state"] == "disputed"


def test_s10_client_retry_after_a_500_restore_does_not_repair(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2)
    sid = _setup(c)
    assert c.dispute("rep-a").json() == {"applied": True}  # delivered to both sites
    delivered = len(_fanout_calls(c))
    _lose_restore(c, monkeypatch)
    retry = c.restore()
    assert retry.status_code == 409  # status already active
    assert len(_fanout_calls(c)) == delivered  # nothing redelivered
    assert c.state(1, sid)["state"] == "disputed"
    assert _repaired(c.reconcile(1)) == "1"
    assert c.state(1, sid) == {"state": "monitor-only", "origin": None, "last_applied_seq": 2}


# ------------------------------------------------------------------ O: observability of trigger failures

def _attempt_warnings(caplog) -> list:
    return [r for r in caplog.records if r.name == HEALTH_LOGGER and r.levelno == logging.WARNING
            and "failed" in r.getMessage()]


def test_o1_persistent_evidence_outage_is_visible_in_health_and_log(make_cluster, caplog) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    _pending_dispute(c)
    c.net.down.discard(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    c.trigger(1).arm()
    c.net.evidence_down = True
    with caplog.at_level(logging.WARNING, logger=HEALTH_LOGGER):
        for n in range(1, 5):
            clock.advance(T + J)  # past any backoff (capped at min(T, 30))
            assert c.tick(1) is True
            assert c.tick(1) is False  # not due: nothing attempted, nothing logged
            health = _health(c)["reconcile"]
            assert health["consecutive_failures"] == n, f"consecutive_failures {health['consecutive_failures']} != {n}: {health}"
    health = _health(c)
    assert health["status"] == "ok" and health["site_id"] == "site-1"
    health = health["reconcile"]
    assert health["enabled"] is True and health["thread_alive"] is False
    assert "evidence unreachable" in health["last_error"] and "ConnectError" in health["last_error"], health
    assert health["seconds_since_last_success"] is None
    assert len(_attempt_warnings(caplog)) == 4, [r.getMessage() for r in caplog.records]


def test_o2_persistent_non_http_error_is_visible(make_cluster, monkeypatch, caplog) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    _pending_dispute(c)
    c.net.down.discard(1)
    mod = c.site_mods[1]

    def broken(*args, **kwargs):
        raise ValueError("boom-apply")

    monkeypatch.setattr(mod, "_apply_fanout_row", broken)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    c.trigger(1).arm()
    with caplog.at_level(logging.WARNING, logger=HEALTH_LOGGER):
        for _ in range(3):
            clock.advance(T + J)
            assert c.tick(1) is True
    health = _health(c)["reconcile"]
    assert health["consecutive_failures"] == 3, health
    assert "ValueError" in health["last_error"] and "boom-apply" in health["last_error"], health
    assert len(_attempt_warnings(caplog)) == 3


def test_o3_recovery_resets_the_counter_and_is_logged(make_cluster, monkeypatch, caplog) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = _pending_dispute(c)
    c.net.down.discard(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    c.trigger(1).arm()
    c.net.evidence_down = True
    with caplog.at_level(logging.WARNING, logger=HEALTH_LOGGER):
        for _ in range(2):
            clock.advance(T + J)
            assert c.tick(1) is True
        assert _health(c)["reconcile"]["consecutive_failures"] == 2
        c.net.evidence_down = False
        clock.advance(T + J)
        assert c.tick(1) is True
    health = _health(c)["reconcile"]
    assert health["consecutive_failures"] == 0 and health["last_error"] is None, health
    assert health["seconds_since_last_success"] is not None and health["seconds_since_last_success"] >= 0
    assert c.state(1, sid)["state"] == "disputed"
    assert any("recovered after 2 failures" in r.getMessage() for r in caplog.records), [r.getMessage() for r in caplog.records]


def test_o4_health_reports_a_disabled_trigger(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    health = _health(c)
    assert health["status"] == "ok" and health["reconcile"]["enabled"] is False, health
    assert health["reconcile"]["consecutive_failures"] == 0


def test_negative_control_without_failure_counting_the_outage_is_invisible(make_cluster, tmp_path, caplog) -> None:
    source = make_source_copy(tmp_path, [(FAILURES_ANCHOR, "pass")])
    c = make_cluster(n_sites=2, env=ENV, source=source)
    _pending_dispute(c)
    c.net.down.discard(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    c.trigger(1).arm()
    c.net.evidence_down = True
    with pytest.raises(AssertionError) as invisible:
        clock.advance(T + J)
        assert c.tick(1) is True  # setup: the attempt itself still happens
        health = _health(c)["reconcile"]
        n = 1
        assert health["consecutive_failures"] == n, f"consecutive_failures {health['consecutive_failures']} != {n}: {health}"
    message = str(invisible.value)
    assert "consecutive_failures 0 != 1" in message, message


def test_o6_health_does_not_touch_the_database_or_the_network(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    mod = c.site_mods[1]

    def forbidden(*args, **kwargs):
        raise AssertionError("/health touched the site database")

    monkeypatch.setattr(mod._site_db, "run", forbidden)
    calls_before = len(c.net.calls)
    health = _health(c)
    assert health["status"] == "ok" and "reconcile" in health
    assert len(c.net.calls) == calls_before  # no network call either


def test_o7_the_loop_survives_an_exception_and_logs_it(make_cluster, caplog) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    trig = c.trigger(1)
    trig.arm()

    class FakeStop:
        """Event stand-in: wait() returns at once (no real waiting), is_set() flips after n waits."""

        def __init__(self, n):
            self.n, self.waits = n, []

        def is_set(self):
            return len(self.waits) >= self.n

        def wait(self, timeout=None):
            self.waits.append(timeout)
            return False

    ticks: list[int] = []

    def buggy_tick():
        ticks.append(1)
        raise RuntimeError("tick bug")

    trig._stop = FakeStop(3)
    trig.tick = buggy_tick
    with caplog.at_level(logging.ERROR, logger=HEALTH_LOGGER):
        trig._loop()  # called in this thread: it must return normally, not raise
    assert len(ticks) == 3  # survived two exceptions and kept going
    errors = [r for r in caplog.records if r.name == HEALTH_LOGGER and r.levelno == logging.ERROR]
    assert len(errors) == 3 and all("reconcile loop error" in r.getMessage() for r in errors)
    assert trig.next_due - clock.now() >= 1.0 - 1e-9  # rescheduled: no hot loop
