"""Radio-neutral interpretation of catalog tone strings.

The catalog stores tones in the BCDx36HP notation the HPE writer needs
(``TONE=C127.3``, ``D023``, ``NAC=293``, ``ColorCode=1``).  Every other radio
wants that same information in its own shape: CHIRP splits it across
``Tone``/``rToneFreq``/``DtcsCode`` columns, and Yaesu programmers use yet
another layout.

Parsing therefore belongs here rather than in any one exporter, so a new
target never has to re-derive the meaning of a tone string.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

TONE_NONE = "none"
TONE_CTCSS = "ctcss"
TONE_DCS = "dcs"
#: Digital squelch that only a digital-capable radio can act on.  Analog
#: radios must treat these as "no tone" rather than inventing a CTCSS value.
TONE_NAC = "nac"
TONE_COLOR_CODE = "colorcode"
TONE_UNKNOWN = "unknown"

_CTCSS_RE = re.compile(r"^TONE=C(\d{1,3}(?:\.\d{1,2})?)$")
_DCS_RE = re.compile(r"^(?:TONE=)?D(\d{3})$")
_NAC_RE = re.compile(r"^NAC=([0-9A-Fa-f]{1,3}|Srch)$")
_COLOR_CODE_RE = re.compile(r"^ColorCode=(\d{1,2})$")


@dataclass(frozen=True)
class ToneSpec:
    """A parsed tone, in whatever form the source expressed it."""

    kind: str = TONE_NONE
    ctcss_hz: Optional[float] = None
    dcs_code: Optional[str] = None
    raw: str = ""

    @property
    def is_analog_squelch(self) -> bool:
        """True when an analog radio can actually use this tone."""
        return self.kind in (TONE_CTCSS, TONE_DCS)


NO_TONE = ToneSpec()


def parse_tone(raw: Optional[str]) -> ToneSpec:
    """Parse a catalog tone string.

    Unrecognized input is reported as :data:`TONE_UNKNOWN` rather than being
    silently discarded or guessed at, so callers can surface it.
    """
    text = (raw or "").strip()
    if not text:
        return NO_TONE

    match = _CTCSS_RE.match(text)
    if match:
        return ToneSpec(kind=TONE_CTCSS, ctcss_hz=float(match.group(1)), raw=text)

    match = _DCS_RE.match(text)
    if match:
        code = match.group(1)
        if all(digit in "01234567" for digit in code):
            return ToneSpec(kind=TONE_DCS, dcs_code=code, raw=text)
        return ToneSpec(kind=TONE_UNKNOWN, raw=text)

    if _NAC_RE.match(text):
        return ToneSpec(kind=TONE_NAC, raw=text)

    if _COLOR_CODE_RE.match(text):
        return ToneSpec(kind=TONE_COLOR_CODE, raw=text)

    return ToneSpec(kind=TONE_UNKNOWN, raw=text)
