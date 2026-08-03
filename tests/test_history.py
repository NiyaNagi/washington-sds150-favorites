from wasds150.catalog import loader
from wasds150.generate.pipeline import apply_profile
from wasds150.history.rollback import rollback_profile
from wasds150.history.snapshots import SnapshotStore
from wasds150.models.profile import Profile


def test_snapshot_ids_increment(tmp_path, sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    store = SnapshotStore(tmp_path / "history")
    profile = Profile()
    result = apply_profile(catalog, profile)

    snap1 = store.commit(profile, result, message="first")
    snap2 = store.commit(profile, result, message="second")
    assert snap1.id == "0001"
    assert snap2.id == "0002"


def test_snapshot_list_returns_in_order(tmp_path, sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    store = SnapshotStore(tmp_path / "history")
    profile = Profile()
    result = apply_profile(catalog, profile)
    store.commit(profile, result, message="a")
    store.commit(profile, result, message="b")

    snapshots = store.list()
    assert [s.message for s in snapshots] == ["a", "b"]


def test_snapshot_load_profile_round_trip(tmp_path, sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    store = SnapshotStore(tmp_path / "history")
    profile = Profile()
    profile.set_enabled("fl01", False)
    result = apply_profile(catalog, profile)
    snap = store.commit(profile, result)

    restored = store.load_profile(snap.id)
    assert restored.entries["fl01"].enabled is False


def test_snapshot_load_raw_missing_id_raises(tmp_path):
    store = SnapshotStore(tmp_path / "history")
    try:
        store.load_raw("9999")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_latest_returns_none_when_empty(tmp_path):
    store = SnapshotStore(tmp_path / "history")
    assert store.latest() is None


def test_latest_returns_most_recent(tmp_path, sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    store = SnapshotStore(tmp_path / "history")
    profile = Profile()
    result = apply_profile(catalog, profile)
    store.commit(profile, result, message="a")
    snap2 = store.commit(profile, result, message="b")
    assert store.latest().id == snap2.id


def test_rollback_profile_restores_state_and_backs_up_current(tmp_path, sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    history_dir = tmp_path / "history"
    profile_path = tmp_path / "profile.json"
    store = SnapshotStore(history_dir)

    profile_v1 = Profile()
    profile_v1.set_enabled("fl01", False)
    result_v1 = apply_profile(catalog, profile_v1)
    snap1 = store.commit(profile_v1, result_v1, message="v1")

    profile_v2 = Profile()
    profile_v2.set_enabled("fl01", True)
    profile_v2.set_enabled("fl02", False)
    profile_v2.save(profile_path)

    rollback_profile(profile_path, history_dir, snap1.id)

    restored = Profile.load(profile_path)
    assert restored.entries["fl01"].enabled is False
    assert "fl02" not in restored.entries

    backups = list(tmp_path.glob("profile.pre-rollback-*.json"))
    assert len(backups) == 1
    backed_up = Profile.load(backups[0])
    assert backed_up.entries["fl02"].enabled is False


def test_rollback_without_existing_profile_does_not_error(tmp_path, sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    history_dir = tmp_path / "history"
    profile_path = tmp_path / "profile.json"
    store = SnapshotStore(history_dir)
    profile = Profile()
    result = apply_profile(catalog, profile)
    snap = store.commit(profile, result)

    rollback_profile(profile_path, history_dir, snap.id)
    assert profile_path.exists()
