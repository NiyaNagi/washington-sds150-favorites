import pytest

from wasds150.util.hashing import canonical_json, content_hash, sha256_of, sha256_of_bytes, stable_id


def test_canonical_json_is_key_order_independent():
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_canonical_json_is_deterministic_string():
    data = {"x": [1, 2, 3], "y": None, "z": "hello"}
    assert canonical_json(data) == '{"x":[1,2,3],"y":null,"z":"hello"}'


def test_content_hash_stable_across_dict_construction_order():
    h1 = content_hash({"a": 1, "b": 2})
    h2 = content_hash({"b": 2, "a": 1})
    assert h1 == h2


def test_content_hash_changes_with_content():
    assert content_hash({"a": 1}) != content_hash({"a": 2})


def test_stable_id_deterministic():
    id1 = stable_id("fl01")
    id2 = stable_id("fl01")
    assert id1 == id2


def test_stable_id_varies_by_slug_and_kind():
    assert stable_id("fl01") != stable_id("fl02")
    assert stable_id("fl01", kind="favorites_list") != stable_id("fl01", kind="system")


def test_sha256_of_bytes_matches_sha256_of_for_ascii_text():
    """Both hash functions must agree for content that's valid in either
    representation, since callers (e.g. wasds150.bundle.manifest) may
    hash a mix of text and binary files with the byte-safe variant."""
    text = "hello world"
    assert sha256_of_bytes(text.encode("utf-8")) == sha256_of(text)


def test_sha256_of_bytes_handles_non_utf8_binary_content():
    """A real .hpe file is XOR/gzip binary, not valid UTF-8 -- this must
    never raise a UnicodeDecodeError the way naively decoding it as text
    first would."""
    binary_data = bytes([0x1F, 0x8B, 0x87, 0x00, 0xFF, 0xFE])
    with pytest.raises(UnicodeDecodeError):
        binary_data.decode("utf-8")
    digest = sha256_of_bytes(binary_data)
    assert len(digest) == 64
    assert digest == sha256_of_bytes(binary_data)  # deterministic


def test_sha256_of_bytes_differs_for_different_content():
    assert sha256_of_bytes(b"a") != sha256_of_bytes(b"b")
