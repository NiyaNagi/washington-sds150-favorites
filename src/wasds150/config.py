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

    @property
    def updates_dir(self) -> Path:
        """Numbered records of applied catalog changes (see
        :mod:`wasds150.catalog.delta`), one per ``save_catalog`` that moved
        anything a radio is programmed from."""
        return self.state_dir / "updates"

    @property
    def fleet_state_path(self) -> Path:
        """When each radio was last programmed, and from which catalog."""
        return self.state_dir / "fleet.json"

    @property
    def fleet_settings_path(self) -> Path:
        """Per-radio inputs for the fleet wizard (COM port, vendor app path,
        copy-to folder). No secrets are ever stored here."""
        return self.state_dir / "fleet-settings.json"

    @property
    def jobs_dir(self) -> Path:
        """Event logs and status documents of background jobs."""
        return self.state_dir / "jobs"

    @property
    def contacts_dir(self) -> Path:
        """Downloaded DMR/NXDN contact tables (radioid.net), never committed."""
        return self.state_dir / "contacts"

    def ensure_dirs(self) -> None:
        for d in (
            self.home,
            self.state_dir,
            self.history_dir,
            self.log_dir,
            self.backup_dir,
            self.updates_dir,
            self.jobs_dir,
            self.contacts_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
