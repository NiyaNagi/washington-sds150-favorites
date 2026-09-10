"""Talkgroup tiers for DMR scan ordering."""
from __future__ import annotations

from wasds150.catalog.atd890_dmr import favorites as dmr_favorites
from wasds150.catalog.dmr_talkgroup_tiers import (
    TIER_CORE,
    TIER_REGIONAL,
    TIER_TEST,
    TIER_WIDE,
    TIERS,
    channel_tier,
    talkgroup_tier,
)
from wasds150.models.catalog import Channel


def _talkgroup_channels():
    for favorite in dmr_favorites():
        for system in favorite.systems:
            departments = list(system.departments) + [d for site in system.sites for d in site.departments]
            for department in departments:
                for channel in department.channels:
                    if channel.dmr_talkgroup is not None:
                        yield channel


def test_one_example_per_tier():
    assert talkgroup_tier("PNWDigital", "Washington 1", 3153) == TIER_CORE
    assert talkgroup_tier("SeattleDMR", "King County", 333153) == TIER_CORE
    assert talkgroup_tier("PNWDigital", "Oregon 1", 3141) == TIER_REGIONAL
    assert talkgroup_tier("PNWDigital", "Idaho 1", 3116) == TIER_WIDE
    assert talkgroup_tier("PNWDigital", "Parrot 1", 9998) == TIER_TEST


def test_a_shared_id_is_ranked_by_network_and_name():
    """TG 3166 is Metro 2 on PNWDigital and Local 2 on SeattleDMR."""
    assert talkgroup_tier("PNWDigital", "Metro 2", 3166) == TIER_CORE
    assert talkgroup_tier("SeattleDMR", "Local 2", 3166) == TIER_CORE
    assert talkgroup_tier("Brandmeister", "Local 2", 3166) == TIER_WIDE


def test_test_groups_on_unknown_networks_are_recognised_by_name():
    assert talkgroup_tier("Brandmeister", "Parrot", 9990) == TIER_TEST
    assert talkgroup_tier("Brandmeister", "Audio Test", 9999) == TIER_TEST


def test_a_bare_colour_code_row_is_wide_area():
    assert talkgroup_tier("PNWDigital", "", None) == TIER_WIDE
    assert channel_tier(Channel(id="c", label="rpt", freq_mhz=440.0, mode="DMR")) == TIER_WIDE


def test_every_shipped_talkgroup_has_a_tier_and_the_calling_groups_are_core():
    seen = {}
    for channel in _talkgroup_channels():
        tier = channel_tier(channel)
        assert tier in TIERS
        seen[(channel.network, channel.dmr_talkgroup_name)] = tier
    assert seen[("PNWDigital", "PNW 1")] == TIER_CORE
    assert seen[("PNWDigital", "Washington 2")] == TIER_CORE
    assert seen[("SeattleDMR", "Seattle 1")] == TIER_CORE
    assert seen[("PNWDigital", "Audio Test 2")] == TIER_TEST
