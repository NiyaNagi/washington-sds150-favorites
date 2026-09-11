"""Open GMRS repeaters within 60 miles of home, added by hand.

GMRS has no frequency coordinator, so there is no WWARA to cite. These rows
were entered by the operator (WA7DAM, licence WRWH962) on 2026-09-10: the
repeaters he intends to use, each with its output channel, site and access
tone. They are manual entries, not a copy of any directory. Closed machines
that need an owner's permission are left out, and the Seattle Hubs Repeater
Group's King County machines arrive from a local RadioReference import
instead.

Positions are town or site centroids, close enough for the radius filter.
The access tones are the operator's best information and are confirmed on
the air one repeater at a time (see docs/open-items.md); a wrong one costs a
failed key-up.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.util.hashing import stable_id

ADDED_ON = "2026-09-10"
CFR_95_1763 = "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-95/subpart-E/section-95.1763"

_HOME = (47.6351, -121.9954)
_ST_OTHER = 21
#: Output MHz to GMRS channel number (47 CFR 95.1763).
_CHANNEL = {462.550: 15, 462.575: 16, 462.600: 17, 462.625: 18, 462.650: 19, 462.675: 20, 462.700: 21, 462.725: 22}

# output, tone in, tone out, call, site, latitude, longitude, note.
_ROWS = (
    (462.575, "156.7", "156.7", "WQRZ288", "Lake Tapps", 47.23, -122.18, ""),
    (462.575, "229.1", "229.1", "WSFY282", "Vaughn", 47.34, -122.77, ""),
    (462.600, "123.0", "123.0", "WQYS525", "Redmond Trilogy", 47.70, -122.03, ""),
    (462.600, "127.3", "127.3", "WQYQ893", "Clinton", 47.91, -122.41, "Scatchet Head"),
    (462.600, "D074", "D074", "WRPC310", "Gold Mtn", 47.55, -122.79, "Bremerton"),
    (462.600, "91.5", "91.5", "WRPE780", "Port Townsend", 48.12, -122.76, "Morgan Hill"),
    (462.600, "103.5", "", "WRTY274", "Roy", 47.00, -122.54, ""),
    (462.600, "141.3", "141.3", "WRJB953", "Olympia", 47.04, -122.90, "Open Repeater Initiative"),
    (462.650, "151.4", "", "WROD852", "Bothell", 47.80, -122.21, "Canyon Park"),
    (462.650, "77.0", "77.0", "WSFK553", "Spanaway", 47.10, -122.44, ""),
    (462.675, "173.8", "173.8", "WRPR468", "Gig Harbor", 47.35, -122.60, "Peacock Hill; 141.3 also reported"),
    (462.700, "103.5", "103.5", "WRNV843", "Mt Si", 47.49, -121.72, "North Bend; Mt Si Neighborhood Radio Watch"),
    (462.700, "136.5", "136.5", "WSLF710", "Mukilteo", 47.88, -122.33, "Picnic Point"),
    (462.700, "254.1", "254.1", "WRBQ486", "Auburn", 47.31, -122.23,
     "Auburn Area Emergency Communication Team; tone unconfirmed, check with AAECT"),
    (462.700, "77.0", "77.0", "WSFK553", "Spanaway", 47.10, -122.44, ""),
    (462.700, "210.7", "210.7", "WRVI233", "Shelton", 47.22, -123.10, ""),
    (462.725, "141.3", "141.3", "WQVZ485", "Snohomish", 47.91, -122.10, "Open Repeater Initiative; travel tone also accepted"),
)


def _tone(value: str) -> str:
    if not value:
        return ""
    return value if value.startswith("D") else f"TONE=C{value}"


def _channel(row) -> Channel:
    output, tone_in, tone_out, call, site, lat, lon, note = row
    number = _CHANNEL[output]
    details = [
        call,
        note,
        f"input {output + 5.0:.3f}, access tone {tone_in}",
        f"added by hand by the operator on {ADDED_ON}; tone not yet confirmed on the air",
    ]
    return Channel(
        id=stable_id(f"gmrs-repeaters:{call}:{output}", kind="channel"),
        label=f"{site} RPT{number}",
        freq_mhz=output,
        tx_freq_mhz=round(output + 5.0, 4),
        mode="FM",
        tone=_tone(tone_out),
        tx_tone=_tone(tone_in),
        service_type=_ST_OTHER,
        notes="; ".join(part for part in details if part),
        lat=lat,
        lon=lon,
        location_precision="unknown",
    )


def channels() -> List[Channel]:
    return [_channel(row) for row in _ROWS]


def favorite() -> FavoritesList:
    """The ``GMRS01`` Favorites List."""
    department = Department(
        id=stable_id("gmrs-repeaters:listed-open", kind="department"),
        label="Open Repeaters",
        channels=channels(),
        lat=_HOME[0],
        lon=_HOME[1],
        range_miles=60.0,
        shape="Circle",
    )
    return FavoritesList(
        id=stable_id("gmrs-repeaters:GMRS01", kind="favorites-list"),
        slug="gmrs01",
        favorite_key="GMRS01",
        favorite_name="Puget Sound Open GMRS Repeaters",
        region="Within 60 miles of Ames Lake / Redmond",
        counties="King, Snohomish, Pierce, Kitsap, Island, Jefferson, Thurston, Mason",
        scenario="GMRS repeaters a licensed station may use without asking first",
        source_type=f"Manual entry by the operator, {ADDED_ON}",
        system_or_category="Open GMRS repeaters with an access tone",
        sites_or_coverage="Town or site centroids, estimated; not published coordinates",
        # Prose only: static_systems_for() reads any number here as a channel.
        departments_or_channels="Open repeaters on the GMRS main-channel outputs, one channel per repeater",
        mode="FM",
        monitorability="FM, native on every radio; the TD-H9 transmits on each input under WRWH962",
        upgrade_required="None",
        source_url=CFR_95_1763,
        notes=(
            "Added by hand by the operator. GMRS has no coordinator; tones are confirmed on the air "
            "one repeater at a time. Seattle Hubs Repeater Group machines come from a local "
            "RadioReference import."
        ),
        systems=[
            System(
                id=stable_id("gmrs-repeaters:system", kind="system"),
                label="Puget Sound GMRS Repeaters",
                departments=[department],
            )
        ],
        provenance=[
            Provenance(source_adapter="operator_manual", source_url=None,
                       fetched_at=f"{ADDED_ON}T00:00:00Z", confidence="community"),
        ],
    )
