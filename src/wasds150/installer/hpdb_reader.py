"""Read-only HPDB access on an SD card.

Strictly read-only: this module only ever reads
``<mount>/BCDx36HP/HPDB/hpdb.cfg`` and its ``s_<StateId>.hpd`` siblings — it
never writes there. The write path (:mod:`wasds150.installer.writer`) only
ever touches ``favorites_lists/``; ``HPDB/`` is not on its allow-list and
this module doesn't change that — see :mod:`wasds150.installer.paths`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from wasds150.hpe.hpdb import CountyIndex, read_hpdb_cfg, read_state_hpd
from wasds150.hpe.record import RecordDocument
from wasds150.installer.paths import HPDB_DIR

_STATE_FILE_RE = re.compile(r"^s_(\d+)\.hpd$", re.IGNORECASE)


@dataclass
class HpdbCard:
    """Everything read from one card's ``HPDB/`` directory."""

    hpdb_cfg: Optional[RecordDocument] = None
    state_files: Dict[int, RecordDocument] = field(default_factory=dict)

    @property
    def county_index(self) -> Optional[CountyIndex]:
        if self.hpdb_cfg is None:
            return None
        return CountyIndex.from_hpdb_cfg(self.hpdb_cfg)


def hpdb_dir_for(mount_point: Path) -> Path:
    return Path(mount_point) / HPDB_DIR


def has_hpdb(mount_point: Path) -> bool:
    hpdb_dir = hpdb_dir_for(mount_point)
    return hpdb_dir.is_dir() and (hpdb_dir / "hpdb.cfg").is_file()


def read_card_hpdb(mount_point: Path) -> HpdbCard:
    """Read (never write) every HPDB file on ``mount_point``: ``hpdb.cfg``
    plus every ``s_<StateId>.hpd`` sibling found in the same directory."""
    hpdb_dir = hpdb_dir_for(mount_point)
    card = HpdbCard()

    cfg_path = hpdb_dir / "hpdb.cfg"
    if cfg_path.is_file():
        card.hpdb_cfg = read_hpdb_cfg(cfg_path)

    if hpdb_dir.is_dir():
        for entry in sorted(hpdb_dir.iterdir()):
            match = _STATE_FILE_RE.match(entry.name)
            if match:
                card.state_files[int(match.group(1))] = read_state_hpd(entry)

    return card
