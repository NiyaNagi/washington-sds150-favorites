"""Nearest-first blocks and filling a radio's spare slots."""
from __future__ import annotations

from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import SORT_NEAREST, ChannelPlan, ChannelSelector, PlanBlock
from wasds150.plan.resolve import resolve_plan

HOME = (47.6351, -121.9954)
MILE = 1 / 69.0  # degrees of latitude


def _favorite(key, *departments):
    return FavoritesList(
        id=key.lower(), slug=key.lower(), favorite_key=key, favorite_name=key, region="", counties="", scenario="",
        source_type="", system_or_category="", sites_or_coverage="", departments_or_channels="", mode="",
        monitorability="", upgrade_required="", source_url="", notes="",
        systems=[System(id=f"{key}-s", label=key, departments=list(departments))],
    )


def _north(miles):
    return HOME[0] + miles * MILE, HOME[1]


def _at(label, freq, miles, **kw):
    lat, lon = _north(miles)
    return Channel(id=label, label=label, freq_mhz=freq, mode="FM", lat=lat, lon=lon, **kw)


def _plan(*blocks, reserve=0, fill=True):
    return ChannelPlan(id="t", radio_id="td-h9", label="t", blocks=tuple(blocks), reserve_slots=reserve,
                       home=HOME, radius_miles=60.0, fill_to_capacity=fill)


def _labels(resolved):
    return [c.label for c in resolved.channels]


def test_a_county_row_ranks_by_its_fence_and_dispatch_comes_first():
    near_lat, near_lon = _north(10)
    far_lat, far_lon = _north(40)
    near = Department(id="n", label="Near county", lat=near_lat, lon=near_lon, range_miles=20, channels=[
        Channel(id="tac", label="Tac", freq_mhz=155.1, mode="FM", service_type=7),
        Channel(id="disp", label="Dispatch", freq_mhz=155.9, mode="FM", service_type=2),
    ])
    far = Department(id="f", label="Far county", lat=far_lat, lon=far_lon, range_miles=20, channels=[
        Channel(id="far", label="Far dispatch", freq_mhz=154.0, mode="FM", service_type=2),
    ])
    block = PlanBlock("PS", selectors=(ChannelSelector(favorite_keys=("RRC-X",)),), sort=SORT_NEAREST)
    resolved = resolve_plan(_plan(block, fill=False), Catalog(favorites=[_favorite("RRC-X", far, near)]))
    assert _labels(resolved) == ["Dispatch", "Tac", "Far dispatch"]
    assert [round(c.distance_miles) for c in resolved.channels] == [10, 10, 40]


def test_anywhere_rows_count_as_here_and_other_unlocated_rows_as_farthest():
    plan_rows = Department(id="p", label="Plan", channels=[Channel(id="16", label="Marine 16", freq_mhz=156.8, mode="FM")])
    mystery = Department(id="m", label="Mystery", channels=[Channel(id="?", label="Mystery", freq_mhz=156.3, mode="FM")])
    port = Department(id="o", label="Ports", channels=[_at("Port Ops", 156.6, 20)])
    block = PlanBlock("Marine", sort=SORT_NEAREST, selectors=(
        ChannelSelector(favorite_keys=("PLAN",), anywhere=True),
        ChannelSelector(favorite_keys=("OTHER",)),
    ))
    catalog = Catalog(favorites=[_favorite("OTHER", mystery, port), _favorite("PLAN", plan_rows)])
    assert _labels(resolve_plan(_plan(block, fill=False), catalog)) == ["Marine 16", "Port Ops", "Mystery"]


def _repeaters():
    return Catalog(favorites=[_favorite("REP", Department(id="r", label="Repeaters", channels=[
        _at("5 mi", 146.64, 5), _at("30 mi", 146.70, 30), _at("90 mi", 146.76, 90), _at("200 mi", 146.82, 200),
    ]))])


def _repeater_block(**kw):
    return PlanBlock("Repeaters", sort=SORT_NEAREST, limit=1, fill=True,
                     selectors=(ChannelSelector(favorite_keys=("REP",), within_miles=(HOME[0], HOME[1], 60.0)),), **kw)


def test_spare_slots_take_the_next_nearest_and_the_far_ones_are_not_scanned():
    # td-h9 holds 199; a reserve of 196 leaves three slots for the test
    resolved = resolve_plan(_plan(_repeater_block(), reserve=196), _repeaters())
    assert _labels(resolved) == ["5 mi", "30 mi", "90 mi"]
    assert [c.skip_scan for c in resolved.channels] == [False, False, True]
    assert any("filled 2 spare slot" in w for w in resolved.warnings)


def test_a_fill_limit_caps_the_block_and_no_fill_keeps_the_budget():
    assert _labels(resolve_plan(_plan(_repeater_block(fill_limit=2), reserve=196), _repeaters())) == ["5 mi", "30 mi"]
    assert _labels(resolve_plan(_plan(_repeater_block(), reserve=196, fill=False), _repeaters())) == ["5 mi"]
