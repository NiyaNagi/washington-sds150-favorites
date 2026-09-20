"""Departments get a geo-fence from what the catalog already knows.

A department with no position cannot be excluded by the scanner's location
control, and the plan's distance filter can only call it "here" or
"infinitely far". Invented agencies throughout; the county points are the real
Census ones from :mod:`wasds150.catalog.wa_counties`.
"""
from __future__ import annotations

from wasds150.catalog.locate import (
    MIN_FENCE_MILES,
    fence_for,
    locate_departments,
    washington_fence,
)
from wasds150.models.catalog import CSV_FIELDS, Channel, Department, FavoritesList, System

HOME = (47.6351, -121.9954)


def _ch(label: str, freq: float, lat=None, lon=None) -> Channel:
    return Channel(id=f"{label}:{freq}", label=label, freq_mhz=freq, mode="FM", lat=lat, lon=lon)


def _fl(key: str, *systems: System, counties: str = "", region: str = "") -> FavoritesList:
    row = {name: "" for name in CSV_FIELDS}
    row.update(favorite_key=key, favorite_name=key, counties=counties, region=region)
    favorite = FavoritesList.from_csv_row(row)
    favorite.systems = list(systems)
    return favorite


def _sys(label: str, *departments: Department) -> System:
    return System(id=label, label=label, departments=list(departments))


def _dept(label: str, *channels: Channel, lat=None, lon=None, miles=None) -> Department:
    return Department(id=label, label=label, channels=list(channels), lat=lat, lon=lon, range_miles=miles)


def test_a_departments_own_channels_place_it():
    """A DMR network's regional department carries a position on every row."""
    department = _dept(
        "Puget Sound",
        _ch("Cougar", 441.2875, 47.54, -122.11),
        _ch("Tiger", 440.3375, 47.51, -121.99),
    )
    favorite = _fl("DMRNET", _sys("PNW DMR", department))

    locate_departments([favorite])

    assert department.lat is not None and department.shape == "Circle"
    assert 47.5 < department.lat < 47.56 and -122.2 < department.lon < -121.9
    # Centre plus the spread to the outermost repeater, never below the floor.
    assert department.range_miles >= MIN_FENCE_MILES


def test_a_county_named_in_the_label_places_it():
    favorite = _fl("PS-EAST", _sys("Okanogan County Sheriff", _dept("Channels", _ch("Disp", 155.1))))

    locate_departments([favorite])

    department = favorite.systems[0].departments[0]
    # Okanogan's Census internal point is well east of the Cascades.
    assert department.lat is not None and department.lon < -119.0


def test_several_counties_in_a_label_are_not_one_county():
    """"King, Snohomish, Pierce" is a region; fencing it to whichever county
    sorted first would put a Puget Sound list inside one of them."""
    system = _sys("Yakima Valley Yakima/Kittitas", _dept("Channels", _ch("Disp", 155.1)))
    favorite = _fl("PS-EAST", system)

    fence = fence_for(favorite, system, system.departments[0])

    assert fence is None or not fence.source.startswith("county:")


def test_a_placed_sister_in_the_same_system_places_it():
    placed = _dept("Marysville", _ch("Fire", 154.1), lat=48.05, lon=-122.17, miles=8.0)
    orphan = _dept("Radio Techs", _ch("Techs", 154.2))
    favorite = _fl("PS-SNO", _sys("Sno911", placed, orphan))

    locate_departments([favorite])

    assert orphan.lat is not None and abs(orphan.lat - 48.05) < 0.01


def test_the_lists_own_counties_place_what_nothing_else_does():
    favorite = _fl("PS-KING", _sys("Some Agency", _dept("Ops", _ch("Ops", 155.5))), counties="King")

    locate_departments([favorite])

    department = favorite.systems[0].departments[0]
    assert department.lat is not None and 47.3 < department.lat < 47.7


def test_a_statewide_list_gets_a_statewide_fence_only_for_the_scanner():
    """The scanner's location control wants the circle; the plan already says
    "relevant anywhere" with a selector flag, and a fence that overlaps every
    radius circle would drag the whole state into a catch-all block."""
    def build():
        return _fl(
            "PS-STATE",
            _sys("Nationwide Interop + WA STATE", _dept("Channels", _ch("VCALL", 155.7525))),
            counties="All 39 counties",
            region="Statewide",
        )

    scanner = build()
    locate_departments([scanner])
    fenced = scanner.systems[0].departments[0]
    assert fenced.lat is not None and fenced.range_miles == washington_fence().radius_miles

    plan = build()
    locate_departments([plan], statewide=False)
    assert plan.systems[0].departments[0].lat is None


def test_an_hf_department_keeps_no_fence():
    """Where an 80 m net is worked from is propagation, not geography."""
    favorite = _fl(
        "HAM-HF",
        _sys("HF Nets", _dept("Channels", _ch("WA Traffic Net 80m", 3.567), _ch("PNW ARES 75m", 3.985))),
        counties="King",
    )

    locate_departments([favorite])

    assert favorite.systems[0].departments[0].lat is None


def test_a_department_that_already_has_a_position_is_left_alone():
    department = _dept("Fire", _ch("Disp", 154.1), lat=47.1, lon=-122.2, miles=3.0)
    favorite = _fl("PS-KING", _sys("Agency", department), counties="King")

    locate_departments([favorite])

    assert (department.lat, department.lon, department.range_miles) == (47.1, -122.2, 3.0)


def test_the_counts_say_which_rule_placed_what():
    favorite = _fl(
        "MIXED",
        _sys(
            "Agency",
            _dept("From channels", _ch("A", 155.1, 47.6, -122.0)),
            _dept("Okanogan County ops", _ch("B", 155.2)),
        ),
        counties="King",
    )

    _lists, filled = locate_departments([favorite])

    assert filled.get("channels") == 1 and filled.get("county") == 1
