"""Rerun of the restoration-policy ablation and the offline-veto campaign on the
reference service (pre-registration: docs/audit/119, sez. 4).

Hypotheses A1-A7 and their criteria are in audit 119; this wrapper does not
judge them (analyze.py does). It runs the two UNMODIFIED generators
(code/scripts/v36_restore_ablation.py, code/scripts/offline_veto_reconciliation.py)
as subprocesses with the reference interpreter, without retries, and writes a
manifest with: commit and diff state, sha256 of the service file each generator
actually loads (TestClient: the SOURCE path; uvicorn subprocesses: the
find_spec origin under the same PYTHONPATH), generator hashes, interpreter,
host, load average, start/end times and the generators' return codes.

Falsification: any non-zero return code is a failed case (kept, with its log).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
SERVICE = CODE / "src/dib/registry/distributed/service.py"
GENERATORS = {
    "restore_ablation": CODE / "scripts/v36_restore_ablation.py",
    "offline_veto": CODE / "scripts/offline_veto_reconciliation.py",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def module_origin(python: str) -> str:
    """Where `import dib.registry.distributed.service` resolves in the generators' subprocesses
    (offline_veto sets PYTHONPATH=code/src); find_spec does not execute the module."""
    env = dict(os.environ, PYTHONPATH=str(CODE / "src"))
    out = subprocess.run([python, "-c", "import importlib.util as u;"
                          "print(u.find_spec('dib.registry.distributed.service').origin)"],
                         env=env, capture_output=True, text=True, check=True, cwd="/")
    return out.stdout.strip()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--trials", type=int, default=30)
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    origin = module_origin(a.python)
    manifest = {
        "prereg": "docs/audit/119_congelamento_e_prereg_rerun_lifecycle.md sez. 4",
        "commit": git("rev-parse", "HEAD"),
        "dirty_files": git("status", "--porcelain").splitlines(),
        "service_sha256_tree": sha(SERVICE),
        "subprocess_module_origin": origin,
        "subprocess_module_sha256": sha(Path(origin)),
        "generators_sha256": {k: sha(v) for k, v in GENERATORS.items()},
        "python": subprocess.run([a.python, "-c", "import platform;print(platform.python_version())"],
                                 capture_output=True, text=True, check=True).stdout.strip(),
        "host": {"platform": platform.platform(), "nproc": os.cpu_count(), "loadavg_start": os.getloadavg()},
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "runs": {},
    }
    env = dict(os.environ, PYTHONPATH=str(CODE / "src"), PYTHONDONTWRITEBYTECODE="1")
    commands = {
        "restore_ablation": [a.python, str(GENERATORS["restore_ablation"]), "--output", str(a.out / "restore_ablation.json")],
        "offline_veto": [a.python, str(GENERATORS["offline_veto"]), "--trials", str(a.trials),
                         "--output", str(a.out / "offline_veto.json")],
    }
    for name, cmd in commands.items():
        t0 = time.monotonic()
        with (a.out / f"{name}.log").open("w") as log:
            rc = subprocess.run(cmd, cwd=CODE / "scripts", env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        result = a.out / f"{name}.json"
        manifest["runs"][name] = {
            "command": [Path(c).name if c.startswith(str(ROOT)) else c for c in cmd],
            "returncode": rc, "wall_s": round(time.monotonic() - t0, 2),
            "result_sha256": sha(result) if result.exists() else None,
        }
    manifest["host"]["loadavg_end"] = os.getloadavg()
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return max(r["returncode"] for r in manifest["runs"].values())


if __name__ == "__main__":
    raise SystemExit(main())
