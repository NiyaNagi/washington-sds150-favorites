"""FAA NASR (28-Day Subscription) — communications facilities and NAVAID
frequencies for Washington.

**Confirmed live during implementation** (downloaded and inspected the real
2026-06-11 cycle zip, ~248 MB):

* Index page ``https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/``
  lists direct links to ``https://nfdc.faa.gov/webContent/28DaySub/28DaySubscription_Effective_<YYYY-MM-DD>.zip``
  for each 28-day AIRAC cycle (27 found, back to 2024-06-13) — :func:`latest_nasr_zip_url`
  picks the lexicographically-greatest (== chronologically latest, since
  the dates are ISO ``YYYY-MM-DD``) match rather than assuming a "Current"
  DOM marker.
* **The CSV data is nested two zips deep** — a real structural fact this
  project's initial research pass did not anticipate: the top-level zip's
  ``CSV_Data/`` directory contains a *second* zip
  (``CSV_Data/<DD>_<Mon>_<YYYY>_CSV.zip``, e.g. ``11_Jun_2026_CSV.zip``),
  and only that inner zip holds the actual per-subject CSV files
  (``COM.csv``, ``NAV_BASE.csv``, ``APT_BASE.csv``, etc.) — the top-level
  zip's own ``*.txt`` files are a legacy fixed-width layout, not CSV.
* ``COM.csv`` real confirmed header: ``EFF_DATE, COMM_LOC_ID, COMM_TYPE,
  NAV_ID, NAV_TYPE, CITY, STATE_CODE, REGION_CODE, COUNTRY_CODE,
  COMM_OUTLET_NAME, LAT_*, LONG_*, FACILITY_ID, FACILITY_NAME, ALT_FSS_ID,
  ALT_FSS_NAME, OPR_HRS, COMM_STATUS_CODE, COMM_STATUS_DATE, REMARK`` — this
  is FSS/Remote Communications Outlet (RCO) facility data; **it does not
  carry a frequency column** (correcting the initial research pass's
  assumption that airport CTAF/UNICOM frequencies live here — they don't;
  no CSV subject file in the 2026-06-11 cycle carries airport CTAF/UNICOM/
  tower frequencies, only NAVAID frequencies do).
* ``NAV_BASE.csv`` real confirmed header includes a genuine ``FREQ``
  column (confirmed real value: Walla Walla VOR/DME ``ALW`` = 116.4 MHz,
  squarely inside the SDS150's 108-137 MHz civil AM aviation band) —
  **this is the adapter's actual frequency-fact source**, not ``COM.csv``.

Parsing is **header-name-based** (``csv.DictReader``, never positional),
specifically because FAA has an announced format change for the
2026-09-03 AIRAC cycle — this adapter tolerates added/reordered/renamed
*other* columns as long as the columns it actually reads
(``STATE_CODE``/``NAV_ID``/``NAV_TYPE``/``NAME``/``FREQ``/lat-lon for
``NAV_BASE.csv``; the ``COM.csv`` equivalents) are still present; missing
expected columns raise a clear error rather than silently producing wrong
facts.

Public domain (US federal work) — fully ingestible/redistributable.
"""
from __future__ import annotations

import csv
import datetime
import io
import re
import zipfile
from typing import Any, Dict, List, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

NASR_INDEX_URL = "https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/"
#: 28-day AIRAC cycle; check weekly for a filename-date change.
DEFAULT_TTL_SECONDS = 7 * 24 * 3600

_ZIP_URL_RE = re.compile(r"https://nfdc\.faa\.gov/webContent/28DaySub/28DaySubscription_Effective_[\d-]+\.zip")

_REQUIRED_NAV_COLUMNS = ("STATE_CODE", "NAV_ID", "NAV_TYPE", "NAME", "FREQ", "LAT_DECIMAL", "LONG_DECIMAL")


def latest_nasr_zip_url(index_html: str) -> Optional[str]:
    matches = _ZIP_URL_RE.findall(index_html)
    return max(matches) if matches else None


def _open_inner_csv_zip(outer_zip_bytes: bytes) -> zipfile.ZipFile:
    outer = zipfile.ZipFile(io.BytesIO(outer_zip_bytes))
    inner_name = next((n for n in outer.namelist() if n.startswith("CSV_Data/") and n.endswith("_CSV.zip")), None)
    if inner_name is None:
        raise ValueError("could not find CSV_Data/*_CSV.zip inside the NASR subscription zip")
    return zipfile.ZipFile(io.BytesIO(outer.read(inner_name)))


def _read_csv_rows(inner_zip: zipfile.ZipFile, filename: str) -> List[Dict[str, Any]]:
    with inner_zip.open(filename) as f:
        text = io.TextIOWrapper(f, encoding="utf-8-sig")
        return list(csv.DictReader(text))


class FaaNasrSource(OnlineSourceAdapter):
    name = "faa_nasr"
    available = True
    kind = "facts"

    def __init__(self, state: str = "WA", index_url: str = NASR_INDEX_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.state = state
        self.index_url = index_url
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        index_result = http_client.fetch(self.index_url, ttl_seconds=self.ttl_seconds, source_id=self.name)
        zip_url = latest_nasr_zip_url(index_result.content.decode("utf-8", errors="replace"))
        if zip_url is None:
            raise ValueError(f"could not find a 28DaySubscription zip URL on {self.index_url}")
        zip_result = http_client.fetch(
            zip_url,
            ttl_seconds=self.ttl_seconds,
            source_id=self.name,
            max_bytes=400 * 1024 * 1024,
        )
        return RawDoc(
            source_adapter=self.name,
            payload={"zip_bytes": zip_result.content, "zip_url": zip_url},
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        zip_bytes = raw.payload["zip_bytes"]
        zip_url = raw.payload["zip_url"]
        facts: List[NormalizedFact] = []
        warnings: List[str] = []

        inner_zip = _open_inner_csv_zip(zip_bytes)

        if "NAV_BASE.csv" not in inner_zip.namelist():
            warnings.append("NAV_BASE.csv not found in this cycle's CSV data; schema may have changed")
        else:
            nav_rows = _read_csv_rows(inner_zip, "NAV_BASE.csv")
            if nav_rows:
                missing = [c for c in _REQUIRED_NAV_COLUMNS if c not in nav_rows[0]]
                if missing:
                    warnings.append(f"NAV_BASE.csv is missing expected column(s) {missing}; skipping NAVAID facts")
                else:
                    for row in nav_rows:
                        if row.get("STATE_CODE") != self.state:
                            continue
                        freq_raw = row.get("FREQ", "")
                        try:
                            freq = float(freq_raw) if freq_raw else None
                        except ValueError:
                            freq = None
                        try:
                            lat = float(row["LAT_DECIMAL"]) if row.get("LAT_DECIMAL") else None
                            lon = float(row["LONG_DECIMAL"]) if row.get("LONG_DECIMAL") else None
                        except ValueError:
                            lat = lon = None
                        nav_id = row.get("NAV_ID", "")
                        nav_type = row.get("NAV_TYPE", "")
                        facts.append(
                            NormalizedFact(
                                entity_key=f"faa_nasr:{nav_id}:{nav_type}",
                                fact_type="station",
                                name=f"{row.get('NAME', nav_id)} {nav_type} ({nav_id})",
                                freq_mhz=freq,
                                mode="AM",
                                county=None,
                                lat=lat,
                                lon=lon,
                                location_precision="exact" if lat is not None else "unknown",
                                source_id=self.name,
                                source_url=zip_url,
                                source_updated=row.get("EFF_DATE"),
                                retrieved_at=raw.fetched_at,
                                raw=row,
                            )
                        )

        if "COM.csv" in inner_zip.namelist():
            com_rows = _read_csv_rows(inner_zip, "COM.csv")
            for row in com_rows:
                if row.get("STATE_CODE") != self.state:
                    continue
                try:
                    lat = float(row["LAT_DECIMAL"]) if row.get("LAT_DECIMAL") else None
                    lon = float(row["LONG_DECIMAL"]) if row.get("LONG_DECIMAL") else None
                except (ValueError, KeyError):
                    lat = lon = None
                facts.append(
                    NormalizedFact(
                        entity_key=f"faa_nasr:com:{row.get('COMM_LOC_ID', '')}",
                        fact_type="doc_ref",
                        name=f"{row.get('COMM_OUTLET_NAME', '')} {row.get('COMM_TYPE', '')}".strip(),
                        freq_mhz=None,
                        lat=lat,
                        lon=lon,
                        location_precision="exact" if lat is not None else "unknown",
                        source_id=self.name,
                        source_url=zip_url,
                        source_updated=row.get("EFF_DATE"),
                        retrieved_at=raw.fetched_at,
                        raw=row,
                    )
                )
        else:
            warnings.append("COM.csv not found in this cycle's CSV data; schema may have changed")

        return NormalizeResult(facts=facts, warnings=warnings)
