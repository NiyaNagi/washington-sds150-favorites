from wasds150.hpe import codec
from wasds150.hpe.record import Record, RecordDocument, parse_records
from wasds150.hpe.schema import (
    BCDX36HP_SCHEMA,
    F_LIST_SCHEMA,
    SERVICE_TYPES,
    detect_dialect,
    format_ctcss_tone,
    format_dcs_tone,
    format_p25_nac,
    validate_schema,
)


def test_all_schema_arities_are_documented_and_nonempty():
    for tag, schema in BCDX36HP_SCHEMA.items():
        assert schema.tag == tag
        assert len(schema.arities) >= 1
        assert all(a > 0 for a in schema.arities)


def test_field_by_name_lookup():
    schema = BCDX36HP_SCHEMA["C-Freq"]
    spec = schema.field_by_name("freq_hz")
    assert spec is not None
    assert spec.index == 5
    assert schema.field_by_name("does-not-exist") is None


def test_t_freq_accepts_both_documented_widths():
    schema = BCDX36HP_SCHEMA["T-Freq"]
    assert schema.arities == (8, 9)


def test_detect_dialect_bcdx36hp():
    doc = parse_records("TargetModel\tBCDx36HP\r\nFormatVersion\t1.00\r\n")
    dialect = detect_dialect(doc)
    assert dialect == codec.Dialect(target_model="BCDx36HP", format_version="1.00")


def test_detect_dialect_missing_header_returns_none():
    doc = parse_records("Conventional\t\t\tName\r\n")
    assert detect_dialect(doc) is None


def test_validate_schema_on_synthetic_fixture_has_no_issues(synthetic_bcdx36hp_path):
    text = synthetic_bcdx36hp_path.read_text(encoding="ascii")
    doc = parse_records(text)
    assert validate_schema(doc) == []


def test_validate_schema_flags_wrong_arity():
    doc = RecordDocument(
        records=[
            Record(tag="TargetModel", fields=["BCDx36HP"]),
            Record(tag="FormatVersion", fields=["1.00"]),
            Record(tag="Conventional", fields=["only", "three", "fields"]),  # should be 15
        ],
        line_endings=["\r\n", "\r\n", "\r\n"],
    )
    issues = validate_schema(doc)
    assert len(issues) == 1
    assert "Conventional" in issues[0]
    assert "expected (15,)" in issues[0]


def test_validate_schema_ignores_unknown_tags():
    doc = RecordDocument(
        records=[
            Record(tag="TargetModel", fields=["BCDx36HP"]),
            Record(tag="FormatVersion", fields=["1.00"]),
            Record(tag="TotallyMadeUpFutureTag", fields=["a", "b", "c"]),
        ],
        line_endings=["\r\n", "\r\n", "\r\n"],
    )
    assert validate_schema(doc) == []


def test_validate_schema_skips_non_bcdx36hp_dialect():
    doc = parse_records("TargetModel\tHomePatrol-1\r\nFormatVersion\t2.04\r\n")
    issues = validate_schema(doc)
    assert len(issues) == 1
    assert "not BCDx36HP" in issues[0]


def test_validate_schema_no_header_reports_issue():
    doc = parse_records("Conventional\t\t\tfoo\r\n")
    issues = validate_schema(doc)
    assert len(issues) == 1
    assert "no TargetModel/FormatVersion header" in issues[0]


def test_validate_schema_explicit_dialect_overrides_detection():
    doc = parse_records("Conventional\t\t\tName\r\n")  # arity 4, wrong (should be 15)
    dialect = codec.Dialect(target_model="BCDx36HP", format_version="1.00")
    issues = validate_schema(doc, dialect=dialect)
    assert len(issues) == 1


def test_f_list_schema_arity_and_named_fields():
    assert F_LIST_SCHEMA.arities == (118,)
    assert F_LIST_SCHEMA.field_by_name("user_name").index == 1
    assert F_LIST_SCHEMA.field_by_name("monitor").index == 4
    assert F_LIST_SCHEMA.field_by_name("s_qkey_00").index == 17
    assert F_LIST_SCHEMA.field_by_name("s_qkey_99").index == 116


def test_tone_formatting_helpers():
    assert format_ctcss_tone(156.7) == "TONE=C156.7"
    assert format_dcs_tone("023") == "D023"
    assert format_p25_nac("293") == "NAC=293"
    assert format_p25_nac("Srch") == "NAC=Srch"


def test_service_types_table_has_documented_codes():
    assert SERVICE_TYPES[3] == "Fire Dispatch"
    assert SERVICE_TYPES[4] == "EMS Dispatch"
    assert SERVICE_TYPES[216] == "Racing Officials"
    assert SERVICE_TYPES[217] == "Racing Teams"
    assert 5 not in SERVICE_TYPES  # documented as unused
