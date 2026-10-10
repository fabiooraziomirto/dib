"""Tests of the automatic /reconcile trigger of distributed/service.py (audit 05, part 1).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-10, branch
fix-reconcile-trigger-fanout). Sul codice attuale falliranno tutti i test che usano il
trigger (non esiste): vanno riportati cosi' come sono. DIST = code/src/dib/registry/
distributed/service.py. Piano: docs/audit/05_reconcile_trigger_fanout.md (piano approvato).

Problema. Nessuno chiama /reconcile nel servizio (niente lifespan, timer o thread): la
staleness di un sito non ha limite superiore.

Contratto d'interfaccia (cio' che l'implementazione deve esporre; i test lo assumono)
------------------------------------------------------------------------------------
Env, letti all'import come gli altri parametri di DIST:
  DIB_DIST_RECONCILE_INTERVAL   T in secondi, default 0 = nessun trigger (nemmeno all'avvio)
  DIB_DIST_RECONCILE_JITTER     J in secondi (se T>0 e non impostato: 0.1*T)
  DIB_DIST_RECONCILE_TIMEOUT    timeout httpx di _reconcile_once, default 5.0
  DIB_DIST_RECONCILE_LOCK_TIMEOUT  attesa massima della route sulla lock, default 60.0
                                (0 = non attendere); alla scadenza la route risponde 503
Modulo-sito: RECONCILE_INTERVAL, RECONCILE_JITTER, RECONCILE_TIMEOUT,
  RECONCILE_LOCK_TIMEOUT, _trigger (None se T == 0), _reconcile_lock (threading.Lock),
  _reconcile_once() -> (first_pull, rounds); /reconcile ne e' un involucro che non cambia
  risposta ne' header.
_trigger (_ReconcileTrigger): attributi liberamente assegnabili `clock` (callable ->
  secondi) e `rng` (oggetto con .uniform(a, b)); `interval`, `jitter`, `next_due`
  (None finche' non e' armato), `thread`. Metodi senza sleep:
  arm()    : next_due = clock() + rng.uniform(0, J)   (ritardo iniziale)
  tick()   : se next_due e' None chiama arm(); se clock() < next_due -> False. Altrimenti
             prende la lock con acquire(blocking=False): se occupata ripianifica
             next_due = clock() + min(1.0, T) e torna False. Se libera chiama
             `self._run()` (= _reconcile_once), rilascia, e torna True ("un tentativo e'
             stato fatto"). Successo: next_due = clock() + T + rng.uniform(0, J).
             Errore (httpx.HTTPError / sqlite3.Error): non propaga; fallimenti consecutivi
             n -> next_due = clock() + min(1.0*2**(n-1), min(T, 30.0)) + rng.uniform(0, J).
  start()/stop(): thread daemon che attende Event con timeout max(next_due-clock(), 0.05)
             e chiama tick(); stop() lo ferma e fa join; un secondo stop() e' innocuo.
FastAPI(lifespan=...): avvia il trigger del sito (se esiste) all'ingresso e lo ferma
  all'uscita; all'uscita chiude anche l'executor del fan-out (vedi il file F).
I test non avviano mai thread reali tranne T7/T9 (start/stop con clock finto, che non
avanza: il thread attende solo e stop() lo sveglia).

Ipotesi (attese e criterio di falsificazione)
---------------------------------------------
H-T1  Con l'evidence irraggiungibile all'avvio il tick non propaga eccezioni, ripianifica
      con backoff 1 s, 2 s (rng al minimo) e, tornata l'evidence, il sito converge senza
      nessuna chiamata HTTP a POST /reconcile. Falsificata se resta monitor-only, se il
      tick solleva, o se compare una chiamata /reconcile.
H-T2  I tentativi riusciti distano in [T, T+J]; due siti con rng diversi hanno ritardo
      iniziale diverso (niente sincronia dopo `compose up`).
H-T3  Single-flight: un tick durante un run in corso non fa un secondo GET /pending, ritorna
      False e ripianifica a now + min(1, T). La lock e' occupata durante il run; la route
      /reconcile con LOCK_TIMEOUT 0 e lock occupata risponde 503, a lock libera 200.
H-T4  Con T = 0: nessun trigger, nessun thread, nessun GET /pending automatico.
H-T5  Limite di staleness T + J + 2*d_run per OGNI fase del periodo e per l'arrivo avverso
      (evento accodato subito dopo la snapshot del GET di un run in corso): nel caso avverso
      con GET che dura D il ritardo e' esattamente T + J + 2D, quindi sopra T + J + d_run
      (d_run = durata del run mancato) e sotto T + J + 2*d_run_max. Falsificata se il
      ritardo osservato supera il limite o se il caso avverso non lo sfiora (test non
      discriminante). Una chiamata manuale che tiene la lock sposta il run di al massimo
      la sua durata + min(1, T).
H-T6  Default: nessun trigger, parametri ai valori dichiarati.
H-T7  start()/stop() (anche via lifespan) non lasciano thread vivi; stop() ripetuto e'
      innocuo.
H-T8  Il timeout dei GET/ack di _reconcile_once e' DIB_DIST_RECONCILE_TIMEOUT.
H-W   (_characterization) Un'eccezione tra la transazione di stato (DIST:500) e _fan_out
      (DIST:502) lascia l'evento in nessuna outbox: il sito non converge mai con /reconcile.
      Il limite T5 vale quindi solo per eventi in outbox. Falsificata se dopo i reconcile
      il sito converge. (Estensione futura, non implementata: anti-entropia che confronta
      fanout_seq di /scores con last_applied_seq.)
H-NC  Controllo negativo su COPIA del sorgente: con il corpo del tick neutralizzato
      (`self._run()` -> `pass`) il sito non converge; il messaggio d'errore riporta stato
      monitor-only e l'evento ancora in outbox. L'ancora deve comparire esattamente una
      volta in DIST (nessun docstring o commento con quel testo).
"""
from __future__ import annotations

import random
import threading

import pytest
from fastapi.testclient import TestClient

from _dist_harness import FakeClock, make_cluster, make_source_copy  # noqa: F401

T, J, D = 10.0, 2.0, 3.0
ENV = {"DIB_DIST_RECONCILE_INTERVAL": str(T), "DIB_DIST_RECONCILE_JITTER": str(J)}
TRIGGER_ANCHOR = "self._run()"


class FixedRng:
    """uniform(a, b) returns a ("lo") or b ("hi"): the two extremes of the jitter."""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def uniform(self, a: float, b: float) -> float:
        return a if self.mode == "lo" else b


def _pending_dispute(c):
    """Site 1 unreachable FROM evidence (direct delivery fails) -> one queued dispute for it."""
    sid = c.seed()
    c.stage(0)
    c.stage(1)
    c.net.down.add(1)
    assert c.dispute("rep-a").json() == {"applied": True}
    assert [p["seq"] for p in c.pending(1)] == [1]
    return sid


def _obs(c, sid, site=1):
    return {"state": c.state(site, sid), "pending": c.pending(site)}


def _script_gets(c, clock, d, per_get=None, path="/pending/site-1"):
    """Every GET of `path` takes `d` fake seconds (clock advance AFTER the evidence answered,
    so an event queued by per_get(n) arrives just after the snapshot); per_get(n) runs first."""
    state = {"n": 0}

    def hook():
        state["n"] += 1
        if per_get is not None:
            per_get(state["n"])
        clock.advance(d)
        c.net.after("GET", path, hook)

    c.net.after("GET", path, hook)
    return state


# ------------------------------------------------------------------ T1 startup

def test_t1_startup_with_evidence_down_then_up_converges_without_external_reconcile(make_cluster) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = _pending_dispute(c)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    trig = c.trigger(1)
    c.net.evidence_down = True
    trig.arm()
    assert trig.next_due == pytest.approx(clock.now())  # initial delay U(0, J) with rng at its minimum
    assert c.tick(1) is True  # an attempt was made; the failure must not propagate
    assert c.state(1, sid)["state"] == "monitor-only"
    assert trig.next_due == pytest.approx(clock.now() + 1.0)  # first backoff
    clock.advance(0.5)
    assert c.tick(1) is False
    clock.advance(0.5)
    assert c.tick(1) is True  # second failure
    assert trig.next_due == pytest.approx(clock.now() + 2.0)  # backoff doubles
    c.net.evidence_down = False
    c.net.down.discard(1)
    clock.advance(2.0)
    assert c.tick(1) is True
    assert c.state(1, sid)["state"] == "disputed", _obs(c, sid)
    assert c.pending(1) == []
    assert [call for call in c.net.calls if call.path == "/reconcile"] == []  # no external /reconcile


def test_t1b_initial_delay_is_bounded_by_the_jitter(make_cluster) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = _pending_dispute(c)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("hi"))
    trig = c.trigger(1)
    trig.arm()
    assert trig.next_due == pytest.approx(clock.now() + J)
    assert c.tick(1) is False
    clock.advance(J - 0.01)
    assert c.tick(1) is False
    clock.advance(0.01)
    assert c.tick(1) is True
    assert c.state(1, sid)["state"] == "disputed"


# ------------------------------------------------------------------ T2 periodic + jitter

def test_t2_successful_runs_are_spaced_by_T_plus_jitter(make_cluster) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    clock = FakeClock()
    c.install_clock(1, clock, random.Random(7))
    c.trigger(1).arm()
    step, starts = 0.25, []
    for _ in range(int(300 / step)):
        clock.advance(step)
        if c.tick(1):
            starts.append(clock.now())
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    assert len(starts) >= 15, starts
    assert all(T - 1e-9 <= g <= T + J + step + 1e-9 for g in gaps), (T, J, gaps)
    assert max(gaps) - min(gaps) > 0.1, "jitter has no effect: all gaps identical"


def test_t2b_exact_schedule_at_the_jitter_extremes(make_cluster) -> None:
    for mode, extra in (("lo", 0.0), ("hi", J)):
        c = make_cluster(n_sites=2, env=ENV)
        clock = FakeClock()
        c.install_clock(1, clock, FixedRng(mode))
        trig = c.trigger(1)
        trig.arm()
        clock.advance(J)
        assert c.tick(1) is True
        assert trig.next_due == pytest.approx(clock.now() + T + extra)
        clock.advance(T + extra - 0.01)
        assert c.tick(1) is False
        clock.advance(0.01)
        assert c.tick(1) is True


def test_t2c_sites_with_different_rng_do_not_start_together(make_cluster) -> None:
    c = make_cluster(n_sites=3, env=ENV)
    clock = FakeClock()
    due = []
    for site, seed in ((0, 1), (1, 2), (2, 3)):
        c.install_clock(site, clock, random.Random(seed))
        c.trigger(site).arm()
        due.append(c.trigger(site).next_due)
    assert len(set(due)) == 3, due
    assert all(clock.now() <= d <= clock.now() + J for d in due), due


# ------------------------------------------------------------------ T3 single flight

def test_t3_tick_during_a_run_is_skipped_and_rescheduled(make_cluster) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = _pending_dispute(c)
    c.net.down.discard(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    trig, mod = c.trigger(1), c.site_mods[1]
    trig.arm()
    seen = {}

    def inside_run():
        gets = [x for x in c.net.calls if x.method == "GET" and x.path == "/pending/site-1"]
        seen["gets_before"] = len(gets)
        seen["nested_tick"] = trig.tick()
        seen["gets_after"] = len([x for x in c.net.calls if x.method == "GET" and x.path == "/pending/site-1"])
        seen["next_due"] = trig.next_due - clock.now()
        seen["lock_free"] = mod._reconcile_lock.acquire(blocking=False)  # T3b: no threads
        if seen["lock_free"]:
            mod._reconcile_lock.release()

    c.net.after("GET", "/pending/site-1", inside_run)
    assert c.tick(1) is True
    assert seen["nested_tick"] is False
    assert seen["gets_after"] == seen["gets_before"] == 1, seen  # no second GET /pending
    assert seen["next_due"] == pytest.approx(min(1.0, T)), seen
    assert seen["lock_free"] is False, "the lock must be held during a run"
    assert mod._reconcile_lock.acquire(blocking=False), "the lock must be released after the run"
    mod._reconcile_lock.release()
    assert c.state(1, sid)["state"] == "disputed"


def test_t3c_route_returns_503_when_the_lock_is_busy_and_200_when_free(make_cluster) -> None:
    c = make_cluster(n_sites=2, env={**ENV, "DIB_DIST_RECONCILE_LOCK_TIMEOUT": "0"})
    _pending_dispute(c)
    c.net.down.discard(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    c.trigger(1).arm()
    seen = {}
    c.net.after("GET", "/pending/site-1", lambda: seen.setdefault("status", c.reconcile(1).status_code))
    assert c.tick(1) is True
    assert seen["status"] == 503  # the route runs on another thread of the TestClient: no deadlock
    r = c.reconcile(1)
    assert r.status_code == 200 and r.json() == {"reconciled": 0}  # already converged by the tick


# ------------------------------------------------------------------ T4 / T6 off by default

def test_t4_interval_zero_means_no_automatic_reconcile(make_cluster) -> None:
    c = make_cluster(n_sites=2, env={"DIB_DIST_RECONCILE_INTERVAL": "0", "DIB_DIST_RECONCILE_JITTER": "2"})
    sid = _pending_dispute(c)
    before = set(threading.enumerate())
    assert c.trigger(1) is None
    with TestClient(c.site_mods[1].app):  # lifespan runs: it must not start anything
        assert set(threading.enumerate()) == before
    assert [x for x in c.net.calls if x.method == "GET" and x.path.startswith("/pending")] == []
    assert c.state(1, sid)["state"] == "monitor-only"


def test_t6_defaults_keep_the_current_behaviour(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    mod = c.site_mods[1]
    assert mod.RECONCILE_INTERVAL == 0 and c.trigger(1) is None
    assert mod.RECONCILE_TIMEOUT == 5.0 and mod.RECONCILE_LOCK_TIMEOUT == 60.0
    assert c.evidence_mod.FANOUT_CONCURRENCY == 1


# ------------------------------------------------------------------ T5 staleness bound

@pytest.mark.parametrize("phase", [0.0, 0.25, 0.5, 0.75, 0.999])
def test_t5_staleness_is_bounded_for_every_phase_of_the_period(make_cluster, monkeypatch, phase) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = c.seed()
    c.stage(0)
    c.stage(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("hi"))
    trig, mod = c.trigger(1), c.site_mods[1]
    applied_at: list[float] = []
    real = mod._apply_fanout_row
    monkeypatch.setattr(mod, "_apply_fanout_row", lambda *a, **k: (applied_at.append(clock.now()), real(*a, **k))[1])
    _script_gets(c, clock, D)
    runs: list[tuple[float, float]] = []

    def step(dt=0.25):
        clock.advance(dt)
        start = clock.now()
        if c.tick(1):
            runs.append((start, clock.now()))

    trig.arm()
    while not runs:
        step()
    target = runs[0][1] + phase * (T + J)  # event arrives `phase` of a period after the end of run 0
    while clock.now() + 0.25 <= target:
        step()
    clock.advance(target - clock.now())
    c.net.down.add(1)
    assert c.dispute("rep-a").json() == {"applied": True}
    t_event = clock.now()
    limit = t_event + 10 * (T + J + 4 * D)
    while c.state(1, sid)["state"] != "disputed" and clock.now() < limit:
        step()
    d_run_max = max(end - start for start, end in runs)
    delay = applied_at[0] - t_event
    assert c.state(1, sid)["state"] == "disputed", (T, J, d_run_max, _obs(c, sid))
    assert delay <= T + J + 2 * d_run_max + 1e-9, f"staleness {delay} > T+J+2*d_run: T={T} J={J} d_run={d_run_max}"


def test_t5_adversarial_arrival_just_after_the_get_of_a_run_in_progress(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = c.seed()
    c.stage(0)
    c.stage(1)
    c.net.down.add(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("hi"))
    trig, mod = c.trigger(1), c.site_mods[1]
    applied_at: list[float] = []
    real = mod._apply_fanout_row
    monkeypatch.setattr(mod, "_apply_fanout_row", lambda *a, **k: (applied_at.append(clock.now()), real(*a, **k))[1])
    event_at: list[float] = []

    def per_get(n):
        if n == 1:  # the GET of run A already answered (empty): the event arrives right after the snapshot
            assert c.dispute("rep-a").json() == {"applied": True}
            event_at.append(clock.now())

    _script_gets(c, clock, D, per_get)
    trig.arm()
    runs: list[tuple[float, float]] = []
    for _ in range(400):
        clock.advance(0.25)
        start = clock.now()
        if c.tick(1):
            runs.append((start, clock.now()))
        if applied_at:
            break
    assert applied_at, ("never applied", T, J, _obs(c, sid))
    delay = applied_at[0] - event_at[0]
    d_run_missed = D  # run A lasted one GET of D fake seconds
    d_run_max = max(end - start for start, end in runs)
    msg = f"T={T} J={J} d_run(missed run)={d_run_missed} d_run_max={d_run_max} observed delay={delay}"
    assert delay > T + J + d_run_missed + 1e-9, "adversarial case does not exceed T+J+d_run: " + msg
    assert delay <= T + J + 2 * d_run_max + 1e-9, "bound T+J+2*d_run violated: " + msg
    assert delay == pytest.approx(T + J + 2 * D), msg  # characterization: the case is tight


def test_t5c_manual_call_holding_the_lock_delays_the_run_by_at_most_its_duration(make_cluster) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    sid = _pending_dispute(c)
    c.net.down.discard(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("hi"))
    trig = c.trigger(1)
    trig.arm()
    clock.advance(J)  # the trigger is due now
    t_due = clock.now()
    seen = {}

    def per_get(n):
        if n == 1:
            seen["nested"] = trig.tick()  # due, but a manual call holds the lock
            seen["resched"] = trig.next_due - clock.now()

    _script_gets(c, clock, D, per_get)
    assert c.reconcile(1).json() == {"reconciled": 1}  # the manual call takes 2 GETs of D
    assert seen["nested"] is False and seen["resched"] == pytest.approx(min(1.0, T)), seen
    assert c.state(1, sid)["state"] == "disputed"
    started = None
    for _ in range(40):
        if c.tick(1):
            started = clock.now()
            break
        clock.advance(0.25)
    assert started is not None
    hold = 2 * D
    assert started - t_due <= hold + min(1.0, T) + 1e-9, (started - t_due, hold)


# ------------------------------------------------------------------ T7 / T9 stop

def test_t7_start_and_stop_leave_no_live_thread(make_cluster) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    clock = FakeClock()  # frozen: the thread only waits, stop() wakes it
    c.install_clock(1, clock, FixedRng("hi"))
    trig = c.trigger(1)
    trig.start()
    assert trig.thread is not None and trig.thread.is_alive()
    trig.stop()
    assert not trig.thread.is_alive()
    assert trig.thread not in threading.enumerate()
    trig.stop()  # idempotent


def test_t9_lifespan_starts_and_stops_the_trigger(make_cluster) -> None:
    c = make_cluster(n_sites=2, env=ENV)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("hi"))
    trig = c.trigger(1)
    with TestClient(c.site_mods[1].app):
        assert trig.thread is not None and trig.thread.is_alive()
    assert not trig.thread.is_alive()
    assert [x for x in c.net.calls if x.path.startswith("/pending")] == []  # frozen clock: never due


# ------------------------------------------------------------------ T8 timeout

def test_t8_reconcile_timeout_is_a_parameter(make_cluster) -> None:
    c = make_cluster(n_sites=2, env={**ENV, "DIB_DIST_RECONCILE_TIMEOUT": "7.5"})
    _pending_dispute(c)
    c.net.down.discard(1)
    assert c.reconcile(1).status_code == 200
    ours = [x for x in c.net.calls if x.path.startswith("/pending/site-1")]
    assert len(ours) >= 3  # GET, ack, GET (re-pull)
    assert {x.timeout for x in ours} == {7.5}, [(x.method, x.path, x.timeout) for x in ours]


def test_t8b_default_reconcile_timeout_is_5_seconds(make_cluster) -> None:
    c = make_cluster(n_sites=2)
    _pending_dispute(c)
    c.net.down.discard(1)
    c.reconcile(1)
    assert {x.timeout for x in c.net.calls if x.path.startswith("/pending/site-1")} == {5.0}


# ------------------------------------------------------------------ W (characterization)

def test_w_event_lost_between_state_commit_and_fanout_characterization(make_cluster, monkeypatch) -> None:
    """H-W: crash-like failure between the status transaction (DIST:500) and _fan_out (DIST:502).
    Characterizes a POSSIBLE defect; asserts the hypothesis, not a desired behaviour."""
    c = make_cluster(n_sites=2)
    sid = c.seed()
    c.stage(0)
    c.stage(1)
    real_fan_out = c.evidence_mod._fan_out

    def crash(*args, **kwargs):
        raise RuntimeError("simulated evidence crash between state commit and fan-out")

    monkeypatch.setattr(c.evidence_mod, "_fan_out", crash)
    quiet = TestClient(c.evidence_mod.app, raise_server_exceptions=False)
    r = quiet.post("/dispute", json={**c._fact("api.vendor.com"), "site_id": "rep-a"})
    assert r.status_code == 500
    monkeypatch.setattr(c.evidence_mod, "_fan_out", real_fan_out)
    score = c.evidence_score()
    assert (score["status"], score["fanout_seq"]) == ("disputed", 1)  # the state change was committed
    assert c.pending(0) == [] and c.pending(1) == []  # ...but no event was queued anywhere
    assert c.reconcile(0).json() == {"reconciled": 0} and c.reconcile(1).json() == {"reconciled": 0}
    assert c.state(0, sid)["state"] == "monitor-only" and c.state(1, sid)["state"] == "monitor-only"


# ------------------------------------------------------------------ NC (negative control)

def _trigger_scenario(c):
    sid = _pending_dispute(c)
    c.net.down.discard(1)
    clock = FakeClock()
    c.install_clock(1, clock, FixedRng("lo"))
    c.trigger(1).arm()
    for _ in range(int(4 * (T + J) / 0.5)):
        clock.advance(0.5)
        c.tick(1)
    assert c.state(1, sid)["state"] == "disputed", _obs(c, sid)


def test_trigger_scenario_converges_on_the_real_code(make_cluster) -> None:
    _trigger_scenario(make_cluster(n_sites=2, env=ENV))


def test_negative_control_without_the_tick_body_the_site_does_not_converge(make_cluster, tmp_path) -> None:
    source = make_source_copy(tmp_path, [(TRIGGER_ANCHOR, "pass")])
    c = make_cluster(n_sites=2, env=ENV, source=source)
    with pytest.raises(AssertionError) as lost:
        _trigger_scenario(c)  # setup completes; only the convergence assertion may fail
    message = str(lost.value)
    assert "'state': 'monitor-only'" in message, message
    assert "'event_type': 'dispute'" in message and "'pending': []" not in message, message
