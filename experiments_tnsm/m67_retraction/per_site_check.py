"""Does cells.jsonl contain the per-site data? (user request 2026-10-11). Checks, for every B1 cell of a run: for each episode the per-site fields
(withdrawn_plog_s, plog_apply_ts, plog_ack_ts, plog_ack_count, pending_after_response, pending_left) have the 10 sites; counts missing P-log
apply timestamps; prints the per-site median withdrawal (ms, P-log, from t0) of each cell. Descriptive only. Usage: python3 per_site_check.py <dir>"""
import json
import statistics as S
import sys
from pathlib import Path

FIELDS = ["withdrawn_plog_s", "plog_apply_ts", "plog_ack_ts", "plog_ack_count", "pending_after_response", "pending_left"]
d = Path(sys.argv[1])
lines = ["| arm | FANOUT | episodes | site-episodes with P-log apply | missing | fields with 10 sites (every episode) | per-site median ms (site 0..9) |", "|---|---|---|---|---|---|---|"]
for c in map(json.loads, (d / "cells.jsonl").read_text().splitlines()):
    sp, rows = c["cell_spec"], [r for r in c["rows"] if not r.get("excluded")]
    full = [f for f in FIELDS if all(len(r.get(f) or {}) == 10 for r in rows)]
    have = sum(1 for r in rows for v in r["withdrawn_plog_s"].values() if v is not None)
    med = [S.median(1000 * r["withdrawn_plog_s"][str(i)] for r in rows if r["withdrawn_plog_s"][str(i)] is not None) for i in range(10)]
    lines.append(f"| {sp['arm']} | {sp['fanout']} | {len(rows)} | {have} / {10 * len(rows)} | {10 * len(rows) - have} | {len(full)}/{len(FIELDS)} | {' '.join(f'{m:.0f}' for m in med)} |")
ep = [json.loads(x) for x in (d / "episodes.jsonl").read_text().splitlines()]
lines.append(f"\nepisodes.jsonl: {len(ep)} lines, keys of a row: {sorted(ep[0]['row'])}" if "row" in ep[0] else f"\nepisodes.jsonl: {len(ep)} lines")
print("\n".join(lines))
