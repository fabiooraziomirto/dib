"""Pure parts of the netns testbed (audit 75). Hypotheses (before the code; falsification = any assertion failing):
 B-1  netem_cmds(d_ms, loss_pct): a prio qdisc whose default band carries netem delay/loss and whose band 2 (pfifo) carries the driver's address 127.0.0.2 in both
      directions (u32 src and dst filters); `change` form for later cells;
 B-2  nominal times: cold D 1.5 R, warm 0.5 R (R = 2 d); a delivery is LATE when its apply time exceeds nominal + 0.75 R;
 B-3  an episode is complete iff all 10 sites applied; slow iff complete and the last site is later than nominal + 0.75 R; its pending flag is the complement of complete;
 B-4  per cell: per-site late share over all sites that applied, slow-episode fraction over complete episodes, median/p95 of the last site over complete episodes,
      pending fraction over valid episodes; setup failures are counted apart and never enter the shares;
 B-5  bootstrap CI (percentile 95%, seed fixed) of a share is reproducible and contains the point estimate; empty input gives None;
 B-6  validity T-0: passes iff the median per-site apply time at p = 0 is within 50 ms of the nominal and no delivery is late.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis as an  # noqa: E402


def test_b1_netem_cmds():
    c = an.netem_cmds(200, 5, initial=True)
    text = "\n".join(" ".join(x) for x in c)
    assert "prio bands 3" in text and "netem delay 200ms loss 5%" in text and "pfifo" in text
    assert "match ip src 127.0.0.2/32" in text and "match ip dst 127.0.0.2/32" in text
    ch = an.netem_cmds(100, 10, initial=False)
    assert len(ch) == 1 and "change" in ch[0] and "delay 100ms loss 10%" in " ".join(ch[0])
    assert "loss" not in " ".join(an.netem_cmds(50, 0, initial=False)[0])


def test_b2_nominal_and_late():
    assert an.nominal(0.1, warm=False) == pytest.approx(0.15) and an.nominal(0.1, warm=True) == pytest.approx(0.05)
    assert an.is_late(0.15 + 0.075 + 0.001, R=0.1, warm=False) and not an.is_late(0.15 + 0.07, R=0.1, warm=False)


def ep(applies, setup_ok=True):
    return {"setup_ok": setup_ok, "applies": applies}


def test_b3_b4_cell_summary():
    R = 0.2
    ok = ep({str(i): 0.3 for i in range(10)})                      # nominal 0.3 cold: nobody late
    late1 = ep({**{str(i): 0.3 for i in range(9)}, "9": 1.4})     # one late site, complete, slow
    pend = ep({**{str(i): 0.3 for i in range(9)}, "9": None})     # one site never applied
    bad = ep({}, setup_ok=False)
    s = an.cell_summary([ok, late1, pend, bad], R=R, warm=False)
    assert s["n_valid"] == 3 and s["n_setup_failed"] == 1
    assert s["pending_fraction"] == pytest.approx(1 / 3)
    assert s["slow_episode_fraction"] == pytest.approx(1 / 2)       # over the 2 complete episodes
    assert s["late_share"] == pytest.approx(1 / 29)                 # 29 sites applied, 1 late
    assert s["median_last_ms"] == pytest.approx(850.0)              # median of (300, 1400) over complete episodes
    assert an.cell_summary([bad], R=R, warm=False)["median_last_ms"] is None


def test_b5_bootstrap():
    xs = [0, 0, 1, 1, 1, 0, 1, 0, 0, 0]
    a, b = an.boot_ci_share(xs, seed=7), an.boot_ci_share(xs, seed=7)
    assert a == b and a[0] <= sum(xs) / len(xs) <= a[1]
    assert an.boot_ci_share([], seed=7) is None


def test_b6_validity():
    R = 0.2
    good = [ep({str(i): 0.31 + 0.001 * i for i in range(10)}) for _ in range(5)]
    assert an.t0_valid(good, R=R, warm=False)["valid"] is True
    off = [ep({str(i): 0.45 for i in range(10)}) for _ in range(5)]
    assert an.t0_valid(off, R=R, warm=False)["valid"] is False
    assert an.t0_valid([ep({str(i): 0.05 + 0.002 * i for i in range(10)})], R=0.2, warm=True)["valid"] is True


def _eps(late_sites, n_eps=40, warm=False, R=0.2):
    """n_eps episodes of 10 sites; `late_sites` of the 10 are late in every episode."""
    nom = an.nominal(R, warm)
    return [ep({str(i): (nom + 1.0 if i < late_sites else nom) for i in range(10)}) for _ in range(n_eps)]


def test_b7_bootstrap_difference_of_late_shares():
    a, b = _eps(0), _eps(2)
    lo, hi = an.boot_diff_late_share(a, b, R=0.2, warm_a=False, warm_b=False, seed=3)
    assert hi < 0 and lo <= hi
    lo2, hi2 = an.boot_diff_late_share(b, b, R=0.2, warm_a=False, warm_b=False, seed=3)
    assert lo2 <= 0 <= hi2
    assert an.boot_diff_late_share([], b, R=0.2, warm_a=False, warm_b=False, seed=3) is None


def test_b8_median_per_site():
    assert an.median_site_ms(_eps(0)) == pytest.approx(300.0)
    assert an.median_site_ms([]) is None
