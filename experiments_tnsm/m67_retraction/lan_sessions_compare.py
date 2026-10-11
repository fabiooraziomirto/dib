"""Descriptive comparison of the two `lan` sessions of 2026-10-11 (b1: 07:52 UTC; b1_default: 08:27 UTC): time, execution order, background,
and first-half vs second-half medians of the last-site P-log per cell. No hypothesis test, no explanation of the drift (user decision).
Usage: python3 lan_sessions_compare.py"""
import datetime as D
import json
import statistics as S
from pathlib import Path

H = Path(__file__).resolve().parent / "lan_20261011"
f = lambda t: D.datetime.fromtimestamp(t, D.timezone.utc).strftime("%H:%M:%S")  # noqa: E731
out = ["| session | order | arm | FANOUT | cell UTC | other_cores | steal_pct | busy_pct | load1 | median ms | 1st 5 / 2nd 5 | ep0 | min-max |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for name in ("b1", "b1_default"):
    for line in (H / name / "cells.jsonl").read_text().splitlines():
        c = json.loads(line)
        sp, bg = c["cell_spec"], c["background_idle"]
        v = [1000 * max(x for x in r["withdrawn_plog_s"].values()) for r in c["rows"] if not r.get("excluded")]
        out.append(f"| {name} | {c['cell']} | {sp['arm']} | {sp['fanout']} | {f(c['t_cell'][0])}-{f(c['t_cell'][1])} | {bg['other_cores']} | {bg['steal_pct']} | {bg['busy_pct']} | {bg['load1']} | "
                   f"{S.median(v):.1f} | {S.median(v[:5]):.1f} / {S.median(v[5:]):.1f} | {v[0]:.1f} | {min(v):.1f}-{max(v):.1f} |")
text = "\n".join(out) + "\n"
print(text)
(H / "sessions_compare.md").write_text(text)
