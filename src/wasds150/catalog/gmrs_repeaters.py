"""Open GMRS repeaters listed within 60 miles of home.

GMRS has no frequency coordinator, so there is no WWARA to cite: the public
record is what owners list in directories. These rows come from the
RepeaterBook Washington GMRS list, cross-checked against the KK7NPS
Washington list (July 2023) where it has the machine, read on 2026-09-10.
Only repeaters listed as open, on the air and with a published access tone
are kept. Closed machines need the owner's permission; the Seattle Hubs
Repeater Group's King County machines arrive from a local RadioReference
import instead, because their tones are published only there.

Positions are town or site centroids estimated for the radius filter, not
published coordinates. The tones are directory data that no owner page
confirms; a wrong one costs a failed key-up.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.util.hashing import stable_id

READ_ON = "2026-09-10"
REPEATERBOOK_LIST = "https://www.repeaterbook.com/gmrs/Display_SS.php?state_id=53"
REPEATERBOOK_DETAIL = "https://www.repeaterbook.com/gmrs/details.php?state_id=53&ID={}"
KK7NPS_LIST = "https://kk7nps.com/gmrs-radio/washington-gmrs-repeaters/"
CFR_95_1763 = "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-95/subpart-E/section-95.1763"

_HOME = (47.6351, -121.9954)
_ST_OTHER = 21
#: Output MHz to GMRS channel number (47 CFR 95.1763).
_CHANNEL = {462.550: 15, 462.575: 16, 462.600: 17, 462.625: 18, 462.650: 19, 462.675: 20, 462.700: 21, 462.725: 22}

# output, tone in, tone out, call, site, latitude, longitude,
# RepeaterBook ID, also on the KK7NPS list, note.
_ROWS = (
    (462.575, "156.7", "156.7", "WQRZ288", "Lake Tapps", 47.23, -122.18, 850, True, ""),
    (462.575, "229.1", "229.1", "WSFY282", "Vaughn", 47.34, -122.77, 1697, False, ""),
    (462.600, "123.0", "123.0", "WQYS525", "Redmond Trilogy", 47.70, -122.03, 802, True, ""),
    (462.600, "127.3", "127.3", "WQYQ893", "Clinton", 47.91, -122.41, 823, True, "Scatchet Head"),
    (462.600, "D074", "D074", "WRPC310", "Gold Mtn", 47.55, -122.79, 1516, False, "Bremerton"),
    (462.600, "91.5", "91.5", "WRPE780", "Port Townsend", 48.12, -122.76, 1410, False, "Morgan Hill"),
    (462.600, "103.5", "", "WRTY274", "Roy", 47.00, -122.54, 574, True, ""),
    (462.600, "141.3", "141.3", "WRJB953", "Olympia", 47.04, -122.90, 203, False, "Open Repeater Initiative"),
    (462.650, "151.4", "", "WROD852", "Bothell", 47.80, -122.21, 663, True, "Canyon Park"),
    (462.650, "77.0", "77.0", "WSFK553", "Spanaway", 47.10, -122.44, 2217, False, ""),
    (462.675, "173.8", "173.8", "WRPR468", "Gig Harbor", 47.35, -122.60, 687, False, "Peacock Hill; KK7NPS lists 141.3"),
    (462.700, "103.5", "103.5", "WRNV843", "Mt Si", 47.49, -121.72, 403, True, "North Bend; Mt Si Neighborhood Radio Watch"),
    (462.700, "136.5", "136.5", "WSLF710", "Mukilteo", 47.88, -122.33, 2193, False, "Picnic Point"),
    (462.700, "254.1", "254.1", "WRBQ486", "Auburn", 47.31, -122.23, 1789, False,
     "Auburn Area Emergency Communication Team; RadioReference lists no tone, so confirm with AAECT"),
    (462.700, "77.0", "77.0", "WSFK553", "Spanaway", 47.10, -122.44, 2218, False, ""),
    (462.700, "210.7", "210.7", "WRVI233", "Shelton", 47.22, -123.10, 1592, False, ""),
    (462.725, "141.3", "141.3", "WQVZ485", "Snohomish", 47.91, -122.10, 439, True,
     "Open Repeater Initiative; travel tone also accepted"),
)


def _tone(value: str) -> str:
    if not value:
        return ""
    return value if value.startswith("D") else f"TONE=C{value}"


def _channel(row) -> Channel:
    output, tone_in, tone_out, call, site, lat, lon, rb_id, on_kk, note = row
    number = _CHANNEL[output]
    sources = [REPEATERBOOK_DETAIL.format(rb_id)] + ([KK7NPS_LIST] if on_kk else [])
    details = [
        call,
        note,
        f"input {output + 5.0:.3f}, access tone {tone_in}",
        f"listed open on {READ_ON}; tone not confirmed by the owner",
        "; ".join(sources),
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
        label="Listed Open Repeaters",
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
        source_type=f"Public repeater directories (RepeaterBook, KK7NPS), read {READ_ON}",
        system_or_category="Open GMRS repeaters with a published access tone",
        sites_or_coverage="Town or site centroids, estimated; not published coordinates",
        # Prose only: static_systems_for() reads any number here as a channel.
        departments_or_channels="Open repeaters on the GMRS main-channel outputs, one channel per listing",
        mode="FM",
        monitorability="FM, native on every radio; the TD-H9 transmits on each input under WRWH962",
        upgrade_required="None",
        source_url=REPEATERBOOK_LIST,
        notes=(
            "GMRS has no coordinator, so these are directory listings: open, on the air and "
            "toned as listed, but not confirmed by their owners. Seattle Hubs Repeater Group "
            "machines come from a local RadioReference import."
        ),
        systems=[
            System(
                id=stable_id("gmrs-repeaters:system", kind="system"),
                label="Puget Sound GMRS Repeaters",
                departments=[department],
            )
        ],
        provenance=[
            Provenance(source_adapter="repeaterbook_list", source_url=REPEATERBOOK_LIST,
                       fetched_at=f"{READ_ON}T00:00:00Z", confidence="community"),
            Provenance(source_adapter="kk7nps_list", source_url=KK7NPS_LIST,
                       fetched_at=f"{READ_ON}T00:00:00Z", confidence="community"),
        ],
    )
