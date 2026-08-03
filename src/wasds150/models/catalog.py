"""Canonical catalog model.

Design note (read this before "fixing" the flat shape): the existing
``washington-sds150-favorites.csv`` describes each Favorites List as a
single row of free-text fields (systems/sites/departments/channels are
prose, not machine-delimited records). Phases 1-4 modeled that faithfully as
:class:`FavoritesList` with the same 14 columns, plus stable identity
(``id``/``slug``), profile-facing fields (``enabled``, ``flqk``), and
provenance, leaving ``System``/``Department``/``Channel`` empty:
populating them accurately from the *baseline CSV's free text* would be
lossy and non-deterministic, so that phase left them unpopulated.

``System``/``Department``/``Channel``/``Site``/``TrunkFrequency`` are now
fleshed out so :mod:`wasds150.hpe` has a structured target to build
``Conventional``/``Trunk`` HPE record trees from. This loader/module still
never derives them directly from CSV free text (that discipline hasn't
changed) — :meth:`FavoritesList.from_csv_row` and :func:`Catalog.from_dict`
leave ``systems`` exactly as given (empty, unless the JSON payload already
carries populated ones). What *has* changed since that note was written:
a caller can now construct them losslessly/semantically rather than only
"explicitly by hand" — see :mod:`wasds150.recipes.systems` (matched local
HPDB/RadioReference facts, matched public-source facts, and a pure
free-text/seed tier that runs on every ``generate``/``preview`` — see
:mod:`wasds150.generate.pipeline`), all of which populate ``systems``
*after* this module hands back an otherwise-unpopulated row, never inside
it. ``systems``/``provenance`` are deliberately excluded from
:meth:`FavoritesList.content_hash` (see below), so none of this changes a
catalog's content hash or the "no local input reproduces the shipped
catalog exactly" guarantee (see ``docs/data-sources.md``).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from wasds150.models.provenance import Provenance
from wasds150.util.hashing import canonical_json, content_hash, stable_id

#: The 14 columns of the existing catalog CSV, in their original order.
#: catalog/loader.py relies on this order for byte-faithful round trips.
CSV_FIELDS: tuple = (
    "favorite_key",
    "favorite_name",
    "region",
    "counties",
    "scenario",
    "source_type",
    "system_or_category",
    "sites_or_coverage",
    "departments_or_channels",
    "mode",
    "monitorability",
    "upgrade_required",
    "source_url",
    "notes",
)

ORIGIN_BASELINE = "baseline"
ORIGIN_LOCAL = "local"


@dataclass
class Channel:
    """A single frequency (conventional) or talkgroup (trunked) entry.

    Field choices mirror what ``wasds150.hpe`` needs to build ``C-Freq``/
    ``TGID`` records (see that package's schema module for the byte-level
    field layout this maps onto): ``freq_mhz`` for conventional channels,
    ``tgid`` for trunked talkgroups, plus the handful of attributes that are
    common to both dialects.
    """

    id: str
    label: str
    freq_mhz: Optional[float] = None
    tgid: Optional[int] = None
    mode: Optional[str] = None
    notes: str = ""
    tone: str = ""
    service_type: Optional[int] = None
    priority: bool = False
    avoid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Channel":
        return cls(**data)


@dataclass
class Department:
    """A group of channels: a ``C-Group`` (conventional) or ``T-Group``
    (trunked) in HPE terms. The optional geo-fence fields (``lat``/``lon``/
    ``range_miles``/``shape``) are populated only when a group uses
    location-based scan gating; both dialects share this shape."""

    id: str
    label: str
    encrypted_bucket: bool = False
    dqk: Optional[int] = None
    channels: List[Channel] = field(default_factory=list)
    lat: Optional[float] = None
    lon: Optional[float] = None
    range_miles: Optional[float] = None
    shape: str = ""
    avoid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["channels"] = [c.to_dict() for c in self.channels]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Department":
        channels = [Channel.from_dict(c) for c in data.get("channels", [])]
        return cls(
            id=data["id"],
            label=data["label"],
            encrypted_bucket=data.get("encrypted_bucket", False),
            dqk=data.get("dqk"),
            channels=channels,
            lat=data.get("lat"),
            lon=data.get("lon"),
            range_miles=data.get("range_miles"),
            shape=data.get("shape", ""),
            avoid=data.get("avoid", False),
        )


@dataclass
class TrunkFrequency:
    """A ``T-Freq`` entry: one LCN (Logical Channel Number) -> frequency
    mapping for a trunked system. See ``wasds150.hpe.schema`` for the
    observed (9-field, not the 8-field spec) real-world column layout this
    maps onto; ``lcn`` is preserved verbatim from the source rather than
    zeroed, per the documented pitfall of assuming it's always a control
    channel."""

    id: str
    freq_mhz: Optional[float] = None
    lcn: Optional[int] = None
    usage: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrunkFrequency":
        return cls(**data)


@dataclass
class Site:
    """A trunked system site: geo-fence plus its ``T-Group`` departments."""

    id: str
    label: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    range_miles: Optional[float] = None
    shape: str = ""
    departments: List[Department] = field(default_factory=list)
    avoid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["departments"] = [dept.to_dict() for dept in self.departments]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Site":
        departments = [Department.from_dict(d) for d in data.get("departments", [])]
        return cls(
            id=data["id"],
            label=data["label"],
            lat=data.get("lat"),
            lon=data.get("lon"),
            range_miles=data.get("range_miles"),
            shape=data.get("shape", ""),
            departments=departments,
            avoid=data.get("avoid", False),
        )


@dataclass
class System:
    """A conventional or trunked radio system.

    Conventional systems use ``departments`` (``C-Group``) directly;
    trunked systems use ``sites`` (each with its own ``T-Group``
    departments) plus ``trunk_frequencies`` (the system-wide LCN table).
    ``tech`` holds the trunking technology tag (e.g. ``P25Standard``).
    """

    id: str
    label: str
    sid: Optional[int] = None
    wacn: Optional[str] = None
    tech: Optional[str] = None
    departments: List[Department] = field(default_factory=list)
    sites: List[Site] = field(default_factory=list)
    trunk_frequencies: List[TrunkFrequency] = field(default_factory=list)
    avoid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["departments"] = [dept.to_dict() for dept in self.departments]
        d["sites"] = [s.to_dict() for s in self.sites]
        d["trunk_frequencies"] = [tf.to_dict() for tf in self.trunk_frequencies]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "System":
        departments = [Department.from_dict(d) for d in data.get("departments", [])]
        sites = [Site.from_dict(s) for s in data.get("sites", [])]
        trunk_frequencies = [TrunkFrequency.from_dict(tf) for tf in data.get("trunk_frequencies", [])]
        return cls(
            id=data["id"],
            label=data["label"],
            sid=data.get("sid"),
            wacn=data.get("wacn"),
            tech=data.get("tech"),
            departments=departments,
            sites=sites,
            trunk_frequencies=trunk_frequencies,
            avoid=data.get("avoid", False),
        )


@dataclass
class FavoritesList:
    """One row of the catalog: a Uniden SDS150 Favorites List."""

    id: str
    slug: str
    favorite_key: str
    favorite_name: str
    region: str
    counties: str
    scenario: str
    source_type: str
    system_or_category: str
    sites_or_coverage: str
    departments_or_channels: str
    mode: str
    monitorability: str
    upgrade_required: str
    source_url: str
    notes: str
    enabled: bool = True
    flqk: Optional[int] = None
    origin: str = ORIGIN_BASELINE
    systems: List[System] = field(default_factory=list)
    provenance: List[Provenance] = field(default_factory=list)

    @classmethod
    def from_csv_row(
        cls,
        row: Dict[str, str],
        *,
        origin: str = ORIGIN_BASELINE,
        provenance: Optional[List[Provenance]] = None,
    ) -> "FavoritesList":
        slug = row["favorite_key"].strip().lower()
        return cls(
            id=stable_id(slug),
            slug=slug,
            favorite_key=row["favorite_key"],
            favorite_name=row["favorite_name"],
            region=row["region"],
            counties=row["counties"],
            scenario=row["scenario"],
            source_type=row["source_type"],
            system_or_category=row["system_or_category"],
            sites_or_coverage=row["sites_or_coverage"],
            departments_or_channels=row["departments_or_channels"],
            mode=row["mode"],
            monitorability=row["monitorability"],
            upgrade_required=row["upgrade_required"],
            source_url=row["source_url"],
            notes=row["notes"],
            origin=origin,
            provenance=provenance or [],
        )

    def csv_row(self) -> Dict[str, str]:
        """The 14-column CSV representation of this entry (values only)."""
        return {name: getattr(self, name) for name in CSV_FIELDS}

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["systems"] = [s.to_dict() for s in self.systems]
        d["provenance"] = [p.to_dict() for p in self.provenance]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FavoritesList":
        kwargs = {k: v for k, v in data.items() if k not in ("systems", "provenance")}
        kwargs["systems"] = [System.from_dict(s) for s in data.get("systems", [])]
        kwargs["provenance"] = [Provenance.from_dict(p) for p in data.get("provenance", [])]
        return cls(**kwargs)

    def content_hash(self) -> str:
        """Hash over the meaningful facts of this entry (order-independent
        of dict construction, stable across runs/machines/time).
        Deliberately excludes ``systems`` and ``provenance`` — both are
        additive, derived enrichment (see :mod:`wasds150.recipes.systems`),
        never a change to the 14 CSV fields/``enabled``/``flqk``/``origin``
        this hash is defined over — so populating them can never change a
        catalog's content hash or the "no local input reproduces the
        shipped catalog exactly" guarantee (see ``docs/data-sources.md``)."""
        payload = self.csv_row()
        payload["enabled"] = self.enabled
        payload["flqk"] = self.flqk
        payload["origin"] = self.origin
        return content_hash(payload)


@dataclass
class Catalog:
    """An ordered collection of :class:`FavoritesList` entries plus a
    deterministic content hash used to detect drift and to pin
    ``Profile.based_on_catalog_hash`` for the (future) merge engine."""

    favorites: List[FavoritesList] = field(default_factory=list)

    def content_hash(self) -> str:
        return content_hash([fl.content_hash() for fl in self.favorites])

    def by_slug(self, slug: str) -> Optional[FavoritesList]:
        for fl in self.favorites:
            if fl.slug == slug:
                return fl
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.content_hash(),
            "favorites": [fl.to_dict() for fl in self.favorites],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Catalog":
        return cls(favorites=[FavoritesList.from_dict(d) for d in data["favorites"]])
