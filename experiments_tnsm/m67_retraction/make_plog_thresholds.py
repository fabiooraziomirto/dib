"""Writes the P-log threshold file of a profile from a calibration (calib_profile.py output), with the SAME rule as the night (night.py:262-266,
imported, not modified): p95 = max(single-container p95, parallel containers' p95); threshold per cell = 10% of the predicted direct
withdrawal (10 x n_RTT x R for FANOUT 1, n_RTT x R for FANOUT 10, R = 2d); a cell is accepted if the calibrated p95 is below it.
Hypothesis: on the night's calibration it reproduces plog_thresholds_wan.json exactly (test_make_plog_thresholds.py).
Usage: python3 make_plog_thresholds.py <calib dir with calib_<profile>_result.json and calib_logs_<profile>.json> <profile> <out.json>
Prints the sha256 of the file; the file must be committed BEFORE the first B1 datum."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import night  # noqa: E402


def p95_of(logs: dict) -> float:
    return max([logs["single"]["p95_ms"]] + [v["p95_ms"] for v in logs["parallel"].values() if isinstance(v, dict) and "p95_ms" in v])


def build(calib_dir: Path, profile: str) -> dict:
    return night.plog_thresholds(profile, p95_of(json.loads((calib_dir / f"calib_logs_{profile}.json").read_text())))


if __name__ == "__main__":
    cdir, profile, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    thr = build(cdir, profile)
    out.write_text(json.dumps(thr, indent=1))
    print(hashlib.sha256(out.read_bytes()).hexdigest(), out)
    print("calibrated p95 ms:", thr["calibrated_p95_ms"], {k: (v["threshold_ms"], v["accepted"]) for k, v in thr["cells"].items()})
