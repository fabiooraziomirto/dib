"""deploy_b2k.sh (audit 45 rules with the user-space applier). Hypotheses (falsified by any failing assertion): the script is valid bash; it starts the applier with --poll 0.1 (the L_dns rule needs <= 0.1 s);
it decides with night.ldns_decision(p95, 0.1) and does NOT run a profile whose decision is not "run" (no threshold change); it passes --l-dns to run.py b2kill; it sets DIB_M67_DNS_NOSEARCH=1 and the
extra compose; it refuses to start with dibtnsm containers, < 4 GB memory or < 2 GB disk; it never calls sudo or pkill."""
import subprocess
from pathlib import Path

S = Path(__file__).resolve().parent / "deploy_b2k.sh"
T = S.read_text()


def test_bash_syntax():
    assert subprocess.run(["bash", "-n", str(S)]).returncode == 0


def test_rules_present():
    for s in ("--poll 0.1", "night.ldns_decision(p95, 0.1)", '[ "$DEC" != "run" ] && {', "--block b2kill", "--l-dns $L", "DIB_M67_DNS_NOSEARCH=1", "DIB_M67_EXTRA_COMPOSE",
              "REFUSED", "MemAvailable", "2000000000", "dibtnsm"):
        assert s in T, s
    assert "sudo" not in T.replace("no sudo", "") and "pkill" not in T
