"""Fase 3 (TNSM): h_d over the union of the real corpora on disk, and how many
device types tolerate K = 1, 2, 3 colluders.

Run from repo root (local files only, no network; ~1-2 min):
    PYTHONPATH=code/src python3 analysis_fs/hd_union.py \
        --data /root/Desktop/DIB/data/processed \
        --private-out /root/Desktop/DIB/outputs/tnsm_hd

Inputs (outside this repo, read-only): observations_enriched.csv (UNSW),
moniotr_full_observations.csv (4 capture trees), yourthings_observations.csv,
and analysis_fs/out/hd_by_device.csv (per-corpus h_d, hd_heterogeneity.py).

Same type across sites: dib.evaluation.profiles.canonical_device_name
(profiles.py:142-194, lowercase + alias table), applied through the reused
dib.adapters.real_federation.find_overlap_devices with min_independent_orgs=1
(every type, not only shared ones). Sites: org labels of
real_federation.ORG_LABELS; "independent" collapses us/us-vpn and uk/uk-vpn
(NON_INDEPENDENT_PAIRS), so at most 4 independent sites exist (UNSW, US, UK,
YourThings). Sensitivity variant "plus_v16": additionally merge the
YourThings labels that docs/label_mapping_v16.csv aligns with Mon(IoT)r
(googlehomemini, insteonhub, rokutv are NOT merged by canonical_device_name;
the two mappings disagree, audit 11 sez. 2). Cross-check: presence restricted to rows with an endpoint
(fqdn or remote_ip), the rule of hd_heterogeneity.py and dib.py:198.

Tolerance rule (audit 11 sez. 1, H' verified on DIBScorer): with h honest
observers, K adversary-only reporters are always rejected by the score iff
K <= 5h/7 (tie included); the declared budget holds iff K/(K+h) <= 0.30;
the quorum m = 2 rejects K = 1 regardless of h.

Hypothesis (stated before running): with at most 4 independent sites, no
type has h >= 5, so K = 3 is never covered at the margin (needs h >= 5) and
K = 2 is never covered at f_s (needs h >= 5); most canonical types are seen
by one independent site only (median h = 1).
Falsified if: any type has h_indep >= 5, or more than half the types have
h_indep >= 2.

Outputs:
  analysis_fs/out/hd_union_histogram.csv   number of types per h (no labels)
  analysis_fs/out/hd_tolerance_k123.csv     per corpus: types covered for
                                            K = 1, 2, 3 (aggregates only)
  <private-out>/hd_union_by_type.csv        per-type labels, NOT in the repo
                                            (Mon(IoT)r data sharing agreement)
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

import pandas as pd

from dib.adapters.real_federation import NON_INDEPENDENT_PAIRS, ORG_LABELS, find_overlap_devices
from dib.evaluation.profiles import canonical_device_name

OUT = Path(__file__).resolve().parent / "out"
FS = Fraction(3, 10)
RATIO = Fraction(5, 7)


def independent(orgs: set[str]) -> set[str]:
    collapsed = set(orgs)
    for a, b in NON_INDEPENDENT_PAIRS:
        if a in collapsed and b in collapsed:
            collapsed.discard(b)
    return collapsed


def labels_and_endpoint_presence(path: Path, site_of) -> tuple[dict, dict]:
    """canonical type -> raw labels; canonical type -> orgs with >=1 endpoint row."""
    raw: dict[str, set[str]] = defaultdict(set)
    pres: dict[str, set[str]] = defaultdict(set)
    for chunk in pd.read_csv(path, usecols=["site_id", "device_type", "fqdn", "remote_ip"],
                             dtype=str, chunksize=1_000_000):
        chunk = chunk.assign(ep=chunk["fqdn"].notna() | chunk["remote_ip"].notna())
        for site, dev, ep in chunk[["site_id", "device_type", "ep"]].drop_duplicates().itertuples(index=False):
            org = site_of(site)
            if org is None or not isinstance(dev, str):
                continue
            c = canonical_device_name(dev)
            raw[c].add(dev)
            if ep:
                pres[c].add(org)
    return raw, pres


def covered(h: int, K: int) -> dict:
    return {"score": K <= RATIO * h, "fs": Fraction(K, K + h) <= FS}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("/root/Desktop/DIB/data/processed"))
    p.add_argument("--private-out", type=Path, default=Path("/root/Desktop/DIB/outputs/tnsm_hd"))
    a = p.parse_args()
    unsw = a.data / "observations_enriched.csv"
    mon = a.data / "moniotr_full_observations.csv"
    yt = a.data / "yourthings_observations.csv"

    presence = find_overlap_devices(unsw, mon, yt, min_independent_orgs=1)

    raw, ep_pres = {}, defaultdict(set)
    for path, site_of, tag in ((unsw, lambda s: ORG_LABELS["unsw"], "unsw"),
                               (mon, ORG_LABELS.get, "moniotr"),
                               (yt, lambda s: ORG_LABELS["yourthings"], "yourthings")):
        r, pr = labels_and_endpoint_presence(path, site_of)
        raw[tag] = r
        for c, orgs in pr.items():
            ep_pres[c] |= orgs

    v16 = {canonical_device_name(m["yourthings_label"]): canonical_device_name(m["moniotr_label"])
           for m in csv.DictReader((REPO / "docs" / "label_mapping_v16.csv").open())}
    merged: dict[str, set[str]] = defaultdict(set)
    for c, orgs in presence.items():
        merged[v16.get(c, c)] |= orgs
    v16_merges = sorted((a, b) for a, b in v16.items() if a != b and a in presence)

    rows = []
    for c in sorted(presence):
        orgs = presence[c]
        rows.append({"canonical": c, "orgs": ";".join(sorted(orgs)),
                     "h_trees": len(orgs), "h_indep": len(independent(orgs)),
                     "h_indep_endpoint_rows": len(independent(ep_pres.get(c, set()))),
                     "labels_unsw": ";".join(sorted(raw["unsw"].get(c, ()))),
                     "labels_moniotr": ";".join(sorted(raw["moniotr"].get(c, ()))),
                     "labels_yourthings": ";".join(sorted(raw["yourthings"].get(c, ())))})
    a.private_out.mkdir(parents=True, exist_ok=True)
    with (a.private_out / "hd_union_by_type.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    hist = []
    for col in ("h_trees", "h_indep", "h_indep_endpoint_rows"):
        counts = defaultdict(int)
        for r in rows:
            counts[r[col]] += 1
        hist += [{"corpus": f"union_canonical_{col}", "h": h, "n_types": n} for h, n in sorted(counts.items())]
    counts = defaultdict(int)
    for o in merged.values():
        counts[len(independent(o))] += 1
    hist += [{"corpus": "union_canonical_plus_v16_h_indep", "h": h, "n_types": n} for h, n in sorted(counts.items())]
    OUT.mkdir(exist_ok=True)
    with (OUT / "hd_union_histogram.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["corpus", "h", "n_types"])
        w.writeheader()
        w.writerows(hist)

    groups: dict[str, list[int]] = defaultdict(list)
    for r in csv.DictReader((OUT / "hd_by_device.csv").open()):
        groups["unsw_10pseudo_all_seeds" if r["corpus"].startswith("unsw") else r["corpus"]].append(int(r["h_d"]))
    groups["union_canonical_trees"] = [r["h_trees"] for r in rows]
    groups["union_canonical_independent"] = [r["h_indep"] for r in rows]
    groups["union_canonical_plus_v16_independent"] = [len(independent(o)) for o in merged.values()]
    tol = []
    for corpus, hs in groups.items():
        hs_sorted = sorted(hs)
        row = {"corpus": corpus, "n_rows": len(hs), "h_min": hs_sorted[0],
               "h_median": hs_sorted[len(hs) // 2], "h_max": hs_sorted[-1]}
        for K in (1, 2, 3):
            row[f"K{K}_score"] = sum(covered(h, K)["score"] for h in hs)
            row[f"K{K}_fs030"] = sum(covered(h, K)["fs"] for h in hs)
        row["K1_quorum_m2"] = len(hs)  # dib.py:45-46: K = 1 never reaches |S_e| >= 2
        tol.append(row)
    with (OUT / "hd_tolerance_k123.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tol[0]))
        w.writeheader()
        w.writerows(tol)

    for t in tol:
        print(t)
    print("union types:", len(rows), "h_indep>=2:", sum(r["h_indep"] >= 2 for r in rows),
          "h_indep>=5:", sum(r["h_indep"] >= 5 for r in rows),
          "endpoint-rule mismatches:", sum(r["h_indep"] != r["h_indep_endpoint_rows"] for r in rows))
    print("v16 merges applied (yourthings -> moniotr canonical):", v16_merges)
    print("min h for K=1,2,3 (score):", [math.ceil(Fraction(7 * K, 5)) for K in (1, 2, 3)],
          "(fs):", [math.ceil(Fraction(7 * K, 3)) for K in (1, 2, 3)])


if __name__ == "__main__":
    main()
