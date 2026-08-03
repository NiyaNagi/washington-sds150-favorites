import json
import zipfile

from wasds150.bundle.csv_export import export_csv
from wasds150.bundle.manifest import build_manifest, file_hash, write_manifest
from wasds150.bundle.markdown_export import export_markdown, render_markdown
from wasds150.bundle.sentinel_import_pack import build_sentinel_import_pack
from wasds150.catalog import loader
from wasds150.generate.pipeline import apply_profile
from wasds150.models.profile import Profile


def test_export_csv_matches_columns(sample_csv_path, tmp_path):
    catalog = loader.load_csv(sample_csv_path)
    out = tmp_path / "out.csv"
    export_csv(catalog.favorites, out)
    reloaded = loader.load_csv(out)
    assert [fl.slug for fl in reloaded.favorites] == [fl.slug for fl in catalog.favorites]


def test_render_markdown_contains_expected_rows(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    md = render_markdown(catalog.favorites, generated_at="2024-01-01T00:00:00Z")
    assert "Generated Favorites List Overview" in md
    assert "FL01" in md
    assert "Alpha Statewide" in md
    assert "Total lists: 3" in md


def test_render_markdown_escapes_pipe_and_newlines(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    md = render_markdown(catalog.favorites)
    # the sample notes field on FL01 contains an embedded newline; ensure it
    # doesn't break the markdown table structure.
    lines = [l for l in md.splitlines() if l.startswith("| FL01")]
    assert len(lines) == 1


def test_export_markdown_writes_file(sample_csv_path, tmp_path):
    catalog = loader.load_csv(sample_csv_path)
    out = tmp_path / "overview.md"
    export_markdown(catalog.favorites, out)
    assert out.exists()
    assert "FL01" in out.read_text(encoding="utf-8")


def test_build_manifest_hashes_files(tmp_path):
    f1 = tmp_path / "a.txt"
    f1.write_text("hello", encoding="utf-8")
    manifest = build_manifest(
        catalog_hash="c", profile_hash="p", content_hash="h", counts={}, warnings=[], files=[f1], base_dir=tmp_path
    )
    assert manifest["files"][0]["path"] == "a.txt"
    assert manifest["files"][0]["sha256"] == file_hash(f1)
    assert manifest["generator"] == "wasds150"


def test_write_manifest_produces_valid_json(tmp_path):
    manifest = {"a": 1}
    path = write_manifest(manifest, tmp_path / "manifest.json")
    assert json.loads(path.read_text(encoding="utf-8")) == manifest


def test_build_sentinel_import_pack_contains_expected_files(sample_csv_path, tmp_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    result = apply_profile(catalog, profile)
    zip_path = build_sentinel_import_pack(result, tmp_path / "pack.zip")

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        # FL01 ("ALPHA1 155.000") and FL09a ("CTAF 122.800") each carry an
        # explicit literal frequency -- Tier C (see
        # wasds150.recipes.systems.static_systems_for) picks them up
        # automatically, so both get a real per-list .hpe. FL02's
        # "Bravo Dispatch, [E]-ENCRYPTED" has no explicit frequency at
        # all, so it is skipped with an actionable warning instead (see
        # below) rather than an empty/fake .hpe.
        assert names == {
            "favorites.csv",
            "favorites-overview.md",
            "SENTINEL_IMPORT_INSTRUCTIONS.txt",
            "manifest.json",
            "hpe/FL01.hpe",
            "hpe/FL09a.hpe",
        }
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["content_hash"] == result.content_hash
        assert manifest["counts"] == result.counts
        assert len(manifest["files"]) == 5  # csv + md + instructions + 2 hpe (not manifest itself)
        assert any("FL02" in w for w in manifest["warnings"])

        # Every produced .hpe decodes and validates cleanly.
        from wasds150.hpe import codec, schema
        from wasds150.hpe.record import parse_records

        for name in ("hpe/FL01.hpe", "hpe/FL09a.hpe"):
            text = codec.decode_container(zf.read(name))
            assert schema.validate_schema(parse_records(text)) == []


def test_build_sentinel_import_pack_only_includes_enabled_favorites(sample_csv_path, tmp_path):
    catalog = loader.load_csv(sample_csv_path)
    profile = Profile()
    profile.set_enabled("fl02", False)
    result = apply_profile(catalog, profile)
    zip_path = build_sentinel_import_pack(result, tmp_path / "pack.zip")

    with zipfile.ZipFile(zip_path) as zf:
        csv_bytes = zf.read("favorites.csv")
        assert b"FL02" not in csv_bytes
        assert b"FL01" in csv_bytes
