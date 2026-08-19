"""Amateur band plan and calling frequencies as a Favorites List.

``HAM01`` is generated from :mod:`wasds150.radios.bandplan` rather than being
typed out again here, so the regulatory data has exactly one home.  Editing a
band edge changes the band plan, the scan ranges, and this list together.

Channels are grouped by band, which is how an operator thinks about them, and
each carries the General-class privilege summary for its band in the note so
the limits travel with the channel into whatever radio it is programmed to.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.radios.bandplan import (
    ARRL_BAND_PLAN,
    BANDS,
    CFR_97_301,
    UNREACHABLE_BANDS,
    Band,
    CallingFrequency,
    general_class_summary,
)
from wasds150.util.hashing import stable_id

#: Sentinel service type for amateur radio.
_ST_HAM = 13

#: Time and frequency standards. Not amateur, but every HF operator uses them
#: to check propagation and calibrate, so they belong with this material.
_STANDARDS = (
    (2.500, "WWV/WWVH 2.5", "AM", "Time and frequency standard"),
    (5.000, "WWV/WWVH 5", "AM", "Time and frequency standard"),
    (10.000, "WWV/WWVH 10", "AM", "Time and frequency standard"),
    (15.000, "WWV/WWVH 15", "AM", "Time and frequency standard"),
    (20.000, "WWV/WWVH 20", "AM", "Time and frequency standard"),
    (3.330, "CHU Canada 3.33", "USB", "Canadian time signal"),
    (7.850, "CHU Canada 7.85", "USB", "Canadian time signal"),
    (14.670, "CHU Canada 14.67", "USB", "Canadian time signal"),
)


def _channel(band: Band, calling: CallingFrequency) -> Channel:
    privileges = general_class_summary(band)
    provenance = calling.note or ARRL_BAND_PLAN
    if not calling.official:
        provenance = f"{provenance}; observed convention, not a published designation"
    return Channel(
        id=stable_id(f"ham-bandplan:{band.id}:{calling.mhz}", kind="channel"),
        label=calling.label,
        freq_mhz=calling.mhz,
        mode=calling.mode,
        service_type=_ST_HAM,
        notes=f"{provenance}. {privileges}",
    )


def _standards_department() -> Department:
    channels = [
        Channel(
            id=stable_id(f"ham-bandplan:standards:{mhz}", kind="channel"),
            label=label,
            freq_mhz=mhz,
            mode=mode,
            service_type=_ST_HAM,
            notes=f"{note}. Receive only.",
        )
        for mhz, label, mode, note in _STANDARDS
    ]
    return Department(
        id=stable_id("ham-bandplan:dept:standards", kind="department"),
        label="Time and Frequency Standards",
        channels=channels,
    )


def system() -> System:
    departments: List[Department] = []
    for band in BANDS:
        if not band.calling:
            continue
        channels = [_channel(band, calling) for calling in band.calling]
        departments.append(
            Department(
                id=stable_id(f"ham-bandplan:dept:{band.id}", kind="department"),
                label=f"{band.label} calling and activity",
                channels=channels,
            )
        )
    departments.append(_standards_department())
    return System(
        id=stable_id("ham-bandplan:system", kind="system"),
        label="US Amateur Band Plan",
        departments=departments,
    )


def favorite() -> FavoritesList:
    """The ``HAM01`` Favorites List."""
    unreachable = "; ".join(f"{key}: {why}" for key, why in UNREACHABLE_BANDS.items())
    return FavoritesList(
        id=stable_id("ham-bandplan:HAM01", kind="favorites-list"),
        slug="ham01",
        favorite_key="HAM01",
        favorite_name="Amateur Band Plan & Calling Frequencies",
        region="United States",
        counties="All",
        scenario="Amateur calling, digital and beacon frequencies across every US band",
        source_type="conventional, generated from the band plan",
        system_or_category="US amateur band plan per 47 CFR 97.301 and the ARRL band plan",
        sites_or_coverage="Not location dependent",
        departments_or_channels=(
            "Per band: CW and SSB calling, QRP calling, FT8, FT4, WSPR, PSK31, "
            "RTTY, SSTV and propagation beacons, plus WWV, WWVH and CHU"
        ),
        mode="CW, USB, LSB, AM and FM",
        monitorability=(
            "Receive anywhere. Transmit only within the operator's licence class; "
            "each channel carries its band's General-class limits in the note."
        ),
        upgrade_required="None",
        source_url=CFR_97_301,
        notes=(
            "Generated from wasds150.radios.bandplan so the regulatory data has a "
            "single home. Frequencies that are widely observed conventions rather "
            "than published designations are labelled as such rather than being "
            "presented as rules. Bands no radio in this project can reach are "
            f"recorded but not programmed: {unreachable}"
        ),
        systems=[system()],
        # This list spans HF through UHF in SSB, CW, AM and FM. No single
        # radio covers all of it, so each exporter keeps the part its target
        # can use rather than the list failing validation for every radio.
        reference_only=True,
    )


def favorites() -> List[FavoritesList]:
    return [favorite()]
