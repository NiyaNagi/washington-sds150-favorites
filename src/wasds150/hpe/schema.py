"""BCDx36HP field/arity schema — the semantic layer on top of the generic,
lossless :mod:`wasds150.hpe.record` tab-record model.

Every ``TagSchema`` below records whether its arity/column layout was
**directly confirmed** against a real third-party fixture during this
project's implementation (``verified=True``, see
``scripts/fetch_hpe_fixtures.py`` / ``NOTICE.md`` for provenance) or is
carried over from the research report's citations only
(``verified=False``) because no fixture exercised that tag. Validation
(:func:`validate_schema`) only *enforces* arities for tags in this table; it
never rejects a tag it doesn't recognize — preserving unknown tags/fields
verbatim is the whole point of the lossless record layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from wasds150.hpe.codec import Dialect
from wasds150.hpe.record import RecordDocument

#: Uniden's own documented per-Favorites-List size ceiling.
MAX_FAVORITES_LIST_BYTES = 1 * 1024 * 1024
#: Uniden's own documented ceiling on the number of Favorites Lists.
MAX_FAVORITES_LISTS = 256
#: Number of quick-key slots == number of ``DQKs_Status`` boolean fields.
MAX_QUICK_KEYS = 100


@dataclass(frozen=True)
class FieldSpec:
    """One named column within a tag's line (0-based, tag included as
    column 0 — matching how offsets are cited throughout this module)."""

    index: int
    name: str
    description: str = ""


@dataclass(frozen=True)
class TagSchema:
    tag: str
    #: Allowed total column counts (tag + fields). More than one value
    #: means multiple observed/documented widths are accepted (see
    #: ``T-Freq`` below).
    arities: Tuple[int, ...]
    fields: Tuple[FieldSpec, ...] = ()
    verified: bool = False
    notes: str = ""

    def field_by_name(self, name: str) -> Optional[FieldSpec]:
        return next((f for f in self.fields if f.name == name), None)


# ---------------------------------------------------------------------------
# BCDx36HP (SDS150/SDS100/SDS200/BCD325P2/BCD436HP/536HP family) dialect.
#
# Arities and column offsets below for Conventional/C-Group/Rectangle/
# C-Freq/Trunk/Site/BandPlan_P25/T-Freq/T-Group/TGID/DQKs_Status were
# directly confirmed (verified=True) by parsing a real, third-party
# synthetic BCDx36HP `.hpd` fixture during this project's implementation
# (see NOTICE.md — FuzzyGophers/platypus, commit 5abb42b, GPL-2.0, facts
# only, no code reused). BandPlan_Mot's arity is carried over from the
# research report only (verified=False): no fixture exercised a Motorola
# band plan.
# ---------------------------------------------------------------------------

BCDX36HP_SCHEMA: Dict[str, TagSchema] = {
    "Conventional": TagSchema(
        tag="Conventional",
        arities=(15,),
        fields=(
            FieldSpec(3, "name"),
            FieldSpec(4, "avoid"),
            FieldSpec(6, "system_class", "literal 'Conventional' on real fixtures"),
        ),
        verified=True,
    ),
    "C-Group": TagSchema(
        tag="C-Group",
        arities=(11,),
        fields=(
            FieldSpec(3, "name"),
            FieldSpec(4, "avoid"),
            FieldSpec(5, "lat"),
            FieldSpec(6, "lon"),
            FieldSpec(7, "range"),
            FieldSpec(8, "shape"),
            FieldSpec(10, "category"),
        ),
        verified=True,
    ),
    "Rectangle": TagSchema(
        tag="Rectangle",
        arities=(6,),
        fields=(
            FieldSpec(2, "lat1"),
            FieldSpec(3, "lon1"),
            FieldSpec(4, "lat2"),
            FieldSpec(5, "lon2"),
        ),
        verified=True,
    ),
    "C-Freq": TagSchema(
        tag="C-Freq",
        arities=(18,),
        fields=(
            FieldSpec(3, "name"),
            FieldSpec(4, "avoid"),
            FieldSpec(5, "freq_hz"),
            FieldSpec(6, "mode"),
            FieldSpec(7, "tone"),
            FieldSpec(8, "service_type"),
            FieldSpec(17, "priority"),
        ),
        verified=True,
    ),
    "Trunk": TagSchema(
        tag="Trunk",
        arities=(22,),
        fields=(
            FieldSpec(3, "name"),
            FieldSpec(4, "avoid"),
            FieldSpec(6, "tech"),
        ),
        verified=True,
    ),
    "Site": TagSchema(
        tag="Site",
        arities=(19, 20),
        fields=(
            FieldSpec(3, "name"),
            FieldSpec(4, "avoid"),
            FieldSpec(5, "lat"),
            FieldSpec(6, "lon"),
            FieldSpec(7, "range"),
            FieldSpec(11, "shape"),
        ),
        verified=True,
        notes="20 fields observed on SDS150; 19 documented for some family siblings.",
    ),
    "T-Group": TagSchema(
        tag="T-Group",
        arities=(10,),
        fields=(
            FieldSpec(3, "name"),
            FieldSpec(4, "avoid"),
            FieldSpec(5, "lat"),
            FieldSpec(6, "lon"),
            FieldSpec(7, "range"),
            FieldSpec(8, "shape"),
        ),
        verified=True,
    ),
    "TGID": TagSchema(
        tag="TGID",
        arities=(17,),
        fields=(
            FieldSpec(3, "name"),
            FieldSpec(4, "avoid"),
            FieldSpec(5, "tgid"),
            FieldSpec(6, "mode"),
            FieldSpec(7, "service_type"),
            FieldSpec(15, "priority"),
            FieldSpec(16, "slot_or_cc"),
        ),
        verified=True,
    ),
    "T-Freq": TagSchema(
        tag="T-Freq",
        # The written spec documents 8 fields; every real BCDx36HP/1.00
        # fixture observed carries 9. Both are accepted; 9 is what this
        # project's builders emit. Column offsets below are as directly
        # observed on the 9-field real layout (col3=avoid, col4=freq_hz) —
        # note this differs from some paraphrased summaries of the older
        # 8-field spec, which is exactly the "format-version delta,
        # preserved verbatim" pitfall this project follows the fixture
        # bytes for rather than a secondhand summary.
        arities=(8, 9),
        fields=(
            FieldSpec(3, "avoid"),
            FieldSpec(4, "freq_hz"),
            FieldSpec(5, "lcn"),
            FieldSpec(6, "usage"),
        ),
        verified=True,
        notes="9-field width confirmed on a real BCDx36HP/1.00 fixture; 8-field spec width also accepted.",
    ),
    "DQKs_Status": TagSchema(
        tag="DQKs_Status",
        arities=(102,),
        fields=(FieldSpec(1, "reserved"),) + tuple(FieldSpec(2 + i, f"quick_key_{i:02d}") for i in range(100)),
        verified=True,
        notes="A quick-key *preference*, not a scan gate: both On and Off are valid working states.",
    ),
    "BandPlan_P25": TagSchema(
        tag="BandPlan_P25",
        arities=(50,),
        verified=True,
        notes="Omit unless the site needs a non-standard plan — adding it unnecessarily can prevent a P25 trunk from locking.",
    ),
    "BandPlan_Mot": TagSchema(
        tag="BandPlan_Mot",
        arities=(26,),
        verified=False,
        notes="Arity per research-report citation only; not exercised by any fixture used in this project.",
    ),
}

#: The `f_list.cfg` index file uses a different tag (`F-List`) with its own
#: very wide schema; kept separate since it lives in a different file, not
#: a Favorites List export/`.hpd`. Confirmed against a real fixture.
F_LIST_SCHEMA = TagSchema(
    tag="F-List",
    arities=(118,),
    fields=(
        FieldSpec(1, "user_name"),
        FieldSpec(2, "filename"),
        FieldSpec(3, "location_control"),
        FieldSpec(4, "monitor"),
        FieldSpec(5, "quick_key"),
        FieldSpec(6, "number_tag"),
    )
    + tuple(FieldSpec(7 + i, f"startup_key_{i}") for i in range(10))
    + tuple(FieldSpec(17 + i, f"s_qkey_{i:02d}") for i in range(100)),
    verified=True,
    notes="Confirmed against a real f_list.cfg fixture: 1 tag + 117 fields = 118 columns.",
)

# ---------------------------------------------------------------------------
# HomePatrol-1 dialect (`TargetModel=HomePatrol-1`, `FormatVersion=2.04`):
# legacy, column-shifted-by-one relative to BCDx36HP for the same tags
# (confirmed directly against a real HomePatrol-1 `.hpe` fixture: its
# `Conventional`/`C-Group` name field is at column 4, not column 3). Not
# used by the SDS150 and out of scope for this project's builders/writer,
# but recognized so `hpe inspect`/`decode` don't misinterpret it as
# BCDx36HP and misreport bogus validation errors.
# ---------------------------------------------------------------------------
KNOWN_DIALECTS = (
    Dialect(target_model="BCDx36HP", format_version="1.00"),
    Dialect(target_model="HomePatrol-1", format_version="2.04"),
)


def detect_dialect(doc: RecordDocument) -> Optional[Dialect]:
    """Extract ``(TargetModel, FormatVersion)`` from a parsed document, if
    present. Returns ``None`` if either header field is missing."""
    target_model_record = doc.find_first("TargetModel")
    format_version_record = doc.find_first("FormatVersion")
    if target_model_record is None or format_version_record is None:
        return None
    return Dialect(
        target_model=target_model_record.get(0, ""),
        format_version=format_version_record.get(0, ""),
    )


def validate_schema(doc: RecordDocument, dialect: Optional[Dialect] = None) -> List[str]:
    """Arity-check every record whose tag is in :data:`BCDX36HP_SCHEMA`.

    Unknown tags are never flagged (they're preserved verbatim by the
    record layer, not something this schema layer has an opinion about).
    If ``dialect`` is not the known BCDx36HP dialect, arity checks are
    skipped entirely (a different, real dialect has different offsets by
    design — see module docstring) and a single informational issue is
    returned instead so callers know why validation was skipped.
    """
    if dialect is None:
        dialect = detect_dialect(doc)
    if dialect is None:
        return ["no TargetModel/FormatVersion header found; cannot determine dialect"]
    if not dialect.is_bcdx36hp:
        return [
            f"dialect {dialect.target_model}/{dialect.format_version} is not BCDx36HP; "
            "arity validation is only defined for BCDx36HP and was skipped"
        ]

    issues: List[str] = []
    for record in doc.records:
        schema = BCDX36HP_SCHEMA.get(record.tag)
        if schema is None:
            continue
        if record.arity not in schema.arities:
            issues.append(
                f"{record.tag}: expected {schema.arities} total column(s), got {record.arity} "
                f"(fields={record.fields!r})"
            )
    return issues


# ---------------------------------------------------------------------------
# Tone / audio-option and service-type encoding.
# ---------------------------------------------------------------------------


def format_ctcss_tone(freq_hz_tenths: float) -> str:
    """``TONE=C<freq>`` — CTCSS analog tone, e.g. ``TONE=C156.7``."""
    return f"TONE=C{freq_hz_tenths:g}"


def format_dcs_tone(code: str) -> str:
    """``TONE=D<code>`` — DCS digital code, e.g. ``TONE=D023``."""
    return f"TONE=D{code}"


def format_p25_nac(nac_hex: str) -> str:
    """``NAC=<hex>`` or the literal ``NAC=Srch`` for search mode."""
    return f"NAC={nac_hex}"


#: 37 documented service-type codes + 8 "Custom" slots (208-217, of which
#: 216/217 are NASCAR-specific "Racing Officials"/"Racing Teams" — kept
#: here purely as documentation of the full enumerated range, independently
#: cross-checked across two references per the research report).
SERVICE_TYPES: Dict[int, str] = {
    1: "Multi-Dispatch",
    2: "Law Dispatch",
    3: "Fire Dispatch",
    4: "EMS Dispatch",
    6: "Multi-Tac",
    7: "Law Tac",
    8: "Fire-Tac",
    9: "EMS-Tac",
    11: "Interop",
    12: "Hospital",
    13: "Ham",
    14: "Public Works",
    15: "Aircraft",
    16: "Federal",
    17: "Business",
    20: "Railroad",
    21: "Other",
    22: "Multi-Talk",
    23: "Law Talk",
    24: "Fire-Talk",
    25: "EMS-Talk",
    26: "Transportation",
    29: "Emergency Ops",
    30: "Military",
    31: "Media",
    32: "Schools",
    33: "Security",
    34: "Utilities",
    37: "Corrections",
    208: "Custom 1",
    209: "Custom 2",
    210: "Custom 3",
    211: "Custom 4",
    212: "Custom 5",
    213: "Custom 6",
    214: "Custom 7",
    215: "Custom 8",
    216: "Racing Officials",
    217: "Racing Teams",
}
