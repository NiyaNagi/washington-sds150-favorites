"""Application configuration: resolves user-writable paths.

Kept deliberately small. ``AppConfig`` is the single object CLI/webui code
asks for paths so tests can point everything at a temp directory via
``WASDS150_HOME`` (see :mod:`wasds150.util.platformdirs`) without monkeypatching
multiple modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wasds150.util import platformdirs


@dataclass(frozen=True)
class AppConfig:
    home: Path

    @classmethod
    def default(cls) -> "AppConfig":
        return cls(home=platformdirs.user_home_dir())

    @property
    def profile_path(self) -> Path:
        return self.home / "profile.json"

    @property
    def catalog_path(self) -> Path:
        """Persisted catalog snapshot, written once a three-way merge is
        applied (see :mod:`wasds150.merge`). When absent, the packaged
        baseline catalog is used instead — see
        :func:`wasds150.appctx.build_context`."""
        return self.home / "catalog.json"

    @property
    def backup_dir(self) -> Path:
        """Where the experimental SD-card installer stores its mandatory
        pre-write backups (see :mod:`wasds150.installer.backup`)."""
        return self.state_dir / "sdcard-backups"

    @property
    def cache_dir(self) -> Path:
        """Where the sqlite HTTP cache + content-addressed blob store live
        (see :mod:`wasds150.cache.store`). Never committed; purely local."""
        return self.state_dir / "http-cache"

    @property
    def sources_config_path(self) -> Path:
        """Local-only source configuration (offline flag, Sentinel HPDB
        path, RadioReference Premium export path/non-secret identifiers —
        see :mod:`wasds150.sources.config`). Never committed; written with
        restrictive permissions since it may reference user file paths."""
        return self.state_dir / "sources.json"

    @property
    def state_dir(self) -> Path:
        return self.home / "state"

    @property
    def history_dir(self) -> Path:
        return self.state_dir / "history"

    @property
    def log_dir(self) -> Path:
        return self.state_dir / "logs"

    @property
    def log_file(self) -> Path:
        return self.log_dir / "wasds150.log"

    def ensure_dirs(self) -> None:
        for d in (self.home, self.state_dir, self.history_dir, self.log_dir, self.backup_dir):
            d.mkdir(parents=True, exist_ok=True)
