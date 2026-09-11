"""Digital contact list CSVs for the Anytone CPS.

**Unverified format.** The header below is the one the Anytone D878UV-family
CPS uses for its digital contact list; the D890UV CPS's own Export All has
not been captured yet, so neither the header nor the file names are
confirmed for this radio. Until they are (flip
:data:`CONTACT_FORMAT_VERIFIED` and record the capture in
``docs/at-d890uv-programming.md``), the files are written next to the bundle
but left out of the ``.LST`` manifest: the operator imports them on their
own and checks a few rows first. Columns are filled by header name, so a
captured header in a different order renders correctly once pasted in.

Every contact is a ``Private Call``: a directory of individual operators is
private calls by definition (talkgroups live with the channels). A list
longer than the radio's ceiling is split into numbered files, never
truncated.
"""
from __future__ import annotations

import csv
import io
from typing import Dict, Iterable, List, Sequence, Tuple

from wasds150.contacts.model import Contact, ContactTable
from wasds150.radios.profile import ContactCapability

CONTACT_HEADER: Tuple[str, ...] = (
    "No.", "Radio ID", "Callsign", "Name", "City", "State", "Country", "Remarks", "Call Type", "Call Alert",
)
CONTACT_FORMAT_VERIFIED = False
CONTACT_FILES = {"DMR": "DigitalContactList.CSV", "NXDN": "NXDNContactList.CSV"}


def render_contact_csv(
    rows: Sequence[Contact], *, header: Sequence[str] = CONTACT_HEADER, call_type: str = "Private Call"
) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(header)
    for number, contact in enumerate(rows, start=1):
        values = {
            "No.": str(number),
            "Radio ID": str(contact.radio_id),
            "Callsign": contact.callsign,
            "Name": contact.name,
            "City": contact.city,
            "State": contact.state,
            "Country": contact.country,
            "Remarks": "",
            "Call Type": call_type,
            "Call Alert": "None",
        }
        writer.writerow([values.get(column, "") for column in header])
    return buffer.getvalue()


def _numbered(base: str, number: int) -> str:
    return base if number == 1 else base.replace(".CSV", f"_{number}.CSV")


def contact_files(
    tables: Iterable[ContactTable], capability: ContactCapability
) -> Tuple[Dict[str, str], List[str]]:
    files: Dict[str, str] = {}
    warnings: List[str] = []
    limit = capability.max_contacts
    for table in tables:
        if not capability.supports(table.protocol) or table.protocol not in CONTACT_FILES:
            continue
        chunks = [table.rows[i:i + limit] for i in range(0, len(table.rows), limit)]
        if len(chunks) > 1:
            warnings.append(
                f"{table.protocol}: {len(table.rows):,} contacts exceed the radio's {limit:,}; "
                f"split into {len(chunks)} files - import one"
            )
        for number, chunk in enumerate(chunks, start=1):
            files[_numbered(CONTACT_FILES[table.protocol], number)] = render_contact_csv(
                chunk, call_type=capability.call_type
            )
    if files and not CONTACT_FORMAT_VERIFIED:
        warnings.append(
            "contact CSV header and file names are not yet confirmed against a D890UV CPS Export All; "
            "import them on their own (Tool > Import) and check a few entries"
        )
    return files, warnings
