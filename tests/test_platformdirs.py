from pathlib import Path

from wasds150.util import platformdirs


def test_wasds150_home_env_var_wins_over_platform_defaults(monkeypatch):
    monkeypatch.setenv("WASDS150_HOME", "/custom/wasds150/home")
    assert platformdirs.user_home_dir() == Path("/custom/wasds150/home")


def test_macos_default_path(monkeypatch):
    monkeypatch.delenv("WASDS150_HOME", raising=False)
    monkeypatch.setattr(platformdirs.sys, "platform", "darwin")
    home = platformdirs.user_home_dir()
    assert home == Path.home() / "Library" / "Application Support" / "wasds150"


def test_windows_default_path_uses_appdata(monkeypatch):
    monkeypatch.delenv("WASDS150_HOME", raising=False)
    monkeypatch.setattr(platformdirs.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", "C:\\Users\\test\\AppData\\Roaming")
    home = platformdirs.user_home_dir()
    assert home == Path("C:\\Users\\test\\AppData\\Roaming") / "wasds150"


def test_windows_default_path_falls_back_without_appdata(monkeypatch):
    monkeypatch.delenv("WASDS150_HOME", raising=False)
    monkeypatch.setattr(platformdirs.sys, "platform", "win32")
    monkeypatch.delenv("APPDATA", raising=False)
    home = platformdirs.user_home_dir()
    assert home == Path.home() / "wasds150"


def test_linux_default_path_uses_xdg_config_home(monkeypatch):
    monkeypatch.delenv("WASDS150_HOME", raising=False)
    monkeypatch.setattr(platformdirs.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/home/test/.config")
    home = platformdirs.user_home_dir()
    assert home == Path("/home/test/.config") / "wasds150"


def test_linux_default_path_falls_back_without_xdg(monkeypatch):
    monkeypatch.delenv("WASDS150_HOME", raising=False)
    monkeypatch.setattr(platformdirs.sys, "platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    home = platformdirs.user_home_dir()
    assert home == Path.home() / ".config" / "wasds150"


def test_ensure_dirs_creates_expected_tree(wasds_home):
    platformdirs.ensure_dirs()
    assert platformdirs.config_dir().is_dir()
    assert platformdirs.state_dir().is_dir()
    assert platformdirs.history_dir().is_dir()
    assert platformdirs.log_dir().is_dir()
