#!/usr/bin/env python3
"""Fetch optional, third-party HPE research fixtures for local testing.

These fixtures are **never vendored into version control** (see
``.gitignore`` and ``NOTICE.md``): both are GPL-2.0-licensed data files from
external repositories, fetched on demand into the git-ignored
``.fixture-cache/`` directory so ``tests/test_hpe_external_fixtures.py`` can
do an independent cross-check of this project's own, fully-original HPE
codec/schema implementation. If this script is never run (e.g. no network
access), those tests skip cleanly — the project's own synthetic fixture
(``tests/fixtures/wasds150_synthetic_bcdx36hp.hpd``) is the primary,
always-available golden fixture and does not depend on this script.

Usage::

    python scripts/fetch_hpe_fixtures.py [--force]

Only the Python standard library is used (``urllib.request``).
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / ".fixture-cache"

# Pinned to specific commit SHAs (not branch HEADs) so fetches are
# reproducible and reviewable; see NOTICE.md for full attribution.
FIXTURES = [
    {
        "name": "platypus_f_example.hpd",
        "url": (
            "https://raw.githubusercontent.com/FuzzyGophers/platypus/"
            "5abb42b54595186ea217ecdf904a19a081be7b08/samples/synthetic/f_example.hpd"
        ),
        "source_repo": "FuzzyGophers/platypus",
        "commit": "5abb42b54595186ea217ecdf904a19a081be7b08",
        "license": "GPL-2.0-only",
        "kind": "synthetic_bcdx36hp_hpd",
    },
    {
        "name": "platypus_f_list.cfg",
        "url": (
            "https://raw.githubusercontent.com/FuzzyGophers/platypus/"
            "5abb42b54595186ea217ecdf904a19a081be7b08/samples/synthetic/f_list.cfg"
        ),
        "source_repo": "FuzzyGophers/platypus",
        "commit": "5abb42b54595186ea217ecdf904a19a081be7b08",
        "license": "GPL-2.0-only",
        "kind": "synthetic_f_list_cfg",
    },
    {
        "name": "platypus_hpdb.cfg",
        "url": (
            "https://raw.githubusercontent.com/FuzzyGophers/platypus/"
            "5abb42b54595186ea217ecdf904a19a081be7b08/samples/synthetic/hpdb.cfg"
        ),
        "source_repo": "FuzzyGophers/platypus",
        "commit": "5abb42b54595186ea217ecdf904a19a081be7b08",
        "license": "GPL-2.0-only",
        "kind": "synthetic_hpdb_cfg",
    },
    {
        "name": "platypus_s_000090.hpd",
        "url": (
            "https://raw.githubusercontent.com/FuzzyGophers/platypus/"
            "5abb42b54595186ea217ecdf904a19a081be7b08/samples/synthetic/s_000090.hpd"
        ),
        "source_repo": "FuzzyGophers/platypus",
        "commit": "5abb42b54595186ea217ecdf904a19a081be7b08",
        "license": "GPL-2.0-only",
        "kind": "synthetic_hpdb_state_hpd",
    },
    {
        "name": "nascarscanner_2026_season.hpe",
        "url": (
            "https://raw.githubusercontent.com/jim-edwards/NascarScanner/"
            "f5ae6c5854cdfa1b04fe076fbf748f16ad0cdd6a/"
            "Uniden%20HomePatrol%20Sentinel/2026_Nascar_Season.hpe"
        ),
        "source_repo": "jim-edwards/NascarScanner",
        "commit": "f5ae6c5854cdfa1b04fe076fbf748f16ad0cdd6a",
        "license": "GPL-2.0",
        "kind": "real_homepatrol1_hpe_container",
    },
]


def fetch_all(force: bool = False, timeout: float = 15.0) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "fixtures": []}
    for fixture in FIXTURES:
        dest = CACHE_DIR / fixture["name"]
        entry = dict(fixture)
        if dest.exists() and not force:
            entry["status"] = "already-cached"
        else:
            try:
                with urllib.request.urlopen(fixture["url"], timeout=timeout) as resp:
                    data = resp.read()
                dest.write_bytes(data)
                entry["status"] = "fetched"
                entry["size_bytes"] = len(data)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                entry["status"] = "failed"
                entry["error"] = str(exc)
        manifest["fixtures"].append(entry)

    manifest_path = CACHE_DIR / "ATTRIBUTION.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-download even if already cached")
    args = parser.parse_args(argv)

    manifest = fetch_all(force=args.force)
    ok = True
    for entry in manifest["fixtures"]:
        print(f"[{entry['status']:>14}] {entry['name']} ({entry['source_repo']}, {entry['license']})")
        if entry["status"] == "failed":
            ok = False
            print(f"    error: {entry['error']}")
    print(f"\nCache directory: {CACHE_DIR}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
