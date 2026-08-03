"""Enables ``python -m wasds150 ...`` as an alternative to the ``wasds150``
console-script entry point installed by ``pyproject.toml``.
"""
from __future__ import annotations

import sys

from wasds150.cli import main

if __name__ == "__main__":
    sys.exit(main())
