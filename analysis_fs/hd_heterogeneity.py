"""Point 4: per-device-type reporting population h_d in the corpora used by the paper.

Run from repo root (local files only, no network; ~3 min, ~3 GB RAM):
    PYTHONPATH=code/src python3 analysis_fs/hd_heterogeneity.py \
        --data /root/Desktop/DIB/data/processed

Inputs (outside this repo, read-only):
  moniotr_full_observations.csv   site_id in {moniotr-us, -uk, -us-vpn, -uk-vpn}
  yourthings_observations.csv     one deployment
  real_federation_observations.csv six org labels (dib.adapters.real_federation)
  observations_enriched_item1fixed.csv  UNSW, input of the 20-seed A2 run
Mapping: docs/label_mapping_v16.csv (six aligned types, three deployments).

Hypothesis (stated before running): in the independent-deployment corpora
h_d <= 3 for every type, so the per-type tolerated k (k < 5/7 h_d) is at most
2 and k=3 always exceeds 5/12; in the UNSW 10-pseudo-site split h_d = 10
for all but the two sparse types the paper's older draft names.

Counting rule: a site is in ES_d iff it holds >=1 row of type d with an
endpoint (fqdn or remote_ip), the same rule DIBScorer uses (dib.py:198).
Per type, k=3 'exceeds 5/12' iff 3/(3+h_d) >= 5/12 (h_d <= 4); exceeds the
declared f_s iff 3/(3+h_d) > 0.30 (h_d <= 6). Tolerated k at the 5/12 limit:
largest k with k/(k+h_d) < 5/12; at f_s: largest k with k/(k+h_d) <= 0.30.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
REPO = Path(__file__).resolve().parents[1]


def tolerated(h: int, limit: Fraction, strict: bool) -> int:
    k = 0
    while True:
        share = Fraction(k + 1, k + 1 + h)
        if (share < limit) if strict else (share <= limit):
            k += 1
        else:
            return k


def row(corpus: str, device: str, sites: set[str]) -> dict:
    h = len(sites)
    return {"corpus": corpus, "device_type": device, "h_d": h, "sites": ";".join(sorted(sites)),
            "k_tol_5_12": tolerated(h, Fraction(5, 12), strict=True),
            "k_tol_fs030": tolerated(h, Fraction(3, 10), strict=False),
            "k3_share": round(3 / (3 + h), 4),
            "k3_exceeds_5_12": Fraction(3, 3 + h) >= Fraction(5, 12),
            "k3_exceeds_fs030": Fraction(3, 3 + h) > Fraction(3, 10)}


def presence(path: Path, site_of=None, device_of=None) -> dict[str, set[str]]:
    pres: dict[str, set[str]] = defaultdict(set)
    for chunk in pd.read_csv(path, usecols=["site_id", "device_type", "fqdn", "remote_ip"],
                             dtype=str, chunksize=1_000_000):
        chunk = chunk[chunk["fqdn"].notna() | chunk["remote_ip"].notna()]
        for site, dev in chunk[["site_id", "device_type"]].drop_duplicates().itertuples(index=False):
            s = site_of(site) if site_of else site
            d = device_of(dev) if device_of else dev
            if s is not None and d is not None:
                pres[d].add(s)
    return pres


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("/root/Desktop/DIB/data/processed"))
    p.add_argument("--unsw-seeds", type=int, default=20)
    a = p.parse_args()
    OUT.mkdir(exist_ok=True)
    rows: list[dict] = []

    collapse = {"moniotr-us": "US", "moniotr-us-vpn": "US", "moniotr-uk": "UK", "moniotr-uk-vpn": "UK"}
    mon = presence(a.data / "moniotr_full_observations.csv", site_of=collapse.get)
    rows += [row("moniotr_US_UK_collapsed", d, s) for d, s in sorted(mon.items())]
    mon_raw = presence(a.data / "moniotr_full_observations.csv")
    rows += [row("moniotr_4_capture_trees", d, s) for d, s in sorted(mon_raw.items())]

    yt = presence(a.data / "yourthings_observations.csv", site_of=lambda s: "YT")
    rows += [row("yourthings", d, s) for d, s in sorted(yt.items())]

    mapping = list(csv.DictReader((REPO / "docs" / "label_mapping_v16.csv").open()))
    for m in mapping:
        sites = set(mon.get(m["moniotr_label"], set())) | ({"YT"} if m["yourthings_label"] in yt else set())
        rows.append(row("three_lab_US_UK_YT", m["canonical"], sites))

    fed = presence(a.data / "real_federation_observations.csv")
    rows += [row("real_federation_6_labels", d, s) for d, s in sorted(fed.items())]
    pair = {"org_D_moniotr_usvpn": "org_B_moniotr_us", "org_E_moniotr_ukvpn": "org_C_moniotr_uk"}
    rows += [row("real_federation_independent", d, {pair.get(x, x) for x in s}) for d, s in sorted(fed.items())]

    # UNSW: replicate the 20-seed A2 run's partition (random round-robin, 10 sites).
    from dib.core.io import read_observations_csv
    from dib.simulator.sites import partition_observations
    obs = list(read_observations_csv(a.data / "observations_enriched_item1fixed.csv"))
    unsw_rows = []
    for seed in range(a.unsw_seeds):
        sites = partition_observations(obs, 10, strategy="random", seed=seed)
        pres: dict[str, set[str]] = defaultdict(set)
        for site in sites:
            for o in site.observations:
                if o.fqdn or o.remote_ip:
                    pres[o.device_type].add(site.site_id)
        for d, s in sorted(pres.items()):
            r = row(f"unsw_10pseudo_seed{seed}", d, s)
            r["sites"] = ""
            unsw_rows.append(r)
    rows += unsw_rows

    with (OUT / "hd_by_device.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    summary = []
    by_corpus: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        key = "unsw_10pseudo_all_seeds" if r["corpus"].startswith("unsw_10pseudo") else r["corpus"]
        by_corpus[key].append(r)
    for c, rs in by_corpus.items():
        hs = [r["h_d"] for r in rs]
        summary.append({"corpus": c, "n_rows(type x seed)": len(rs), "h_min": min(hs), "h_median": sorted(hs)[len(hs) // 2],
                        "h_max": max(hs),
                        "frac_types_k3_exceeds_5_12": round(sum(r["k3_exceeds_5_12"] for r in rs) / len(rs), 3),
                        "frac_types_k3_exceeds_fs030": round(sum(r["k3_exceeds_fs030"] for r in rs) / len(rs), 3),
                        "frac_types_h_le_2": round(sum(h <= 2 for h in hs) / len(hs), 3)})
    with (OUT / "hd_summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    for s in summary:
        print(s)
    sparse = sorted({(r["device_type"], r["h_d"]) for r in unsw_rows if r["h_d"] < 10})
    print("UNSW types with h_d<10 across seeds:", sparse)


if __name__ == "__main__":
    main()
