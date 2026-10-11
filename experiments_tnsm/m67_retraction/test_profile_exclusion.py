"""Tests of profile_exclusion.py (exclusion of episodes that overlap an interval in which the netem profile was not settled). Hypotheses (declared first):
X-1  watch2.log lines are parsed with their UTC time (ms) and classified; an interval of UNSETTLED profile starts at `containers changed -> applying`,
     `request accepted`, `apply FAILED`, `the set of containers changed during the application` or `profile.applied NOT written`, and ends at the next
     `applied ...` line; consecutive start events without an `applied` in between make ONE interval from the first; no end = open interval;
X-2  the transient incoherence intervals of the monitor (profile_events.jsonl: from_ms .. end_ms) are used as they are;
X-3  an episode window is [t0, max(t_resp, plog_apply_ts of every site, plog_ack_ts when present)]; overlap is on CLOSED intervals, no margin;
X-4  overlapping episodes get excluded=True and excluded_reason `profile_incoherent_overlap`; episodes already excluded keep their reason and are not
     recounted; non-overlapping episodes are untouched; the intervals used are returned verbatim for the report.
Falsification: any assertion failing."""
import json
from datetime import datetime, timezone

import profile_exclusion as px


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp()


LOG = """2026-10-11T11:56:31.143Z netem_watch: request accepted: degraded
2026-10-11T11:56:31.192Z netem_watch: applied degraded (0.024 s)
2026-10-11T11:58:46.017Z netem_watch: containers changed -> applying degraded
2026-10-11T11:58:46.937Z netem_watch: apply FAILED (attempt 1), retrying every 0.5s
2026-10-11T11:58:49.332Z netem_watch: applied degraded (0.229 s)
2026-10-11T11:59:03.585Z netem_watch: containers changed -> applying degraded
2026-10-11T11:59:04.465Z netem_watch: applied degraded (0.871 s)
2026-10-11T11:59:05.023Z netem_watch: containers changed -> applying degraded
2026-10-11T11:59:05.870Z netem_watch: applied degraded (0.838 s)
2026-10-11T11:59:20.593Z netem_watch: request accepted: lan
"""


def test_x1_parse_and_unsettled_intervals():
    ev = px.parse_watch_log(LOG)
    assert [k for _, k in ev][:3] == ["request_accepted", "applied", "changed"] and abs(ev[0][0] - ts("2026-10-11T11:56:31.143Z")) < 1e-6
    iv = px.watch_unsettled_intervals(LOG)
    assert iv[0] == (ts("2026-10-11T11:56:31.143Z"), ts("2026-10-11T11:56:31.192Z"))
    assert iv[1] == (ts("2026-10-11T11:58:46.017Z"), ts("2026-10-11T11:58:49.332Z"))        # changed + FAILED: one interval, to the next `applied`
    assert iv[2] == (ts("2026-10-11T11:59:03.585Z"), ts("2026-10-11T11:59:04.465Z"))
    assert iv[3] == (ts("2026-10-11T11:59:05.023Z"), ts("2026-10-11T11:59:05.870Z"))
    assert iv[4][0] == ts("2026-10-11T11:59:20.593Z") and iv[4][1] == float("inf")           # open: no `applied` after it in this excerpt
    assert len(iv) == 5
    other = "2026-10-11T12:00:00.000Z netem_watch: the set of containers changed during the application (before: 10, after: 11): profile.applied not written, re-applying\n" \
            "2026-10-11T12:00:01.000Z netem_watch: applied degraded (0.9 s)\n2026-10-11T12:05:00.000Z netem_watch: profile.applied NOT written (netem applied)\n" \
            "2026-10-11T12:05:02.000Z netem_watch: profile.applied written after 3 failed attempt(s)\n"
    iv2 = px.watch_unsettled_intervals(other)
    assert iv2[0] == (ts("2026-10-11T12:00:00.000Z"), ts("2026-10-11T12:00:01.000Z"))
    assert iv2[1][0] == ts("2026-10-11T12:05:00.000Z") and iv2[1][1] == ts("2026-10-11T12:05:02.000Z")
    assert px.watch_unsettled_intervals("garbage\nnot a log line\n") == []


def test_x2_monitor_intervals(tmp_path):
    p = tmp_path / "ev.jsonl"
    p.write_text(json.dumps({"epoch_ms": 1, "coherent": True}) + "\n" + json.dumps({"transient": True, "from_ms": 1791719944000, "start_ms": 1791719944456, "end_ms": 1791719945870}) + "\n")
    assert px.monitor_intervals(p) == [(1791719944.0, 1791719945.87)]
    assert px.monitor_intervals(tmp_path / "missing.jsonl") == []


def test_x3_episode_window_and_overlap():
    row = {"t0": 100.0, "t_resp": 100.5, "plog_apply_ts": {"0": 100.4, "1": 101.2, "2": None}, "plog_ack_ts": {"0": 103.0, "1": None}}
    assert px.episode_window(row) == (100.0, 103.0)
    assert px.episode_window({"t0": 5.0, "t_resp": 5.2}) == (5.0, 5.2)
    assert px.overlaps((100.0, 103.0), [(103.0, 104.0)])                  # touching counts: closed intervals
    assert not px.overlaps((100.0, 103.0), [(103.0001, 104.0)]) and not px.overlaps((100.0, 103.0), [(90.0, 99.9999)])
    assert px.overlaps((100.0, 103.0), [(0.0, float("inf"))])


def test_x4_marking():
    rows = [{"episode": 0, "t0": 10.0, "t_resp": 10.4, "excluded": False},
            {"episode": 1, "t0": 20.0, "t_resp": 20.4, "excluded": False},
            {"episode": 2, "t0": 21.0, "t_resp": 21.4, "excluded": True, "excluded_reason": "client_timeout"},
            {"episode": 3, "t0": 40.0, "t_resp": 40.4, "excluded": False}]
    n, used = px.mark_overlaps(rows, [("monitor", (20.2, 20.3)), ("watch2.log", (21.2, 21.3)), ("watch2.log", (100.0, 101.0))])
    assert n == 1                                                         # only episode 1: episode 2 was already excluded (keeps its reason)
    assert rows[1]["excluded"] is True and rows[1]["excluded_reason"] == "profile_incoherent_overlap"
    assert rows[2]["excluded_reason"] == "client_timeout" and rows[0]["excluded"] is False and rows[3]["excluded"] is False
    assert used == [("monitor", (20.2, 20.3))]                           # only the interval that excluded something is reported as used
    assert rows[1]["excluded_overlap_source"] == "monitor"


def test_x5_analysis_helper_marks_rows_and_reports(tmp_path):
    import analyze_b1 as a
    ev = tmp_path / "ev.jsonl"
    ev.write_text(json.dumps({"transient": True, "from_ms": 20_000, "start_ms": 20_100, "end_ms": 20_300}) + "\n")
    log = "2026-10-11T11:59:03.585Z netem_watch: containers changed -> applying degraded\n2026-10-11T11:59:04.465Z netem_watch: applied degraded (0.8 s)\n"
    base = ts("2026-10-11T11:59:04.000Z")
    cells = [{"cell_spec": {"arm": "C", "fanout": 10}, "rows": [
        {"episode": 0, "t0": 20.05, "t_resp": 20.1, "excluded": False},                  # overlaps the monitor interval (20.0 .. 20.3)
        {"episode": 1, "t0": base - 0.2, "t_resp": base + 0.1, "excluded": False},       # overlaps the watcher interval
        {"episode": 2, "t0": 50.0, "t_resp": 50.1, "excluded": False}]}]
    labelled, per_cell, text = a.overlap_exclusion(cells, str(ev), log)
    text = "\n".join(text)
    assert [r["excluded"] for r in cells[0]["rows"]] == [True, True, False]
    assert [r.get("excluded_overlap_source") for r in cells[0]["rows"]] == ["monitor", "watch2.log", None]
    assert per_cell == {("C", 10): 2} and "profile_incoherent_overlap" in text and "11:59:03" in text
    labelled2, per2, text2 = a.overlap_exclusion([{"cell_spec": {"arm": "D", "fanout": 1}, "rows": []}], None, None)
    assert per2 == {} and "NOT applied" in "\n".join(text2)                                             # no inputs: said explicitly, never silent
