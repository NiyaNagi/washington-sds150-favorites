"""Structural + business-rule validation for catalogs and profiles.

Returns lists of human-readable issue strings rather than raising, so the
CLI/UI can show every problem at once (``wasds150 catalog validate``,
``wasds150 doctor``) instead of stopping at the first one.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import CSV_FIELDS, Catalog
from wasds150.models.profile import EDITABLE_FIELDS, Profile

FLQK_MIN = 0
FLQK_MAX = 99
FLQK_RESERVED = (0, 99)


def validate_catalog(catalog: Catalog) -> List[str]:
    issues: List[str] = []
    seen_slugs: dict = {}
    seen_keys: dict = {}
    for fl in catalog.favorites:
        for field_name in CSV_FIELDS:
            value = getattr(fl, field_name)
            if not isinstance(value, str):
                issues.append(f"{fl.slug}: field {field_name!r} must be a string, got {type(value).__name__}")
        if fl.slug in seen_slugs:
            issues.append(f"duplicate slug {fl.slug!r} (favorite_key {fl.favorite_key!r} and {seen_slugs[fl.slug]!r})")
        else:
            seen_slugs[fl.slug] = fl.favorite_key
        if fl.favorite_key in seen_keys:
            issues.append(f"duplicate favorite_key {fl.favorite_key!r}")
        else:
            seen_keys[fl.favorite_key] = fl.slug
        issues.extend(_validate_flqk(fl.slug, fl.flqk))
    return issues


def _validate_flqk(slug: str, flqk) -> List[str]:
    issues: List[str] = []
    if flqk is None:
        return issues
    if not isinstance(flqk, int) or isinstance(flqk, bool):
        issues.append(f"{slug}: flqk must be an int, got {type(flqk).__name__}")
        return issues
    if not (FLQK_MIN <= flqk <= FLQK_MAX):
        issues.append(f"{slug}: flqk {flqk} out of range [{FLQK_MIN}, {FLQK_MAX}]")
    elif flqk in FLQK_RESERVED:
        issues.append(
            f"{slug}: flqk {flqk} is reserved (all-off/debug-scratch) and should not be "
            "assigned in a production profile"
        )
    return issues


def validate_profile(profile: Profile, catalog: Catalog) -> List[str]:
    issues: List[str] = []
    baseline_slugs = {fl.slug for fl in catalog.favorites}

    for slug, entry in profile.entries.items():
        if slug != entry.slug:
            issues.append(f"profile entry key {slug!r} does not match entry.slug {entry.slug!r}")
        if slug not in baseline_slugs:
            issues.append(f"profile entry references unknown baseline slug {slug!r}")
        for field_name, value in entry.overrides.items():
            if field_name not in EDITABLE_FIELDS:
                issues.append(f"{slug}: override field {field_name!r} is not editable")
            if field_name == "flqk":
                issues.extend(_validate_flqk(slug, value))

    for slug, fl in profile.local_lists.items():
        if slug != fl.slug:
            issues.append(f"local list key {slug!r} does not match entry.slug {fl.slug!r}")
        if slug in baseline_slugs:
            issues.append(f"local list slug {slug!r} collides with a baseline favorite_key/slug")
        issues.extend(_validate_flqk(slug, fl.flqk))

    return issues
