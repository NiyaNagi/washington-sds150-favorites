"""radioid.net - the worldwide DMR and NXDN ID registry.

radioid.net publishes its whole database as CSV (``/static/user.csv`` for
DMR, about 17 MB, and ``/static/nxdn.csv`` for NXDN), both with the header
``RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY``. Columns are
read by name, so an added column does not break parsing; a file without
``RADIO_ID`` and ``CALLSIGN`` is rejected outright.

The source is ``kind="contacts"``: it produces no catalog facts, so the
catalog update pipelines never run it. The fleet update's contact step does
(:mod:`wasds150.contacts.refresh`), and ``wasds150 sources fetch radioid``
fetches it on demand.
"""
from __future__ import annotations

import csv
import datetime
import io
from typing import Any, List, Optional, Sequence

from wasds150.contacts.model import PROTOCOL_DMR, PROTOCOL_NXDN, PROTOCOLS, Contact, ContactTable, clean_ascii
from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizeResult
from wasds150.util.hashing import sha256_of_bytes

URLS = {
    PROTOCOL_DMR: "https://radioid.net/static/user.csv",
    PROTOCOL_NXDN: "https://radioid.net/static/nxdn.csv",
}
#: The registry changes daily, but a month-old directory is still useful.
DEFAULT_TTL_SECONDS = 30 * 24 * 3600
MAX_BYTES = 64 * 1024 * 1024
_REQUIRED = ("RADIO_ID", "CALLSIGN")
#: DMR IDs are 24-bit; NXDN unit IDs are 16-bit.
_ID_MAX = {PROTOCOL_DMR: 16_777_215, PROTOCOL_NXDN: 65_535}


def parse_contacts(text: str, protocol: str, *, source_url: str = "", retrieved_at: str = "") -> ContactTable:
    protocol = protocol.upper()
    if protocol not in PROTOCOLS:
        raise ValueError(f"unknown contact protocol {protocol!r}")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        raise ValueError(f"the {protocol} contact list is empty")
    index = {name.strip().upper(): position for position, name in enumerate(header)}
    missing = [column for column in _REQUIRED if column not in index]
    if missing:
        raise ValueError(f"the {protocol} contact list has no {', '.join(missing)} column")

    def cell(row: List[str], column: str) -> str:
        position = index.get(column)
        return clean_ascii(row[position]) if position is not None and position < len(row) else ""

    seen = set()
    rows: List[Contact] = []
    for row in reader:
        try:
            radio_id = int(row[index["RADIO_ID"]].strip())
        except (ValueError, IndexError):
            continue
        if not 0 < radio_id <= _ID_MAX[protocol] or radio_id in seen:
            continue
        seen.add(radio_id)
        rows.append(
            Contact(
                radio_id=radio_id,
                callsign=cell(row, "CALLSIGN").upper(),
                first_name=cell(row, "FIRST_NAME"),
                last_name=cell(row, "LAST_NAME"),
                city=cell(row, "CITY"),
                state=cell(row, "STATE"),
                country=cell(row, "COUNTRY"),
                protocol=protocol,
            )
        )
    return ContactTable(
        protocol=protocol,
        retrieved_at=retrieved_at,
        source_url=source_url,
        sha256=sha256_of_bytes(text.encode("utf-8")),
        rows=rows,
    )


class RadioIdSource(OnlineSourceAdapter):
    name = "radioid"
    available = True
    kind = "contacts"
    #: ~17 MB for DMR alone: fetched only when asked for.
    bulk = True

    def __init__(self, protocols: Sequence[str] = PROTOCOLS, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.protocols = tuple(p.upper() for p in protocols)
        for protocol in self.protocols:
            if protocol not in URLS:
                raise ValueError(f"unknown contact protocol {protocol!r}; choices: {list(URLS)}")
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        payload = {}
        for protocol in self.protocols:
            result = http_client.fetch(
                URLS[protocol], ttl_seconds=self.ttl_seconds, source_id=self.name, max_bytes=MAX_BYTES
            )
            payload[protocol] = {"url": URLS[protocol], "text": result.content.decode("utf-8-sig", errors="replace")}
        return RawDoc(
            source_adapter=self.name,
            payload=payload,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def tables(self, raw: RawDoc) -> List[ContactTable]:
        return [
            parse_contacts(entry["text"], protocol, source_url=entry["url"], retrieved_at=raw.fetched_at)
            for protocol, entry in raw.payload.items()
        ]

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        return NormalizeResult(
            facts=[],
            warnings=[
                f"{table.protocol}: {len(table.rows):,} contacts (kept in the contact store, not the catalog)"
                for table in self.tables(raw)
            ],
        )
