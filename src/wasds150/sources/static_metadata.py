"""Conservative scanner metadata for checked-in conventional channels.

The static catalog contains enough context to choose useful service types,
modulation modes, and a very small set of priority channels without
guessing site coordinates, tones, or trunked-system details.  Keep this
policy deterministic and deliberately narrow: Sentinel/HPDB remains the
authority for richer metadata once it is available.
"""
from __future__ import annotations

from typing import Optional

from wasds150.models.catalog import FavoritesList
from wasds150.sources.static_channels import ParsedChannel


def channel_mode(fl: FavoritesList, channel: ParsedChannel) -> str:
    context = f"{channel.label} {channel.note}".upper()
    if "NXDN" in context:
        return "NXDN"
    if "DMR" in context:
        return "DMR"
    if "P25" in context or "NAC" in context:
        return "P25"
    if 108.0 <= channel.freq_mhz <= 137.0 or 225.0 <= channel.freq_mhz <= 400.0:
        return "AM"
    if channel.freq_mhz < 30.0 and "AM" in fl.mode.upper():
        return "AM"
    if "FMN" in context or fl.mode.strip().upper() == "FMN":
        return "NFM"
    if "AM" in context:
        return "AM"
    return "FM"


def channel_service_type(fl: FavoritesList, channel: ParsedChannel) -> Optional[int]:
    scenario = fl.scenario.lower()
    label = channel.label.lower()

    if "weather" in scenario:
        return 21  # Other (the BCDx36HP table has no dedicated Weather code)
    if "amateur" in scenario:
        return 13
    if "rail" in scenario:
        return 20
    if channel_mode(fl, channel) == "AM" and (
        "aviation" in scenario or 108.0 <= channel.freq_mhz <= 137.0 or 225.0 <= channel.freq_mhz <= 400.0
    ):
        return 15
    if "military" in scenario:
        return 30
    if "medical" in scenario or "hospital" in label or "hear" in label or "med-" in label:
        return 12
    if "utility" in scenario:
        return 34
    if "transport" in scenario:
        return 26
    if "business" in scenario or "commercial" in scenario or "event" in scenario:
        return 17
    if "school" in scenario:
        return 32
    if "wildfire" in scenario:
        return 8
    if "mountain" in scenario:
        return 11 if "sar" in label or abs(channel.freq_mhz - 155.160) < 0.000001 else 16
    if "interop" in scenario or "sar" in scenario:
        return 11
    if "emergency management" in scenario:
        return 29
    if "public safety" in scenario:
        if "fire" in label:
            return 3 if "dispatch" in label else 8
        if "ems" in label or "ambulance" in label:
            return 4
        if any(term in label for term in ("sheriff", "police", " pd", "law")):
            return 2
        return 1
    return 21


def channel_is_priority(fl: FavoritesList, channel: ParsedChannel) -> bool:
    """Priority only universally important calling/distress channels.

    Broadly flagging every dispatch channel would slow scan cycles, so
    regional fire/EMS priority remains a user/profile decision.
    """
    frequency = round(channel.freq_mhz, 6)
    if frequency == 168.625 and fl.favorite_key in {
        "FL07", "FL32", "FL33", "FL34", "FL35", "FL36", "FL37",
        "FL38", "FL39", "FL40", "FL41", "FL42", "FL43", "FL44",
    }:
        return True
    if frequency == 121.5 and fl.favorite_key in {"FL44", "FL48"}:
        return True
    if frequency == 156.8 and fl.favorite_key in {"FL44", "FL52", "FL54"}:
        return True
    return frequency == 155.16 and fl.favorite_key == "FL01"


def channel_should_avoid(fl: FavoritesList, channel: ParsedChannel) -> bool:
    """Avoid explicitly data-only carrier hits that have no voice audio."""
    del fl
    return "carrier-only" in channel.note.lower()
