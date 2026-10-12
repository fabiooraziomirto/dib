"""classify_log / is_httpx_error of diag_setup500.py (audit 101). Hypotheses: the last traceback of a container log is parsed to its final exception line and the last service.py frame; a log without
traceback gives (None, None); httpx.* and httpcore.* count as httpx errors, anything else does not."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diag_setup500 as d  # noqa: E402

LOG = """INFO: x
Traceback (most recent call last):
  File "/app/dib/registry/distributed/service.py", line 100, in a
    pass
  File "/usr/lib/python3/httpx/_transports/default.py", line 1, in handle
    raise
httpx.ConnectTimeout: timed out
INFO: after
Traceback (most recent call last):
  File "/app/dib/registry/distributed/service.py", line 501, in query
    score = _evidence_get_score()
  File "/usr/lib/python3/httpcore/_exceptions.py", line 2, in map
    raise
httpcore.ReadTimeout
"""


def test_last_traceback_and_frame():
    c = d.classify_log(LOG)
    assert c["exception"] == "httpcore.ReadTimeout" and "line 501" in c["frame"]


def test_no_traceback():
    assert d.classify_log("INFO: only\n") == {"exception": None, "frame": None}


def test_httpx_error():
    assert d.is_httpx_error("httpx.ConnectTimeout: timed out") and d.is_httpx_error("httpcore.ReadTimeout")
    assert not d.is_httpx_error("KeyError: 'x'") and not d.is_httpx_error(None)


def test_docker_timestamps_are_stripped():
    """Audit 102: `docker logs -t` lines start with a timestamp; the first classifier returned (None, None) on the real logs."""
    ts = "2026-10-12T13:20:58.981536510Z "
    log = "\n".join(ts + l for l in LOG.splitlines())
    c = d.classify_log(log)
    assert c["exception"] == "httpcore.ReadTimeout" and "line 501" in c["frame"]
