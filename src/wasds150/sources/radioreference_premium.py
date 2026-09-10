"""RadioReference Premium — import of exports the user downloaded themselves.

A logged-in Premium subscriber can download a county or a whole state as
CSV from radioreference.com (``ctid_<id>_<stamp>.csv`` and
``stid_<id><stamp>.csv``). This adapter reads those files from a path the
user configured (``wasds150 sources configure --rr-export-path``), which may
be one file or a directory of them, and turns every row into a
:class:`~wasds150.sources.facts.NormalizedFact`. It never touches the
network, never redistributes anything, and the data it produces stays in
the user's local catalog (see ``docs/data-sources.md``).

**Verified layout** (RadioReference county and state CSV exports, September
2026)::

    "Frequency Output","Frequency Input","FCC Callsign",Agency/Category,
    [County,]Description,"Alpha Tag","PL Output Tone","PL Input Tone",Mode,
    "Class Station Code",Tag

* ``County`` is present only in the state-wide export; a county export
  carries the county in its filename (``ctid_2974``) rather than a column.
* ``Frequency Input`` is ``0.00000`` when there is no input.
* Tones are written ``103.5 PL``, ``023 DPL``, ``CSQ``, ``293 NAC``,
  ``37 RAN`` or ``CC 1|TG 9|SL 1`` (``*`` for an unspecified talkgroup or
  slot); ``n/a`` and blank mean none.
* ``Mode`` is one of ``FM``, ``FMN``, ``AM``, ``DMR``, ``NXDN``, ``NXDN48``,
  ``NXDN48E``, ``P25``, ``P25E``, ``Project 25``, ``D-STAR``, ``Motorola``,
  ``MPT-1327``, ``LTR``, ``EDACS``, ``iDEN``, ``Telm``.
* ``Tag == "TRS"`` rows are trunked-system site frequencies (control and
  voice channels of a system listed elsewhere with talkgroups); they are
  imported as ``fact_type="site"`` so nothing programs them as a
  conventional voice channel.

Older exports with different headers are still read through a tolerant
alias table, but a summary warning is always emitted so the caller can see
which layout was recognised.

**Credentials / SOAP hook**: :class:`RadioReferenceCredentials` is kept so
the live SOAP client (:mod:`wasds150.sources.radioreference_api`) and this
file importer share one configuration shape. Passing credentials here
without an export path raises :class:`RadioReferenceSoapNotImplemented`
pointing at that adapter; this module itself never makes a network call.
"""
from __future__ import annotations

import csv
import datetime
import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from wasds150.catalog.wa_counties import RADIOREFERENCE_CTIDS, WA_COUNTIES
from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

SOURCE_ID = "radioreference_premium"
RADIOREFERENCE_STATE_URL = "https://www.radioreference.com/db/browse/stid/53"

#: The verified export header, normalised to lower case.
_VERIFIED_COLUMNS = {
    "frequency output": "freq_out",
    "frequency input": "freq_in",
    "fcc callsign": "callsign",
    "agency/category": "category",
    "county": "county",
    "description": "description",
    "alpha tag": "alpha",
    "pl output tone": "tone_out",
    "pl input tone": "tone_in",
    "mode": "mode",
    "class station code": "station_class",
    "tag": "tag",
}

#: Tolerant fallback for exports with other headers (older layouts, agency
#: exports). Matched case-insensitively; anything unrecognised stays in
#: ``raw`` verbatim.
_CSV_COLUMN_ALIASES = {
    "county": ("county",),
    "system": ("system", "agency", "system/agency"),
    "site": ("site", "site description", "site name"),
    "description": ("description", "name"),
    "alpha": ("alpha tag", "tag"),
    "freq_out": ("frequency", "freq", "output freq", "output"),
    "freq_in": ("input", "input freq"),
    "tone_out": ("tone", "ctcss/dcs", "pl"),
    "tone_in": ("input tone",),
    "category": ("category", "service type"),
    "mode": ("mode",),
}

#: RadioReference mode labels -> the catalog's scanner vocabulary. D-STAR,
#: Fusion and the trunking control formats become ``AUTO`` (a carrier the
#: scanner can detect but not decode), matching what the WWARA adapter does.
_MODE_MAP = {
    "FM": "FM",
    "FMN": "NFM",
    "AM": "AM",
    "DMR": "DMR",
    "NXDN": "NXDN",
    "NXDN48": "NXDN",
    "NXDN96": "NXDN",
    "NXDN48E": "NXDN",
    "NXDN96E": "NXDN",
    "P25": "P25",
    "P25E": "P25",
    "PROJECT 25": "P25",
}

_PL_RE = re.compile(r"^(\d{2,3}(?:\.\d)?)\s*PL$", re.IGNORECASE)
_DPL_RE = re.compile(r"^(\d{3})\s*DPL$", re.IGNORECASE)
_NAC_RE = re.compile(r"^([0-9A-Fa-f]{1,3})\s*NAC$", re.IGNORECASE)
_RAN_RE = re.compile(r"^(\d{1,2})\s*RAN$", re.IGNORECASE)
_DMR_RE = re.compile(r"^CC\s*(\d{1,2})\|TG\s*([0-9*]+)\|SL\s*([12*])$", re.IGNORECASE)
_BARE_CTCSS_RE = re.compile(r"^\d{2,3}\.\d$")
_CTID_RE = re.compile(r"ctid[_-]?(\d+)", re.IGNORECASE)


class RadioReferenceSoapNotImplemented(NotImplementedError):
    """Raised when credentials are handed to the file importer."""


@dataclass
class RadioReferenceCredentials:
    """Shared credential shape for the SOAP client. Never logged --
    ``__repr__`` intentionally redacts every field."""

    username: str = ""
    password: str = ""
    app_key: str = ""

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "RadioReferenceCredentials(<redacted>)"

    __str__ = __repr__

    def is_configured(self) -> bool:
        return bool(self.username and self.password and self.app_key)


@dataclass(frozen=True)
class RrTone:
    """A RadioReference tone cell, decoded."""

    tone: str = ""  # catalog notation: TONE=C103.5 / D023 / NAC=293 / ColorCode=1
    color_code: Optional[int] = None
    talkgroup: Optional[int] = None
    slot: Optional[int] = None
    ran: Optional[int] = None
    raw: str = ""


def parse_rr_tone(text: Optional[str]) -> RrTone:
    value = (text or "").strip()
    if not value or value.lower() in ("n/a", "csq", "none"):
        return RrTone(raw=value)
    match = _PL_RE.match(value)
    if match:
        return RrTone(tone=f"TONE=C{float(match.group(1)):g}", raw=value)
    match = _DPL_RE.match(value)
    if match:
        return RrTone(tone=f"D{match.group(1)}", raw=value)
    match = _NAC_RE.match(value)
    if match:
        return RrTone(tone=f"NAC={match.group(1).upper()}", raw=value)
    match = _RAN_RE.match(value)
    if match:
        return RrTone(ran=int(match.group(1)), raw=value)
    match = _DMR_RE.match(value)
    if match:
        talkgroup = int(match.group(2)) if match.group(2) != "*" else None
        slot = int(match.group(3)) if match.group(3) != "*" else None
        color = int(match.group(1))
        return RrTone(tone=f"ColorCode={color}", color_code=color, talkgroup=talkgroup, slot=slot, raw=value)
    if _BARE_CTCSS_RE.match(value):
        return RrTone(tone=f"TONE=C{float(value):g}", raw=value)
    return RrTone(raw=value)


def normalize_mode(text: Optional[str]) -> str:
    key = (text or "").strip().upper()
    if not key:
        return "AUTO"
    return _MODE_MAP.get(key, "AUTO")


def _parse_freq(text: Optional[str]) -> Optional[float]:
    value = (text or "").strip()
    if not value:
        return None
    try:
        freq = float(value)
    except ValueError:
        return None
    return freq if freq > 0 else None


def county_from_filename(name: str) -> Optional[str]:
    """Recover the county a county export describes from its filename."""
    lowered = name.lower()
    for county in WA_COUNTIES:
        if county.lower().replace(" ", "-") in lowered.replace("_", "-") or county.lower() in lowered:
            return county
    match = _CTID_RE.search(name)
    if match:
        return RADIOREFERENCE_CTIDS.get(int(match.group(1)))
    if "stid" in lowered or "statewide" in lowered:
        return "Statewide"
    return None


def _match_alias(header: str) -> Optional[str]:
    lowered = header.strip().lower()
    if lowered in _VERIFIED_COLUMNS:
        return _VERIFIED_COLUMNS[lowered]
    for canonical, aliases in _CSV_COLUMN_ALIASES.items():
        if lowered in aliases:
            return canonical
    return None


def _fact_from_mapped(
    mapped: Dict[str, str],
    row: Dict[str, Any],
    *,
    index: int,
    default_county: Optional[str],
    filename: str,
    retrieved_at: str,
) -> Optional[NormalizedFact]:
    freq = _parse_freq(mapped.get("freq_out"))
    if freq is None:
        return None
    tx_freq = _parse_freq(mapped.get("freq_in"))
    tone_out = parse_rr_tone(mapped.get("tone_out"))
    tone_in = parse_rr_tone(mapped.get("tone_in"))
    mode = normalize_mode(mapped.get("mode"))
    county = (mapped.get("county") or "").strip() or default_county or None
    tag = (mapped.get("tag") or "").strip()
    category = (mapped.get("category") or mapped.get("system") or "").strip()
    description = (mapped.get("description") or "").strip()
    alpha = (mapped.get("alpha") or "").strip()
    name = description or alpha or category or f"row-{index}"
    is_trunked_site = tag.upper() == "TRS"

    raw: Dict[str, Any] = dict(row)
    raw.update(
        {
            "rr_category": category,
            "rr_description": description,
            "rr_alpha": alpha,
            "rr_tag": tag,
            "rr_mode": (mapped.get("mode") or "").strip(),
            "rr_callsign": (mapped.get("callsign") or "").strip(),
            "rr_station_class": (mapped.get("station_class") or "").strip(),
            "rr_tone_out": tone_out.raw,
            "rr_tone_in": tone_in.raw,
            "tx_tone": tone_in.tone,
            "rr_file": filename,
        }
    )
    entity_key = (
        f"rr_premium:{(county or 'unknown').lower()}:{category.lower()}:"
        f"{freq:.5f}:{(tx_freq or 0):.5f}:{mode}:{name.lower()}"
    )
    return NormalizedFact(
        entity_key=entity_key,
        fact_type="site" if is_trunked_site else "frequency",
        name=name,
        freq_mhz=freq,
        offset_mhz=(tx_freq - freq) if tx_freq is not None else None,
        tone=tone_out.tone or None,
        mode=mode,
        county=county,
        location_precision="unknown",
        source_id=SOURCE_ID,
        source_url=RADIOREFERENCE_STATE_URL,
        retrieved_at=retrieved_at,
        raw=raw,
        tx_freq_mhz=tx_freq,
        dmr_color_code=tone_out.color_code,
        dmr_timeslot=tone_out.slot,
        dmr_talkgroup=tone_out.talkgroup,
        nxdn_ran=tone_out.ran,
    )


def _parse_csv_export(text: str, *, retrieved_at: str, filename: str = "") -> NormalizeResult:
    reader = csv.DictReader(io.StringIO(text))
    facts: List[NormalizedFact] = []
    warnings: List[str] = []
    if not reader.fieldnames:
        warnings.append(f"{filename or 'export'}: no header row; nothing imported")
        return NormalizeResult(facts=facts, warnings=warnings)

    alias_by_header = {h: _match_alias(h) for h in reader.fieldnames}
    verified = all(h.strip().lower() in _VERIFIED_COLUMNS for h in reader.fieldnames)
    default_county = county_from_filename(filename) if filename else None
    skipped = 0
    sites = 0
    for index, row in enumerate(reader):
        mapped: Dict[str, str] = {}
        for header, value in row.items():
            canonical = alias_by_header.get(header)
            if canonical and value is not None:
                mapped[canonical] = value
        fact = _fact_from_mapped(
            mapped, row, index=index, default_county=default_county,
            filename=filename, retrieved_at=retrieved_at,
        )
        if fact is None:
            skipped += 1
            continue
        if fact.fact_type == "site":
            sites += 1
        facts.append(fact)

    layout = "verified RadioReference export layout" if verified else "tolerant alias mapping (unverified header)"
    warnings.append(
        f"{filename or 'export'}: {len(facts)} rows imported via {layout}; "
        f"{sites} trunked-site rows kept as site facts; {skipped} rows without a frequency skipped"
        + (f"; county {default_county!r} from filename" if default_county and "county" not in [
            alias_by_header.get(h) for h in reader.fieldnames] else "")
    )
    return NormalizeResult(facts=facts, warnings=warnings)


def _local_tag(elem: ET.Element) -> str:
    tag = elem.tag
    return tag.split("}", 1)[1] if "}" in tag else tag


def _parse_xml_export(text: str, *, retrieved_at: str, filename: str = "") -> NormalizeResult:
    warnings: List[str] = [
        f"{filename or 'export'}: XML element mapping is best-effort; review mapped facts before trusting them"
    ]
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return NormalizeResult(facts=[], warnings=warnings + [f"could not parse XML export: {exc}"])

    facts: List[NormalizedFact] = []
    default_county = county_from_filename(filename) if filename else None
    for index, elem in enumerate(root.iter()):
        children = list(elem)
        if not children:
            continue
        record: Dict[str, str] = {}
        for child in children:
            if list(child):
                continue
            record[_local_tag(child)] = (child.text or "").strip()
        if not record:
            continue
        mapped: Dict[str, str] = {}
        for key, value in record.items():
            canonical = _match_alias(key)
            if canonical:
                mapped[canonical] = value
        if not mapped:
            continue
        fact = _fact_from_mapped(
            mapped, record, index=index, default_county=default_county,
            filename=filename, retrieved_at=retrieved_at,
        )
        if fact is not None:
            facts.append(fact)
    if not facts:
        warnings.append("no recognizable records found in XML export")
    return NormalizeResult(facts=facts, warnings=warnings)


def _export_files(path: Path) -> List[Path]:
    if path.is_dir():
        files = sorted(p for p in path.iterdir() if p.suffix.lower() in (".csv", ".xml") and p.is_file())
        if not files:
            raise FileNotFoundError(f"radioreference_premium: no .csv/.xml exports in {path}")
        return files
    if not path.is_file():
        raise FileNotFoundError(f"radioreference_premium export file not found: {path}")
    return [path]


class RadioReferencePremiumSource(OnlineSourceAdapter):
    name = SOURCE_ID
    available = True
    kind = "local"

    def __init__(
        self,
        export_path: Optional[Path] = None,
        credentials: Optional[RadioReferenceCredentials] = None,
    ):
        self.export_path = Path(export_path) if export_path is not None else None
        self.credentials = credentials

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        # kind == "local": never uses http_client, even if one is passed.
        fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if self.export_path is not None:
            files = []
            for file in _export_files(self.export_path):
                files.append(
                    {
                        "format": "xml" if file.suffix.lower() == ".xml" else "csv",
                        "text": file.read_bytes().decode("utf-8-sig", errors="replace"),
                        "filename": file.name,
                    }
                )
            return RawDoc(source_adapter=self.name, payload={"files": files}, fetched_at=fetched_at)
        if self.credentials is not None and self.credentials.is_configured():
            raise RadioReferenceSoapNotImplemented(
                "radioreference_premium reads exported files only; for the live SOAP "
                "service use the 'radioreference_api' source (needs a RadioReference "
                "application key plus your Premium login), or export your county/state "
                "data from radioreference.com and pass it as export_path= to this source. "
                "See docs/data-sources.md."
            )
        return RawDoc(source_adapter=self.name, payload=None, fetched_at=fetched_at)

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        if raw.payload is None:
            return NormalizeResult(
                facts=[],
                warnings=["no radioreference_premium export_path configured; no facts produced"],
            )
        result = NormalizeResult()
        seen: set = set()
        for entry in raw.payload["files"]:
            if entry["format"] == "xml":
                part = _parse_xml_export(entry["text"], retrieved_at=raw.fetched_at, filename=entry["filename"])
            else:
                part = _parse_csv_export(entry["text"], retrieved_at=raw.fetched_at, filename=entry["filename"])
            duplicates = 0
            for fact in part.facts:
                if fact.entity_key in seen:
                    duplicates += 1
                    continue
                seen.add(fact.entity_key)
                result.facts.append(fact)
            result.warnings.extend(part.warnings)
            if duplicates:
                result.warnings.append(
                    f"{entry['filename']}: {duplicates} rows already imported from another export (state and county files overlap)"
                )
        return result
