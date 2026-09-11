"""BrandMeister repeaters (BMNET) and the NXDN unit ID."""
from wasds150 import station
from wasds150.catalog import brandmeister_snapshot
from wasds150.catalog.brandmeister import BMNET_KEY, NETWORK, favorites_from_snapshot
from wasds150.catalog.dmr_talkgroup_tiers import TIER_CORE, TIER_REGIONAL, channel_tier
from wasds150.catalog.extras import extras_for
from wasds150.fleet.registry import FLEET
from wasds150.radios.registry import get_profile


def _channels(fl):
    return [c for s in fl.systems for d in s.departments for c in d.channels]


def test_snapshot_rows_become_dmr_channels_with_full_identity():
    rows = [(311757, "N7QT", "Redmond", 442.325, 447.325, 1, 47.6746, -122.05393, "2026-09-11",
             ((3153, 2), (31538, 1)))]
    (fl,) = favorites_from_snapshot({3153: "Washington - 10 Minute Limit", 31538: "Washington State ARES"}, rows, "2026-09-11")
    assert fl.favorite_key == BMNET_KEY
    by_tg = {c.dmr_talkgroup: c for c in _channels(fl)}
    washington = by_tg[3153]
    assert (washington.freq_mhz, washington.tx_freq_mhz) == (442.325, 447.325)
    assert (washington.mode, washington.tone, washington.dmr_color_code, washington.dmr_timeslot) == ("DMR", "ColorCode=1", 1, 2)
    assert washington.network == NETWORK and washington.lat is not None
    assert channel_tier(washington) == TIER_CORE
    assert channel_tier(by_tg[31538]) == TIER_REGIONAL


def test_repeater_without_static_talkgroups_adds_no_channels():
    rows = [(312953, "WA7EBH", "Port Angeles", 443.7, 448.7, 1, 48.05, -123.32, "2026-09-11", ())]
    assert favorites_from_snapshot({}, rows, "2026-09-11") == []


def test_committed_snapshot_reaches_the_dmr_radio_only():
    assert brandmeister_snapshot.REPEATERS, "snapshot should not be empty"
    assert BMNET_KEY in {fl.favorite_key for fl in extras_for(get_profile("at-d890uv"))}
    assert BMNET_KEY not in {fl.favorite_key for fl in extras_for(get_profile("td-h9"))}
    channels = _channels(brandmeister_snapshot.favorite())
    assert channels and all(c.mode == "DMR" and c.dmr_talkgroup for c in channels)


def test_the_anytone_checklist_sets_the_nxdn_unit_id():
    assert station.NXDN_ID == 16240 and 0 < station.NXDN_ID <= 65535
    step = FLEET["at-d890uv"].step("set-nxdn-id")
    assert str(station.NXDN_ID) in step.instructions and "Unit ID(Own)" in step.instructions
