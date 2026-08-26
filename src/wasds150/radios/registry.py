"""Registered radio capability profiles.

Registration is an explicit dict, matching ``wasds150.sources.registry``.
There is no plugin discovery: a radio exists in this project only when
someone has written down what it can do and cited where that came from.
"""
from __future__ import annotations

import string
from typing import Dict, List

from wasds150.radios.profile import RadioProfile

#: Characters the TIDRADIO TD-H8/H3/H9 family accepts in a channel name,
#: per the ``TDH8_CHARSET`` constant in CHIRP's ``tdh8.py`` driver.
_TDH9_CHARSET = string.ascii_letters + string.digits + "!@#$%^&*()+-=[]:\";'<>?,./ "

#: Uniden SDS150 / BCDx36HP.
#:
#: Bands and modes mirror the values the HPE writer has always enforced, so
#: adopting this profile cannot change existing SDS150 output.
#: Source: docs/washington-sds150-favorites-master.md section 1.2, which
#: corrects the coverage figures against the Uniden product specification.
SDS150 = RadioProfile(
    id="sds150",
    vendor="Uniden",
    model="SDS150",
    rx_bands=(
        (25.0, 512.0),
        (758.0, 824.0),
        (849.0, 869.0),
        (894.0, 960.0),
        (1240.0, 1300.0),
    ),
    modes=frozenset(
        {"AUTO", "ALL", "AM", "FM", "NFM", "WFM", "FMB", "P25", "DMR", "NXDN"}
    ),
    tx_bands=(),
    max_channels=None,
    name_max_len=None,
    supports_trunking=True,
    supports_talkgroups=True,
    supports_banks=True,
    notes=(
        "Receive-only scanner. P25 Phase I/II native; DMR and NXDN require a "
        "paid upgrade keyed to the scanner serial. Organizes channels into "
        "Favorites Lists, systems, sites and departments."
    ),
)

#: TIDRADIO TD-H9.
#:
#: Sources: the manufacturer comparison table at
#: https://tidradio.com/products/td-h9-10w-bluetooth-aprs-radio-handheld ,
#: the TD-H9 user manual, and the memory layout in the CHIRP test driver
#: attached to https://chirpmyradio.com/issues/12216 (199 usable memories in a
#: 200-entry struct, eight-character names, no banks, per-channel modulation).
#:
#: ``tx_bands`` describes the Normal/unlocked firmware mode.  It is a
#: statement about the hardware, not about what any operator is licensed to
#: transmit on; transmit policy is decided when a plan is built.
TD_H9 = RadioProfile(
    id="td-h9",
    vendor="TIDRADIO",
    model="TD-H9",
    rx_bands=(
        (76.0, 108.0),
        (108.0, 136.0),
        (136.0, 174.0),
        (220.0, 230.0),
        (350.0, 390.0),
        (400.0, 520.0),
    ),
    modes=frozenset({"AM", "FM", "NFM"}),
    tx_bands=(
        (136.0, 174.0),
        (220.0, 259.0),
        (300.0, 390.0),
        (400.0, 590.0),
    ),
    max_channels=199,
    name_max_len=8,
    name_charset=_TDH9_CHARSET,
    supports_trunking=False,
    supports_talkgroups=False,
    supports_banks=False,
    supports_per_channel_tone=True,
    supports_per_channel_mode=True,
    supports_per_channel_step=False,
    notes=(
        "Analog only: no P25, DMR, NXDN, D-STAR or Fusion decode. No 700/800 "
        "MHz coverage, so trunked public-safety systems are out of reach. No "
        "banks or zones, so memory order is the only organization and scanning "
        "walks the list. GNSS, APRS and SMS settings cannot be written by any "
        "current tool including the factory CPS."
    ),
)

#: Yaesu FTX-1 (Field / optima).  Scaffolding for a later export target.
#:
#: Source: the Yaesu product page and the RigPix specification summary.  The
#: per-channel field list has not been confirmed against the operating manual,
#: so this profile is marked unverified and must not be used to publish
#: artifacts until it has been checked.
FTX1 = RadioProfile(
    id="ftx1",
    vendor="Yaesu",
    model="FTX-1",
    rx_bands=(
        (0.03, 174.0),
        (400.0, 470.0),
    ),
    modes=frozenset({"AM", "FM", "NFM", "USB", "LSB", "CW", "DV"}),
    tx_bands=(
        (1.8, 2.0),
        (3.5, 4.0),
        (5.3, 5.4),
        (7.0, 7.3),
        (10.1, 10.15),
        (14.0, 14.35),
        (18.068, 18.168),
        (21.0, 21.45),
        (24.89, 24.99),
        (28.0, 29.7),
        (50.0, 54.0),
        (144.0, 148.0),
        (430.0, 450.0),
    ),
    max_channels=999,
    name_max_len=12,
    supports_trunking=False,
    supports_talkgroups=False,
    supports_banks=True,
    notes=(
        "HF/50/144/430 MHz all-mode SDR transceiver. Amateur transmit only. "
        "Programmed with RT Systems YPS-FTX1; CHIRP does not support it. "
        "PRELIMINARY: per-channel fields not yet confirmed against the manual."
    ),
    verified=False,
)

#: Kenwood TH-D75A, North American model, firmware 1.03.
#:
#: Sources: Kenwood's product specification and in-depth manual, MCP-D75
#: 1.00, and a physical TH-D75A running firmware 1.03. Band B is the
#: wideband receiver; Band A's narrower coverage is a subset of it, so the
#: union is one continuous receive range here. The 1,500-entry native D-STAR
#: repeater list is separate from the 1,000 ordinary memory channels.
TH_D75 = RadioProfile(
    id="th-d75",
    vendor="Kenwood",
    model="TH-D75A",
    rx_bands=((0.1, 524.0),),
    modes=frozenset({"FM", "NFM", "DV", "AM", "USB", "LSB", "CW", "WFM"}),
    tx_bands=(
        (144.0, 148.0),
        (222.0, 225.0),
        (430.0, 450.0),
    ),
    max_channels=1000,
    name_max_len=16,
    name_charset=string.ascii_letters + string.digits + " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    supports_trunking=False,
    supports_talkgroups=False,
    supports_banks=True,
    supports_per_channel_tone=True,
    supports_per_channel_mode=True,
    supports_per_channel_step=True,
    notes=(
        "Tri-band 144/222/430 MHz FM/NFM/D-STAR transceiver with a 0.1-524 "
        "MHz Band B receiver supporting AM, SSB, CW and WFM. Holds 1,000 "
        "ordinary memories in 30 named groups plus a separate 1,500-entry "
        "D-STAR repeater list. No P25, DMR, NXDN, trunk tracking or Fusion "
        "voice decode. APRS identity is operator-specific and is preserved "
        "from the radio rather than synthesized."
    ),
    verified=True,
)

_REGISTRY: Dict[str, RadioProfile] = {
    SDS150.id: SDS150,
    TD_H9.id: TD_H9,
    FTX1.id: FTX1,
    TH_D75.id: TH_D75,
}


def list_profiles() -> Dict[str, RadioProfile]:
    return dict(_REGISTRY)


def profile_ids() -> List[str]:
    return sorted(_REGISTRY)


def get_profile(radio_id: str) -> RadioProfile:
    key = str(radio_id).strip().lower()
    try:
        return _REGISTRY[key]
    except KeyError:
        raise KeyError(
            f"unknown radio {radio_id!r}; known radios: {', '.join(profile_ids())}"
        ) from None
