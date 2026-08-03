"""CSV export of the generated (profile-applied) Favorites List set.

Byte-compatible with the original catalog CSV shape (same 14 columns, same
QUOTE_ALL/CRLF conventions) so it can be diffed against
``washington-sds150-favorites.csv`` or reopened by any spreadsheet tool.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from wasds150.catalog.loader import write_csv
from wasds150.bundle.validation import validate_csv_bytes
from wasds150.models.catalog import Catalog, FavoritesList


def export_csv(favorites: List[FavoritesList], path: Path) -> Path:
    write_csv(Catalog(favorites=list(favorites)), path)
    validate_csv_bytes(path.read_bytes(), favorites)
    return path
