"""Exclusion of episodes that overlap an interval in which the netem profile was not settled (rule declared in the docstring of analyze_b1.py BEFORE
any `degraded` B1 datum). Pure functions, no I/O except the two readers:
  * monitor_intervals(profile_events.jsonl): the `transient` rows of auto_block.py's ProfileMonitor, (from_ms, end_ms) -> seconds;
  * watch_unsettled_intervals(watch2.log text): from `containers changed -> applying`, `request accepted`, `apply FAILED`, `the set of containers
    changed during the application` or `profile.applied NOT written` to the next `applied ...` (or `profile.applied written after ...`) line; start events
    with no `applied` in between make one interval from the first; no end = open (infinity). Times are the watcher's UTC milliseconds (same node clock as t0).
An episode window is [t0, max(t_resp, plog_apply_ts, plog_ack_ts)]; overlap on closed intervals, no margin."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

_LINE = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3})Z netem_watch: (.*)$")
CAUSE = "profile_incoherent_overlap"


def _epoch(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp()


def parse_watch_log(text: str) -> list[tuple[float, str]]:
    """[(epoch_s, kind)] with kind in request_accepted, changed, apply_failed, set_changed, not_written, applied, written."""
    out = []
    for line in text.splitlines():
        m = _LINE.match(line.strip())
        if not m:
            continue
        msg, kind = m.group(2), None
        if msg.startswith("request accepted"):
            kind = "request_accepted"
        elif msg.startswith("containers changed -> applying"):
            kind = "changed"
        elif msg.startswith("apply FAILED"):
            kind = "apply_failed"
        elif msg.startswith("the set of containers changed during the application"):
            kind = "set_changed"
        elif msg.startswith("profile.applied NOT written"):
            kind = "not_written"
        elif msg.startswith("profile.applied written after"):
            kind = "written"
        elif re.match(r"^applied \S+ \(", msg):
            kind = "applied"
        if kind:
            out.append((_epoch(m.group(1)), kind))
    return out


def watch_unsettled_intervals(text: str) -> list[tuple[float, float]]:
    iv, start = [], None
    for t, kind in parse_watch_log(text):
        if kind in ("applied", "written"):
            if start is not None:
                iv.append((start, t))
                start = None
        elif start is None:
            start = t
    if start is not None:
        iv.append((start, float("inf")))
    return iv


def monitor_intervals(path) -> list[tuple[float, float]]:
    try:
        rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    except OSError:
        return []
    return [(r["from_ms"] / 1000.0, r["end_ms"] / 1000.0) for r in rows if r.get("transient")]


def episode_window(row: dict) -> tuple[float, float]:
    ts = [row["t_resp"]] if row.get("t_resp") is not None else []
    for k in ("plog_apply_ts", "plog_ack_ts"):
        ts += [t for t in (row.get(k) or {}).values() if t is not None]
    return row["t0"], max([row["t0"]] + ts)


def overlaps(win: tuple[float, float], intervals) -> bool:
    return any(win[0] <= b and win[1] >= a for a, b in intervals)


def mark_overlaps(rows: list[dict], labelled_intervals: list[tuple[str, tuple[float, float]]]):
    """Marks overlapping, not-yet-excluded episodes (excluded=True, excluded_reason CAUSE, excluded_overlap_source = first source that overlaps).
    Returns (number newly excluded, the labelled intervals that excluded at least one episode)."""
    n, used = 0, []
    for r in rows:
        if r.get("excluded") or "t0" not in r:
            continue
        w = episode_window(r)
        for lab, iv in labelled_intervals:
            if overlaps(w, [iv]):
                r["excluded"], r["excluded_reason"], r["excluded_overlap_source"] = True, CAUSE, lab
                n += 1
                if (lab, iv) not in used:
                    used.append((lab, iv))
                break
    return n, used
