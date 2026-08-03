import pytest

from wasds150.hpe.record import Record, RecordDocument, new_document, parse_records, serialize_records


def test_parse_simple_record():
    doc = parse_records("Conventional\t\t\tName\tOff\r\n")
    assert len(doc.records) == 1
    r = doc.records[0]
    assert r.tag == "Conventional"
    assert r.fields == ["", "", "Name", "Off"]
    assert r.arity == 5
    assert doc.line_endings == ["\r\n"]


def test_round_trip_preserves_mixed_line_endings():
    text = "A\t1\r\nB\t2\nC\t3\rD\t4"
    doc = parse_records(text)
    assert doc.line_endings == ["\r\n", "\n", "\r", ""]
    assert serialize_records(doc) == text


def test_round_trip_preserves_unknown_tags_and_blank_fields():
    text = "SomeFutureTag\t\t\tfoo\t\t\r\nAnotherTag\r\n"
    doc = parse_records(text)
    assert serialize_records(doc) == text
    assert doc.records[0].tag == "SomeFutureTag"
    assert doc.records[1].fields == []


def test_round_trip_empty_text():
    doc = parse_records("")
    assert doc.records == []
    assert serialize_records(doc) == ""


def test_record_get_with_default():
    r = Record(tag="X", fields=["a", "b"])
    assert r.get(0) == "a"
    assert r.get(1) == "b"
    assert r.get(2) is None
    assert r.get(2, "fallback") == "fallback"
    assert r.get(-1) is None


def test_record_render():
    r = Record(tag="Trunk", fields=["", "name", ""])
    assert r.render() == "Trunk\t\tname\t"


def test_find_all_and_find_first():
    doc = parse_records("A\t1\r\nB\t2\r\nA\t3\r\n")
    assert [r.fields for r in doc.find_all("A")] == [["1"], ["3"]]
    assert doc.find_first("A").fields == ["1"]
    assert doc.find_first("Z") is None


def test_record_document_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        RecordDocument(records=[Record(tag="A")], line_endings=[])


def test_new_document_applies_uniform_line_ending():
    doc = new_document([Record(tag="A", fields=["1"]), Record(tag="B", fields=["2"])], line_ending="\r\n")
    assert doc.line_endings == ["\r\n", "\r\n"]
    assert serialize_records(doc) == "A\t1\r\nB\t2\r\n"


def test_real_repo_fixture_round_trips_byte_identical(synthetic_bcdx36hp_path):
    text = synthetic_bcdx36hp_path.read_text(encoding="ascii")
    doc = parse_records(text)
    assert serialize_records(doc) == text
