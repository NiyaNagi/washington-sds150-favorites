"""Repeater-coordination records stay in their own lists.

WWARA and IACC once filled a "Channels" department of every list whose text
mentioned "amateur", "ham" or "IACC", and every rollup copied them again.
See wasds150.recipes.systems.strip_coordinator_copies.
"""
import copy

from wasds150.models.catalog import CSV_FIELDS, Catalog, Channel, Department, FavoritesList, System
from wasds150.recipes.systems import COORDINATOR_HOMES, strip_coordinator_copies, systems_from_flat_facts
from wasds150.sources.facts import NormalizedFact
from wasds150.util.hashing import stable_id


def _fl(key, *systems):
    row = {name: "" for name in CSV_FIELDS}
    row.update(favorite_key=key, favorite_name=f"{key} list")
    favorite = FavoritesList.from_csv_row(row)
    favorite.systems = list(systems)
    return favorite


def _fact(source, name, freq, key):
    return NormalizedFact(entity_key=key, fact_type="coordination", name=name, freq_mhz=freq, mode="FM", source_id=source)


def _labels(catalog, key):
    favorite = next(f for f in catalog.favorites if f.favorite_key == key)
    return sorted(c.label for s in favorite.systems for d in s.departments for c in d.channels)


def test_a_coordinators_records_go_only_to_its_home_list_in_a_system_of_their_own():
    facts = [
        _fact("iacc", "N7RHT (Leavenworth, Chelan Co.)", 146.78, "iacc:1"),
        _fact("wwara", "WW7CH (Ashford)", 146.78, "wwara:2"),
        _fact("noaa_nwr", "KHB60 Seattle", 162.55, "noaa:3"),
    ]
    # A mountain list that mentions IACC keeps only what is not a repeater.
    mountain = systems_from_flat_facts(_fl("FL37"), facts)
    assert [[c.label for d in s.departments for c in d.channels] for s in mountain] == [["KHB60 Seattle"]]
    home = systems_from_flat_facts(_fl("FL60"), facts)
    by_system = {s.label: [c.label for d in s.departments for c in d.channels] for s in home}
    assert by_system == {"FL60 list": ["KHB60 Seattle"], "FL60 list - Coordinated": ["N7RHT (Leavenworth, Chelan Co.)"]}
    # WWARA's home rebuilds from its own records, so no aggregate ever takes them.
    assert COORDINATOR_HOMES["wwara"] == "PSHAM01"


def test_copies_already_in_a_catalog_come_out_of_every_list_and_rollup():
    aggregate = System(id=stable_id("fl51:public-facts", kind="system"), label="Satellites", departments=[Department(
        id="d", label="Channels", channels=[
            Channel(id="a", label="WW7CH (Ashford)", freq_mhz=146.78, tone="TONE=C103.5"),
            Channel(id="b", label="ISS [FM]", freq_mhz=145.8),
            Channel(id="c", label="NOAA Seattle", freq_mhz=162.55),
        ])])
    curated = System(id="fl60:static", label="Curated", departments=[Department(
        id="e", label="Repeaters", channels=[Channel(id="f", label="WW7CH (Ashford)", freq_mhz=146.78)])])
    coordination = System(id=stable_id("fl60:coordination", kind="system"), label="IACC", departments=[Department(
        id="g", label="Coordinated Repeaters", channels=[Channel(id="h", label="N7RHT (Leavenworth)", freq_mhz=146.78)])])
    catalog = Catalog(favorites=[
        _fl("FL51", aggregate),
        _fl("FL60", curated, coordination),
        _fl("OUT01", copy.deepcopy(aggregate)),  # a rollup's copy of FL51's system
    ])
    assert strip_coordinator_copies(catalog) == 2
    # The satellite and weather channels stay; only the repeater copies go.
    assert _labels(catalog, "FL51") == ["ISS [FM]", "NOAA Seattle"]
    assert _labels(catalog, "OUT01") == ["ISS [FM]", "NOAA Seattle"]
    # Curated systems and the coordinator's own system are not aggregates.
    assert _labels(catalog, "FL60") == ["N7RHT (Leavenworth)", "WW7CH (Ashford)"]
