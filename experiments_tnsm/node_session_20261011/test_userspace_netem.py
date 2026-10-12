"""User-space netem applier (docs/audit/85). Hypotheses (before the code; falsification = any assertion failing):
 U-1  profile specs equal the watcher's (netem_apply.sh): wan 'delay 80ms loss 1%', degraded 'delay 200ms loss 5%', lan removes the qdisc;
 U-2  apply_cmd(name, spec) runs tc INSIDE the container (docker exec -u 0) through the host loader and mounted tc: '... qdisc replace dev eth0 root netem <spec>';
      lan: '... qdisc del dev eth0 root';
 U-3  decide(): a container is (re)applied iff its id is new or the profile changed; an unchanged id is left alone; vanished ids are forgotten;
 U-4  a failed application is retried on the next pass (the id is not marked applied).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import userspace_netem as un  # noqa: E402


def test_u1_specs():
    assert un.SPEC["wan"] == "delay 80ms loss 1%" and un.SPEC["degraded"] == "delay 200ms loss 5%" and un.SPEC["lan"] is None


def test_u2_commands():
    c = un.apply_cmd("dibtnsm-site-1-1", "delay 200ms loss 5%")
    assert c[:4] == ["docker", "exec", "-u", "0"] and "dibtnsm-site-1-1" in c
    joined = " ".join(c)
    assert "/hostlib/ld-linux-x86-64.so.2 --library-path /hostlib /hosttc qdisc replace dev eth0 root netem delay 200ms loss 5%" in joined
    d = " ".join(un.apply_cmd("dibtnsm-site-1-1", None))
    assert "qdisc del dev eth0 root" in d


def test_u3_decide():
    applied = {}
    todo = un.decide([("id1", "n1"), ("id2", "n2")], "degraded", applied)
    assert [t[0] for t in todo] == ["id1", "id2"]
    applied.update({"id1": "degraded", "id2": "degraded"})
    assert un.decide([("id1", "n1"), ("id2", "n2")], "degraded", applied) == []
    assert [t[0] for t in un.decide([("id1", "n1"), ("id2", "n2")], "wan", applied)] == ["id1", "id2"]
    assert [t[0] for t in un.decide([("id1", "n1"), ("id3", "n3")], "degraded", applied)] == ["id3"]
    un.forget_vanished([("id1", "n1")], applied)
    assert set(applied) == {"id1"}


def test_u4_retry_on_failure():
    applied = {}
    calls = []

    def runner(cmd):
        calls.append(cmd)
        return 1 if len(calls) == 1 else 0
    un.apply_all([("id1", "n1")], "degraded", applied, runner)
    assert applied == {}
    un.apply_all([("id1", "n1")], "degraded", applied, runner)
    assert applied == {"id1": "degraded"} and len(calls) == 2


def test_x_profiles_specs():
    """Audit 107: the applier knows x1..x4 with the netem specs of the testbed conditions (one-way delay and loss per side)."""
    import userspace_netem as u
    assert u.SPEC["x1"] == "delay 60ms loss 6%" and u.SPEC["x2"] == "delay 100ms loss 4%" and u.SPEC["x3"] == "delay 150ms loss 6%" and u.SPEC["x4"] == "delay 150ms loss 8%"
    assert u.SPEC["degraded"] == "delay 200ms loss 5%" and u.SPEC["lan"] is None
