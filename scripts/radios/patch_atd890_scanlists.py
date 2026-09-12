"""Restore full scan-list membership to a saved AT-D890UV codeplug.

The CPS's CSV importer keeps scan-list members in a fixed array of fifty; a
51st raises VB6 runtime error 9, subscript out of range. The radio holds a
hundred (firmware 1.05 change log line 10), and the CPS's own editor and its
``.rdt`` carry more than fifty without complaint - only the import routine is
broken.

So ``ScanList.CSV`` ships the first fifty of each list, the exporter writes the
full membership beside it in ``scanlists.json``, and this puts the rest back
into the codeplug the CPS saved.

The ``.rdt`` is a plain uncompressed container with no checksum. Its scan-list
section is a chain of records::

    [index:1] [name:16] [settings:10] [count:uint16le] [count x member]
    member = [channel:uint16le] [sep:1]

``sep`` is zero except on the last member of a record, where it carries the
next record's index byte - so it is a separator, not a flag. A ``uint32le`` at
offset 5 holds the container length, filesize minus the fourteen-byte header.

Only member arrays grow: no record is added, removed or renumbered, so nothing
that refers to a scan list by index - every channel does - is disturbed.

Usage::

    python scripts/radios/patch_atd890_scanlists.py \\
        --rdt radio-backups/at-d890uv/saved.rdt \\
        --sidecar wasds150-output/radios/at-d890uv-fleet/scanlists.json \\
        --output radio-backups/at-d890uv/saved-patched.rdt
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

HEADER = 14
LENGTH_AT = 5
NAME = 16
SETTINGS = 10
ENTRY = 3
MAX_MEMBERS = 100


class PatchError(RuntimeError):
    """The codeplug does not look the way the format requires."""


def _name_at(data: bytes, at: int) -> Optional[str]:
    raw = data[at:at + NAME]
    if len(raw) < NAME:
        return None
    text = raw.split(b"\x00")[0]
    if not text or not re.fullmatch(rb"[\x20-\x7e]+", text):
        return None
    return text.decode("ascii")


def read_record(data: bytes, at: int) -> Optional[Dict]:
    """Decode the scan-list record whose name starts at ``at``."""
    name = _name_at(data, at)
    if name is None:
        return None
    count_at = at + NAME + SETTINGS
    count = int.from_bytes(data[count_at:count_at + 2], "little")
    if not 1 <= count <= 250:
        return None
    body = data[count_at + 2:count_at + 2 + count * ENTRY]
    if len(body) < count * ENTRY:
        return None
    members = [int.from_bytes(body[k:k + 2], "little") for k in range(0, len(body), ENTRY)]
    seps = [body[k + 2] for k in range(0, len(body), ENTRY)]
    if any(s != 0 for s in seps[:-1]):
        return None
    return {
        "name": name,
        "at": at,
        "count_at": count_at,
        "count": count,
        "members": members,
        "sep": seps[-1],
        "end": count_at + 2 + count * ENTRY,
    }


def find_scan_lists(data: bytes, names: List[str]) -> List[Dict]:
    """Every scan-list record, in file order.

    Anchored on a name from the bundle and walked forwards and backwards, so
    the section is found without hard-coding an offset.
    """
    anchor = None
    for name in names:
        hits = [m.start() for m in re.finditer(re.escape(name.encode("ascii")), data)]
        # Zones share their scan list's name, and the zone section comes first,
        # so the last occurrence is the scan-list one.
        for at in reversed(hits):
            rec = read_record(data, at)
            if rec is not None and rec["name"] == name:
                anchor = at
                break
        if anchor is not None:
            break
    if anchor is None:
        raise PatchError("no scan-list record found for any name in the sidecar")

    start = anchor
    while True:
        for back in range(1, 1200):
            rec = read_record(data, start - back)
            if rec is not None and rec["end"] == start:
                start = start - back
                break
        else:
            break

    out: List[Dict] = []
    at = start
    while True:
        rec = read_record(data, at)
        if rec is None:
            break
        out.append(rec)
        at = rec["end"]
    return out


def patch(data: bytes, sidecar: Dict) -> bytes:
    wanted = {entry["name"]: list(entry["members"]) for entry in sidecar["scan_lists"]}
    records = find_scan_lists(data, [e["name"] for e in sidecar["scan_lists"]])
    print(f"found {len(records)} scan-list record(s) in the codeplug")

    known = [r for r in records if r["name"] in wanted]
    if not known:
        raise PatchError("none of the codeplug's scan lists are named in the sidecar")

    csv_max = int(sidecar.get("csv_scanlist_max", 50))
    changed = 0
    for rec in known:
        full = wanted[rec["name"]]
        if len(full) > MAX_MEMBERS:
            raise PatchError(f"{rec['name']!r}: {len(full)} members exceeds the radio's {MAX_MEMBERS}")
        # The importer truncates, so what is in the file must be the head of
        # what the plan intended. If it is not, this codeplug came from some
        # other export and patching it would scramble the list.
        head = full[:min(len(full), csv_max)]
        if rec["members"] != head:
            raise PatchError(
                f"{rec['name']!r}: the codeplug holds {rec['members'][:4]}... but the sidecar's "
                f"first members are {head[:4]}... - this .rdt was not built from this export"
            )
        if rec["members"] != full:
            changed += 1

    print(f"{len(known)} list(s) matched the sidecar, {changed} need extending")
    if not changed:
        return data

    out = bytearray()
    cursor = 0
    for rec in known:
        full = wanted[rec["name"]]
        if rec["members"] == full:
            continue
        out += data[cursor:rec["count_at"]]
        out += len(full).to_bytes(2, "little")
        for i, channel in enumerate(full):
            out += channel.to_bytes(2, "little")
            out += bytes([rec["sep"] if i == len(full) - 1 else 0])
        cursor = rec["end"]
    out += data[cursor:]
    out[LENGTH_AT:LENGTH_AT + 4] = (len(out) - HEADER).to_bytes(4, "little")
    return bytes(out)


def verify(data: bytes, sidecar: Dict) -> None:
    """Re-parse the patched bytes and check every list against the sidecar."""
    wanted = {entry["name"]: list(entry["members"]) for entry in sidecar["scan_lists"]}
    records = {r["name"]: r for r in find_scan_lists(data, list(wanted))}
    declared = int.from_bytes(data[LENGTH_AT:LENGTH_AT + 4], "little")
    if declared != len(data) - HEADER:
        raise PatchError(f"container length {declared} != {len(data) - HEADER}")
    for name, full in wanted.items():
        rec = records.get(name)
        if rec is None:
            raise PatchError(f"{name!r} is missing after patching")
        if rec["members"] != full:
            raise PatchError(f"{name!r}: {len(rec['members'])} members after patching, wanted {len(full)}")
    print(f"verified: {len(wanted)} list(s) match the sidecar, container length is consistent")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rdt", required=True, type=Path, help="codeplug saved by the CPS after Import")
    ap.add_argument("--sidecar", required=True, type=Path, help="scanlists.json from the export")
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    data = args.rdt.read_bytes()
    sidecar = json.loads(args.sidecar.read_text(encoding="utf-8"))
    print(f"{args.rdt.name}: {len(data):,} bytes")

    declared = int.from_bytes(data[LENGTH_AT:LENGTH_AT + 4], "little")
    if declared != len(data) - HEADER:
        raise PatchError(
            f"{args.rdt.name} does not look like an .rdt: length field {declared} != {len(data) - HEADER}"
        )

    try:
        patched = patch(data, sidecar)
    except PatchError as exc:
        print(f"refusing to patch: {exc}", file=sys.stderr)
        return 1
    verify(patched, sidecar)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(f"wrote {len(patched):,} bytes to {args.output}")
    print(f"SHA-256 {hashlib.sha256(patched).hexdigest().upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
