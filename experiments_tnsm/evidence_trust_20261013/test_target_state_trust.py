"""Does a site accept a fan-out whose target_state does not match its event_type?

Claim under test (docs/main_10p.tex:411, G3): "a faulty evidence service ... cannot
make a fact exportable" because a restoration returns records to MonitorOnly.
Hypothesis H-T1: /apply_fanout with event_type="restore" and target_state="active"
(higher seq) leaves a disputed record non-exportable.
Falsification: the record becomes Active and /export_mud emits its ACE.
Code read before running: service.py:508-511 writes target_state verbatim.
Result: falsified on service 3ffa57ee (kept as xfail strict, per the project rule);
test_valid_restore_returns_to_monitor_only documents the intended path.
"""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "code" / "scripts"))
from v35_lifecycle_experiment import Deployment  # noqa: E402

FACT = dict(device_type="camera", endpoint="subject.example.org", protocol="tcp", port=443)


def _disputed_site():
    temp = tempfile.TemporaryDirectory(prefix="dib-trust-")
    dep = Deployment(Path(temp.name), quorum=1, sites=1)
    dep.post("evidence", "/seed", FACT)
    dep.post("site-0", "/query", FACT)
    dep.post("site-0", "/commit", FACT)
    dep.post("evidence", "/dispute", dict(FACT, site_id="reporter"))
    assert dep.state("site-0", 1)["state"] == "disputed" and dep.aces() == [0]
    return temp, dep


@pytest.mark.xfail(strict=True, reason="H-T1 falsified on 3ffa57ee: target_state is applied verbatim (service.py:508-511)")
def test_mismatched_restore_target_cannot_create_authorization():
    temp, dep = _disputed_site()
    try:
        dep.post("site-0", "/apply_fanout", dict(score_id=1, seq=99, event_type="restore", target_state="active"))
        assert dep.state("site-0", 1)["state"] != "active"
        assert dep.aces() == [0]
    finally:
        dep.close(); temp.cleanup()


def test_valid_restore_returns_to_monitor_only():
    temp, dep = _disputed_site()
    try:
        dep.post("site-0", "/apply_fanout", dict(score_id=1, seq=99, event_type="restore", target_state="monitor-only"))
        assert dep.state("site-0", 1)["state"] == "monitor-only" and dep.aces() == [0]
    finally:
        dep.close(); temp.cleanup()
