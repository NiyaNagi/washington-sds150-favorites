"""Conversion between the on-disk catalog CSV, the canonical JSON snapshot,
and in-memory :class:`~wasds150.models.catalog.Catalog` objects.

The CSV round trip is byte-faithful (same quoting, CRLF line endings, column
order) so ``load_csv(write_csv(load_csv(path)))`` reproduces the original
file exactly — this is what pins the packaged baseline to the human-curated
``washington-sds150-favorites.csv`` in this repository.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from wasds150.catalog.ids import slugify
from wasds150.models.catalog import CSV_FIELDS, Catalog, FavoritesList
from wasds150.models.provenance import Provenance

CSV_LINE_TERMINATOR = "\r\n"


def load_csv(path: Path) -> Catalog:
    """Load the flat catalog CSV into a :class:`Catalog`.

    Each row becomes one baseline :class:`FavoritesList` with a single
    provenance entry pointing at that row's own ``source_url`` (the citation
    the human curators already recorded), tagged as the ``static_pack``
    source adapter.
    """
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or tuple(reader.fieldnames) != CSV_FIELDS:
            raise ValueError(
                f"Unexpected CSV columns in {path}: {reader.fieldnames!r} "
                f"(expected {CSV_FIELDS!r})"
            )
        favorites: List[FavoritesList] = []
        for row in reader:
            provenance = [
                Provenance(source_adapter="static_pack", source_url=row.get("source_url") or None)
            ]
            favorites.append(FavoritesList.from_csv_row(row, provenance=provenance))
    return Catalog(favorites=favorites)


def write_csv(catalog: Catalog, path: Path) -> None:
    """Write a :class:`Catalog` back out in the exact format of the original
    catalog CSV (QUOTE_ALL, CRLF line endings, original column order).

    Only baseline-shaped fields are written; ``enabled``/``flqk``/``origin``
    and structured ``systems``/``provenance`` are not representable in this
    legacy flat format (use JSON for a lossless snapshot).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=list(CSV_FIELDS), quoting=csv.QUOTE_ALL, lineterminator=CSV_LINE_TERMINATOR
        )
        writer.writeheader()
        for fl in catalog.favorites:
            writer.writerow(fl.csv_row())


def save_json(catalog: Catalog, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(catalog.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_json(path: Path) -> Catalog:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Catalog.from_dict(data)
