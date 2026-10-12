"""analyze_deploy.py (audit 85). Hypotheses (before the code; falsification = any assertion failing):
 A-1  per_site_late_share: fraction of per-site P-log values above nominal + 0.3 s over NON-excluded episodes (None values skipped);
 A-2  verdict_h_n1: both D/10 and C/10 within +-4 points of the B5 values (0.178, 0.310); verdict_h_n2: D/10 within 4 of 0.179, C/10 within 8 of 0.251, F1 medians within 25% of 10600 and 16400;
 A-3  the model is validated on the deployment iff H-N1 and H-N2 both hold.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_deploy as ad  # noqa: E402


def row(vals, excluded=False):
    return {"excluded": excluded, "withdrawn_plog_s": {str(i): v for i, v in enumerate(vals)}}


def test_a1_late_share():
    rows = [row([0.6] * 10), row([0.6] * 9 + [1.7]), row([5.0] * 10, excluded=True), row([0.6] * 9 + [None])]
    assert ad.per_site_late_share(rows, nominal=0.6) == 1 / 29


def test_a2_a3():
    ok = ad.verdicts({"D10": 0.18, "C10": 0.30}, {"D1": 10500.0, "C1": 18000.0})
    assert ok["h_n1"] and ok["h_n2"] and ok["validated"]
    off_n1 = ad.verdicts({"D10": 0.18, "C10": 0.20}, {"D1": 10500.0, "C1": 18000.0})
    assert not off_n1["h_n1"] and not off_n1["validated"]
    c_gap = ad.verdicts({"D10": 0.18, "C10": 0.33}, {"D1": 10500.0, "C1": 18000.0})     # C within 8 of 0.251 is 0.331 at most: 0.33 inside; and within 4 of 0.310: inside
    assert c_gap["h_n2"] and c_gap["h_n1"]
    bad_f1 = ad.verdicts({"D10": 0.18, "C10": 0.30}, {"D1": 14000.0, "C1": 18000.0})
    assert not bad_f1["h_n2"] and not bad_f1["validated"]
