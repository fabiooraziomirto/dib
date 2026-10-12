"""End-of-trial invariants of the lifecycle FSM as pure functions (docs/audit/90 sez. 5, written by the FSM session, executed there with 4 tests; adopted here unchanged in logic).
Formats: rows = {(site, score_id): {"state", "origin", "last_applied_seq"}} (absent key = 404); scores = {score_id: {"status", "fanout_seq"}};
pending = {(site, score_id): n}; events = [{"t", "op", "site", "score_id", "status"}] with op in {commit, local_revoke, local_restore, dispute, restore}.
Limits (audit 90): checked at the END of a trial, not at every step; ExportSafe is meaningful only if the site answered and its queue was empty; times must come from ONE clock (the driver's)."""
from __future__ import annotations

TRANSIENT = {"staging", "committing"}


def caught_up_is_coherent(rows, scores):
    bad = []
    for (site, sid), r in rows.items():
        sc = scores[sid]
        if r["last_applied_seq"] == sc["fanout_seq"]:
            if not (sc["status"] == "active" or r["state"] in ("disputed", "revoked")):
                bad.append(("CaughtUpIsCoherent", site, sid, r["state"], sc["status"]))
    return bad


def no_transient_left(rows):
    return [("TransientLeft", site, sid, r["state"]) for (site, sid), r in rows.items() if r["state"] in TRANSIENT]


def export_safe(rows, scores, pending):
    return [("ExportSafe", site, sid) for (site, sid), r in rows.items()
            if scores[sid]["status"] != "active" and pending.get((site, sid), 0) == 0 and r["state"] == "active"]


def _last(events, op, sid, site=None, ok=True):
    ts = [e["t"] for e in events if e["op"] == op and e["score_id"] == sid
          and (site is None or e["site"] == site) and (not ok or e["status"] == 200)]
    return max(ts) if ts else None


def no_active_without_commit_after_restore(rows, events):
    bad = []
    for (site, sid), r in rows.items():
        if r["state"] != "active":
            continue
        t_commit, t_restore = _last(events, "commit", sid, site), _last(events, "restore", sid)
        if t_commit is None:
            bad.append(("I1_ActiveWithoutCommit", site, sid))
        elif t_restore is not None and t_commit < t_restore:
            bad.append(("I3_StaleActiveAfterRestore", site, sid, t_commit, t_restore))
    return bad


def veto_preserved(rows, events):
    bad = []
    for (site, sid), r in rows.items():
        t_rv = _last(events, "local_revoke", sid, site)
        if t_rv is None:
            continue
        t_rs = _last(events, "local_restore", sid, site)
        if (t_rs is None or t_rs < t_rv) and (r["state"], r["origin"]) != ("revoked", "local"):
            bad.append(("I3_VetoLost", site, sid, r["state"], r["origin"]))
    return bad


def confinement(rows, events):
    return [("I2_LocalOriginWithoutLocalRevoke", site, sid) for (site, sid), r in rows.items()
            if r["origin"] == "local" and _last(events, "local_revoke", sid, site) is None]


def all_checks(rows, scores, pending, events):
    return (caught_up_is_coherent(rows, scores) + no_transient_left(rows) + export_safe(rows, scores, pending)
            + no_active_without_commit_after_restore(rows, events) + veto_preserved(rows, events)
            + confinement(rows, events))
