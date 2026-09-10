"""Which radios are out of date, and since when.

A :class:`RadioSyncRecord` is written when a radio has actually been
programmed - not when a file was exported for it - and records the catalog it
was built from. A radio is stale when it has never been synced, when it is
now built from a different plan, or when the catalog has moved since:
``content_hash`` for the list-level fields, and the structure hash from
:mod:`wasds150.catalog.delta` for the channels and talkgroups a refresh
changes (which ``content_hash`` deliberately does not see).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wasds150.catalog.delta import structure_hash
from wasds150.fleet.model import FleetRadio
from wasds150.util.hashing import sha256_of


@dataclass
class RadioSyncRecord:
    radio_id: str
    plan_id: str
    synced_at: str
    job_id: str = ""
    catalog_content_hash: str = ""
    catalog_structure_hash: str = ""
    #: Hash of the plan definition the radio was built from, so editing a
    #: plan (or its knobs) marks the radio stale even with an unchanged catalog.
    plan_fingerprint: str = ""
    export_sha256: str = ""
    loadout_snapshot_path: str = ""
    #: True once what reached the radio was read back and matched.
    verified: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RadioSyncRecord":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class FleetState:
    records: Dict[str, RadioSyncRecord] = field(default_factory=dict)

    def record(self, record: RadioSyncRecord) -> None:
        self.records[record.radio_id] = record

    def to_dict(self) -> Dict[str, Any]:
        return {"records": {key: rec.to_dict() for key, rec in sorted(self.records.items())}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FleetState":
        return cls(
            records={
                key: RadioSyncRecord.from_dict(value) for key, value in (data.get("records") or {}).items()
            }
        )

    @classmethod
    def load(cls, path: Path) -> "FleetState":
        if not Path(path).exists():
            return cls()
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def plan_fingerprint(plan: Any) -> str:
    """Stable hash of a plan definition, selectors included (the dataclass
    ``repr`` is deterministic: tuples, strings and floats only)."""
    return sha256_of(repr(plan)) if plan is not None else ""


def sha256_of_path(path: Path) -> str:
    """SHA-256 of a file, or of a directory as ``name  sha`` lines in name
    order (the shape ``sha256sum`` prints, so it can be checked by hand)."""
    path = Path(path)
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    lines = [
        f"{child.relative_to(path).as_posix()}  {hashlib.sha256(child.read_bytes()).hexdigest()}"
        for child in sorted(path.rglob("*"))
        if child.is_file()
    ]
    return sha256_of("\n".join(lines))


@dataclass
class RadioStatus:
    radio_id: str
    plan_id: str
    stale: bool
    reasons: List[str] = field(default_factory=list)
    record: Optional[RadioSyncRecord] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "radio_id": self.radio_id,
            "plan_id": self.plan_id,
            "stale": self.stale,
            "reasons": list(self.reasons),
            "record": self.record.to_dict() if self.record else None,
        }


def catalog_hashes(catalog: Any) -> Tuple[str, str]:
    return catalog.content_hash(), structure_hash(catalog)


def radio_status(
    radio: FleetRadio,
    record: Optional[RadioSyncRecord],
    *,
    content_hash: str,
    structure: str,
    current_plan_fingerprint: str = "",
) -> RadioStatus:
    reasons: List[str] = []
    if record is None:
        reasons.append("never synced")
    else:
        if record.plan_id != radio.plan_id:
            reasons.append(f"plan changed ({record.plan_id or 'none'} -> {radio.plan_id or 'none'})")
        elif current_plan_fingerprint and record.plan_fingerprint and (
            record.plan_fingerprint != current_plan_fingerprint
        ):
            reasons.append("plan definition changed")
        if record.catalog_structure_hash != structure:
            reasons.append(f"channels or talkgroups changed since {record.synced_at}")
        if record.catalog_content_hash != content_hash:
            reasons.append(f"catalog lists changed since {record.synced_at}")
    return RadioStatus(
        radio_id=radio.radio_id,
        plan_id=radio.plan_id,
        stale=bool(reasons),
        reasons=reasons,
        record=record,
    )
