"""Radio-neutral interpretation of a channel's digital-voice identity.

A DMR memory is not just a frequency: the radio also needs the colour code,
the timeslot and the talkgroup it should key up with, and an NXDN memory
needs its RAN.  The catalog carries those either as structured fields on
:class:`~wasds150.models.catalog.Channel` (preferred) or, for older rows,
folded into the scanner-facing ``tone`` string (``ColorCode=1``) and free
text (``RAN14``).  This module is where the two representations are
reconciled so that no exporter has to re-derive them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

from wasds150.radios.tones import _COLOR_CODE_RE

DIGITAL_MODES = frozenset({"DMR", "NXDN", "P25"})

_RAN_RE = re.compile(r"\bRAN\s*[=:]?\s*(\d{1,2})\b", re.IGNORECASE)
_NAC_RE = re.compile(r"^NAC=([0-9A-Fa-f]{1,3})$")
_CALL_TYPES = ("group", "private", "all")


@dataclass(frozen=True)
class DigitalSpec:
    """What a digital-capable radio needs to program one memory."""

    protocol: str
    color_code: Optional[int] = None
    timeslot: Optional[int] = None
    talkgroup: Optional[int] = None
    talkgroup_name: str = ""
    call_type: str = "group"
    ran: Optional[int] = None
    group_id: Optional[int] = None
    network: str = ""

    @property
    def has_contact(self) -> bool:
        return self.talkgroup is not None


def color_code_from_tone(raw: Optional[str]) -> Optional[int]:
    match = _COLOR_CODE_RE.match((raw or "").strip())
    return int(match.group(1)) if match else None


def ran_from_text(*texts: Optional[str]) -> Optional[int]:
    """Find an NXDN RAN written into free text (``RAN14``, ``RAN 14``,
    ``RAN=14``)."""
    for text in texts:
        if not text:
            continue
        match = _RAN_RE.search(text)
        if match:
            value = int(match.group(1))
            if 0 <= value <= 63:
                return value
    return None


def digital_spec(channel, mode: Optional[str]) -> Optional[DigitalSpec]:
    """Describe ``channel`` for ``mode``, or ``None`` for analog modes.

    Structured fields win; the tone string and notes are only consulted for
    what they lack, so a row that only carries ``ColorCode=1`` still yields
    the colour code while never inventing a talkgroup.
    """
    protocol = (mode or "").strip().upper()
    if protocol not in DIGITAL_MODES:
        return None

    call_type = (getattr(channel, "dmr_call_type", "") or "group").strip().lower()
    if call_type not in _CALL_TYPES:
        call_type = "group"

    if protocol == "DMR":
        color = getattr(channel, "dmr_color_code", None)
        if color is None:
            color = color_code_from_tone(getattr(channel, "tone", ""))
        return DigitalSpec(
            protocol="DMR",
            color_code=color,
            timeslot=getattr(channel, "dmr_timeslot", None),
            talkgroup=getattr(channel, "dmr_talkgroup", None),
            talkgroup_name=getattr(channel, "dmr_talkgroup_name", "") or "",
            call_type=call_type,
            network=getattr(channel, "network", "") or "",
        )
    if protocol == "NXDN":
        ran = getattr(channel, "nxdn_ran", None)
        if ran is None:
            ran = ran_from_text(getattr(channel, "tone", ""), getattr(channel, "notes", ""), getattr(channel, "label", ""))
        return DigitalSpec(
            protocol="NXDN",
            ran=ran,
            group_id=getattr(channel, "nxdn_group_id", None),
            talkgroup=getattr(channel, "dmr_talkgroup", None),
            talkgroup_name=getattr(channel, "dmr_talkgroup_name", "") or "",
            call_type=call_type,
            network=getattr(channel, "network", "") or "",
        )
    # P25: the catalog stores the NAC in the tone string; no memory-list radio
    # in this project decodes it, but keep the identity so reports can show it.
    return DigitalSpec(protocol="P25", network=getattr(channel, "network", "") or "")


def digital_identity(spec: Optional[DigitalSpec]) -> Tuple:
    """The part of a digital memory that makes it distinct from another on
    the same frequency: two talkgroups on one repeater are two memories."""
    if spec is None:
        return ()
    return (spec.protocol, spec.color_code, spec.talkgroup, spec.timeslot, spec.ran, spec.group_id)


def describe(spec: Optional[DigitalSpec]) -> str:
    """Short human-readable form for reports: ``CC1 TS2 TG3153 WA1``."""
    if spec is None:
        return ""
    parts = []
    if spec.protocol == "DMR":
        if spec.color_code is not None:
            parts.append(f"CC{spec.color_code}")
        if spec.timeslot is not None:
            parts.append(f"TS{spec.timeslot}")
        if spec.talkgroup is not None:
            parts.append(f"TG{spec.talkgroup}")
        if spec.talkgroup_name:
            parts.append(spec.talkgroup_name)
    elif spec.protocol == "NXDN":
        if spec.ran is not None:
            parts.append(f"RAN{spec.ran}")
        if spec.group_id is not None:
            parts.append(f"GID{spec.group_id}")
    else:
        parts.append(spec.protocol)
    return " ".join(parts)
