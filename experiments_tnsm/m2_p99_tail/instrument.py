"""Per-operation timing decomposition for M2 (SQLAlchemy events; production code unchanged).

For every timed operation (one ``harness.timed_call``) on the calling thread it records:
  total_s             latency as the harness measures it;
  to_first_stmt_s     operation start -> start of its first SQL statement: session setup
                      plus WAITING FOR A POOLED CONNECTION (QueuePool 5+10, timeout 30 s);
  first_write_s       duration of the first INSERT/UPDATE/DELETE: in journal_mode=delete
                      this is where the RESERVED lock is taken, with SQLite's busy handler
                      polling up to busy_timeout (5 s);
  to_lock_s           operation start -> end of the first write statement ("time until
                      the write lock is held"); None for operations that never write;
  write_s / read_s    total time inside write / read statements;
  commit_s            time inside Session.commit() (EXCLUSIVE lock + journal fsync);
  attempts            re-executions of services._retry_on_conflict (as p99_tail_breakdown);
  error               exception type name ("" when none), thread name (the "writer").
"""
from __future__ import annotations

import threading
import time

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession

_tl = threading.local()
records: list[dict] = []
_lock = threading.Lock()
_WRITE = ("INSERT", "UPDATE", "DELETE", "REPLACE")


def _reset() -> None:
    _tl.active = True
    _tl.first_stmt = None
    _tl.first_write_start = None
    _tl.first_write_end = None
    _tl.write_s = 0.0
    _tl.read_s = 0.0
    _tl.commit_s = 0.0
    _tl.attempts = 0
    _tl.stmt_start = None
    _tl.stmt_is_write = False


def _before(conn, cursor, statement, parameters, context, executemany):
    if not getattr(_tl, "active", False):
        return
    now = time.perf_counter()
    if _tl.first_stmt is None:
        _tl.first_stmt = now
    _tl.stmt_start = now
    _tl.stmt_is_write = statement.lstrip().split(" ", 1)[0].upper() in _WRITE
    if _tl.stmt_is_write and _tl.first_write_start is None:
        _tl.first_write_start = now


def _end_stmt() -> None:
    if not getattr(_tl, "active", False) or _tl.stmt_start is None:
        return
    now = time.perf_counter()
    dt = now - _tl.stmt_start
    if _tl.stmt_is_write:
        _tl.write_s += dt
        if _tl.first_write_end is None:
            _tl.first_write_end = now
    else:
        _tl.read_s += dt
    _tl.stmt_start = None


def _after(conn, cursor, statement, parameters, context, executemany):
    _end_stmt()


def _error(exception_context):
    _end_stmt()


def install(harness, services, ptb) -> None:
    """Hook statement timing on every Engine and wrap timed_call, the retry loop and
    Session.commit (the last two exactly as code/scripts/p99_tail_breakdown.py does)."""
    event.listen(Engine, "before_cursor_execute", _before)
    event.listen(Engine, "after_cursor_execute", _after)
    event.listen(Engine, "handle_error", _error)
    orig_commit = SASession.commit
    orig_retry = services._retry_on_conflict
    orig_timed = harness.timed_call

    def timed_commit(self, *a, **k):
        started = time.perf_counter()
        try:
            return orig_commit(self, *a, **k)
        finally:
            if getattr(_tl, "active", False):
                _tl.commit_s += time.perf_counter() - started

    def counting_retry(session, attempt):
        def counted():
            if getattr(_tl, "active", False):  # seeding calls services outside timed_call
                _tl.attempts += 1
            return attempt()
        return orig_retry(session, counted)

    def timed_call(get_session, fn_name, *args, **kwargs):
        _reset()
        t0 = time.perf_counter()
        elapsed, result, err = orig_timed(get_session, fn_name, *args, **kwargs)
        _tl.active = False
        rec = {
            "op": fn_name, "thread": threading.current_thread().name, "total_s": elapsed,
            "to_first_stmt_s": (_tl.first_stmt - t0) if _tl.first_stmt is not None else None,
            "first_write_s": (_tl.first_write_end - _tl.first_write_start) if _tl.first_write_end else None,
            "to_lock_s": (_tl.first_write_end - t0) if _tl.first_write_end else None,
            "write_s": _tl.write_s, "read_s": _tl.read_s, "commit_s": _tl.commit_s,
            "attempts": max(1, _tl.attempts),
            "error": type(err).__name__ if err is not None else "",
            "business_rejection": isinstance(err, services.InvalidStateTransition),
        }
        with _lock:
            records.append(rec)
        return elapsed, result, err

    del ptb  # instrumentation re-implemented here with the same wrapping points
    SASession.commit = timed_commit
    services._retry_on_conflict = counting_retry
    harness.timed_call = timed_call
