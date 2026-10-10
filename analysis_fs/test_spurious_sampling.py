"""Tests for Punto A (spurious dates) and Punto B (sampling models).

Hypotheses (stated before running):
  A.1 both UNSW inputs contain exactly 8 rows dated before 2016-09-01, in
      AugustDoorBell (2), NestDropCam (4), WithingsSleepSensor (2);
  A.2 the filtered copies have exactly 8 fewer data lines than the originals;
  A.3 removing the rows never lowers a score (raw breadth: only |D_d| shrinks,
      n_d shrinks by <= 4 rows) and raises it by at most the day-coverage bound
      0.28*(|D_d|/|D_d'| - 1), plus 1e-4 for the frequency term;
  B.1 hypergeometric P(Netatmo covered) with |ES_d|=2 of 10, by hand:
      k=2: 1/45, k=3: 8/120, k=4: 28/210, k=5: 56/252;
  B.2 uniform model, k=3: Netatmo admitted exactly in seeds 1, 6, 13 (original run);
  B.3 Netatmo admitted iff k_d = 2, in both models.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import netatmo_sampling  # noqa: E402
import spurious_dates  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def _csv(name: str) -> list[dict]:
    path = OUT / name
    if not path.exists():
        pytest.skip(f"run the script producing {name} first")
    return list(csv.DictReader(path.open()))


def test_a1_eight_rows_in_three_types_per_file() -> None:
    rows = _csv("spurious_rows.csv")
    per_file = Counter(r["file"] for r in rows)
    assert per_file == {"observations_enriched.csv": 8, "observations_enriched_item1fixed.csv": 8}
    for f in per_file:
        types = Counter(r["device_type"] for r in rows if r["file"] == f)
        assert types == {"AugustDoorBell": 2, "NestDropCam": 4, "WithingsSleepSensor": 2}


def _lines(path: Path) -> int:
    with path.open("rb") as fh:
        return sum(chunk.count(b"\n") for chunk in iter(lambda: fh.read(1 << 24), b""))


@pytest.mark.parametrize("src", [spurious_dates.ENRICHED, spurious_dates.ITEM1])
def test_a2_filtered_copy_drops_exactly_eight(src: Path) -> None:
    dst = OUT / f"{src.stem}_nospurious.csv"
    if not (src.exists() and dst.exists()):
        pytest.skip("data or filtered copy missing")
    assert _lines(src) - _lines(dst) == 8


def test_a2_filter_logic_on_synthetic(tmp_path) -> None:
    src = tmp_path / "in.csv"
    src.write_text("site_id,device_type,timestamp,x\n"
                   "s,d,1970-01-01T00:00:00+00:00,1\n"
                   "s,d,2016-08-31T23:59:59+00:00,2\n"
                   "s,d,2016-09-01T00:00:00+00:00,3\n"
                   "s,d,2017-04-13T19:29:49+00:00,4\n")
    assert spurious_dates.write_filtered_copy(src, tmp_path / "out.csv") == 2
    assert (tmp_path / "out.csv").read_text().count("\n") == 3


@pytest.mark.xfail(strict=True, reason=(
    "Hypothesis A.3 REFUTED by the data (REPORT §11): the 4 endpoints that own "
    "spurious rows lose their own days and drop (min delta -0.066). Assertion "
    "left unchanged; strict=True flags it if it ever starts passing."))
def test_a3_scores_only_rise_within_bound_raw() -> None:
    rows = [r for r in _csv("spurious_dates_impact.csv") if r["config"] == "raw_breadth" and r["delta"] != ""]
    assert rows
    for r in rows:
        d = float(r["delta"])
        assert -1e-9 <= d <= spurious_dates.DELTA_BOUND[r["device_type"]] + 1e-4, r


OWNERS = {("AugustDoorBell", "doorbells.august.com", "tcp", "443"), ("AugustDoorBell", "dmsv2.video-cloud.net", "tcp", "443"),
          ("NestDropCam", "52.87.241.159", "syslog", "443"), ("NestDropCam", "52.87.241.159", "tcp", "443"),
          ("WithingsSleepSensor", "89.30.121.22", "tcp", "5222"), ("WithingsSleepSensor", "89.30.121.26", "syslog", "5222")}


def test_a3_posthoc_non_owner_endpoints_rise_within_bound_raw() -> None:
    """POST-HOC (written after seeing A.3 fail): restricted to endpoints that do
    not own one of the 8 rows (keys from spurious_rows.csv), scores only rise,
    within the day-coverage bound. No admission flips in either config."""
    rows = _csv("spurious_dates_impact.csv")
    for r in rows:
        if r["config"] == "raw_breadth" and r["delta"] != "" and \
                (r["device_type"], r["endpoint"], r["protocol"], r["port"]) not in OWNERS:
            assert -1e-9 <= float(r["delta"]) <= spurious_dates.DELTA_BOUND[r["device_type"]] + 1e-4, r
        assert r["accepted_before"] == r["accepted_after"], r


def test_b1_hypergeometric_by_hand() -> None:
    expected = {1: Fraction(0), 2: Fraction(1, 45), 3: Fraction(8, 120), 4: Fraction(28, 210), 5: Fraction(56, 252)}
    for k, p in expected.items():
        assert netatmo_sampling.p_admissible_uniform(k, 2) == p


def test_b2_uniform_k3_reproduces_original_seeds() -> None:
    rows = _csv("netatmo_sampling.csv")
    seeds = {int(r["seed"]) for r in rows if r["device_type"] == "NetatmoWeatherStation"
             and r["model"] == "uniform" and r["k"] == "3" and r["admitted"] == "True"}
    assert seeds == {1, 6, 13}


def test_b3_netatmo_admitted_iff_both_sites() -> None:
    for r in _csv("netatmo_sampling.csv"):
        if r["device_type"] == "NetatmoWeatherStation":
            assert (r["admitted"] == "True") == (r["k_d"] == "2"), r
