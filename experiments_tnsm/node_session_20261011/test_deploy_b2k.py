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


def test_trials_and_seed_are_parameters_with_the_old_defaults():
    assert "TRIALS=${TRIALS:-10}" in T and "SEED=${SEED:-20261014}" in T and "--seed $SEED --trials $TRIALS" in T


def test_night_queue_syntax_and_order():
    q = (Path(__file__).resolve().parent / "night_queue.sh").read_text()
    assert subprocess.run(["bash", "-n", str(Path(__file__).resolve().parent / "night_queue.sh")]).returncode == 0
    body = q.split("mkdir -p", 1)[1]   # the header comments also name deploy_run.sh
    assert body.index("TRIALS=20 SEED=20261016") < body.index("deploy_run.sh") and "$FIRST/DONE" in q and "sudo" not in q.replace("no sudo", "") and "pkill" not in q


def test_night_queue2():
    p = Path(__file__).resolve().parent / "night_queue2.sh"
    q = p.read_text()
    assert subprocess.run(["bash", "-n", str(p)]).returncode == 0
    body = q.split("mkdir -p", 1)[1]
    assert "QUEUE_DONE" in body and "for X in x1 x2 x3 x4" in body and "deploy_run.sh $T4 $ROOT/node_oos_$X $X default D,C 10" in body
    assert "sudo" not in q.replace("no sudo", "") and "pkill" not in q


def test_queues_read_their_tree_from_pointer_files():
    """Runtime correction: a fixed tree can be swapped in between steps by writing a pointer file, without restarting the queue."""
    d = Path(__file__).resolve().parent
    q1, q2 = (d / "night_queue.sh").read_text(), (d / "night_queue2.sh").read_text()
    assert "CURRENT_TREE_B2K_B" in q1 and "CURRENT_TREE_R1F" in q1 and "CURRENT_TREE_OOS" in q2
    for p in ("night_queue.sh", "night_queue2.sh"):
        assert subprocess.run(["bash", "-n", str(d / p)]).returncode == 0
