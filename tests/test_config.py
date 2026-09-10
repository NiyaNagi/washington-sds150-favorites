from pathlib import Path

from wasds150.config import AppConfig


def test_appconfig_default_uses_wasds150_home_env(wasds_home):
    config = AppConfig.default()
    assert config.home == wasds_home


def test_appconfig_derived_paths(wasds_home):
    config = AppConfig.default()
    assert config.profile_path == wasds_home / "profile.json"
    assert config.state_dir == wasds_home / "state"
    assert config.history_dir == wasds_home / "state" / "history"
    assert config.log_dir == wasds_home / "state" / "logs"
    assert config.log_file == wasds_home / "state" / "logs" / "wasds150.log"


def test_ensure_dirs_creates_all_directories(wasds_home):
    config = AppConfig.default()
    assert not config.home.exists()
    config.ensure_dirs()
    assert config.home.is_dir()
    assert config.state_dir.is_dir()
    assert config.history_dir.is_dir()
    assert config.log_dir.is_dir()


def test_fleet_and_update_paths_live_under_state(wasds_home):
    config = AppConfig.default()
    state = wasds_home / "state"
    assert config.updates_dir == state / "updates"
    assert config.fleet_state_path == state / "fleet.json"
    assert config.fleet_settings_path == state / "fleet-settings.json"
    assert config.jobs_dir == state / "jobs"
    assert config.contacts_dir == state / "contacts"


def test_ensure_dirs_creates_fleet_directories(wasds_home):
    config = AppConfig.default()
    config.ensure_dirs()
    for directory in (config.updates_dir, config.jobs_dir, config.contacts_dir):
        assert directory.is_dir()


def test_appconfig_explicit_home_overrides_env(wasds_home, tmp_path):
    explicit = tmp_path / "explicit-home"
    config = AppConfig(home=explicit)
    assert config.home == explicit
    assert config.home != wasds_home
