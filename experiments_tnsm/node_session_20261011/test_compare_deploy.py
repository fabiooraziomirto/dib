"""compare_deploy.py (audit 88, H-R1b). Hypotheses (falsified by any failing assertion):
 C-1  regression_verdict: late-share differences <= 0.04 (D/10, C/10) and last-site median differences <= 15% (D/1, C/1) -> no regression; any cell outside -> regression, with the offending cells named;
 C-2  the thresholds are inclusive and relative to the OLD value for medians.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_deploy as cd  # noqa: E402

OLD = {"late": {"D10": 0.186, "C10": 0.282}, "med": {"D1": 10670.0, "C1": 16126.0}}


def test_c1_no_regression():
    new = {"late": {"D10": 0.20, "C10": 0.27}, "med": {"D1": 11000.0, "C1": 15000.0}}
    r = cd.regression_verdict(OLD, new)
    assert r["regression"] is False and r["cells"] == []


def test_c1_regression_names_cells():
    new = {"late": {"D10": 0.30, "C10": 0.282}, "med": {"D1": 10670.0, "C1": 20000.0}}
    r = cd.regression_verdict(OLD, new)
    assert r["regression"] is True and sorted(r["cells"]) == ["C1", "D10"]


def test_c2_inclusive_boundaries():
    new = {"late": {"D10": 0.186 + 0.04, "C10": 0.282}, "med": {"D1": 10670.0 * 1.15, "C1": 16126.0}}
    assert cd.regression_verdict(OLD, new)["regression"] is False
