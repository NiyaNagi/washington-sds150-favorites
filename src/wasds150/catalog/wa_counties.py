"""Washington county reference points.

Internal points and land areas from the U.S. Census Bureau 2023 Gazetteer
(``2023_Gaz_counties_national.zip``, public domain). The radius is that of a
circle with the county's land area, which is the coarse "somewhere in this
county" geo-fence a scanner department gets when a source publishes a county
but no site position.
"""
from __future__ import annotations

from typing import Dict, NamedTuple, Optional

CENSUS_GAZETTEER_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/"
    "2023_Gaz_counties_national.zip"
)


class CountyPoint(NamedTuple):
    name: str
    geoid: int
    lat: float
    lon: float
    radius_miles: float


# name, GEOID, INTPTLAT, INTPTLONG, equal-area radius (mi)
_ROWS = (
    ("Adams", 53001, 47.011238, -118.512861, 24.8),
    ("Asotin", 53003, 46.181861, -117.227781, 14.2),
    ("Benton", 53005, 46.228125, -119.516659, 23.3),
    ("Chelan", 53007, 47.860974, -120.619041, 30.5),
    ("Clallam", 53009, 48.110903, -123.889860, 23.5),
    ("Clark", 53011, 45.771730, -122.485953, 14.1),
    ("Columbia", 53013, 46.292850, -117.911634, 16.6),
    ("Cowlitz", 53015, 46.196785, -122.678460, 19.1),
    ("Douglas", 53017, 47.741763, -119.694622, 24.1),
    ("Ferry", 53019, 48.473256, -118.533589, 26.5),
    ("Franklin", 53021, 46.537502, -118.903891, 19.9),
    ("Garfield", 53023, 46.429318, -117.536705, 15.0),
    ("Grant", 53025, 47.213633, -119.467788, 29.2),
    ("Grays Harbor", 53027, 47.113732, -123.826735, 24.6),
    ("Island", 53029, 48.158554, -122.670649, 8.1),
    ("Jefferson", 53031, 47.805708, -123.527057, 24.0),
    ("King", 53033, 47.490552, -121.833977, 26.0),
    ("Kitsap", 53035, 47.639595, -122.649634, 11.2),
    ("Kittitas", 53037, 47.124441, -120.676709, 27.0),
    ("Klickitat", 53039, 45.870446, -120.779305, 24.4),
    ("Lewis", 53041, 46.580071, -122.377444, 27.7),
    ("Lincoln", 53043, 47.582743, -118.417692, 27.1),
    ("Mason", 53045, 47.350832, -123.173103, 17.5),
    ("Okanogan", 53047, 48.548453, -119.742235, 40.9),
    ("Pacific", 53049, 46.556587, -123.782419, 17.2),
    ("Pend Oreille", 53051, 48.543825, -117.232191, 21.1),
    ("Pierce", 53053, 47.051413, -122.153240, 23.0),
    ("San Juan", 53055, 48.507190, -123.103769, 7.4),
    ("Skagit", 53057, 48.493292, -121.815770, 23.5),
    ("Skamania", 53059, 46.024785, -121.953232, 23.0),
    ("Snohomish", 53061, 48.054913, -121.765038, 25.8),
    ("Spokane", 53063, 47.620375, -117.403371, 23.7),
    ("Stevens", 53065, 48.388728, -117.854455, 28.1),
    ("Thurston", 53067, 46.935822, -122.830152, 15.2),
    ("Wahkiakum", 53069, 46.294638, -123.424458, 9.1),
    ("Walla Walla", 53071, 46.254606, -118.480370, 20.1),
    ("Whatcom", 53073, 48.842653, -121.836432, 25.9),
    ("Whitman", 53075, 46.905944, -117.535390, 26.2),
    ("Yakima", 53077, 46.456558, -120.740145, 37.0),
)

WA_COUNTIES: Dict[str, CountyPoint] = {row[0]: CountyPoint(*row) for row in _ROWS}

#: RadioReference county ids (``ctid``) for the counties this project has
#: seen in export filenames. Extend as new exports arrive; unknown ids fall
#: back to whatever county name the file itself carries.
RADIOREFERENCE_CTIDS: Dict[int, str] = {
    2974: "King",
    2984: "Pierce",
    2988: "Snohomish",
}


def county_point(name: Optional[str]) -> Optional[CountyPoint]:
    """Look a county up by name, tolerating ``"King County"`` and case."""
    if not name:
        return None
    key = name.strip()
    if key.lower().endswith(" county"):
        key = key[: -len(" county")].strip()
    for county_name, point in WA_COUNTIES.items():
        if county_name.lower() == key.lower():
            return point
    return None
