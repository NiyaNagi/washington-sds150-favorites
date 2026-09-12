"""Restoring full scan-list membership to a saved .rdt.

The format was decoded from two real codeplugs that differed by exactly one
scan-list member (radio-backups/at-d890uv/rdt-a.rdt and rdt-b.rdt): rebuilding
one from the other reproduced it byte for byte, which is what says there is no
checksum to maintain.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "radios"))

from patch_atd890_scanlists import (  # noqa: E402
    ENTRY,
    HEADER,
    LENGTH_AT,
    NAME,
    SETTINGS,
    PatchError,
    locate,
    patch,
    read_record,
    verify,
)


def record(name: str, members, next_index: int) -> bytes:
    """One record. Records abut: the separator on the last member is the next
    record's index byte, which sits immediately before that record's name."""
    out = bytearray()
    out += name.encode("ascii").ljust(NAME, b"\x00")
    out += bytes(SETTINGS)
    out += len(members).to_bytes(2, "little")
    for i, channel in enumerate(members):
        out += channel.to_bytes(2, "little")
        out += bytes([next_index if i == len(members) - 1 else 0])
    return bytes(out)


def codeplug(lists) -> bytes:
    """A container whose scan-list section holds ``lists`` of (name, members)."""
    body = bytearray(b"\x00" * 63)          # something before the section
    body += bytes([1])                       # the first record's index byte
    for i, (name, members) in enumerate(lists, start=1):
        body += record(name, members, i + 1)
    body += b"\xff" * 32                     # something after it
    out = bytearray(b"V1323") + bytes(4) + b"D890UV\x00\x00\x0e" + body
    out[LENGTH_AT:LENGTH_AT + 4] = (len(out) - HEADER).to_bytes(4, "little")
    return bytes(out)


def sidecar(lists):
    return {"radio": "at-d890uv", "csv_scanlist_max": 50,
            "scan_lists": [{"name": n, "members": list(m)} for n, m in lists]}


def test_a_record_decodes_and_the_separator_is_the_next_index():
    data = codeplug([("Alpha", [1, 2, 3])])
    at = data.index(b"Alpha")
    rec = read_record(data, at)
    assert rec["name"] == "Alpha" and rec["count"] == 3 and rec["members"] == [1, 2, 3]
    # The byte after the last member is the next record's index, not a flag.
    assert rec["sep"] == 2


def test_a_record_is_located_by_its_content_not_a_stride():
    lists = [("Alpha", [1, 2]), ("Bravo", [3, 4, 5]), ("Charlie", [6])]
    data = codeplug(lists)
    for name, members in lists:
        rec = locate(data, name, members)
        assert rec is not None and rec["members"] == members, name
    # A list whose members are not what the export left is not this record.
    assert locate(data, "Bravo", [9, 9, 9]) is None


def test_extending_a_list_keeps_every_other_byte():
    short = [("Alpha", list(range(50))), ("Bravo", [900, 901])]
    full = [("Alpha", list(range(100))), ("Bravo", [900, 901])]
    data = codeplug(short)
    out = patch(data, sidecar(full))
    verify(out, sidecar(full))

    assert len(out) == len(data) + 50 * ENTRY
    recs = {n: locate(out, n, m) for n, m in full}
    assert recs["Alpha"]["members"] == list(range(100))
    assert recs["Bravo"]["members"] == [900, 901]
    # The separator still carries Bravo's index, and Bravo is untouched.
    assert recs["Alpha"]["sep"] == 2
    # Everything before the patched record is untouched, bar the length field.
    head = data.index(b"Alpha")
    assert out[LENGTH_AT + 4:head] == data[LENGTH_AT + 4:head]
    assert out[:LENGTH_AT] == data[:LENGTH_AT]
    assert out.endswith(b"\xff" * 32)


def test_the_container_length_is_updated():
    short = [("Alpha", list(range(50)))]
    full = [("Alpha", list(range(80)))]
    out = patch(codeplug(short), sidecar(full))
    assert int.from_bytes(out[LENGTH_AT:LENGTH_AT + 4], "little") == len(out) - HEADER


def test_nothing_to_do_is_a_no_op():
    lists = [("Alpha", [1, 2, 3])]
    data = codeplug(lists)
    assert patch(data, sidecar(lists)) == data


def test_a_codeplug_from_a_different_export_is_refused():
    # The importer truncates, so the file must hold the head of the plan. A
    # codeplug built from some other export would be scrambled by patching.
    data = codeplug([("Alpha", [7, 8, 9])])
    with pytest.raises(PatchError, match="not built from this export"):
        patch(data, sidecar([("Alpha", [1, 2, 3, 4])]))


def test_more_than_the_radio_holds_is_refused():
    data = codeplug([("Alpha", list(range(50)))])
    with pytest.raises(PatchError, match="exceeds the radio's 100"):
        patch(data, sidecar([("Alpha", list(range(101)))]))


def test_the_real_codeplugs_confirm_the_format():
    """rdt-b is rdt-a with one more member in Wildfire 01, and nothing else."""
    a = Path("radio-backups/at-d890uv/rdt-a.rdt")
    b = Path("radio-backups/at-d890uv/rdt-b.rdt")
    if not (a.exists() and b.exists()):
        pytest.skip("the captured codeplugs are not in this checkout")
    da, db = a.read_bytes(), b.read_bytes()
    fifty = list(range(42, 92))          # what rdt-a's Wildfire 01 holds
    fifty_one = fifty + [92]             # and what rdt-b's does

    assert locate(da, "Wildfire 01", fifty) is not None
    assert locate(da, "Wildfire 01", fifty_one) is None
    assert locate(db, "Wildfire 01", fifty_one) is not None

    # Patching A up to B's membership must reproduce B byte for byte. That is
    # what says the container has no checksum and nothing else to maintain.
    assert patch(da, sidecar([("Wildfire 01", fifty_one)])) == db
