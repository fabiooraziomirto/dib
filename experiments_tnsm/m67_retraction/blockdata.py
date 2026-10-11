"""Analysis input of a block run (see test_blockdata.py). `load_block(dir)` returns (cells, manifest):
  * dir holds cells.jsonl + manifest.json (one run.py invocation): loaded as they are;
  * dir holds b1_*/ group directories (auto_block.py runs ONE run.py invocation per group; each numbers its cells from 1): the cells of every group
    directory that has a cells.jsonl and a manifest.json are merged in the order of the directory names, each cell gets a unique number (`cell_orig` keeps the
    original, `_group_dir` the directory), and the manifests' cells_summary entries are remapped to the new numbers, so that the per-cell fields read from
    the manifest (e.g. generator_path_flag) stay attached to the right cell. Header fields: earliest started_utc, latest finished_utc, aborted if any;
    the other header fields are those of the first group manifest."""
from __future__ import annotations

import json
from pathlib import Path


def load_block(d) -> tuple[list[dict], dict]:
    d = Path(d)
    if (d / "cells.jsonl").exists() and (d / "manifest.json").exists():
        return [json.loads(x) for x in (d / "cells.jsonl").read_text().splitlines() if x.strip()], json.loads((d / "manifest.json").read_text())
    groups = sorted(g for g in d.glob("b1_*") if (g / "cells.jsonl").exists() and (g / "manifest.json").exists())
    if not groups:
        raise FileNotFoundError(f"{d}: neither cells.jsonl+manifest.json nor b1_*/ group directories with both")
    cells, summary, mans, offset = [], [], [], 0
    for g in groups:
        cs = [json.loads(x) for x in (g / "cells.jsonl").read_text().splitlines() if x.strip()]
        man = json.loads((g / "manifest.json").read_text())
        mans.append(man)
        for c in cs:
            if "cell" in c:
                c["cell_orig"] = c["cell"]
                c["cell"] = c["cell"] + offset
            c["_group_dir"] = str(g)
        for e in man.get("cells_summary") or []:
            summary.append({**e, "cell": e["cell"] + offset})
        offset += max([c["cell_orig"] for c in cs if "cell_orig" in c] or [0])
        cells += cs
    merged = dict(mans[0])
    merged["cells_summary"] = summary
    merged["started_utc"] = min(m["started_utc"] for m in mans if m.get("started_utc"))
    merged["finished_utc"] = max((m["finished_utc"] for m in mans if m.get("finished_utc")), default=None)
    merged["aborted"] = any(m.get("aborted") for m in mans)
    return cells, merged
