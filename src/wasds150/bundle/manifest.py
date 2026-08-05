"""Bundle manifest: what got generated, from what, with what hashes.

Every export bundle includes a ``manifest.json`` so its provenance and
integrity can be checked later (e.g. before trusting a bundle enough to
write it to an SD card, once that phase exists).
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List

from wasds150 import __version__
from wasds150.util.hashing import sha256_of_bytes


def file_hash(path: Path) -> str:
    """Binary-safe file content hash — a bundle can contain both text
    (CSV/Markdown/instructions) and binary (``.hpe``) files, so this reads
    bytes rather than assuming UTF-8 text (a real ``.hpe`` file is
    XOR/gzip binary and is not valid UTF-8 — see
    :mod:`wasds150.bundle.hpe_export`)."""
    return sha256_of_bytes(path.read_bytes())


def build_manifest(
    *,
    catalog_hash: str,
    profile_hash: str,
    content_hash: str,
    counts: Dict[str, int],
    warnings: List[str],
    files: List[Path],
    base_dir: Path,
) -> Dict[str, Any]:
    return {
        "generator": "wasds150",
        "generator_version": __version__,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "catalog_hash": catalog_hash,
        "profile_hash": profile_hash,
        "content_hash": content_hash,
        "counts": counts,
        "warnings": warnings,
        "files": [
            {"path": p.relative_to(base_dir).as_posix(), "sha256": file_hash(p)} for p in files
        ],
    }


def write_manifest(manifest: Dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
