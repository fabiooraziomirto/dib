"""analyze.py must detect a violated criterion, not only pass the stored run.

Hypothesis: each mutation below breaks exactly the criterion it targets.
Falsification: a mutated input that analyze.py still judges as passing.
"""
import copy
import json
import shutil
from pathlib import Path

import pytest

import analyze

HERE = Path(__file__).resolve().parent


@pytest.fixture()
def data():
    return (json.loads((HERE / "restore_ablation.json").read_text()),
            json.loads((HERE / "offline_veto.json").read_text()))


def test_stored_run_passes(data):
    abl, ov = data
    assert all(analyze.judge_ablation(abl)["criteria"].values())
    assert all(analyze.judge_offline(ov)["criteria"].values())


def test_export_without_commit_is_caught(data):
    abl = copy.deepcopy(data[0])
    case = next(c for c in abl["cases"] if c["policy"] == "dib")
    final = next(t for t in case["trace"] if t["event"] == "restored_and_reconciled")
    final["subject_aces"][1] = 1
    assert analyze.judge_ablation(abl)["criteria"]["A1 dib"] is False


def test_lost_veto_is_caught(data):
    ov = copy.deepcopy(data[1])
    ov["trials"][3]["after"]["veto"]["origin"] = None
    assert analyze.judge_offline(ov)["criteria"]["A2 veto preserved"] is False


def test_control_change_is_caught(data):
    abl = copy.deepcopy(data[0])
    abl["cases"][0]["trace"][2]["control_aces"] = [1, 0, 1]
    assert analyze.judge_ablation(abl)["criteria"]["A4 persistent_approval"] is False


def test_old_service_hash_fails_provenance(tmp_path):
    for name in ("restore_ablation.json", "offline_veto.json", "manifest.json"):
        shutil.copy(HERE / name, tmp_path / name)
    ov = json.loads((tmp_path / "offline_veto.json").read_text())
    ov["service_sha256"] = "3186304363ed309241134752689423088dda98b9d8fe3bcdf9669749264398fd"
    (tmp_path / "offline_veto.json").write_text(json.dumps(ov))
    assert analyze.main(tmp_path) == 1
