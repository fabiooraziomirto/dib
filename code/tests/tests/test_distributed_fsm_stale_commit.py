"""Stale commit across a whole dispute/restore episode (audit 67 sez. 10, found by TLC v3_n5).

PRE-REGISTRAZIONE. Scritto e committato PRIMA di essere eseguito (2026-10-12, notte).
service.py non e' modificato. S = service.py a 6e6d352. Traccia del modello (v3_n5_export_nofix):
CommitRead (evidence Active, seq 0) -> Dispute (seq 1) -> Restore (seq 2) -> consegna del restore al
sito (monitor-only, last_applied 2) -> CommitWrite: active. La consegna della dispute (seq 1), se
arriva dopo, e' scartata (1 <= 2).

H-S1  Sul codice reale: un /commit la cui lettura dell'evidence precede un intero episodio
      dispute+restore NON porta il record ad active (I3, main_wip.tex:340: "Restoration requires
      fresh local approval"; invariante NoStaleActiveAfterEpisode di DIB_AE.tla). ROSSO previsto:
      la transazione di /commit controlla solo lo stato locale monitor-only (S:528).
H-S2  Sulla copia corretta (test_distributed_fsm_fix_copy.FIXES): stesso scenario, il commit e'
      rifiutato (409) e il record resta monitor-only. Verde previsto (guardia last_applied 2 > seq 0
      letto, e seconda lettura con seq cambiato).
"""
from __future__ import annotations

import pytest

from _dist_harness import make_cluster, make_source_copy  # noqa: F401  (fixture)
from test_distributed_fsm_fix_copy import FIXES

N3 = 3


def _episode_during_commit(c):
    sid = c.seed()
    assert c.stage(0).json()["applied"] is True

    def whole_episode():
        assert c.dispute("site-1").json() == {"applied": True}
        assert c.restore().status_code == 200

    c.net.after("GET", "/scores", whole_episode)
    r = c.commit(0)
    ev = c.evidence_score()
    assert (ev["status"], ev["fanout_seq"]) == ("active", 2)
    return sid, r


@pytest.mark.xfail(strict=True, reason="H-S1 falsificata 2026-10-12: il record diventa active dopo il restore "
                   "(S:528 controlla solo monitor-only; docs/audit/67 sez. 10)")
def test_s1_commit_read_before_a_whole_episode_does_not_activate(make_cluster) -> None:
    c = make_cluster(n_sites=N3)
    sid, _r = _episode_during_commit(c)
    assert c.state(0, sid)["state"] != "active"
    assert c.ace_count(0) == 0


def test_s2_corrected_copy_refuses_the_stale_commit(make_cluster, tmp_path) -> None:
    c = make_cluster(n_sites=N3, source=make_source_copy(tmp_path, FIXES, name="service_fixed_s.py"))
    sid, r = _episode_during_commit(c)
    assert r.status_code == 409
    assert c.state(0, sid)["state"] == "monitor-only"
    assert c.ace_count(0) == 0


def test_s1_observed_stale_commit_activates_after_restore_characterization(make_cluster) -> None:
    """Added AFTER the run (rule of Fase 2): pins the observed defect."""
    c = make_cluster(n_sites=N3)
    sid, r = _episode_during_commit(c)
    assert r.status_code == 200
    assert c.state(0, sid) == {"state": "active", "origin": None, "last_applied_seq": 2}
    assert c.ace_count(0) == 1
