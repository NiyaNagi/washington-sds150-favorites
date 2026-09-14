"""Per-list scanner settings on install: a new list gets its quick key,
location control and monitor state; an existing list changes only its
monitor state; a list the tool did not make is left alone."""
from pathlib import Path

from wasds150.hpe.flist import ListSettings, entries, parse_f_list
from wasds150.hpe.schema import F_LIST_SCHEMA
from wasds150.installer.sentinel_workspace import confirmation_phrase, install_selected_favorites
from wasds150.models.catalog import Channel, Department, FavoritesList, System


def _favorite(key: str, frequency: float) -> FavoritesList:
    slug = key.lower()
    return FavoritesList(
        id=slug, slug=slug, favorite_key=key, favorite_name=f"{key} Test", region="Test", counties="Test",
        scenario="Test", source_type="conventional", system_or_category="Test", sites_or_coverage="Test",
        departments_or_channels="Test", mode="NFM", monitorability="Full", upgrade_required="None",
        source_url="", notes="",
        systems=[System(id=f"{slug}-system", label=f"{key} System", departments=[Department(
            id=f"{slug}-department", label="Operations",
            channels=[Channel(id=f"{slug}-channel", label="Dispatch", freq_mhz=frequency, mode="NFM")],
        )])],
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "Uniden" / "BCDx36HP"
    (root / "FavoriteLists").mkdir(parents=True)
    (root / "Profile" / "Preset").mkdir(parents=True)
    existing = "TargetModel\tBCDx36HP\r\nFormatVersion\t1.00\r\nF-List\tExisting\tf_000001.hpd\tOff\tOn\t7\tOff\r\n"
    (root / "FavoriteLists" / "f_list.cfg").write_bytes(existing.encode("ascii"))
    (root / "FavoriteLists" / "f_000001.hpd").write_bytes(b"existing")
    (root / "Profile" / "Preset" / "f_list.cfg").write_bytes(existing.encode("ascii"))
    (root / "Profile" / "Preset" / "profile.cfg").write_bytes(b"profile")
    return root


def _install(workspace, tmp_path, favorites, settings):
    plan = install_selected_favorites(workspace, "Preset", favorites, backup_dir=tmp_path / "backups",
                                      allow_replacements=True, list_settings=settings)
    return install_selected_favorites(workspace, "Preset", favorites, backup_dir=tmp_path / "backups", execute=True,
                                      confirm=confirmation_phrase("Preset"), expected_plan_id=plan.plan_id,
                                      allow_replacements=True, list_settings=settings)


def _rows(workspace):
    doc = parse_f_list((workspace / "Profile" / "Preset" / "f_list.cfg").read_bytes().decode("ascii"))
    names = ("user_name", "monitor", "quick_key", "location_control")
    return [tuple(r.get(F_LIST_SCHEMA.field_by_name(n).index - 1) for n in names) for r in entries(doc)]


def test_new_lists_get_their_settings_and_the_lead_list_comes_first(tmp_path):
    workspace = _workspace(tmp_path)
    favorites = [_favorite("FL01", 155.16), _favorite("NM-PS", 155.55)]
    settings = {
        "FL01": ListSettings(monitor=False),
        "NM-PS": ListSettings(monitor=True, quick_key=1, location_control=True, lead=True),
    }
    assert _install(workspace, tmp_path, favorites, settings).outcome == "committed"
    rows = _rows(workspace)
    assert rows[0] == ("NM-PS - NM-PS Test", "On", "1", "On")
    assert ("FL01 - FL01 Test", "Off", "0", "Off") in rows
    assert ("Existing", "On", "7", "Off") in rows  # not ours: untouched


def test_an_existing_entry_changes_only_its_monitor_state(tmp_path):
    workspace = _workspace(tmp_path)
    favorites = [_favorite("NM-PS", 155.55)]
    _install(workspace, tmp_path, favorites, {"NM-PS": ListSettings(monitor=True, quick_key=1, location_control=True, lead=True)})
    # The operator may have moved it; a later install must not reset that.
    _install(workspace, tmp_path, favorites, {"NM-PS": ListSettings(monitor=False, quick_key=5, location_control=False, lead=True)})
    assert _rows(workspace)[0] == ("NM-PS - NM-PS Test", "Off", "1", "On")


def test_short_names_take_over_old_entries_and_superseded_lists_are_removed(tmp_path):
    from wasds150.radios.scanner_categories import is_retired_name

    workspace = _workspace(tmp_path)
    old = [_favorite("NM-PS", 155.55), _favorite("FL01", 155.16), _favorite("KC29", 155.2)]
    _install(workspace, tmp_path, old, {"NM-PS": ListSettings(monitor=True, quick_key=1, location_control=True, lead=True)})
    old_files = {row[0]: row for row in _rows(workspace)}
    assert {"FL01 - FL01 Test", "KC29 - KC29 Test"} <= set(old_files)

    new = [_favorite("NM-PS", 155.55), _favorite("PS-STATE", 155.16)]
    settings = {
        "NM-PS": ListSettings(monitor=True, quick_key=1, location_control=True, lead=True, name="NM Public Safety"),
        "PS-STATE": ListSettings(monitor=False, quick_key=17, lead=True, name="PS Statewide"),
    }
    plan = install_selected_favorites(workspace, "Preset", new, backup_dir=tmp_path / "backups",
                                      allow_replacements=True, list_settings=settings, retire=is_retired_name)
    assert plan.retired == ["FL01 - FL01 Test", "KC29 - KC29 Test"] and len(plan.planned_deletes) == 2
    done = install_selected_favorites(workspace, "Preset", new, backup_dir=tmp_path / "backups", execute=True,
                                      confirm=confirmation_phrase("Preset"), expected_plan_id=plan.plan_id,
                                      allow_replacements=True, list_settings=settings, retire=is_retired_name)
    assert done.outcome == "committed"
    rows = _rows(workspace)
    # Near Me keeps its entry (and so its file and quick key) under the new name.
    assert rows[0] == ("NM Public Safety", "On", "1", "On")
    assert rows[1] == ("PS Statewide", "Off", "17", "Off")
    assert ("Existing", "On", "7", "Off") in rows  # not ours: untouched
    assert not [row for row in rows if " - " in row[0]]
    for relative in plan.planned_deletes:
        assert not (workspace / relative).exists()
    assert (workspace / "FavoriteLists" / "f_000001.hpd").exists()


def test_a_list_another_profile_uses_is_only_taken_out_of_this_profile(tmp_path):
    from wasds150.radios.scanner_categories import is_retired_name

    workspace = _workspace(tmp_path)
    _install(workspace, tmp_path, [_favorite("FL01", 155.16)], {"FL01": ListSettings(monitor=False)})
    other = workspace / "Profile" / "Trip"
    other.mkdir()
    (other / "profile.cfg").write_bytes(b"profile")
    (other / "f_list.cfg").write_bytes((workspace / "Profile" / "Preset" / "f_list.cfg").read_bytes())

    new = [_favorite("PS-STATE", 155.16)]
    settings = {"PS-STATE": ListSettings(monitor=False, quick_key=17, lead=True, name="PS Statewide")}
    done = _install_retiring(workspace, tmp_path, new, settings, is_retired_name)
    assert done.outcome == "committed" and done.planned_deletes == []
    assert "FL01 - FL01 Test" not in [row[0] for row in _rows(workspace)]
    global_doc = parse_f_list((workspace / "FavoriteLists" / "f_list.cfg").read_bytes().decode("ascii"))
    assert "FL01 - FL01 Test" in [r.get(F_LIST_SCHEMA.field_by_name("user_name").index - 1) for r in entries(global_doc)]


def _install_retiring(workspace, tmp_path, favorites, settings, retire):
    plan = install_selected_favorites(workspace, "Preset", favorites, backup_dir=tmp_path / "backups",
                                      allow_replacements=True, list_settings=settings, retire=retire)
    return install_selected_favorites(workspace, "Preset", favorites, backup_dir=tmp_path / "backups", execute=True,
                                      confirm=confirmation_phrase("Preset"), expected_plan_id=plan.plan_id,
                                      allow_replacements=True, list_settings=settings, retire=retire)
