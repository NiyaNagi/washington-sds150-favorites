"""The `.hpe` container codec: XOR(0x0C) <-> gzip <-> tab-delimited text.

Verified directly against a real, third-party `.hpe` file (see
``scripts/fetch_hpe_fixtures.py`` / ``NOTICE.md``): XORing every byte of a
`.hpe` file with the constant ``0x0C`` yields a standard RFC-1952 gzip
stream (confirmed by observing the resulting bytes start with the gzip
magic ``1f 8b``); decompressing that stream yields plain ASCII, tab- and
CRLF-delimited text ending in the literal signature line
``File\\tHomePatrol Export File\\r\\n``. This module is an original
implementation of that (now-public, previously reverse-engineered) fact —
see ``NOTICE.md`` for the full attribution/sourcing discipline.

Two independent safety properties are enforced beyond the bare algorithm:

* **Decompression-bomb guard**: ``decode_container`` never inflates more
  than ``max_decompressed_size`` bytes, raising
  :class:`HpeDecompressionLimitError` instead of exhausting memory on a
  malicious/corrupt input.
* **Byte-range validation**: the observed real-world `.hpe`/`.hpd` dialect is
  strict ASCII ``0x20``-``0x7E`` plus TAB/CR/LF only; anything else
  (including an embedded NUL) is rejected rather than silently passed
  through, so a corrupt decode fails loudly instead of producing bytes that
  would corrupt a downstream tab-record parse.
"""
from __future__ import annotations

import gzip
import io
from dataclasses import dataclass

#: Single-byte XOR key. Self-inverse: the same operation both encodes and
#: decodes. Confirmed by observing that XORing a real `.hpe` file with this
#: constant yields the gzip magic bytes ``1f 8b``.
XOR_KEY = 0x0C

#: Literal trailer line observed at the end of every real `.hpe` export
#: (both dialects), not counting its CRLF terminator.
SIGNATURE_LINE = "File\tHomePatrol Export File"

#: Conservative default cap on inflated size. Real favorites lists are
#: small (Uniden's own documented per-list limit is 1 MB; see
#: ``wasds150.hpe.schema.MAX_FAVORITES_LIST_BYTES``); 64 MiB comfortably
#: covers a large multi-list bundle while still bounding a decompression
#: bomb to a small, fixed amount of memory.
DEFAULT_MAX_DECOMPRESSED_SIZE = 64 * 1024 * 1024

#: Bytes allowed in the decoded inner text: printable ASCII, TAB, CR, LF.
_ALLOWED_CONTROL_BYTES = frozenset({0x09, 0x0A, 0x0D})


class HpeError(Exception):
    """Base class for all `.hpe` codec errors."""


class HpeDecompressionLimitError(HpeError):
    """Raised when decompressing a `.hpe` payload would exceed the
    configured size limit (decompression-bomb guard)."""


class HpeByteRangeError(HpeError):
    """Raised when decoded text contains a byte outside the documented
    strict-ASCII + TAB/CR/LF range (see module docstring)."""


def xor_bytes(data: bytes, key: int = XOR_KEY) -> bytes:
    """Apply the self-inverse XOR obfuscation/de-obfuscation."""
    return bytes(b ^ key for b in data)


def validate_ascii(text: str) -> None:
    """Raise :class:`HpeByteRangeError` if ``text`` contains any character
    outside printable ASCII (0x20-0x7E) plus TAB/CR/LF."""
    for index, ch in enumerate(text):
        code = ord(ch)
        if code in _ALLOWED_CONTROL_BYTES:
            continue
        if 0x20 <= code <= 0x7E:
            continue
        raise HpeByteRangeError(
            f"byte 0x{code:02x} at text offset {index} is outside the allowed "
            "range (printable ASCII 0x20-0x7E, or TAB/CR/LF)"
        )


def _gunzip_with_limit(data: bytes, max_size: int) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as gz:
            chunk = gz.read(max_size + 1)
    except OSError as exc:
        raise HpeError(f"not a valid gzip stream after XOR de-obfuscation: {exc}") from None
    if len(chunk) > max_size:
        raise HpeDecompressionLimitError(
            f"decompressed payload exceeds the {max_size}-byte limit; refusing to continue "
            "(possible decompression bomb, or max_decompressed_size is too small)"
        )
    return chunk


def decode_container(
    hpe_bytes: bytes, *, max_decompressed_size: int = DEFAULT_MAX_DECOMPRESSED_SIZE
) -> str:
    """`.hpe` bytes -> inner tab-delimited text.

    Raises :class:`HpeDecompressionLimitError` if the payload would inflate
    past ``max_decompressed_size``, or :class:`HpeByteRangeError` if the
    decoded text contains bytes outside the documented allowed range.
    """
    gz_bytes = xor_bytes(hpe_bytes)
    raw = _gunzip_with_limit(gz_bytes, max_decompressed_size)
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise HpeByteRangeError(f"decompressed payload is not ASCII: {exc}") from None
    validate_ascii(text)
    return text


def encode_container(text: str, *, mtime: int = 0, compresslevel: int = 9) -> bytes:
    """Inner tab-delimited text -> `.hpe` bytes.

    ``mtime=0`` is pinned (rather than the current time, which
    ``gzip.compress``'s default would embed) so that encoding the same text
    twice always produces byte-identical output — a real reference
    generator that does *not* pin ``mtime`` was observed to embed the
    current time, making its output non-reproducible; we deliberately avoid
    that pitfall for a deterministic tool.
    """
    validate_ascii(text)
    gz_bytes = gzip.compress(text.encode("ascii"), compresslevel=compresslevel, mtime=mtime)
    return xor_bytes(gz_bytes)


@dataclass(frozen=True)
class Dialect:
    """The two header fields that identify which `.hpe`/`.hpd` column
    layout a document uses. See ``wasds150.hpe.schema`` for why this
    matters: the two known dialects have *shifted column offsets* for the
    same tags."""

    target_model: str
    format_version: str

    @property
    def is_bcdx36hp(self) -> bool:
        return self.target_model == "BCDx36HP"

    @property
    def is_homepatrol1(self) -> bool:
        return self.target_model == "HomePatrol-1"

    @property
    def is_known(self) -> bool:
        return self.is_bcdx36hp or self.is_homepatrol1


def has_signature_line(text: str) -> bool:
    """True if ``text`` ends with the standard export-file signature line
    (allowing for a trailing CRLF/LF or none)."""
    return text.rstrip("\r\n").endswith(SIGNATURE_LINE)
