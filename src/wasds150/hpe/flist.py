"""``f_list.cfg`` (the on-card Favorites List index) read/patch helpers.

Confirmed directly against a real, third-party ``f_list.cfg`` fixture (see
``NOTICE.md``): each entry is a 118-column ``F-List`` record — 1=UserName,
2=Filename, 3=LocationControl, 4=Monitor, 5=QuickKey, 6=NumberTag,
7-16=StartupKey0-9, 17-116=S-Qkey_00-99 (see
:data:`wasds150.hpe.schema.F_LIST_SCHEMA`) — and a single fresh/default
entry has ``LocationControl=Off``, ``Monitor=On``, ``QuickKey=0``,
``NumberTag=Off``, and every StartupKey/S-Qkey slot ``Off``.

**The documented write-safety rule this module exists to enforce:** when
updating an *existing* list's entry, only ``UserName``/``Monitor`` (and
slot membership/order, handled by the caller re-ordering the record list)
may change — every other field (QuickKey, NumberTag, StartupKeys, S-Qkeys)
must be preserved byte-for-byte from the existing entry. A prior real-world
regression (an earlier tool regenerating the whole entry from a template on
every save, silently resetting every list's quick-key/monitor assignment)
is exactly what this module's :func:`patch_entry` avoids by construction:
it only ever copies-then-overwrites the two named fields, never
reconstructs the other 112.
"""
from __future__ import annotations

from typing import List, Optional

from wasds150.hpe.record import Record, RecordDocument, parse_records, serialize_records
from wasds150.hpe.schema import F_LIST_SCHEMA

FLIST_TAG = "F-List"


def parse_f_list(text: str) -> RecordDocument:
    return parse_records(text)


def entries(doc: RecordDocument) -> List[Record]:
    """All ``F-List`` entries, in on-disk order (== list ordering)."""
    return doc.find_all(FLIST_TAG)


def find_entry_by_filename(doc: RecordDocument, filename: str) -> Optional[Record]:
    spec = F_LIST_SCHEMA.field_by_name("filename")
    for record in entries(doc):
        if record.get(spec.index - 1) == filename:
            return record
    return None


def patch_entry(
    record: Record, *, user_name: Optional[str] = None, monitor: Optional[str] = None
) -> Record:
    """Return a **new** ``Record`` with only ``UserName``/``Monitor``
    changed; every other field is copied verbatim from ``record``."""
    if record.tag != FLIST_TAG:
        raise ValueError(f"expected an {FLIST_TAG!r} record, got {record.tag!r}")
    fields = list(record.fields)
    if user_name is not None:
        spec = F_LIST_SCHEMA.field_by_name("user_name")
        fields[spec.index - 1] = user_name
    if monitor is not None:
        spec = F_LIST_SCHEMA.field_by_name("monitor")
        fields[spec.index - 1] = monitor
    return Record(tag=FLIST_TAG, fields=fields)


def new_entry(user_name: str, filename: str) -> Record:
    """Synthesize a brand-new ``F-List`` entry using the exact defaults
    observed on a real single-entry ``f_list.cfg`` fixture: ``Monitor=On``,
    ``LocationControl=Off``, ``QuickKey=0``, ``NumberTag=Off``, and every
    StartupKey/S-Qkey slot ``Off``. Only ever used for a list that doesn't
    already have an entry — see module docstring for why existing entries
    must go through :func:`patch_entry` instead.
    """
    total_fields = max(F_LIST_SCHEMA.arities) - 1
    fields = ["Off"] * total_fields
    _set(fields, "user_name", user_name)
    _set(fields, "filename", filename)
    _set(fields, "location_control", "Off")
    _set(fields, "monitor", "On")
    _set(fields, "quick_key", "0")
    _set(fields, "number_tag", "Off")
    return Record(tag=FLIST_TAG, fields=fields)


def _set(fields: List[str], name: str, value: str) -> None:
    spec = F_LIST_SCHEMA.field_by_name(name)
    fields[spec.index - 1] = value


def render(doc: RecordDocument) -> str:
    return serialize_records(doc)
