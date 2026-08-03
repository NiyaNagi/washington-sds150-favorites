"""Generic, lossless tab-record model.

The `.hpe`/`.hpd`/`f_list.cfg` text format is a flat sequence of lines, each
a TAB-separated tag followed by fields (e.g. ``Conventional\\t\\t\\tName\\t...``).
:func:`parse_records` / :func:`serialize_records` round-trip this **exactly**
byte-for-byte for *any* well-formed input, including unknown tags and
unknown/blank fields — per line, the exact terminator used (``\\r\\n``,
``\\n``, or none for a final unterminated line) is preserved individually
rather than assumed uniform, since a bare LF has been observed mixed into
otherwise-CRLF real files.

This module deliberately knows nothing about what any particular tag
*means* — that semantic layer (arities, named columns, tone/service-type
encoding) lives in :mod:`wasds150.hpe.schema`. Keeping them separate is what
makes the parser genuinely lossless: it never has to understand a field to
preserve it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Record:
    """One tab-delimited line: a tag plus its ordered, raw string fields."""

    tag: str
    fields: List[str] = field(default_factory=list)

    def get(self, index: int, default: Optional[str] = None) -> Optional[str]:
        return self.fields[index] if 0 <= index < len(self.fields) else default

    @property
    def arity(self) -> int:
        """Total column count *including* the tag itself (column 0), which
        is how arities are documented/cited in :mod:`wasds150.hpe.schema`."""
        return 1 + len(self.fields)

    def render(self) -> str:
        return "\t".join([self.tag] + self.fields)


@dataclass
class RecordDocument:
    """An ordered list of :class:`Record` plus the exact line terminator
    used after each one, so serialization reproduces the original bytes."""

    records: List[Record] = field(default_factory=list)
    line_endings: List[str] = field(default_factory=list)  # "\r\n" | "\n" | "\r" | ""

    def __post_init__(self) -> None:
        if len(self.line_endings) != len(self.records):
            raise ValueError(
                f"line_endings length ({len(self.line_endings)}) must match "
                f"records length ({len(self.records)})"
            )

    def find_all(self, tag: str) -> List[Record]:
        return [r for r in self.records if r.tag == tag]

    def find_first(self, tag: str) -> Optional[Record]:
        for r in self.records:
            if r.tag == tag:
                return r
        return None


def parse_records(text: str) -> RecordDocument:
    """Parse tab-delimited text into a lossless :class:`RecordDocument`.

    Uses ``str.splitlines(keepends=True)`` specifically so each line's
    original terminator (or lack thereof, for a final unterminated line) is
    captured individually rather than assumed uniform across the file.
    """
    records: List[Record] = []
    endings: List[str] = []
    for raw_line in text.splitlines(keepends=True):
        if raw_line.endswith("\r\n"):
            content, ending = raw_line[:-2], "\r\n"
        elif raw_line.endswith("\n"):
            content, ending = raw_line[:-1], "\n"
        elif raw_line.endswith("\r"):
            content, ending = raw_line[:-1], "\r"
        else:
            content, ending = raw_line, ""
        parts = content.split("\t")
        records.append(Record(tag=parts[0], fields=parts[1:]))
        endings.append(ending)
    return RecordDocument(records=records, line_endings=endings)


def serialize_records(doc: RecordDocument) -> str:
    """Inverse of :func:`parse_records`: reproduces the original text
    exactly, including per-line terminators, for any document that came
    from (or was constructed to look like) ``parse_records`` output."""
    parts = []
    for record, ending in zip(doc.records, doc.line_endings):
        parts.append(record.render() + ending)
    return "".join(parts)


def new_document(records: List[Record], line_ending: str = "\r\n") -> RecordDocument:
    """Build a fresh :class:`RecordDocument` from scratch (e.g. for a
    builder), applying the same line ending to every record. ``\\r\\n`` is
    the standard observed terminator for `.hpe`/`.hpd` content."""
    return RecordDocument(records=list(records), line_endings=[line_ending] * len(records))
