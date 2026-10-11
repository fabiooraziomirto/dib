"""Tests of m8_mud_sig/run.py (audit 55). Local tests with the REAL `openssl` (tiny sizes); no node. Hypotheses (before the module; falsification = any
assertion failing):
 M-1  the MUD files come from export_mud_file: the exported ACE count equals the requested one (5, 20, 100) and the JSON is deterministic (same bytes twice);
 M-2  the sign command is a DETACHED CMS signature (no -nodetach), -binary, -md sha256, DER; the verify command uses -content, -CAfile, -purpose any;
 M-3  validity: verify of a correct signature succeeds for ecdsa-p256 and rsa-2048; verify of a file altered by one byte FAILS (negative control);
 M-4  p95 = sorted[ceil(0.95 n) - 1]; the verdict is 'falsified' iff the CI lower bound > 10 ms, 'inconclusive' iff p95 > 10 with the CI crossing, else
      'not falsified'; the global verdict is falsified iff any cell is falsified, reported as k/n;
 M-5  a cell returns n_reps x pairs_per_rep measured pairs (warm-up discarded) and the spawn baseline has the same count;
 M-6  the cell order is a seeded shuffle (same seed, same order).
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as m8  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl not available")


def test_mud_files_from_export(tmp_path):
    p1 = m8.make_mud_files(tmp_path / "a", (5, 20, 100))
    p2 = m8.make_mud_files(tmp_path / "b", (5, 20, 100))
    for n in (5, 20, 100):
        doc = json.loads(p1[n].read_text())
        aces = doc["ietf-access-control-list:acls"]["acl"][0]["aces"]["ace"]
        assert len(aces) == n
        assert p1[n].read_bytes() == p2[n].read_bytes()


def test_commands():
    s = m8.sign_cmd("f", "c.pem", "k.pem", "s.der")
    v = m8.verify_cmd("f", "s.der", "c.pem")
    assert "-nodetach" not in s and {"cms", "-sign", "-binary", "-outform", "DER"} <= set(s) and s[s.index("-md") + 1] == "sha256"
    assert {"-content", "-CAfile", "-purpose", "-no_check_time"} <= set(v) and v[v.index("-purpose") + 1] == "any"


@pytest.mark.parametrize("alg", ["ecdsa-p256", "rsa-2048"])
def test_validity_and_negative_control(tmp_path, alg):
    files = m8.make_mud_files(tmp_path / "mud", (5,))
    key, cert = m8.make_keypair(tmp_path / "keys", alg)
    sig = tmp_path / "s.der"
    assert m8.run_ok(m8.sign_cmd(files[5], cert, key, sig))
    assert m8.run_ok(m8.verify_cmd(files[5], sig, cert))
    bad = tmp_path / "bad.json"
    data = bytearray(files[5].read_bytes())
    data[len(data) // 2] ^= 0x01
    bad.write_bytes(bytes(data))
    assert not m8.run_ok(m8.verify_cmd(bad, sig, cert))


def test_p95_and_verdict():
    assert m8.p95(list(range(1, 101))) == 95
    assert m8.p95([5.0]) == 5.0
    assert m8.verdict(12.0, 10.5, 14.0) == "falsified"
    assert m8.verdict(12.0, 9.5, 14.0) == "inconclusive"
    assert m8.verdict(8.0, 7.0, 9.0) == "not falsified"
    assert m8.verdict(10.0, 9.0, 11.0) == "not falsified"          # p95 == 10 is not above
    g = m8.global_verdict(["falsified", "not falsified", "inconclusive"])
    assert g["verdict"] == "falsified" and g["k"] == (1, 3)
    assert m8.global_verdict(["not falsified"] * 6)["verdict"] == "not falsified"


def test_cell_counts_and_order(tmp_path):
    files = m8.make_mud_files(tmp_path / "mud", (5,))
    key, cert = m8.make_keypair(tmp_path / "keys", "ecdsa-p256")
    r = m8.run_cell(files[5], key, cert, tmp_path / "w", reps=2, pairs=3, warmup=1)
    assert len(r["pair_ms"]) == 6 and len(r["spawn_ms"]) == 6 and r["negative_control_ok"] is True and r["sig_bytes"] > 0
    assert all(x > 0 for x in r["pair_ms"])
    assert m8.cell_order(["a", "b", "c", "d", "e", "f"], 20261011) == m8.cell_order(["a", "b", "c", "d", "e", "f"], 20261011)
    assert m8.cell_order(list("abcdef"), 1) != m8.cell_order(list("abcdef"), 2)
