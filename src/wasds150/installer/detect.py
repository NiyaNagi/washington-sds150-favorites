"""Removable-volume detection.

Splits deliberately into two layers:

* :func:`scan_candidates` — pure, fully unit-testable: given a list of
  candidate directories (in tests, simulated volumes under ``tmp_path``),
  checks each for the documented ``BCDx36HP`` marker directory.
* :func:`list_os_candidate_mount_points` — thin, OS-specific enumeration of
  *real* removable-volume mount points (macOS ``/Volumes``, Windows via
  PowerShell ``Get-Volume``, best-effort ``/media``/``/mnt`` on Linux). This
  layer depends on real hardware/OS state and is intentionally **not**
  unit-tested — per the task's "simulated-volume tests only" requirement,
  all installer tests exercise :func:`scan_candidates` and above with
  simulated directories, never this function.

:func:`detect_volumes` is the convenience entry point the CLI/UI use; it
defers to the OS layer only when the caller doesn't supply candidates
itself (as every test does).
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from wasds150.installer.paths import is_sds150_card


@dataclass
class RemovableVolume:
    mount_point: Path
    label: str = ""
    is_sds150_candidate: bool = False


def scan_candidates(candidate_dirs: List[Path]) -> List[RemovableVolume]:
    volumes: List[RemovableVolume] = []
    for raw in candidate_dirs:
        d = Path(raw)
        if not d.is_dir():
            continue
        volumes.append(
            RemovableVolume(mount_point=d, label=d.name, is_sds150_candidate=is_sds150_card(d))
        )
    return volumes


def list_os_candidate_mount_points() -> List[Path]:  # pragma: no cover - real-hardware only
    """Best-effort real removable-volume enumeration. Never raises — returns
    ``[]`` on any unsupported platform or subprocess/filesystem error."""
    candidates: List[Path] = []
    try:
        if sys.platform == "darwin":
            volumes_dir = Path("/Volumes")
            if volumes_dir.is_dir():
                candidates = [p for p in volumes_dir.iterdir() if p.is_dir()]
        elif sys.platform.startswith("win"):
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Volume | Select-Object -ExpandProperty DriveLetter"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    candidates.append(Path(f"{line}:\\"))
        else:
            for base in (Path("/media"), Path("/mnt"), Path("/run/media")):
                if not base.is_dir():
                    continue
                for entry in base.iterdir():
                    if entry.is_dir():
                        # Some Linux distros mount removable media directly
                        # under /media/<label>, others under
                        # /media/<user>/<label>; include both shapes.
                        candidates.append(entry)
                        candidates.extend(p for p in entry.iterdir() if p.is_dir())
    except (OSError, subprocess.SubprocessError):
        return []
    return candidates


def detect_volumes(candidate_dirs: Optional[List[Path]] = None) -> List[RemovableVolume]:
    dirs = candidate_dirs if candidate_dirs is not None else list_os_candidate_mount_points()
    return scan_candidates(dirs)
