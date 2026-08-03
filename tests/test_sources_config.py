"""Tests for local, never-committed source configuration persistence
(offline flag + local-file paths; no secrets ever stored to disk)."""
from __future__ import annotations

import os
import stat

import pytest

from wasds150.sources.config import SourcesConfig


def test_default_config_is_online_and_unconfigured():
    config = SourcesConfig()
    assert config.offline is False
    assert config.sentinel_local_mount is None
    assert config.radioreference_export_path is None


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "sources.json"
    config = SourcesConfig(offline=True, sentinel_local_mount="/Volumes/SDS150", radioreference_username="alice")
    config.save(path)
    loaded = SourcesConfig.load(path)
    assert loaded == config


def test_load_missing_file_returns_defaults(tmp_path):
    loaded = SourcesConfig.load(tmp_path / "does-not-exist.json")
    assert loaded == SourcesConfig()


@pytest.mark.skipif(os.name != "posix", reason="POSIX file mode bits only")
def test_save_sets_restrictive_permissions(tmp_path):
    path = tmp_path / "sources.json"
    SourcesConfig(radioreference_username="alice").save(path)
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600


def test_from_dict_ignores_unknown_keys():
    config = SourcesConfig.from_dict({"offline": True, "totally_unknown_field": "x"})
    assert config.offline is True
    assert not hasattr(config, "totally_unknown_field")


def test_no_password_field_exists_on_the_dataclass():
    """Structural guarantee that a password can never accidentally be
    persisted to disk via this config object (see module docstring)."""
    fields = SourcesConfig.__dataclass_fields__
    assert not any("password" in name.lower() for name in fields)
