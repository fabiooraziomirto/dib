"""Dispute flood on the evaluated service (pre-registration: docs/audit/123 addendum 1).

Runs the UNCHANGED generator code/scripts/dispute_flood.py (--facts 100, 10 sites, plain
HTTP as it supports) 5 times, each on a fresh 1+10 container topology built from the tree
(sweep.up), with the service hash verified inside every container before and after. The
generator does not inspect the status of the legitimate reads; this wrapper counts HTTP
status codes from each container's uvicorn access log over the repetition.
"""
import collections
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "experiments_tnsm/site_sweep_20261013"))
import sweep  # noqa: E402

STATUS = re.compile(r'" (\d{3})')


def main() -> int:
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    man = {"prereg": "docs/audit/123 addendum 1", "started_utc": datetime.now(timezone.utc).isoformat(),
           "commit": sweep.run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip(),
           "generator_sha256": sweep.sha(ROOT / "code/scripts/dispute_flood.py"),
           "service_sha256_tree": sweep.sha(ROOT / "code/src/dib/registry/distributed/service.py"), "reps": []}
    for rep in range(reps):
        out = HERE / f"rep{rep}"
        out.mkdir(exist_ok=False)
        ids = sweep.up(10, False, Path("/nonexistent"), out)
        start = sweep.verify(ids)
        t0 = datetime.now(timezone.utc).isoformat()
        r = subprocess.run([sys.executable, str(ROOT / "code/scripts/dispute_flood.py"), "--facts", "100",
                            "--output-dir", str(out)], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        (out / "generator.log").write_text(r.stdout + r.stderr)
        codes = {}
        for svc, cid in ids.items():
            logs = subprocess.run(["docker", "logs", "--since", t0, cid], capture_output=True, text=True)
            codes[svc] = dict(collections.Counter(STATUS.findall(logs.stdout + logs.stderr)))
        end = sweep.verify(ids)
        sweep.down(out, 10)
        man["reps"].append({"rep": rep, "returncode": r.returncode, "status_codes": codes,
                            "service_in_containers": sorted({v["/app/service.py"] for v in list(start.values()) + list(end.values())}),
                            "loadavg": os.getloadavg()})
        (HERE / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    man["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (HERE / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
