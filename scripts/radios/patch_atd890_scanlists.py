"""Restore full scan-list membership to a saved AT-D890UV codeplug.

The CPS's CSV importer keeps scan-list members in a fixed array of fifty; a
51st raises VB6 runtime error 9, subscript out of range. The radio holds a
hundred (firmware 1.05 change log line 10), and the CPS's own editor and its
``.rdt`` carry more than fifty without complaint - only the import routine is
broken.

So ``ScanList.CSV`` ships the first fifty of each list, the exporter writes the
full membership beside it in ``scanlists.json``, and this puts the rest back
into the codeplug the CPS saved.

The ``.rdt`` is a plain uncompressed container with no checksum. A scan-list
record is a name, some settings, a ``uint16le`` count and that many three-byte
members::

    member = [channel:uint16le] [sep:1]

``sep`` is zero except on the last member of a record, where it carries the
next record's index byte - so it is a separator, not a flag. A ``uint32le`` at
offset 5 holds the container length, filesize minus the fourteen-byte header.

The gap between the name and the count is **not** fixed - an eleven-character
name puts the count at +26 and a sixteen-character one at +30 - so a record is
found by its content rather than by a stride: the count must equal the number
of members the CPS imported, and those members must be exactly the ones this
export asked for. That is also what stops a same-named zone matching, and what
refuses a codeplug built from some other export.

Only member arrays grow: no record is added, removed or renumbered, so nothing
that refers to a scan list by index - every channel does - is disturbed.

Usage::

    python scripts/radios/patch_atd890_scanlists.py \\
        --rdt radio-data/at-d890uv/backups/at-d890uv-fleet-YYYY-MM-DD.rdt \\
        --sidecar radio-data/at-d890uv/exports/at-d890uv-fleet/scanlists.json \\
        --output radio-data/at-d890uv/backups/at-d890uv-fleet-YYYY-MM-DD-full.rdt
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


#: How far past a name the count field has been seen to sit. The stride is not
#: fixed - an eleven-character name puts it at +26 and a sixteen-character one
#: at +30 - so it is searched for rather than assumed.
COUNT_SEARCH = range(16, 48)


def locate(data: bytes, name: str, head: List[int]) -> Optional[Dict]:
    """Find the record for ``name`` whose members begin with ``head``.

    Locating by content rather than by a stride: the count must equal the
    number of members the CPS imported, and those members must be exactly the
    ones the export asked for. A zone of the same name does not match, because
    its member ids are stored differently, and neither does a record from some
    other export.
    """
    for at in [m.start() for m in re.finditer(re.escape(name.encode("ascii")), data)]:
        after = data[at + len(name):at + len(name) + 1]
        if after and after != b"\x00":
            continue  # a longer name that merely starts with this one
        for gap in COUNT_SEARCH:
            count_at = at + gap
            if int.from_bytes(data[count_at:count_at + 2], "little") != len(head):
                continue
            body = data[count_at + 2:count_at + 2 + len(head) * ENTRY]
            if len(body) < len(head) * ENTRY:
                continue
            members = [int.from_bytes(body[k:k + 2], "little") for k in range(0, len(body), ENTRY)]
            seps = [body[k + 2] for k in range(0, len(body), ENTRY)]
            if members != head or any(s != 0 for s in seps[:-1]):
                continue
            return {"name": name, "at": at, "count_at": count_at, "count": len(head),
                    "members": members, "sep": seps[-1],
                    "end": count_at + 2 + len(head) * ENTRY}
    return None


def patch(data: bytes, sidecar: Dict) -> bytes:
    csv_max = int(sidecar.get("csv_scanlist_max", 50))
    wanted = {entry["name"]: list(entry["members"]) for entry in sidecar["scan_lists"]}

    found: List[Dict] = []
    missing: List[str] = []
    for name, full in wanted.items():
        if len(full) > MAX_MEMBERS:
            raise PatchError(f"{name!r}: {len(full)} members exceeds the radio's {MAX_MEMBERS}")
        rec = locate(data, name, full[:min(len(full), csv_max)])
        if rec is None:
            missing.append(name)
        else:
            rec["full"] = full
            found.append(rec)
    if missing:
        raise PatchError(
            f"{len(missing)} of {len(wanted)} scan list(s) were not found as this export left them, "
            f"e.g. {missing[:3]} - this .rdt was not built from this export, or was edited since"
        )

    found.sort(key=lambda r: r["count_at"])
    changed = [r for r in found if r["members"] != r["full"]]
    print(f"located all {len(found)} scan list(s); {len(changed)} need extending")
    if not changed:
        return data

    out = bytearray()
    cursor = 0
    for rec in changed:
        if rec["count_at"] < cursor:
            raise PatchError(f"{rec['name']!r}: records overlap, refusing to patch")
        full = rec["full"]
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
    declared = int.from_bytes(data[LENGTH_AT:LENGTH_AT + 4], "little")
    if declared != len(data) - HEADER:
        raise PatchError(f"container length {declared} != {len(data) - HEADER}")
    for entry in sidecar["scan_lists"]:
        full = list(entry["members"])
        # Locating on the FULL membership: it only matches if every member of
        # every list is now in the file, in order.
        if locate(data, entry["name"], full) is None:
            raise PatchError(f"{entry['name']!r} does not hold its {len(full)} members after patching")
    print(f"verified: {len(sidecar['scan_lists'])} list(s) hold their full membership, length is consistent")


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
