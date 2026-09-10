"""Structure hash, per-list catalog deltas and the update store."""
from __future__ import annotations

import copy

import pytest

from wasds150.catalog.delta import (
    CatalogDelta,
    UpdateStore,
    channel_fingerprint,
    compute_delta,
    structure_hash,
)
from wasds150.models.catalog import (
    CSV_FIELDS,
    Catalog,
    Channel,
    Department,
    FavoritesList,
    System,
    TrunkFrequency,
)


def _favorite(key: str, channels=(), trunk=()) -> FavoritesList:
    row = {name: "" for name in CSV_FIELDS}
    row["favorite_key"] = key
    row["favorite_name"] = key
    favorite = FavoritesList.from_csv_row(row)
    department = Department(id=f"{key}-d", label="Ops", channels=list(channels))
    favorite.systems = [
        System(
            id=f"{key}-s",
            label=f"{key} system",
            departments=[department],
            trunk_frequencies=list(trunk),
        )
    ]
    return favorite


def _ch(cid: str, freq: float, label=None, **kw) -> Channel:
    return Channel(id=cid, label=label or cid, freq_mhz=freq, mode="FM", **kw)


def _catalog() -> Catalog:
    return Catalog(
        favorites=[
            _favorite("A", [_ch("a1", 146.52), _ch("a2", 147.0)]),
            _favorite("B", [_ch("b1", 155.0)]),
        ]
    )


# ------------------------------------------------------------ fingerprints --
def test_fingerprint_changes_with_frequency_but_not_notes():
    base = _ch("x", 146.52)
    assert channel_fingerprint(base) != channel_fingerprint(_ch("x", 146.54))
    noted = copy.deepcopy(base)
    noted.notes = "annotated"
    assert channel_fingerprint(base) == channel_fingerprint(noted)


def test_structure_hash_sees_channels_that_content_hash_ignores():
    before = _catalog()
    after = copy.deepcopy(before)
    after.favorites[0].systems[0].departments[0].channels.append(_ch("a3", 147.3))
    assert before.content_hash() == after.content_hash()
    assert structure_hash(before) != structure_hash(after)


def test_structure_hash_ignores_csv_text():
    before = _catalog()
    after = copy.deepcopy(before)
    after.favorites[0].notes = "reworded"
    assert before.content_hash() != after.content_hash()
    assert structure_hash(before) == structure_hash(after)


def test_structure_hash_ignores_channel_ids():
    before = _catalog()
    after = copy.deepcopy(before)
    after.favorites[0].systems[0].departments[0].channels[0].id = "renamed"
    assert structure_hash(before) == structure_hash(after)


def test_structure_hash_sees_trunk_frequency_changes():
    before = Catalog(favorites=[_favorite("T", trunk=[TrunkFrequency(id="t1", freq_mhz=851.0)])])
    after = Catalog(favorites=[_favorite("T", trunk=[TrunkFrequency(id="t1", freq_mhz=851.5)])])
    assert structure_hash(before) != structure_hash(after)


# ------------------------------------------------------------------ delta --
def test_identical_catalogs_give_an_empty_delta():
    delta = compute_delta(_catalog(), _catalog())
    assert delta.is_empty
    assert delta.per_slug == []
    assert delta.summary() == "no change"


def test_added_and_removed_lists_are_reported_with_channel_counts():
    before = _catalog()
    after = Catalog(favorites=[before.favorites[0], _favorite("C", [_ch("c1", 160.0), _ch("c2", 161.0)])])
    delta = compute_delta(before, after)
    assert delta.lists_added == ["c"]
    assert delta.lists_removed == ["b"]
    by_slug = {s.slug: s for s in delta.per_slug}
    assert by_slug["c"].status == "added" and by_slug["c"].channels_added == 2
    assert by_slug["b"].status == "removed" and by_slug["b"].channels_removed == 1


def test_channel_added_removed_and_changed_are_counted():
    before = _catalog()
    after = copy.deepcopy(before)
    channels = after.favorites[0].systems[0].departments[0].channels
    channels[0].freq_mhz = 146.54  # changed
    del channels[1]  # removed
    channels.append(_ch("a9", 147.36))  # added
    delta = compute_delta(before, after)
    [entry] = delta.per_slug
    assert entry.slug == "a"
    assert entry.status == "changed"
    assert (entry.channels_added, entry.channels_removed, entry.channels_changed) == (1, 1, 1)
    assert any(sample.startswith("~ a1 146.52 -> a1 146.54") for sample in entry.samples)
    assert delta.totals()["channels_changed"] == 1


def test_a_renumbered_channel_counts_as_moved_not_added_and_removed():
    before = _catalog()
    after = copy.deepcopy(before)
    after.favorites[0].systems[0].departments[0].channels[0].id = "a1-new"
    delta = compute_delta(before, after)
    assert delta.structure_before == delta.structure_after
    assert delta.per_slug == []


def test_moved_between_departments_is_reported_as_moved():
    before = _catalog()
    after = copy.deepcopy(before)
    system = after.favorites[0].systems[0]
    moved = system.departments[0].channels.pop()
    system.departments.append(Department(id="new", label="New", channels=[moved]))
    [entry] = compute_delta(before, after).per_slug
    assert entry.channels_moved == 1
    assert entry.channels_added == entry.channels_removed == 0


def test_csv_only_change_lists_the_fields():
    before = _catalog()
    after = copy.deepcopy(before)
    after.favorites[1].notes = "new note"
    [entry] = compute_delta(before, after).per_slug
    assert entry.fields_changed == ["notes"]
    assert entry.channels_changed == 0


def test_trunk_table_change_names_the_system():
    before = Catalog(favorites=[_favorite("T", trunk=[TrunkFrequency(id="t1", freq_mhz=851.0)])])
    after = Catalog(favorites=[_favorite("T", trunk=[TrunkFrequency(id="t1", freq_mhz=851.5)])])
    [entry] = compute_delta(before, after).per_slug
    assert entry.systems_changed == ["T system"]


def test_delta_round_trips_through_dict():
    before = _catalog()
    after = copy.deepcopy(before)
    after.favorites[0].systems[0].departments[0].channels.append(_ch("a3", 147.3))
    delta = compute_delta(before, after, reason="test")
    again = CatalogDelta.from_dict(delta.to_dict())
    assert again.to_dict() == delta.to_dict()
    assert again.reason == "test"


# ------------------------------------------------------------------ store --
def test_update_store_numbers_records_sequentially(tmp_path):
    store = UpdateStore(tmp_path / "updates")
    assert store.latest() is None
    before = _catalog()
    after = copy.deepcopy(before)
    after.favorites[0].notes = "x"
    first = store.commit(compute_delta(before, after, reason="one"))
    second = store.commit(compute_delta(after, before, reason="two"))
    assert (first.id, second.id) == ("0001", "0002")
    assert [d.reason for d in store.list()] == ["one", "two"]
    assert store.latest().id == "0002"
    assert store.load("0001").per_slug[0].fields_changed == ["notes"]
    assert (tmp_path / "updates" / "0001.json").exists()
    assert not list((tmp_path / "updates").glob("*.tmp"))


def test_update_store_unknown_id_raises(tmp_path):
    with pytest.raises(KeyError):
        UpdateStore(tmp_path).load("0042")
