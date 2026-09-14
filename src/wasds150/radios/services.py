"""Which radio service a frequency is in, and so whether the operator may
transmit on it.

Blocks group channels for scanning; they do not decide what a channel is. A
ham repeater that lands in a catch-all block is still a ham repeater, and
blocking PTT on it - the TH-D75 does that with an out-of-band split - only
makes a radio refuse a station its operator may use. Fleet plans therefore
decide transmit by service (``ChannelPlan.transmit_by_service``):

* amateur: any frequency in a US amateur band, inside the licence class's
  privileges (:func:`wasds150.radios.bandplan.may_transmit`);
* GMRS and FRS: the 22 channels and the GMRS repeater inputs, for a GMRS
  licensee;
* MURS: its five channels.

Everything else - public safety, business, marine, air, rail, weather - is
receive only whatever block holds it: the operator holds no licence there.
"""
from __future__ import annotations

from typing import Iterable, Optional

from wasds150.radios.bandplan import band_for

GMRS_MAIN = (462.550, 462.575, 462.600, 462.625, 462.650, 462.675, 462.700, 462.725)
GMRS_INTERSTITIAL = (462.5625, 462.5875, 462.6125, 462.6375, 462.6625, 462.6875, 462.7125)
FRS_ONLY = (467.5625, 467.5875, 467.6125, 467.6375, 467.6625, 467.6875, 467.7125)
#: A GMRS repeater listens five megahertz above its main-channel output.
GMRS_REPEATER_INPUTS = tuple(round(f + 5.0, 4) for f in GMRS_MAIN)
MURS = (151.820, 151.880, 151.940, 154.570, 154.600)

AMATEUR = "amateur"
GMRS = "gmrs"
FRS = "frs"
MURS_SERVICE = "murs"


def _on(freq_mhz: float, channels: Iterable[float], tolerance: float = 0.0006) -> bool:
    return any(abs(freq_mhz - channel) <= tolerance for channel in channels)


def service_for(freq_mhz: Optional[float]) -> Optional[str]:
    """``amateur``, ``gmrs``, ``frs`` or ``murs`` for a frequency the
    operator could be licensed to transmit on, else ``None``."""
    if freq_mhz is None:
        return None
    if band_for(freq_mhz) is not None:
        return AMATEUR
    if _on(freq_mhz, GMRS_MAIN + GMRS_INTERSTITIAL + GMRS_REPEATER_INPUTS):
        return GMRS
    if _on(freq_mhz, FRS_ONLY):
        return FRS
    if _on(freq_mhz, MURS):
        return MURS_SERVICE
    return None
