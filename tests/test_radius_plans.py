"""Radius-filtered channel selection and the location data it depends on."""
from __future__ import annotations

from pathlib import Path

import pytest

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.models.catalog import Channel
from wasds150.models.plan import ChannelSelector
from wasds150.plan.service import resolve_named_plan
from wasds150.plans.ftx1_local import HOME, RADIUS_MILES
from wasds150.util.geo import haversine_miles

SEATTLE = (47.6062, -122.3321)
PORTLAND = (45.5152, -122.6784)


# --------------------------------------------------------------- distance --
def test_haversine_matches_a_known_distance():
    """Seattle to Portland is about 145 statute miles."""
    miles = haversine_miles(*SEATTLE, *PORTLAND)
    assert 140 <= miles <= 150


def test_haversine_is_zero_for_the_same_point():
    assert haversine_miles(*SEATTLE, *SEATTLE) == pytest.approx(0.0, abs=1e-9)


def test_scanner_and_planner_share_one_distance_function():
    """Two copies would drift; the geo-fence and the radius filter must agree."""
    from wasds150.hpe import hpdb

    assert hpdb.haversine_miles(*SEATTLE, *PORTLAND) == haversine_miles(
        *SEATTLE, *PORTLAND
    )


# ---------------------------------------------------------------- filter ---
def _channel(label: str, lat=None, lon=None) -> Channel:
    return Channel(id=label, label=label, freq_mhz=146.52, lat=lat, lon=lon)


def test_within_miles_keeps_a_near_channel():
    selector = ChannelSelector(
        favorite_keys=("X",), within_miles=(SEATTLE[0], SEATTLE[1], 50.0)
    )
    near = _channel("near", lat=47.62, lon=-122.33)
    assert selector.matches("X", "dept", near)


def test_within_miles_drops_a_far_channel():
    selector = ChannelSelector(
        favorite_keys=("X",), within_miles=(SEATTLE[0], SEATTLE[1], 50.0)
    )
    far = _channel("far", lat=PORTLAND[0], lon=PORTLAND[1])
    assert not selector.matches("X", "dept", far)


def test_within_miles_drops_a_channel_with_no_position():
    """Silently keeping unlocated channels would make the filter a no-op.

    A source that omits coordinates would otherwise pass every channel
    through a radius filter untouched, which looks like it worked.
    """
    selector = ChannelSelector(
        favorite_keys=("X",), within_miles=(SEATTLE[0], SEATTLE[1], 50.0)
    )
    assert not selector.matches("X", "dept", _channel("nowhere"))


def test_within_miles_alone_is_a_real_selector():
    """A radius on its own must not count as an empty selector."""
    selector = ChannelSelector(within_miles=(SEATTLE[0], SEATTLE[1], 50.0))
    assert not selector.is_empty()


def test_radius_composes_with_other_criteria():
    selector = ChannelSelector(
        favorite_keys=("X",),
        label_pattern="keep",
        within_miles=(SEATTLE[0], SEATTLE[1], 50.0),
    )
    near_wrong_name = _channel("drop", lat=47.62, lon=-122.33)
    assert not selector.matches("X", "dept", near_wrong_name)


# --------------------------------------------------------- shipped plan ----
@pytest.fixture()
def real_ctx(tmp_path, repo_csv_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return build_context(config, csv_override=repo_csv_path)


def test_local_plan_resolves(real_ctx):
    plan, resolved = resolve_named_plan(real_ctx, "ftx1-local")
    assert plan.radio_id == "ftx1"
    assert resolved.slots_used > 0
    assert resolved.capacity is not None
    assert resolved.slots_used <= resolved.capacity


REPEATER_BLOCKS = {
    "Local 2m Repeaters",
    "Local 70cm Repeaters",
    "Local 6m Repeaters",
}


def test_every_repeater_block_carries_the_radius():
    """A block that forgot its radius would quietly ship the whole state."""
    from wasds150.plans.ftx1_local import FTX1_LOCAL

    seen = set()
    for block in FTX1_LOCAL.blocks:
        if block.label not in REPEATER_BLOCKS:
            continue
        seen.add(block.label)
        for selector in block.selectors:
            assert selector.within_miles == (HOME[0], HOME[1], RADIUS_MILES), (
                f"{block.label} selects without a radius"
            )
    assert seen == REPEATER_BLOCKS


def test_no_other_block_claims_a_radius():
    """HF and calling channels have no position; a radius there drops them all."""
    from wasds150.plans.ftx1_local import FTX1_LOCAL

    for block in FTX1_LOCAL.blocks:
        if block.label in REPEATER_BLOCKS:
            continue
        for selector in block.selectors:
            assert selector.within_miles is None, f"{block.label} filters by radius"


def test_local_plan_repeaters_are_all_inside_the_radius(real_ctx):
    """The whole point of the plan: nothing distant should reach the radio.

    Repeaters arrive from WWARA enrichment, so a bare packaged catalog has
    none. Skip rather than pass vacuously.
    """
    _plan, resolved = resolve_named_plan(real_ctx, "ftx1-local")

    located = {}
    for favorite in real_ctx.catalog.favorites:
        for system in favorite.systems:
            departments = list(system.departments)
            for site in system.sites:
                departments.extend(site.departments)
            for department in departments:
                for channel in department.channels:
                    if channel.lat is not None and channel.freq_mhz:
                        located[(round(channel.freq_mhz, 5), channel.label)] = channel

    checked = 0
    for planned in resolved.channels:
        if planned.block not in REPEATER_BLOCKS:
            continue
        channel = located.get((round(planned.rx_freq_mhz, 5), planned.label))
        if channel is None:
            continue
        checked += 1
        distance = haversine_miles(HOME[0], HOME[1], channel.lat, channel.lon)
        assert distance <= RADIUS_MILES + 0.01, (
            f"{planned.name} is {distance:.1f} mi away, outside the "
            f"{RADIUS_MILES:g} mi radius"
        )
    if checked == 0:
        pytest.skip("no located repeaters in the catalog; run 'sources update'")


def test_local_plan_is_smaller_than_the_statewide_one(real_ctx):
    _plan_a, local = resolve_named_plan(real_ctx, "ftx1-local")
    _plan_b, statewide = resolve_named_plan(real_ctx, "ftx1-wa")
    assert local.slots_used < statewide.slots_used


def test_both_ftx1_plans_are_registered():
    """Two plans for one radio is the point - they are picked from a dropdown."""
    from wasds150.plans import list_plans

    ftx1 = [p for p in list_plans().values() if p.radio_id == "ftx1"]
    assert {p.id for p in ftx1} == {"ftx1-wa", "ftx1-local"}
