"""Distributed prototype: N site processes + 1 evidence process, each a
real OS process (a Docker container in the deployed version), talking over
HTTP instead of sharing SQLite files. This replaces the ATTACH-based
sharded_prototype.py, whose cross-process file-sharing caused pathological
contention under real multi-process load (measured: N_SITES=10 performed
*worse* than N_SITES=1 once workers were genuine OS processes, not GIL-bound
threads -- see sharded_concurrency_benchmark_mp.py's results).

Design, addressing the reviewer-style critique that a naive ATTACH-to-HTTP
swap would just relocate the same bug class:

  - Single writer per site. The evidence service never touches a site's
    database. It only sends "apply this transition" requests over HTTP; each
    site is the only writer of its own local_decisions table, and applies
    the SAME provenance rule production services.py enforces centrally
    (Sec. III): a REVOKED decision whose origin is this site's own
    local_revoke is never overwritten by a fan-out event, only by this
    site's own local_restore. That check now lives where the record lives.

  - Idempotent, ordered fan-out. Every dispute/restore bumps a per-score
    monotonic fanout_seq at the evidence service. Each HTTP fan-out call
    carries that seq; a site ignores (no-ops) any call whose seq is <= the
    last one it already applied for that score_id -- a retried or duplicated
    call is a safe no-op, not a double-apply.

  - Explicit CP choice, not silent AP. A dispute/restore fans out
    synchronously with bounded retries per site (see _FANOUT_RETRIES/
    _FANOUT_TIMEOUT_S below). A site that is still unreachable after that
    budget is recorded in the evidence service's pending-fanout outbox
    (keyed by (site_id, score_id), overwritten with the latest target state
    -- reconciliation only needs the current truth, not full history) rather
    than blocking forever or silently dropping the update. A site pulls
    GET /pending/{site_id} (POST /reconcile, or the automatic trigger below)
    and applies whatever is queued through the identical idempotent apply
    path. This means I3 ("dispute immediately clears export eligibility...
    across all sites") is honest only as "immediately at every reachable
    site; a partitioned site converges once it reconciles" -- the
    fault-injection experiment (fault_injection_experiment.py) measures
    exactly that convergence window, rather than leaving it an unstated
    assumption.

  - Acknowledgement is per (score_id, seq) actually applied, not per site
    (audit D12). A site's POST /reconcile acks only the (score_id, seq)
    pairs it applied without error; the evidence service deletes a queued
    row only if it has the same score_id and a seq <= the acked one, so an
    event queued after the site's GET /pending survives the ack. seq is
    per fact (scores.fanout_seq), never comparable across facts. An ack
    without a body keeps the legacy "delete everything for the site"
    behaviour. After the ack /reconcile pulls again, at most
    _RECONCILE_MAX_ROUNDS rounds in total; an event arriving after the last
    pull stays queued until the next /reconcile call.

  - Automatic reconcile trigger (audit 05). WITHOUT CONFIGURATION THIS SERVICE
    HAS UNBOUNDED STALENESS: with DIB_DIST_RECONCILE_INTERVAL unset or 0 nothing
    calls /reconcile on its own and a site converges only when an external
    caller does. With T = DIB_DIST_RECONCILE_INTERVAL > 0 the site role runs
    _reconcile_once from a background trigger (FastAPI lifespan): first run
    after U(0, J) seconds (J = DIB_DIST_RECONCILE_JITTER, default 0.1*T), then
    T + U(0, J) after the end of each successful run; an unreachable evidence
    service is retried with exponential backoff (1 s, 2 s, ... capped at
    min(T, 30 s)). Runs never overlap (single flight): a manual /reconcile
    holds the same lock and may wait up to d_run (503 after
    DIB_DIST_RECONCILE_LOCK_TIMEOUT). Declared bound, for an event already in
    the outbox and a site that is running and reaches the evidence service:
    staleness <= T + J + 2*d_run, d_run = duration of one _reconcile_once
    (to be measured; theoretical worst case with the 5 s timeouts of
    DIB_DIST_RECONCILE_TIMEOUT is ~30 s). Run ONE worker process per site:
    --workers N would start N triggers.

  - State-based anti-entropy (audit 06, D19). The bound above holds from the
    COMMIT of the status change at the evidence service, not from the outbox
    insert: GET /pending also returns "current", the (seq, event, target
    state) of every fact with fanout_seq > 0, read in the same transaction as
    the outbox rows, and _reconcile_once applies any item newer than the
    site's last_applied_seq through the same _apply_fanout_row (seq check,
    local veto, origin rule). This recovers an event lost between the status
    commit and _fan_out, or whose outbox insert failed. A 500 from /dispute or
    /restore does NOT imply the state was left unchanged, and a client retry
    does not redo the fan-out (the second /dispute returns applied=false, the
    second /restore 409): only the anti-entropy repairs it. Still outside the
    bound: T = 0, a stopped site process, an evidence service the site cannot
    reach (the bound restarts when it is reachable), loss of the evidence
    database. Several missed events collapse to the final state.

  - Fan-out concurrency (audit D11). DIB_DIST_FANOUT_CONCURRENCY (default
    min(N_SITES, 16), docs/audit/62; it was 1 until 2026-10-12) is the size of
    ONE module-wide thread pool shared by all fan-outs; with 1 the delivery is
    the historical sequential loop. With cap > 1 every
    dispute/restore still answers only after all sites were tried, but down
    sites no longer delay the others: worst case ceil(k_down / cap) * 3 s
    (3 attempts x 1 s timeout) instead of k_down * 3 s.
"""
from __future__ import annotations

import logging
import os
import random
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

STATUS_ACTIVE = "active"
STATUS_DISPUTED = "disputed"
STATUS_REVOKED = "revoked"

DECISION_MONITOR_ONLY = "monitor-only"
DECISION_ACTIVE = "active"
DECISION_DISPUTED = "disputed"
DECISION_REVOKED = "revoked"

ORIGIN_LOCAL = "local"
ORIGIN_FANOUT = "fanout"

_FANOUT_RETRIES = 3
_FANOUT_TIMEOUT_S = 1.0
_RECONCILE_MAX_ROUNDS = 3  # pull/apply/ack rounds per /reconcile call (audit D12)

DATA_DIR = Path(os.environ.get("DIB_DIST_DATA_DIR", "/data"))
N_SITES = int(os.environ.get("DIB_DIST_N_SITES", "10"))
SUSPENSION_QUORUM = int(os.environ.get("DIB_DIST_SUSPENSION_QUORUM", "1"))
if SUSPENSION_QUORUM not in (1, 2):
    raise ValueError("DIB_DIST_SUSPENSION_QUORUM must be 1 or 2")
ROLE = os.environ.get("DIB_DIST_ROLE", "site")  # "site" or "evidence"
SITE_INDEX = int(os.environ.get("DIB_DIST_SITE_INDEX", "0"))
EVIDENCE_URL = os.environ.get("DIB_DIST_EVIDENCE_URL", "http://evidence:8000")


def _env_float(name: str, default: float, *, minimum: float = 0.0, exclusive: bool = False) -> float:
    value = float(os.environ.get(name, default))
    if value < minimum or (exclusive and value == minimum):
        raise ValueError(f"{name} must be {'>' if exclusive else '>='} {minimum}")
    return value


# Automatic reconcile trigger (audit 05). 0 = disabled: unbounded staleness (see docstring).
RECONCILE_INTERVAL = _env_float("DIB_DIST_RECONCILE_INTERVAL", 0.0)
RECONCILE_JITTER = _env_float("DIB_DIST_RECONCILE_JITTER", 0.1 * RECONCILE_INTERVAL)
RECONCILE_TIMEOUT = _env_float("DIB_DIST_RECONCILE_TIMEOUT", 5.0, exclusive=True)
RECONCILE_LOCK_TIMEOUT = _env_float("DIB_DIST_RECONCILE_LOCK_TIMEOUT", 60.0)
FANOUT_CONCURRENCY = int(os.environ.get("DIB_DIST_FANOUT_CONCURRENCY", str(min(N_SITES, 16))))  # default: one slot per site (cap 16); 1 = historical sequential path
if FANOUT_CONCURRENCY < 1:
    raise ValueError("DIB_DIST_FANOUT_CONCURRENCY must be >= 1")
# Persistent fan-out connections (docs/audit/62). OFF by default: with DIB_DIST_FANOUT_KEEPALIVE unset or 0 every delivery attempt opens a fresh
# connection exactly as before. With 1 the evidence service keeps one httpx.Client per site and (WARM_INTERVAL > 0) a daemon thread per site sends
# GET /health on it every WARM_INTERVAL seconds, so a withdrawal usually finds a warm connection (no TCP/TLS handshake, no handshake loss).
FANOUT_KEEPALIVE = os.environ.get("DIB_DIST_FANOUT_KEEPALIVE", "0") == "1"
WARM_INTERVAL = _env_float("DIB_DIST_FANOUT_WARM_INTERVAL", 2.0)

# Mutual TLS and certificate-based authorization (docs/audit/13_mtls_design.md). Off by
# default: with DIB_DIST_MTLS unset or 0 no request is checked and no outgoing call changes,
# so the existing tests and results keep their meaning. With DIB_DIST_MTLS=1 the service is
# served by ``python -m dib.registry.distributed.mtls`` (client certificate required), the
# caller is the SAN URI of its certificate mapped by DIB_DIST_IDENTITIES, and outgoing calls
# present DIB_DIST_TLS_CERT. DIB_DIST_TYPE_LIST=1 (requires mTLS) also limits /attest and
# /dispute to the device types listed for the caller's site (audit 13 sez. 3.2, Q5).
MTLS = os.environ.get("DIB_DIST_MTLS", "0") == "1"
TYPE_LIST = os.environ.get("DIB_DIST_TYPE_LIST", "0") == "1"
if TYPE_LIST and not MTLS:
    raise ValueError("DIB_DIST_TYPE_LIST=1 requires DIB_DIST_MTLS=1")
_HTTP_TLS: dict = {}  # extra keyword arguments of every outgoing httpx call
_identities = None
if MTLS:
    from dib.registry.distributed import mtls as _mtls

    _identities = _mtls.Identities(os.environ["DIB_DIST_IDENTITIES"])
    _HTTP_TLS = {"verify": _mtls.client_context(
        os.environ["DIB_DIST_TLS_CERT"], os.environ["DIB_DIST_TLS_KEY"], os.environ["DIB_DIST_TLS_CA"])}


def _authorize(request: Request, *, roles: tuple[str, ...] = (), site_roles: tuple[str, ...] = (),
               site: str | None = None) -> dict | None:
    """None when mTLS is off. Otherwise the caller's mapping entry if its role is in
    ``roles``, or in ``site_roles`` with the entry's site equal to ``site``; else 403."""
    if not MTLS:
        return None
    entry = _identities.resolve(_mtls.peer_sans(request.scope))
    if entry is not None and (entry["role"] in roles or (entry["role"] in site_roles and entry.get("site") == site)):
        return entry
    raise HTTPException(403, "caller not authorized")


_ANY_ROLE = ("member", "operator", "evidence", "consortium_admin")

_BACKOFF_BASE_S = 1.0
_BACKOFF_CAP_S = 30.0
_MIN_WAIT_S = 0.05  # floor of the trigger thread's wait: no busy loop
_LAST_ERROR_MAX = 200  # /health is unauthenticated: keep last_error short (see PRE_PUBLICATION_CHECKLIST)
_log = logging.getLogger("dib.distributed")


def _site_url(index: int) -> str:
    override = os.environ.get(f"DIB_DIST_SITE_URL_{index}")
    return override or f"http://site-{index}:8000"


class _Db:
    def __init__(self, path: Path, schema_sql: list[str]):
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(path), check_same_thread=False, timeout=10)
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA busy_timeout=10000")
        for stmt in schema_sql:
            self._con.execute(stmt)
        self._con.commit()

    def run(self, fn):
        with self._lock:
            try:
                result = fn(self._con)
                self._con.commit()
                return result
            except Exception:
                self._con.rollback()
                raise


class _ReconcileTrigger:
    """Schedules _reconcile_once on a site (audit 05). The scheduler is a plain object driven
    by tick(), with an injectable clock and rng, so tests need neither threads nor sleep;
    start() only wraps tick() in a daemon thread."""

    def __init__(self, interval: float, jitter: float, run, lock, clock=time.monotonic, rng=None):
        self.interval = interval
        self.jitter = jitter
        self._run = run
        self.lock = lock
        self.clock = clock
        self.rng = rng if rng is not None else random.Random()
        self.next_due: float | None = None  # None until arm()
        self.failures = 0
        self.last_error: str | None = None  # repr() of the last failure, truncated (audit 06)
        self.last_attempt_at: float | None = None
        self.last_success_at: float | None = None
        self.thread: threading.Thread | None = None
        self._stop = threading.Event()

    def arm(self) -> None:
        """Initial delay U(0, J): N sites started together do not pull together."""
        self.next_due = self.clock() + self.rng.uniform(0.0, self.jitter)

    def tick(self) -> bool:
        """One scheduler step. True iff an attempt was made (whatever its outcome)."""
        if self.next_due is None:
            self.arm()
        if self.clock() < self.next_due:
            return False
        if not self.lock.acquire(blocking=False):  # single flight: a run is already in progress
            self.next_due = self.clock() + min(1.0, self.interval)
            return False
        self.last_attempt_at = self.clock()
        try:
            try:
                self._run()
            except Exception as exc:  # noqa: BLE001 - a daemon must survive; the error is kept
                self.failures += 1
                self.last_error = repr(exc)[:_LAST_ERROR_MAX]
                # one WARNING per failed attempt (never per idle tick); traceback only for the first of a series
                _log.warning("reconcile attempt %d failed: %r", self.failures, exc,
                             exc_info=exc if self.failures == 1 else None)
                backoff = min(_BACKOFF_BASE_S * 2 ** min(self.failures - 1, 30), min(self.interval, _BACKOFF_CAP_S))
                self.next_due = self.clock() + backoff + self.rng.uniform(0.0, self.jitter)
            else:
                if self.failures:
                    _log.warning("reconcile recovered after %d failures", self.failures)
                self.failures = 0
                self.last_error = None
                self.last_success_at = self.clock()
                self.next_due = self.clock() + self.interval + self.rng.uniform(0.0, self.jitter)
        finally:
            self.lock.release()
        return True

    def snapshot(self) -> dict:
        """In-memory state for /health: no database, no network, no lock."""
        now = self.clock()
        return {
            "enabled": True,
            "consecutive_failures": self.failures,
            "last_error": self.last_error,
            "seconds_since_last_success": None if self.last_success_at is None else now - self.last_success_at,
            "thread_alive": self.thread is not None and self.thread.is_alive(),
            "next_due_in": None if self.next_due is None else self.next_due - now,
        }

    def _loop(self) -> None:
        while not self._stop.is_set():
            if self._stop.wait(max(self.next_due - self.clock(), _MIN_WAIT_S)):
                break
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - the thread must not die silently
                _log.error("reconcile loop error", exc_info=True)
                self.next_due = self.clock() + _BACKOFF_BASE_S  # no hot loop: at most one log per backoff

    def start(self) -> None:
        if self.thread is not None and self.thread.is_alive():
            return
        self._stop.clear()
        self.arm()
        self.thread = threading.Thread(target=self._loop, name="dib-reconcile-trigger", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self.thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)


_trigger: _ReconcileTrigger | None = None  # set in the site block when RECONCILE_INTERVAL > 0
_fanout_executor: ThreadPoolExecutor | None = None
_fanout_executor_lock = threading.Lock()


def _get_fanout_executor() -> ThreadPoolExecutor | None:
    """The ONE shared fan-out pool (global cap on deliveries in flight); None when the cap is 1."""
    global _fanout_executor
    if FANOUT_CONCURRENCY <= 1:
        return None
    with _fanout_executor_lock:
        if _fanout_executor is None:
            _fanout_executor = ThreadPoolExecutor(max_workers=FANOUT_CONCURRENCY, thread_name_prefix="dib-fanout")
        return _fanout_executor


def _shutdown_fanout_executor() -> None:
    global _fanout_executor
    with _fanout_executor_lock:
        executor, _fanout_executor = _fanout_executor, None
    if executor is not None:
        executor.shutdown(wait=True)


_WARM_TIMEOUT_S = 5.0   # longer than a delivery attempt: a ping delayed by one TCP retransmission must not drop a good connection (docs/audit/76)
_site_clients: dict = {}
_site_clients_lock = threading.Lock()
_warmer_threads: list = []
_warmer_stop = threading.Event()


def _new_site_client() -> httpx.Client:
    return httpx.Client(timeout=_FANOUT_TIMEOUT_S, limits=httpx.Limits(max_keepalive_connections=2, keepalive_expiry=max(30.0, 3 * WARM_INTERVAL)), **_HTTP_TLS)


def _site_client(i: int):
    """The cached persistent client of site i (created once, thread-safe)."""
    with _site_clients_lock:
        client = _site_clients.get(i)
        if client is None:
            client = _site_clients[i] = _new_site_client()
        return client


def _drop_site_client(i: int, client=None) -> None:
    """Close and forget the client of site i (only if it is still `client`, when given): the next attempt opens a fresh connection."""
    with _site_clients_lock:
        current = _site_clients.get(i)
        if current is None or (client is not None and current is not client):
            return
        del _site_clients[i]
    try:
        current.close()
    except Exception:  # noqa: BLE001 -- closing a broken connection must never raise into the delivery path
        pass


def _close_site_clients() -> None:
    for i in list(_site_clients):
        _drop_site_client(i)


def _warm_once(i: int) -> None:
    client = _site_client(i)
    try:
        client.get(f"{_site_url(i)}/health", timeout=_WARM_TIMEOUT_S)
    except httpx.HTTPError:
        _drop_site_client(i, client)


def _warm_loop(i: int) -> None:
    while not _warmer_stop.is_set():
        try:
            _warm_once(i)
        except Exception:  # noqa: BLE001 -- the warmer is best effort and must not die
            _log.exception("connection warmer failed for site-%d", i)
        _warmer_stop.wait(WARM_INTERVAL)


def _start_warmers() -> None:
    """One daemon thread per site; only the evidence role, only with KEEPALIVE and WARM_INTERVAL > 0."""
    if ROLE != "evidence" or not FANOUT_KEEPALIVE or WARM_INTERVAL <= 0 or _warmer_threads:
        return
    _warmer_stop.clear()
    for i in range(N_SITES):
        t = threading.Thread(target=_warm_loop, args=(i,), name=f"dib-warm-{i}", daemon=True)
        _warmer_threads.append(t)
        t.start()


def _stop_warmers() -> None:
    _warmer_stop.set()
    for t in _warmer_threads:
        t.join(timeout=5)
    _warmer_threads.clear()


@asynccontextmanager
async def _lifespan(_app):
    if _trigger is not None:
        _trigger.start()
    _start_warmers()
    try:
        yield
    finally:
        if _trigger is not None:
            _trigger.stop()
        _stop_warmers()
        _close_site_clients()
        _shutdown_fanout_executor()


app = FastAPI(title=f"DIB distributed prototype ({ROLE})", lifespan=_lifespan)


# --------------------------------------------------------------------------
# Site role
# --------------------------------------------------------------------------

if ROLE == "site":
    _site_db = _Db(
        DATA_DIR / "site.db",
        [
            "CREATE TABLE IF NOT EXISTS local_decisions ("
            " score_id INTEGER PRIMARY KEY, state TEXT, origin TEXT, last_applied_seq INTEGER DEFAULT 0,"
            " device_type TEXT, endpoint TEXT, protocol TEXT, port INTEGER)",
        ],
    )
    # D1 (audit 90): a crash between the two phases of /query or /commit leaves a transient row that no event would ever move (a `staging` row of a fact with
    # fanout_seq 0 is permanent). Nothing is in flight at startup, so: a reservation that was never closed is dropped (a new /query reserves again), a commit that was
    # never completed goes back to monitor-only (the abort path of /commit). Other states are untouched.
    _site_db.run(lambda con: (con.execute("DELETE FROM local_decisions WHERE state='staging'"),
                              con.execute("UPDATE local_decisions SET state=? WHERE state='committing'", (DECISION_MONITOR_ONLY,))))

    class ApplyFanout(BaseModel):
        score_id: int
        seq: int
        event_type: str  # "dispute" | "revoke" | "restore"
        target_state: str

    class QueryReq(BaseModel):
        device_type: str
        endpoint: str
        protocol: str = "https"
        port: int = 443

    def _site_id() -> str:
        return f"site-{SITE_INDEX}"

    def _evidence_get_score(device_type: str, endpoint: str, protocol: str = "https", port: int = 443) -> dict | None:
        try:
            resp = httpx.get(
                f"{EVIDENCE_URL}/scores",
                params={"device_type": device_type, "endpoint": endpoint, "protocol": protocol, "port": port},
                timeout=5.0, **_HTTP_TLS,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            # audit 102: a timeout, a refused connection or a failing evidence is a clean 503, never an unhandled 500 (7 of 50 mTLS setups at 5 % loss on the node)
            raise HTTPException(503, "evidence unreachable") from exc
        return resp.json()

    def _apply_fanout_row(con, score_id: int, seq: int, event_type: str, target_state: str) -> None:
        row = con.execute(
            "SELECT state, origin, last_applied_seq FROM local_decisions WHERE score_id=?", (score_id,)
        ).fetchone()
        if row is None:
            # No local record at this site for this fact -- nothing to fan out to.
            return
        state, origin, last_seq = row
        if seq <= last_seq:
            return  # already applied (or stale/duplicate) -- idempotent no-op
        if event_type == "restore" and state == DECISION_REVOKED and origin == ORIGIN_LOCAL:
            # Provenance guard, enforced locally: this site's own local_revoke
            # is never overwritten by a fan-out restore -- only local_restore can.
            con.execute("UPDATE local_decisions SET last_applied_seq=? WHERE score_id=?", (seq, score_id))
            return
        if event_type in ("dispute", "revoke") and state == DECISION_REVOKED and origin == ORIGIN_LOCAL:
            # Same guard for the opening/confirming dispute path (services.py's from_states check).
            con.execute("UPDATE local_decisions SET last_applied_seq=? WHERE score_id=?", (seq, score_id))
            return
        new_origin = None if target_state != DECISION_REVOKED else ORIGIN_FANOUT
        con.execute(
            "UPDATE local_decisions SET state=?, origin=?, last_applied_seq=? WHERE score_id=?",
            (target_state, new_origin, seq, score_id),
        )

    @app.post("/query")
    def query_score(req: QueryReq, request: Request):
        _authorize(request, site_roles=("operator",), site=_site_id())
        score = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        if score is None or not score["accepted"] or score["status"] != STATUS_ACTIVE:
            return {"applied": False}
        sid = score["id"]

        def reserve(con):
            if con.execute("SELECT 1 FROM local_decisions WHERE score_id=?", (sid,)).fetchone() is not None:
                return False
            con.execute(
                "INSERT INTO local_decisions"
                " (score_id, state, origin, last_applied_seq, device_type, endpoint, protocol, port)"
                " VALUES (?, 'staging', NULL, 0, ?, ?, ?, ?)",
                (sid, req.device_type, req.endpoint, req.protocol, req.port),
            )
            return True

        if not _reconcile_lock.acquire(timeout=RECONCILE_LOCK_TIMEOUT):  # D2 (audit 90): like /reconcile, a bounded wait, never an unbounded one
            raise HTTPException(503, "a reconcile is in progress")
        try:  # v5: no reservation between a reconcile apply and its ack
            reserved = _site_db.run(reserve)
        finally:
            _reconcile_lock.release()
        if not reserved:
            return {"applied": True, "score_id": sid}
        try:
            again = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        except Exception:
            _site_db.run(lambda con: con.execute(
                "DELETE FROM local_decisions WHERE score_id=? AND state='staging'", (sid,)))
            raise
        ok = again is not None and again["accepted"] and again["status"] == STATUS_ACTIVE

        def finish(con):
            row = con.execute(
                "SELECT state, last_applied_seq FROM local_decisions WHERE score_id=?", (sid,)).fetchone()
            if row is None:
                return
            if row[0] != "staging":
                # v6: a fan-out moved the reserved row; apply this read's snapshot through the same
                # seq guard, so an event that hit the row while it was Absent is not lost
                if again is not None:
                    ev = {STATUS_DISPUTED: ("dispute", DECISION_DISPUTED), STATUS_REVOKED: ("revoke", DECISION_REVOKED),
                          STATUS_ACTIVE: ("restore", DECISION_MONITOR_ONLY)}[again["status"]]
                    _apply_fanout_row(con, sid, again["fanout_seq"], ev[0], ev[1])
                return
            if ok:
                con.execute("UPDATE local_decisions SET state=?, last_applied_seq=? WHERE score_id=?",
                            (DECISION_MONITOR_ONLY, max(row[1], again["fanout_seq"]), sid))
            else:
                con.execute("DELETE FROM local_decisions WHERE score_id=?", (sid,))

        _site_db.run(finish)
        return {"applied": ok, "score_id": sid}

    @app.post("/commit")
    def operator_commit(req: QueryReq, request: Request):
        _authorize(request, site_roles=("operator",), site=_site_id())
        score = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        if score is None or not score["accepted"] or score["status"] != STATUS_ACTIVE:
            raise HTTPException(409, "global evidence is not admissible")

        sid, seq0 = score["id"], score["fanout_seq"]

        def phase1(con):
            row = con.execute(
                "SELECT state, last_applied_seq FROM local_decisions WHERE score_id=?", (sid,)).fetchone()
            if row is None or row[0] != DECISION_MONITOR_ONLY or row[1] > seq0:
                raise HTTPException(409, f"cannot commit: state is {row[0] if row else None!r}")
            con.execute("UPDATE local_decisions SET state='committing' WHERE score_id=?", (sid,))

        _site_db.run(phase1)
        try:
            again = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        except Exception:
            again = None
        promote = (again is not None and again["accepted"] and again["status"] == STATUS_ACTIVE
                   and again["fanout_seq"] == seq0)

        def phase2(con):
            row = con.execute("SELECT state FROM local_decisions WHERE score_id=?", (sid,)).fetchone()
            if row is None or row[0] != "committing":
                return False
            con.execute("UPDATE local_decisions SET state=? WHERE score_id=?",
                        (DECISION_ACTIVE if promote else DECISION_MONITOR_ONLY, sid))
            return promote

        if not _site_db.run(phase2):
            raise HTTPException(409, "the evidence changed during the commit")
        return {"applied": True}

    @app.post("/local_revoke")
    def local_revoke(req: QueryReq, request: Request):
        _authorize(request, site_roles=("operator",), site=_site_id())
        def txn(con):
            found = con.execute(
                "SELECT state, origin, score_id FROM local_decisions"
                " WHERE device_type=? AND endpoint=? AND protocol=? AND port=?",
                (req.device_type, req.endpoint, req.protocol, req.port)).fetchone()
            row = found[:2] if found else None
            score = {"id": found[2]} if found else None
            if row is None or not (
                row[0] in (DECISION_MONITOR_ONLY, DECISION_ACTIVE, DECISION_DISPUTED, "committing")
                or (row[0] == DECISION_REVOKED and row[1] == ORIGIN_FANOUT)
            ):
                raise HTTPException(409, f"cannot local-revoke: state is {row[0] if row else None!r}")
            con.execute(
                "UPDATE local_decisions SET state=?, origin=? WHERE score_id=?",
                (DECISION_REVOKED, ORIGIN_LOCAL, score["id"]),
            )

        _site_db.run(txn)
        return {"applied": True}

    @app.post("/local_restore")
    def local_restore(req: QueryReq, request: Request):
        _authorize(request, site_roles=("operator",), site=_site_id())
        score = _evidence_get_score(req.device_type, req.endpoint, req.protocol, req.port)
        if score is None:
            raise HTTPException(404, "unknown fact")
        if score["status"] in (STATUS_DISPUTED, STATUS_REVOKED):
            raise HTTPException(409, "a cross-site dispute episode is open")

        def txn(con):
            row = con.execute("SELECT state, origin, last_applied_seq FROM local_decisions WHERE score_id=?",
                              (score["id"],)).fetchone()
            if row is None or row[0] != DECISION_REVOKED or row[1] != ORIGIN_LOCAL:
                raise HTTPException(409, "not locally revoked")
            if row[2] > score["fanout_seq"]:
                raise HTTPException(409, "a newer lifecycle event arrived during the local restore")
            con.execute(
                "UPDATE local_decisions SET state=?, origin=NULL WHERE score_id=?",
                (DECISION_MONITOR_ONLY, score["id"]),
            )

        _site_db.run(txn)
        return {"applied": True}

    @app.post("/apply_fanout")
    def apply_fanout(req: ApplyFanout, request: Request):
        _authorize(request, roles=("evidence",))
        _site_db.run(lambda con: _apply_fanout_row(con, req.score_id, req.seq, req.event_type, req.target_state))
        return {"applied": True}

    def _repair_from_snapshot(current: list[dict], applied_seqs: dict[int, int]) -> int:
        """State-based anti-entropy (audit 06, D19): for every fact whose evidence seq is newer
        than the one this site applied, apply the evidence's current state through the same
        _apply_fanout_row as an outbox item (so the seq check, the local veto and the origin
        rule all hold). No ack: there is no outbox row to delete. Returns the number of items
        applied."""
        repaired = 0
        for item in current:
            last = applied_seqs.get(item["score_id"])
            if last is None or item["seq"] <= last:  # no local record, or nothing missed
                continue
            _site_db.run(
                lambda con, item=item: _apply_fanout_row(
                    con, item["score_id"], item["seq"], item["event_type"], item["target_state"]
                )
            )
            repaired += 1
        return repaired

    def _reconcile_once() -> tuple[int, int, int]:
        """Pull any events the evidence service could not deliver while this site was
        unreachable and apply them through the same idempotent path. Returns
        (items of the first pull, rounds that applied something, facts repaired from the
        evidence's current state).

        Each round is GET /pending, apply, ack of exactly the (score_id, seq)
        pairs applied without error (an item whose apply raised is never
        acked, so it stays queued; items applied before the error are acked).
        After a round that applied something the site pulls again, up to
        _RECONCILE_MAX_ROUNDS rounds, to pick up events queued meanwhile.
        After the rounds, the evidence's current state of every fact (the "current" list of
        the last GET, read in the same transaction as the outbox rows) is compared with this
        site's last_applied_seq and any newer state is applied: this recovers events that
        never reached the outbox (audit D19).
        Callers hold _reconcile_lock (the route and the trigger)."""
        first_pull = None
        rounds = 0
        current: list[dict] = []
        for _round in range(_RECONCILE_MAX_ROUNDS):
            resp = httpx.get(f"{EVIDENCE_URL}/pending/{_site_id()}", timeout=RECONCILE_TIMEOUT, **_HTTP_TLS)
            resp.raise_for_status()
            body = resp.json()
            pending = body["pending"]
            current = body.get("current", [])  # absent from an older evidence service
            if first_pull is None:
                first_pull = len(pending)
            if not pending:
                break
            rounds += 1
            applied = []
            try:
                for item in pending:
                    _site_db.run(
                        lambda con, item=item: _apply_fanout_row(
                            con, item["score_id"], item["seq"], item["event_type"], item["target_state"]
                        )
                    )
                    applied.append({"score_id": item["score_id"], "seq": item["seq"]})
            finally:
                if applied:
                    httpx.post(
                        f"{EVIDENCE_URL}/pending/{_site_id()}/ack", json={"applied": applied},
                        timeout=RECONCILE_TIMEOUT, **_HTTP_TLS,
                    )
        applied_seqs = {}
        if current:
            applied_seqs = dict(_site_db.run(
                lambda con: con.execute("SELECT score_id, last_applied_seq FROM local_decisions").fetchall()
            ))
        repaired = _repair_from_snapshot(current, applied_seqs)
        return first_pull, rounds, repaired

    _reconcile_lock = threading.Lock()

    @app.post("/reconcile")
    def reconcile(response: Response, request: Request):
        """Pull and apply the queued events now (the automatic trigger runs the same
        _reconcile_once). The JSON body keeps its original single field, ``reconciled`` =
        items of the first pull; the number of rounds that applied items is in the
        X-Dib-Reconcile-Rounds response header and the number of facts repaired from the
        evidence's current state in X-Dib-Reconcile-Repaired. Serialized with the trigger: a manual call
        may wait up to d_run for a run in progress; after DIB_DIST_RECONCILE_LOCK_TIMEOUT
        it answers 503 (never in normal operation)."""
        _authorize(request, site_roles=("operator",), site=_site_id())
        if not _reconcile_lock.acquire(timeout=RECONCILE_LOCK_TIMEOUT):
            raise HTTPException(503, "a reconcile is already in progress")
        try:
            first_pull, rounds, repaired = _reconcile_once()
        finally:
            _reconcile_lock.release()
        response.headers["X-Dib-Reconcile-Rounds"] = str(rounds)
        response.headers["X-Dib-Reconcile-Repaired"] = str(repaired)
        return {"reconciled": first_pull}

    if RECONCILE_INTERVAL > 0:
        _trigger = _ReconcileTrigger(RECONCILE_INTERVAL, RECONCILE_JITTER, _reconcile_once, _reconcile_lock)

    @app.get("/export_mud")
    def export_mud(request: Request, device_type: str, mud_url: str | None = None):
        """RFC 8520 MUD export for this site alone -- point 5 of the
        reviewer-style critique: reuses the same export_mud_file() the
        centralized registry uses (dib.evaluation.mud_export), fed from THIS
        site's own local_decisions instead of a direct SQLAlchemy session, so
        the OpenWrt/osMUD testbed can be driven from a real site container
        rather than only from the monolithic in-process path."""
        _authorize(request, site_roles=("operator",), site=_site_id())
        from dib.core.models import EndpointScore
        from dib.evaluation.mud_export import export_mud_file

        rows = _site_db.run(
            lambda con: con.execute(
                "SELECT endpoint, protocol, port FROM local_decisions"
                " WHERE state=? AND device_type=?",
                (DECISION_ACTIVE, device_type),
            ).fetchall()
        )
        scores = [
            EndpointScore(
                device_type=device_type, endpoint=endpoint, protocol=protocol, port=port,
                site_confidence=1.0, temporal_confidence=1.0, graph_confidence=0.0,
                score=1.0, accepted=True, supporting_sites=1, eligible_sites=1,
            )
            for endpoint, protocol, port in rows
        ]
        result = export_mud_file(device_type, scores, mud_url=mud_url)
        return result.document

    @app.get("/state/{score_id}")
    def get_state(score_id: int, request: Request):
        _authorize(request, roles=("consortium_admin",), site_roles=("operator",), site=_site_id())
        row = _site_db.run(
            lambda con: con.execute(
                "SELECT state, origin, last_applied_seq FROM local_decisions WHERE score_id=?", (score_id,)
            ).fetchone()
        )
        if row is None:
            raise HTTPException(404, "no local decision")
        return {"state": row[0], "origin": row[1], "last_applied_seq": row[2]}

    @app.get("/health")
    def health(request: Request):
        _authorize(request, roles=_ANY_ROLE)
        # In-memory state only: no database, no network (the evidence lock is contended by
        # disputes and GET /pending). last_error is unauthenticated: see PRE_PUBLICATION_CHECKLIST.
        reconcile = _trigger.snapshot() if _trigger is not None else {
            "enabled": False, "consecutive_failures": 0, "last_error": None,
            "seconds_since_last_success": None, "thread_alive": False, "next_due_in": None,
        }
        return {"status": "ok", "site_id": _site_id(), "reconcile": reconcile}


# --------------------------------------------------------------------------
# Evidence role
# --------------------------------------------------------------------------

if ROLE == "evidence":
    _evidence_db = _Db(
        DATA_DIR / "evidence.db",
        [
            "CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY, device_type TEXT, endpoint TEXT,"
            " protocol TEXT DEFAULT 'https', port INTEGER DEFAULT 443,"
            " status TEXT, disputed_by TEXT, positive_attestations INTEGER DEFAULT 0, fanout_seq INTEGER DEFAULT 0,"
            " accepted INTEGER DEFAULT 1, UNIQUE(device_type, endpoint, protocol, port))",
            "CREATE TABLE IF NOT EXISTS pending_fanout (site_id TEXT, score_id INTEGER, seq INTEGER,"
            " event_type TEXT, target_state TEXT, PRIMARY KEY (site_id, score_id))",
            "CREATE TABLE IF NOT EXISTS suspension_reports ("
            " score_id INTEGER, site_id TEXT NOT NULL, PRIMARY KEY (score_id, site_id))",
        ],
    )

    class SeedReq(BaseModel):
        device_type: str
        endpoint: str
        protocol: str = "https"
        port: int = 443

    class AckItem(BaseModel):
        score_id: int
        seq: int

    class AckReq(BaseModel):
        applied: list[AckItem]

    class ActionReq(BaseModel):
        device_type: str
        endpoint: str
        protocol: str = "https"
        port: int = 443
        site_id: str | None = None

    def _get_score_row(con, device_type: str, endpoint: str, protocol: str, port: int):
        return con.execute(
            "SELECT id, status, disputed_by, fanout_seq, accepted FROM scores"
            " WHERE device_type=? AND endpoint=? AND protocol=? AND port=?",
            (device_type, endpoint, protocol, port),
        ).fetchone()

    def _deliver_to_site(i: int, score_id: int, seq: int, event_type: str, target_state: str) -> None:
        """Up to _FANOUT_RETRIES attempts (timeout _FANOUT_TIMEOUT_S, no pause) to site i; if all
        fail, queue the event in the outbox (latest seq wins)."""
        site_id = f"site-{i}"
        delivered = False
        for _attempt in range(_FANOUT_RETRIES):
            try:
                body = {"score_id": score_id, "seq": seq, "event_type": event_type, "target_state": target_state}
                if FANOUT_KEEPALIVE:
                    client = _site_client(i)
                    try:
                        resp = client.post(f"{_site_url(i)}/apply_fanout", json=body, timeout=_FANOUT_TIMEOUT_S)
                    except httpx.HTTPError:
                        _drop_site_client(i, client)  # the next attempt opens a fresh connection
                        raise
                    except RuntimeError as exc:  # client closed by another thread: retry on a fresh one, as for a transport error
                        _drop_site_client(i, client)
                        raise httpx.TransportError(str(exc)) from exc
                else:
                    resp = httpx.post(f"{_site_url(i)}/apply_fanout", json=body, timeout=_FANOUT_TIMEOUT_S, **_HTTP_TLS)
                if resp.status_code == 200:
                    delivered = True
                    break
            except httpx.HTTPError:
                pass
        if not delivered:
            _evidence_db.run(
                lambda con: con.execute(
                    "INSERT INTO pending_fanout (site_id, score_id, seq, event_type, target_state)"
                    " VALUES (?, ?, ?, ?, ?)"
                    " ON CONFLICT(site_id, score_id) DO UPDATE SET seq=excluded.seq,"
                    " event_type=excluded.event_type, target_state=excluded.target_state"
                    " WHERE excluded.seq > pending_fanout.seq",
                    (site_id, score_id, seq, event_type, target_state),
                )
            )

    def _fan_out(score_id: int, seq: int, event_type: str, target_state: str) -> None:
        executor = _get_fanout_executor()
        if executor is None:  # FANOUT_CONCURRENCY == 1: the historical sequential loop
            for i in range(N_SITES):
                _deliver_to_site(i, score_id, seq, event_type, target_state)
            return
        futures = []
        for i in range(N_SITES):
            futures.append(executor.submit(_deliver_to_site, i, score_id, seq, event_type, target_state))
        first_error = None
        for future in futures:  # wait for ALL tasks, so none outlives the response
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001 - re-raised below, after every task finished
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error

    @app.post("/seed")
    def seed(req: SeedReq, request: Request):
        _authorize(request, roles=("consortium_admin",))
        def txn(con):
            cur = con.execute(
                "INSERT INTO scores (device_type, endpoint, protocol, port, status, accepted) VALUES (?, ?, ?, ?, ?, 1)",
                (req.device_type, req.endpoint, req.protocol, req.port, STATUS_ACTIVE),
            )
            return cur.lastrowid

        score_id = _evidence_db.run(txn)
        return {"id": score_id}

    @app.get("/scores")
    def get_score(request: Request, device_type: str, endpoint: str, protocol: str = "https", port: int = 443):
        _authorize(request, roles=("member", "operator", "consortium_admin"))
        row = _evidence_db.run(lambda con: _get_score_row(con, device_type, endpoint, protocol, port))
        if row is None:
            raise HTTPException(404, "unknown fact")
        return {"id": row[0], "status": row[1], "disputed_by": row[2], "fanout_seq": row[3], "accepted": bool(row[4])}

    @app.get("/scores/by_id/{score_id}")
    def get_score_by_id(score_id: int, request: Request):
        _authorize(request, roles=("member", "operator", "consortium_admin"))
        row = _evidence_db.run(
            lambda con: con.execute(
                "SELECT device_type, endpoint, protocol, port FROM scores WHERE id=?", (score_id,)
            ).fetchone()
        )
        if row is None:
            raise HTTPException(404, "unknown fact")
        return {"device_type": row[0], "endpoint": row[1], "protocol": row[2], "port": row[3]}

    def _reporter(request: Request, req: ActionReq) -> None:
        """With mTLS the reporting site is the caller's certificate site: a payload site_id
        naming another site is refused, and with DIB_DIST_TYPE_LIST=1 so is a fact whose
        device type is not listed for that site. Without mTLS: no-op (trusted harness)."""
        entry = _authorize(request, roles=("member", "operator"))
        if entry is None:
            return
        if req.site_id is not None and req.site_id != entry.get("site"):
            raise HTTPException(403, "site_id does not match the caller's certificate")
        req.site_id = entry.get("site")
        if TYPE_LIST and req.device_type not in entry.get("device_types", ()):
            raise HTTPException(403, "device type not declared for the caller's site")

    @app.post("/attest")
    def attest(req: ActionReq, request: Request):
        _reporter(request, req)
        def txn(con):
            row = _get_score_row(con, req.device_type, req.endpoint, req.protocol, req.port)
            if row is None:
                raise HTTPException(404, "unknown fact")
            con.execute(
                "UPDATE scores SET positive_attestations = positive_attestations + 1 WHERE id=?", (row[0],)
            )

        _evidence_db.run(txn)
        return {"applied": True}

    @app.post("/dispute")
    def dispute(req: ActionReq, request: Request):
        # Without mTLS the identity is supplied by the trusted harness; with mTLS it is the
        # caller's certificate (_reporter). Duplicate reports never add a vote.
        _reporter(request, req)
        if not req.site_id:
            raise HTTPException(422, "a reporting site is required")
        def txn(con):
            row = _get_score_row(con, req.device_type, req.endpoint, req.protocol, req.port)
            if row is None:
                raise HTTPException(404, "unknown fact")
            score_id, status, disputed_by, seq, _accepted = row
            if status == STATUS_ACTIVE:
                if SUSPENSION_QUORUM == 2:
                    con.execute("INSERT OR IGNORE INTO suspension_reports VALUES (?, ?)", (score_id, req.site_id))
                    votes = con.execute("SELECT COUNT(*) FROM suspension_reports WHERE score_id=?", (score_id,)).fetchone()[0]
                    if votes < SUSPENSION_QUORUM:
                        return None
                new_seq = seq + 1
                con.execute(
                    "UPDATE scores SET status=?, disputed_by=?, fanout_seq=? WHERE id=?",
                    (STATUS_DISPUTED, req.site_id, new_seq, score_id),
                )
                return score_id, new_seq, "dispute", DECISION_DISPUTED
            if status == STATUS_DISPUTED and req.site_id != disputed_by and (
                SUSPENSION_QUORUM == 1 or con.execute(
                    "SELECT 1 FROM suspension_reports WHERE score_id=? AND site_id=?",
                    (score_id, req.site_id)).fetchone() is None):
                new_seq = seq + 1
                con.execute("UPDATE scores SET status=?, fanout_seq=? WHERE id=?", (STATUS_REVOKED, new_seq, score_id))
                return score_id, new_seq, "revoke", DECISION_REVOKED
            return None

        result = _evidence_db.run(txn)
        if result:
            _fan_out(*result)
        return {"applied": result is not None}

    @app.post("/restore")
    def restore(req: ActionReq, request: Request):
        _authorize(request, roles=("consortium_admin",))
        def txn(con):
            row = _get_score_row(con, req.device_type, req.endpoint, req.protocol, req.port)
            if row is None:
                raise HTTPException(404, "unknown fact")
            score_id, status, _disputed_by, seq, _accepted = row
            if status not in (STATUS_DISPUTED, STATUS_REVOKED):
                raise HTTPException(409, f"cannot restore: status is {status!r}")
            new_seq = seq + 1
            con.execute(
                "UPDATE scores SET status=?, disputed_by=NULL, fanout_seq=? WHERE id=?",
                (STATUS_ACTIVE, new_seq, score_id),
            )
            con.execute("DELETE FROM suspension_reports WHERE score_id=?", (score_id,))
            return score_id, new_seq

        score_id, new_seq = _evidence_db.run(txn)
        _fan_out(score_id, new_seq, "restore", DECISION_MONITOR_ONLY)
        return {"applied": True}

    # status -> (event_type, target_state): the same mapping the dispute, revoke and restore
    # routes use for the fan-out.
    _STATUS_EVENT = {
        STATUS_DISPUTED: ("dispute", DECISION_DISPUTED),
        STATUS_REVOKED: ("revoke", DECISION_REVOKED),
        STATUS_ACTIVE: ("restore", DECISION_MONITOR_ONLY),
    }

    @app.get("/pending/{site_id}")
    def get_pending(site_id: str, request: Request):
        _authorize(request, site_roles=("member",), site=site_id)
        def txn(con):  # one transaction: the outbox rows and the current state are one snapshot
            rows = con.execute(
                "SELECT score_id, seq, event_type, target_state FROM pending_fanout WHERE site_id=?", (site_id,)
            ).fetchall()
            facts = con.execute("SELECT id, status, fanout_seq FROM scores WHERE fanout_seq > 0").fetchall()
            return rows, facts

        rows, facts = _evidence_db.run(txn)
        return {
            "pending": [{"score_id": r[0], "seq": r[1], "event_type": r[2], "target_state": r[3]} for r in rows],
            # Current state of every fact that ever had an event (audit 06, D19): lets a site recover an
            # event that never reached the outbox. Same item shape as "pending"; no ack.
            "current": [
                {"score_id": f[0], "seq": f[2], "event_type": _STATUS_EVENT[f[1]][0],
                 "target_state": _STATUS_EVENT[f[1]][1]}
                for f in facts if f[1] in _STATUS_EVENT
            ],
        }

    @app.post("/pending/{site_id}/ack")
    def ack_pending(site_id: str, request: Request, req: AckReq | None = None):
        _authorize(request, site_roles=("member",), site=site_id)
        def txn(con):
            if req is None:  # legacy caller (no body): acknowledge everything queued for the site
                con.execute("DELETE FROM pending_fanout WHERE site_id=?", (site_id,))
                return
            for item in req.applied:
                # Same fact and not newer than what the site applied; a row updated
                # after the site's GET (higher seq) or of another fact survives.
                con.execute(
                    "DELETE FROM pending_fanout WHERE site_id=? AND score_id=? AND seq<=?",
                    (site_id, item.score_id, item.seq),
                )

        _evidence_db.run(txn)
        return {"acked": True}

    @app.get("/health")
    def health(request: Request):
        _authorize(request, roles=_ANY_ROLE)
        return {"status": "ok"}
