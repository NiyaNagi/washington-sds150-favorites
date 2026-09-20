"""Corrections to the regional DMR layout where a network's own site disagrees."""
from __future__ import annotations

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.recipes.dmr_corrections import (
    ADDED,
    PAIRS,
    SUPERSEDED,
    correct_color_codes,
    correct_network_list,
    correct_network_lists,
    correct_pairs,
)


def _dmr(
    label: str, mhz: float, tg: int, ts: int, cc: int = 2, name: str = "",
    network: str = "SeattleDMR",
) -> Channel:
    return Channel(
        id=f"{label}-{mhz}", label=label, freq_mhz=mhz, tx_freq_mhz=mhz + 5.0, mode="DMR",
        tone=f"ColorCode={cc}", dmr_color_code=cc, dmr_timeslot=ts, dmr_talkgroup=tg,
        dmr_talkgroup_name=name or label.rsplit(" ", 1)[0], network=network,
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


def _pnw(label: str, tg: int, ts: int, name: str = "") -> Channel:
    """A Cougar UHF row: the PNWDigital layout both West Tiger sites copy."""
    return _dmr(label, 441.2875, tg, ts, cc=1, name=name, network="PNWDigital")


def test_west_tiger_is_the_pnwdigital_machine_its_operator_publishes():
    assert ("BWT", 442.075) in SUPERSEDED
    stu = next(a for a in ADDED if a.code == "STU")
    stv = next(a for a in ADDED if a.code == "STV")
    source = _list("DMRNET", [
        _pnw("Washington 1 BVC", 3153, 1),
        _pnw("Metro 2 BVC", 3166, 2),
        # On Cougar's deck but not on either West Tiger deck.
        _pnw("Hawaii 1 BVC", 3115, 2),
        _dmr("King County BWT", 442.075, 333153, 2),
    ])

    fixed = correct_network_list(source)

    labels = [c.label for c in _channels(fixed)]
    assert "King County BWT" not in labels
    # Colour code 1, not the 2 that SeattleDMR and WWARA's extract carry.
    for code, added in (("STU", stu), ("STV", stv)):
        rows = [c for c in _channels(fixed) if c.label.endswith(f" {code}")]
        assert [c.label for c in rows] == [f"Washington 1 {code}", f"Metro 2 {code}"]
        assert [(c.dmr_talkgroup, c.dmr_timeslot) for c in rows] == [(3153, 1), (3166, 2)]
        for channel in rows:
            assert channel.freq_mhz == added.rx_mhz and channel.tx_freq_mhz == added.tx_mhz
            assert channel.dmr_color_code == 1 and channel.tone == "ColorCode=1"
            assert (channel.lat, channel.lon) == (added.lat, added.lon)
            assert channel.network == "PNWDigital"
            assert "pnwdigital.net" in channel.notes
    # A talkgroup the machine's own deck does not list is never invented onto it.
    assert not [c for c in _channels(fixed) if c.dmr_talkgroup == 3115 and c.label.endswith(("STU", "STV"))]
    # The input is not modified in place.
    assert "King County BWT" in [c.label for c in _channels(source)]


def test_an_off_air_repeater_leaves_the_layout():
    assert ("SHR", 440.125) in SUPERSEDED
    source = _list("DMRNET", [
        _pnw("Washington 1 BVC", 3153, 1),
        _dmr("Washington 1 SHR", 440.125, 3153, 1, cc=1, network="PNWDigital"),
    ])
    assert "Washington 1 SHR" not in [c.label for c in _channels(correct_network_list(source))]


def test_corrections_are_idempotent_and_leave_a_present_repeater_alone():
    source = _list("DMRNET", [
        _pnw("Washington 1 BVC", 3153, 1),
        _dmr("Washington 1 STU", 440.3375, 3153, 1, cc=1, network="PNWDigital"),
        _dmr("Washington 1 STV", 146.5, 3153, 1, cc=1, network="PNWDigital"),
    ])
    once = correct_network_list(source)
    twice = correct_network_list(once)
    assert [c.label for c in _channels(once)] == [
        "Washington 1 BVC", "Washington 1 STU", "Washington 1 STV",
    ]
    assert [c.label for c in _channels(twice)] == [c.label for c in _channels(once)]


def test_a_repeater_that_moved_takes_its_new_pair_in_any_list():
    assert ("BVV", 147.02) in PAIRS and ("WA7DMR", 147.02) in PAIRS
    network = _dmr("Washington 1 BVV", 147.02, 3153, 1, cc=1, network="PNWDigital")
    coordinated = Channel(id="w", label="WA7DMR - Cougar Mtn", freq_mhz=147.02,
                          tx_freq_mhz=147.62, mode="DMR", tone="ColorCode=1")
    elsewhere = Channel(id="o", label="NM7R - Cathlamet", freq_mhz=147.02,
                        tx_freq_mhz=147.62, mode="FM", tone="TONE=C118.8")
    source = _list("PSHAM01", [network, coordinated, elsewhere])

    moved, also, untouched = _channels(correct_pairs(source))

    for channel in (moved, also):
        assert (channel.freq_mhz, channel.tx_freq_mhz) == (147.025, 147.625)
        assert "147.0250/147.6250" in channel.notes
    # Another machine on the pair the repeater left keeps it.
    assert (untouched.freq_mhz, untouched.tx_freq_mhz) == (147.02, 147.62)
    assert _channels(source)[0].freq_mhz == 147.02  # input untouched
    # Already moved, or nothing on the pair: the same object comes back.
    once = correct_pairs(source)
    assert correct_pairs(once) is once
    nothing = _list("PSHAM01", [elsewhere])
    assert correct_pairs(nothing) is nothing


def test_other_lists_are_untouched():
    other = _list("BMNET", [_dmr("King County BWT", 442.075, 333153, 2)])
    assert correct_network_list(other) is other


def test_a_coordinated_colour_code_is_corrected_in_any_list():
    wrong = Channel(id="n7qt", label="N7QT - Redmond", freq_mhz=442.325, tx_freq_mhz=447.325,
                    mode="DMR", tone="ColorCode=2")
    analog = Channel(id="fm", label="N7QT", freq_mhz=442.325, mode="FM", tone="TONE=C103.5")
    source = _list("PSHAM01", [wrong, analog])

    fixed = correct_color_codes(source)

    dmr, fm = _channels(fixed)
    assert dmr.tone == "ColorCode=1" and dmr.dmr_color_code == 1
    assert fm.tone == "TONE=C103.5"  # only the DMR row
    assert _channels(source)[0].tone == "ColorCode=2"  # input untouched
    # Already right, or not the station: the same object comes back.
    assert correct_color_codes(fixed) is fixed
    other = _list("PSHAM01", [Channel(id="x", label="K7XX", freq_mhz=442.325, mode="DMR", tone="ColorCode=2")])
    assert correct_color_codes(other) is other
    # The combined entry point applies both kinds of correction.
    assert _channels(correct_network_lists([source])[0])[0].tone == "ColorCode=1"


def test_an_analog_channel_on_the_same_frequency_survives():
    analog = Channel(id="a", label="K7NWS Tgr Mtn BWT", freq_mhz=442.075, mode="FM", tone="TONE=C110.9")
    fixed = correct_network_list(_list("DMRNET", [analog, _dmr("Washington 1 SCE", 440.775, 3153, 1)]))
    assert "K7NWS Tgr Mtn BWT" in [c.label for c in _channels(fixed)]
