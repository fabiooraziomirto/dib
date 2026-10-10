"""Tests for Passo 0 (corrections), Passo 1 controls, Passo 2/3 helpers.

Run from the repo root:
    PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 \
        python3 -m pytest analysis_fs -q -p no:cacheprovider

Hypotheses (stated before running):
  P0.1 Tolerated k, by hand: k < 5h/7 (limit 5/12, strict) and k <= 3h/7 (f_s):
       h=1..8 -> (0,0),(1,0),(2,1),(2,1),(3,2),(4,2),(4,3),(5,3).
  P0.2 Coverage needed for k colluders: h > 7k/5 (5/12) and h >= 7k/3 (f_s);
       k=3 -> h>=5 and h>=7.
  P0.3 h_d=3: two colluders (2/5) stay below 5/12; three (1/2) exceed it.
  P0.4 h_d=2: k=1 has share 1/3 < 5/12 and is blocked by the quorum anyway.
  P0.5 Two sources, one adversarial (cold-start shape): the score can clear
       theta (C_s = 1/2, flood) and only the quorum m=2 rejects.
  P1.x a2_raw_k: k=0 injects nothing; adversaries drawn inside ES_d; k_d capped
       at |ES_d|; on the real-data output, k<=4 at |ES_d|=10 never admitted and
       single-shot k=5 also not admitted (H-A2.3).
  P2   worst_case_real closed form == DIBScorer on a synthetic population.
  P3   mitigations: base == DIBScorer; timestamp-based tenure is forgeable by
       backdating, registration-based tenure zeroes a newcomer's C_t.
"""
from __future__ import annotations

import csv
import math
import sys
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dib.core.models import Observation  # noqa: E402
from dib.evaluation.dib import DIBScorer, ScoringConfig  # noqa: E402

import a2_raw_k  # noqa: E402
import mitigations  # noqa: E402
import worst_case_real  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
CFG = ScoringConfig(alpha=0.6, beta=0.4, gamma=0.0, theta=0.65, min_reporting_sites=2, graph_enabled=False)
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
LIM, FS = Fraction(5, 12), Fraction(3, 10)


def ob(site, fqdn, day, sec=0, device="cam"):
    return Observation(site_id=site, device_id=None, device_type=device, fqdn=fqdn, remote_ip=None,
                       protocol="https", port=443, timestamp=T0 + timedelta(days=day, seconds=sec),
                       source_dataset="t", evidence_type="flow")


def tol(h: int, lim: Fraction, strict: bool) -> int:
    k = 0
    while (Fraction(k + 1, k + 1 + h) < lim) if strict else (Fraction(k + 1, k + 1 + h) <= lim):
        k += 1
    return k


# ------------------------------------------------------------------ Passo 0
def test_p0_1_tolerance_table_by_hand() -> None:
    expected = {1: (0, 0), 2: (1, 0), 3: (2, 1), 4: (2, 1), 5: (3, 2), 6: (4, 2), 7: (4, 3), 8: (5, 3)}
    for h, (k512, kfs) in expected.items():
        assert tol(h, LIM, True) == k512 == math.ceil(Fraction(5 * h, 7)) - 1
        assert tol(h, FS, False) == kfs == math.floor(Fraction(3 * h, 7))


def test_p0_2_coverage_requirement() -> None:
    for k in range(1, 6):
        h512 = min(h for h in range(1, 100) if Fraction(k, k + h) < LIM)
        hfs = min(h for h in range(1, 100) if Fraction(k, k + h) <= FS)
        assert h512 == math.floor(Fraction(7 * k, 5)) + 1  # smallest h > 7k/5
        assert hfs == math.ceil(Fraction(7 * k, 3))  # smallest h >= 7k/3
    assert (min(h for h in range(1, 99) if Fraction(3, 3 + h) < LIM),
            min(h for h in range(1, 99) if Fraction(3, 3 + h) <= FS)) == (5, 7)


def test_p0_3_hd3_statements() -> None:
    assert Fraction(2, 5) < LIM and Fraction(3, 6) >= LIM
    assert Fraction(1, 3) > FS and Fraction(1, 2) > FS  # h_d<=2: one colluder exceeds f_s


def _flood(honest: list[str], adv: list[str], days: int, per_day: int) -> list[Observation]:
    rows = [ob(s, "legit.example", d) for s in honest for d in range(days)]
    rows += [ob(s, "fake.example", d, x) for s in adv for d in range(days) for x in range(per_day)]
    return rows


def _fake(rows):
    return next(s for s in DIBScorer(CFG).score(rows) if s.endpoint == "fake.example")


def test_p0_4_hd2_k1_quorum_blocks() -> None:
    s = _fake(_flood(["h0", "h1"], ["a0"], days=5, per_day=200))
    assert s.site_confidence == pytest.approx(1 / 3)
    assert s.supporting_sites == 1 and not s.accepted
    assert s.score < 0.65  # 0.2 + 0.4*C_t <= 0.6: score alone also rejects at 1/3


def test_p0_5_two_sources_only_quorum_rejects() -> None:
    s = _fake(_flood(["h0"], ["a0"], days=5, per_day=200))
    assert s.site_confidence == 0.5 and s.score >= 0.65
    assert not s.accepted and s.supporting_sites == 1


# ------------------------------------------------------------------ Passo 1
def _sites_population():
    rows = [ob(f"site-{i:04d}", "legit.example", 0, device="common") for i in range(10)]
    rows += [ob(f"site-{i:04d}", "legit.example", 0, device="rare") for i in range(2)]
    return rows


def test_p1_k0_injects_nothing() -> None:
    base = _sites_population()
    poisoned, chosen = a2_raw_k.inject_k_from_es(base, 0, seed=0)
    assert len(poisoned) == len(base) and all(not v for v in chosen.values())


def test_p1_adversaries_inside_es_d_and_capped() -> None:
    base = _sites_population()
    for seed in range(20):
        poisoned, chosen = a2_raw_k.inject_k_from_es(base, 3, seed=seed)
        assert chosen["rare"] == ["site-0000", "site-0001"]  # k_d = min(3, |ES_d|=2)
        assert len(set(chosen["common"])) == 3
        fakes = [o for o in poisoned if o.fqdn == a2_raw_k.FAKE]
        assert {(o.site_id, o.device_type) for o in fakes} == {(s, d) for d, ss in chosen.items() for s in ss}


def _a2_rows():
    path = OUT / "a2_raw_k.csv"
    if not path.exists():
        pytest.skip("run analysis_fs/a2_raw_k.py first")
    return list(csv.DictReader(path.open()))


def test_p1_real_k0_and_k_le4_full_coverage_never_admitted() -> None:
    rows = _a2_rows()
    assert all(r["supporting_sites"] == "0" for r in rows if r["k"] == "0")
    full = [r for r in rows if r["ES_d"] == "10" and int(r["k"]) <= 4]
    assert full and not any(r["admitted"] == "True" for r in full)
    for r in full:
        assert float(r["site_confidence"]) == pytest.approx(int(r["k"]) / 10)


def test_p1_real_k5_single_shot_not_admitted() -> None:
    rows = [r for r in _a2_rows() if r["ES_d"] == "10" and r["k"] == "5"]
    assert rows and not any(r["admitted"] == "True" for r in rows)


# ------------------------------------------------------------------ Passo 2
def test_p2_closed_form_matches_dibscorer() -> None:
    honest = [ob(f"h{i}", "legit.example", d) for i in range(6) for d in range(4)]
    adv = ["h0", "h1", "h2", "h3"]  # insider k=4 of 6
    days = sorted({o.timestamp.date() for o in honest})
    fakes = worst_case_real.fake_rows("cam", adv, days, per_cell=7)
    s = worst_case_real.score_fake(honest, fakes, "cam")
    assert s.score == pytest.approx(worst_case_real.closed_form(Fraction(4, 6), Fraction(len(fakes), len(honest))))
    assert worst_case_real.k_tol_insider(10) == 4 and worst_case_real.k_tol_h2(10) == 7
    assert worst_case_real.k_fs_insider(10) == 3 and worst_case_real.k_fs_h2(10) == 4


# ------------------------------------------------------------------ Passo 3
def test_p3_base_reimplementation_equals_dibscorer() -> None:
    rows = _flood(["h0", "h1", "h2", "h3"], ["a0", "a1", "a2"], days=5, per_day=22)
    rows += [ob("h0", "x.example", 1, device="plug"), ob("h1", "x.example", 2, device="plug")]
    assert mitigations.check_equivalence(rows) > 0


def test_p3_tenure_timestamp_forgeable_registration_not() -> None:
    honest = [ob(f"h{i}", "legit.example", d) for i in range(4) for d in range(30)]
    adv = [ob(f"n{j}", mitigations.FAKE, d, x) for j in range(3) for d in range(30) for x in range(50)]
    pop = honest + adv
    key = ("cam", mitigations.FAKE, "https", 443)
    forged = mitigations.score_variant(pop, tenure_days=7)[key]
    assert forged["temporal_confidence"] > 0.9  # backdated rows -> old first-seen
    as_of = date(2026, 1, 30)
    reg = mitigations.score_variant(pop, tenure_days=7, registration={f"n{j}": as_of for j in range(3)})[key]
    assert reg["temporal_confidence"] == 0.0
    assert reg["score"] == pytest.approx(0.6 * 3 / 7) and not reg["accepted"]
