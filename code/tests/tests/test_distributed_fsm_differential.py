"""Differential, step-by-step check of I1-I3 on the in-process distributed service (audit 61 obiettivo 3, a4).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-12).
Nessun codice di produzione e' modificato; i mutanti sono COPIE di service.py in tmp_path
(``make_source_copy``). S = service.py a 6e6d352 (sha256 0501b383...3d42a64), righe come in
docs/audit/63_fsm_specifica.md.

Cosa fa. Per ogni seed (``random.Random(seed)``, seed 0..39) un cluster di 3 siti e 2 fatti riceve
25 eventi scelti a caso fra: stage, commit, local_revoke, local_restore (sito s, fatto f),
dispute (segnalante site-r, fatto f), restore (f), down(s) / up(s) (l'evidence non raggiunge s;
s raggiunge l'evidence e serve il suo operatore, come FakeNet.down e come `unreachable` in
DIB_AE.tla:41-46), reconcile(s). Gli eventi sono SEQUENZIALI: le finestre di audit 64 (b3) non
sono esercitate qui. Dopo ogni evento si leggono /state di ogni (sito, fatto) e /export_mud di
ogni sito, e si controllano:
  I1      un (s, f) diventa active solo se l'evento e' commit(s, f) con risposta 200
          (main_wip.tex:338).
  I2      un evento locale a s (stage, commit, local_revoke, local_restore) lascia invariati
          (state, origin, last_applied_seq) di tutti gli altri siti (main_wip.tex:339).
  I3-d    dopo una dispute applicata su f, ogni sito raggiungibile con un record di f e' disputed
          o revoked e non esporta f (main_wip.tex:340, "at reachable sites during fan-out").
  I3-r    dopo un restore di f, nessun sito raggiungibile che era active resta active (la
          restaurazione richiede un nuovo commit).
  I3-v    un record revoked/local resta revoked/local finche' l'evento non e' local_restore dello
          stesso (s, f) (veto preservato da dispute, restore e reconcile; main_wip.tex:334, :340).
  EXP     per ogni (s, f): f e' nell'export di s se e solo se lo stato e' active (Eq. exportable).
  CONV    a fine sequenza, dopo up e reconcile di tutti i siti: ogni record non revoked/local ha
          lo stato che corrisponde allo stato dell'evidence (active->monitor-only o active per un
          commit successivo, disputed->disputed, revoked->revoked) e last_applied_seq = fanout_seq.
  ORACLE  stato di ogni (s, f) uguale a quello di un oracolo Python che implementa la tabella
          "sito" e "evidence" di audit 63 sez. 1-2 (quorum 1).

Ipotesi
H-D1  Sul codice reale: nessuna violazione di I1, I2, I3-d, I3-r, I3-v, EXP, CONV e nessuna
      differenza con l'oracolo, su 40 seed x 25 passi. Falsificata da una qualunque violazione
      (riportata con seed, passo ed evento).
H-D2  Mutante M1 (guardia di provenienza del restore S:482 sostituita da `if False:`): almeno un
      seed produce una violazione di I3-v. Falsificata se M1 sopravvive a tutti i seed per I3-v.
H-D3  Mutante M2 (target del restore S:948 = DECISION_ACTIVE invece di MONITOR_ONLY): almeno un
      seed produce una violazione di I1. Falsificata se M2 sopravvive a tutti i seed per I1.
H-D4  (non vacuita') Sui 40 seed del codice reale: almeno 5 restore applicati mentre qualche sito
      aveva un record revoked/local del fatto, almeno 5 dispute applicate con un sito down, almeno
      5 reconcile che cambiano almeno un record, almeno 10 commit riusciti. Se no, H-D1 e' vuota e
      il test fallisce.
Il generatore non e' adattivo: seed, numero di passi e pesi sono fissati qui e non si cambiano
dopo aver visto gli esiti.

ESITO della prima esecuzione (2026-10-12, docs/audit/64 sez. 2): H-D1, H-D2, H-D3 confermate;
H-D4 FALSIFICATA (restore con veto locale 1 < 5, reconcile che cambiano un record 3 < 5): H-D1 e'
quindi debole sul percorso del veto. Durata ~72 s per test, ~290 s per i quattro: il file
supererebbe il timeout 300 s della suite documentata, percio' gira solo con DIB_FSM_DIFF=1 (le
asserzioni non cambiano).

PRE-REGISTRAZIONE 2 (scritta dopo l'esito sopra e PRIMA di eseguire i test D5-D7). Generatore
PESATO, fissato qui: pesi WEIGHTS sotto, 40 passi, seed 100..119 (nuovi, non riusati).
H-D5  Sul codice reale con il generatore pesato: nessuna violazione (come H-D1) E soglie di non
      vacuita' di H-D4 raggiunte (>= 5 restore con veto locale, >= 5 dispute con un sito down,
      >= 5 reconcile che cambiano un record, >= 10 commit riusciti). Falsificata da una
      violazione o da una soglia mancata.
H-D6  M1 rilevato da I3-v in almeno 3 seed distinti dei 20 (con il generatore uniforme: 1 seed su
      40, seed 32 passo 22). Falsificata se < 3.
H-D7  M2 rilevato da I1 in almeno 3 seed distinti dei 20. Falsificata se < 3.
"""
from __future__ import annotations

import os
import random
from collections import Counter

import pytest

from _dist_harness import DEVICE, make_cluster, make_source_copy  # noqa: F401  (fixture)

N_SITES = 3
FACTS = ("a.vendor.com", "b.vendor.com")
SEEDS = range(40)
STEPS = 25
EVENTS = ("stage", "commit", "local_revoke", "local_restore", "dispute", "restore", "down", "up", "reconcile")
# Pre-registrazione 2 (generatore pesato), stesso ordine di EVENTS.
WEIGHTS = (3, 3, 2, 1, 2, 2, 1, 1, 2)
SEEDS_W = range(100, 120)
STEPS_W = 40

pytestmark = pytest.mark.skipif(
    os.environ.get("DIB_FSM_DIFF") != "1",
    reason="~5 min: run with DIB_FSM_DIFF=1 (docs/audit/64 sez. 2)",
)

M1 = ('        if event_type == "restore" and state == DECISION_REVOKED and origin == ORIGIN_LOCAL:',
      "        if False:")
M2 = ('        _fan_out(score_id, new_seq, "restore", DECISION_MONITOR_ONLY)',
      '        _fan_out(score_id, new_seq, "restore", DECISION_ACTIVE)')


# ------------------------------------------------------------------ oracle (audit 63 sez. 1-2, Q=1)
class Oracle:
    def __init__(self) -> None:
        self.status = {f: "active" for f in FACTS}
        self.disputed_by = {f: None for f in FACTS}
        self.seq = {f: 0 for f in FACTS}
        self.rows: dict[tuple[int, str], dict | None] = {(s, f): None for s in range(N_SITES) for f in FACTS}
        self.down: set[int] = set()
        self.outbox: dict[tuple[int, str], tuple[int, str, str]] = {}

    def _apply(self, s, f, seq, ev, target) -> None:
        row = self.rows[(s, f)]
        if row is None or seq <= row["last_applied_seq"]:
            return
        if row["state"] == "revoked" and row["origin"] == "local":
            row["last_applied_seq"] = seq
            return
        row.update(state=target, origin="fanout" if target == "revoked" else None, last_applied_seq=seq)

    def _fan_out(self, f, ev, target) -> None:
        for s in range(N_SITES):
            if s in self.down:
                old = self.outbox.get((s, f))
                if old is None or self.seq[f] > old[0]:
                    self.outbox[(s, f)] = (self.seq[f], ev, target)
            else:
                self._apply(s, f, self.seq[f], ev, target)

    def step(self, ev, s, f, r) -> None:
        row = self.rows.get((s, f))
        if ev == "stage":
            if self.status[f] == "active" and row is None:
                self.rows[(s, f)] = {"state": "monitor-only", "origin": None, "last_applied_seq": self.seq[f]}
        elif ev == "commit":
            if self.status[f] == "active" and row is not None and row["state"] == "monitor-only":
                row["state"] = "active"
        elif ev == "local_revoke":
            if row is not None and (row["state"] in ("monitor-only", "active", "disputed")
                                    or (row["state"], row["origin"]) == ("revoked", "fanout")):
                row.update(state="revoked", origin="local")
        elif ev == "local_restore":
            if (self.status[f] == "active" and row is not None
                    and (row["state"], row["origin"]) == ("revoked", "local")):
                row.update(state="monitor-only", origin=None)
        elif ev == "dispute":
            if self.status[f] == "active":
                self.status[f], self.disputed_by[f] = "disputed", f"site-{r}"
                self.seq[f] += 1
                self._fan_out(f, "dispute", "disputed")
            elif self.status[f] == "disputed" and f"site-{r}" != self.disputed_by[f]:
                self.status[f] = "revoked"
                self.seq[f] += 1
                self._fan_out(f, "revoke", "revoked")
        elif ev == "restore":
            if self.status[f] in ("disputed", "revoked"):
                self.status[f], self.disputed_by[f] = "active", None
                self.seq[f] += 1
                self._fan_out(f, "restore", "monitor-only")
        elif ev == "down":
            self.down.add(s)
        elif ev == "up":
            self.down.discard(s)
        elif ev == "reconcile":
            for g in FACTS:
                item = self.outbox.pop((s, g), None)
                if item is not None:
                    self._apply(s, g, *item)
            current = {"active": ("restore", "monitor-only"), "disputed": ("dispute", "disputed"),
                       "revoked": ("revoke", "revoked")}
            for g in FACTS:
                if self.seq[g] > 0:
                    self._apply(s, g, self.seq[g], *current[self.status[g]])


# ------------------------------------------------------------------ driver and checks
def _exported(c, s) -> set[str]:
    doc = c.sites[s].get("/export_mud", params={"device_type": DEVICE}).json()
    names = set()
    for acl in doc["ietf-access-control-list:access-lists"]["acl"]:
        for ace in acl["aces"]["ace"]:
            names.add(ace["matches"]["ipv4"].get("ietf-acldns:dst-dnsname"))
    return names


def _snapshot(c, sids) -> tuple[dict, dict]:
    states = {(s, f): c.state(s, sids[f]) for s in range(N_SITES) for f in FACTS}
    exports = {s: _exported(c, s) for s in range(N_SITES)}
    return states, exports


def _do(c, ev, s, f, r):
    """Run one event through the real HTTP handlers; return the status code (or None)."""
    if ev == "stage":
        return c.stage(s, f).status_code
    if ev == "commit":
        return c.commit(s, f).status_code
    if ev == "local_revoke":
        return c.local_revoke(s, f).status_code
    if ev == "local_restore":
        return c.local_restore(s, f).status_code
    if ev == "dispute":
        resp = c.dispute(f"site-{r}", f)
        return 200 if resp.json().get("applied") else 204  # 204 = accepted but no transition
    if ev == "restore":
        return c.restore(f).status_code
    if ev == "down":
        c.net.down.add(s)
        return None
    if ev == "up":
        c.net.down.discard(s)
        return None
    if ev == "reconcile":
        return c.reconcile(s).status_code
    raise AssertionError(ev)


def run_sequence(c, seed: int, coverage: Counter | None = None, *, steps: int = STEPS,
                 weights: tuple | None = None) -> list[tuple]:
    """Return the violations [(kind, seed, step, event, detail)]; empty = all checks hold."""
    rng = random.Random(seed)
    sids = {f: c.seed(f) for f in FACTS}
    oracle = Oracle()
    violations: list[tuple] = []
    before, exp_before = _snapshot(c, sids)
    for step in range(steps):
        ev = rng.choice(EVENTS) if weights is None else rng.choices(EVENTS, weights=weights)[0]
        s, f, r = rng.randrange(N_SITES), rng.choice(FACTS), rng.randrange(N_SITES)
        down_before = set(c.net.down)
        c.net.calls.clear()  # FakeNet.MAX_CALLS is a per-test anti-runaway cap, not a per-sequence one
        code = _do(c, ev, s, f, r)
        oracle.step(ev, s, f, r)
        after, exp_after = _snapshot(c, sids)
        tag = (seed, step, (ev, s, f, r), code)

        def bad(kind, detail):
            violations.append((kind, *tag, detail))

        for (t, g), st in after.items():
            prev = before[(t, g)]
            # I1
            if st and st["state"] == "active" and not (prev and prev["state"] == "active"):
                if not (ev == "commit" and (t, g) == (s, f) and code == 200):
                    bad("I1", (t, g, prev, st))
            # I2
            if ev in ("stage", "commit", "local_revoke", "local_restore") and t != s and st != prev:
                bad("I2", (t, g, prev, st))
            # I3-v
            if prev and (prev["state"], prev["origin"]) == ("revoked", "local"):
                if not (ev == "local_restore" and (t, g) == (s, f)):
                    if not st or (st["state"], st["origin"]) != ("revoked", "local"):
                        bad("I3-v", (t, g, prev, st))
            # EXP
            if (g in exp_after[t]) != bool(st and st["state"] == "active"):
                bad("EXP", (t, g, st, sorted(exp_after[t])))
            # ORACLE
            if st != oracle.rows[(t, g)]:
                bad("ORACLE", (t, g, st, oracle.rows[(t, g)]))
        if ev == "dispute" and code == 200:
            for t in range(N_SITES):
                st = after[(t, f)]
                if t not in down_before and st and (st["state"] not in ("disputed", "revoked") or f in exp_after[t]):
                    bad("I3-d", (t, f, st))
        if ev == "restore" and code == 200:
            for t in range(N_SITES):
                prev, st = before[(t, f)], after[(t, f)]
                if t not in down_before and prev and prev["state"] == "active" and st["state"] == "active":
                    bad("I3-r", (t, f, prev, st))
        if coverage is not None:
            coverage[f"{ev}:{code}"] += 1
            if ev == "restore" and code == 200 and any(
                    before[(t, f)] and (before[(t, f)]["state"], before[(t, f)]["origin"]) == ("revoked", "local")
                    for t in range(N_SITES)):
                coverage["restore_with_local_veto"] += 1
            if ev == "dispute" and code == 200 and down_before:
                coverage["dispute_with_site_down"] += 1
            if ev == "reconcile" and after != before:
                coverage["reconcile_changed"] += 1
        before, exp_before = after, exp_after
    # CONV
    c.net.down.clear()
    for t in range(N_SITES):
        c.net.calls.clear()
        c.reconcile(t)
    final, _ = _snapshot(c, sids)
    expected = {"active": ("monitor-only", "active"), "disputed": ("disputed",), "revoked": ("revoked",)}
    for f in FACTS:
        ev_state = c.evidence_score(f)
        for t in range(N_SITES):
            st = final[(t, f)]
            if st is None or (st["state"], st["origin"]) == ("revoked", "local"):
                continue
            if st["state"] not in expected[ev_state["status"]] or st["last_applied_seq"] != ev_state["fanout_seq"]:
                bad_tag = (seed, "final", ("converge",), None)
                violations.append(("CONV", *bad_tag, (t, f, st, ev_state)))
    return violations


def _run_all(make_cluster, source=None, coverage=None, *, seeds=SEEDS, steps=STEPS, weights=None) -> list[tuple]:
    out = []
    for seed in seeds:
        c = make_cluster(n_sites=N_SITES, source=source)
        out += run_sequence(c, seed, coverage, steps=steps, weights=weights)
        c.close()
    return out


def test_d1_real_code_keeps_i1_i3_at_every_step(make_cluster) -> None:
    violations = _run_all(make_cluster)
    assert violations == [], violations[:10]


@pytest.mark.xfail(strict=True, reason="H-D4 falsificata 2026-10-12: restore con veto locale 1 < 5, "
                   "reconcile che cambiano un record 3 < 5 (docs/audit/64 sez. 2)")
def test_d4_generator_is_not_vacuous(make_cluster) -> None:
    coverage: Counter = Counter()
    _run_all(make_cluster, coverage=coverage)
    print(dict(sorted(coverage.items())))
    assert coverage["restore_with_local_veto"] >= 5, coverage
    assert coverage["dispute_with_site_down"] >= 5, coverage
    assert coverage["reconcile_changed"] >= 5, coverage
    assert coverage["commit:200"] >= 10, coverage


def test_d2_mutant_m1_restore_ignores_local_veto_is_caught_by_i3v(make_cluster, tmp_path) -> None:
    source = make_source_copy(tmp_path, [M1], name="service_m1.py")
    kinds = Counter(v[0] for v in _run_all(make_cluster, source=source))
    print(dict(kinds))
    assert kinds["I3-v"] >= 1, kinds


def test_d3_mutant_m2_restore_reactivates_is_caught_by_i1(make_cluster, tmp_path) -> None:
    source = make_source_copy(tmp_path, [M2], name="service_m2.py")
    kinds = Counter(v[0] for v in _run_all(make_cluster, source=source))
    print(dict(kinds))
    assert kinds["I1"] >= 1, kinds


# ------------------------------------------------------------------ pre-registrazione 2 (generatore pesato)
def _run_weighted(make_cluster, source=None, coverage=None) -> list[tuple]:
    return _run_all(make_cluster, source, coverage, seeds=SEEDS_W, steps=STEPS_W, weights=WEIGHTS)


def test_d5_weighted_real_code_keeps_i1_i3_and_is_not_vacuous(make_cluster) -> None:
    coverage: Counter = Counter()
    violations = _run_weighted(make_cluster, coverage=coverage)
    print(dict(sorted(coverage.items())))
    assert violations == [], violations[:10]
    assert coverage["restore_with_local_veto"] >= 5, coverage
    assert coverage["dispute_with_site_down"] >= 5, coverage
    assert coverage["reconcile_changed"] >= 5, coverage
    assert coverage["commit:200"] >= 10, coverage


def _seeds_with(violations, kind) -> set[int]:
    return {v[1] for v in violations if v[0] == kind}


def test_d6_weighted_m1_caught_by_i3v_in_three_seeds(make_cluster, tmp_path) -> None:
    source = make_source_copy(tmp_path, [M1], name="service_m1w.py")
    seeds = _seeds_with(_run_weighted(make_cluster, source=source), "I3-v")
    print(sorted(seeds))
    assert len(seeds) >= 3, seeds


def test_d7_weighted_m2_caught_by_i1_in_three_seeds(make_cluster, tmp_path) -> None:
    source = make_source_copy(tmp_path, [M2], name="service_m2w.py")
    seeds = _seeds_with(_run_weighted(make_cluster, source=source), "I1")
    print(sorted(seeds))
    assert len(seeds) >= 3, seeds
