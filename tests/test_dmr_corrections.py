"""Corrections to the regional DMR layout where a network's own site disagrees."""
from __future__ import annotations

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.recipes.dmr_corrections import ADDED, SUPERSEDED, correct_network_list


def _dmr(label: str, mhz: float, tg: int, ts: int, cc: int = 2, name: str = "") -> Channel:
    return Channel(
        id=f"{label}-{mhz}", label=label, freq_mhz=mhz, tx_freq_mhz=mhz + 5.0, mode="DMR",
        tone=f"ColorCode={cc}", dmr_color_code=cc, dmr_timeslot=ts, dmr_talkgroup=tg,
        dmr_talkgroup_name=name or label.rsplit(" ", 1)[0], network="SeattleDMR",
    )


def _list(key: str, channels) -> FavoritesList:
    return FavoritesList(
        id=key.lower(), slug=key.lower(), favorite_key=key, favorite_name=key, region="", counties="",
        scenario="", source_type="", system_or_category="", sites_or_coverage="",
        departments_or_channels="", mode="DMR", monitorability="", upgrade_required="", source_url="",
        notes="", systems=[System(id="s", label="S", departments=[
            Department(id="ps", label="Puget Sound", channels=list(channels)),
        ])],
    )


def _channels(fl: FavoritesList):
    return fl.systems[0].departments[0].channels


def test_the_stale_west_tiger_row_goes_and_the_real_one_arrives():
    assert ("BWT", 442.075) in SUPERSEDED
    knw = next(a for a in ADDED if a.code == "KNW")
    source = _list("DMRNET", [
        _dmr("Washington 1 SCE", 440.775, 3153, 1),
        _dmr("King County SCE", 440.775, 333153, 2),
        _dmr("King County BWT", 442.075, 333153, 2),
    ])

    fixed = correct_network_list(source)

    labels = [c.label for c in _channels(fixed)]
    assert "King County BWT" not in labels
    added = [c for c in _channels(fixed) if c.label.endswith(" KNW")]
    assert [c.label for c in added] == ["Washington 1 KNW", "King County KNW"]
    for channel in added:
        assert channel.freq_mhz == knw.rx_mhz and channel.tx_freq_mhz == knw.tx_mhz
        assert channel.dmr_color_code == 2 and channel.tone == "ColorCode=2"
        assert (channel.lat, channel.lon) == (knw.lat, knw.lon)
        assert "seattledmr.org" in channel.notes
    # Talkgroup and timeslot come from the layout it copies.
    assert [(c.dmr_talkgroup, c.dmr_timeslot) for c in added] == [(3153, 1), (333153, 2)]
    # The input is not modified in place.
    assert "King County BWT" in [c.label for c in _channels(source)]


def test_corrections_are_idempotent_and_leave_a_present_repeater_alone():
    source = _list("DMRNET", [
        _dmr("Washington 1 SCE", 440.775, 3153, 1),
        _dmr("Washington 1 KNW", 440.3375, 3153, 1),
    ])
    once = correct_network_list(source)
    twice = correct_network_list(once)
    assert [c.label for c in _channels(once)] == ["Washington 1 SCE", "Washington 1 KNW"]
    assert [c.label for c in _channels(twice)] == [c.label for c in _channels(once)]


def test_other_lists_are_untouched():
    other = _list("BMNET", [_dmr("King County BWT", 442.075, 333153, 2)])
    assert correct_network_list(other) is other


def test_an_analog_channel_on_the_same_frequency_survives():
    analog = Channel(id="a", label="K7NWS Tgr Mtn BWT", freq_mhz=442.075, mode="FM", tone="TONE=C110.9")
    fixed = correct_network_list(_list("DMRNET", [analog, _dmr("Washington 1 SCE", 440.775, 3153, 1)]))
    assert "K7NWS Tgr Mtn BWT" in [c.label for c in _channels(fixed)]
