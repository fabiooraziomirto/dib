"""make_plog_thresholds reproduces the night's file from the night's calibration (hypothesis; falsified by any difference)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_plog_thresholds as m  # noqa: E402

N = Path(__file__).resolve().parent / "night_wan_20261011"


def test_reproduces_night_file():
    thr = m.build(N / "calib", "wan")
    old = json.loads((N / "plog_thresholds_wan.json").read_text())
    assert thr == old
    assert {k: v["threshold_ms"] for k, v in thr["cells"].items()} == {"D/1": 320.0, "D/10": 32.0, "C/1": 480.0, "C/10": 48.0}
