"""HPDB (on-card RadioReference database) parser, extraction, and
HPDB-to-Favorites dialect conversion.

Distinct from a Favorites List export/`.hpd`: the on-card ``BCDx36HP/HPDB/``
tree (``hpdb.cfg`` + one ``s_<StateId>.hpd`` per imported state) carries the
*full* imported RadioReference database — every system in that state, not
just the user's selected Favorites Lists — with real identity columns
(RadioReference's own ``CountyId``/``StateId``/``TrunkId``/``SiteId``/...
ids) that a Favorites export blanks out. Every fact below (arities, column
layout, the id/parent-id convention, the ``AreaCounty`` "owner id is not
always a county id" quirk, the synthesized-``DQKs_Status``-only rule) was
directly confirmed against a real, third-party synthetic HPDB fixture
during this project's implementation — see ``NOTICE.md`` for provenance;
no code was copied, only facts.

This module is **read-only**: parsing, segmentation, geo/county lookup, and
one-way dialect conversion (HPDB -> Favorites). It never writes to a card —
see :mod:`wasds150.installer` for the write path, which only ever touches
``favorites_lists/`` and never ``HPDB/`` (unchanged by this module).

**Preserving ids for merge**: :func:`own_id`/:func:`parent_id` and
:meth:`SystemSlice.identity` expose the real RadioReference ids a Favorites
export would otherwise discard. :func:`system_slice_to_system` builds on
these primitives to convert a segmented :class:`SystemSlice` into a
canonical :class:`wasds150.models.catalog.System` for
:mod:`wasds150.recipes` — every RadioReference id involved (``TrunkId``/
``SiteId``/``CGroupId``/``CFreqId``/``TGroupId``/``Tid``/``TFreqId``)
becomes that object's own ``id`` (e.g. ``"hpdb:TrunkId:6001"``), so a
future by-id merge strategy (matching :mod:`wasds150.merge`'s
upstream-catalog model, which currently keys on the flat CSV's
``favorite_key``/slug, a different keyspace) has a stable key to build on
without needing to re-derive it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from wasds150.hpe.record import Record, RecordDocument, parse_records
from wasds150.hpe.schema import BCDX36HP_SCHEMA, FieldSpec, TagSchema

# ---------------------------------------------------------------------------
# HPDB-only tags (never appear in a Favorites List export). Arities/columns
# confirmed directly against a real synthetic hpdb.cfg / s_000090.hpd
# fixture (see NOTICE.md — FuzzyGophers/platypus, commit 5abb42b, GPL-2.0,
# facts only, no code reused).
# ---------------------------------------------------------------------------

HPDB_ONLY_SCHEMA: Dict[str, TagSchema] = {
    "DateModified": TagSchema(tag="DateModified", arities=(2,), verified=True),
    "StateInfo": TagSchema(
        tag="StateInfo",
        arities=(5,),
        fields=(FieldSpec(1, "state_id"), FieldSpec(2, "country_id"), FieldSpec(3, "name")),
        verified=True,
    ),
    "CountyInfo": TagSchema(
        tag="CountyInfo",
        arities=(4,),
        fields=(FieldSpec(1, "county_id"), FieldSpec(2, "state_id"), FieldSpec(3, "name")),
        verified=True,
    ),
    "LM": TagSchema(
        tag="LM",
        arities=(9,),
        fields=(
            FieldSpec(1, "state_id"),
            FieldSpec(2, "county_id"),
            FieldSpec(3, "trunk_id"),
            FieldSpec(4, "site_id"),
            FieldSpec(7, "lat"),
            FieldSpec(8, "lon"),
        ),
        verified=True,
        notes="Locate-Me flattened site-location lookup row inside hpdb.cfg; separate from the full Site record in s_<state>.hpd.",
    ),
    "AreaState": TagSchema(
        tag="AreaState",
        arities=(3,),
        fields=(FieldSpec(1, "owner_id"), FieldSpec(2, "state_id")),
        verified=True,
    ),
    "AreaCounty": TagSchema(
        tag="AreaCounty",
        arities=(3,),
        fields=(FieldSpec(1, "owner_id"), FieldSpec(2, "county_id")),
        verified=True,
        notes=(
            "field 1 echoes the owning system's own id (e.g. AgencyId=... for a Conventional "
            "system, not necessarily a CountyId) -- field 2 is always the real county. A "
            "single-county system's field 1 can coincide with field 2, hiding the distinction; "
            "a multi-county/agency system does not."
        ),
    ),
}

#: Hierarchical record tags shared with the Favorites dialect: same arity
#: and column layout as :data:`wasds150.hpe.schema.BCDX36HP_SCHEMA`; HPDB
#: populates columns 1/2 with real ids, Favorites blanks them.
HIERARCHICAL_TAGS = ("Conventional", "C-Group", "C-Freq", "Trunk", "Site", "T-Group", "TGID", "T-Freq")
#: Tags that start a new system during segmentation.
SYSTEM_HEADER_TAGS = ("Conventional", "Trunk")
#: Tags dropped entirely when converting HPDB -> Favorites dialect.
AREA_TAGS = ("AreaState", "AreaCounty")

EARTH_RADIUS_MILES = 3958.7613  # matches Uniden's mile-based `range` field


def _schema_for(tag: str) -> Optional[TagSchema]:
    return BCDX36HP_SCHEMA.get(tag) or HPDB_ONLY_SCHEMA.get(tag)


def parse_keyed_id(value: str) -> Optional[Tuple[str, int]]:
    """``"SiteId=8201"`` -> ``("SiteId", 8201)``. ``None`` for a blank or
    non-``Key=<int>`` string (e.g. a Favorites-dialect blanked column)."""
    if not value or "=" not in value:
        return None
    key, _, raw = value.partition("=")
    try:
        return key, int(raw)
    except ValueError:
        return None


def own_id(record: Record) -> Optional[Tuple[str, int]]:
    """A hierarchical record's own identity (column 1), if present."""
    return parse_keyed_id(record.get(0, "") or "")


def parent_id(record: Record) -> Optional[Tuple[str, int]]:
    """A hierarchical record's parent identity (column 2), if present."""
    return parse_keyed_id(record.get(1, "") or "")


# ---------------------------------------------------------------------------
# Geo / haversine
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Geo:
    lat: float
    lon: float
    range_mi: float = 0.0
    shape: str = ""


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in statute miles (Earth radius 3958.7613 mi,
    matching Uniden's mile-based ``range`` field)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(min(1.0, math.sqrt(a)))


def geo_of(record: Record) -> Optional[Geo]:
    """Extract a point ``Geo`` from any record whose schema declares
    ``lat``/``lon`` fields (``Rectangle`` is handled separately by
    :func:`rectangle_corners`, since it's a bounding box, not a point)."""
    schema = _schema_for(record.tag)
    if schema is None:
        return None
    lat_spec = schema.field_by_name("lat")
    lon_spec = schema.field_by_name("lon")
    if lat_spec is None or lon_spec is None:
        return None
    lat_raw = record.get(lat_spec.index - 1)
    lon_raw = record.get(lon_spec.index - 1)
    if not lat_raw or not lon_raw:
        return None
    try:
        lat, lon = float(lat_raw), float(lon_raw)
    except ValueError:
        return None
    range_spec = schema.field_by_name("range")
    shape_spec = schema.field_by_name("shape")
    range_mi = 0.0
    if range_spec is not None:
        try:
            range_mi = float(record.get(range_spec.index - 1) or 0.0)
        except ValueError:
            range_mi = 0.0
    shape = (record.get(shape_spec.index - 1, "") if shape_spec is not None else "") or ""
    return Geo(lat=lat, lon=lon, range_mi=range_mi, shape=shape)


def rectangle_corners(record: Record) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """``Rectangle`` bounding-box corners: ``((lat1, lon1), (lat2, lon2))``."""
    schema = BCDX36HP_SCHEMA.get("Rectangle")
    if record.tag != "Rectangle" or schema is None:
        return None
    try:
        lat1 = float(record.get(schema.field_by_name("lat1").index - 1))
        lon1 = float(record.get(schema.field_by_name("lon1").index - 1))
        lat2 = float(record.get(schema.field_by_name("lat2").index - 1))
        lon2 = float(record.get(schema.field_by_name("lon2").index - 1))
    except (TypeError, ValueError):
        return None
    return (lat1, lon1), (lat2, lon2)


# ---------------------------------------------------------------------------
# System segmentation (s_<state>.hpd)
# ---------------------------------------------------------------------------


@dataclass
class SystemSlice:
    """A single system (``Conventional``/``Trunk`` header + every record up
    to the next system header) — a read-only, borrowed view over a slice of
    ``doc.records``; never mutates the source document."""

    records: List[Record] = field(default_factory=list)

    @property
    def header(self) -> Record:
        return self.records[0]

    def kind(self) -> str:
        return self.header.tag  # "Conventional" | "Trunk"

    def name(self) -> str:
        schema = BCDX36HP_SCHEMA.get(self.header.tag)
        spec = schema.field_by_name("name") if schema else None
        return (self.header.get(spec.index - 1, "") if spec else "") or ""

    def tech(self) -> str:
        schema = BCDX36HP_SCHEMA.get(self.header.tag)
        spec = schema.field_by_name("tech") if schema else None
        return (self.header.get(spec.index - 1, "") if spec else "") or ""

    def identity(self) -> Optional[Tuple[str, int]]:
        """This system's own RadioReference id, e.g. ``("TrunkId", 9201)``."""
        return own_id(self.header)

    def county_ids(self) -> List[int]:
        """Every county this system covers, read from its ``AreaCounty``
        children's **field 2** (never field 1 — field 1 is the owning
        system's own id, which is not always a county id; see
        :data:`HPDB_ONLY_SCHEMA`'s ``AreaCounty`` note)."""
        ids = []
        for r in self.records:
            if r.tag == "AreaCounty":
                pid = parent_id(r)
                if pid is not None:
                    ids.append(pid[1])
        return ids

    def state_ids(self) -> List[int]:
        ids = []
        for r in self.records:
            if r.tag == "AreaState":
                pid = parent_id(r)
                if pid is not None:
                    ids.append(pid[1])
        return ids

    def geos(self) -> List[Geo]:
        return [g for r in self.records for g in [geo_of(r)] if g is not None]

    def is_within(self, lat: float, lon: float, radius_mi: float) -> bool:
        """True if any of this system's geo-bearing children (sites,
        groups) — or any ``Rectangle`` corner — is within ``radius_mi`` of
        ``(lat, lon)``."""
        for g in self.geos():
            if haversine_miles(lat, lon, g.lat, g.lon) <= radius_mi:
                return True
        for r in self.records:
            corners = rectangle_corners(r)
            if corners is None:
                continue
            for corner_lat, corner_lon in corners:
                if haversine_miles(lat, lon, corner_lat, corner_lon) <= radius_mi:
                    return True
        return False

    def is_in_county(self, county_id: int) -> bool:
        return county_id in self.county_ids()


def preamble_records(doc: RecordDocument) -> List[Record]:
    """Everything before the first system header (``TargetModel``,
    ``FormatVersion``, ``DateModified``, ``StateInfo``, ``CountyInfo``, ...)."""
    for i, r in enumerate(doc.records):
        if r.tag in SYSTEM_HEADER_TAGS:
            return doc.records[:i]
    return list(doc.records)


def segment_systems(doc: RecordDocument) -> List[SystemSlice]:
    """Segment a parsed ``s_<state>.hpd`` document into one
    :class:`SystemSlice` per ``Conventional``/``Trunk`` header — a single
    linear scan collecting header indices, then slicing the ranges between
    consecutive starts (mirrors the documented segmentation algorithm)."""
    starts = [i for i, r in enumerate(doc.records) if r.tag in SYSTEM_HEADER_TAGS]
    slices = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(doc.records)
        slices.append(SystemSlice(records=doc.records[start:end]))
    return slices


def serialize_system_slice(system_slice: SystemSlice) -> List[Dict[str, object]]:
    """A JSON-safe (plain dict/list/str) form of a :class:`SystemSlice`'s
    records, for carrying the full record tree through
    :class:`wasds150.sources.facts.NormalizedFact.raw` (a plain ``dict``)
    without losing it -- see
    :mod:`wasds150.sources.sentinel_local`'s module docstring for why this
    matters (finding: the adapter used to summarize a system into one fact
    and discard the tree a real ``.hpe`` needs)."""
    return [{"tag": r.tag, "fields": list(r.fields)} for r in system_slice.records]


def deserialize_system_slice(data: List[Dict[str, object]]) -> SystemSlice:
    """Inverse of :func:`serialize_system_slice`."""
    records = [Record(tag=str(item["tag"]), fields=list(item.get("fields", []))) for item in data]
    return SystemSlice(records=records)


def is_voice_channel(record: Record) -> bool:
    """``TGID``/``C-Freq`` only — explicitly excludes ``T-Freq`` (a site's
    control/voice frequency is trunk scaffolding, not a user-selectable
    channel)."""
    return record.tag in ("TGID", "C-Freq")


# ---------------------------------------------------------------------------
# HPDB SystemSlice -> canonical System conversion (the inverse of
# wasds150.hpe.builders' build_system_records/build_conventional_records/
# build_trunk_records: same BCDX36HP_SCHEMA field layout, read instead of
# written). Preserves every real RadioReference id it finds as this
# project's own `.id` (see module docstring, "Preserving ids for merge").
# ---------------------------------------------------------------------------


def _field(record: Record, schema: TagSchema, name: str) -> str:
    spec = schema.field_by_name(name)
    if spec is None:
        return ""
    return record.get(spec.index - 1, "") or ""


def _keyed_id(record: Record, fallback: str) -> str:
    """This record's own RadioReference id (e.g. ``"hpdb:SiteId:8201"``),
    or ``fallback`` if it has none (a Favorites-dialect-blanked record, or
    a synthetic caller-built one) -- never blank, since every catalog
    dataclass requires a non-empty ``id``."""
    ident = own_id(record)
    return f"hpdb:{ident[0]}:{ident[1]}" if ident is not None else fallback


def _hpdb_avoid(record: Record, schema: TagSchema) -> bool:
    return _field(record, schema, "avoid") == "On"


def _hpdb_float(record: Record, schema: TagSchema, name: str) -> Optional[float]:
    raw = _field(record, schema, name)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _hpdb_int(record: Record, schema: TagSchema, name: str) -> Optional[int]:
    raw = _field(record, schema, name)
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _c_freq_channel(record: Record) -> "Channel":
    from wasds150.models.catalog import Channel

    schema = BCDX36HP_SCHEMA["C-Freq"]
    freq_hz = _hpdb_float(record, schema, "freq_hz")
    return Channel(
        id=_keyed_id(record, stable_id_fallback(record, "c-freq")),
        label=_field(record, schema, "name"),
        freq_mhz=(freq_hz / 1_000_000) if freq_hz is not None else None,
        mode=_field(record, schema, "mode") or None,
        tone=_field(record, schema, "tone"),
        service_type=_hpdb_int(record, schema, "service_type"),
        avoid=_hpdb_avoid(record, schema),
    )


def _tgid_channel(record: Record) -> "Channel":
    from wasds150.models.catalog import Channel

    schema = BCDX36HP_SCHEMA["TGID"]
    return Channel(
        id=_keyed_id(record, stable_id_fallback(record, "tgid")),
        label=_field(record, schema, "name"),
        tgid=_hpdb_int(record, schema, "tgid"),
        mode=_field(record, schema, "mode") or None,
        service_type=_hpdb_int(record, schema, "service_type"),
        avoid=_hpdb_avoid(record, schema),
    )


def _c_group_department(record: Record) -> "Department":
    from wasds150.models.catalog import Department

    schema = BCDX36HP_SCHEMA["C-Group"]
    return Department(
        id=_keyed_id(record, stable_id_fallback(record, "c-group")),
        label=_field(record, schema, "name"),
        lat=_hpdb_float(record, schema, "lat"),
        lon=_hpdb_float(record, schema, "lon"),
        range_miles=_hpdb_float(record, schema, "range"),
        shape=_field(record, schema, "shape"),
        avoid=_hpdb_avoid(record, schema),
    )


def _t_group_department(record: Record) -> "Department":
    from wasds150.models.catalog import Department

    schema = BCDX36HP_SCHEMA["T-Group"]
    return Department(
        id=_keyed_id(record, stable_id_fallback(record, "t-group")),
        label=_field(record, schema, "name"),
        lat=_hpdb_float(record, schema, "lat"),
        lon=_hpdb_float(record, schema, "lon"),
        range_miles=_hpdb_float(record, schema, "range"),
        shape=_field(record, schema, "shape"),
        avoid=_hpdb_avoid(record, schema),
    )


def _site(record: Record) -> "Site":
    from wasds150.models.catalog import Site

    schema = BCDX36HP_SCHEMA["Site"]
    return Site(
        id=_keyed_id(record, stable_id_fallback(record, "site")),
        label=_field(record, schema, "name"),
        lat=_hpdb_float(record, schema, "lat"),
        lon=_hpdb_float(record, schema, "lon"),
        range_miles=_hpdb_float(record, schema, "range"),
        shape=_field(record, schema, "shape"),
        avoid=_hpdb_avoid(record, schema),
    )


def _t_freq(record: Record) -> "TrunkFrequency":
    from wasds150.models.catalog import TrunkFrequency

    schema = BCDX36HP_SCHEMA["T-Freq"]
    freq_hz = _hpdb_float(record, schema, "freq_hz")
    return TrunkFrequency(
        id=_keyed_id(record, stable_id_fallback(record, "t-freq")),
        freq_mhz=(freq_hz / 1_000_000) if freq_hz is not None else None,
        lcn=_hpdb_int(record, schema, "lcn"),
        usage=_field(record, schema, "usage"),
    )


def stable_id_fallback(record: Record, kind: str) -> str:
    """Deterministic fallback id for a record with no RadioReference id of
    its own (should not normally happen for real HPDB data -- every
    hierarchical record carries an id column -- but keeps this converter
    total rather than raising on unexpected input)."""
    from wasds150.util.hashing import stable_id

    return stable_id(f"{kind}:{'|'.join(record.fields)}", kind="hpdb-fallback")


def system_slice_to_system(system_slice: SystemSlice) -> "System":
    """Convert a segmented HPDB :class:`SystemSlice` (real record tree,
    from :func:`segment_systems`) into a canonical
    :class:`wasds150.models.catalog.System` -- the read direction that
    complements :mod:`wasds150.hpe.builders`' write direction, using the
    same :data:`~wasds150.hpe.schema.BCDX36HP_SCHEMA` column layout so the
    two are exact inverses for every field this project's model carries.

    Every RadioReference id this slice carries becomes that object's own
    ``id`` (see module docstring); :attr:`System.sid` is set to the
    system's own numeric id (``TrunkId``/``AgencyId``/... value) so
    :mod:`wasds150.recipes` can match it against a baseline row's own
    ``"SID <n>"`` text the same way it already matches on ``entity_key``.
    """
    from wasds150.models.catalog import System

    header = system_slice.header
    identity = system_slice.identity()
    sid = identity[1] if identity is not None else None
    sys_id = f"hpdb:{identity[0]}:{identity[1]}" if identity is not None else stable_id_fallback(header, "system")

    if system_slice.kind() == "Trunk":
        schema = BCDX36HP_SCHEMA["Trunk"]
        system = System(
            id=sys_id,
            label=system_slice.name(),
            sid=sid,
            tech=system_slice.tech() or None,
            avoid=_hpdb_avoid(header, schema),
        )
        current_site: Optional["Site"] = None
        for record in system_slice.records[1:]:
            if record.tag == "Site":
                current_site = _site(record)
                system.sites.append(current_site)
            elif record.tag == "T-Group" and current_site is not None:
                current_site.departments.append(_t_group_department(record))
            elif record.tag == "TGID" and current_site is not None and current_site.departments:
                current_site.departments[-1].channels.append(_tgid_channel(record))
            elif record.tag == "T-Freq":
                system.trunk_frequencies.append(_t_freq(record))
        return system

    # Conventional. Note: `sid` is deliberately left unset here -- a
    # Conventional system's own HPDB id is typically an AgencyId/CountyId
    # (see the AreaCounty quirk documented near the top of this module),
    # not a RadioReference "SID" the way a Trunk system's TrunkId/SysId is;
    # its full identity is still preserved verbatim as `System.id` above.
    schema = BCDX36HP_SCHEMA["Conventional"]
    system = System(id=sys_id, label=system_slice.name(), avoid=_hpdb_avoid(header, schema))
    current_department: Optional["Department"] = None
    for record in system_slice.records[1:]:
        if record.tag == "C-Group":
            current_department = _c_group_department(record)
            system.departments.append(current_department)
        elif record.tag == "C-Freq" and current_department is not None:
            current_department.channels.append(_c_freq_channel(record))
    return system


# ---------------------------------------------------------------------------
# County/state index (hpdb.cfg)
# ---------------------------------------------------------------------------


@dataclass
class CountyIndex:
    """Built once from a parsed ``hpdb.cfg``. County names are **not**
    unique across states (many "Washington" counties exist nationally), so
    ``by_name`` maps to a list — a caller wanting a specific state must
    intersect with a known ``state_id``."""

    by_id: Dict[int, str] = field(default_factory=dict)
    by_name: Dict[str, List[int]] = field(default_factory=dict)
    county_state: Dict[int, int] = field(default_factory=dict)
    state_by_id: Dict[int, str] = field(default_factory=dict)

    @classmethod
    def from_hpdb_cfg(cls, doc: RecordDocument) -> "CountyIndex":
        index = cls()
        for r in doc.records:
            if r.tag == "StateInfo":
                sid = own_id(r)
                name = r.get(2, "") or ""
                if sid is not None:
                    index.state_by_id[sid[1]] = name
            elif r.tag == "CountyInfo":
                cid = own_id(r)
                pid = parent_id(r)
                name = r.get(2, "") or ""
                if cid is not None:
                    index.by_id[cid[1]] = name
                    index.by_name.setdefault(name, []).append(cid[1])
                    if pid is not None:
                        index.county_state[cid[1]] = pid[1]
        return index

    def counties_named(self, name: str) -> List[int]:
        return list(self.by_name.get(name, []))

    def id_by_name(self, name: str, state_id: Optional[int] = None) -> Optional[int]:
        candidates = self.by_name.get(name, [])
        if state_id is not None:
            candidates = [cid for cid in candidates if self.county_state.get(cid) == state_id]
        return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# HPDB -> Favorites dialect conversion
# ---------------------------------------------------------------------------


def synthesize_dqks_record() -> Record:
    """One ``DQKs_Status`` line, all 100 quick-key slots ``"Off"`` — the
    exact default observed on a real Favorites-dialect fixture. HPDB never
    contains this tag at all; it exists only in the Favorites dialect."""
    dqks_schema = BCDX36HP_SCHEMA["DQKs_Status"]
    fields = [""] * (max(dqks_schema.arities) - 1)
    for i in range(100):
        spec = dqks_schema.field_by_name(f"quick_key_{i:02d}")
        fields[spec.index - 1] = "Off"
    return Record(tag="DQKs_Status", fields=fields)


def to_favorites_dialect(doc: RecordDocument, *, synthesize_dqks: bool = True) -> RecordDocument:
    """Convert a parsed HPDB document (or any slice of one) into the
    Favorites dialect:

    1. **Blank, never drop, identity columns** — columns 1/2 of every
       hierarchical record become the empty string, preserving arity (the
       scanner reads Favorites-dialect hierarchy positionally; there are no
       ids left to join on).
    2. **Drop ``AreaState``/``AreaCounty`` entirely** — they never appear in
       a Favorites export.
    3. **Synthesize exactly one ``DQKs_Status``** immediately after each
       ``Conventional``/``Trunk`` header, idempotently (skipped if one is
       already there). ``BandPlan_P25``/``BandPlan_Mot`` are never
       synthesized — see :mod:`wasds150.hpe.builders` for why omitting them
       by default is the documented-safe choice.

    Never mutates ``doc``; returns a new :class:`RecordDocument`.
    """
    new_records: List[Record] = []
    new_endings: List[str] = []
    n = len(doc.records)
    for i, (record, ending) in enumerate(zip(doc.records, doc.line_endings)):
        if record.tag in AREA_TAGS:
            continue
        if record.tag in HIERARCHICAL_TAGS:
            fields = list(record.fields)
            if len(fields) >= 1:
                fields[0] = ""
            if len(fields) >= 2:
                fields[1] = ""
            record = Record(tag=record.tag, fields=fields)
        new_records.append(record)
        new_endings.append(ending)
        if synthesize_dqks and record.tag in SYSTEM_HEADER_TAGS:
            next_tag = doc.records[i + 1].tag if i + 1 < n else None
            if next_tag != "DQKs_Status":
                new_records.append(synthesize_dqks_record())
                new_endings.append(ending)
    return RecordDocument(records=new_records, line_endings=new_endings)


# ---------------------------------------------------------------------------
# Selection primitives (generic predicates over SystemSlice)
# ---------------------------------------------------------------------------


def select_systems(systems: List[SystemSlice], predicate) -> List[SystemSlice]:
    """Generic whole-system keep/drop filter — ``by_county``/``within_radius``
    below are just this with a specific predicate; callers can compose their
    own the same way (by service type, free text, etc.)."""
    return [s for s in systems if predicate(s)]


def by_county(systems: List[SystemSlice], county_id: int) -> List[SystemSlice]:
    return select_systems(systems, lambda s: s.is_in_county(county_id))


def within_radius(systems: List[SystemSlice], lat: float, lon: float, radius_mi: float) -> List[SystemSlice]:
    return select_systems(systems, lambda s: s.is_within(lat, lon, radius_mi))


# ---------------------------------------------------------------------------
# Read-only file access
# ---------------------------------------------------------------------------


def parse_hpdb_cfg(text: str) -> RecordDocument:
    return parse_records(text)


def parse_state_hpd(text: str) -> RecordDocument:
    return parse_records(text)


def read_hpdb_cfg(path: Path) -> RecordDocument:
    return parse_hpdb_cfg(path.read_bytes().decode("ascii"))


def read_state_hpd(path: Path) -> RecordDocument:
    return parse_state_hpd(path.read_bytes().decode("ascii"))
