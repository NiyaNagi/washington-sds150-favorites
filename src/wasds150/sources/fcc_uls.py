"""FCC ULS (Universal Licensing System) bulk weekly data — Washington
land-mobile/GMRS/amateur licensing facts.

**Confirmed live** (fetched directly during implementation):
``https://data.fcc.gov/download/pub/uls/complete/l_LMpriv.zip`` (Land
Mobile Private — county/state/DNR/WSDOT/USFS-cooperator public-safety and
business licenses), ``l_LMcomm.zip`` (Land Mobile Commercial/SMR),
``l_amat.zip`` (Amateur), ``l_gmrs.zip`` (GMRS). ``l_pw.zip`` does **not**
exist — Public Safety Pool licenses live inside ``l_LMpriv.zip``, filtered
by radio service code, not a separate file.

**``HD.dat``/``EN.dat`` column layout below is directly byte-verified**
against a real downloaded ``l_gmrs.zip`` during implementation (pipe-
delimited, no header row): ``HD`` row confirmed
``HD|<unique_system_identifier>|<uls_file_num>||<call_sign>|<license_status>|
<radio_service_code>|<grant_date>|<expired_date>|<cancellation_date>|...``;
``EN`` row confirmed
``EN|<unique_system_identifier>|||<call_sign>|<entity_type>|<licensee_id>|
<entity_name>|<first_name>|<mi>|<last_name>|<suffix>||||<street_address>|
<city>|<state>|<zip_code>|...``.

**``LO.dat``/``FR.dat`` column layout below is per FCC's publicly
documented, unified ULS schema (stable across services and used
identically by numerous independent open-source ULS parsers) — it was
*not* independently byte-verified against a live extract in this project
(``l_LMpriv.zip`` is 420 MB; GMRS, the service byte-verified above, carries
no location/frequency records to check against). Treat the ``LO``/``FR``
column positions as documented-but-unverified and re-confirm against a
real ``l_LMpriv.zip``/``l_LMcomm.zip`` row before trusting frequency/site
facts in production.**

The ``counts`` file (a plain-text row-count manifest bundled in every zip)
is a cheap "did anything change" signal, since ``data.fcc.gov`` bulk files
don't always make conditional-GET worthwhile on their own — the shared
cache's own TTL already avoids re-parsing unchanged content within the
configured window regardless.

**Entity key**: ``fcc:{radio_service_code}:{unique_system_identifier}`` —
stable across weekly refreshes; call signs can be reassigned/renewed, so
never keyed alone.

Public domain (US federal work) — fully ingestible/redistributable, no
attribution legally required (though citing "FCC ULS" is good practice).
"""
from __future__ import annotations

import datetime
import io
import zipfile
from typing import Any, Dict, List, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

BASE_URL = "https://data.fcc.gov/download/pub/uls/complete"

#: service short-name -> (zip filename, confirmed-live)
SERVICE_ZIPS = {
    "lmpriv": "l_LMpriv.zip",
    "lmcomm": "l_LMcomm.zip",
    "amat": "l_amat.zip",
    "gmrs": "l_gmrs.zip",
}
#: Weekly refresh; no need to check more than once a week.
DEFAULT_TTL_SECONDS = 7 * 24 * 3600

# HD.dat / EN.dat: byte-verified (see module docstring).
_HD_UNIQUE_SYSTEM_ID = 1
_HD_CALL_SIGN = 4
_HD_LICENSE_STATUS = 5
_HD_RADIO_SERVICE_CODE = 6
_HD_GRANT_DATE = 7
_HD_EXPIRED_DATE = 8
_HD_CANCELLATION_DATE = 9

_EN_UNIQUE_SYSTEM_ID = 1
_EN_CALL_SIGN = 4
_EN_ENTITY_NAME = 7
_EN_STREET_ADDRESS = 15
_EN_CITY = 16
_EN_STATE = 17

# LO.dat / FR.dat: documented, NOT independently byte-verified this session
# (see module docstring) -- re-confirm before trusting in production.
_LO_UNIQUE_SYSTEM_ID = 1
_LO_CITY = 11
_LO_COUNTY = 12
_LO_STATE = 13
_LO_LAT_DEG, _LO_LAT_MIN, _LO_LAT_SEC, _LO_LAT_DIR = 18, 19, 20, 21
_LO_LONG_DEG, _LO_LONG_MIN, _LO_LONG_SEC, _LO_LONG_DIR = 22, 23, 24, 25

_FR_UNIQUE_SYSTEM_ID = 1
_FR_FREQUENCY_ASSIGNED = 8  # documented units: decimal MHz (e.g. "154.130000")


def _split_pipe_dat(text: str) -> List[List[str]]:
    return [line.split("|") for line in text.splitlines() if line]


def _dms_to_decimal(deg: str, minutes: str, seconds: str, direction: str) -> Optional[float]:
    try:
        value = float(deg) + float(minutes) / 60 + float(seconds) / 3600
    except ValueError:
        return None
    if direction and direction.upper() in ("S", "W"):
        value = -value
    return value


class FccUlsSource(OnlineSourceAdapter):
    name = "fcc_uls"
    available = True
    kind = "facts"

    def __init__(self, service: str = "lmpriv", state: str = "WA", ttl_seconds: int = DEFAULT_TTL_SECONDS):
        if service not in SERVICE_ZIPS:
            raise ValueError(f"unknown FCC ULS service {service!r}; choices: {sorted(SERVICE_ZIPS)}")
        self.service = service
        self.state = state
        self.ttl_seconds = ttl_seconds
        self.url = f"{BASE_URL}/{SERVICE_ZIPS[service]}"

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        result = http_client.fetch(
            self.url, ttl_seconds=self.ttl_seconds, source_id=self.name, max_bytes=500 * 1024 * 1024
        )
        return RawDoc(
            source_adapter=self.name,
            payload=result.content,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        zf = zipfile.ZipFile(io.BytesIO(raw.payload))
        names = set(zf.namelist())
        warnings: List[str] = []

        def read_table(fname: str) -> List[List[str]]:
            if fname not in names:
                return []
            with zf.open(fname) as f:
                return _split_pipe_dat(f.read().decode("latin-1"))

        hd_rows = read_table("HD.dat")
        en_rows = read_table("EN.dat")
        lo_rows = read_table("LO.dat")
        fr_rows = read_table("FR.dat")

        if not hd_rows:
            warnings.append("HD.dat not found or empty; no license facts produced")
            return NormalizeResult(facts=[], warnings=warnings)

        # Index EN/LO/FR by unique_system_identifier for an in-memory join
        # (stdlib dict; small enough at WA scale without needing sqlite).
        en_by_id: Dict[str, List[str]] = {}
        for row in en_rows:
            if len(row) > _EN_UNIQUE_SYSTEM_ID:
                en_by_id[row[_EN_UNIQUE_SYSTEM_ID]] = row

        lo_by_id: Dict[str, List[List[str]]] = {}
        for row in lo_rows:
            if len(row) > _LO_UNIQUE_SYSTEM_ID:
                lo_by_id.setdefault(row[_LO_UNIQUE_SYSTEM_ID], []).append(row)

        fr_by_id: Dict[str, List[List[str]]] = {}
        for row in fr_rows:
            if len(row) > _FR_UNIQUE_SYSTEM_ID:
                fr_by_id.setdefault(row[_FR_UNIQUE_SYSTEM_ID], []).append(row)

        facts: List[NormalizedFact] = []
        for hd in hd_rows:
            if len(hd) <= _HD_RADIO_SERVICE_CODE:
                continue
            unique_id = hd[_HD_UNIQUE_SYSTEM_ID]
            call_sign = hd[_HD_CALL_SIGN] if len(hd) > _HD_CALL_SIGN else ""
            radio_service_code = hd[_HD_RADIO_SERVICE_CODE]
            license_status = hd[_HD_LICENSE_STATUS] if len(hd) > _HD_LICENSE_STATUS else ""

            en = en_by_id.get(unique_id)
            entity_name = en[_EN_ENTITY_NAME] if en and len(en) > _EN_ENTITY_NAME else ""
            en_state = en[_EN_STATE] if en and len(en) > _EN_STATE else ""

            lo_list = lo_by_id.get(unique_id, [])
            matched_wa = en_state == self.state or any(
                len(lo) > _LO_STATE and lo[_LO_STATE] == self.state for lo in lo_list
            )
            if not matched_wa:
                continue

            county = None
            lat = lon = None
            if lo_list:
                lo = lo_list[0]
                if len(lo) > _LO_COUNTY:
                    county = lo[_LO_COUNTY] or None
                if len(lo) > _LO_LONG_DIR:
                    lat = _dms_to_decimal(lo[_LO_LAT_DEG], lo[_LO_LAT_MIN], lo[_LO_LAT_SEC], lo[_LO_LAT_DIR])
                    lon = _dms_to_decimal(lo[_LO_LONG_DEG], lo[_LO_LONG_MIN], lo[_LO_LONG_SEC], lo[_LO_LONG_DIR])

            fr_list = fr_by_id.get(unique_id, [])
            freqs: List[float] = []
            for fr in fr_list:
                if len(fr) > _FR_FREQUENCY_ASSIGNED and fr[_FR_FREQUENCY_ASSIGNED]:
                    try:
                        freqs.append(float(fr[_FR_FREQUENCY_ASSIGNED]))  # already decimal MHz
                    except ValueError:
                        pass

            entity_key = f"fcc:{radio_service_code}:{unique_id}"
            name = entity_name or call_sign or unique_id
            if not freqs:
                facts.append(
                    NormalizedFact(
                        entity_key=entity_key,
                        fact_type="system",
                        name=name,
                        county=county,
                        lat=lat,
                        lon=lon,
                        location_precision="exact" if lat is not None else "unknown",
                        source_id=self.name,
                        source_url=f"https://data.fcc.gov/download/pub/uls/complete/{SERVICE_ZIPS[self.service]}",
                        retrieved_at=raw.fetched_at,
                        raw={"call_sign": call_sign, "license_status": license_status, "radio_service_code": radio_service_code},
                    )
                )
            for freq in freqs:
                facts.append(
                    NormalizedFact(
                        entity_key=f"{entity_key}:{freq}",
                        fact_type="frequency",
                        name=f"{name} ({call_sign})" if call_sign else name,
                        freq_mhz=freq,
                        county=county,
                        lat=lat,
                        lon=lon,
                        location_precision="exact" if lat is not None else "unknown",
                        source_id=self.name,
                        source_url=f"https://data.fcc.gov/download/pub/uls/complete/{SERVICE_ZIPS[self.service]}",
                        retrieved_at=raw.fetched_at,
                        raw={"call_sign": call_sign, "license_status": license_status, "radio_service_code": radio_service_code},
                    )
                )

        return NormalizeResult(facts=facts, warnings=warnings)
