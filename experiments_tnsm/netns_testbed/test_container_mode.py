"""Container mode of the netns testbed (audit 83): on the node, where unprivileged namespaces are blocked, the worker runs inside a Docker container with NET_ADMIN and uses the
host's `tc` through the host's dynamic loader. Hypotheses (before the code; falsification = any assertion failing):
 M-1  tc_cmd(args) without DIB_TESTBED_TC_PREFIX is ['tc', *args] (local behaviour unchanged);
 M-2  with DIB_TESTBED_TC_PREFIX='/hostlib/ld-linux-x86-64.so.2 --library-path /hostlib /hosttc' the command is that prefix + args (the leading 'tc' replaced);
 M-3  in container mode (DIB_TESTBED_CONTAINER=1) the worker does not call `ip`; otherwise it does (checked on the pure helper `needs_ip_link()`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testbed as tb  # noqa: E402


def test_m1_m2(monkeypatch):
    monkeypatch.delenv("DIB_TESTBED_TC_PREFIX", raising=False)
    assert tb.tc_cmd(["tc", "qdisc", "show"]) == ["tc", "qdisc", "show"]
    monkeypatch.setenv("DIB_TESTBED_TC_PREFIX", "/hostlib/ld-linux-x86-64.so.2 --library-path /hostlib /hosttc")
    assert tb.tc_cmd(["tc", "qdisc", "show"]) == ["/hostlib/ld-linux-x86-64.so.2", "--library-path", "/hostlib", "/hosttc", "qdisc", "show"]
    assert tb.tc_cmd(["ip", "x"]) == ["ip", "x"]          # only tc commands are rewritten


def test_m3(monkeypatch):
    monkeypatch.delenv("DIB_TESTBED_CONTAINER", raising=False)
    assert tb.needs_ip_link() is True
    monkeypatch.setenv("DIB_TESTBED_CONTAINER", "1")
    assert tb.needs_ip_link() is False
