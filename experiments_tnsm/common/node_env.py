"""Environment record for a measurement already run (M1 was launched before the manifest
gained these fields, audit 04 sez. 7.4): SQLite pragmas and pool parameters of the
engine the harness builds from the same deployed tree, filesystem and fsync latency of
the directory holding the cell databases, host and interpreter. Run right after the
measurement, on the same node, with the same interpreter.

    python node_env.py --code <deployed code/> --tmp-dir /tmp/dib_tnsm_db --out node_env.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cells  # noqa: E402
import node_monitor as nm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--code", required=True)
    p.add_argument("--tmp-dir", default="/tmp/dib_tnsm_db")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    harness = cells.import_harness(Path(a.code).resolve())
    tmp = Path(a.tmp_dir)
    tmp.mkdir(parents=True, exist_ok=True)
    env = {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "python_vv": sys.version.replace("\n", " "),
        "sqlite_version": __import__("sqlite3").sqlite_version,
        "host": nm.host_info(),
        "load": open("/proc/loadavg").read().strip(),
        "filesystem": nm.fs_info(str(tmp)),
        "fsync_bench": nm.fsync_bench(str(tmp)),
        "sqlite": cells.sqlite_settings(harness, tmp / "probe.db"),
    }
    Path(a.out).write_text(json.dumps(env, indent=1) + "\n")
    print(json.dumps(env, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
