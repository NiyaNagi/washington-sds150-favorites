"""RepeaterBook data is never committed.

``docs/repeaterbook-api-compliance-design.md`` tells RepeaterBook that this
repository holds no RepeaterBook data. A link to repeaterbook.com as a
directory pointer is fine in prose. What must never happen is a committed
catalog row, catalog channel or radio programming file naming a RepeaterBook
repeater *data page* as its source -- that would mean the values came from
RepeaterBook, which this project may not redistribute.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from wasds150.catalog import baseline

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PAGE = re.compile(r"repeaterbook\.com/(?:repeaters|gmrs)/", re.IGNORECASE)


def _catalog_citations(catalog):
    for fl in catalog.favorites:
        yield fl.favorite_key, "source_url", fl.source_url
        for provenance in fl.provenance:
            yield fl.favorite_key, "provenance", provenance.source_url
        for system in fl.systems:
            for department in system.departments:
                for channel in department.channels:
                    yield fl.favorite_key, channel.label, channel.notes


def test_packaged_baseline_cites_no_repeaterbook_data_page():
    offenders = [
        (key, where)
        for key, where, text in _catalog_citations(baseline.load_baseline())
        if text and DATA_PAGE.search(text)
    ]
    assert offenders == []


def test_repo_csv_cites_no_repeaterbook_data_page():
    with (REPO_ROOT / "washington-sds150-favorites.csv").open(encoding="utf-8", newline="") as f:
        offenders = [
            (row["favorite_key"], column)
            for row in csv.DictReader(f)
            for column, value in row.items()
            if value and DATA_PAGE.search(value)
        ]
    assert offenders == []


def test_catalog_sources_cite_no_repeaterbook_data_page():
    """The hand-built channel tables and the packaged snapshot, as text, so a
    citation cannot hide in a module constant the snapshot does not reach."""
    roots = [REPO_ROOT / "src" / "wasds150" / "catalog", REPO_ROOT / "src" / "wasds150" / "data"]
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".json", ".csv"}
        and DATA_PAGE.search(path.read_text(encoding="utf-8", errors="replace"))
    ]
    assert offenders == []


def test_committed_radio_configs_cite_no_repeaterbook_data_page():
    """Every committed programming file and report, binary formats included."""
    needles = (b"repeaterbook.com/repeaters/", b"repeaterbook.com/gmrs/")
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in sorted((REPO_ROOT / "radio-configs").rglob("*"))
        if path.is_file() and any(needle in path.read_bytes().lower() for needle in needles)
    ]
    assert offenders == []
