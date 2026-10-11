"""Defaults of the fan-out concurrency and the opt-in keep-alive pass-through (docs/audit/62, decision 2026-10-12). PRE-REGISTRATION: written before the change.
Why: the shipped compose used concurrency 8 and the library default was 1 (sequential): at `degraded` the sequential default costs ~6x (docs/audit/60 s.2, 62), and a
cap below N_SITES makes the last sites wait for a slot (head-of-line). Decision: the default cap is min(N_SITES, 16); the compose generator follows the same rule;
DIB_DIST_FANOUT_CONCURRENCY=1 still gives the historical sequential path (the in-process harness now sets 1 unless a test says otherwise, so the existing tests keep
their meaning).
Hypotheses (falsification = any assertion failing):
 D-1  service default cap = min(N_SITES, 16): 10 -> 10, 3 -> 3, 40 -> 16; an explicit value wins; 1 -> no executor;
 D-2  generate_compose.py default cap = min(N_SITES, 16) (N_SITES 10 -> 10, 20 -> 16); explicit env wins;
 D-3  generate_compose.py passes DIB_DIST_FANOUT_KEEPALIVE / DIB_DIST_FANOUT_WARM_INTERVAL to the EVIDENCE service only when they are set in the generator's environment; unset -> absent.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from _dist_harness import make_cluster  # noqa: F401

DIST = Path(__file__).resolve().parents[2] / "src" / "dib" / "registry" / "distributed"
UNSET = {"DIB_DIST_FANOUT_CONCURRENCY": None}


@pytest.mark.parametrize("n,expected", [(10, 10), (3, 3), (40, 16)])
def test_d1_service_default(make_cluster, n, expected):
    c = make_cluster(n_sites=n, env=UNSET) if n <= 10 else make_cluster(n_sites=n, env=UNSET)
    assert c.evidence_mod.FANOUT_CONCURRENCY == expected
    assert (c.evidence_mod._get_fanout_executor() is None) == (expected == 1)


def test_d1_explicit_wins(make_cluster):
    c = make_cluster(n_sites=10, env={"DIB_DIST_FANOUT_CONCURRENCY": "1"})
    assert c.evidence_mod.FANOUT_CONCURRENCY == 1 and c.evidence_mod._get_fanout_executor() is None
    c = make_cluster(n_sites=10, env={"DIB_DIST_FANOUT_CONCURRENCY": "4"})
    assert c.evidence_mod.FANOUT_CONCURRENCY == 4


def _generate(**env) -> str:
    base = {"PATH": "/usr/bin:/bin"}
    return subprocess.run([sys.executable, str(DIST / "generate_compose.py")], env={**base, **env}, capture_output=True, text=True, check=True).stdout


def _evidence_block(text: str) -> str:
    return text.split("  site-0:")[0]


def test_d2_generator_default_cap():
    assert "DIB_DIST_FANOUT_CONCURRENCY=10\n" in _evidence_block(_generate())
    assert "DIB_DIST_FANOUT_CONCURRENCY=16\n" in _evidence_block(_generate(DIB_DIST_N_SITES="20"))
    assert "DIB_DIST_FANOUT_CONCURRENCY=3\n" in _evidence_block(_generate(DIB_DIST_FANOUT_CONCURRENCY="3"))


def test_d3_keepalive_pass_through():
    off = _generate()
    assert "KEEPALIVE" not in off and "WARM_INTERVAL" not in off
    on = _generate(DIB_DIST_FANOUT_KEEPALIVE="1", DIB_DIST_FANOUT_WARM_INTERVAL="2")
    ev, rest = _evidence_block(on), on.split("  site-0:", 1)[1]
    assert "DIB_DIST_FANOUT_KEEPALIVE=1" in ev and "DIB_DIST_FANOUT_WARM_INTERVAL=2" in ev
    assert "KEEPALIVE" not in rest
