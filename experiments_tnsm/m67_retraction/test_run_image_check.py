"""The containers must run the tree's service.py (audit 104). FOUND 2026-10-12: `docker compose up -d` reused the image built on 2026-10-10, so every node run since then executed service.py
sha256 31863043... whatever the tree said. Hypotheses (falsified by any failing assertion):
 I-1  Env.up() builds: the `up` command carries --build (images are rebuilt from the tree's code; unchanged layers are cached);
 I-2  Env.verify_service_image() runs `docker exec <container> sha256sum /app/service.py` for the evidence and the 10 sites and returns {container: sha256};
 I-3  it raises ImageMismatch naming the containers when any sha256 differs from the tree's code/src/dib/registry/distributed/service.py, and returns normally when all are equal;
 I-4  the manifest/cell record carries the verified sha256 (cell_image_field(sha) = {"image_service_sha256": sha}).
"""
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as r  # noqa: E402


def _env(tmp_path, monkeypatch, shas):
    svc = tmp_path / "code/src/dib/registry/distributed"
    svc.mkdir(parents=True, exist_ok=True)
    (svc / "service.py").write_text("print('x')\n")
    want = hashlib.sha256((svc / "service.py").read_bytes()).hexdigest()
    monkeypatch.setenv("HOME", str(tmp_path))
    env = r.Env(str(tmp_path), "C", 10, 5.0, tmp_path / "pki")
    calls = []

    def sh(cmd, check=True, timeout=300):
        calls.append(cmd)
        for name, sha in shas(want).items():
            if f"exec {name} " in cmd or f"exec -i {name} " in cmd:
                return f"{sha}  /app/service.py\n"
        return ""
    env.sh = sh
    return env, calls, want


NAMES = ["dibtnsm-evidence-1"] + [f"dibtnsm-site-{i}-1" for i in range(10)]


def test_i1_up_builds(tmp_path, monkeypatch):
    env, calls, _ = _env(tmp_path, monkeypatch, lambda w: {})
    env.up()
    assert any("up -d --build" in c for c in calls)


def test_i2_i3_verify(tmp_path, monkeypatch):
    env, calls, want = _env(tmp_path, monkeypatch, lambda w: {n: w for n in NAMES})
    out = env.verify_service_image()
    assert out == {n: want for n in NAMES} and len([c for c in calls if "sha256sum /app/service.py" in c]) == 11
    env, _, want = _env(tmp_path, monkeypatch, lambda w: {**{n: w for n in NAMES}, "dibtnsm-site-3-1": "31863043" + "0" * 56, "dibtnsm-evidence-1": "31863043" + "0" * 56})
    with pytest.raises(r.ImageMismatch) as ei:
        env.verify_service_image()
    assert "dibtnsm-site-3-1" in str(ei.value) and "dibtnsm-evidence-1" in str(ei.value) and "dibtnsm-site-4-1" not in str(ei.value)


def test_i4_cell_field():
    assert r.cell_image_field({"a": "b"}) == {"image_service_sha256": {"a": "b"}}
