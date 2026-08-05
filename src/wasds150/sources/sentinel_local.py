"""Local Sentinel/SDS150-card HPDB source — read-only, user-local only.

Reads the on-card RadioReference "HPDB" database that Uniden's Sentinel
software (or the radio itself) writes to
``<card>/BCDx36HP/HPDB/hpdb.cfg`` + ``s_<StateId>.hpd`` (schema and parser
documented/tested in :mod:`wasds150.hpe.hpdb`, built from a real
independently-fetched fixture in an earlier phase). This is the *only*
adapter in this project that is allowed to read arbitrarily-detailed
trunked-system data (site/department/TGID granularity), because that level
of detail is RadioReference's own compiled database, not something this
project may legally redistribute or re-derive from public sources.

**Strictly user-local, never redistributed**: facts produced here are
tagged ``source_id="sentinel_local"`` and are only ever written into the
*user's own* generated bundle/profile on their own machine — this project
never bundles, commits, caches-to-share, or otherwise republishes any HPDB
content (see ``NOTICE.md`` and ``installer/hpdb_reader.py``'s read-only
guarantee). No network access of any kind — ``kind = "local"`` and
``fetch()`` never uses an ``http_client`` even if one is passed.

**Facts carry the full record tree, not just a summary**: each
``fact_type="system"`` fact's ``raw`` dict includes ``"records"`` — a
JSON-safe serialization (see
:func:`wasds150.hpe.hpdb.serialize_system_slice`) of that system's entire
``Conventional``/``Trunk`` record tree — plus ``"sid"``, the system's own
numeric RadioReference id. Both stay strictly local (never written to any
shared/committed artifact); :mod:`wasds150.recipes.systems` uses them to
convert a matched recipe's fact back into a real, populated
:class:`wasds150.models.catalog.System` (site/department/channel detail
intact) rather than only attaching provenance, which is what makes a real
per-list ``.hpe`` export possible for a trunked baseline row.

Two ways to point this adapter at data, both read-only:

* ``mount_point`` — a directory that looks like an SDS150 card (i.e. has
  ``BCDx36HP/HPDB/hpdb.cfg``), read via
  :mod:`wasds150.installer.hpdb_reader` (works whether or not the card is
  actually plugged in as a real removable volume — a synced/backed-up copy
  on local disk works identically).
* ``hpdb_cfg_path`` — point directly at an ``hpdb.cfg`` file (with sibling
  ``s_*.hpd`` files in the same directory), for users who copied just the
  HPDB folder off a card rather than mounting the whole card.

If neither is supplied, :func:`discover_local_hpdb_paths` best-effort scans
common removable-volume mount points (reusing
:mod:`wasds150.installer.detect`) for a card; finding nothing is not an
error — it just means this source produces zero facts (public sources
still work standalone).
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Any, List, Optional

from wasds150.installer.detect import list_os_candidate_mount_points, scan_candidates
from wasds150.installer.hpdb_reader import HpdbCard, has_hpdb, hpdb_dir_for, read_card_hpdb
from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult

_STATE_FILE_RE = re.compile(r"^s_(\d+)\.hpd$", re.IGNORECASE)


def discover_local_hpdb_paths(candidate_dirs: Optional[List[Path]] = None) -> List[Path]:
    """Best-effort discovery of mount points that carry an HPDB folder.
    Never raises; returns ``[]`` if nothing is found or on unsupported
    platforms (mirrors :func:`wasds150.installer.detect.detect_volumes`'s
    "never fail hardware scanning" contract)."""
    dirs = candidate_dirs if candidate_dirs is not None else list_os_candidate_mount_points()
    volumes = scan_candidates(dirs)
    return [v.mount_point for v in volumes if has_hpdb(v.mount_point)]


class SentinelLocalSource(OnlineSourceAdapter):
    name = "sentinel_local"
    available = True
    kind = "local"

    def __init__(
        self,
        mount_point: Optional[Path] = None,
        hpdb_cfg_path: Optional[Path] = None,
        state: str = "WA",
    ):
        if mount_point is not None and hpdb_cfg_path is not None:
            raise ValueError("pass at most one of mount_point / hpdb_cfg_path, not both")
        self.mount_point = Path(mount_point) if mount_point is not None else None
        self.hpdb_cfg_path = Path(hpdb_cfg_path) if hpdb_cfg_path is not None else None
        self.state = state

    def _read_hpdb_dir(self, hpdb_dir: Path) -> HpdbCard:
        from wasds150.hpe.hpdb import read_hpdb_cfg, read_state_hpd

        card = HpdbCard(hpdb_cfg=read_hpdb_cfg(hpdb_dir / "hpdb.cfg"))
        for entry in sorted(hpdb_dir.iterdir()):
            m = _STATE_FILE_RE.match(entry.name)
            if m:
                card.state_files[int(m.group(1))] = read_state_hpd(entry)
        return card

    def _read(self) -> Optional[HpdbCard]:
        if self.mount_point is not None:
            if not has_hpdb(self.mount_point):
                return None
            return read_card_hpdb(self.mount_point)
        if self.hpdb_cfg_path is not None:
            if not self.hpdb_cfg_path.is_file():
                return None
            return self._read_hpdb_dir(self.hpdb_cfg_path.parent)
        # Neither configured explicitly: best-effort auto-discovery.
        found = discover_local_hpdb_paths()
        if not found:
            return None
        return read_card_hpdb(found[0])

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        # kind == "local": never touches the network; http_client is
        # accepted (for interface symmetry with other adapters) but unused.
        card = self._read()
        return RawDoc(
            source_adapter=self.name,
            payload=card,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        card: Optional[HpdbCard] = raw.payload
        if card is None or card.hpdb_cfg is None:
            return NormalizeResult(
                facts=[],
                warnings=["no local HPDB found (no card mounted / no hpdb.cfg path configured)"],
            )

        from wasds150.hpe.hpdb import segment_systems, serialize_system_slice

        county_index = card.county_index
        facts: List[NormalizedFact] = []
        warnings: List[str] = []

        for state_id, doc in card.state_files.items():
            for system in segment_systems(doc):
                identity = system.identity()
                entity_key = (
                    f"hpdb:{identity[0]}:{identity[1]}" if identity else f"hpdb:{state_id}:{system.name()}"
                )
                county_names = []
                if county_index is not None:
                    for cid in system.county_ids():
                        name = county_index.by_id.get(cid)
                        if name:
                            county_names.append(name)
                geos = system.geos()
                lat = lon = None
                if geos:
                    lat, lon = geos[0].lat, geos[0].lon
                facts.append(
                    NormalizedFact(
                        entity_key=entity_key,
                        fact_type="system",
                        name=system.name(),
                        county=", ".join(county_names) if county_names else None,
                        lat=lat,
                        lon=lon,
                        location_precision="exact" if lat is not None else "unknown",
                        source_id=self.name,
                        source_url="",
                        retrieved_at=raw.fetched_at,
                        raw={
                            "kind": system.kind(),
                            "tech": system.tech(),
                            "state_id": state_id,
                            # Real RadioReference numeric id (TrunkId/SysId/
                            # CountyId/AgencyId, whichever this system's own
                            # column 1 carries) -- lets the recipe engine
                            # match by SID/TrunkId directly rather than only
                            # via an entity_key substring check.
                            "sid": identity[1] if identity else None,
                            "sid_kind": identity[0] if identity else None,
                            # The full record tree (see
                            # wasds150.hpe.hpdb.serialize_system_slice),
                            # carried through so a matched recipe can build
                            # a real, populated
                            # wasds150.models.catalog.System from it (see
                            # wasds150.recipes.systems) -- previously
                            # dropped here, leaving no way to produce real
                            # per-list HPE output from a local HPDB match.
                            "records": serialize_system_slice(system),
                        },
                    )
                )
        if not facts:
            warnings.append("HPDB found but contains no systems (empty/corrupt card data?)")
        return NormalizeResult(facts=facts, warnings=warnings)
