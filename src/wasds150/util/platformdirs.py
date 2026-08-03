"""Tiny, dependency-free stand-in for the ``platformdirs`` package.

Only the handful of directories wasds150 needs are implemented here, and the
behavior is intentionally simple/predictable rather than fully matching the
XDG spec or Windows conventions in every edge case. All paths can be
overridden by setting the ``WASDS150_HOME`` environment variable, which is
what the test suite uses to avoid touching a real user's home directory.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

APP_NAME = "wasds150"


def _explicit_home() -> Optional[Path]:
    override = os.environ.get("WASDS150_HOME")
    if override:
        return Path(override).expanduser()
    return None


def user_home_dir() -> Path:
    """Root directory for all wasds150 user state (config/data/history/logs).

    Resolution order:
    1. ``WASDS150_HOME`` environment variable (used heavily by tests).
    2. Platform-conventional application-support directory.
    """
    explicit = _explicit_home()
    if explicit is not None:
        return explicit

    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    elif sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) / APP_NAME if appdata else Path.home() / APP_NAME
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) / APP_NAME if xdg else Path.home() / ".config" / APP_NAME
    return base


def config_dir() -> Path:
    return user_home_dir()


def state_dir() -> Path:
    return user_home_dir() / "state"


def history_dir() -> Path:
    return state_dir() / "history"


def log_dir() -> Path:
    return state_dir() / "logs"


def ensure_dirs() -> None:
    for d in (config_dir(), state_dir(), history_dir(), log_dir()):
        d.mkdir(parents=True, exist_ok=True)
