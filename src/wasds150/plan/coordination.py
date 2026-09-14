"""Repeater coordination records, for checking what a radio is programmed with.

WWARA's extract holds four lists: current, pending, about to expire and
expired. Plans are built from the current list (:mod:`wasds150.sources.wwara`);
the audit reads all four, because a new coordination sits in *pending* for
months - KC7BAE's Tiger Mountain machine on 443.050 in 2026 - and an expired
one says the machine may be gone. The extract is read from the local HTTP
cache that a source refresh fills; nothing is fetched here and nothing is
committed (WWARA reserves redistribution of the compiled file).
"""
from __future__ import annotations

import csv
import datetime
import io
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

STATUS_CURRENT = "current"
STATUS_PENDING = "pending"
STATUS_EXPIRING = "about to expire"
STATUS_EXPIRED = "expired"

#: File name prefix -> status. Later entries win when a record is in several
#: lists, and a lapsed expiry date beats all of them.
_LISTS = (
    ("WWARA-rptrlist-", STATUS_CURRENT),
    ("WWARA-About2Expire-", STATUS_EXPIRING),
    ("WWARA-pending-rptrlist-", STATUS_PENDING),
    ("WWARA-Expired-", STATUS_EXPIRED),
)
_DATE = re.compile(r"(\d{8})\.csv$", re.IGNORECASE)


@dataclass(frozen=True)
class Coordination:
    call: str
    city: str
    output_mhz: float
    input_mhz: Optional[float]
    #: The access tone the repeater's input needs (``CTCSS_IN``).
    ctcss_in: Optional[float]
    dcs: str
    #: ``DMR``, ``D-STAR``, ``P25``, ``NXDN``, ``Fusion`` or empty for analog.
    digital: str
    status: str
    expires: str

    @property
    def live(self) -> bool:
        return self.status != STATUS_EXPIRED


def _float(text: Optional[str]) -> Optional[float]:
    try:
        return float((text or "").strip())
    except ValueError:
        return None


def _expired(expires: str, today: datetime.date) -> bool:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(expires, fmt).date() < today
        except ValueError:
            continue
    return False


def _digital(row: Dict[str, str]) -> str:
    for label, field in (("DMR", "DMR"), ("D-STAR", "DSTAR_DV"), ("P25", "P25_PHASE_1"), ("P25", "P25_PHASE_2"),
                         ("NXDN", "NXDN_DIGITAL"), ("Fusion", "FUSION")):
        if (row.get(field) or "").strip().upper() == "Y":
            return label
    return ""


class CoordinationIndex:
    """Coordination records by output frequency."""

    def __init__(self, records: Iterable[Coordination], source_date: str = ""):
        self.records = list(records)
        self.source_date = source_date
        self._by_output: Dict[float, List[Coordination]] = defaultdict(list)
        for record in self.records:
            self._by_output[round(record.output_mhz, 4)].append(record)

    def __len__(self) -> int:
        return len(self.records)

    def on_output(self, freq_mhz: float) -> List[Coordination]:
        return list(self._by_output.get(round(freq_mhz, 4), ()))


def index_from_zip(data: bytes, today: Optional[datetime.date] = None) -> CoordinationIndex:
    today = today or datetime.date.today()
    chosen: Dict[tuple, Coordination] = {}
    source_date = ""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        for prefix, status in _LISTS:
            for name in names:
                if not name.startswith(prefix):
                    continue
                match = _DATE.search(name)
                if status == STATUS_CURRENT and match:
                    date = match.group(1)
                    source_date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
                lines = archive.read(name).decode("utf-8-sig", errors="replace").splitlines()
                body = lines[1:] if lines and lines[0].startswith("DATA_SPEC_VERSION") else lines
                for row in csv.DictReader(body):
                    output = _float(row.get("OUTPUT_FREQ"))
                    if output is None:
                        continue
                    call = (row.get("CALL") or "").strip().upper()
                    record_id = (row.get("FC_RECORD_ID") or "").strip()
                    key = ("id", record_id) if record_id else ("pair", call, round(output, 4), row.get("INPUT_FREQ"))
                    expires = (row.get("EXPIRATION_DATE") or "").strip()
                    chosen[key] = Coordination(
                        call=call,
                        city=(row.get("CITY") or "").strip(),
                        output_mhz=output,
                        input_mhz=_float(row.get("INPUT_FREQ")),
                        ctcss_in=_float(row.get("CTCSS_IN")),
                        dcs=(row.get("DCS_CDCSS") or "").strip(),
                        digital=_digital(row),
                        status=STATUS_EXPIRED if expires and _expired(expires, today) else status,
                        expires=expires,
                    )
    return CoordinationIndex(chosen.values(), source_date)


def fill_access_tones(resolved, index: Optional[CoordinationIndex]) -> int:
    """Give a transmitting analog amateur memory that has no access tone the
    tone WWARA publishes for its pair, when every live coordinated machine on
    the pair uses the same one. A source that simply left the tone out (a
    county database row, a club's channel plan) would otherwise key a toned
    repeater that never opens. Returns how many memories were filled."""
    if index is None:
        return 0
    from wasds150.radios.services import AMATEUR, service_for
    from wasds150.radios.tones import NO_TONE, parse_tone

    filled = 0
    for channel in resolved.channels:
        if not (
            channel.transmit and channel.tx_freq_mhz is not None
            and (channel.mode or "").upper() in ("FM", "NFM")
            and channel.tx_tone.kind == NO_TONE.kind
            and service_for(channel.rx_freq_mhz) == AMATEUR
        ):
            continue
        tones = {
            record.ctcss_in
            for record in index.on_output(channel.rx_freq_mhz)
            if record.live and record.ctcss_in is not None and record.input_mhz is not None
            and abs(record.input_mhz - channel.tx_freq_mhz) < 0.0005
        }
        if len(tones) == 1:
            tone = tones.pop()
            channel.tx_tone = parse_tone(f"TONE=C{tone:g}")
            resolved.warnings.append(f"{channel.label}: access tone {tone:g} Hz from WWARA's coordination (the source had none)")
            filled += 1
    return filled


def load_coordination(config) -> Optional[CoordinationIndex]:
    """The cached WWARA extract as an index, or ``None`` when no source
    refresh has cached it yet."""
    from wasds150.cache.store import HttpCacheStore
    from wasds150.sources.wwara import DATABASE_EXTRACT_URL

    cache_dir = config.cache_dir
    if not (cache_dir / "cache.db").is_file():
        return None
    store = HttpCacheStore(cache_dir)
    try:
        entry = store.get(DATABASE_EXTRACT_URL)
        if entry is None:
            return None
        return index_from_zip(store.read_blob(entry))
    finally:
        store.close()
