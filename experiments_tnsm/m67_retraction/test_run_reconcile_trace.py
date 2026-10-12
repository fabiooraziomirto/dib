"""reconcile_trace (audit 99 addendum 3): per b2kill trial, the times (relative to t_start) and statuses of ALL evidence access-log lines `GET /pending/site-3` and `POST /pending/site-3/ack` after t_start,
so that a convergence tail (audit 99 / first violation of (e): 7.097 s against 7.0 s, first evidence pull at +1.62 s, withdrawal 5.48 s later) can be read from the data instead of inferred. Measurement only.
Hypotheses (falsified by any failing assertion): R-1 the trace lists every pull and ack with t >= t_start, in time order, with their statuses (not only the 200s); R-2 lines before t_start are excluded;
R-3 an empty log gives {"pulls": [], "acks": []}; R-4 the existing field t_first_reconcile_pull is unchanged (first 200 pull)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


def _log(entries):
    # docker logs -t style access lines as parse_access_lines reads them: use the module's own parser through a fake
    return entries


def test_trace(monkeypatch):
    t0 = 1000.0
    lines = {("GET", "/pending/site-3"): [(999.0, "/pending/site-3", 200), (1001.6, "/pending/site-3", 200), (1006.8, "/pending/site-3", 200), (1007.3, "/pending/site-3", 503)],
             ("POST", "/pending/site-3/ack"): [(1002.0, "/pending/site-3/ack", 200), (1006.9, "/pending/site-3/ack", 404)]}
    monkeypatch.setattr(r, "parse_access_lines", lambda logs, method, path: lines[(method, path)])
    tr = r.reconcile_trace("LOG", t0)
    assert tr["pulls"] == [[1.6, 200], [6.8, 200], [7.3, 503]]
    assert tr["acks"] == [[2.0, 200], [6.9, 404]]
    assert all(x[0] >= 0 for x in tr["pulls"] + tr["acks"])


def test_empty(monkeypatch):
    monkeypatch.setattr(r, "parse_access_lines", lambda *a: [])
    assert r.reconcile_trace("", 1.0) == {"pulls": [], "acks": []}
