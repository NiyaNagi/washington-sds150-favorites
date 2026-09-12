"""Digital contact list CSVs for the Anytone CPS.

The two protocols do **not** share a format, which is why they get separate
headers here. Both were taken from a D890UV CPS 1.05 ``Export All``
(``radio-backups/at-d890uv/20260911-export-all-fw105-nxdn/``):

* DMR, ``DMRDigitalContactList.CSV`` - a ``No.`` column, one ``Name``, and a
  ``Call Type``/``Call Alert`` pair, the same shape as the D878UV family.
* NXDN, ``NXDigitalContactList.CSV`` - no ``No.`` column, the name split into
  ``FIRST_NAME``/``LAST_NAME``, and three trailing columns of its own. The
  first seven are exactly
  :data:`~wasds150.contacts.model.STORE_COLUMNS`.

The captured NXDN table was empty, so the three trailing columns
(``Attr``, ``TxForbid``, ``Ring``) have a confirmed *name* but no confirmed
*value*; they are written empty and
:data:`NXDN_TRAILING_VERIFIED` stays False until a codeplug with a real NXDN
contact has been exported. Columns are filled by header name, so a re-capture
in a different order renders correctly once pasted in.

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
NXDN_CONTACT_HEADER: Tuple[str, ...] = (
    "RADIO_ID", "CALLSIGN", "FIRST_NAME", "LAST_NAME", "CITY", "STATE", "COUNTRY",
    "Attr", "TxForbid", "Ring",
)
CONTACT_HEADERS = {"DMR": CONTACT_HEADER, "NXDN": NXDN_CONTACT_HEADER}
CONTACT_FORMAT_VERIFIED = True
#: The captured NXDN table had no rows, so Attr/TxForbid/Ring are written empty.
NXDN_TRAILING_VERIFIED = False
CONTACT_FILES = {"DMR": "DMRDigitalContactList.CSV", "NXDN": "NXDigitalContactList.CSV"}


def render_contact_csv(
    rows: Sequence[Contact], *, header: Sequence[str] = CONTACT_HEADER, call_type: str = "Private Call"
) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(header)
    for number, contact in enumerate(rows, start=1):
        values = {
            # DMR
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
            # NXDN
            "RADIO_ID": str(contact.radio_id),
            "CALLSIGN": contact.callsign,
            "FIRST_NAME": contact.first_name,
            "LAST_NAME": contact.last_name,
            "CITY": contact.city,
            "STATE": contact.state,
            "COUNTRY": contact.country,
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
                chunk,
                header=CONTACT_HEADERS[table.protocol],
                call_type=capability.call_type,
            )
        if table.protocol == "NXDN" and table.rows and not NXDN_TRAILING_VERIFIED:
            warnings.append(
                "NXDN contacts: Attr, TxForbid and Ring are written empty - the captured "
                "Export All had no NXDN contact to copy them from. Import the list, open "
                "an entry, and if those fields need a value, add one contact by hand and "
                "export again to capture it"
            )
    return files, warnings
