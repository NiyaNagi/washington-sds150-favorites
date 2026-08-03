"""Tests for wasds150.recipes.systems: the three tiers that turn a matched
fact (or a row's own checked-in free text) into a real
wasds150.models.catalog.System, plus deterministic de-duplication."""
from __future__ import annotations

from wasds150.hpe import hpdb
from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.recipes.systems import (
    dedupe_channels,
    dedupe_systems,
    static_systems_for,
    system_from_hpdb_fact,
    systems_from_flat_facts,
    systems_from_matched_facts,
)
from wasds150.sources.facts import NormalizedFact


def _fl(slug="fl01", favorite_key="FL01", favorite_name="Test List", departments_or_channels="", **kwargs):
    fields = dict(
        id=slug,
        slug=slug,
        favorite_key=favorite_key,
        favorite_name=favorite_name,
        region="Statewide",
        counties="",
        scenario="",
        source_type="",
        system_or_category="",
        sites_or_coverage="",
        departments_or_channels=departments_or_channels,
        mode="FM",
        monitorability="",
        upgrade_required="",
        source_url="",
        notes="",
    )
    fields.update(kwargs)
    return FavoritesList(**fields)


# --------------------------------------------------------------- Tier C ----
def test_static_systems_for_populates_from_explicit_free_text():
    fl = _fl(departments_or_channels="Ch16 156.800(distress);Ch13 156.650")
    systems = static_systems_for(fl)
    assert len(systems) == 1
    channels = systems[0].departments[0].channels
    assert {c.label: c.freq_mhz for c in channels} == {"Ch16": 156.8, "Ch13": 156.65}
    assert systems[0].label == fl.favorite_name


def test_static_systems_for_empty_when_no_explicit_frequency():
    fl = _fl(departments_or_channels="District dispatch (D1 Pierce,D2 King); tactical/car-to-car")
    assert static_systems_for(fl) == []


def test_static_systems_for_applies_curated_seed_when_anchors_present():
    fl = _fl(
        slug="fl65",
        favorite_key="FL65",
        favorite_name="GMRS/FRS + NWAC Backcountry",
        departments_or_channels=(
            "Ch1-7 shared462.5625-462.7125;Ch8-14 FRS-only467.5625-467.7125(0.5W);"
            "Ch15-22 GMRS/FRS462.5500-462.7250;NWAC FRS Ch7(462.7125,CTCSS71.9)"
        ),
    )
    systems = static_systems_for(fl)
    assert len(systems) == 1
    channels = systems[0].departments[0].channels
    # 22 seeded FRS/GMRS channels + the one literal NWAC-labeled channel at
    # the same 462.7125 frequency (kept distinct: dedup keys on label too,
    # since two different labels at the same frequency are not necessarily
    # the same real-world channel entry).
    assert len(channels) == 23
    assert sum(1 for c in channels if c.freq_mhz == 462.7125) == 2


def test_static_systems_for_seed_never_fires_for_unrelated_row_reusing_key():
    fl = _fl(slug="fl02", favorite_key="FL02", departments_or_channels="Bravo Dispatch, [E]-ENCRYPTED")
    assert static_systems_for(fl) == []


def test_static_systems_for_is_deterministic():
    fl = _fl(departments_or_channels="CMD 46.520; RADEF 46.000")
    first = static_systems_for(fl)
    second = static_systems_for(fl)
    assert [s.to_dict() for s in first] == [s.to_dict() for s in second]
    assert first[0].id == second[0].id


def test_static_systems_for_ids_are_stable_across_calls():
    fl = _fl(departments_or_channels="CMD 46.520")
    ids_a = {c.id for s in static_systems_for(fl) for d in s.departments for c in d.channels}
    ids_b = {c.id for s in static_systems_for(fl) for d in s.departments for c in d.channels}
    assert ids_a == ids_b


# ------------------------------------------------------------- dedupe -----
def test_dedupe_channels_by_freq_and_label():
    channels = [
        Channel(id="a", label="Ch16", freq_mhz=156.8),
        Channel(id="b", label="Ch16", freq_mhz=156.8),  # duplicate
        Channel(id="c", label="Ch13", freq_mhz=156.65),
    ]
    result = dedupe_channels(channels)
    assert len(result) == 2
    assert result[0].id == "a"  # first-seen wins


def test_dedupe_systems_by_id_preserves_order():
    s1 = System(id="s1", label="A")
    s2 = System(id="s2", label="B")
    s1_dup = System(id="s1", label="A-again")
    result = dedupe_systems([s1, s2, s1_dup])
    assert [s.id for s in result] == ["s1", "s2"]
    assert result[0].label == "A"  # first-seen wins


# --------------------------------------------------------------- Tier A ----
def test_system_from_hpdb_fact_returns_none_for_non_hpdb_source():
    fact = NormalizedFact(entity_key="x", fact_type="system", source_id="noaa_nwr", raw={})
    assert system_from_hpdb_fact(fact) is None


def test_system_from_hpdb_fact_returns_none_without_records():
    fact = NormalizedFact(entity_key="x", fact_type="system", source_id="sentinel_local", raw={"sid": 1})
    assert system_from_hpdb_fact(fact) is None


def test_system_from_hpdb_fact_converts_real_record_tree(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    trunk_slice = next(s for s in systems if s.kind() == "Trunk")
    raw_records = hpdb.serialize_system_slice(trunk_slice)
    fact = NormalizedFact(
        entity_key="hpdb:TrunkId:6001", fact_type="system", source_id="sentinel_local",
        raw={"sid": 6001, "records": raw_records},
    )
    system = system_from_hpdb_fact(fact)
    assert system is not None
    assert system.label == "Regional P25"
    assert system.sites[0].departments[0].channels[0].tgid == 101


# --------------------------------------------------------------- Tier B ----
def test_systems_from_flat_facts_builds_one_system_with_one_channel_per_fact():
    fl = _fl()
    facts = [
        NormalizedFact(entity_key="noaa:1", fact_type="station", name="NOAA WX Seattle", freq_mhz=162.55, source_id="noaa_nwr"),
        NormalizedFact(entity_key="noaa:2", fact_type="station", name="NOAA WX Yakima", freq_mhz=162.4, source_id="noaa_nwr"),
    ]
    systems = systems_from_flat_facts(fl, facts)
    assert len(systems) == 1
    channels = systems[0].departments[0].channels
    assert {c.freq_mhz for c in channels} == {162.55, 162.4}


def test_systems_from_flat_facts_excludes_facts_without_frequency():
    fl = _fl()
    facts = [NormalizedFact(entity_key="fcc:1", fact_type="system", source_id="fcc_uls", freq_mhz=None)]
    assert systems_from_flat_facts(fl, facts) == []


def test_systems_from_flat_facts_excludes_sentinel_local_facts():
    """sentinel_local facts are handled by Tier A (system_from_hpdb_fact)
    instead -- Tier B must never also turn them into a flat, detail-losing
    channel."""
    fl = _fl()
    facts = [NormalizedFact(entity_key="hpdb:x", fact_type="system", source_id="sentinel_local", freq_mhz=154.28)]
    assert systems_from_flat_facts(fl, facts) == []


def test_systems_from_matched_facts_combines_tier_a_and_tier_b(synthetic_hpdb_state_path):
    fl = _fl()
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    conv_slice = next(s for s in hpdb.segment_systems(doc) if s.kind() == "Conventional")
    hpdb_fact = NormalizedFact(
        entity_key="hpdb:CountyId:5301", fact_type="system", source_id="sentinel_local",
        raw={"records": hpdb.serialize_system_slice(conv_slice)},
    )
    flat_fact = NormalizedFact(entity_key="noaa:1", fact_type="station", name="NOAA WX", freq_mhz=162.55, source_id="noaa_nwr")
    systems = systems_from_matched_facts(fl, [hpdb_fact, flat_fact])
    assert len(systems) == 2
    assert systems[0].label == "King County Public Safety"  # Tier A first
    assert systems[1].departments[0].channels[0].freq_mhz == 162.55  # Tier B
