from pathlib import Path

import pytest

import wasds150.installer.sentinel_workspace as workspace_module
from wasds150.installer.backup import InstallerError
from wasds150.hpe.flist import entries, parse_f_list
from wasds150.installer.sentinel_workspace import (
    confirmation_phrase,
    discover_profiles,
    install_selected_favorites,
)
from wasds150.models.catalog import Channel, Department, FavoritesList, System


def _favorite(key: str, slug: str, frequency: float) -> FavoritesList:
    return FavoritesList(
        id=slug,
        slug=slug,
        favorite_key=key,
        favorite_name=f"{key} Test",
        region="Test",
        counties="Test",
        scenario="Test",
        source_type="conventional",
        system_or_category="Test",
        sites_or_coverage="Test",
        departments_or_channels="Test",
        mode="NFM",
        monitorability="Full",
        upgrade_required="None",
        source_url="",
        notes="",
        systems=[System(
            id=f"{slug}-system",
            label=f"{key} System",
            departments=[Department(
                id=f"{slug}-department",
                label="Operations",
                channels=[Channel(id=f"{slug}-channel", label="Dispatch", freq_mhz=frequency, mode="NFM")],
            )],
        )],
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "Uniden" / "BCDx36HP"
    favorites = root / "FavoriteLists"
    profile = root / "Profile" / "Preset"
    favorites.mkdir(parents=True)
    profile.mkdir(parents=True)
    existing = (
        "TargetModel\tBCDx36HP\r\n"
        "FormatVersion\t1.00\r\n"
        "F-List\tExisting\tf_000001.hpd\tOff\tOn\t7\tOff\r\n"
    )
    (favorites / "f_list.cfg").write_bytes(existing.encode("ascii"))
    (favorites / "f_000001.hpd").write_bytes(b"existing")
    (profile / "f_list.cfg").write_bytes(existing.encode("ascii"))
    (profile / "profile.cfg").write_bytes(b"profile")
    return root


def test_sentinel_workspace_dry_run_is_non_mutating(tmp_path):
    workspace = _workspace(tmp_path)
    before = {path.relative_to(workspace): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}

    result = install_selected_favorites(
        workspace,
        "Preset",
        [_favorite("FL01", "fl01", 155.16), _favorite("FL02", "fl02", 851.0125)],
        backup_dir=tmp_path / "backups",
    )

    assert result.dry_run is True
    assert [assignment.index for assignment in result.assignments] == [0, 2]
    assert len(result.planned_writes) == 4
    assert not (tmp_path / "backups").exists()
    after = {path.relative_to(workspace): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    assert after == before


def test_sentinel_workspace_bulk_install_writes_all_lists_and_preserves_existing(tmp_path):
    workspace = _workspace(tmp_path)
    selected = [_favorite("FL01", "fl01", 155.16), _favorite("FL02", "fl02", 851.0125)]
    plan = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
    )

    result = install_selected_favorites(
        workspace,
        "Preset",
        selected,
        backup_dir=tmp_path / "backups",
        execute=True,
        confirm=confirmation_phrase("Preset"),
        expected_plan_id=plan.plan_id,
    )

    assert result.outcome == "committed"
    assert result.verified is True
    assert result.backup_path.is_file()
    assert (workspace / "FavoriteLists" / "f_000001.hpd").read_bytes() == b"existing"
    for filename in ("f_000000.hpd", "f_000002.hpd"):
        payload = (workspace / "FavoriteLists" / filename).read_bytes()
        assert payload.startswith(b"TargetModel\tBCDx36HP\r\n")
        assert b"File\tHomePatrol Export File" not in payload

    global_doc = parse_f_list((workspace / "FavoriteLists" / "f_list.cfg").read_bytes().decode("ascii"))
    profile_doc = parse_f_list((workspace / "Profile" / "Preset" / "f_list.cfg").read_bytes().decode("ascii"))
    assert len(entries(global_doc)) == 3
    assert len(entries(profile_doc)) == 3
    assert discover_profiles(workspace) == ["Preset"]


def test_sentinel_workspace_reuses_generated_slots_on_repeat_install(tmp_path):
    workspace = _workspace(tmp_path)
    selected = [_favorite("FL01", "fl01", 155.16)]
    first_plan = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
    )
    first = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
        execute=True, confirm=confirmation_phrase("Preset"), expected_plan_id=first_plan.plan_id,
    )
    selected[0].favorite_name = "Updated"
    second_plan = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
    )
    second = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
        execute=True, confirm=confirmation_phrase("Preset"), expected_plan_id=second_plan.plan_id,
        allow_replacements=True,
    )

    assert first.assignments[0].index == second.assignments[0].index == 0
    assert second.assignments[0].replacing is True
    doc = parse_f_list((workspace / "FavoriteLists" / "f_list.cfg").read_bytes().decode("ascii"))
    assert len(entries(doc)) == 2


def test_sentinel_workspace_rejects_backup_inside_workspace(tmp_path):
    workspace = _workspace(tmp_path)
    with pytest.raises(InstallerError, match="outside"):
        install_selected_favorites(
            workspace, "Preset", [_favorite("FL01", "fl01", 155.16)],
            backup_dir=workspace / "backups",
        )


def test_sentinel_workspace_failure_rolls_back_entire_transaction(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    before = {path.relative_to(workspace): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    real_write = workspace_module._write_synced
    calls = 0

    def fail_second_write(path, data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated write failure")
        real_write(path, data)

    monkeypatch.setattr(workspace_module, "_write_synced", fail_second_write)

    plan = install_selected_favorites(
        workspace,
        "Preset",
        [_favorite("FL01", "fl01", 155.16), _favorite("FL02", "fl02", 851.0125)],
        backup_dir=tmp_path / "backups",
    )

    with pytest.raises(InstallerError, match="rolled back"):
        install_selected_favorites(
            workspace,
            "Preset",
            [_favorite("FL01", "fl01", 155.16), _favorite("FL02", "fl02", 851.0125)],
            backup_dir=tmp_path / "backups",
            execute=True,
            confirm=confirmation_phrase("Preset"),
            expected_plan_id=plan.plan_id,
        )

    after = {path.relative_to(workspace): path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    assert after == before


def test_sentinel_workspace_rejects_stale_plan(tmp_path):
    workspace = _workspace(tmp_path)
    selected = [_favorite("FL01", "fl01", 155.16)]
    plan = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
    )
    with (workspace / "FavoriteLists" / "f_list.cfg").open("ab") as stream:
        stream.write(b"\r\n")

    with pytest.raises(InstallerError, match="changed after planning"):
        install_selected_favorites(
            workspace, "Preset", selected, backup_dir=tmp_path / "backups",
            execute=True, confirm=confirmation_phrase("Preset"), expected_plan_id=plan.plan_id,
        )


def test_sentinel_workspace_requires_explicit_replacement_approval(tmp_path):
    workspace = _workspace(tmp_path)
    selected = [_favorite("FL01", "fl01", 155.16)]
    initial = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
    )
    install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
        execute=True, confirm=confirmation_phrase("Preset"), expected_plan_id=initial.plan_id,
    )
    replacement = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
    )

    with pytest.raises(InstallerError, match="explicitly approve"):
        install_selected_favorites(
            workspace, "Preset", selected, backup_dir=tmp_path / "backups",
            execute=True, confirm=confirmation_phrase("Preset"), expected_plan_id=replacement.plan_id,
        )


def test_sentinel_workspace_lock_is_workspace_wide(tmp_path):
    workspace = _workspace(tmp_path)
    with workspace_module._workspace_lock(workspace):
        with pytest.raises(InstallerError, match="another Sentinel install"):
            with workspace_module._workspace_lock(workspace):
                pass


def test_sentinel_workspace_preserves_unindexed_hpd_and_fingerprints_targets(tmp_path):
    workspace = _workspace(tmp_path)
    orphan = workspace / "FavoriteLists" / "f_000000.hpd"
    orphan.write_bytes(b"orphan")
    selected = [_favorite("FL01", "fl01", 155.16)]

    plan = install_selected_favorites(
        workspace, "Preset", selected, backup_dir=tmp_path / "backups",
    )
    assert plan.assignments[0].index == 2
    target = workspace / "FavoriteLists" / plan.assignments[0].filename
    target.write_bytes(b"created after plan")

    with pytest.raises(InstallerError, match="changed after planning"):
        install_selected_favorites(
            workspace, "Preset", selected, backup_dir=tmp_path / "backups",
            execute=True, confirm=confirmation_phrase("Preset"), expected_plan_id=plan.plan_id,
        )
    assert orphan.read_bytes() == b"orphan"
