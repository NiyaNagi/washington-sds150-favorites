"""Shared path constants and the write allow-list for the SD-card installer.

Layout confirmed identically by two independent projects (see NOTICE.md):

    <card>/BCDx36HP/favorites_lists/f_list.cfg    — index (one F-List/line)
    <card>/BCDx36HP/favorites_lists/f_NNNNNN.hpd  — one list, plain text,
                                                     CRLF, NO gzip/XOR
    <card>/BCDx36HP/HPDB/                          — full RR database
    <card>/BCDx36HP/profile.cfg                    — display settings
    <card>/BCDx36HP/app_data.cfg                   — resume state; MUST be
                                                     deleted after any
                                                     program-data write
    <card>/BCDx36HP/discvery.cfg                   — (sic) a third, separate
                                                     config file — never the
                                                     favorites index

The installer is only ever permitted to **write** inside
``favorites_lists/`` (new/updated ``.hpd`` files and ``f_list.cfg``) and to
**delete** ``app_data.cfg``. ``HPDB/``, ``profile.cfg``, and ``discvery.cfg``
are never touched by this project — :func:`is_within_allowed_write_path`
enforces that as a hard allow-list, not just a convention.
"""
from __future__ import annotations

from pathlib import Path

BCDX36HP_DIR = "BCDx36HP"
FAVORITES_LISTS_DIR = f"{BCDX36HP_DIR}/favorites_lists"
F_LIST_CFG = f"{FAVORITES_LISTS_DIR}/f_list.cfg"
APP_DATA_CFG = f"{BCDX36HP_DIR}/app_data.cfg"
HPDB_DIR = f"{BCDX36HP_DIR}/HPDB"
PROFILE_CFG = f"{BCDX36HP_DIR}/profile.cfg"
#: Sic — misspelled on real cards; never confuse with f_list.cfg.
DISCOVERY_CFG = f"{BCDX36HP_DIR}/discvery.cfg"

#: Uniden's own documented ceiling on the number of Favorites Lists (also
#: in wasds150.hpe.schema.MAX_FAVORITES_LISTS; repeated here so this module
#: has no import dependency on hpe).
MAX_FAVORITES_LISTS = 256


def hpd_filename(index: int) -> str:
    if not (0 <= index < MAX_FAVORITES_LISTS):
        raise ValueError(f"favorites list index {index} out of range [0, {MAX_FAVORITES_LISTS})")
    return f"f_{index:06d}.hpd"


def is_sds150_card(mount_point: Path) -> bool:
    """The documented marker for an SDS150-family card: a ``BCDx36HP``
    directory at the volume root."""
    marker = Path(mount_point) / BCDX36HP_DIR
    return marker.is_dir() and not marker.is_symlink()


def is_within_allowed_write_path(mount_point: Path, target: Path) -> bool:
    """True only for ``favorites_lists/f_list.cfg`` or
    ``favorites_lists/f_NNNNNN.hpd`` under ``mount_point`` — the sole
    allow-listed write targets."""
    mount_point = Path(mount_point)
    configured_dir = mount_point / FAVORITES_LISTS_DIR
    if configured_dir.is_symlink() or Path(target).is_symlink():
        return False
    try:
        mount_resolved = mount_point.resolve()
        allowed_dir = configured_dir.resolve()
        resolved = Path(target).resolve()
    except OSError:
        return False
    try:
        allowed_dir.relative_to(mount_resolved)
    except ValueError:
        return False
    if resolved.parent != allowed_dir:
        return False
    if resolved.name == "f_list.cfg":
        return True
    return resolved.name.startswith("f_") and resolved.suffix == ".hpd"


def is_allowed_delete_path(mount_point: Path, target: Path) -> bool:
    """True only for ``app_data.cfg`` under ``mount_point`` — the sole
    allow-listed delete target."""
    mount_point = Path(mount_point)
    expected = (mount_point / APP_DATA_CFG).resolve()
    try:
        resolved = Path(target).resolve()
    except OSError:
        return False
    return resolved == expected
