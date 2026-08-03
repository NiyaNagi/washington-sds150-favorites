"""Independent cross-checks against real, third-party HPE fixtures.

These fixtures are never vendored (see NOTICE.md); they are fetched on
demand into ``.fixture-cache/`` by ``scripts/fetch_hpe_fixtures.py``. Every
test here skips cleanly if its fixture is absent (no network access, or the
script hasn't been run) — the project's own synthetic fixture
(``tests/fixtures/wasds150_synthetic_bcdx36hp.hpd``) is what CI depends on;
these are supplementary, best-effort validation only.
"""
from __future__ import annotations

import pytest

from wasds150.hpe import codec, schema
from wasds150.hpe.record import parse_records, serialize_records


def _require_fixture(fixture_cache_dir, name):
    path = fixture_cache_dir / name
    if not path.exists():
        pytest.skip(f"external fixture {name} not fetched; run scripts/fetch_hpe_fixtures.py")
    return path


def test_platypus_synthetic_hpd_matches_our_schema_exactly(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_f_example.hpd")
    text = path.read_text(encoding="ascii")
    doc = parse_records(text)

    dialect = schema.detect_dialect(doc)
    assert dialect == codec.Dialect(target_model="BCDx36HP", format_version="1.00")

    issues = schema.validate_schema(doc, dialect)
    assert issues == [], f"our schema disagrees with a real BCDx36HP fixture: {issues}"

    # Byte-exact round trip through our generic, lossless record layer.
    assert serialize_records(doc) == text


def test_platypus_fixture_tag_arities_match_our_table(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_f_example.hpd")
    doc = parse_records(path.read_text(encoding="ascii"))

    observed_arities = {}
    for record in doc.records:
        observed_arities.setdefault(record.tag, set()).add(record.arity)

    for tag, arities in observed_arities.items():
        if tag not in schema.BCDX36HP_SCHEMA:
            continue
        for arity in arities:
            assert arity in schema.BCDX36HP_SCHEMA[tag].arities, (
                f"{tag}: real fixture has arity {arity}, our schema only allows "
                f"{schema.BCDX36HP_SCHEMA[tag].arities}"
            )


def test_platypus_t_freq_is_9_fields_confirming_the_documented_quirk(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "platypus_f_example.hpd")
    doc = parse_records(path.read_text(encoding="ascii"))
    t_freq = doc.find_first("T-Freq")
    assert t_freq is not None
    assert t_freq.arity == 9  # not the 8-field written spec


def test_nascar_hpe_containers_use_homepatrol1_dialect_not_bcdx36hp(fixture_cache_dir):
    path = _require_fixture(fixture_cache_dir, "nascarscanner_2026_season.hpe")
    text = codec.decode_container(path.read_bytes())
    doc = parse_records(text)
    dialect = schema.detect_dialect(doc)
    assert dialect == codec.Dialect(target_model="HomePatrol-1", format_version="2.04")
    # Confirms the documented column-shift pitfall: HomePatrol-1's
    # Conventional/C-Group name field is one column later than BCDx36HP's.
    conventional = doc.find_first("Conventional")
    assert conventional.get(3) not in ("", None)  # name at col4 (fields idx 3) in this dialect
