"""Minimal reproducible checks for hypotheses H1-H6 on the f_s = 0.30 assumption.

Run from the repo root:
    PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 \
        python3 -m pytest analysis_fs/test_hypotheses.py -q -p no:cacheprovider

Read-only with respect to production code: every test imports dib.* and
exercises it on synthetic observations. Registry tests use a throw-away
SQLite file under pytest's tmp_path.

Hypotheses (stated before running, as CLAUDE.md requires):
  H1  C_t has no per-site cap: one adversarial site that reports on every
      day of D_d and floods volume drives C_t toward 1 (sup, never reached
      while an honest site is in ES_d).
  H2  The scorer and the registry derive ES_d from whoever submitted an
      observation of d; nothing checks that the site owns a device of type d.
      So the share is k/(k+h_d), and k=3 vs h_d=4 (3/7 > 5/12) can be admitted.
  H3  At f = 5/12 exactly the bound equals theta; the tie would be admitted
      only if C_t = 1, which needs every observation of d to be adversarial.
  H4  inject_fake_endpoint realises fractions with int(round(N*f)) (banker's
      rounding), so f=0.05 at N=10 gives 0 adversaries; adversaries are drawn
      from all sites, not from ES_d.
  H5  At N=10, k=4 (0.40) cannot be admitted even with maximal C_t (0.64);
      k=5 can.
  H6  Surfaces outside f_s: DIBScorer never feeds openDispute; any two
      sites can revoke a fact without evidence; the eligibility filter
      accepts any FQDN (vendor-cloud) and any global IP on port 53/123.
"""
from __future__ import annotations

import inspect
import os
from datetime import datetime, timedelta, timezone
from fractions import Fraction

import pytest

from dib.core.models import Observation
from dib.evaluation.dib import DIBScorer, ScoringConfig, admit_auto
from dib.evaluation.intent_overlap import classify_core
from dib.experiments.poisoning import inject_fake_endpoint

SELECTED = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2, graph_enabled=False)
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
DEV = "camera"
LEGIT = "api.vendor.example"
FAKE = "evil-c2.example"


def _obs(site: str, fqdn: str, day: int, sec: int = 0, device: str = DEV) -> Observation:
    return Observation(
        site_id=site, device_id=None, device_type=device, fqdn=fqdn, remote_ip=None,
        protocol="https", port=443, timestamp=T0 + timedelta(days=day, seconds=sec),
        source_dataset="analysis_fs", evidence_type="flow",
    )


def _population(h: int, k: int, days: int, flood_per_day: int) -> list[Observation]:
    """h honest sites, one legit observation per day each; k adversaries that
    report FAKE on every day of D_d, flood_per_day times per day each.
    The adversary does NOT need to own the device: it just submits rows."""
    out = [_obs(f"h{i}", LEGIT, d) for i in range(h) for d in range(days)]
    out += [_obs(f"a{j}", FAKE, d, s) for j in range(k) for d in range(days) for s in range(flood_per_day)]
    return out


def _fake_score(obs: list[Observation]):
    return next(s for s in DIBScorer(SELECTED).score(obs) if s.endpoint == FAKE)


# --------------------------------------------------------------------- H1
def test_h1_single_site_flood_drives_ct_towards_one() -> None:
    """H1: no per-site cap on n_de/n_d (dib.py:278 counts all rows; no per-site
    normalisation). One adversary, 4 honest sites, 5 days."""
    cts = []
    for flood in (1, 10, 100, 1000):
        s = _fake_score(_population(h=4, k=1, days=5, flood_per_day=flood))
        cts.append(s.temporal_confidence)
    assert cts == sorted(cts)
    # Expected exactly 0.7 + 0.3*n_a/(n_a+n_h); first draft of this test used
    # "> 0.999", a miscomputation of mine (true value 0.99880), see REPORT.md.
    assert cts[0] == pytest.approx(0.7 + 0.3 * 5 / 25)
    assert cts[-1] == pytest.approx(0.7 + 0.3 * 5000 / 5020)
    # Sup is not attained in exact arithmetic while honest rows exist.
    n_h, n_a = 4 * 5, 1000 * 5
    assert Fraction(7, 10) + Fraction(3, 10) * Fraction(n_a, n_a + n_h) < 1


# --------------------------------------------------------------------- H2
def test_h2_scorer_accepts_k3_vs_h4_with_flood() -> None:
    """H2 (scorer): k/(k+h)=3/7=0.4286 > 5/12. Needed C_t >= (0.65-0.6*3/7)/0.4
    = 0.98214, i.e. fr >= 0.9405, i.e. n_adv >= 15.8 * n_h. flood=22/day: 330 vs 20."""
    s = _fake_score(_population(h=4, k=3, days=5, flood_per_day=22))
    assert s.eligible_sites == 7 and s.supporting_sites == 3
    assert s.accepted and s.score >= 0.65


def test_h2_k3_vs_h5_never_accepted_even_with_large_flood() -> None:
    """Control: 3/8 = 0.375 < 5/12, sup = 0.625 < 0.65."""
    s = _fake_score(_population(h=5, k=3, days=5, flood_per_day=500))
    assert not s.accepted and s.score < 0.625


def test_h2_registry_accepts_unowned_device_type(tmp_path) -> None:
    """H2 (registry): record_observation upserts any site_id (services.py:73)
    and stores any device_type string (services.py:92); recompute_admission
    scores straight from those rows (services.py:263-266). Three brand-new
    sites that never owned a 'camera' join ES_camera and stage FAKE."""
    import dib.registry.db as db
    from dib.registry import services

    os.environ["DIB_DATABASE_URL"] = f"sqlite:///{tmp_path / 'reg.db'}"
    db._engine = None
    db._SessionLocal = None
    session = db.get_session()
    try:
        def put(site, fqdn, day, sec=0):
            services.record_observation(session, {
                "site_id": site, "device_id": None, "device_type": DEV, "fqdn": fqdn,
                "remote_ip": None, "protocol": "https", "port": 443,
                "timestamp": T0 + timedelta(days=day, seconds=sec),
                "source_dataset": "analysis_fs", "evidence_type": "flow",
            })
        for i in range(4):
            for d in range(5):
                put(f"h{i}", LEGIT, d)
        for j in range(3):
            for d in range(5):
                for s in range(22):
                    put(f"newcomer{j}", FAKE, d, s)
        session.commit()
        verdict = services.recompute_admission(session, DEV, FAKE, "https", 443)
        assert verdict is not None and verdict.eligible_sites == 7
        assert verdict.accepted
        stored = services.upsert_score(session, {
            "device_type": DEV, "endpoint": FAKE, "protocol": "https", "port": 443,
            "site_confidence": 0.0, "temporal_confidence": 0.0, "graph_confidence": 0.0,
            "score": 0.0, "accepted": False,
        }, trust_client_verdict=False)
        assert stored.accepted  # registry recomputation stages it
    finally:
        session.close()
        db._engine = None
        db._SessionLocal = None


# --------------------------------------------------------------------- H3
def test_h3_exact_five_twelfths_tie_unreachable_with_honest_rows() -> None:
    """N=12, k=5, h=7. In float, 0.6*(5/12)+0.4*1.0 == 0.65 (tie admitted by
    dib.py:47 'score >= theta'), but C_t == 1.0 requires fr == 1.0, i.e.
    n_h/M below ~1e-16. With realistic floods the score stays below theta."""
    assert 0.6 * (5 / 12) + 0.4 * 1.0 == 0.65
    assert admit_auto(0.65, 0.65, "vendor-cloud", supporting_sites=5, min_reporting_sites=2)
    for flood in (10, 100, 1000):
        s = _fake_score(_population(h=7, k=5, days=3, flood_per_day=flood))
        assert s.site_confidence == 5 / 12
        assert s.score < 0.65 and not s.accepted


# --------------------------------------------------------------------- H4
@pytest.mark.parametrize("f,expected", [(0.05, 0), (0.1, 1), (0.2, 2), (0.3, 3), (0.4, 4), (0.5, 5),
                                        (0.15, 2), (0.25, 2), (0.35, 4), (0.45, 4)])
def test_h4_rounded_pseudo_site_count(f: float, expected: int) -> None:
    """poisoning.py:24 int(round(len(sites)*f)): Python banker's rounding."""
    base = [_obs(f"site-{i:04d}", LEGIT, 0) for i in range(10)]
    poisoned = inject_fake_endpoint(base, f, fake_fqdn=FAKE, seed=0)
    assert len({o.site_id for o in poisoned if o.fqdn == FAKE}) == expected


def test_h4_adversaries_drawn_from_all_sites_not_es_d() -> None:
    """poisoning.py:23-25 samples from every site; a device present at only 2
    of 10 sites gets effective share 2/2 for some seeds at nominal f=0.3."""
    base = [_obs(f"site-{i:04d}", LEGIT, 0, device="common") for i in range(10)]
    base += [_obs(f"site-{i:04d}", LEGIT, 0, device="rare") for i in range(2)]
    full_cover = 0
    for seed in range(200):
        poisoned = inject_fake_endpoint(base, 0.3, fake_fqdn=FAKE, seed=seed)
        mal_rare = {o.site_id for o in poisoned if o.fqdn == FAKE and o.device_type == "rare"}
        full_cover += len(mal_rare) == 2
    # Hypergeometric P(both rare sites among 3 of 10) = C(8,1)/C(10,3) = 8/120.
    assert 0 < full_cover < 40


# --------------------------------------------------------------------- H5
def test_h5_n10_k4_rejected_k5_admitted_under_max_ct() -> None:
    k4 = _fake_score(_population(h=6, k=4, days=5, flood_per_day=500))
    assert not k4.accepted and k4.score < 0.64
    k5 = _fake_score(_population(h=5, k=5, days=5, flood_per_day=5))
    assert k5.accepted  # 0.30 + 0.4*(0.7+0.3*125/150) = 0.68


# --------------------------------------------------------------------- H6
def test_h6a_scorer_never_receives_open_dispute() -> None:
    """dib.py:297-303 calls admit_auto without open_dispute (default False,
    dib.py:26); DIBScorer.score has no dispute input. The registry gates on
    status instead (services.py:439, query_score requires STATUS_ACTIVE)."""
    assert "open_dispute" not in inspect.signature(DIBScorer.score).parameters
    src = inspect.getsource(DIBScorer.score)
    assert "open_dispute" not in src


def test_h6b_two_sites_without_evidence_revoke_admitted_fact(tmp_path) -> None:
    """dispute_score (services.py:615-667) needs no observation from the
    disputer and upserts unknown sites (services.py:643). Two colluding sites
    revoke regardless of f_s: an availability, not integrity, surface."""
    import dib.registry.db as db
    from dib.registry import services

    os.environ["DIB_DATABASE_URL"] = f"sqlite:///{tmp_path / 'reg.db'}"
    db._engine = None
    db._SessionLocal = None
    session = db.get_session()
    try:
        for i in range(4):
            for d in range(5):
                services.record_observation(session, {
                    "site_id": f"h{i}", "device_id": None, "device_type": DEV, "fqdn": LEGIT,
                    "remote_ip": None, "protocol": "https", "port": 443,
                    "timestamp": T0 + timedelta(days=d), "source_dataset": "analysis_fs",
                    "evidence_type": "flow",
                })
        stored = services.upsert_score(session, {
            "device_type": DEV, "endpoint": LEGIT, "protocol": "https", "port": 443,
            "site_confidence": 0.0, "temporal_confidence": 0.0, "graph_confidence": 0.0,
            "score": 0.0, "accepted": False,
        }, trust_client_verdict=False)
        assert stored.accepted
        services.dispute_score(session, DEV, LEGIT, "https", 443, site_id="stranger1")
        after = services.dispute_score(session, DEV, LEGIT, "https", 443, site_id="stranger2")
        assert after.status == services.STATUS_REVOKED
        assert services.query_score(session, "h0", DEV, LEGIT, "https", 443) is None
    finally:
        session.close()
        db._engine = None
        db._SessionLocal = None


def test_h6c_eligibility_accepts_any_fqdn_and_global_ip_on_53_123() -> None:
    """intent_overlap.py:101-109: any FQDN -> vendor-cloud; any global IP on
    53/123 -> dns/ntp. Attacker-controlled names and masqueraded ports pass."""
    assert classify_core("evil-c2.example", "https", 443) == "vendor-cloud"
    assert classify_core("192.88.99.11", "udp", 53) == "dns"
    assert classify_core("192.88.99.11", "udp", 123) == "ntp"
    assert classify_core("192.88.99.11", "https", 443) == "other"
