from wasds150.hpe import flist
from wasds150.hpe.record import Record, new_document


def _sample_f_list_text() -> str:
    doc = new_document(
        [
            Record(tag="TargetModel", fields=["BCDx36HP"]),
            Record(tag="FormatVersion", fields=["1.00"]),
            flist.new_entry("Home County", "f_000000.hpd"),
        ],
        line_ending="\r\n",
    )
    return flist.render(doc)


def test_new_entry_matches_observed_real_defaults():
    entry = flist.new_entry("My List", "f_000001.hpd")
    assert entry.tag == "F-List"
    assert entry.arity == 118
    assert entry.get(0) == "My List"  # user_name (0-based fields index for column 1)
    assert entry.get(1) == "f_000001.hpd"  # filename
    assert entry.get(2) == "Off"  # location_control
    assert entry.get(3) == "On"  # monitor
    assert entry.get(4) == "0"  # quick_key
    assert entry.get(5) == "Off"  # number_tag
    assert all(v == "Off" for v in entry.fields[6:])  # every StartupKey/S-Qkey slot


def test_parse_f_list_and_find_entry_by_filename():
    text = _sample_f_list_text()
    doc = flist.parse_f_list(text)
    assert len(flist.entries(doc)) == 1
    entry = flist.find_entry_by_filename(doc, "f_000000.hpd")
    assert entry is not None
    assert entry.get(0) == "Home County"
    assert flist.find_entry_by_filename(doc, "does-not-exist.hpd") is None


def test_patch_entry_only_touches_user_name_and_monitor():
    original = flist.new_entry("Old Name", "f_000000.hpd")
    # Simulate a user having customized QuickKey/NumberTag/StartupKeys away
    # from the fresh-entry defaults, to prove patch_entry never touches them.
    customized = Record(tag="F-List", fields=list(original.fields))
    customized.fields[4] = "7"  # quick_key
    customized.fields[6] = "On"  # startup_key_0

    patched = flist.patch_entry(customized, user_name="New Name", monitor="Off")

    assert patched.get(0) == "New Name"
    assert patched.get(3) == "Off"  # monitor changed
    assert patched.get(4) == "7"  # quick_key preserved verbatim
    assert patched.get(6) == "On"  # startup_key_0 preserved verbatim
    assert patched.get(1) == customized.get(1)  # filename untouched
    assert patched.fields[7:] == customized.fields[7:]  # everything else untouched


def test_patch_entry_partial_update_leaves_other_field_alone():
    original = flist.new_entry("Name", "f_000000.hpd")
    patched = flist.patch_entry(original, monitor="Off")  # user_name not given
    assert patched.get(0) == "Name"  # unchanged
    assert patched.get(3) == "Off"  # changed


def test_patch_entry_rejects_wrong_tag():
    bad = Record(tag="NotFList", fields=[])
    try:
        flist.patch_entry(bad, user_name="x")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_render_round_trips():
    text = _sample_f_list_text()
    doc = flist.parse_f_list(text)
    assert flist.render(doc) == text


def test_real_f_list_fixture_parses_with_expected_arity(fixture_cache_dir):
    import pytest

    fixture = fixture_cache_dir / "platypus_f_list.cfg"
    if not fixture.exists():
        pytest.skip("external fixture not fetched; run scripts/fetch_hpe_fixtures.py")
    text = fixture.read_text(encoding="ascii")
    doc = flist.parse_f_list(text)
    entries = flist.entries(doc)
    assert len(entries) == 1
    assert entries[0].arity == 118
