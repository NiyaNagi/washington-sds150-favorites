"""Explicit typed-confirmation gate for destructive SD-card writes.

Requiring the user to type back the exact volume label (rather than a
generic "yes") is a deliberate speed bump against confirming the wrong
volume by habit — the same discipline recommended for any irreversible
action against removable/external storage.
"""
from __future__ import annotations

from pathlib import Path


def confirm_phrase_for(mount_point: Path) -> str:
    """The exact phrase a caller must supply to authorize a write:
    ``WRITE <volume-name>``, e.g. ``WRITE SDS150``."""
    return f"WRITE {Path(mount_point).name}"


def verify_confirmation(provided: str, mount_point: Path) -> bool:
    return provided == confirm_phrase_for(mount_point)
