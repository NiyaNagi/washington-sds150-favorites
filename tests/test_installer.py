"""Installer tests — simulated volumes only (plain directories under
tmp_path), per the task's "simulated-volume tests only" requirement. No
real hardware/removable-media enumeration is exercised here — see
:func:`wasds150.installer.detect.list_os_candidate_mount_points` for the
(intentionally untested) real-hardware layer.
"""
import zipfile

import pytest

from wasds150.hpe import builders, flist as hpe_flist
from wasds150.installer import confirm, detect, hpdb_reader, paths
from wasds150.installer.backup import InstallerError, backup_card, read_backup_manifest, verify_backup
from wasds150.installer.confirm import confirm_phrase_for
from wasds150.installer.rollback import rollback_from_backup
from wasds150.installer.writer import plan_write, write_favorites_list
from wasds150.models.catalog import Channel, Department, System


def make_simulated_card(tmp_path, *, with_app_data=True):
    card = tmp_path / "card"
    (card / paths.FAVORITES_LISTS_DIR).mkdir(parents=True)
    (card / paths.HPDB_DIR).mkdir(parents=True)
    (card / paths.PROFILE_CFG).write_text("dummy profile\r\n", encoding="ascii")
    if with_app_data:
        (card / paths.APP_DATA_CFG).write_text("resume-state-blob", encoding="ascii")
    return card


def make_test_document():
    system = System(
        id="s1", label="Test Conv",
        departments=[Department(id="d1", label="Ops", channels=[Channel(id="c1", label="Ch1", freq_mhz=154.1, mode="NFM")])],
    )
    return builders.build_favorites_document([system])


# --------------------------------------------------------------- paths ----
def test_hpd_filename_format():
    assert paths.hpd_filename(0) == "f_000000.hpd"
    assert paths.hpd_filename(255) == "f_000255.hpd"


def test_hpd_filename_rejects_out_of_range():
    with pytest.raises(ValueError):
        paths.hpd_filename(256)
    with pytest.raises(ValueError):
        paths.hpd_filename(-1)


def test_is_sds150_card(tmp_path):
    card = make_simulated_card(tmp_path)
    assert paths.is_sds150_card(card)
    assert not paths.is_sds150_card(tmp_path / "not-a-card")


def test_is_within_allowed_write_path_accepts_favorites_files(tmp_path):
    card = make_simulated_card(tmp_path)
    assert paths.is_within_allowed_write_path(card, card / paths.FAVORITES_LISTS_DIR / "f_000000.hpd")
    assert paths.is_within_allowed_write_path(card, card / paths.F_LIST_CFG)


def test_is_within_allowed_write_path_rejects_everything_else(tmp_path):
    card = make_simulated_card(tmp_path)
    assert not paths.is_within_allowed_write_path(card, card / paths.PROFILE_CFG)
    assert not paths.is_within_allowed_write_path(card, card / paths.HPDB_DIR / "hpdb.cfg")
    assert not paths.is_within_allowed_write_path(card, card / paths.DISCOVERY_CFG)
    assert not paths.is_within_allowed_write_path(card, card / paths.APP_DATA_CFG)
    # path traversal attempt
    assert not paths.is_within_allowed_write_path(
        card, card / paths.FAVORITES_LISTS_DIR / ".." / ".." / "evil.hpd"
    )


def test_is_within_allowed_write_path_rejects_symlinked_target_and_directory(tmp_path):
    card = make_simulated_card(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    external_file = outside / "external.hpd"
    external_file.write_text("do not overwrite", encoding="ascii")
    target = card / paths.FAVORITES_LISTS_DIR / "f_000007.hpd"
    target.symlink_to(external_file)
    assert not paths.is_within_allowed_write_path(card, target)

    card2 = tmp_path / "card2"
    (card2 / paths.BCDX36HP_DIR).mkdir(parents=True)
    (card2 / paths.FAVORITES_LISTS_DIR).symlink_to(outside, target_is_directory=True)
    assert not paths.is_within_allowed_write_path(card2, card2 / paths.FAVORITES_LISTS_DIR / "f_000007.hpd")


def test_is_allowed_delete_path(tmp_path):
    card = make_simulated_card(tmp_path)
    assert paths.is_allowed_delete_path(card, card / paths.APP_DATA_CFG)
    assert not paths.is_allowed_delete_path(card, card / paths.PROFILE_CFG)


# -------------------------------------------------------------- detect ----
def test_scan_candidates_flags_sds150_marker(tmp_path):
    card = make_simulated_card(tmp_path)
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    volumes = detect.scan_candidates([card, plain_dir, tmp_path / "nonexistent"])
    by_path = {v.mount_point: v for v in volumes}
    assert by_path[card].is_sds150_candidate is True
    assert by_path[plain_dir].is_sds150_candidate is False
    assert len(volumes) == 2  # nonexistent dir skipped


def test_detect_volumes_with_explicit_candidates_does_not_touch_os_layer(tmp_path):
    card = make_simulated_card(tmp_path)
    volumes = detect.detect_volumes([card])
    assert len(volumes) == 1
    assert volumes[0].is_sds150_candidate


# -------------------------------------------------------------- confirm ---
def test_confirm_phrase_for_uses_volume_name(tmp_path):
    card = tmp_path / "MySDS150"
    card.mkdir()
    assert confirm.confirm_phrase_for(card) == "WRITE MySDS150"


def test_verify_confirmation(tmp_path):
    card = tmp_path / "MySDS150"
    card.mkdir()
    assert confirm.verify_confirmation("WRITE MySDS150", card)
    assert not confirm.verify_confirmation("WRITE wrong", card)


# --------------------------------------------------------------- backup ---
def test_backup_card_archives_bcdx36hp_tree_with_manifest(tmp_path):
    card = make_simulated_card(tmp_path)
    backup_dir = tmp_path / "backups"
    archive = backup_card(card, backup_dir)
    assert archive.exists()
    manifest = read_backup_manifest(archive)
    paths_in_manifest = {f["path"] for f in manifest["files"]}
    assert f"{paths.BCDX36HP_DIR}/profile.cfg" in paths_in_manifest
    assert f"{paths.BCDX36HP_DIR}/app_data.cfg" in paths_in_manifest


def test_backup_card_raises_for_non_sds150_directory(tmp_path):
    not_a_card = tmp_path / "empty"
    not_a_card.mkdir()
    with pytest.raises(InstallerError):
        backup_card(not_a_card, tmp_path / "backups")


def test_verify_backup_detects_no_issues_for_fresh_backup(tmp_path):
    card = make_simulated_card(tmp_path)
    archive = backup_card(card, tmp_path / "backups")
    assert verify_backup(archive) == []


def test_verify_backup_detects_corruption(tmp_path):
    card = make_simulated_card(tmp_path)
    archive = backup_card(card, tmp_path / "backups")
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        contents = {n: zf.read(n) for n in names}
    contents[f"{paths.BCDX36HP_DIR}/profile.cfg"] = b"TAMPERED"
    with zipfile.ZipFile(archive, "w") as zf:
        for name, data in contents.items():
            zf.writestr(name, data)
    issues = verify_backup(archive)
    assert any("checksum mismatch" in i for i in issues)


# --------------------------------------------------------------- writer ---
def test_plan_write_returns_allowlisted_paths(tmp_path):
    card = make_simulated_card(tmp_path)
    hpd, flist_path = plan_write(card, 0)
    assert hpd == card / paths.FAVORITES_LISTS_DIR / "f_000000.hpd"
    assert flist_path == card / paths.F_LIST_CFG


def test_plan_write_rejects_out_of_range_index(tmp_path):
    card = make_simulated_card(tmp_path)
    with pytest.raises(ValueError):
        plan_write(card, 999)


def test_write_favorites_list_rejects_non_sds150_card(tmp_path):
    not_a_card = tmp_path / "empty"
    not_a_card.mkdir()
    with pytest.raises(InstallerError):
        write_favorites_list(
            not_a_card, index=0, document=make_test_document(), user_name="X",
            backup_dir=tmp_path / "backups", dry_run=True,
        )


def test_write_favorites_list_dry_run_makes_no_changes(tmp_path):
    card = make_simulated_card(tmp_path)
    result = write_favorites_list(
        card, index=0, document=make_test_document(), user_name="Test List",
        backup_dir=tmp_path / "backups", dry_run=True,
    )
    assert result.dry_run
    assert not (card / paths.FAVORITES_LISTS_DIR / "f_000000.hpd").exists()
    assert not (tmp_path / "backups").exists()
    assert (card / paths.APP_DATA_CFG).exists()  # untouched


def test_write_favorites_list_requires_correct_confirm_phrase(tmp_path):
    card = make_simulated_card(tmp_path)
    with pytest.raises(InstallerError):
        write_favorites_list(
            card, index=0, document=make_test_document(), user_name="Test",
            backup_dir=tmp_path / "backups", confirm_phrase="wrong phrase", dry_run=False,
        )
    assert not (card / paths.FAVORITES_LISTS_DIR / "f_000000.hpd").exists()


def test_write_favorites_list_real_write_full_sequence(tmp_path):
    card = make_simulated_card(tmp_path)
    result = write_favorites_list(
        card, index=0, document=make_test_document(), user_name="Test List",
        backup_dir=tmp_path / "backups", confirm_phrase=confirm_phrase_for(card), dry_run=False,
    )
    assert not result.dry_run
    assert result.verified
    assert result.backup_path is not None and result.backup_path.exists()
    hpd_path = card / paths.FAVORITES_LISTS_DIR / "f_000000.hpd"
    assert hpd_path.exists()
    assert hpd_path.read_bytes().endswith(b"\r\n")  # CRLF preserved
    assert (card / paths.F_LIST_CFG).exists()
    assert not (card / paths.APP_DATA_CFG).exists()  # deleted per documented safety rule
    # Never touched:
    assert (card / paths.PROFILE_CFG).read_bytes() == b"dummy profile\r\n"


def test_write_favorites_list_patches_existing_entry_preserving_other_fields(tmp_path):
    card = make_simulated_card(tmp_path)
    phrase = confirm_phrase_for(card)
    write_favorites_list(
        card, index=0, document=make_test_document(), user_name="First Name",
        backup_dir=tmp_path / "backups", confirm_phrase=phrase, dry_run=False,
    )
    flist_doc = hpe_flist.parse_f_list((card / paths.F_LIST_CFG).read_text(encoding="ascii"))
    entry = hpe_flist.find_entry_by_filename(flist_doc, "f_000000.hpd")
    entry.fields[4] = "42"  # simulate a user having customized QuickKey
    (card / paths.F_LIST_CFG).write_text(hpe_flist.render(flist_doc), encoding="ascii")

    # Re-create app_data.cfg to simulate the scanner having run since.
    (card / paths.APP_DATA_CFG).write_text("resume-again", encoding="ascii")

    write_favorites_list(
        card, index=0, document=make_test_document(), user_name="Renamed",
        backup_dir=tmp_path / "backups", confirm_phrase=phrase, dry_run=False,
    )
    flist_doc2 = hpe_flist.parse_f_list((card / paths.F_LIST_CFG).read_text(encoding="ascii"))
    entry2 = hpe_flist.find_entry_by_filename(flist_doc2, "f_000000.hpd")
    assert entry2.get(0) == "Renamed"  # user_name updated
    assert entry2.get(4) == "42"  # quick_key preserved verbatim
    assert not (card / paths.APP_DATA_CFG).exists()  # deleted again


# ------------------------------------------------------------- rollback ---
def test_rollback_restores_files_and_verifies_checksums(tmp_path):
    card = make_simulated_card(tmp_path)
    archive = backup_card(card, tmp_path / "backups")
    (card / paths.PROFILE_CFG).write_text("MODIFIED AFTER BACKUP\r\n", encoding="ascii")

    restored = rollback_from_backup(card, archive)
    assert f"{paths.BCDX36HP_DIR}/profile.cfg" in restored
    assert (card / paths.PROFILE_CFG).read_bytes() == b"dummy profile\r\n"


def test_rollback_removes_files_created_after_backup(tmp_path):
    card = make_simulated_card(tmp_path)
    archive = backup_card(card, tmp_path / "backups")  # backup BEFORE any favorites write
    write_favorites_list(
        card, index=0, document=make_test_document(), user_name="Test",
        backup_dir=tmp_path / "backups2", confirm_phrase=confirm_phrase_for(card), dry_run=False,
    )
    assert (card / paths.FAVORITES_LISTS_DIR / "f_000000.hpd").exists()

    rollback_from_backup(card, archive)
    assert not (card / paths.FAVORITES_LISTS_DIR / "f_000000.hpd").exists()
    assert not (card / paths.F_LIST_CFG).exists()


def test_rollback_can_keep_extraneous_files_if_requested(tmp_path):
    card = make_simulated_card(tmp_path)
    archive = backup_card(card, tmp_path / "backups")
    write_favorites_list(
        card, index=0, document=make_test_document(), user_name="Test",
        backup_dir=tmp_path / "backups2", confirm_phrase=confirm_phrase_for(card), dry_run=False,
    )
    rollback_from_backup(card, archive, remove_extraneous=False)
    assert (card / paths.FAVORITES_LISTS_DIR / "f_000000.hpd").exists()  # kept


def test_rollback_raises_on_checksum_mismatch(tmp_path):
    card = make_simulated_card(tmp_path)
    archive = backup_card(card, tmp_path / "backups")
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        contents = {n: zf.read(n) for n in names}
    contents[f"{paths.BCDX36HP_DIR}/profile.cfg"] = b"TAMPERED"
    with zipfile.ZipFile(archive, "w") as zf:
        for name, data in contents.items():
            zf.writestr(name, data)

    with pytest.raises(ValueError):
        rollback_from_backup(card, archive)


# -------------------------------------------------------------- fsync -----
def test_write_uses_real_fsync_without_raising(tmp_path):
    """Not a hardware test — just confirms our fsync calls don't raise on
    a normal filesystem (the actual durability guarantee can't be verified
    without real removable media, but the code path must not error)."""
    card = make_simulated_card(tmp_path)
    result = write_favorites_list(
        card, index=1, document=make_test_document(), user_name="Fsync Test",
        backup_dir=tmp_path / "backups", confirm_phrase=confirm_phrase_for(card), dry_run=False,
    )
    assert result.verified


# ---------------------------------------------------------- hpdb_reader ---
def test_hpdb_reader_has_hpdb(tmp_path, synthetic_hpdb_cfg_path):
    card = make_simulated_card(tmp_path)
    assert not hpdb_reader.has_hpdb(card)
    (card / paths.HPDB_DIR).mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copy(synthetic_hpdb_cfg_path, card / paths.HPDB_DIR / "hpdb.cfg")
    assert hpdb_reader.has_hpdb(card)


def test_hpdb_reader_reads_cfg_and_state_files(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    import shutil

    card = make_simulated_card(tmp_path)
    (card / paths.HPDB_DIR).mkdir(parents=True, exist_ok=True)
    shutil.copy(synthetic_hpdb_cfg_path, card / paths.HPDB_DIR / "hpdb.cfg")
    shutil.copy(synthetic_hpdb_state_path, card / paths.HPDB_DIR / "s_000053.hpd")

    result = hpdb_reader.read_card_hpdb(card)
    assert result.hpdb_cfg is not None
    assert result.county_index.by_id == {5301: "King", 5302: "Pierce"}
    assert 53 in result.state_files


def test_hpdb_reader_ignores_non_state_files(tmp_path, synthetic_hpdb_cfg_path):
    import shutil

    card = make_simulated_card(tmp_path)
    (card / paths.HPDB_DIR).mkdir(parents=True, exist_ok=True)
    shutil.copy(synthetic_hpdb_cfg_path, card / paths.HPDB_DIR / "hpdb.cfg")
    (card / paths.HPDB_DIR / "some_other_file.txt").write_text("not a state file", encoding="ascii")

    result = hpdb_reader.read_card_hpdb(card)
    assert result.state_files == {}


def test_hpdb_reader_handles_missing_hpdb_dir_gracefully(tmp_path):
    card = make_simulated_card(tmp_path)
    result = hpdb_reader.read_card_hpdb(card)
    assert result.hpdb_cfg is None
    assert result.state_files == {}
    assert result.county_index is None


def test_hpdb_reader_never_writes(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    """Defense-in-depth: confirm HPDB_DIR is not on the write/delete
    allow-list, so even a hypothetical bug elsewhere can't accidentally
    write into it via the shared allow-list helpers."""
    card = make_simulated_card(tmp_path)
    (card / paths.HPDB_DIR).mkdir(parents=True, exist_ok=True)
    target = card / paths.HPDB_DIR / "hpdb.cfg"
    assert not paths.is_within_allowed_write_path(card, target)
    assert not paths.is_allowed_delete_path(card, target)
