"""WWARA (Western Washington Amateur Relay Association) repeater
coordination data.

**Confirmed live** (fetched directly during implementation):
``https://www.wwara.org/DataBaseExtract.zip`` -> a zip containing
``WWARA-rptrlist-<YYYYMMDD>.csv`` (plus pending/expired/about-to-expire
variants and ``readme.txt``/``copyright.txt``). The CSV's **first line is
a version marker** (``DATA_SPEC_VERSION=2015.2.2``), not the header — the
real header (confirmed live) is::

    FC_RECORD_ID, SOURCE, OUTPUT_FREQ, INPUT_FREQ, STATE, CITY, LOCALE,
    CALL, SPONSOR, CTCSS_IN, CTCSS_OUT, DCS_CDCSS, DTMF, LINK, FM_WIDE,
    FM_NARROW, DSTAR_DV, DSTAR_DD, DMR, DMR_COLOR_CODE, FUSION, FUSION_DSQ,
    P25_PHASE_1, P25_PHASE_2, P25_NAC, NXDN_DIGITAL, NXDN_MIXED, NXDN_RAN,
    ATV, DATV, RACES, ARES, WX, URL, LATITUDE, LONGITUDE, EXPIRATION_DATE,
    COMMENT

**License** (from the zip's own ``readme.txt``, confirmed live): WWARA
explicitly publishes this **for programming radios** ("designed to be
generic and able to be consumed [by] the software hams use[d] to program
their radios") — exactly this project's use case. ``copyright.txt``
reserves rights against wholesale reproduction/redistribution of the
compiled database; this adapter caches the file locally (never committed
to the repo) and derives per-repeater facts for the user's own generated
catalog, consistent with the readme's stated intent, rather than
republishing WWARA's file as-is.

Some repeaters' coordinates are intentionally fuzzed (to ~50 miles) at the
owner's request per the readme — this adapter conservatively marks all
WWARA coordinates ``"unknown"`` precision rather than asserting "exact" for
data it cannot itself verify is unfuzzed.
"""
from __future__ import annotations

import csv
import datetime
import io
import re
import zipfile
from typing import Any, List, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

DATABASE_EXTRACT_URL = "https://www.wwara.org/DataBaseExtract.zip"
#: Matches their nightly regeneration cadence.
DEFAULT_TTL_SECONDS = 24 * 3600
ASSUME_LOCATION_PRECISION = "unknown"

_MAIN_CSV_RE = re.compile(r"^WWARA-rptrlist-(\d{8})\.csv$")


def parse_wwara_zip(data: bytes):
    """Returns ``(rows, source_updated_iso)`` — ``rows`` a list of dicts
    (real header, confirmed live), ``source_updated_iso`` the date embedded
    in the filename itself (more trustworthy than any HTTP header)."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        main_name = next((n for n in zf.namelist() if _MAIN_CSV_RE.match(n)), None)
        if main_name is None:
            raise ValueError("could not find a WWARA-rptrlist-<date>.csv entry in the zip")
        date_str = _MAIN_CSV_RE.match(main_name).group(1)
        source_updated = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        with zf.open(main_name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8-sig")
            lines = text.readlines()
    # First line is "DATA_SPEC_VERSION=...", not the header.
    body = lines[1:] if lines and lines[0].startswith("DATA_SPEC_VERSION") else lines
    reader = csv.DictReader(body)
    return list(reader), source_updated


class WwaraSource(OnlineSourceAdapter):
    name = "wwara"
    available = True
    kind = "facts"

    def __init__(self, state: str = "WA", url: str = DATABASE_EXTRACT_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.state = state
        self.url = url
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        result = http_client.fetch(
            self.url, ttl_seconds=self.ttl_seconds, source_id=self.name, max_bytes=5 * 1024 * 1024
        )
        return RawDoc(
            source_adapter=self.name,
            payload=result.content,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        rows, source_updated = parse_wwara_zip(raw.payload)
        facts: List[NormalizedFact] = []
        warnings: List[str] = []

        for row in rows:
            if row.get("STATE", "").strip() != self.state:
                continue
            call = row.get("CALL", "").strip()
            try:
                freq = float(row["OUTPUT_FREQ"]) if row.get("OUTPUT_FREQ") else None
            except ValueError:
                freq = None
                warnings.append(f"{call}: could not parse OUTPUT_FREQ {row.get('OUTPUT_FREQ')!r}")
            try:
                input_freq = float(row["INPUT_FREQ"]) if row.get("INPUT_FREQ") else None
            except ValueError:
                input_freq = None
            offset_mhz = (input_freq - freq) if (freq is not None and input_freq is not None) else None
            tone = row.get("CTCSS_OUT") or row.get("DCS_CDCSS") or None
            try:
                lat = float(row["LATITUDE"]) if row.get("LATITUDE") else None
                lon = float(row["LONGITUDE"]) if row.get("LONGITUDE") else None
            except ValueError:
                lat = lon = None
            record_id = row.get("FC_RECORD_ID", "").strip()
            entity_key = f"wwara:{record_id}" if record_id else f"wwara:{call}:{freq}"
            if row.get("DMR") == "Y":
                mode = "DMR"
                color_code = re.sub(r"\D", "", row.get("DMR_COLOR_CODE", ""))
                tone = f"ColorCode={color_code}" if color_code else None
            elif row.get("P25_PHASE_1") == "Y" or row.get("P25_PHASE_2") == "Y":
                mode = "P25"
                nac = row.get("P25_NAC", "").strip()
                tone = f"NAC={nac}" if nac else None
            elif row.get("FM_NARROW") == "Y":
                mode = "NFM"
                tone = row.get("CTCSS_OUT", "").strip() or row.get("DCS_CDCSS", "").strip() or None
            elif row.get("FM_WIDE") == "Y":
                mode = "FM"
                tone = row.get("CTCSS_OUT", "").strip() or row.get("DCS_CDCSS", "").strip() or None
            else:
                mode = "AUTO"  # D-STAR/Fusion/other carrier: scanner cannot decode voice.
                tone = None
            if tone and mode in ("FM", "NFM"):
                tone = f"TONE=C{tone}" if row.get("CTCSS_OUT", "").strip() else f"D{tone.zfill(3)}"
            facts.append(
                NormalizedFact(
                    entity_key=entity_key,
                    fact_type="coordination",
                    name=f"{call} ({row.get('CITY', '')})".strip(),
                    freq_mhz=freq,
                    offset_mhz=offset_mhz,
                    tone=tone,
                    mode=mode,
                    county=None,  # WWARA publishes city/locale, not county directly
                    lat=lat,
                    lon=lon,
                    location_precision=ASSUME_LOCATION_PRECISION,
                    source_id=self.name,
                    source_url=row.get("URL") or self.url,
                    source_updated=source_updated,
                    retrieved_at=raw.fetched_at,
                    raw=row,
                )
            )
        return NormalizeResult(facts=facts, warnings=warnings)
