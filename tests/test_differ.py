from wasds150.catalog import loader
from wasds150.diffing.differ import diff_profile
from wasds150.models.catalog import FavoritesList, ORIGIN_LOCAL
from wasds150.models.profile import Profile


def test_no_changes_yields_empty_diff(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    assert diff_profile(catalog, profile) == []


def test_disable_produces_disable_change(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_enabled("fl01", False)
    changes = diff_profile(catalog, profile)
    assert len(changes) == 1
    assert changes[0].op == "disable"
    assert changes[0].slug == "fl01"


def test_enable_after_disabling_baseline_default_is_noop(sample_csv_path):
    # baseline default is already enabled=True, so explicitly re-enabling
    # produces no visible change.
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_enabled("fl01", True)
    changes = diff_profile(catalog, profile)
    assert changes == []


def test_remove_produces_remove_change(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_removed("fl01", True)
    changes = diff_profile(catalog, profile)
    assert len(changes) == 1
    assert changes[0].op == "remove"


def test_edit_produces_edit_change_with_before_after(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_override("fl01", "notes", "new note")
    changes = diff_profile(catalog, profile)
    assert len(changes) == 1
    assert changes[0].op == "edit"
    assert changes[0].field == "notes"
    assert changes[0].after == "new note"
    assert changes[0].before != "new note"


def test_edit_matching_baseline_value_is_not_a_change(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    baseline_notes = catalog.by_slug("fl01").notes
    profile = Profile()
    profile.set_override("fl01", "notes", baseline_notes)
    assert diff_profile(catalog, profile) == []


def test_local_add_produces_add_change(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    fl = FavoritesList(
        id="x",
        slug="local01",
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
        origin=ORIGIN_LOCAL,
    )
    profile.add_local_list(fl)
    changes = diff_profile(catalog, profile)
    assert len(changes) == 1
    assert changes[0].op == "add"
    assert changes[0].slug == "local01"
