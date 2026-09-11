"""One name per station, whichever radio programs it."""
from __future__ import annotations

from wasds150.catalog.labels import StationLabels, source_rank
from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.plan.resolve import resolve_plan
from wasds150.plans.template import build_fleet_plan

HOME = (47.6351, -121.9954)
KING = dict(lat=47.49, lon=-121.84, range_miles=30.0)
SPOKANE = dict(lat=47.66, lon=-117.43, range_miles=30.0)


def _fl(key, *departments):
    return FavoritesList(
        id=key.lower(), slug=key.lower(), favorite_key=key, favorite_name=key, region="", counties="", scenario="",
        source_type="", system_or_category="", sites_or_coverage="", departments_or_channels="", mode="",
        monitorability="", upgrade_required="", source_url="", notes="",
        systems=[System(id=f"{key}-s", label=key, departments=list(departments))],
    )


def _dept(ident, label, *channels, **fence):
    return Department(id=ident, label=label, channels=list(channels), **fence)


def _ch(ident, label, freq, **kw):
    return Channel(id=ident, label=label, freq_mhz=freq, **kw)


def _rows(*favorites):
    return [(f.favorite_key, d, c) for f in favorites for s in f.systems for d in s.departments for c in d.channels]


def _only(favorite):
    department = favorite.systems[0].departments[0]
    return department, department.channels[0]


def test_one_station_one_name_whatever_the_list_says_about_mode_or_tone():
    rr = _fl("RRC-KING", _dept("k", "Law", _ch("rr", "Law Enforcement Radio Network", 155.37, mode="FM", tone="TONE=C103.5"), **KING))
    curated = _fl("FL02", _dept("c", "Interop", _ch("fl", "LERN", 155.37, mode="NFM")))
    labels = StationLabels(_rows(rr, curated), home=HOME)
    # the name written for radios wins over the database description
    assert labels.label(*_only(rr)) == labels.label(*_only(curated)) == "LERN"


def test_the_same_frequency_in_two_counties_keeps_two_names():
    king = _fl("RRC-KING", _dept("k", "Fire", _ch("k1", "King Fire Tac", 154.43, mode="FM"), **KING))
    spokane = _fl("RRC-SPOKANE", _dept("s", "Fire", _ch("s1", "Spokane Fire Dispatch", 154.43, mode="FM"), **SPOKANE))
    labels = StationLabels(_rows(king, spokane), home=HOME)
    assert (labels.label(*_only(king)), labels.label(*_only(spokane))) == ("King Fire Tac", "Spokane Fire Dispatch")


def test_a_dmr_talkgroup_keeps_its_own_name():
    network = _fl("DMRNET", _dept("d", "Puget Sound",
        _ch("a", "Local 2 BVV", 147.02, mode="DMR", tone="ColorCode=1", dmr_talkgroup=2, lat=47.7, lon=-122.1),
        _ch("b", "PNW Rgnl BVV", 147.02, mode="DMR", tone="ColorCode=1", dmr_talkgroup=3, lat=47.7, lon=-122.1),
    ))
    labels = StationLabels(_rows(network), home=HOME)
    department = network.systems[0].departments[0]
    assert [labels.label(department, c) for c in department.channels] == ["Local 2 BVV", "PNW Rgnl BVV"]


def test_the_faa_name_wins_and_every_radio_shows_it():
    faa = _fl("FAAAIR", _dept("f", "RNT Renton Muni", _ch("f1", "RNT TWR", 124.7, mode="AM", lat=47.49, lon=-122.21),
                                lat=47.49, lon=-122.21, range_miles=25.0))
    curated = _fl("FL46", _dept("c", "Channels", _ch("c1", "Renton Tower", 124.7, mode="AM")))
    catalog = Catalog(favorites=[curated, faa])
    for radio_id in ("td-h9", "th-d75", "at-d890uv"):
        names = {c.label for c in resolve_plan(build_fleet_plan(radio_id), catalog).channels if c.rx_freq_mhz == 124.7}
        assert names == {"RNT TWR"}, radio_id


def test_source_ranks():
    assert [source_rank(k) for k in ("FAAAIR", "FL01", "PSHAM01", "RRC-KING", "RRWA", "THD75LOCAL")] == [0, 1, 1, 2, 2, 3]
