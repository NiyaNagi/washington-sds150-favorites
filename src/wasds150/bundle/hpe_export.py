"""Per-Favorites-List ``.hpe`` export: one importable file per enabled,
non-empty :class:`~wasds150.models.catalog.FavoritesList`.

This is the piece that turns a populated ``FavoritesList.systems`` (see
:mod:`wasds150.recipes.systems`) into the actual importable artifact a
Sentinel user drags onto their project — closing the gap the audit
flagged as finding #2 ("`generate` CLI/UI emits CSV/Markdown/legacy zip
but no per-list HPE files"). :func:`wasds150.hpe.builders.build_favorites_list_hpe`
already did the hard part (canonical model -> ``.hpe`` bytes); this module
adds the missing plumbing around it:

* **Skip, don't silently "succeed empty"**: a row with no ``systems`` at
  all produces a clear, actionable warning (naming the row and what it
  needs — a local Sentinel HPDB/RadioReference Premium match, or manual
  entry) instead of an empty or missing file that looks like success.
* **Safe, deterministic filenames**: derived from the row's own stable
  ``favorite_key``, sanitized to a small safe character set, with a
  numeric suffix on the rare collision (e.g. two local lists that
  sanitize to the same name) — resolved deterministically by favorites
  order, never by dict/set iteration order.
* **Decode/validate before finalizing**: every generated ``.hpe`` is
  immediately decoded back (:func:`wasds150.hpe.codec.decode_container`)
  and arity-validated (:func:`wasds150.hpe.schema.validate_schema`) before
  being handed to a caller — a row that fails either check is reported as
  a warning and excluded, rather than shipping bytes nobody has confirmed
  are importable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from wasds150.hpe import builders as hpe_builders
from wasds150.hpe import codec as hpe_codec
from wasds150.hpe import schema as hpe_schema
from wasds150.hpe.record import parse_records
from wasds150.models.catalog import FavoritesList

#: Characters kept verbatim in a generated filename; everything else
#: becomes "_". Deliberately conservative (safe on Windows/macOS/Linux
#: filesystems and inside a zip archive alike).
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


@dataclass
class HpeExportResult:
    #: ``filename -> .hpe bytes``, in the same order ``favorites`` was
    #: given (Python 3.7+ dicts preserve insertion order).
    files: Dict[str, bytes] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def safe_filename_component(text: str, *, default: str = "list") -> str:
    """Sanitize ``text`` to a small safe character set for use as (part
    of) a filename. Never returns an empty string."""
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", text.strip()).strip("_")
    return cleaned or default


def _unique_filename(base: str, used: Dict[str, int]) -> str:
    """Deterministically disambiguate ``base`` against filenames already
    handed out (in favorites order, never dict/set iteration order) by
    appending ``-2``, ``-3``, ... on a collision."""
    count = used.get(base, 0)
    used[base] = count + 1
    if count == 0:
        return f"{base}.hpe"
    return f"{base}-{count + 1}.hpe"


def hpe_filename_for(fl: FavoritesList, used: Dict[str, int]) -> str:
    base = safe_filename_component(fl.favorite_key or fl.slug)
    return _unique_filename(base, used)


def build_per_list_hpe(favorites: List[FavoritesList]) -> HpeExportResult:
    """Build one ``.hpe`` per entry in ``favorites`` that has 1+ populated
    ``systems`` — callers typically pass
    :attr:`wasds150.generate.pipeline.GeneratedResult.enabled_favorites`.
    Every produced file is decode/validate-checked before being included;
    a row that is empty, or that somehow fails validation, is reported as
    a warning and skipped rather than shipped as an empty/broken file.
    """
    result = HpeExportResult()
    used_names: Dict[str, int] = {}

    for fl in favorites:
        if not fl.systems:
            result.warnings.append(
                f"{fl.favorite_key} ({fl.favorite_name}): no structured systems available; skipping .hpe. "
                "This usually means the row needs a local Sentinel HPDB export or RadioReference "
                "Premium match (see 'wasds150 sources configure' / 'wasds150 sources update --apply') "
                "-- or you can add systems by hand via 'wasds150 hpe build'."
            )
            continue

        hpe_bytes = hpe_builders.build_favorites_list_hpe(fl)
        if len(hpe_bytes) > hpe_schema.MAX_FAVORITES_LIST_BYTES:
            result.warnings.append(
                f"{fl.favorite_key} ({fl.favorite_name}): generated .hpe is {len(hpe_bytes)} bytes, "
                f"over Uniden's documented {hpe_schema.MAX_FAVORITES_LIST_BYTES}-byte per-list limit; skipping."
            )
            continue

        try:
            text = hpe_codec.decode_container(hpe_bytes)
        except hpe_codec.HpeError as exc:
            result.warnings.append(f"{fl.favorite_key} ({fl.favorite_name}): generated .hpe failed to decode: {exc}")
            continue

        doc = parse_records(text)
        issues = hpe_schema.validate_schema(doc)
        if issues:
            result.warnings.append(
                f"{fl.favorite_key} ({fl.favorite_name}): generated .hpe failed schema validation: {issues}"
            )
            continue

        filename = hpe_filename_for(fl, used_names)
        result.files[filename] = hpe_bytes

    return result
