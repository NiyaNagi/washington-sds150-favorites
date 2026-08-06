"""Upper Lena Lake listening profiles using public intent and NPS coordinates.

The campsite coordinate is from Olympic National Park's public Camp Areas GPX.
No licensed HPDB records are checked in; richer regional P25 content is resolved
from the user's local Sentinel database and reused from existing catalog rows.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import FavoritesList
from wasds150.util.hashing import stable_id

UPPER_LENA_LAT = 47.63373172965662
UPPER_LENA_LON = -123.209626245127
NPS_TRAIL_URL = "https://www.nps.gov/olym/planyourvisit/upper-lena-lake-trail.htm"
NPS_COORDINATE_SOURCE = "https://nps.gov/olym/planyourvisit/upload/OLYM-Camp-Areas-11_16_2018.gpx"


def _profile(
    key: str,
    name: str,
    scenario: str,
    components: str,
    radius: float,
    content: str,
    source_type: str = "derived verified rollup",
    notes: str = "",
) -> FavoritesList:
    return FavoritesList(
        id=stable_id(f"upper-lena:{key}", kind="favorites-list"),
        slug=key.lower(),
        favorite_key=key,
        favorite_name=name,
        region="Upper Lena Lake / Hamma Hamma / Hood Canal / Olympic Peninsula",
        counties="Mason, Jefferson, Clallam, Kitsap",
        scenario=scenario,
        source_type=source_type,
        system_or_category=f"Upper Lena Lake profile (reuses {components})",
        sites_or_coverage=(
            f"NPS Upper Lena Lake campsite {UPPER_LENA_LAT:.6f},{UPPER_LENA_LON:.6f}; "
            f"{radius:g}-mile department radius; component site locations retained"
        ),
        departments_or_channels=content,
        mode="FM/NFM + AM + P25 + WX; DMR/NXDN where explicitly reused",
        monitorability="Clear/reference channels prioritized; encrypted and data-only traffic may be silent",
        upgrade_required="DMR/NXDN only for reused components explicitly using those modes",
        source_url=NPS_TRAIL_URL,
        notes=(
            "Official NPS campsite coordinate and wilderness context; Upper Lena is inside Olympic National Park "
            "and approached through Olympic National Forest. " + notes
        ),
    )


def favorites() -> List[FavoritesList]:
    return [
        FavoritesList(
            id=stable_id("upper-lena:UL00", kind="favorites-list"),
            slug="ul00",
            favorite_key="UL00",
            favorite_name="Upper Lena - Fast Local Essentials",
            region="Upper Lena Lake / Hamma Hamma / Hood Canal",
            counties="Mason, Jefferson",
            scenario="Compact backcountry safety / local public safety / weather / calling",
            source_type="conventional static public channels",
            system_or_category="Upper Lena Lake compact verified local channel set",
            sites_or_coverage=(
                f"NPS Upper Lena Lake campsite {UPPER_LENA_LAT:.6f},{UPPER_LENA_LON:.6f}; "
                "45-mile department radius"
            ),
            departments_or_channels=(
                "ONP Main168.525;ONP Maint168.350;ONF West164.825;ONF East164.800;"
                "WA SAR155.160;WSP D8 154.770;Mason Sheriff460.225/460.5125;"
                "Mason Fire5 154.190;REDNET153.830;Jefferson Sheriff453.575;"
                "Brinnon Fire154.0925;Olympic Ambulance462.950;DNR Main159.420;"
                "DNR Common151.415(PL103.5);NIFC Air Guard168.625;NIFC Flight Following168.650;"
                "NIFC ICP168.550;Civil Guard121.500(AM);Military Guard243.000(AM);"
                "SAR Air123.100(AM);Airlift NW129.825(AM);HEAR155.340;"
                "Marine Ch16 156.800;Ch13 156.650;Ch22A 157.100;Ch5A 156.250;"
                "Ch14 156.700;Ch6 156.300;Ch68 156.425;Ch69 156.475;Ch71 156.575;Ch72 156.625;"
                "NOAA Capitol Peak162.475;NOAA Puget Sound Marine162.425;NOAA Seattle162.550;"
                "Mason ARC146.720(PL103.5);Ham Call146.520/446.000/223.500/52.525;"
                "NWAC FRS Ch7 462.7125(CTCSS71.9)"
            ),
            mode="FM/NFM + AM + WX",
            monitorability="Full for clear analog channels; terrain and line of sight dominate reception",
            upgrade_required="None",
            source_url=NPS_COORDINATE_SOURCE,
            notes=(
                "Fast scan-cycle list for the trail and campsite. Mason ARC 146.720 (-600 kHz, PL 103.5) "
                "is from the club's published weekly-net page; receive frequency only is programmed."
            ),
        ),
        _profile(
            "UL01", "Upper Lena - Wilderness Essentials",
            "Backcountry safety / SAR / park / forest / wildfire / weather / local calling",
            "UL00, FL01, FL02, FL03, FL06, FL07, FL13, FL14, FL32, FL44, FL46, FL48, FL52, FL53, FL55, FL60, FL62, FL63, FL65, FL66, FL71, FL74b, FL75",
            45,
            "ONP/ONF, Mason/Jefferson fire/EMS, SAR/mutual aid, NIFOG/STATEOPS, DNR/NIFC, WSP D8 conventional, "
            "NOAA Weather, civil/SAR/medevac air, Hood Canal marine, amateur/ARES/simplex, FRS/GMRS/MURS/CB and road crews",
            notes=(
                "Designed to work without private data because every component has a static public channel baseline. "
                "NPS warns the route is moderate-to-strenuous, rises to 4,550 feet, can retain snow, and requires emergency planning."
            ),
        ),
        _profile(
            "UL02", "Upper Lena - Regional Public Safety",
            "Regional public safety / transportation / EMS / Hood Canal travel",
            "FL04, FL05, FL13, FL14, FL18, FL32",
            85,
            "WSP/WSDOT P25, Mason/Thurston, Jefferson/Kitsap, Clallam, Olympic NP/Forest and regional fire/EMS/SAR",
            source_type="derived verified rollup (local Sentinel HPDB required for full P25 content)",
            notes="Use location control; distant or encrypted law groups can be avoided to keep scan cycles short.",
        ),
        _profile(
            "UL03", "Upper Lena - Complete Area",
            "Complete Upper Lena / Hood Canal / Olympic Peninsula listening",
            "UL01, UL02",
            85,
            "Combined wilderness essentials and regional public-safety/travel profile",
            source_type="derived profile-of-profiles",
            notes="One-list convenience profile; disable distant departments or use UL01 alone for the fastest wilderness scan cycle.",
        ),
    ]


def apply_location(favorite: FavoritesList) -> None:
    """Apply the profile's public circular location tag to copied departments."""
    if favorite.favorite_key not in {"UL00", "UL01", "UL02", "UL03"}:
        return
    radius = 45.0 if favorite.favorite_key in {"UL00", "UL01"} else 85.0
    for system in favorite.systems:
        departments = list(system.departments)
        for site in system.sites:
            departments.extend(site.departments)
        for department in departments:
            department.lat = UPPER_LENA_LAT
            department.lon = UPPER_LENA_LON
            department.range_miles = radius
            department.shape = "Circle"
