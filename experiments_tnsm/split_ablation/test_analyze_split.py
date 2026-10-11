"""Tests of analyze_split.py (audit 53) on SYNTHETIC aggregates only; no real data. Hypotheses (before the module; falsification = any assertion failing):
 T-1  the parametric copy at (w=0.7, alpha=0.6, beta=0.4, theta=0.65, m=2, gate=True) equals moniotr_cross_lab.score_keys(gate=True, quorum=True) on
      random aggregates (the validity condition of audit 53);
 T-2  w moves the admission exactly where C_t = w*d + (1-w)*f crosses the threshold (crafted key: d=0.2, f=0: admitted iff w >= 0.625);
 T-3  Cs-only (alpha=1, beta=0) at theta 0.65 with two sources equals {|S_e| >= 2, eligible class} (audit 53 H-S2), and Ct-only is a subset of V0 (H-S3);
 T-4  an ineligible class is never admitted (gate), whatever the score; m = 3 with two sources admits nothing.
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "scripts"))
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from moniotr_cross_lab import Aggregate, score_keys  # noqa: E402
import analyze_split as S  # noqa: E402

D0 = date(2026, 1, 1)


def add(agg, site, key, day_offsets, count_per_day):
    for off in day_offsets:
        day = D0 + timedelta(days=off)
        agg.endpoints[key].add(site)
        agg.site_endpoint_days[(site, key)].add(day)
        agg.site_endpoint_date_counts[(site, key, day)] += count_per_day
        agg.device_sites[key[0]].add(site)
        agg.site_device_days[(site, key[0])].add(day)
        agg.site_device_date_counts[(site, key[0], day)] += count_per_day


def random_agg(seed):
    rng = random.Random(seed)
    agg = Aggregate()
    for d in ("d1", "d2"):
        for e in range(6):
            host = ("x%d.vendor.example" % e) if e < 5 else "192.168.1.9"
            key = (d, host, "https", 443)
            for s in ("A", "B", "C"):
                if rng.random() < 0.6:
                    add(agg, s, key, rng.sample(range(10), rng.randint(1, 10)), rng.randint(1, 20))
        # make sure every site observes the device somewhere
        for s in ("A", "B", "C"):
            add(agg, s, (d, "base.vendor.example", "https", 443), range(10), 5)
    return agg


@pytest.mark.parametrize("seed", range(25))
def test_t1_default_reproduces_score_keys(seed):
    agg = random_agg(seed)
    for sources in ({"A", "B"}, {"A", "C"}, {"B", "C"}):
        want, _ = score_keys(agg, sources, gate=True, quorum=True)
        assert S.score_keys_variant(agg, sources) == want


def test_t2_split_crossing():
    agg = Aggregate()
    key = ("d", "x.vendor.example", "https", 443)
    for s in ("A", "B"):
        add(agg, s, key, [0, 1], 1)                                   # endpoint on 2 of 10 days
        add(agg, s, ("d", "base.vendor.example", "https", 443), range(10), 1000)   # keeps f ~ 0
    got = {w: key in S.score_keys_variant(agg, {"A", "B"}, w=w) for w in (0.5, 0.6, 0.62, 0.63, 0.7, 1.0)}
    assert got[0.5] is False and got[0.6] is False and got[0.62] is False
    assert got[0.63] is True and got[0.7] is True and got[1.0] is True


@pytest.mark.parametrize("seed", range(25))
def test_t3_cs_only_subset_of_quorum_class(seed):
    agg = random_agg(seed)
    src = {"A", "B"}
    assert S.score_keys_variant(agg, src, alpha=1.0, beta=0.0) <= S.quorum_class_set(agg, src)


def test_t3_cs_only_equals_quorum_when_both_sources_host_the_device():
    agg = random_agg(3)
    src = {"A", "B"}
    assert S.score_keys_variant(agg, src, alpha=1.0, beta=0.0) == S.quorum_class_set(agg, src)


def test_t3_ct_only_subset_of_v0():
    for seed in range(40):
        agg = random_agg(seed)
        src = {"A", "B"}
        assert S.score_keys_variant(agg, src, alpha=0.0, beta=1.0) <= S.score_keys_variant(agg, src)


def test_t4_gate_and_quorum():
    agg = random_agg(5)
    out = S.score_keys_variant(agg, {"A", "B"})
    assert all(k[1] != "192.168.1.9" for k in out)
    assert S.score_keys_variant(agg, {"A", "B"}, m=3) == set()


def test_ablation_parameters_are_used():
    """Ct-only must admit a key with C_t >= 0.65 and reject one with C_t = 0.14 that V0 admits (guards alpha/beta being applied)."""
    agg = Aggregate()
    hi, lo = ("d", "hi.vendor.example", "https", 443), ("d", "lo.vendor.example", "https", 443)
    for s in ("A", "B"):
        add(agg, s, hi, range(10), 1)                                 # every day: d = 1
        add(agg, s, lo, [0, 1], 1)                                    # d = 0.2
        add(agg, s, ("d", "base.vendor.example", "https", 443), range(10), 1000)
    src = {"A", "B"}
    ct = S.score_keys_variant(agg, src, alpha=0.0, beta=1.0)
    v0 = S.score_keys_variant(agg, src)
    assert hi in ct and lo not in ct and lo in v0 and hi in v0
    cs = S.score_keys_variant(agg, src, alpha=1.0, beta=0.0)
    assert hi in cs and lo in cs
