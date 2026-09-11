"""Contact tables and the local store they live in.

A contact directory is not catalog content: it says who a DMR or NXDN
station is (ID, call sign, name, place), not what to tune. It is downloaded
whole, kept under ``state/contacts/`` and written into a radio's codeplug
by the exporters of radios that keep one (see
:class:`~wasds150.radios.profile.ContactCapability`).

The Anytone CPS stores plain ASCII and uses ``|``, ``,`` and ``"`` as
separators, so every text field is folded to ASCII (accents dropped by
Unicode NFKD decomposition, anything else non-ASCII removed) and stripped of
those characters on the way in.
"""
from __future__ import annotations

import csv
import io
import json
import os
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

PROTOCOL_DMR = "DMR"
PROTOCOL_NXDN = "NXDN"
PROTOCOLS = (PROTOCOL_DMR, PROTOCOL_NXDN)

STORE_COLUMNS = ("RADIO_ID", "CALLSIGN", "FIRST_NAME", "LAST_NAME", "CITY", "STATE", "COUNTRY")
_SEPARATORS = str.maketrans("", "", '|,"')


def clean_ascii(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(folded.translate(_SEPARATORS).split())


@dataclass(frozen=True)
class Contact:
    radio_id: int
    callsign: str
    first_name: str = ""
    last_name: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    protocol: str = PROTOCOL_DMR

    @property
    def name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part)


@dataclass
class ContactTable:
    protocol: str
    retrieved_at: str = ""
    source_url: str = ""
    sha256: str = ""
    rows: List[Contact] = field(default_factory=list)

    def meta(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol,
            "retrieved_at": self.retrieved_at,
            "source_url": self.source_url,
            "sha256": self.sha256,
            "rows": len(self.rows),
        }


class ContactStore:
    FILES = {PROTOCOL_DMR: "dmr-contacts.csv", PROTOCOL_NXDN: "nxdn-contacts.csv"}

    def __init__(self, contacts_dir: Path):
        self.directory = Path(contacts_dir)

    @property
    def _meta_path(self) -> Path:
        return self.directory / "meta.json"

    def meta(self) -> Dict[str, Dict[str, Any]]:
        if not self._meta_path.exists():
            return {}
        return json.loads(self._meta_path.read_text(encoding="utf-8"))

    def save(self, table: ContactTable) -> Path:
        protocol = table.protocol.upper()
        if protocol not in self.FILES:
            raise ValueError(f"unknown contact protocol {table.protocol!r}")
        self.directory.mkdir(parents=True, exist_ok=True)
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(STORE_COLUMNS)
        for c in table.rows:
            writer.writerow([c.radio_id, c.callsign, c.first_name, c.last_name, c.city, c.state, c.country])
        path = self.directory / self.FILES[protocol]
        tmp = path.with_suffix(".csv.tmp")
        tmp.write_text(buffer.getvalue(), encoding="ascii", errors="replace")
        os.replace(tmp, path)
        meta = self.meta()
        meta[protocol] = table.meta()
        tmp_meta = self._meta_path.with_suffix(".json.tmp")
        tmp_meta.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_meta, self._meta_path)
        return path

    def load(self, protocol: str) -> Optional[ContactTable]:
        protocol = protocol.upper()
        path = self.directory / self.FILES.get(protocol, "missing")
        if not path.exists():
            return None
        info = self.meta().get(protocol, {})
        rows = []
        for record in csv.DictReader(io.StringIO(path.read_text(encoding="ascii", errors="replace"))):
            rows.append(
                Contact(
                    radio_id=int(record["RADIO_ID"]),
                    callsign=record.get("CALLSIGN", ""),
                    first_name=record.get("FIRST_NAME", ""),
                    last_name=record.get("LAST_NAME", ""),
                    city=record.get("CITY", ""),
                    state=record.get("STATE", ""),
                    country=record.get("COUNTRY", ""),
                    protocol=protocol,
                )
            )
        return ContactTable(
            protocol=protocol,
            retrieved_at=info.get("retrieved_at", ""),
            source_url=info.get("source_url", ""),
            sha256=info.get("sha256", ""),
            rows=rows,
        )
