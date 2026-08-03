"""Read-after-write validation for every generated bundle artifact."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import List

from wasds150.hpe.validation import HpeValidationError, require_valid_hpe_container
from wasds150.models.catalog import CSV_FIELDS, FavoritesList


class BundleValidationError(ValueError):
    pass


def validate_csv_bytes(data: bytes, favorites: List[FavoritesList]) -> None:
    try:
        text = data.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise BundleValidationError(f"CSV is not readable: {exc}") from exc
    columns = tuple(rows[0].keys()) if rows else tuple(CSV_FIELDS)
    if columns != tuple(CSV_FIELDS):
        raise BundleValidationError("CSV columns do not match the canonical 14-column schema")
    expected = [favorite.favorite_key for favorite in favorites]
    actual = [row["favorite_key"] for row in rows]
    if actual != expected:
        raise BundleValidationError(f"CSV Favorites List order/content mismatch: expected {expected}, got {actual}")


def validate_markdown_bytes(data: bytes, favorites: List[FavoritesList]) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BundleValidationError(f"Markdown is not UTF-8: {exc}") from exc
    if f"Total lists: {len(favorites)}" not in text:
        raise BundleValidationError("Markdown total does not match generated Favorites Lists")
    for favorite in favorites:
        if f"| {favorite.favorite_key} |" not in text:
            raise BundleValidationError(f"Markdown is missing {favorite.favorite_key}")


def validate_sentinel_import_pack(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise BundleValidationError("ZIP contains duplicate entry names")
            for name in names:
                posix = PurePosixPath(name)
                if posix.is_absolute() or ".." in posix.parts or "\\" in name:
                    raise BundleValidationError(f"ZIP contains unsafe path {name!r}")
            if "manifest.json" not in names:
                raise BundleValidationError("ZIP is missing manifest.json")
            manifest = json.loads(archive.read("manifest.json"))
            manifest_files = manifest.get("files")
            if not isinstance(manifest_files, list):
                raise BundleValidationError("manifest.json has no files list")
            declared = {entry.get("path"): entry.get("sha256") for entry in manifest_files}
            actual_content = set(names) - {"manifest.json"}
            if set(declared) != actual_content:
                raise BundleValidationError(
                    f"manifest file set mismatch: declared={sorted(declared)}, actual={sorted(actual_content)}"
                )
            for name, expected_hash in declared.items():
                data = archive.read(name)
                actual_hash = hashlib.sha256(data).hexdigest()
                if actual_hash != expected_hash:
                    raise BundleValidationError(f"checksum mismatch for {name}")
                if name.endswith(".hpe"):
                    try:
                        require_valid_hpe_container(data, context=name)
                    except HpeValidationError as exc:
                        raise BundleValidationError(str(exc)) from exc
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, KeyError) as exc:
        raise BundleValidationError(f"invalid Sentinel import pack: {exc}") from exc
