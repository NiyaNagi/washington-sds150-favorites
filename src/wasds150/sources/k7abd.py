"""K7ABD "Anytone Config Builder" CSV files, and the SeattleDMR copies of them.

Andrew Dickinson K7ABD's Config Builder (https://www.k7abd.net/anytone-config-builder/)
takes four small CSV files and produces an Anytone codeplug. The Pacific
Northwest DMR community maintains those inputs for the PNWDigital and
SeattleDMR networks and publishes them at https://seattledmr.com/ConfigBuilder/,
which makes them the most complete machine-readable statement of *which
talkgroup sits on which timeslot of which repeater* in this region.

Formats (verified against the 2025-09-22 files):

``Digital-Repeaters__*.csv``::

    Zone Name,Comment,Power,RX Freq,TX Freq,Color Code,<one column per talkgroup>...
    Bellevu/Cougar;BVV,,High,147.02,147.62,1,2,1,-,...

  ``Zone Name`` is ``<zone label>;<3-letter code>``. Talkgroup columns hold
  the timeslot (``1``/``2``) the talkgroup is carried on, or ``-``.

``Talkgroups__*.csv``: ``<name>,<id>`` with no header. A name ending in a
  digit after a space (``Washington 1``) carries the network's suggested
  timeslot, but the repeater matrix is authoritative.

``Analog__*.csv``::

    Zone,Channel Name,Bandwidth,Power,RX Freq,TX Freq,CTCSS Decode,CTCSS Encode,TX Prohibit

The :class:`SeattleDmrSource` adapter fetches the published copies through
the shared HTTP cache and emits one ``frequency`` fact per repeater/talkgroup
pair and per analog channel. :mod:`wasds150.recipes.dmr_networks` turns those
facts into Favorites Lists; ``scripts/radios/build_atd890_dmr_snapshot.py``
turns the same files into the checked-in snapshot module
:mod:`wasds150.catalog.atd890_dmr` so plans resolve without a network.
"""
from __future__ import annotations

import csv
import datetime
import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

SEATTLEDMR_BASE = "https://seattledmr.com/ConfigBuilder/"
SEATTLEDMR_FILES = {
    "digital_repeaters": SEATTLEDMR_BASE + "Digital-Repeaters-Merged.csv",
    "talkgroups": SEATTLEDMR_BASE + "Talkgroups-Merged.csv",
    "analog": SEATTLEDMR_BASE + "Analog-Public-Merged.csv",
}
SEATTLEDMR_INFO_URL = "https://seattledmr.com/"
PNWDIGITAL_URL = "https://pnwdigital.net/talkgroups/"
DEFAULT_TTL_SECONDS = 7 * 24 * 3600

#: Repeater codes grouped by where the site is, from the zone labels in the
#: file and the operators' own pages. Anything not listed is outside
#: Washington (Oregon, Idaho, British Columbia, California) or a hotspot.
PUGET_SOUND_CODES = frozenset(
    {"BVV", "BVC", "SHR", "SEC", "SEM", "SUL", "TLE", "TLW", "TBV", "TBU", "TB2", "TAR",
     "NBV", "SHL", "BWT", "SCE", "LFP", "SWE", "KNW"}
)
WESTERN_WA_CODES = frozenset({"CHB", "COM", "OCS", "BEU", "BEV", "KEC", "LVR", "ARA"})
EASTERN_WA_CODES = frozenset(
    {"NMV", "NMU", "RRU", "RRV", "ELV", "EPB", "WEN", "MAZ", "WRZ", "YAK", "PHH", "TRU",
     "TRV", "SKU", "SKV", "SPL", "SRv", "PAU", "PAV", "PUW", "TFM"}
)
SEATTLEDMR_CODES = frozenset({"BWT", "SCE", "LFP", "SWE", "KNW"})
#: Hotspots and personal MMDVM servers in the file: real DMR, but nothing a
#: scanner or a visitor should program.
HOTSPOT_PREFIXES = ("MM/", "BC:MM", "SeattleDMR;HOT")

_ZONE_RE = re.compile(r"^(?P<label>[^;]+?)\s*(?:;(?P<code>[A-Za-z0-9]{2,4}))?$")


@dataclass(frozen=True)
class TalkgroupDef:
    name: str
    tg_id: int


@dataclass
class RepeaterDef:
    label: str
    code: str
    rx_mhz: float
    tx_mhz: float
    color_code: int
    power: str = "High"
    comment: str = ""
    #: talkgroup column name -> timeslot
    slots: Dict[str, int] = field(default_factory=dict)

    @property
    def region(self) -> str:
        if self.code in PUGET_SOUND_CODES:
            return "Puget Sound"
        if self.code in WESTERN_WA_CODES:
            return "Western Washington"
        if self.code in EASTERN_WA_CODES:
            return "Eastern Washington"
        return "Outside Washington"

    @property
    def network(self) -> str:
        return "SeattleDMR" if self.code in SEATTLEDMR_CODES else "PNWDigital"

    @property
    def is_hotspot(self) -> bool:
        return self.label.startswith(HOTSPOT_PREFIXES) or self.code == "HOT" or self.rx_mhz == self.tx_mhz and self.rx_mhz < 431.0


@dataclass(frozen=True)
class AnalogDef:
    zone: str
    name: str
    bandwidth: str
    power: str
    rx_mhz: float
    tx_mhz: float
    rx_tone: str
    tx_tone: str
    tx_prohibit: bool


def _split_zone(value: str) -> Tuple[str, str]:
    match = _ZONE_RE.match(value.strip())
    if not match:
        return value.strip(), ""
    label = match.group("label").strip()
    code = (match.group("code") or "").strip()
    if not code and label.lower().startswith("n bend"):
        code = "NBV"
    return label, code


def parse_talkgroups(text: str) -> List[TalkgroupDef]:
    result: List[TalkgroupDef] = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2:
            continue
        name = row[0].strip()
        try:
            tg_id = int(row[1].strip())
        except ValueError:
            continue
        if name:
            result.append(TalkgroupDef(name=name, tg_id=tg_id))
    return result


def parse_digital_repeaters(text: str) -> List[RepeaterDef]:
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        return []
    header = [h.strip() for h in header]
    tg_columns = header[6:]
    result: List[RepeaterDef] = []
    for row in reader:
        if len(row) < 6 or not row[0].strip():
            continue
        label, code = _split_zone(row[0])
        try:
            rx = float(row[3])
            tx = float(row[4])
            cc = int(row[5])
        except ValueError:
            continue
        slots: Dict[str, int] = {}
        for name, value in zip(tg_columns, row[6:]):
            value = value.strip()
            if value in ("1", "2"):
                slots[name] = int(value)
        result.append(
            RepeaterDef(label=label, code=code, rx_mhz=rx, tx_mhz=tx, color_code=cc,
                        power=row[2].strip() or "High", comment=row[1].strip(), slots=slots)
        )
    return result


def _tone(value: str) -> str:
    text = value.strip()
    if not text or text.lower() == "off":
        return ""
    if text.upper().startswith("D") and text[1:4].isdigit():
        return f"D{text[1:4]}"
    try:
        return f"TONE=C{float(text):g}"
    except ValueError:
        return ""


def parse_analog(text: str) -> List[AnalogDef]:
    reader = csv.DictReader(io.StringIO(text))
    result: List[AnalogDef] = []
    for row in reader:
        try:
            rx = float(row["RX Freq"])
            tx = float(row["TX Freq"])
        except (KeyError, ValueError, TypeError):
            continue
        result.append(
            AnalogDef(
                zone=(row.get("Zone") or "").strip(),
                name=(row.get("Channel Name") or "").strip(),
                bandwidth=(row.get("Bandwidth") or "25K").strip(),
                power=(row.get("Power") or "High").strip(),
                rx_mhz=rx,
                tx_mhz=tx,
                rx_tone=_tone(row.get("CTCSS Decode") or ""),
                tx_tone=_tone(row.get("CTCSS Encode") or ""),
                tx_prohibit=(row.get("TX Prohibit") or "").strip().lower() == "on",
            )
        )
    return result


_SLOT_SUFFIX_RE = re.compile(r"^(?P<name>.*\d)-[12]$")


def talkgroup_short_name(column: str) -> str:
    """``TAC 310-2`` -> ``TAC 310``, ``Hawaii 1-2`` -> ``Hawaii 1``.

    The Config Builder column carries a ``-<slot>`` hint after a numbered
    name; that hint is not part of the talkgroup's name. Names such as
    ``Washington 1`` or ``Local 2`` keep their digit because it is the name
    the network uses (``Local 1`` and ``Local 2`` are different talkgroups).
    """
    text = column.strip()
    match = _SLOT_SUFFIX_RE.match(text)
    return match.group("name") if match else text


#: Site words for repeater codes whose zone label does not name the place
#: the coordinator lists the machine under.
CODE_SITE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "SHR": ("Shoreline", "Lake Forest Park"),
    "LFP": ("Lake Forest Park",),
    "NBV": ("North Bend",),
    "BWT": ("Tiger",),
    "KNW": ("Tiger",),
    "TAR": ("Tacoma",),
}

_TOKEN_RE = re.compile(r"[A-Za-z]{4,}")


def site_tokens(repeater: RepeaterDef) -> frozenset:
    """Words that identify the repeater's site, for matching against a
    coordinator's label (``WA7DMR - Cougar Mtn``)."""
    words = {t.lower() for t in _TOKEN_RE.findall(repeater.label)}
    for alias in CODE_SITE_ALIASES.get(repeater.code, ()):
        words.update(t.lower() for t in _TOKEN_RE.findall(alias))
    return frozenset(words)


class SeattleDmrSource(OnlineSourceAdapter):
    name = "seattledmr"
    available = True
    kind = "facts"

    def __init__(self, urls: Optional[Dict[str, str]] = None, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.urls = dict(urls or SEATTLEDMR_FILES)
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        payload: Dict[str, str] = {}
        for key, url in self.urls.items():
            result = http_client.fetch(url, ttl_seconds=self.ttl_seconds, source_id=self.name, max_bytes=1024 * 1024)
            payload[key] = result.content.decode("utf-8-sig", errors="replace")
        return RawDoc(
            source_adapter=self.name,
            payload=payload,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        payload = raw.payload or {}
        talkgroups = {tg.name: tg for tg in parse_talkgroups(payload.get("talkgroups", ""))}
        repeaters = parse_digital_repeaters(payload.get("digital_repeaters", ""))
        analog = parse_analog(payload.get("analog", ""))
        return NormalizeResult(
            facts=list(facts_from_k7abd(repeaters, talkgroups, analog, retrieved_at=raw.fetched_at)),
            warnings=[
                f"seattledmr: {len(repeaters)} repeaters, {len(talkgroups)} talkgroups, "
                f"{len(analog)} analog channels from {SEATTLEDMR_BASE}"
            ],
        )


def facts_from_k7abd(
    repeaters: Iterable[RepeaterDef],
    talkgroups: Dict[str, TalkgroupDef],
    analog: Iterable[AnalogDef],
    *,
    retrieved_at: str = "",
    source_id: str = "seattledmr",
) -> Iterable[NormalizedFact]:
    for repeater in repeaters:
        if repeater.is_hotspot:
            continue
        for column, slot in sorted(repeater.slots.items()):
            tg = talkgroups.get(column)
            if tg is None:
                continue
            short = talkgroup_short_name(column)
            yield NormalizedFact(
                entity_key=f"k7abd:{repeater.code or repeater.label}:{repeater.rx_mhz:.5f}:{tg.tg_id}:{slot}",
                fact_type="frequency",
                # "Washington 1 BVV": talkgroup first, then the repeater code,
                # the way the network's own codeplugs name channels.
                name=f"{short} {repeater.code}".strip(),
                freq_mhz=repeater.rx_mhz,
                offset_mhz=round(repeater.tx_mhz - repeater.rx_mhz, 6),
                tone=f"ColorCode={repeater.color_code}",
                mode="DMR",
                location_precision="unknown",
                source_id=source_id,
                source_url=SEATTLEDMR_FILES["digital_repeaters"],
                retrieved_at=retrieved_at,
                raw={
                    "kind": "digital",
                    "repeater_label": repeater.label,
                    "repeater_code": repeater.code,
                    "region": repeater.region,
                    "network": repeater.network,
                    "site_tokens": sorted(site_tokens(repeater)),
                    "talkgroup_column": column,
                    "talkgroup_name": short,
                    "power": repeater.power,
                },
                tx_freq_mhz=repeater.tx_mhz,
                dmr_color_code=repeater.color_code,
                dmr_timeslot=slot,
                dmr_talkgroup=tg.tg_id,
            )
    for channel in analog:
        yield NormalizedFact(
            entity_key=f"k7abd:analog:{channel.zone}:{channel.name}:{channel.rx_mhz:.5f}",
            fact_type="frequency",
            name=channel.name,
            freq_mhz=channel.rx_mhz,
            offset_mhz=round(channel.tx_mhz - channel.rx_mhz, 6),
            tone=channel.rx_tone or None,
            mode="NFM" if channel.bandwidth.upper().startswith("12") else "FM",
            location_precision="unknown",
            source_id=source_id,
            source_url=SEATTLEDMR_FILES["analog"],
            retrieved_at=retrieved_at,
            raw={
                "kind": "analog",
                "zone": channel.zone,
                "tx_tone": channel.tx_tone,
                "tx_prohibit": channel.tx_prohibit,
                "power": channel.power,
            },
            tx_freq_mhz=channel.tx_mhz,
        )
