"""Tests for wasds150.bundle.hpe_export: per-Favorites-List .hpe export
with safe filenames, decode/validate-before-finalizing, and actionable
"no systems yet" warnings instead of a silently empty/missing file."""
from __future__ import annotations

from wasds150.bundle.hpe_export import (
    HpeExportResult,
    build_per_list_hpe,
    hpe_filename_for,
    safe_filename_component,
)
from wasds150.hpe import codec, schema
from wasds150.hpe.record import parse_records
from wasds150.models.catalog import Channel, Department, FavoritesList, System


def _fl(favorite_key, slug=None, systems=None, favorite_name=None, enabled=True):
    slug = slug or favorite_key.lower()
    return FavoritesList(
        id=slug,
        slug=slug,
        favorite_key=favorite_key,
        favorite_name=favorite_name or f"{favorite_key} name",
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
        enabled=enabled,
        systems=systems or [],
    )


def _system_with_one_channel(freq_mhz=154.28):
    return System(
        id="s1",
        label="Test System",
        departments=[
            Department(id="d1", label="Ops", channels=[Channel(id="c1", label="Ch1", freq_mhz=freq_mhz, mode="NFM")])
        ],
    )


# ------------------------------------------------------------- filenames --
def test_safe_filename_component_sanitizes_unsafe_characters():
    assert safe_filename_component("FL09a") == "FL09a"
    assert safe_filename_component("weird/name:here*") == "weird_name_here"
    assert safe_filename_component("   ") == "list"
    assert safe_filename_component("") == "list"


def test_hpe_filename_for_deterministic_and_disambiguates_collisions():
    used = {}
    fl1 = _fl("FL01")
    fl2 = _fl("FL01", slug="fl01-local")  # same favorite_key, different row
    name1 = hpe_filename_for(fl1, used)
    name2 = hpe_filename_for(fl2, used)
    assert name1 == "FL01.hpe"
    assert name2 == "FL01-2.hpe"


def test_hpe_filename_for_is_order_dependent_not_iteration_order_dependent():
    """Disambiguation must follow the caller's own favorites order, not
    dict/set iteration order (which is a documented determinism
    requirement for this project)."""
    used_a = {}
    used_b = {}
    fl1, fl2 = _fl("FL01"), _fl("FL01", slug="other")
    seq1 = [hpe_filename_for(fl1, used_a), hpe_filename_for(fl2, used_a)]
    seq2 = [hpe_filename_for(fl1, used_b), hpe_filename_for(fl2, used_b)]
    assert seq1 == seq2 == ["FL01.hpe", "FL01-2.hpe"]


# --------------------------------------------------------- build_per_list_hpe
def test_build_per_list_hpe_produces_valid_decodable_hpe_for_populated_row():
    fl = _fl("FL01", systems=[_system_with_one_channel()])
    result = build_per_list_hpe([fl])
    assert set(result.files) == {"FL01.hpe"}
    assert result.warnings == []

    hpe_bytes = result.files["FL01.hpe"]
    text = codec.decode_container(hpe_bytes)
    assert schema.validate_schema(parse_records(text)) == []
    assert "Test System" in text


def test_build_per_list_hpe_skips_empty_systems_with_actionable_warning():
    fl = _fl("FL04", favorite_name="WA State Patrol (WSP)", systems=[])
    result = build_per_list_hpe([fl])
    assert result.files == {}
    assert len(result.warnings) == 1
    assert "FL04" in result.warnings[0]
    assert "WA State Patrol (WSP)" in result.warnings[0]
    assert "HPDB" in result.warnings[0] or "RadioReference" in result.warnings[0]


def test_build_per_list_hpe_mixed_batch():
    populated = _fl("FL01", systems=[_system_with_one_channel()])
    empty = _fl("FL04", systems=[])
    result = build_per_list_hpe([populated, empty])
    assert set(result.files) == {"FL01.hpe"}
    assert len(result.warnings) == 1


def test_build_per_list_hpe_is_deterministic():
    fl = _fl("FL01", systems=[_system_with_one_channel()])
    result1 = build_per_list_hpe([fl])
    result2 = build_per_list_hpe([fl])
    assert result1.files == result2.files
    assert result1.warnings == result2.warnings


def test_build_per_list_hpe_empty_input():
    result = build_per_list_hpe([])
    assert result.files == {}
    assert result.warnings == []


def test_build_per_list_hpe_multiple_populated_rows_get_distinct_filenames():
    fl1 = _fl("FL01", systems=[_system_with_one_channel(154.28)])
    fl2 = _fl("FL02", systems=[_system_with_one_channel(155.0)])
    result = build_per_list_hpe([fl1, fl2])
    assert set(result.files) == {"FL01.hpe", "FL02.hpe"}


def test_hpe_export_result_files_preserve_input_order():
    fl1 = _fl("FL02", systems=[_system_with_one_channel()])
    fl2 = _fl("FL01", systems=[_system_with_one_channel()])
    result = build_per_list_hpe([fl1, fl2])
    assert list(result.files.keys()) == ["FL02.hpe", "FL01.hpe"]


def test_hpe_export_result_default_construction():
    result = HpeExportResult()
    assert result.files == {}
    assert result.warnings == []
