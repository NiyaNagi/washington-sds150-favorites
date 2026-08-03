"""Builders: canonical wasds150 model -> HPE ``Record`` objects.

Maps :class:`wasds150.models.catalog.System` (and its nested
``Department``/``Channel``/``Site``/``TrunkFrequency``) onto the
``Conventional``/``C-Group``/``C-Freq`` and ``Trunk``/``Site``/``T-Group``/
``TGID``/``T-Freq`` record shapes documented in :mod:`wasds150.hpe.schema`.
Only the fields this project's canonical model actually carries are
written; every other column is left blank rather than guessed, per the
"only touch what you understand" discipline described in
``NOTICE.md``/the research report.

Two explicit, documented design choices, both grounded in a real verified
fixture (see ``NOTICE.md``):

* An "avoid" flag renders as ``"On"`` when set and **blank** (not the
  literal string ``"Off"``) when unset — matching what was directly
  observed in a real BCDx36HP fixture (blank, not ``"Off"``, for
  not-avoided entries).
* A ``TrunkFrequency.lcn`` is written verbatim (including ``0``, including
  ``None`` -> blank) rather than ever being forced to ``0`` — the
  documented pitfall is exactly that assumption.
"""
from __future__ import annotations

from typing import List

from wasds150.hpe.record import Record, RecordDocument, new_document
from wasds150.hpe.schema import BCDX36HP_SCHEMA, TagSchema
from wasds150.models.catalog import Channel, Department, FavoritesList, Site, System, TrunkFrequency


def _flag(value: bool) -> str:
    return "On" if value else ""


def _to_hz(freq_mhz: float) -> int:
    return int(round(freq_mhz * 1_000_000))


def _blank_fields(schema: TagSchema) -> List[str]:
    return [""] * (max(schema.arities) - 1)


def _set(fields: List[str], schema: TagSchema, name: str, value: str) -> None:
    spec = schema.field_by_name(name)
    if spec is None:  # pragma: no cover - defensive, all names used below exist
        raise KeyError(f"{schema.tag} has no field named {name!r}")
    fields[spec.index - 1] = value


def build_c_freq_record(channel: Channel) -> Record:
    schema = BCDX36HP_SCHEMA["C-Freq"]
    fields = _blank_fields(schema)
    _set(fields, schema, "name", channel.label)
    _set(fields, schema, "avoid", _flag(channel.avoid))
    if channel.freq_mhz is not None:
        _set(fields, schema, "freq_hz", str(_to_hz(channel.freq_mhz)))
    _set(fields, schema, "mode", channel.mode or "AUTO")
    if channel.tone:
        _set(fields, schema, "tone", channel.tone)
    if channel.service_type is not None:
        _set(fields, schema, "service_type", str(channel.service_type))
    _set(fields, schema, "priority", _flag(channel.priority))
    return Record(tag="C-Freq", fields=fields)


def build_c_group_record(department: Department) -> Record:
    schema = BCDX36HP_SCHEMA["C-Group"]
    fields = _blank_fields(schema)
    _set(fields, schema, "name", department.label)
    _set(fields, schema, "avoid", _flag(department.avoid))
    if department.lat is not None:
        _set(fields, schema, "lat", f"{department.lat:.6f}")
    if department.lon is not None:
        _set(fields, schema, "lon", f"{department.lon:.6f}")
    if department.range_miles is not None:
        _set(fields, schema, "range", f"{department.range_miles:g}")
    if department.shape:
        _set(fields, schema, "shape", department.shape)
    return Record(tag="C-Group", fields=fields)


def build_conventional_records(system: System) -> List[Record]:
    """``Conventional`` system + its ``C-Group`` departments + ``C-Freq``
    channels, in the flat, sequential order a real file uses."""
    schema = BCDX36HP_SCHEMA["Conventional"]
    fields = _blank_fields(schema)
    _set(fields, schema, "name", system.label)
    _set(fields, schema, "avoid", _flag(system.avoid))
    _set(fields, schema, "system_class", "Conventional")
    records = [Record(tag="Conventional", fields=fields)]
    for department in system.departments:
        records.append(build_c_group_record(department))
        for channel in department.channels:
            records.append(build_c_freq_record(channel))
    return records


def build_tgid_record(channel: Channel) -> Record:
    schema = BCDX36HP_SCHEMA["TGID"]
    fields = _blank_fields(schema)
    _set(fields, schema, "name", channel.label)
    _set(fields, schema, "avoid", _flag(channel.avoid))
    if channel.tgid is not None:
        _set(fields, schema, "tgid", str(channel.tgid))
    if channel.mode:
        _set(fields, schema, "mode", channel.mode)
    if channel.service_type is not None:
        _set(fields, schema, "service_type", str(channel.service_type))
    _set(fields, schema, "priority", _flag(channel.priority))
    return Record(tag="TGID", fields=fields)


def build_t_group_record(department: Department) -> Record:
    schema = BCDX36HP_SCHEMA["T-Group"]
    fields = _blank_fields(schema)
    _set(fields, schema, "name", department.label)
    _set(fields, schema, "avoid", _flag(department.avoid))
    if department.lat is not None:
        _set(fields, schema, "lat", f"{department.lat:.6f}")
    if department.lon is not None:
        _set(fields, schema, "lon", f"{department.lon:.6f}")
    if department.range_miles is not None:
        _set(fields, schema, "range", f"{department.range_miles:g}")
    if department.shape:
        _set(fields, schema, "shape", department.shape)
    return Record(tag="T-Group", fields=fields)


def build_site_records(site: Site) -> List[Record]:
    schema = BCDX36HP_SCHEMA["Site"]
    fields = _blank_fields(schema)
    _set(fields, schema, "name", site.label)
    _set(fields, schema, "avoid", _flag(site.avoid))
    if site.lat is not None:
        _set(fields, schema, "lat", f"{site.lat:.6f}")
    if site.lon is not None:
        _set(fields, schema, "lon", f"{site.lon:.6f}")
    if site.range_miles is not None:
        _set(fields, schema, "range", f"{site.range_miles:g}")
    if site.shape:
        _set(fields, schema, "shape", site.shape)
    records = [Record(tag="Site", fields=fields)]
    for department in site.departments:
        records.append(build_t_group_record(department))
        for channel in department.channels:
            records.append(build_tgid_record(channel))
    return records


def build_t_freq_record(trunk_frequency: TrunkFrequency) -> Record:
    """A single LCN -> frequency mapping. ``lcn`` is written verbatim
    (including ``0``) — never force-zeroed; see module docstring."""
    schema = BCDX36HP_SCHEMA["T-Freq"]
    fields = _blank_fields(schema)
    if trunk_frequency.freq_mhz is not None:
        _set(fields, schema, "freq_hz", str(_to_hz(trunk_frequency.freq_mhz)))
    if trunk_frequency.lcn is not None:
        _set(fields, schema, "lcn", str(trunk_frequency.lcn))
    if trunk_frequency.usage:
        _set(fields, schema, "usage", trunk_frequency.usage)
    return Record(tag="T-Freq", fields=fields)


def build_trunk_records(system: System) -> List[Record]:
    """``Trunk`` system + its ``Site``s (each with ``T-Group``/``TGID``)
    + the system-wide ``T-Freq`` LCN table.

    ``BandPlan_P25``/``BandPlan_Mot`` are deliberately never emitted here:
    the documented guidance is to omit them unless a site needs a
    non-standard plan, which this project's canonical model has no field
    to express yet — omitting by default is the safe choice (adding one
    unnecessarily has been observed to prevent a P25 trunk from locking).
    """
    schema = BCDX36HP_SCHEMA["Trunk"]
    fields = _blank_fields(schema)
    _set(fields, schema, "name", system.label)
    _set(fields, schema, "avoid", _flag(system.avoid))
    _set(fields, schema, "tech", system.tech or "P25Standard")
    records = [Record(tag="Trunk", fields=fields)]
    for site in system.sites:
        records.extend(build_site_records(site))
    for trunk_frequency in system.trunk_frequencies:
        records.append(build_t_freq_record(trunk_frequency))
    return records


def is_trunked(system: System) -> bool:
    return bool(system.sites or system.trunk_frequencies or system.sid or system.wacn or system.tech)


def build_system_records(system: System) -> List[Record]:
    """Dispatch to :func:`build_trunk_records` or
    :func:`build_conventional_records` based on whether ``system`` carries
    any trunked-system data."""
    if is_trunked(system):
        return build_trunk_records(system)
    return build_conventional_records(system)


def build_favorites_document(systems: List[System]) -> RecordDocument:
    """A complete, exportable Favorites List document: header, one or more
    systems (each with its full nested tree), and the trailing signature
    line — ready for :func:`wasds150.hpe.record.serialize_records` and
    :func:`wasds150.hpe.codec.encode_container`.
    """
    records: List[Record] = [
        Record(tag="TargetModel", fields=["BCDx36HP"]),
        Record(tag="FormatVersion", fields=["1.00"]),
    ]
    for system in systems:
        records.extend(build_system_records(system))
    records.append(Record(tag="File", fields=["HomePatrol Export File"]))
    return new_document(records, line_ending="\r\n")


def build_favorites_list_hpe(favorites_list: FavoritesList) -> bytes:
    """Convenience entry point: a canonical :class:`FavoritesList` (with its
    ``systems`` populated) -> a ready-to-import ``.hpe`` file's bytes."""
    from wasds150.hpe.codec import encode_container

    doc = build_favorites_document(favorites_list.systems)
    text = record_text(doc)
    return encode_container(text)


def record_text(doc: RecordDocument) -> str:
    from wasds150.hpe.record import serialize_records

    return serialize_records(doc)
