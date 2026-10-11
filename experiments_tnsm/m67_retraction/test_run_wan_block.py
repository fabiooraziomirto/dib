"""Offline tests of run_wan_block.py (nothing touches the node). Hypotheses: T-1 no remote command contains, contiguous, the names its own
pgrep looks for (a pgrep -f would find its own shell); T-2 every node command begins with the guard (set -e, docker empty, no run.py, watcher
required/absent, >= 2 GB, PKI >= 2 h); T-3 the background wrapper writes the exit status to <name>.rc with the `$?` escaped for the inner shell;
T-4 B1 uses the committed thresholds file, the new p95, seed 20261014, four groups in one invocation; T-5 --dry-run calls neither ssh nor scp.
Falsification: any assertion failing."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_wan_block as w  # noqa: E402


def test_no_self_matching_names():
    for label, cmd in w.plan():
        assert "m67_retraction/run.py" not in cmd and "netem_watch" not in cmd, label


def test_every_command_starts_with_the_guard():
    for label, cmd in w.plan():
        assert cmd.startswith("set -e; export PATH=/snap/bin:$PATH;"), label
        assert "-gt 2000000000" in cmd and "-checkend 7200" in cmd and "docker ps -a -q --filter label=com.docker.compose.project=dibtnsm" in cmd
    assert 'if ! pgrep -f "$W"' in w.guard("required") and 'if pgrep -f "$W"' in w.guard("absent")
    assert 'if ! pgrep -f "$W"' not in w.guard("absent")


def test_background_wrapper_writes_rc():
    cmd = w.background("b1", "true", "required")
    assert 'echo \\$? > $OUT/b1.rc' in cmd and "setsid nohup bash -c" in cmd and cmd.endswith("echo avviato")
    assert "rm -f $OUT/b1.rc" in cmd


def test_b1_command():
    c = w.b1_cmd(3.6)
    for part in ("--block b1", "--profile wan", "--arms D,C", "--fanouts 1,10", "--seed 20261014", "--plog-thresholds $OUT/plog_thresholds_wan.json", "--plog-p95-ms 3.6", "$R"):
        assert part in c
    assert '"' not in c          # it goes inside a double-quoted bash -c


def test_dry_run_touches_nothing(monkeypatch, capsys):
    def boom(*a, **k):
        raise AssertionError("subprocess called in --dry-run")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(sys, "argv", ["run_wan_block.py", "--dry-run"])
    assert w.main() == 0
    assert "W1 calibrazione wan" in capsys.readouterr().out


def test_calibration_hold_is_long_enough_for_netem_show():
    assert "--hold 240" in w.calib_cmd("wan", "calib_wan_b", w.HOLD_S) and w.HOLD_S >= 180
