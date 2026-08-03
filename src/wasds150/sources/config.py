"""Local, never-committed source configuration: offline mode + local-file
paths for the ``local``-kind adapters (:mod:`wasds150.sources.sentinel_local`,
:mod:`wasds150.sources.radioreference_premium`).

**Secrets discipline**: only *non-secret* RadioReference identifiers
(username, app key) are ever persisted here — never a password. A future,
*verified* SOAP client (see
:class:`wasds150.sources.radioreference_premium.RadioReferenceCredentials`)
would need a password supplied per-invocation (CLI flag or the
``WASDS150_RR_PASSWORD`` environment variable), never written to disk, so
there is nothing to leak from this file even if it were mishandled. The
file is written with ``0600`` permissions on POSIX (best-effort on Windows,
which has no equivalent bit) as defense in depth.

Every field here is written to disk in a small JSON dict — no dataclass
`repr`/`str` override is needed like
:class:`~wasds150.sources.radioreference_premium.RadioReferenceCredentials`
has, precisely because nothing secret is ever stored in it.
"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class SourcesConfig:
    offline: bool = False
    sentinel_local_mount: Optional[str] = None
    sentinel_local_hpdb_cfg: Optional[str] = None
    radioreference_export_path: Optional[str] = None
    radioreference_username: Optional[str] = None
    radioreference_app_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourcesConfig":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def load(cls, path: Path) -> "SourcesConfig":
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        if os.name == "posix":
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
