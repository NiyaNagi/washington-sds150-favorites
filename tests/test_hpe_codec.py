import gzip

import pytest

from wasds150.hpe import codec


def test_xor_is_self_inverse():
    data = b"\x00\x01\x02hello\xff"
    once = codec.xor_bytes(data)
    twice = codec.xor_bytes(once)
    assert twice == data
    assert once != data


def test_encode_decode_round_trip():
    text = "TargetModel\tBCDx36HP\r\nFormatVersion\t1.00\r\nFile\tHomePatrol Export File\r\n"
    encoded = codec.encode_container(text)
    decoded = codec.decode_container(encoded)
    assert decoded == text


def test_encode_produces_valid_gzip_after_xor():
    text = "TargetModel\tBCDx36HP\r\n"
    encoded = codec.encode_container(text)
    gz_bytes = codec.xor_bytes(encoded)
    assert gz_bytes[:2] == b"\x1f\x8b"  # gzip magic
    assert gzip.decompress(gz_bytes).decode("ascii") == text


def test_encode_is_deterministic_with_pinned_mtime():
    text = "TargetModel\tBCDx36HP\r\n"
    first = codec.encode_container(text)
    second = codec.encode_container(text)
    assert first == second


def test_decode_rejects_decompression_bomb():
    # A large repetitive text compresses tiny but decompresses huge.
    text = "A" * (200 * 1024)
    encoded = codec.encode_container(text)
    with pytest.raises(codec.HpeDecompressionLimitError):
        codec.decode_container(encoded, max_decompressed_size=1024)


def test_decode_within_limit_succeeds():
    text = "A" * 1000
    encoded = codec.encode_container(text)
    decoded = codec.decode_container(encoded, max_decompressed_size=2000)
    assert decoded == text


def test_decode_rejects_non_gzip_input():
    with pytest.raises(codec.HpeError):
        codec.decode_container(b"not a valid hpe file at all")


def test_validate_ascii_accepts_tab_cr_lf_and_printable():
    codec.validate_ascii("Hello\tWorld\r\n!@#$%^&*()")  # should not raise


def test_validate_ascii_rejects_control_chars():
    with pytest.raises(codec.HpeByteRangeError):
        codec.validate_ascii("bad\x00null")


def test_validate_ascii_rejects_high_bytes():
    with pytest.raises(codec.HpeByteRangeError):
        codec.validate_ascii("café")  # é is > 0x7E


def test_encode_rejects_invalid_ascii():
    with pytest.raises(codec.HpeByteRangeError):
        codec.encode_container("bad\x00null")


def test_has_signature_line_true_and_false():
    assert codec.has_signature_line("foo\r\nFile\tHomePatrol Export File\r\n")
    assert codec.has_signature_line("foo\r\nFile\tHomePatrol Export File")  # no trailing newline
    assert not codec.has_signature_line("foo\r\nbar\r\n")


def test_dialect_properties():
    bcd = codec.Dialect(target_model="BCDx36HP", format_version="1.00")
    assert bcd.is_bcdx36hp
    assert not bcd.is_homepatrol1
    assert bcd.is_known

    hp1 = codec.Dialect(target_model="HomePatrol-1", format_version="2.04")
    assert hp1.is_homepatrol1
    assert not hp1.is_bcdx36hp
    assert hp1.is_known

    unknown = codec.Dialect(target_model="Something-Else", format_version="9.99")
    assert not unknown.is_known


def test_real_nascar_fixture_round_trips(fixture_cache_dir):
    """Independent cross-check against a real, third-party .hpe container
    (see NOTICE.md); skipped if the fixture hasn't been fetched."""
    fixture = fixture_cache_dir / "nascarscanner_2026_season.hpe"
    if not fixture.exists():
        pytest.skip("external fixture not fetched; run scripts/fetch_hpe_fixtures.py")

    data = fixture.read_bytes()
    text = codec.decode_container(data)
    assert text.startswith("TargetModel\tHomePatrol-1\r\n")
    assert codec.has_signature_line(text)
    reencoded = codec.encode_container(text)
    assert codec.decode_container(reencoded) == text
