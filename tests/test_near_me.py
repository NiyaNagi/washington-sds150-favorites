"""Near Me: the SDS150 lists for the car - fenced, each frequency once, only
live channels - and the scanner settings they are installed with."""
from __future__ import annotations

from wasds150.models.catalog import Channel, Department, FavoritesList, Site, System
from wasds150.radios.near_me import build_near_me_lists, list_settings

HOME = (47.6351, -121.9954)
KING = dict(lat=47.49, lon=-121.84, range_miles=30.0)


def _fl(key, *systems, licensed=False):
    return FavoritesList(
        id=key.lower(), slug=key.lower(), favorite_key=key, favorite_name=key, region="", counties="", scenario="",
        source_type="", system_or_category="", sites_or_coverage="", departments_or_channels="", mode="",
        monitorability="", upgrade_required="", source_url="", notes="", systems=list(systems), licensed=licensed,
    )


def _conv(label, *departments):
    return System(id=f"s-{label}", label=label, departments=list(departments))


def _ch(label, freq, **kw):
    return Channel(id=f"c-{label}-{freq}", label=label, freq_mhz=freq, **kw)


def _tg(label, tgid, service, **kw):
    return Channel(id=f"t-{tgid}", label=label, tgid=tgid, service_type=service, **kw)


def _catalog():
    king = Department(id="king-disp", label="Law Dispatch", channels=[
        _ch("KCSO Disp", 155.55, mode="FM", service_type=2),
        _ch("KCSO Tac", 155.61, mode="FM", service_type=7),
        _ch("Encrypted", 155.73, mode="FM", service_type=2, avoid=True),
        _ch("Paging data", 152.0, mode="FM", service_type=2),
        _ch("NOAA Seattle", 162.55, mode="FM", service_type=2),
    ], **KING)
    statewide = Department(id="wa", label="Statewide", channels=[_ch("WSP Tac", 155.37, mode="FM", service_type=2)])
    faa = Department(id="bfi", label="BFI Boeing Fld", channels=[
        _ch("BFI TWR", 118.3, mode="AM", service_type=15, lat=47.53, lon=-122.30),
        _ch("BFI ATIS", 127.75, mode="AM", service_type=15, lat=47.53, lon=-122.30),
    ], lat=47.53, lon=-122.30, range_miles=25.0)
    repeaters = Department(id="rep", label="Analog 2 Meter", channels=[
        _ch("W7DX - Redmond", 146.82, mode="FM", lat=47.69, lon=-122.12),
        _ch("K7NWS - Tiger Mtn", 146.62, mode="FM", lat=47.50, lon=-121.97),
    ], lat=47.6, lon=-122.2, range_miles=90.0)
    calling = Department(id="call", label="Calling", channels=[_ch("National Simplex", 146.52, mode="FM")])
    dmr = Department(id="dmr", label="Puget Sound", channels=[
        _ch("Local 2 BVV", 147.02, mode="DMR", tone="ColorCode=1", lat=47.7, lon=-122.1, dmr_talkgroup=2),
        _ch("PNW Rgnl BVV", 147.02, mode="DMR", tone="ColorCode=1", lat=47.7, lon=-122.1, dmr_talkgroup=3),
    ])
    tiger = dict(lat=47.5, lon=-121.97, range_miles=20.0)
    psern_fire = System(id="psern-a", label="PSERN", sid=11628, sites=[Site(id="s1", label="Tiger", **tiger, departments=[
        Department(id="f", label="Fire", channels=[_tg("Fire Disp", 1377, 3), _tg("Fire Tac", 1383, 8)]),
    ])])
    psern_law = System(id="psern-b", label="PSERN", sid=11628, sites=[
        Site(id="s1", label="Tiger", **tiger, departments=[
            Department(id="l", label="Law", channels=[_tg("KCSO North", 1447, 2), _tg("Encrypted", 1500, 2, avoid=True)]),
        ]),
        Site(id="s9", label="Unfenced", departments=[]),
    ])
    redmond = Department(id="red", label="Local", channels=[_ch("KCSO Dispatch", 155.55, mode="NFM", service_type=2)], **KING)
    return [
        _fl("RRC-KING", _conv("King", king), licensed=True),
        _fl("RRWA", _conv("WA", statewide)),
        _fl("FAAAIR", _conv("FAA", faa)),
        _fl("PSHAM01", _conv("Ham", repeaters)),
        _fl("HAM01", _conv("Band plan", calling)),
        _fl("DMRNET", _conv("DMR", dmr)),
        _fl("FL09a", psern_fire),
        _fl("FL09b", psern_law),
        _fl("KC29", _conv("Redmond", redmond)),  # the county dispatch channel again
    ]


def _lists():
    return {fl.favorite_key: fl for fl in build_near_me_lists(_catalog(), home=HOME)}


def _conventional(fl):
    return [c for s in fl.systems for d in s.departments for c in d.channels]


def _talkgroups(fl):
    return {c.tgid: c.label for s in fl.systems for site in s.sites for d in site.departments for c in d.channels}


def test_the_lists_come_in_quick_key_order_and_empty_ones_are_left_out():
    lists = build_near_me_lists(_catalog(), home=HOME)
    assert [fl.favorite_key for fl in lists] == ["NM-PS", "NM-TAC", "NM-AIR", "NM-HAM"]
    assert lists[0].licensed  # built from RadioReference rows


def test_public_safety_is_fenced_live_and_each_frequency_once():
    lists = _lists()
    departments = [d for s in lists["NM-PS"].systems for d in s.departments]
    # One channel for the station, named as every radio names it: the curated
    # list's name wins over the database's, FM and NFM notwithstanding.
    assert [(d.label, [c.label for c in d.channels]) for d in departments] == [("King: Law Dispatch", ["KCSO Dispatch"])]
    assert (departments[0].lat, departments[0].lon, departments[0].range_miles) == (47.49, -121.84, 30.0)
    # encrypted, data, NOAA and the unfenced statewide row are gone; tac has its own list
    assert [c.label for c in _conventional(lists["NM-TAC"])] == ["KCSO Tac"]
    everywhere = [c.freq_mhz for fl in lists.values() for c in _conventional(fl)]
    assert everywhere.count(155.55) == 1


def test_the_same_frequency_in_another_county_is_another_station():
    spokane = Department(id="spo", label="Law Dispatch", channels=[_ch("Spokane SO", 155.55, mode="FM", service_type=2)],
                         lat=47.66, lon=-117.43, range_miles=30.0)
    catalog = _catalog() + [_fl("RRC-SPOKANE", _conv("Spokane", spokane))]
    lists = {fl.favorite_key: fl for fl in build_near_me_lists(catalog, home=HOME)}
    assert sorted(c.label for c in _conventional(lists["NM-PS"]) if c.freq_mhz == 155.55) == ["KCSO Dispatch", "Spokane SO"]


def test_copies_with_different_tones_get_open_squelch():
    a = Department(id="a", label="A", channels=[_ch("Agency A", 155.1, mode="FM", service_type=2, tone="TONE=C103.5")], **KING)
    b = Department(id="b", label="B", channels=[_ch("Agency B", 155.1, mode="FM", service_type=2, tone="TONE=C123.0")], **KING)
    lists = {fl.favorite_key: fl for fl in build_near_me_lists([_fl("RRC-KING", _conv("King", a, b))], home=HOME)}
    [channel] = [c for c in _conventional(lists["NM-PS"]) if c.freq_mhz == 155.1]
    assert channel.tone == ""  # hears both agencies


def test_air_keeps_the_towers_and_drops_broadcasts_that_never_stop():
    assert [c.label for c in _conventional(_lists()["NM-AIR"])] == ["BFI TWR"]


def test_ham_repeaters_are_fenced_where_they_stand_and_a_dmr_repeater_is_one_entry():
    ham = _lists()["NM-HAM"]
    departments = [d for s in ham.systems for d in s.departments]
    labels = {c.label for d in departments for c in d.channels}
    assert labels == {"W7DX - Redmond", "K7NWS - Tiger Mtn", "BVV", "National Simplex"}
    [dmr] = [c for d in departments for c in d.channels if c.mode == "DMR"]
    assert dmr.label == "BVV" and dmr.service_type == 13
    fenced = [d for d in departments if d.lat is not None]
    assert all(d.range_miles >= 30.0 for d in fenced)
    assert [d.label for d in departments if d.lat is None] == ["Ham - Anywhere"]  # the national calling channel


def test_copies_of_a_trunked_system_merge_and_split_by_service():
    lists = _lists()
    assert _talkgroups(lists["NM-PS"]) == {1377: "Fire Disp", 1447: "KCSO North"}
    assert _talkgroups(lists["NM-TAC"]) == {1383: "Fire Tac"}
    [system] = [s for s in lists["NM-PS"].systems if s.sites]
    assert system.sid == 11628 and [site.label for site in system.sites] == ["Tiger"]


def test_near_me_lists_lead_on_quick_keys_and_everything_else_stays_quiet():
    favorites = build_near_me_lists(_catalog(), home=HOME) + _catalog()
    settings = list_settings(favorites)
    ps, tac, old = settings["NM-PS"], settings["NM-TAC"], settings["RRC-KING"]
    assert (ps.monitor, ps.quick_key, ps.location_control, ps.lead) == (True, 1, True, True)
    assert (tac.monitor, tac.quick_key) == (False, 2)
    assert (old.monitor, old.location_control, old.lead) == (False, False, False)
