"""Shared, validated, transactional publisher for CLI and web generation."""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

from wasds150.bundle.csv_export import export_csv
from wasds150.bundle.hpe_export import HpeExportResult, build_per_list_hpe
from wasds150.bundle.markdown_export import export_markdown
from wasds150.bundle.sentinel_import_pack import build_sentinel_import_pack
from wasds150.generate.pipeline import GeneratedResult

VALID_FORMATS = frozenset({"csv", "md", "zip", "hpe"})


@dataclass
class PublishedOutputs:
    files: List[Path] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _copy_preserved_non_hpe(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    for child in source.iterdir():
        if child.is_file() and child.suffix.lower() != ".hpe":
            shutil.copy2(child, destination / child.name)


def generate_outputs(result: GeneratedResult, out_dir: Path, formats: Sequence[str]) -> PublishedOutputs:
    """Build and validate every requested artifact in a staging directory,
    then publish the complete set as one rollback-capable transaction."""
    normalized = [str(fmt).strip().lower() for fmt in formats if str(fmt).strip()]
    unknown = sorted(set(normalized) - VALID_FORMATS)
    if unknown:
        raise ValueError(f"unknown format(s): {', '.join(unknown)}")

    out_dir = Path(out_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    hpe_export: HpeExportResult = (
        build_per_list_hpe(result.enabled_favorites)
        if "zip" in normalized or "hpe" in normalized
        else HpeExportResult()
    )

    with tempfile.TemporaryDirectory(prefix=".wasds150-generate-", dir=out_dir.parent) as tmp:
        stage_root = Path(tmp)
        staged_targets = []
        returned_files: List[Path] = []

        if "csv" in normalized:
            staged = export_csv(result.enabled_favorites, stage_root / "favorites.csv")
            target = out_dir / "favorites.csv"
            staged_targets.append((staged, target))
            returned_files.append(target)
        if "md" in normalized:
            staged = export_markdown(result.enabled_favorites, stage_root / "favorites-overview.md")
            target = out_dir / "favorites-overview.md"
            staged_targets.append((staged, target))
            returned_files.append(target)
        if "zip" in normalized:
            staged = build_sentinel_import_pack(
                result,
                stage_root / "sentinel-import-pack.zip",
                hpe_export=hpe_export,
            )
            target = out_dir / "sentinel-import-pack.zip"
            staged_targets.append((staged, target))
            returned_files.append(target)
        if "hpe" in normalized:
            staged_hpe = stage_root / "hpe"
            staged_hpe.mkdir()
            _copy_preserved_non_hpe(out_dir / "hpe", staged_hpe)
            for filename, data in hpe_export.files.items():
                (staged_hpe / filename).write_bytes(data)
                returned_files.append(out_dir / "hpe" / filename)
            staged_targets.append((staged_hpe, out_dir / "hpe"))

        out_dir.mkdir(parents=True, exist_ok=True)
        backup_root = stage_root / ".previous"
        backup_root.mkdir()
        published = []
        backed_up = []
        try:
            for index, (staged, target) in enumerate(staged_targets):
                if target.exists():
                    backup = backup_root / f"{index}-{target.name}"
                    os.replace(target, backup)
                    backed_up.append((backup, target))
                os.replace(staged, target)
                published.append(target)
        except Exception:
            for target in reversed(published):
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
            for backup, target in reversed(backed_up):
                os.replace(backup, target)
            raise

    return PublishedOutputs(files=returned_files, warnings=list(hpe_export.warnings))
