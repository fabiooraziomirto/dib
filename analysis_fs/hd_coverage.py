"""Passo 0.4: per-corpus median k_tol and share of device types meeting the
coverage requirement for k = 1, 2, 3 (h_d > 7k/5 at 5/12, h_d >= 7k/3 at f_s).

Run: python3 analysis_fs/hd_coverage.py   (reads out/hd_by_device.csv, <1 s)
Hypothesis (stated before running): only the UNSW pseudo-site split meets the
requirement for k=3 on most types; corpora with 1-3 sites meet it for none.
"""
from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"


def main() -> None:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in csv.DictReader((OUT / "hd_by_device.csv").open()):
        groups["unsw_10pseudo_all_seeds" if r["corpus"].startswith("unsw") else r["corpus"]].append(r)
    rows = []
    for corpus, rs in groups.items():
        kt = [int(r["k_tol_5_12"]) for r in rs]
        kf = [int(r["k_tol_fs030"]) for r in rs]
        row = {"corpus": corpus, "rows": len(rs), "h_med": st.median(int(r["h_d"]) for r in rs),
               "k_tol_5_12_med": st.median(kt), "k_tol_fs_med": st.median(kf)}
        for k in (1, 2, 3):
            row[f"cov_k{k}_5_12"] = round(sum(x >= k for x in kt) / len(rs), 3)
            row[f"cov_k{k}_fs"] = round(sum(x >= k for x in kf) / len(rs), 3)
        rows.append(row)
        print(row)
    with (OUT / "hd_coverage_requirement.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
