"""Selector primitives: key patterns, department exclusion, geo fallback."""
from __future__ import annotations

import pytest

from wasds150.models.catalog import CSV_FIELDS, Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import (
    GEO_DEPARTMENT,
    GEO_EITHER,
    ChannelPlan,
    ChannelSelector,
    PlanBlock,
)
from wasds150.plan.resolve import resolve_plan
from wasds150.radios.registry import get_profile

SEATTLE = (47.6062, -122.3321)
SPOKANE = (47.6588, -117.4260)
NEAR = (47.62, -122.33)


def _channel(label="ch", lat=None, lon=None, freq=146.52) -> Channel:
    return Channel(id=label, label=label, freq_mhz=freq, mode="FM", lat=lat, lon=lon)


def _department(label="Dept", lat=None, lon=None, range_miles=None) -> Department:
    return Department(id=label, label=label, lat=lat, lon=lon, range_miles=range_miles)


def _radius(**kwargs) -> ChannelSelector:
    return ChannelSelector(favorite_keys=("X",), within_miles=(SEATTLE[0], SEATTLE[1], 30.0), **kwargs)


# --------------------------------------------------------------- patterns --
def test_favorite_key_pattern_matches_a_naming_family():
    selector = ChannelSelector(favorite_key_pattern=r"^RRC-")
    assert selector.matches("RRC-KING", "dept", _channel())
    assert selector.matches("rrc-king", "dept", _channel())
    assert not selector.matches("RRWA", "dept", _channel())


def test_favorite_key_pattern_alone_is_a_real_selector():
    assert not ChannelSelector(favorite_key_pattern=".*").is_empty()


def test_exclude_department_pattern_drops_named_departments():
    selector = ChannelSelector(favorite_keys=("RRWA",), exclude_department_pattern=r"Spokane|Walla")
    assert selector.matches("RRWA", "King County", _channel())
    assert not selector.matches("RRWA", "Spokane County", _channel())


def test_exclusions_alone_leave_a_selector_empty():
    """An exclude-only selector would otherwise match the whole catalog."""
    selector = ChannelSelector(exclude_department_pattern="Spokane")
    assert selector.is_empty()
    assert not selector.matches("X", "King", _channel())


def test_unknown_geo_fallback_is_rejected():
    with pytest.raises(ValueError):
        ChannelSelector(geo_fallback="county")


# ------------------------------------------------------------ geo fallback --
def test_default_fallback_still_drops_unlocated_channels():
    fence = _department(lat=SEATTLE[0], lon=SEATTLE[1], range_miles=20)
    assert not _radius().matches("X", "Dept", _channel(), fence)


def test_department_fallback_admits_unlocated_channel_inside_fence():
    fence = _department(lat=SEATTLE[0], lon=SEATTLE[1], range_miles=20)
    assert _radius(geo_fallback=GEO_DEPARTMENT).matches("X", "Dept", _channel(), fence)


def test_department_fallback_uses_fence_radius_for_overlap():
    """A county fence 40 miles out with a 15-mile radius reaches a 30-mile circle."""
    fence_centre = (SEATTLE[0], SEATTLE[1] + 0.85)  # roughly 40 miles east
    touching = _department(lat=fence_centre[0], lon=fence_centre[1], range_miles=15)
    short = _department(lat=fence_centre[0], lon=fence_centre[1], range_miles=5)
    selector = _radius(geo_fallback=GEO_DEPARTMENT)
    assert selector.matches("X", "Dept", _channel(), touching)
    assert not selector.matches("X", "Dept", _channel(), short)


def test_department_fallback_drops_unlocated_channel_far_away():
    fence = _department(lat=SPOKANE[0], lon=SPOKANE[1], range_miles=25)
    assert not _radius(geo_fallback=GEO_DEPARTMENT).matches("X", "Dept", _channel(), fence)


def test_department_fallback_does_not_rescue_a_located_far_channel():
    fence = _department(lat=SEATTLE[0], lon=SEATTLE[1], range_miles=20)
    far = _channel(lat=SPOKANE[0], lon=SPOKANE[1])
    assert not _radius(geo_fallback=GEO_DEPARTMENT).matches("X", "Dept", far, fence)


def test_either_fallback_admits_a_located_channel_in_an_overlapping_fence():
    fence = _department(lat=SEATTLE[0], lon=SEATTLE[1], range_miles=20)
    far = _channel(lat=SPOKANE[0], lon=SPOKANE[1])
    assert _radius(geo_fallback=GEO_EITHER).matches("X", "Dept", far, fence)


def test_fallback_without_a_department_position_drops_the_channel():
    assert not _radius(geo_fallback=GEO_EITHER).matches("X", "Dept", _channel(), _department())
    assert not _radius(geo_fallback=GEO_EITHER).matches("X", "Dept", _channel(), None)


def test_located_near_channel_passes_in_every_mode():
    near = _channel(lat=NEAR[0], lon=NEAR[1])
    for mode in ("channel", "department", "either"):
        assert _radius(geo_fallback=mode).matches("X", "Dept", near)


# ------------------------------------------------------------- resolver ----
def _favorite(key: str, systems) -> FavoritesList:
    row = {name: "" for name in CSV_FIELDS}
    row["favorite_key"] = key
    row["favorite_name"] = key
    favorite = FavoritesList.from_csv_row(row)
    favorite.systems = list(systems)
    return favorite


def test_resolver_hands_the_department_to_the_selector():
    fence = _department("King", lat=SEATTLE[0], lon=SEATTLE[1], range_miles=20)
    fence.channels = [_channel("KC Fire", freq=154.25)]
    far = _department("Spokane", lat=SPOKANE[0], lon=SPOKANE[1], range_miles=20)
    far.channels = [_channel("Spo Fire", freq=154.31)]
    catalog = Catalog(favorites=[_favorite("RRC-TEST", [System(id="s", label="S", departments=[fence, far])])])
    plan = ChannelPlan(
        id="t",
        radio_id="td-h9",
        label="t",
        blocks=(
            PlanBlock(
                label="County",
                selectors=(
                    ChannelSelector(
                        favorite_key_pattern="^RRC-",
                        within_miles=(SEATTLE[0], SEATTLE[1], 30.0),
                        geo_fallback=GEO_DEPARTMENT,
                    ),
                ),
            ),
        ),
    )
    resolved = resolve_plan(plan, catalog, get_profile("td-h9"))
    assert [c.label for c in resolved.channels] == ["KC Fire"]
