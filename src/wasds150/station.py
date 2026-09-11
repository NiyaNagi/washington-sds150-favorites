"""The station every radio in this project is programmed for.

One place for the operator's identity, so the plan template, the Anytone
codeplug, the settings replay and the generated docs cannot disagree. All of
it is public record: the call signs in the FCC ULS, the DMR ID on
radioid.net.
"""
from __future__ import annotations

CALLSIGN = "WA7DAM"
#: Amateur licence class (see :mod:`wasds150.radios.bandplan`).
LICENSE_CLASS = "general"
#: radioid.net DMR ID registered to :data:`CALLSIGN`; every Anytone channel
#: transmits it.
DMR_ID = 3227807
GMRS_CALL = "WRWH962"
