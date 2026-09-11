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

**``LO.dat``, ``FR.dat`` and ``EM.dat`` have not been byte-verified** against
a land-mobile extract in this project (``l_LMpriv.zip`` is 420 MB; GMRS, the
service verified above, carries no location, frequency or emission
records). The FCC's public-access field definitions put ``FR``'s
``frequency_assigned`` at index 10, ``EM``'s ``emission_code`` at index 9
and ``LO``'s state at index 14, while earlier versions of this module read
``FR[8]`` and ``LO[13]``. Rather than trust either, each column is
*detected*: the documented position is tried first and a candidate is used
only when at least 90% of its values validate (a frequency parses, an
emission designator matches its ITU shape, a state is two letters). Falling
back to a non-documented position, or finding nothing valid, produces a
warning, so the first real extract says which layout it has. The real
``l_LMpriv.zip`` of 2026-09-10 matched the documented positions with no
warning: 109,713 frequency facts, 32,156 of them within 60 miles of home.

**Emission designators** (``EM.dat``) say what a licensee transmits:
``7K60FXE`` is DMR, ``4K00F1E``/``8K30F1E`` NXDN, ``8K10F1E`` P25,
``11K2F3E`` narrowband FM. :func:`mode_from_emission` maps them to the
catalog's modes, every frequency fact carries ``raw["emissions"]``, and
``emissions=`` keeps only frequencies licensed for the given designators or
modes (the input to the ``FCCDIG`` list, :mod:`wasds150.recipes.fcc_digital`).

``active_only`` drops licences whose status is not Active or whose expiry
date has passed; ``home``/``within_miles`` keep only licence locations near
home.

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
import re
import zipfile
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult
from wasds150.util.geo import haversine_miles

BASE_URL = "https://data.fcc.gov/download/pub/uls/complete"

#: service short-name -> zip filename (all confirmed live).
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

# FR / EM / LO: detected (see module docstring). Documented position first.
_FR_UNIQUE_SYSTEM_ID = 1
_FR_FREQ_CANDIDATES = (10, 8)
_EM_UNIQUE_SYSTEM_ID = 1
_EM_FREQ_CANDIDATES = (7, 8)
_EM_CODE_CANDIDATES = (9, 10, 8)
_LO_UNIQUE_SYSTEM_ID = 1
_LO_LAYOUTS: Tuple[Tuple[str, Dict[str, Any]], ...] = (
    ("documented", {"city": 12, "county": 13, "state": 14, "lat": (19, 20, 21, 22), "lon": (23, 24, 25, 26)}),
    ("legacy", {"city": 11, "county": 12, "state": 13, "lat": (18, 19, 20, 21), "lon": (22, 23, 24, 25)}),
)
#: Share of sampled values that must validate for a column to be used.
_VALID_SHARE = 0.9

#: ITU emission designator: four bandwidth characters (digits with one of
#: H/K/M/G as the decimal point) and three class characters.
_EMISSION_RE = re.compile(r"^(?=[0-9A-Z]{7}$)[0-9]{1,3}[HKMG][0-9]{0,3}[A-Z0-9]{3}$")

_EMISSION_MODES = {
    "7K60FXE": "DMR", "7K60FXD": "DMR",
    "4K00F1E": "NXDN", "4K00F1D": "NXDN", "4K00F7W": "NXDN",
    "8K30F1E": "NXDN", "8K30F1D": "NXDN", "8K30F7W": "NXDN",
    "8K10F1E": "P25", "8K10F1D": "P25", "8K10F1W": "P25",
    "11K0F3E": "NFM", "11K2F3E": "NFM",
    "16K0F3E": "FM", "20K0F3E": "FM",
}
#: When one frequency is licensed for several emissions, the most specific wins.
_MODE_PRIORITY = ("DMR", "NXDN", "P25", "NFM", "FM")


def _bandwidth_khz(code: str) -> Optional[float]:
    part = code[:4]
    for letter, scale in (("H", 0.001), ("K", 1.0), ("M", 1000.0), ("G", 1_000_000.0)):
        if letter in part:
            whole, _, fraction = part.partition(letter)
            try:
                return float(f"{whole}.{fraction or '0'}") * scale
            except ValueError:
                return None
    return None


def mode_from_emission(code: str) -> Optional[str]:
    """Catalog mode for an emission designator, or ``None`` when it says
    nothing a radio plan can use (data, telemetry, unknown)."""
    code = (code or "").strip().upper()
    if code in _EMISSION_MODES:
        return _EMISSION_MODES[code]
    if len(code) == 7 and code.endswith("F3E"):
        bandwidth = _bandwidth_khz(code)
        if bandwidth is not None:
            return "NFM" if bandwidth <= 12.5 else "FM"
    return None


def is_emission_designator(value: str) -> bool:
    return bool(_EMISSION_RE.match((value or "").strip().upper()))


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


def _is_frequency(value: str) -> bool:
    try:
        return 0.01 <= float(value) <= 300000.0
    except ValueError:
        return False


def _pick_column(
    rows: List[List[str]], candidates: Sequence[int], valid: Callable[[str], bool], label: str, warnings: List[str]
) -> Optional[int]:
    sample = rows[:500]
    for position, index in enumerate(candidates):
        values = [row[index] for row in sample if len(row) > index and row[index].strip()]
        if values and sum(1 for v in values if valid(v)) / len(values) >= _VALID_SHARE:
            if position:
                warnings.append(
                    f"{label}: the documented column {candidates[0]} did not hold valid values; "
                    f"read column {index} instead"
                )
            return index
    if rows:
        warnings.append(f"{label}: no candidate column {list(candidates)} held valid values; skipped")
    return None


def _lo_row_valid(row: List[str], layout: Dict[str, Any]) -> Optional[bool]:
    state_index = layout["state"]
    if len(row) <= state_index or not row[state_index].strip():
        return None
    state = row[state_index].strip()
    if not (len(state) == 2 and state.isalpha()):
        return False
    degrees = row[layout["lat"][0]].strip() if len(row) > layout["lat"][0] else ""
    if not degrees:
        return True
    try:
        return 0 <= float(degrees) <= 90
    except ValueError:
        return False


def _pick_lo_layout(rows: List[List[str]], warnings: List[str]) -> Optional[Dict[str, Any]]:
    for position, (name, layout) in enumerate(_LO_LAYOUTS):
        verdicts = [v for v in (_lo_row_valid(row, layout) for row in rows[:500]) if v is not None]
        if verdicts and sum(verdicts) / len(verdicts) >= _VALID_SHARE:
            if position:
                warnings.append(f"LO.dat: the documented layout did not validate; read the {name} layout instead")
            return layout
    if rows:
        warnings.append("LO.dat: no known column layout validated; licence locations skipped")
    return None


def _licence_active(hd: List[str], today: datetime.date) -> bool:
    status = hd[_HD_LICENSE_STATUS].strip().upper() if len(hd) > _HD_LICENSE_STATUS else ""
    if status and status != "A":
        return False
    expired = hd[_HD_EXPIRED_DATE].strip() if len(hd) > _HD_EXPIRED_DATE else ""
    try:
        return datetime.datetime.strptime(expired, "%m/%d/%Y").date() >= today
    except ValueError:
        return True


class FccUlsSource(OnlineSourceAdapter):
    name = "fcc_uls"
    available = True
    kind = "facts"
    #: Land Mobile Private alone is ~420 MB: refreshed only when asked for.
    bulk = True

    def __init__(
        self,
        service: str = "lmpriv",
        state: str = "WA",
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        *,
        services: Optional[Sequence[str]] = None,
        emissions: Sequence[str] = (),
        home: Optional[Tuple[float, float]] = None,
        within_miles: Optional[float] = None,
        active_only: bool = True,
        today: Optional[datetime.date] = None,
    ):
        self.services = tuple(services or (service,))
        for name in self.services:
            if name not in SERVICE_ZIPS:
                raise ValueError(f"unknown FCC ULS service {name!r}; choices: {sorted(SERVICE_ZIPS)}")
        if within_miles is not None and home is None:
            raise ValueError("within_miles needs a home point")
        self.service = self.services[0]
        self.state = state
        self.ttl_seconds = ttl_seconds
        self.url = f"{BASE_URL}/{SERVICE_ZIPS[self.service]}"
        wanted = [e.strip().upper() for e in emissions if e and e.strip()]
        self.emission_codes: Set[str] = {e for e in wanted if is_emission_designator(e)}
        self.emission_modes: Set[str] = {e for e in wanted if not is_emission_designator(e)}
        self.home = home
        self.within_miles = within_miles
        self.active_only = active_only
        self.today = today

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        zips = {}
        for service in self.services:
            result = http_client.fetch(
                f"{BASE_URL}/{SERVICE_ZIPS[service]}", ttl_seconds=self.ttl_seconds, source_id=self.name,
                max_bytes=500 * 1024 * 1024,
            )
            zips[service] = result.content
        return RawDoc(
            source_adapter=self.name,
            payload={"zips": zips},
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def _emission_wanted(self, codes: Iterable[str]) -> bool:
        if not (self.emission_codes or self.emission_modes):
            return True
        for code in codes:
            if code in self.emission_codes or mode_from_emission(code) in self.emission_modes:
                return True
        return False

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        zips = raw.payload["zips"] if isinstance(raw.payload, dict) else {self.service: raw.payload}
        result = NormalizeResult()
        for service, data in zips.items():
            facts, warnings = self._normalize_zip(service, data, raw.fetched_at)
            result.facts.extend(facts)
            result.warnings.extend(f"{SERVICE_ZIPS.get(service, service)}: {w}" for w in warnings)
        return result

    def _normalize_zip(self, service: str, data: bytes, fetched_at: str) -> Tuple[List[NormalizedFact], List[str]]:
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = set(zf.namelist())
        warnings: List[str] = []
        source_url = f"{BASE_URL}/{SERVICE_ZIPS.get(service, '')}"

        def read_table(fname: str) -> List[List[str]]:
            if fname not in names:
                return []
            with zf.open(fname) as f:
                return _split_pipe_dat(f.read().decode("latin-1"))

        hd_rows = read_table("HD.dat")
        if not hd_rows:
            return [], ["HD.dat not found or empty; no license facts produced"]
        en_rows, lo_rows, fr_rows, em_rows = (read_table(n) for n in ("EN.dat", "LO.dat", "FR.dat", "EM.dat"))

        en_by_id = {row[_EN_UNIQUE_SYSTEM_ID]: row for row in en_rows if len(row) > _EN_UNIQUE_SYSTEM_ID}

        lo_layout = _pick_lo_layout(lo_rows, warnings) if lo_rows else None
        lo_by_id: Dict[str, List[List[str]]] = {}
        for row in lo_rows:
            if len(row) > _LO_UNIQUE_SYSTEM_ID:
                lo_by_id.setdefault(row[_LO_UNIQUE_SYSTEM_ID], []).append(row)

        fr_freq = _pick_column(fr_rows, _FR_FREQ_CANDIDATES, _is_frequency, "FR.dat frequency", warnings) if fr_rows else None
        fr_by_id: Dict[str, List[float]] = {}
        if fr_freq is not None:
            for row in fr_rows:
                if len(row) > fr_freq and len(row) > _FR_UNIQUE_SYSTEM_ID and _is_frequency(row[fr_freq]):
                    fr_by_id.setdefault(row[_FR_UNIQUE_SYSTEM_ID], []).append(float(row[fr_freq]))

        em_code = (
            _pick_column(em_rows, _EM_CODE_CANDIDATES, is_emission_designator, "EM.dat emission", warnings)
            if em_rows else None
        )
        em_freq = _pick_column(em_rows, _EM_FREQ_CANDIDATES, _is_frequency, "EM.dat frequency", []) if em_rows else None
        emissions_by_freq: Dict[Tuple[str, float], Set[str]] = {}
        emissions_by_id: Dict[str, Set[str]] = {}
        if em_code is not None:
            for row in em_rows:
                if len(row) <= em_code or not is_emission_designator(row[em_code]):
                    continue
                code = row[em_code].strip().upper()
                usi = row[_EM_UNIQUE_SYSTEM_ID]
                emissions_by_id.setdefault(usi, set()).add(code)
                if em_freq is not None and len(row) > em_freq and _is_frequency(row[em_freq]):
                    emissions_by_freq.setdefault((usi, round(float(row[em_freq]), 5)), set()).add(code)
        elif (self.emission_codes or self.emission_modes) and em_rows == []:
            warnings.append("EM.dat not found; the emission filter keeps nothing")

        today = self.today or datetime.date.today()
        filtering = bool(self.emission_codes or self.emission_modes or self.within_miles)
        facts: List[NormalizedFact] = []
        for hd in hd_rows:
            if len(hd) <= _HD_RADIO_SERVICE_CODE:
                continue
            if self.active_only and not _licence_active(hd, today):
                continue
            unique_id = hd[_HD_UNIQUE_SYSTEM_ID]
            call_sign = hd[_HD_CALL_SIGN] if len(hd) > _HD_CALL_SIGN else ""
            radio_service_code = hd[_HD_RADIO_SERVICE_CODE]
            license_status = hd[_HD_LICENSE_STATUS] if len(hd) > _HD_LICENSE_STATUS else ""

            en = en_by_id.get(unique_id)
            entity_name = en[_EN_ENTITY_NAME] if en and len(en) > _EN_ENTITY_NAME else ""
            en_state = en[_EN_STATE] if en and len(en) > _EN_STATE else ""

            lo_list = lo_by_id.get(unique_id, [])
            lo_states = [
                lo[lo_layout["state"]] for lo in lo_list if lo_layout and len(lo) > lo_layout["state"]
            ]
            if not (en_state == self.state or self.state in lo_states):
                continue

            county = None
            lat = lon = None
            if lo_list and lo_layout:
                lo = lo_list[0]
                if len(lo) > lo_layout["county"]:
                    county = lo[lo_layout["county"]] or None
                if len(lo) > lo_layout["lon"][3]:
                    lat = _dms_to_decimal(*(lo[i] for i in lo_layout["lat"]))
                    lon = _dms_to_decimal(*(lo[i] for i in lo_layout["lon"]))
            if self.within_miles is not None:
                if lat is None or lon is None:
                    continue
                if haversine_miles(self.home[0], self.home[1], lat, lon) > self.within_miles:
                    continue

            entity_key = f"fcc:{radio_service_code}:{unique_id}"
            name = entity_name or call_sign or unique_id
            base_raw = {"call_sign": call_sign, "license_status": license_status, "radio_service_code": radio_service_code}
            freqs = fr_by_id.get(unique_id, [])
            if not freqs:
                if not filtering:
                    facts.append(
                        NormalizedFact(
                            entity_key=entity_key, fact_type="system", name=name, county=county, lat=lat, lon=lon,
                            location_precision="exact" if lat is not None else "unknown", source_id=self.name,
                            source_url=source_url, retrieved_at=fetched_at, raw=dict(base_raw),
                        )
                    )
                continue
            for freq in freqs:
                codes = emissions_by_freq.get((unique_id, round(freq, 5))) or emissions_by_id.get(unique_id, set())
                if not self._emission_wanted(codes):
                    continue
                modes = {mode_from_emission(code) for code in codes} - {None}
                mode = next((m for m in _MODE_PRIORITY if m in modes), None)
                facts.append(
                    NormalizedFact(
                        entity_key=f"{entity_key}:{freq}",
                        fact_type="frequency",
                        name=f"{name} ({call_sign})" if call_sign else name,
                        freq_mhz=freq,
                        mode=mode,
                        county=county,
                        lat=lat,
                        lon=lon,
                        location_precision="exact" if lat is not None else "unknown",
                        source_id=self.name,
                        source_url=source_url,
                        retrieved_at=fetched_at,
                        raw={**base_raw, "emissions": sorted(codes)},
                    )
                )
        return facts, warnings
