# Prediction (c): observable per site and episode (written 2026-10-10, BEFORE any B1 data)

Status: replaces the per-delivery wording of the (c) table in `run.py` / audit 14 for the *observable*; the model (f, f^3) and the
method (Clopper-Pearson 95% interval outside the predicted interval falsifies) are unchanged. The intervals stay conditional on
the tcpdump calibration, which re-estimates f. Not to be modified after B1 data.

## What is observed now
Not the deliveries but, per episode and site, whether the site has an `ack` line in the evidence log after t0 (or a delivery
still queued at the deadline): `summarize_rows` counts `n_pending_sites_log`. Reason: GET /pending reads are late by ~d..2d
and miss drains (audit 18 s.2.5).

## Why the unit differs from "a delivery"
`pending_fanout` has one row per (site, score_id) and keeps the highest seq (`service.py:720-724`, `ON CONFLICT(site_id, score_id)
DO UPDATE ... WHERE excluded.seq > pending_fanout.seq`). Several failed deliveries to the same site for the same fact collapse into
ONE row, hence one site-episode "pending" however many deliveries failed. The observed quantity is
`p_site = 1 - (1 - f^3)^k ~ k f^3` (f^3 = a delivery fails all 3 attempts; k = number of fan-outs per site and fact in the episode).

## k, read from service.py
- B1 episode: ONE `POST /dispute` by site-1 on a fresh fact, `SUSPENSION_QUORUM` default 1 (`service.py:126`; not overridden in the
  compose files of this run) => a single fan-out (`dispute`, seq 1; `service.py:828-837`, `_fan_out` at the end of `dispute`). **k = 1.**
  With k = 1 the observable per site-episode IS the per-delivery event, `1-(1-f^3)^1 = f^3`: **the intervals do not change.**
- B2-kill trial (not used for (c)): per fact dispute (site-1), revoke (site-2), restore = 3 fan-outs (`service.py:809-873`), k = 3 per
  fact; reported only for completeness.
Since k = 1 in B1 no collapse is expected; it is CHECKED, not assumed: each episode row records `plog_ack_count` (ack lines per site
after t0) and the cell summary `ack_lines_total` / `ack_lines_max_per_site_episode`. A reconcile round acks only if it applied
something, so one pending site-episode normally shows >= 1 ack line (up to 3 rounds); more events collapsed would show as extra
queued rows only through repeated acks and, above all, through `read_undercount_sites` and the tcpdump.

## Intervals (degraded, B1, observable = site-episodes with a pending delivery / site-episodes)
| Arm | f | k = 1 (B1, the one used) | for reference k = 2 | k = 3 |
|---|---|---|---|---|
| D | 0.185-0.226 | **0.0063-0.0115** (falsify outside CP [0.004, 0.015]) | 0.0126-0.0230 | 0.0189-0.0342 |
| C | 0.302-0.401 | **0.0275-0.0645** (falsify outside CP [0.025, 0.08]) | 0.0543-0.1248 | 0.0804-0.1812 |
| both, sensitivity (a3 false) f = 0.0975 | | 9.3e-4 | 1.9e-3 | 2.8e-3 |

The previous (per-delivery) version of the table is identical for k = 1 and is kept in `run.py` (docstring, prediction (c)) with the note
"superseded as to the observable by this file: the count is per site-episode because pending collapses". Other profiles (`regional`,
`wan`, `mixed`, `extreme`) keep their criteria (0 observed / >= 2 in the block / all pending); with k = 1 they are unchanged.

## Unit and test
n = (episodes x sites) per cell, per arm pooled over FANOUT only if the arms of FANOUT do not differ (same rule as (d)); the
intervals are Clopper-Pearson 95% on the site-episode proportion. Within an episode the ten deliveries are independent given the
loss process; cluster-level correlation is not modelled (declared).
