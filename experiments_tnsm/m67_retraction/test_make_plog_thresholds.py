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


def test_degraded_thresholds_values():
    """Prepared 2026-10-11 before the degraded block: R = 0.4 s -> 10% of the predicted direct withdrawal = D/1 800, D/10 80, C/1 1200, C/10 120 ms
    (the file itself is written after the degraded calibration, with the same rule as `wan`). Falsification: any assertion failing."""
    import night
    t = night.plog_thresholds("degraded", 3.0)
    assert {k: round(v["threshold_ms"], 6) for k, v in t["cells"].items()} == {"D/1": 800.0, "D/10": 80.0, "C/1": 1200.0, "C/10": 120.0}
    assert all(v["accepted"] for v in t["cells"].values())
