"""Fase 3 bis (TNSM): overlap of the NCSU IoT-Lab sample (Ahmed et al.,
PETS 2022) with the 119 canonical device types of audit 11 sez. 2.

Run from repo root (local files only, no network; reads the zip in place,
nothing is extracted; ~1 min):
    python3 -I analysis_fs/ncsu_overlap.py \
        --zip /root/Desktop/DIB/data/external/ncsu_sample/sample.zip \
        --union /root/Desktop/DIB/outputs/tnsm_hd/hd_union_by_type.csv \
        --private-out /root/Desktop/DIB/outputs/tnsm_hd/ncsu_overlap.csv

Input: sample.zip (sha256 10143e34..., 498,170,708 bytes, downloaded
2026-10-10 from privacy-datahub.csc.ncsu.edu), i.e. sample/device_mappings.csv
(label -> LAN IP) and 51 pcaps (2021-01-28/29). Untrusted data: parsed with
struct only (classic pcap and pcapng; the files are pcapng despite the .pcap name), no third-party parser, interpreter run with -I.

Same type across sites. Two declared mappings, nothing changed in
canonical_device_name or docs/label_mapping_v16.csv:
  strict  canonical_device_name(label) must equal an existing canonical type
          (the same rule as hd_union.py);
  family  a manual, by-product-name table (FAMILY below), recorded here so it
          can be reviewed; generation and model are not verified (e.g. Echo
          Plus 2nd Gen vs Mon(IoT)r echoplus, SmartThings Hub 2 vs smartthings).
NCSU counts as ONE new independent site (one lab).

A device counts as observed only if the capture contains at least one IPv4
packet between its LAN IP and a global (non-private) address, mirroring the
"row with an endpoint" rule (dib.py:198, hd_heterogeneity.py).

Hypothesis (stated before running): strict -> only ring-doorbell gains a
site (h 4 -> 5); family -> at most 6 types gain a site, and at most 2 types
(ring-doorbell, smartthings) reach h = 5. So with 5 independent sites K = 2
at f_s = 0.30 (needs h >= 5) is covered on at most 2 types and K = 3 at f_s
(needs h >= 7) on none.
Falsified if: more than 2 types reach h >= 5 under either mapping, or any
type reaches h >= 7.

Output (outside the repo; NCSU license not declared, docs/audit/10 sez. 6):
per NCSU label: mapped type under each mapping, packets with a global peer,
h before and after. Printed summary has counts only.
"""
from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import re
import struct
import zipfile
from collections import Counter
from pathlib import Path

NON_IOT = {"Desktop", "Router", "Motog phone", "Pixel 2 Phone"}
FAMILY = {
    "Amazon Echo Plus 2nd Gen": "echoplus",
    "Nestcam": "nestcamera",
    "Google OnHub": "googleonhub",
    "Ring Doorbell": "ring-doorbell",
    "Samsung SmartThings Hub 2": "smartthings",
    "Amcrest Camera": "amcrest-cam-wired",
    "LG Smart TV": "lgtv-wired",
    # not mapped: "Amazon Echo Look", "Foscam", "Smart WiFi Plug" (no vendor)
}


def canonical(value: str) -> str:
    """Same normalisation as dib.evaluation.profiles.canonical_device_name
    (profiles.py:143-144); none of the NCSU labels hits its alias table
    (checked by importing it, audit 11 sez. 2.6). Copied to keep -I isolation."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


L2 = {1: 14, 113: 16, 101: 0, 228: 0}  # Ethernet, Linux SLL, raw IP, raw IPv4


def _ipv4(pkt: bytes, linktype: int):
    off = L2.get(linktype)
    if off is None:
        raise ValueError(f"unsupported link type {linktype}")
    if linktype == 1:
        if len(pkt) < 14:
            return None
        etype = struct.unpack(">H", pkt[12:14])[0]
        if etype == 0x8100 and len(pkt) >= 18:  # one VLAN tag
            etype, off = struct.unpack(">H", pkt[16:18])[0], 18
        if etype != 0x0800:
            return None
    elif linktype == 113 and (len(pkt) < 16 or struct.unpack(">H", pkt[14:16])[0] != 0x0800):
        return None
    if len(pkt) < off + 20 or pkt[off] >> 4 != 4:
        return None
    return pkt[off + 12:off + 16], pkt[off + 16:off + 20]


def ipv4_pairs(fh):
    """Yield (src, dst) IPv4 addresses from a classic pcap or a pcapng stream
    (Ethernet, Linux SLL, or raw IP link types)."""
    head = fh.read(4)
    if head == b"\n\r\r\n":  # pcapng section header block
        yield from _pcapng(fh, head)
        return
    head += fh.read(20)
    endian = {b"\xd4\xc3\xb2\xa1": "<", b"\xa1\xb2\xc3\xd4": ">",
              b"\x4d\x3c\xb2\xa1": "<", b"\xa1\xb2\x3c\x4d": ">"}.get(head[:4])
    if endian is None:
        raise ValueError(f"unknown capture format (magic {head[:4]!r})")
    linktype = struct.unpack(endian + "I", head[20:24])[0]
    while True:
        rec = fh.read(16)
        if len(rec) < 16:
            return
        pair = _ipv4(fh.read(struct.unpack(endian + "IIII", rec)[2]), linktype)
        if pair:
            yield pair


def _pcapng(fh, first4: bytes):
    endian, links, btype = "<", [], first4
    while True:
        rest = fh.read(4) if btype else None
        if btype is None:
            hdr = fh.read(8)
            if len(hdr) < 8:
                return
            btype, rest = hdr[:4], hdr[4:]
        if btype == b"\n\r\r\n":
            bom = fh.read(4)
            endian = "<" if bom == b"\x4d\x3c\x2b\x1a" else ">"
            total = struct.unpack(endian + "I", rest)[0]
            fh.read(total - 12)
            links = []
        else:
            t = struct.unpack(endian + "I", btype)[0]
            total = struct.unpack(endian + "I", rest)[0]
            body = fh.read(total - 8)
            if t == 1:  # interface description block
                links.append(struct.unpack(endian + "H", body[:2])[0])
            elif t == 6:  # enhanced packet block
                iface, _, _, caplen = struct.unpack(endian + "IIII", body[:16])
                pair = _ipv4(body[20:20 + caplen], links[iface])
                if pair:
                    yield pair
            elif t == 3:  # simple packet block (interface 0)
                orig = struct.unpack(endian + "I", body[:4])[0]
                pair = _ipv4(body[4:4 + orig], links[0])
                if pair:
                    yield pair
        btype = None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--union", type=Path, required=True)
    p.add_argument("--private-out", type=Path, required=True)
    a = p.parse_args()

    union = {r["canonical"]: int(r["h_indep"]) for r in csv.DictReader(a.union.open())}
    with zipfile.ZipFile(a.zip) as z:
        mapping = list(csv.DictReader(io.TextIOWrapper(z.open("sample/device_mappings.csv"), "utf-8")))
        ip_label = {ipaddress.IPv4Address(r["IP"]).packed: r["Device"] for r in mapping}
        global_pkts: Counter[str] = Counter()
        for name in sorted(n for n in z.namelist() if n.endswith(".pcap")):
            with z.open(name) as fh:
                for src, dst in ipv4_pairs(io.BufferedReader(fh, 1 << 20)):
                    for mine, peer in ((src, dst), (dst, src)):
                        label = ip_label.get(mine)
                        if label and ipaddress.IPv4Address(peer).is_global:
                            global_pkts[label] += 1

    rows, gained = [], {"strict": Counter(), "family": Counter()}
    for r in mapping:
        label = r["Device"]
        if label in NON_IOT:
            continue
        observed = global_pkts[label] > 0
        row = {"ncsu_label": label, "global_packets": global_pkts[label], "observed": observed}
        for kind, target in (("strict", canonical(label)), ("family", FAMILY.get(label))):
            hit = target if target in union else None
            row[f"{kind}_type"] = hit or ""
            row[f"{kind}_h_before"] = union.get(hit, "") if hit else ""
            if hit and observed:
                gained[kind][hit] = union[hit] + 1
        rows.append(row)
    a.private_out.parent.mkdir(parents=True, exist_ok=True)
    with a.private_out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print("IoT labels:", len(rows), "observed with a global peer:", sum(r["observed"] for r in rows))
    for kind in ("strict", "family"):
        h_after = gained[kind]
        print(kind, "types gaining NCSU:", len(h_after),
              "h_after histogram:", dict(sorted(Counter(h_after.values()).items())),
              "types with h>=5:", sum(v >= 5 for v in h_after.values()),
              "types with h>=7:", sum(v >= 7 for v in h_after.values()))


if __name__ == "__main__":
    main()
