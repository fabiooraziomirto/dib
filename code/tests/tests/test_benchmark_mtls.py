"""Step 2 before M3/M4 (audit 13 sez. 9, item 6): certificates in the distributed benchmark.

Hypotheses (stated before running, written before the benchmark change):
  B1. With --pki the benchmark routes every operation with the identity audit 13
      sez. 3.3 requires: query/commit -> the worker's site operator at that site;
      attest/dispute -> the same operator at the evidence (reporter = its site);
      restore and seeding -> the consortium admin; contribute stays a no-op. Without
      --pki nothing changes (no identity, plain http).
  B2. Against real mTLS processes (make_dist_pki.py layout, DIB_DIST_TYPE_LIST=1) a
      batch completes with zero unexpected errors.
  B3. An authorization failure is not silent: a 403 is counted as an unexpected error
      (kind "http.403"). Today the benchmark never inspects status codes, so a wrong
      mapping would look like fast successful operations.
Falsification: any assertion below failing. Docker is not used.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from _mtls_ca import requires_openssl
from _mtls_cluster import PkiServices

pytestmark = requires_openssl

CODE = Path(__file__).resolve().parents[2]


@pytest.fixture()
def bench():
    from scripts import distributed_concurrency_benchmark as b

    n_sites = b.N_SITES
    yield b
    b.configure()  # back to the plain defaults for other tests
    b.N_SITES = n_sites


def test_b1_routing_table(bench):
    bench.configure()
    assert bench.route("query", 3) == ("site", None)
    bench.configure(evidence_url="https://e", site_urls=["https://s0", "https://s1"], pki_dir=None)
    expected = {"query": ("site", "op-site-1"), "commit": ("site", "op-site-1"),
                "attest": ("evidence", "op-site-1"), "dispute": ("evidence", "op-site-1"),
                "restore": ("evidence", "admin"), "contribute": (None, None)}
    for op, want in expected.items():
        assert bench.route(op, 1, mtls=True) == want, op


@pytest.fixture(scope="module")
def services(tmp_path_factory):
    root = tmp_path_factory.mktemp("bench-mtls")
    pki = root / "pki"
    subprocess.run([sys.executable, str(CODE / "scripts" / "make_dist_pki.py"), "--out", str(pki),
                    "--n-sites", "2", "--not-before", "2026-01-01T00:00:00Z", "--valid-hours", "87600"],
                   check=True, capture_output=True, cwd=CODE)
    svc = PkiServices(root, pki, 2)
    yield svc, pki
    svc.close()


def test_b2_batch_over_mtls_has_no_unexpected_errors(bench, services):
    svc, pki = services
    bench.configure(evidence_url=svc.url["evidence"], site_urls=[svc.url[0], svc.url[1]], pki_dir=pki)
    bench.seed_all()
    latencies, unexpected, wall, kinds = bench.run_one_batch(4, 20, bench._MIX_REALISTIC)
    assert unexpected == 0, kinds
    assert sum(len(v) for v in latencies.values()) == 80


def test_b3_forbidden_is_an_unexpected_error(bench, services):
    svc, pki = services
    bench.configure(evidence_url=svc.url["evidence"], site_urls=[svc.url[0], svc.url[1]], pki_dir=pki)
    bench._site_clients.reverse()  # deliberately wrong: site-1's operator talks to site-0
    _lat, unexpected, _wall, kinds = bench.run_one_batch(2, 20, bench._MIX_REALISTIC)
    assert unexpected > 0
    assert all(k.endswith(":http.403") for k in kinds), kinds
