"""cpu_sampler (audit 18, user decision 2026-10-10; written before the code).
Hypotheses: S-1 parse_stat_line splits /proc/stat's first line into (busy_ticks, total_ticks,
steal_ticks) with busy = total - idle - iowait and total = the first 8 fields (guest is already in
user); S-2 cores_between(a, b, ncpu) = busy-tick delta / total-tick delta * ncpu; S-3
container_cores(prev_usec, cur_usec, seconds) = delta usage_usec / 1e6 / seconds and is never
negative; S-4 read_cgroup_usage(path) reads usage_usec from a cpu.stat text.
Falsification: any assertion failing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cpu_sampler as cs  # noqa: E402


def test_s1_parse_stat_line():
    line = "cpu  100 10 50 800 40 5 5 20 7 0"      # user nice system idle iowait irq softirq steal guest guest_nice
    busy, total, steal = cs.parse_stat_line(line)
    assert total == 100 + 10 + 50 + 800 + 40 + 5 + 5 + 20
    assert busy == total - 800 - 40
    assert steal == 20


def test_s2_cores_between():
    a = (100, 1000, 0)
    b = (100 + 480, 1000 + 800, 8)       # 480 busy of 800 total ticks, 16 cpus -> 9.6 cores
    assert abs(cs.cores_between(a, b, 16) - 9.6) < 1e-9
    assert cs.cores_between(a, a, 16) == 0.0


def test_s3_container_cores():
    assert abs(cs.container_cores(1_000_000, 3_500_000, 2.0) - 1.25) < 1e-9
    assert cs.container_cores(5_000_000, 4_000_000, 1.0) == 0.0     # counter reset: never negative


def test_s4_read_cgroup_usage(tmp_path):
    p = tmp_path / "cpu.stat"
    p.write_text("usage_usec 123456\nuser_usec 100000\nsystem_usec 23456\nnr_periods 0\n")
    assert cs.read_cgroup_usage(str(p)) == 123456
    assert cs.read_cgroup_usage(str(tmp_path / "missing")) is None
