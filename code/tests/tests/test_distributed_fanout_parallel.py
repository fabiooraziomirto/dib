"""Tests of the bounded-concurrency fan-out of distributed/service.py (audit D11, audit 05 part 2).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-10, branch
fix-reconcile-trigger-fanout). Sul codice attuale falliranno i test che usano il nuovo
fan-out (non esiste): vanno riportati cosi' come sono. DIST = code/src/dib/registry/
distributed/service.py.

D11. _fan_out e' sincrono e sequenziale: 3 tentativi per sito, timeout 1,0 s, nessuna pausa,
un sito giu' ritarda tutti quelli che seguono (misurato in-process: N=10, giu' {1..9} ->
28 chiamate, il sito 9 riceve l'evento dopo 27 chiamate). Tempi non misurati qui: si
contano chiamate, ordine e sottomissioni.

Contratto d'interfaccia (ruolo evidence)
----------------------------------------
DIB_DIST_FANOUT_CONCURRENCY (env, default 1) -> FANOUT_CONCURRENCY. Con 1: percorso
sequenziale identico a oggi, nessun executor.
_get_fanout_executor(): None se cap == 1; altrimenti UN solo ThreadPoolExecutor condiviso a
livello di modulo (creato lazy) con max_workers == cap.
_deliver_to_site(i, score_id, seq, event_type, target_state): i 3 tentativi (timeout
1,0 s) verso il sito i, poi, se fallisce, la riga in outbox (DIST:417-426, invariata).
_fan_out: se executor non e' None sottomette un task per sito, nell'ordine dei siti, con
il PRIMO argomento = indice del sito, e poi attende TUTTI i future con future.result()
(anche se uno solleva: rilancia la prima eccezione solo dopo averli attesi tutti).
Righe esatte (ancore del controllo negativo, una sola occorrenza in DIST):
  futures.append(executor.submit(_deliver_to_site, i, score_id, seq, event_type, target_state))
Il lifespan chiude l'executor (shutdown) all'uscita.
I test usano un FakeExecutor sincrono/parcheggiante al posto del pool: nessun thread reale.

Ipotesi
-------
H-F1   Stesse chiamate di oggi: 3 tentativi per sito giu', 1 per sito su, timeout 1,0,
       stesse righe in outbox; contigui per sito (con l'executor inline).
H-F2   Tutti gli N task sono sottomessi prima che il primo sia atteso; l'executor e'
       unico e condiviso (tra chiamate) con max_workers == cap.
H-F3   Un sito giu'/lento non ritarda gli altri: quando il task del sito 1 (parcheggiato)
       parte, i siti 0, 2, 3 sono gia' consegnati; la risposta arriva dopo tutti i task.
H-F1b  Con k siti giu' > cap, il caso peggiore e' ceil(k/cap) ondate da 3 unita' (simulazione
       list-scheduling sull'ordine di sottomissione registrato): N=10, cap=2, giu' {1..5}
       -> 9 contro 15 in serie; il sito sano 6 (dopo i giu') parte a 6, non a 15 -- ma non
       a 0: in una coda FIFO con cap < k i sani accodati dopo aspettano (head-of-line).
       Con cap >= k: 3. La frase "3 s indipendente da k" e' falsa per k > cap.
H-F4   D12 invariata con cap > 1 (scenario _lost_restore).
H-F5   Con il default (cap 1) l'ordine e' quello storico 0 111 222 e non esiste executor.
H-F6   Consegne fuori ordine (seq2 prima di seq1): il vecchio e' scartato da
       seq <= last_applied_seq (DIST:168); stato finale quello di seq2, nessuna riga.
H-F7   L'executor e' unico, ha max_workers == cap e viene chiuso all'uscita del lifespan.
H-F8   Un task che solleva (errore non HTTP): risposta 500 come oggi; con cap > 1 tutti i
       future sono attesi prima di rispondere (nessun task orfano); con cap 1 il giro si
       interrompe come oggi (i siti successivi non sono chiamati).
H-NC   Controllo negativo su COPIA: sottomissione resa sequenziale (si attende il future
       subito dopo la sottomissione) -> H-F3 fallisce con "not delivered while site 1 gated".
"""
from __future__ import annotations

import math
from concurrent.futures import Future

import httpx
import pytest
from fastapi.testclient import TestClient

from _dist_harness import make_cluster, make_source_copy  # noqa: F401
from test_distributed_d12_reproducer import _converged, _lost_restore, _observation

SUBMIT_ANCHOR = "futures.append(executor.submit(_deliver_to_site, i, score_id, seq, event_type, target_state))"


class _Fut(Future):
    def __init__(self, ex, site):
        super().__init__()
        self._ex, self._site, self._thunk = ex, site, None

    def result(self, timeout=None):
        self._ex.events.append(("await", self._site))
        if self._thunk is not None:
            thunk, self._thunk = self._thunk, None
            if self._ex.on_parked:
                self._ex.on_parked()
            thunk()
        return super().result(timeout)


class FakeExecutor:
    """Deterministic stand-in for the shared pool: runs each task inline at submit(), except
    the task of `parked_site`, which runs only when its future is awaited (a 'slow site')."""

    def __init__(self, max_workers=8, parked_site=None, on_parked=None):
        self.max_workers, self.parked_site, self.on_parked = max_workers, parked_site, on_parked
        self.events: list[tuple[str, int]] = []
        self.shutdown_called = False

    @property
    def submitted(self):
        return [s for kind, s in self.events if kind == "submit"]

    def submit(self, fn, *args, **kwargs):
        site = args[0]
        self.events.append(("submit", site))
        fut = _Fut(self, site)

        def run():
            self.events.append(("run", site))
            try:
                fut.set_result(fn(*args, **kwargs))
            except BaseException as exc:  # noqa: BLE001 - mirrors a real worker
                fut.set_exception(exc)

        if site == self.parked_site:
            fut._thunk = run
        else:
            run()
        return fut

    def shutdown(self, *a, **k):
        self.shutdown_called = True


def _install(c, executor):
    c.evidence_mod._get_fanout_executor = lambda: executor
    return executor


def _setup(c) -> int:
    sid = c.seed()
    for s in range(c.n_sites):
        assert c.stage(s).json()["applied"] is True
    return sid


def _simulate(order, down, workers, cost=3):
    """List-scheduling of the recorded submission order on `workers` slots; a task costs 3
    timeout units if its site is down (3 attempts x 1 s), else 0. Returns (makespan, start)."""
    free, start = [0] * workers, {}
    for site in order:
        k = min(range(workers), key=lambda w: free[w])
        start[site] = free[k]
        free[k] += cost if site in down else 0
    return max(free), start


# ------------------------------------------------------------------ F1 / F1b / F2

def test_f1_same_calls_as_the_sequential_fanout_with_down_sites(make_cluster) -> None:
    c = make_cluster(n_sites=10, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"})
    _install(c, FakeExecutor(max_workers=8))
    sid = _setup(c)
    down = {3, 5, 7}
    c.net.down.update(down)
    assert c.dispute("rep-a").json() == {"applied": True}
    for s in range(10):
        calls = c.net.calls_to(s, "/apply_fanout")
        assert len(calls) == (3 if s in down else 1), (s, len(calls))
        assert {x.timeout for x in calls} == {1.0}
        assert (c.pending(s) != []) == (s in down)
        assert c.state(s, sid)["state"] == ("monitor-only" if s in down else "disputed")
    assert c.pending(3) == [{"score_id": sid, "seq": 1, "event_type": "dispute", "target_state": "disputed"}]
    assert len([x for x in c.net.calls if x.path == "/apply_fanout"]) == 16


def test_f2_all_tasks_are_submitted_before_the_first_is_awaited(make_cluster) -> None:
    c = make_cluster(n_sites=10, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"})
    ex = _install(c, FakeExecutor(max_workers=8))
    _setup(c)
    c.dispute("rep-a")
    kinds = [kind for kind, _ in ex.events]
    assert ex.submitted == list(range(10))
    assert "await" in kinds and kinds.index("await") > max(i for i, k in enumerate(kinds) if k == "submit"), ex.events
    assert [s for k, s in ex.events if k == "await"] == list(range(10))  # all awaited


@pytest.mark.parametrize("cap,k,expected_span,expected_start6", [(2, 5, 9, 6), (10, 5, 3, 0), (8, 9, 6, None)])
def test_f1b_waves_when_down_sites_exceed_the_cap(make_cluster, cap, k, expected_span, expected_start6) -> None:
    c = make_cluster(n_sites=10, env={"DIB_DIST_FANOUT_CONCURRENCY": str(cap)})
    ex = _install(c, FakeExecutor(max_workers=cap))
    _setup(c)
    down = set(range(1, k + 1))
    c.net.down.update(down)
    c.dispute("rep-a")
    assert ex.max_workers == cap
    span, start = _simulate(ex.submitted, down, ex.max_workers)
    assert span == 3 * math.ceil(k / cap) == expected_span, (cap, k, span)
    assert sum(3 for _ in down) == 3 * k  # sequential reference: 3 * k
    if expected_start6 is not None:
        assert start[6] == expected_start6, start  # healthy sites queued behind down ones wait (FIFO)
        assert start[6] < 3 * k or cap >= k


# ------------------------------------------------------------------ F3 / NC

def _parked_scenario(c, ex):
    """Site 1 is down and 'slow' (parked); sites 0, 2, 3 are up. Returns the set of sites
    delivered at the moment the site-1 task finally runs."""
    sid = _setup(c)
    c.net.down.add(1)
    snap: dict = {}
    ex.on_parked = lambda: snap.setdefault("delivered", {s for s in range(c.n_sites) if c.state(s, sid)["state"] == "disputed"})
    assert c.dispute("rep-a").json() == {"applied": True}  # answered only after all tasks
    missing = sorted({0, 2, 3} - snap["delivered"])
    assert not missing, f"sites {missing} not delivered while site 1 gated: delivered={sorted(snap['delivered'])}"
    return sid


def test_f3_a_slow_site_does_not_delay_the_others_and_the_response_waits_for_all(make_cluster) -> None:
    c = make_cluster(n_sites=4, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"})
    ex = _install(c, FakeExecutor(max_workers=8, parked_site=1))
    sid = _parked_scenario(c, ex)
    assert sorted(s for k, s in ex.events if k == "run") == [0, 1, 2, 3]  # no orphan task
    assert len(c.pending(1)) == 1 and c.state(1, sid)["state"] == "monitor-only"


def test_negative_control_sequential_submission_delays_the_other_sites(make_cluster, tmp_path) -> None:
    sequential = SUBMIT_ANCHOR + "; futures[-1].result()"
    source = make_source_copy(tmp_path, [(SUBMIT_ANCHOR, sequential)])
    c = make_cluster(n_sites=4, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"}, source=source)
    ex = _install(c, FakeExecutor(max_workers=8, parked_site=1))
    with pytest.raises(AssertionError) as slow:
        _parked_scenario(c, ex)  # setup and dispute complete; only the delivery assertion fails
    message = str(slow.value)
    assert "not delivered while site 1 gated" in message and "[2, 3]" in message, message


# ------------------------------------------------------------------ F4 / F5 / F6 / F7 / F8

def test_f4_d12_lost_restore_still_converges_with_parallel_fanout(make_cluster) -> None:
    c = make_cluster(n_sites=2, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"})
    _install(c, FakeExecutor(max_workers=8))
    sid = _lost_restore(c)
    assert _converged(c, sid), _observation(c, sid)


def test_f5_default_cap_1_keeps_the_historical_order_and_creates_no_executor(make_cluster) -> None:
    c = make_cluster(n_sites=3)
    assert c.evidence_mod.FANOUT_CONCURRENCY == 1 and c.evidence_mod._get_fanout_executor() is None
    _setup(c)
    c.net.down.update({1, 2})
    c.dispute("rep-a")
    order = [call.host for call in c.net.calls if call.path == "/apply_fanout"]
    assert order == ["site0.test"] + ["site1.test"] * 3 + ["site2.test"] * 3


def test_f6_out_of_order_delivery_does_not_regress_the_state(make_cluster) -> None:
    c = make_cluster(n_sites=2, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"})
    ex = _install(c, FakeExecutor(max_workers=8, parked_site=1))
    sid = _setup(c)

    def second_event_overtakes():
        ex.parked_site = None  # the second event is delivered at once; the first one is still parked
        assert c.dispute("rep-b").json() == {"applied": True}  # revoke, seq 2

    ex.on_parked = second_event_overtakes
    assert c.dispute("rep-a").json() == {"applied": True}  # seq 1: site 1 receives it AFTER seq 2
    assert c.state(1, sid) == {"state": "revoked", "origin": "fanout", "last_applied_seq": 2}
    assert c.state(0, sid) == {"state": "revoked", "origin": "fanout", "last_applied_seq": 2}
    assert c.pending(1) == [] and c.pending(0) == []
    seqs = [call.json["seq"] for call in c.net.calls_to(1, "/apply_fanout")]
    assert seqs == [2, 1], seqs  # seq 2 really arrived first


def test_f7_executor_is_shared_and_closed_on_lifespan_exit(make_cluster) -> None:
    c = make_cluster(n_sites=2, env={"DIB_DIST_FANOUT_CONCURRENCY": "4"})
    mod = c.evidence_mod
    ex = mod._get_fanout_executor()
    assert ex is mod._get_fanout_executor()  # one shared executor, not one per call
    assert ex._max_workers == 4
    with TestClient(mod.app):
        pass  # lifespan startup + shutdown
    with pytest.raises(RuntimeError):
        ex.submit(lambda: None)  # shut down: no live pool left behind


def _site2_raises(c, monkeypatch):
    real = c.net.post

    def post(url, **kw):
        if url.startswith("http://site2.test") and url.endswith("/apply_fanout"):
            raise RuntimeError("non-HTTP failure in a fan-out task")
        return real(url, **kw)

    monkeypatch.setattr(httpx, "post", post)


def test_f8_a_raising_task_gives_500_and_all_futures_are_awaited(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=5, env={"DIB_DIST_FANOUT_CONCURRENCY": "8"})
    ex = _install(c, FakeExecutor(max_workers=8))
    _setup(c)
    _site2_raises(c, monkeypatch)
    quiet = TestClient(c.evidence_mod.app, raise_server_exceptions=False)
    r = quiet.post("/dispute", json={**c._fact("api.vendor.com"), "site_id": "rep-a"})
    assert r.status_code == 500
    assert [s for k, s in ex.events if k == "await"] == [0, 1, 2, 3, 4], ex.events  # all awaited
    assert sorted(s for k, s in ex.events if k == "run") == [0, 1, 2, 3, 4]
    assert c.net.calls_to(4, "/apply_fanout") != []  # the failure did not stop the other tasks


def test_f8b_with_cap_1_a_raising_task_interrupts_the_round_as_today(make_cluster, monkeypatch) -> None:
    c = make_cluster(n_sites=5)
    _setup(c)
    _site2_raises(c, monkeypatch)
    quiet = TestClient(c.evidence_mod.app, raise_server_exceptions=False)
    r = quiet.post("/dispute", json={**c._fact("api.vendor.com"), "site_id": "rep-a"})
    assert r.status_code == 500
    assert c.net.calls_to(3, "/apply_fanout") == [] and c.net.calls_to(4, "/apply_fanout") == []
