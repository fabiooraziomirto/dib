"""Tests of blockdata.load_block (analysis input of a block run by auto_block.py: ONE run.py invocation PER GROUP, so a block directory holds b1_<arm>_f<fanout>/
cells.jsonl + manifest.json, each numbering its cells from 1). Hypotheses (declared first): L-1 a single-run directory (cells.jsonl + manifest.json) loads as
before; L-2 a block directory merges every b1_*/ group, giving cells unique numbers and remapping each manifest's cells_summary (the generator_path flags)
to them, in the registered group order of the directory names; L-3 header fields are merged (earliest start, latest finish, aborted if any); L-4 a missing
input raises, never an empty analysis. Falsification: any assertion failing."""
import json

import pytest

import blockdata as b


def mk(d, arm, fo, ts):
    d.mkdir(parents=True)
    (d / "cells.jsonl").write_text(json.dumps({"cell": 1, "cell_spec": {"arm": arm, "fanout": fo}, "rows": [], "summary": {}}) + "\n")
    (d / "manifest.json").write_text(json.dumps({"profile": "degraded", "started_utc": ts, "finished_utc": ts + "9", "aborted": False,
                                                "cells_summary": [{"cell": 1, "generator_path_flag": arm == "C"}], "run_py_sha256": "r"}))


def test_single_dir(tmp_path):
    mk(tmp_path / "one", "D", 1, "t1")
    cells, man = b.load_block(tmp_path / "one")
    assert len(cells) == 1 and man["profile"] == "degraded"


def test_block_dir_merges_groups_with_unique_numbers(tmp_path):
    blk = tmp_path / "degraded"
    mk(blk / "b1_C_f10", "C", 10, "2026-10-11T12:00")
    mk(blk / "b1_D_f1", "D", 1, "2026-10-11T12:30")
    mk(blk / "b1_D_f10", "D", 10, "2026-10-11T12:10")
    (blk / "b1_D_f1_retry1").mkdir()                                     # a retry dir without data: ignored
    cells, man = b.load_block(blk)
    assert [(c["cell_spec"]["arm"], c["cell_spec"]["fanout"]) for c in cells] == [("C", 10), ("D", 1), ("D", 10)]
    assert sorted(c["cell"] for c in cells) == [1, 2, 3] and len({c["cell"] for c in cells}) == 3
    flags = {x["cell"]: x["generator_path_flag"] for x in man["cells_summary"]}
    assert flags == {cells[0]["cell"]: True, cells[1]["cell"]: False, cells[2]["cell"]: False}      # remapped to the NEW numbers
    assert man["started_utc"] == "2026-10-11T12:00" and man["finished_utc"] == "2026-10-11T12:309" and man["aborted"] is False
    assert all("_group_dir" in c for c in cells)


def test_missing_input_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        b.load_block(tmp_path / "nothing")
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError):
        b.load_block(tmp_path / "empty")


def test_load_cells_needs_no_manifest(tmp_path):
    """The `lan` reference of rule (a) reads cells only: a directory with cells.jsonl alone, or b1_*/ groups with cells.jsonl alone."""
    (tmp_path / "one").mkdir()
    (tmp_path / "one" / "cells.jsonl").write_text(json.dumps({"cell": 1, "rows": []}) + "\n")
    assert len(b.load_cells(tmp_path / "one")) == 1
    for g in ("b1_C_f10", "b1_D_f10"):
        (tmp_path / "blk" / g).mkdir(parents=True)
        (tmp_path / "blk" / g / "cells.jsonl").write_text(json.dumps({"cell": 1, "rows": []}) + "\n")
    assert len(b.load_cells(tmp_path / "blk")) == 2
    with pytest.raises(FileNotFoundError):
        b.load_cells(tmp_path / "none")
