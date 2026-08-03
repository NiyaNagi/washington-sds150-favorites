from wasds150.models.catalog import FavoritesList, ORIGIN_LOCAL
from wasds150.models.profile import EDITABLE_FIELDS, Profile, ProfileEntry
import pytest


def test_entry_for_creates_and_reuses():
    profile = Profile()
    e1 = profile.entry_for("fl01")
    e2 = profile.entry_for("fl01")
    assert e1 is e2
    assert "fl01" in profile.entries


def test_set_enabled_and_removed():
    profile = Profile()
    profile.set_enabled("fl01", False)
    assert profile.entries["fl01"].enabled is False
    profile.set_removed("fl01", True)
    assert profile.entries["fl01"].removed is True


def test_set_override_rejects_non_editable_field():
    profile = Profile()
    with pytest.raises(ValueError):
        profile.set_override("fl01", "id", "hacked")


def test_set_override_accepts_editable_field():
    profile = Profile()
    profile.set_override("fl01", "notes", "hello")
    assert profile.entries["fl01"].overrides["notes"] == "hello"


def test_clear_override_prunes_noop_entry():
    profile = Profile()
    profile.set_override("fl01", "notes", "hello")
    profile.clear_override("fl01", "notes")
    assert "fl01" not in profile.entries


def test_clear_override_keeps_entry_if_other_state_remains():
    profile = Profile()
    profile.set_override("fl01", "notes", "hello")
    profile.set_enabled("fl01", False)
    profile.clear_override("fl01", "notes")
    assert "fl01" in profile.entries
    assert profile.entries["fl01"].enabled is False


def test_restore_drops_all_changes():
    profile = Profile()
    profile.set_enabled("fl01", False)
    profile.set_override("fl01", "notes", "x")
    profile.restore("fl01")
    assert "fl01" not in profile.entries


def test_is_noop():
    entry = ProfileEntry(slug="fl01")
    assert entry.is_noop()
    entry.enabled = False
    assert not entry.is_noop()


def _make_local_fl(slug="local01") -> FavoritesList:
    return FavoritesList(
        id="id",
        slug=slug,
        favorite_key="LOCAL01",
        favorite_name="My List",
        region="",
        counties="",
        scenario="",
        source_type="",
        system_or_category="",
        sites_or_coverage="",
        departments_or_channels="",
        mode="",
        monitorability="",
        upgrade_required="",
        source_url="",
        notes="",
    )


def test_add_and_remove_local_list_sets_origin():
    profile = Profile()
    fl = _make_local_fl()
    fl.origin = "baseline"  # add_local_list should force it to local
    profile.add_local_list(fl)
    assert profile.local_lists["local01"].origin == ORIGIN_LOCAL
    profile.remove_local_list("local01")
    assert "local01" not in profile.local_lists


def test_profile_to_dict_from_dict_round_trip():
    profile = Profile(profile_id="test", based_on_catalog_hash="abc123")
    profile.set_enabled("fl01", False)
    profile.set_override("fl02", "notes", "hi")
    profile.add_local_list(_make_local_fl())

    data = profile.to_dict()
    restored = Profile.from_dict(data)

    assert restored.profile_id == "test"
    assert restored.based_on_catalog_hash == "abc123"
    assert restored.entries["fl01"].enabled is False
    assert restored.entries["fl02"].overrides["notes"] == "hi"
    assert "local01" in restored.local_lists


def test_profile_save_and_load(tmp_path):
    profile = Profile(based_on_catalog_hash="abc")
    profile.set_enabled("fl01", False)
    path = tmp_path / "profile.json"
    profile.save(path)

    assert path.exists()
    loaded = Profile.load(path)
    assert loaded.entries["fl01"].enabled is False


def test_profile_load_or_create_creates_when_missing(tmp_path):
    path = tmp_path / "profile.json"
    profile = Profile.load_or_create(path, catalog_hash="xyz")
    assert not path.exists()  # load_or_create doesn't save by itself
    assert profile.based_on_catalog_hash == "xyz"
    assert profile.entries == {}


def test_editable_fields_includes_all_csv_fields_and_flqk():
    from wasds150.models.catalog import CSV_FIELDS

    assert set(CSV_FIELDS).issubset(set(EDITABLE_FIELDS))
    assert "flqk" in EDITABLE_FIELDS
