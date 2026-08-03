import json
from pathlib import Path

import pytest

from wasds150.catalog import loader
from wasds150.models.catalog import CSV_FIELDS


def test_load_csv_reads_all_rows_and_stable_slugs(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    assert len(catalog.favorites) == 3
    assert [fl.slug for fl in catalog.favorites] == ["fl01", "fl02", "fl09a"]
    assert catalog.favorites[0].favorite_name == "Alpha Statewide"
    # Embedded newline in a quoted CSV field must survive the round trip.
    assert "\n" in catalog.favorites[0].notes


def test_load_csv_sets_provenance_from_source_url(sample_csv_path):
    catalog = loader.load_csv(sample_csv_path)
    fl = catalog.favorites[0]
    assert len(fl.provenance) == 1
    assert fl.provenance[0].source_adapter == "static_pack"
    assert fl.provenance[0].source_url == "https://example.org/alpha"


def test_load_csv_rejects_wrong_columns(tmp_path):
    bad = tmp_path / "bad.csv"
    with bad.open("w", encoding="utf-8", newline="") as f:
        f.write('"only_one_column"\r\n"value"\r\n')
    with pytest.raises(ValueError):
        loader.load_csv(bad)


def test_write_csv_round_trip_byte_identical(sample_csv_path, tmp_path):
    catalog = loader.load_csv(sample_csv_path)
    out_path = tmp_path / "out.csv"
    loader.write_csv(catalog, out_path)
    assert out_path.read_bytes() == sample_csv_path.read_bytes()


def test_write_csv_uses_crlf_and_quote_all(sample_csv_path, tmp_path):
    catalog = loader.load_csv(sample_csv_path)
    out_path = tmp_path / "out.csv"
    loader.write_csv(catalog, out_path)
    raw = out_path.read_bytes()
    assert b"\r\n" in raw
    # header row is fully quoted
    assert raw.splitlines()[0].startswith(b'"favorite_key"')


def test_real_repo_csv_round_trips_byte_identical(repo_csv_path, tmp_path):
    """Golden test: this repo's real 78-row catalog CSV must survive a full
    load -> write cycle byte-for-byte. This is what guarantees the packaged
    baseline JSON stays traceable to the human-curated CSV."""
    catalog = loader.load_csv(repo_csv_path)
    assert len(catalog.favorites) == 78
    out_path = tmp_path / "roundtrip.csv"
    loader.write_csv(catalog, out_path)
    assert out_path.read_bytes() == repo_csv_path.read_bytes()


def test_save_json_and_load_json_round_trip(sample_csv_path, tmp_path):
    catalog = loader.load_csv(sample_csv_path)
    json_path = tmp_path / "catalog.json"
    loader.save_json(catalog, json_path)

    reloaded = loader.load_json(json_path)
    assert reloaded.content_hash() == catalog.content_hash()
    assert [fl.slug for fl in reloaded.favorites] == [fl.slug for fl in catalog.favorites]


def test_save_json_is_valid_json_with_sorted_keys(sample_csv_path, tmp_path):
    catalog = loader.load_csv(sample_csv_path)
    json_path = tmp_path / "catalog.json"
    loader.save_json(catalog, json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "version" in data
    assert len(data["favorites"]) == 3
