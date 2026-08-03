"""The Sentinel-ready export bundle: CSV + Markdown overview + one
importable ``.hpe`` per non-empty Favorites List + a signed-content
manifest, zipped together.

Every enabled Favorites List whose ``systems`` were populated (see
:mod:`wasds150.recipes.systems` — the free-text/seed tier runs
automatically, with zero setup, for every ``generate``; a local Sentinel
HPDB/RadioReference Premium match adds the rest once configured) gets a
real, decode/validate-checked ``.hpe`` file under ``hpe/`` in this bundle
(see :mod:`wasds150.bundle.hpe_export`) — this project's own ``.hpe``
codec is no longer "not yet implemented" (see git history for that
now-stale claim); a row that still has no systems gets an explicit,
actionable warning instead of a silently-empty/missing file.
"""
from __future__ import annotations

import tempfile
import zipfile
import os
from pathlib import Path
from typing import List

from wasds150.bundle.csv_export import export_csv
from wasds150.bundle.hpe_export import HpeExportResult, build_per_list_hpe
from wasds150.bundle.manifest import build_manifest, write_manifest
from wasds150.bundle.markdown_export import export_markdown
from wasds150.bundle.validation import validate_sentinel_import_pack
from wasds150.generate.pipeline import GeneratedResult

_INSTRUCTIONS = """\
Sentinel Import Instructions
=============================

This bundle's hpe/ directory contains one importable .hpe file per
Favorites List that has structured system data (see manifest.json's
"hpe_warnings" for any list that does not, and why — usually because it
needs a local Sentinel HPDB export or RadioReference Premium match; run
'wasds150 sources configure' + 'wasds150 sources update --apply', or the
web UI's Advanced > Sources panel, then regenerate).

1. Open Sentinel and load your scanner project.
2. For each file in hpe/, use Sentinel's own "Import Favorites List"
   (File > Import, or drag-and-drop, depending on your Sentinel version)
   to bring it in as a new or replacement Favorites List.
3. Save the Sentinel project, then write it to your scanner as usual.
4. For any Favorites List with no hpe/<key>.hpe file (see the warning
   list), use favorites.csv/favorites-overview.md as your reference while
   building it manually via Sentinel's "Append to Favorites List"
   workflow instead (see this repo's
   washington-sds150-programming-checklist.md, "Build Order" section, for
   the recommended phase-by-phase build order) — do not hand-type a large
   trunked system.
5. Keep this bundle (and its manifest.json content hash) alongside your
   Sentinel project backup so you can tell which generated snapshot it
   came from later.
"""


def build_sentinel_import_pack(
    result: GeneratedResult,
    output_zip: Path,
    *,
    hpe_export: HpeExportResult = None,
) -> Path:
    favorites = result.enabled_favorites
    output_zip = Path(output_zip)
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="wasds150-bundle-") as tmp:
        base_dir = Path(tmp)
        csv_path = export_csv(favorites, base_dir / "favorites.csv")
        md_path = export_markdown(favorites, base_dir / "favorites-overview.md")
        instructions_path = base_dir / "SENTINEL_IMPORT_INSTRUCTIONS.txt"
        instructions_path.write_text(_INSTRUCTIONS, encoding="utf-8")

        hpe_export = hpe_export or build_per_list_hpe(favorites)
        hpe_dir = base_dir / "hpe"
        hpe_paths: List[Path] = []
        if hpe_export.files:
            hpe_dir.mkdir(parents=True, exist_ok=True)
            for filename, hpe_bytes in hpe_export.files.items():
                hpe_path = hpe_dir / filename
                hpe_path.write_bytes(hpe_bytes)
                hpe_paths.append(hpe_path)

        content_files: List[Path] = [csv_path, md_path, instructions_path] + hpe_paths
        manifest = build_manifest(
            catalog_hash=result.catalog_hash,
            profile_hash=result.profile_hash,
            content_hash=result.content_hash,
            counts=result.counts,
            warnings=list(result.warnings) + hpe_export.warnings,
            files=content_files,
            base_dir=base_dir,
        )
        manifest_path = write_manifest(manifest, base_dir / "manifest.json")

        fd, candidate_name = tempfile.mkstemp(prefix=output_zip.name + ".", suffix=".tmp", dir=output_zip.parent)
        os.close(fd)
        candidate = Path(candidate_name)
        try:
            with zipfile.ZipFile(candidate, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in content_files + [manifest_path]:
                    arcname = str(path.relative_to(base_dir))
                    zf.write(path, arcname=arcname)
            validate_sentinel_import_pack(candidate)
            os.replace(candidate, output_zip)
        finally:
            if candidate.exists():
                candidate.unlink()

    return output_zip
