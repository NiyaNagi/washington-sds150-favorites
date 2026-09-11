"""Radio-native catalog modules, handed out by capability."""
from __future__ import annotations

from wasds150.catalog.extras import extra_keys_for, extras_for
from wasds150.plan.service import _extra_favorites
from wasds150.radios.registry import get_profile


def test_the_two_radios_that_had_extras_get_the_same_lists_in_the_same_order():
    """Order matters: ties in frequency-sorted blocks keep catalog order."""
    assert extra_keys_for(get_profile("th-d75")) == ["THD75BC", "THD75LOCAL", "THD75USER", "THD75WWARA"]
    assert extra_keys_for(get_profile("at-d890uv")) == ["THD75BC", "THD75WWARA", "ATD890LOCAL", "DMRNET", "BMNET"]


def test_other_radios_get_what_their_capabilities_allow():
    # Both receive FM broadcast; neither decodes DMR; the FTX-1's digital
    # voice is C4FM, so the D-STAR table is not for it.
    assert extra_keys_for(get_profile("td-h9")) == ["THD75BC", "THD75WWARA"]
    assert extra_keys_for(get_profile("ftx1")) == ["THD75BC", "THD75WWARA"]


def test_plan_service_delegates_to_the_capability_rules():
    keys = [favorite.favorite_key for favorite in _extra_favorites("th-d75")]
    assert keys == ["THD75BC", "THD75LOCAL", "THD75USER", "THD75WWARA"]


def test_dmr_radios_receive_the_network_layout():
    keys = [favorite.favorite_key for favorite in extras_for(get_profile("at-d890uv"))]
    assert keys[:3] == ["THD75BC", "THD75WWARA", "ATD890LOCAL"]
    assert "DMRNET" in keys
