"""Exhaustive regression tests for automatic generated-artifact validation."""
from __future__ import annotations

import hashlib
import json
import zipfile

import pytest

from wasds150.bundle.hpe_export import build_per_list_hpe
from wasds150.bundle.generate_outputs import generate_outputs
from wasds150.bundle.sentinel_import_pack import build_sentinel_import_pack
from wasds150.bundle.validation import (
    BundleValidationError,
    validate_csv_bytes,
    validate_markdown_bytes,
    validate_sentinel_import_pack,
)
from wasds150.appctx import AppContext
from wasds150.config import AppConfig
from wasds150.catalog.baseline import load_baseline
from wasds150 import cli
from wasds150.generate.pipeline import GenerationValidationError, apply_profile
from wasds150.hpe import builders, codec
from wasds150.hpe.record import Record, new_document, parse_records, serialize_records
from wasds150.hpe.validation import (
    HpeValidationError,
    ValidationIssue,
    require_valid_document,
    require_valid_hpe_bytes,
    validate_favorites_list,
    validate_hpe_container,
)
from wasds150.installer.backup import InstallerError
from wasds150.installer.writer import write_favorites_list
from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.profile import Profile


def run(argv):
    return cli.main(argv)


def _favorite(channel: Channel) -> FavoritesList:
    return FavoritesList(
        id="fltest",
        slug="fltest",
        favorite_key="FLTEST",
        favorite_name="Validation Test",
        region="",
        counties="",
        scenario="",
        source_type="conventional",
        system_or_category="",
        sites_or_coverage="",
        departments_or_channels="",
        mode="",
        monitorability="",
        upgrade_required="",
        source_url="",
        notes="",
        systems=[
            System(
                id="s1",
                label="Test System",
                departments=[Department(id="d1", label="Ops", channels=[channel])],
            )
        ],
    )


def test_every_baseline_generated_hpe_passes_full_semantic_and_parity_validation(tmp_path):
    catalog = load_baseline()
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    export = build_per_list_hpe(result.enabled_favorites)

    assert len(result.enabled_favorites) == 78
    assert len(export.files) == 58
    assert len(export.warnings) == 20
    by_key = {favorite.favorite_key: favorite for favorite in result.enabled_favorites}
    for filename, data in export.files.items():
        favorite = by_key[filename.removesuffix(".hpe")]
        require_valid_hpe_bytes(favorite, data)
        assert codec.encode_container(codec.decode_container(data)) == data

    fl65 = next(favorite for favorite in result.enabled_favorites if favorite.favorite_key == "FL65")
    fl65_channels = [
        channel
        for system in fl65.systems
        for department in system.departments
        for channel in department.channels
    ]
    assert len(fl65_channels) == 22
    assert sum(channel.freq_mhz == 462.7125 for channel in fl65_channels) == 1


def test_every_baseline_hpe_is_byte_identical_across_full_independent_runs():
    catalog = load_baseline()
    profile = Profile(based_on_catalog_hash=catalog.content_hash())
    first = build_per_list_hpe(apply_profile(catalog, profile).enabled_favorites)
    second = build_per_list_hpe(apply_profile(catalog, profile).enabled_favorites)
    assert first.files == second.files
    assert first.warnings == second.warnings


def test_generation_rejects_more_than_scanner_favorites_list_limit():
    favorite = _favorite(Channel(id="c", label="Good", freq_mhz=154.1))
    favorites = []
    for index in range(257):
        clone = FavoritesList.from_dict(favorite.to_dict())
        clone.id = clone.slug = f"fl{index}"
        clone.favorite_key = f"FL{index}"
        favorites.append(clone)
    with pytest.raises(HpeValidationError, match="exceeds the SDS150 limit"):
        build_per_list_hpe(favorites)


def test_generation_rejects_invalid_catalog_before_creating_outputs():
    favorite = _favorite(Channel(id="c", label="Good", freq_mhz=154.1))
    duplicate = FavoritesList.from_dict(favorite.to_dict())
    duplicate.id = "duplicate-id"
    catalog = Catalog(favorites=[favorite, duplicate])
    with pytest.raises(GenerationValidationError, match="duplicate slug"):
        apply_profile(catalog, Profile())


def test_reserved_quick_key_is_advisory_not_generation_blocking():
    favorite = _favorite(Channel(id="c", label="Good", freq_mhz=154.1))
    catalog = Catalog(favorites=[favorite])
    profile = Profile()
    profile.set_override(favorite.slug, "flqk", 0)
    result = apply_profile(catalog, profile)
    assert any("is reserved" in warning for warning in result.warnings)
    assert build_per_list_hpe(result.enabled_favorites).files


def test_oversized_list_is_warned_and_skipped_without_losing_valid_lists(monkeypatch):
    from wasds150.hpe import builders as builder_module

    good = _favorite(Channel(id="good", label="Good", freq_mhz=154.1))
    oversized = FavoritesList.from_dict(good.to_dict())
    oversized.id = oversized.slug = "flbig"
    oversized.favorite_key = "FLBIG"
    original = builder_module.build_favorites_list_hpe

    def build_or_raise(favorite):
        if favorite.favorite_key == "FLBIG":
            raise HpeValidationError(
                "FLBIG",
                [ValidationIssue("file-size", "container exceeds one MiB")],
            )
        return original(favorite)

    monkeypatch.setattr(builder_module, "build_favorites_list_hpe", build_or_raise)
    export = build_per_list_hpe([good, oversized])
    assert set(export.files) == {"FLTEST.hpe"}
    assert len(export.warnings) == 1
    assert "exceeds" in export.warnings[0]


def test_catalog_persistence_rejects_invalid_catalog(tmp_path):
    favorite = _favorite(Channel(id="c", label="Good", freq_mhz=154.1))
    duplicate = FavoritesList.from_dict(favorite.to_dict())
    duplicate.id = "duplicate-id"
    catalog = Catalog(favorites=[favorite, duplicate])
    config = AppConfig(home=tmp_path / "home")
    context = AppContext(config=config, catalog=Catalog(), catalog_source="test")
    with pytest.raises(ValueError, match="invalid catalog"):
        context.save_catalog(catalog)
    assert not config.catalog_path.exists()


@pytest.mark.parametrize(
    ("channel", "code"),
    [
        (Channel(id="c", label="Bad", freq_mhz=24.999), "unsupported-frequency"),
        (Channel(id="c", label="Bad", freq_mhz=154.1, mode="USB"), "invalid-mode"),
        (Channel(id="c", label="Bad", freq_mhz=154.1, tone="CTCSS 127.3"), "invalid-tone"),
        (Channel(id="c", label="", freq_mhz=154.1), "empty-name"),
        (Channel(id="c", label="Bad\tName", freq_mhz=154.1), "unsafe-text"),
        (Channel(id="c", label="Bad", freq_mhz=154.1, service_type=999), "invalid-service-type"),
    ],
)
def test_invalid_model_content_is_rejected_before_hpe_publication(channel, code):
    favorite = _favorite(channel)
    issues = validate_favorites_list(favorite)
    assert any(issue.code == code for issue in issues)
    with pytest.raises(HpeValidationError):
        build_per_list_hpe([favorite])


def test_document_validation_rejects_schema_valid_but_semantically_empty_document():
    document = new_document(
        [
            Record("TargetModel", ["BCDx36HP"]),
            Record("FormatVersion", ["1.00"]),
            Record("Conventional", ["", "", "Empty", "", "", "Conventional", "", "", "", "", "", "", "", ""]),
            Record("File", ["HomePatrol Export File"]),
        ]
    )
    with pytest.raises(HpeValidationError, match="no-scannable-content"):
        require_valid_document(document)


def test_container_validation_rejects_noncanonical_gzip_timestamp():
    favorite = _favorite(Channel(id="c", label="Good", freq_mhz=154.1, mode="NFM"))
    text = serialize_records(builders.build_favorites_document(favorite.systems))
    noncanonical = codec.encode_container(text, mtime=123)
    issues = validate_hpe_container(noncanonical)
    assert any(issue.code == "container-determinism" for issue in issues)


def test_bundle_manifest_hashes_and_all_embedded_hpes_validate(tmp_path):
    catalog = load_baseline()
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    path = build_sentinel_import_pack(result, tmp_path / "pack.zip")
    validate_sentinel_import_pack(path)

    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        declared = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
        assert len([name for name in declared if name.endswith(".hpe")]) == 58
        for name, digest in declared.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest


def test_bundle_validation_detects_tampered_content(tmp_path):
    catalog = load_baseline()
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    path = build_sentinel_import_pack(result, tmp_path / "pack.zip")
    with zipfile.ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    contents["favorites.csv"] += b"tampered"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    with pytest.raises(BundleValidationError, match="checksum mismatch"):
        validate_sentinel_import_pack(path)


def test_bundle_validation_detects_unsafe_zip_path(tmp_path):
    path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../escape", b"x")
        archive.writestr("manifest.json", b'{"files":[]}')
    with pytest.raises(BundleValidationError, match="unsafe path"):
        validate_sentinel_import_pack(path)


def test_csv_and_markdown_readback_validation_detects_tampering():
    favorite = _favorite(Channel(id="c", label="Good", freq_mhz=154.1))
    with pytest.raises(BundleValidationError):
        validate_csv_bytes(b'"wrong"\r\n"value"\r\n', [favorite])
    with pytest.raises(BundleValidationError):
        validate_markdown_bytes(b"# Generated Favorites List Overview\nTotal lists: 1\n", [favorite])


def test_generate_removes_stale_loose_hpe_files(wasds_home, sample_csv_path, tmp_path):
    out = tmp_path / "out"
    hpe_dir = out / "hpe"
    hpe_dir.mkdir(parents=True)
    stale = hpe_dir / "STALE.hpe"
    stale.write_bytes(b"old")

    assert run(["--csv", str(sample_csv_path), "generate", "--out", str(out), "--formats", "hpe"]) == 0
    assert not stale.exists()
    assert sorted(path.name for path in hpe_dir.glob("*.hpe")) == ["FL01.hpe", "FL09a.hpe"]


def test_transactional_generation_preserves_previous_outputs_on_staging_failure(
    sample_csv_path, tmp_path, monkeypatch
):
    from wasds150.catalog import loader
    import wasds150.bundle.generate_outputs as output_module

    catalog = loader.load_csv(sample_csv_path)
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    out = tmp_path / "out"
    out.mkdir()
    old_csv = out / "favorites.csv"
    old_csv.write_bytes(b"previous-good-csv")

    def fail_markdown(*args, **kwargs):
        raise RuntimeError("simulated staging failure")

    monkeypatch.setattr(output_module, "export_markdown", fail_markdown)
    with pytest.raises(RuntimeError, match="simulated staging failure"):
        generate_outputs(result, out, ["csv", "md", "hpe"])
    assert old_csv.read_bytes() == b"previous-good-csv"
    assert not (out / "hpe").exists()


def test_transactional_hpe_publish_preserves_non_hpe_files_and_removes_stale_hpes(
    sample_csv_path, tmp_path
):
    from wasds150.catalog import loader

    catalog = loader.load_csv(sample_csv_path)
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    out = tmp_path / "out"
    hpe_dir = out / "hpe"
    hpe_dir.mkdir(parents=True)
    (hpe_dir / "notes.txt").write_text("keep me", encoding="utf-8")
    (hpe_dir / "STALE.hpe").write_bytes(b"old")

    generate_outputs(result, out, ["hpe"])
    assert (hpe_dir / "notes.txt").read_text(encoding="utf-8") == "keep me"
    assert not (hpe_dir / "STALE.hpe").exists()


def test_transactional_generation_restores_all_previous_outputs_on_mid_publish_failure(
    sample_csv_path, tmp_path, monkeypatch
):
    from wasds150.catalog import loader
    import wasds150.bundle.generate_outputs as output_module

    catalog = loader.load_csv(sample_csv_path)
    result = apply_profile(catalog, Profile(based_on_catalog_hash=catalog.content_hash()))
    out = tmp_path / "out"
    out.mkdir()
    old_csv = out / "favorites.csv"
    old_md = out / "favorites-overview.md"
    old_csv.write_bytes(b"old-csv")
    old_md.write_bytes(b"old-md")
    real_replace = output_module.os.replace

    def fail_on_staged_markdown(source, target):
        source_path = type(old_csv)(source)
        target_path = type(old_csv)(target)
        if (
            source_path.name == "favorites-overview.md"
            and target_path == old_md
            and source_path.parent != out
        ):
            raise OSError("simulated publish failure")
        return real_replace(source, target)

    monkeypatch.setattr(output_module.os, "replace", fail_on_staged_markdown)
    with pytest.raises(OSError, match="simulated publish failure"):
        generate_outputs(result, out, ["csv", "md"])
    assert old_csv.read_bytes() == b"old-csv"
    assert old_md.read_bytes() == b"old-md"


def test_installer_rejects_invalid_document_before_creating_backup(tmp_path):
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    invalid = builders.build_favorites_document([])
    backup_dir = tmp_path / "backups"
    with pytest.raises(InstallerError, match="no-scannable-content"):
        write_favorites_list(
            card,
            index=0,
            document=invalid,
            user_name="Invalid",
            backup_dir=backup_dir,
            dry_run=True,
        )
    assert not backup_dir.exists()


def test_installer_aborts_before_write_when_mandatory_backup_verification_fails(
    tmp_path, monkeypatch
):
    import wasds150.installer.writer as writer_module

    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    favorite = _favorite(Channel(id="c", label="Good", freq_mhz=154.1, mode="NFM"))
    document = builders.build_favorites_document(favorite.systems)
    monkeypatch.setattr(writer_module, "verify_backup", lambda path: ["simulated checksum failure"])

    with pytest.raises(InstallerError, match="backup failed verification"):
        write_favorites_list(
            card,
            index=0,
            document=document,
            user_name="Test",
            backup_dir=tmp_path / "backups",
            confirm_phrase=f"WRITE {card.name}",
            dry_run=False,
        )
    assert not (card / "BCDx36HP" / "favorites_lists" / "f_000000.hpd").exists()


def test_hpdb_extract_generation_adds_signature_and_passes_semantic_validation(
    wasds_home, synthetic_hpdb_state_path, tmp_path
):
    out = tmp_path / "extracted.hpe"
    assert run(
        [
            "hpe",
            "hpdb-extract",
            str(synthetic_hpdb_state_path),
            "--county-id",
            "5301",
            "--out",
            str(out),
        ]
    ) == 0
    assert validate_hpe_container(out.read_bytes()) == []
    document = parse_records(codec.decode_container(out.read_bytes()))
    assert document.records[-1].tag == "File"
