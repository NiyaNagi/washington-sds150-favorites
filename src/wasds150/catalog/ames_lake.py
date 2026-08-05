"""Public intent and location definitions for ZIP 98053 and King County.

Coordinates are 2023 U.S. Census Gazetteer internal-point coordinates for
Washington incorporated places. No licensed frequencies, sites, or talkgroup
IDs are stored here; those are resolved from the user's local Sentinel HPDB.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from wasds150.models.catalog import FavoritesList
from wasds150.util.hashing import stable_id

PSERN_URL = "https://www.radioreference.com/db/sid/11628"
CENSUS_SOURCE = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_gaz_place_53.txt"
AMES_LAKE_LAT = 47.633966
AMES_LAKE_LON = -121.960584


@dataclass(frozen=True)
class CitySpec:
    name: str
    lat: float
    lon: float
    range_miles: float = 8.0
    direct_departments: Tuple[str, ...] = ()
    kcso_dispatch: Tuple[str, ...] = ()
    norcom_law_terms: Tuple[str, ...] = ()
    hospital_terms: Tuple[str, ...] = ()
    fire_dispatch: str = "norcom"  # norcom | valley | none
    extra_channel_terms: Tuple[str, ...] = ()
    sids: Tuple[int, ...] = (11628,)


# All 39 incorporated cities/towns wholly or partly in King County.
KING_COUNTY_CITIES: Dict[str, CitySpec] = {
    "KC01": CitySpec("Algona", 47.281987, -122.250467, 6, ("Algona-Pacific",), fire_dispatch="valley"),
    "KC02": CitySpec("Auburn", 47.303773, -122.210000, 12, ("Auburn",), hospital_terms=("Multicare Auburn",), fire_dispatch="valley"),
    "KC03": CitySpec("Beaux Arts Village", 47.585343, -122.203646, 5, norcom_law_terms=("Bellevue", "Clyde Hill", "Medina")),
    "KC04": CitySpec("Bellevue", 47.597837, -122.156480, 10, ("Bellevue",), norcom_law_terms=("Bellevue", "Clyde Hill", "Medina"), hospital_terms=("Overlake",)),
    "KC05": CitySpec("Black Diamond", 47.314748, -122.017685, 8, kcso_dispatch=("Southeast",), fire_dispatch="valley"),
    "KC06": CitySpec("Bothell", 47.773531, -122.204376, 10, ("Bothell",), norcom_law_terms=("Bothell",), hospital_terms=("Evergreen",)),
    "KC07": CitySpec("Burien", 47.475605, -122.344661, 10, ("Highline",), kcso_dispatch=("Southwest",), hospital_terms=("St. Anne",), fire_dispatch="valley"),
    "KC08": CitySpec("Carnation", 47.644188, -121.900670, 7, kcso_dispatch=("North",), hospital_terms=("Snoqualmie Valley",)),
    "KC09": CitySpec("Clyde Hill", 47.630354, -122.217983, 5, norcom_law_terms=("Bellevue", "Clyde Hill", "Medina")),
    "KC10": CitySpec("Covington", 47.364793, -122.104561, 9, kcso_dispatch=("Southeast",), fire_dispatch="valley", extra_channel_terms=("Covington", "Water")),
    "KC11": CitySpec("Des Moines", 47.388708, -122.317581, 9, ("Des Moines",), fire_dispatch="valley"),
    "KC12": CitySpec("Duvall", 47.735512, -121.972224, 7, ("Duval",), kcso_dispatch=("North",), hospital_terms=("Snoqualmie Valley",)),
    "KC13": CitySpec("Enumclaw", 47.202179, -121.988976, 9, ("Enumclaw",), kcso_dispatch=("Southeast",), fire_dispatch="valley"),
    "KC14": CitySpec("Federal Way", 47.311596, -122.337757, 12, ("Federal Way",), hospital_terms=("St. Francis",), fire_dispatch="valley"),
    "KC15": CitySpec("Hunts Point", 47.642958, -122.229197, 5, norcom_law_terms=("Bellevue", "Clyde Hill", "Medina")),
    "KC16": CitySpec("Issaquah", 47.544488, -122.049085, 9, ("Issaquah", "Snoqualmie"), kcso_dispatch=("Southeast",), norcom_law_terms=("Issaquah",), hospital_terms=("Overlake", "Snoqualmie Valley")),
    "KC17": CitySpec("Kenmore", 47.749858, -122.247244, 7, kcso_dispatch=("North",), hospital_terms=("Evergreen",)),
    "KC18": CitySpec("Kent", 47.387970, -122.212727, 12, ("Kent",), hospital_terms=("Valley Medical",), fire_dispatch="valley"),
    "KC19": CitySpec("Kirkland", 47.696658, -122.204170, 9, ("Kirkland",), norcom_law_terms=("Kirkland",), hospital_terms=("Evergreen",)),
    "KC20": CitySpec("Lake Forest Park", 47.758911, -122.291729, 6, ("Lake Forest Park",), kcso_dispatch=("North",)),
    "KC21": CitySpec("Maple Valley", 47.367147, -122.034815, 9, kcso_dispatch=("Southeast",), fire_dispatch="valley", extra_channel_terms=("Soos Creek", "Water")),
    "KC22": CitySpec("Medina", 47.626541, -122.242866, 5, norcom_law_terms=("Bellevue", "Clyde Hill", "Medina")),
    "KC23": CitySpec("Mercer Island", 47.564004, -122.231214, 7, ("Mercer Island",), norcom_law_terms=("Mercer Island",)),
    "KC24": CitySpec("Milton", 47.251994, -122.317289, 7, ("Sumner",), fire_dispatch="valley", extra_channel_terms=("Milton",), sids=(11628, 8203)),
    "KC25": CitySpec("Newcastle", 47.531486, -122.165582, 7, kcso_dispatch=("Southeast",)),
    "KC26": CitySpec("Normandy Park", 47.432975, -122.344689, 6, ("Highline",), norcom_law_terms=("Normandy Park",), fire_dispatch="valley"),
    "KC27": CitySpec("North Bend", 47.487967, -121.768786, 9, ("Snoqualmie",), kcso_dispatch=("Southeast",), norcom_law_terms=("Snoqualmie",), hospital_terms=("Snoqualmie Valley",)),
    "KC28": CitySpec("Pacific", 47.261974, -122.252429, 6, ("Algona-Pacific",), fire_dispatch="valley"),
    "KC29": CitySpec("Redmond", 47.677924, -122.115336, 10, ("Redmond",), hospital_terms=("Overlake",)),
    "KC30": CitySpec("Renton", 47.479190, -122.194613, 12, ("Renton",), norcom_law_terms=("Renton",), hospital_terms=("Valley Medical",), fire_dispatch="valley"),
    "KC31": CitySpec("Sammamish", 47.594268, -122.038081, 10, kcso_dispatch=("North",), hospital_terms=("Overlake", "Snoqualmie Valley")),
    "KC32": CitySpec("SeaTac", 47.443403, -122.298287, 10, ("Highline",), kcso_dispatch=("Southwest",), fire_dispatch="valley"),
    "KC33": CitySpec("Seattle", 47.619335, -122.351538, 15, ("Seattle", "Seattle Fire", "Seattle Police"), hospital_terms=("Harborview", "Seattle Children", "Swedish - Seattle", "UW Medical", "Virginia Mason"), fire_dispatch="none"),
    "KC34": CitySpec("Shoreline", 47.756917, -122.345505, 10, ("Shoreline",), kcso_dispatch=("North",)),
    "KC35": CitySpec("Skykomish", 47.709852, -121.356448, 8, kcso_dispatch=("North",)),
    "KC36": CitySpec("Snoqualmie", 47.543245, -121.868645, 9, ("Snoqualmie",), kcso_dispatch=("Southeast",), norcom_law_terms=("Snoqualmie",), hospital_terms=("Snoqualmie Valley",)),
    "KC37": CitySpec("Tukwila", 47.476289, -122.275740, 9, ("Tukwila",), fire_dispatch="valley"),
    "KC38": CitySpec("Woodinville", 47.757695, -122.146791, 8, ("Woodinville",), kcso_dispatch=("North",), hospital_terms=("Evergreen",)),
    "KC39": CitySpec("Yarrow Point", 47.644576, -122.219994, 5, norcom_law_terms=("Bellevue", "Clyde Hill", "Medina")),
}


def _system_description(sids: Tuple[int, ...]) -> str:
    labels = [f"SID {sid}" for sid in sids]
    return "PSERN " + " + ".join(labels) + " (locally curated)"


def _city(key: str, spec: CitySpec) -> FavoritesList:
    slug = key.lower()
    return FavoritesList(
        id=stable_id(f"king-county:{key}", kind="favorites-list"),
        slug=slug,
        favorite_key=key,
        favorite_name=f"{spec.name} Local",
        region="King County, Washington",
        counties="King",
        scenario="Local public safety / EMS / city services",
        source_type="trunked P25 Phase II (local Sentinel HPDB required)",
        system_or_category=_system_description(spec.sids),
        sites_or_coverage=(
            f"{spec.name} center {spec.lat:.6f},{spec.lon:.6f}; "
            f"{spec.range_miles:g}-mile department location radius; component site GPS retained"
        ),
        departments_or_channels=(
            "Reviewed fire/EMS, emergency management, interop, hospital, public works, "
            "transportation, and city services; law groups retained in avoided encrypted buckets"
        ),
        mode="P25 Phase II",
        monitorability="Clear operational services plus encrypted law reference buckets",
        upgrade_required="None (P25 native)",
        source_url=PSERN_URL,
        notes=(
            f"Public intent and Census Gazetteer location tag for {spec.name}; "
            "exact radio records resolved from the user-local Sentinel database."
        ),
    )


def favorites() -> List[FavoritesList]:
    rows = [_city(key, spec) for key, spec in KING_COUNTY_CITIES.items()]
    rows.append(FavoritesList(
        id=stable_id("ames-lake:home", kind="favorites-list"),
        slug="la01",
        favorite_key="LA01",
        favorite_name="Ames Lake Home Area",
        region="Ames Lake / Eastside King County",
        counties="King",
        scenario="Home-area public safety / EMS / emergency / city services",
        source_type="trunked P25 Phase II (local Sentinel HPDB required)",
        system_or_category="PSERN SID 11628 (locally curated)",
        sites_or_coverage=f"Ames Lake center {AMES_LAKE_LAT:.6f},{AMES_LAKE_LON:.6f}; 22-mile department radius",
        departments_or_channels="Redmond, Sammamish, Duvall, Carnation, Woodinville, and shared Eastside response services",
        mode="P25 Phase II",
        monitorability="Clear operations plus avoided encrypted law reference buckets",
        upgrade_required="None (P25 native)",
        source_url=PSERN_URL,
        notes="Home profile for ZIP 98053; component site GPS retained.",
    ))
    rows.append(FavoritesList(
        id=stable_id("ames-lake:eastside", kind="favorites-list"),
        slug="la17",
        favorite_key="LA17",
        favorite_name="Eastside King Regional",
        region="Eastside King County",
        counties="King",
        scenario="Regional public safety / EMS / emergency / transportation",
        source_type="trunked P25 Phase II (local Sentinel HPDB required)",
        system_or_category="PSERN SID 11628 (locally curated)",
        sites_or_coverage=f"Ames Lake center {AMES_LAKE_LAT:.6f},{AMES_LAKE_LON:.6f}; 35-mile department radius",
        departments_or_channels="Regional fire/EMS, emergency management, hospitals, public works, transportation, interop, and avoided law reference",
        mode="P25 Phase II",
        monitorability="Clear operations plus avoided encrypted law reference buckets",
        upgrade_required="None (P25 native)",
        source_url=PSERN_URL,
        notes="Broad Eastside travel profile with reviewed city and shared-service groups.",
    ))
    rows.append(FavoritesList(
        id=stable_id("ames-lake:OUT01", kind="favorites-list"),
        slug="out01",
        favorite_key="OUT01",
        favorite_name="WA Outdoor Safety - All",
        region="Washington statewide / Cascades / Puget Sound outdoors",
        counties="All 39 counties",
        scenario="Outdoor safety / SAR / wildfire / emergency / weather / travel",
        source_type="derived verified rollup",
        system_or_category=(
            "Outdoor safety rollup (reuses FL01, FL02, FL03, FL04, FL05, FL06, FL07, FL09a, "
            "FL32, FL33, FL34, FL35, FL36, FL37, FL38, FL39, FL40, FL41, FL42, FL43, FL44, "
            "FL46, FL47, FL48, FL52, FL53, FL54, FL55, FL60, FL61, FL62, FL63, FL65, FL66, "
            "FL71, FL74b, FL75)"
        ),
        sites_or_coverage="Statewide and regional component location metadata preserved",
        departments_or_channels=(
            "SAR; mutual aid; state/federal interoperability; DNR/NIFC wildfire; WSP/WSDOT; "
            "mountain/forest/park safety; civil/FSS/rescue/medevac aviation; marine/USCG/ferries/ports; "
            "amateur/ARES/simplex; GMRS/FRS/NWAC; MURS/CB; hospitals; road/tow; NOAA Weather"
        ),
        mode="P25 Phase II + FM/NFM/AM/DMR/NXDN where verified",
        monitorability="Verified clear/reference components; encrypted law and Discovery-only lists excluded",
        upgrade_required="DMR/NXDN only for verified component channels using those modes",
        source_url="https://www.dnr.wa.gov/WildfireResources",
        notes="Comprehensive travel list; use location control and disable distant components for scan-cycle performance.",
    ))
    return rows
