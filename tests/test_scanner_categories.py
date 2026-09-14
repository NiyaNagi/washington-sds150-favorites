from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.fleet.service import scanner_favorites
from wasds150.models.catalog import Channel, Department, FavoritesList, Site, System
from wasds150.radios.near_me import NEAR_ME
from wasds150.radios.scanner_categories import (
    CATEGORIES,
    DISPLAY_WIDTH,
    NEAR_ME_NAMES,
    category_for,
    compact_lists,
    is_retired_name,
    list_settings,
)


def _fl(key, *systems):
    return FavoritesList(
        id=key, slug=key.lower(), favorite_key=key, favorite_name=f"{key} list", region="r", counties="c",
        scenario="s", source_type="t", system_or_category="", sites_or_coverage="", departments_or_channels="",
        mode="FM", monitorability="", upgrade_required="", source_url="", notes="", systems=list(systems),
    )


def _conv(label, *freqs):
    channels = [Channel(id=f"c-{label}-{f}", label=f"{label} {f}", freq_mhz=f, mode="FM") for f in freqs]
    return System(id=f"sys-{label}", label=label, departments=[Department(id=f"d-{label}", label=label, channels=channels)])


def _trunk(sid, site, group, *tgids):
    channels = [Channel(id=f"tg-{group}-{t}", label=f"TG {t}", tgid=t) for t in tgids]
    department = Department(id=f"td-{group}", label=group, channels=channels)
    return System(id=f"t-{group}", label="PSERN", sid=sid, tech="P25Standard", wacn="BEE00",
                  sites=[Site(id=f"s-{group}", label=site, lat=47.6, lon=-122.0, departments=[department])])


def test_names_fit_the_scanner_and_quick_keys_do_not_collide():
    names = [c.name for c in CATEGORIES] + list(NEAR_ME_NAMES.values())
    assert all(len(name) <= DISPLAY_WIDTH and name.isascii() for name in names)
    assert len(set(names)) == len(names)
    keys = [c.quick_key for c in CATEGORIES] + [spec.quick_key for spec in NEAR_ME]
    assert len(set(keys)) == len(keys) and all(0 < key < 100 for key in keys)


def test_copies_of_one_trunked_system_become_one_system():
    [king] = compact_lists([
        _fl("KC29", _trunk(1234, "Tiger", "Redmond", 1, 2)),
        _fl("KC31", _trunk(1234, "Tiger", "Sammamish", 2, 3), _conv("City", 155.1)),
        _fl("RRC-KING", _conv("County", 155.1, 460.2)),
    ])
    assert (king.favorite_key, king.favorite_name) == ("PS-KING", "PS King County")
    [trunk] = [s for s in king.systems if s.sites]
    assert len(trunk.sites) == 1
    assert sorted(c.tgid for d in trunk.sites[0].departments for c in d.channels) == [1, 2, 3]
    assert sorted(c.freq_mhz for s in king.systems for d in s.departments for c in d.channels) == [155.1, 460.2]


def test_near_me_leads_categories_follow_and_unknown_lists_pass_through():
    lists = compact_lists([_fl("NM-PS", _conv("Near", 155.5)), _fl("FL01", _conv("SAR", 155.16)),
                           _fl("ZZ99", _conv("Other", 151.1))])
    assert [f.favorite_key for f in lists] == ["NM-PS", "PS-STATE", "ZZ99"]
    settings = list_settings(lists)
    assert (settings["NM-PS"].name, settings["NM-PS"].quick_key, settings["NM-PS"].monitor) == ("NM Public Safety", 1, True)
    state = settings["PS-STATE"]
    assert (state.name, state.quick_key, state.monitor, state.lead) == ("PS Statewide", 17, False, True)
    assert settings["ZZ99"].name is None and not settings["ZZ99"].monitor


def test_only_names_an_earlier_install_generated_are_retired():
    assert is_retired_name("FL01 - WA SAR & Mutual Aid")
    assert is_retired_name("KC29 - Redmond Local")
    assert is_retired_name("RRC-GRAYS HARBOR - RadioReference - Grays Harbor County")
    assert not is_retired_name("NM-PS - Public Safety")
    assert not is_retired_name("PS King County")
    assert not is_retired_name("My own list")


def test_the_ftx1_import_is_spread_by_service_and_its_old_list_is_retired():
    ftx = _fl("FTX01", _conv("Mixed", 146.96, 156.75, 464.825))
    lists = {f.favorite_key: f for f in compact_lists([ftx])}

    def freqs(key):
        return sorted(c.freq_mhz for s in lists[key].systems for d in s.departments for c in d.channels)

    assert (freqs("HAM-RPT"), freqs("MAR"), freqs("BIZ")) == ([146.96], [156.75], [464.825])
    assert "HAM-FTX" not in lists and all(c.name != "HAM FTX-1 Import" for c in CATEGORIES)
    assert is_retired_name("HAM FTX-1 Import")


def test_every_list_the_scanner_is_loaded_with_has_a_category(tmp_path):
    config = AppConfig(home=tmp_path)
    config.ensure_dirs()
    favorites = scanner_favorites(build_context(config), near_me=False, compact=False)
    assert [f.favorite_key for f in favorites if category_for(f.favorite_key) is None] == []
