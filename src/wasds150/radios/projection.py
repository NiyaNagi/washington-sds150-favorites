"""Project a radio-neutral catalog onto one radio's capabilities.

The catalog describes signals, not radios.  Once it carries HF calling
frequencies for a transceiver and 800 MHz talkgroups for a scanner, no single
radio can represent all of it, and an exporter that assumes otherwise will
fail on content that is perfectly valid for a different target.

Projection is the answer: keep what this radio can use, drop the rest, and
say what was dropped.  It is the same rule the channel-plan resolver follows,
applied to the hierarchical shape the scanner exports need.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Tuple

from wasds150.models.catalog import Department, FavoritesList, Site, System
from wasds150.radios.profile import RadioProfile


@dataclass
class ProjectionResult:
    favorites: List[FavoritesList] = field(default_factory=list)
    dropped_channels: int = 0
    warnings: List[str] = field(default_factory=list)


def _channel_is_usable(channel, profile: RadioProfile) -> bool:
    if channel.tgid is not None:
        # A talkgroup needs a trunk-tracking receiver, not a frequency.
        return profile.supports_talkgroups
    if channel.freq_mhz is None:
        return False
    if not profile.can_receive(channel.freq_mhz):
        return False
    return profile.supports_mode(channel.mode)


def _project_department(department: Department, profile: RadioProfile) -> Tuple[Department, int]:
    kept = [c for c in department.channels if _channel_is_usable(c, profile)]
    dropped = len(department.channels) - len(kept)
    projected = copy.deepcopy(department)
    projected.channels = kept
    return projected, dropped


def _project_system(system: System, profile: RadioProfile) -> Tuple[System, int]:
    projected = copy.deepcopy(system)
    dropped = 0

    departments = []
    for department in system.departments:
        new_department, lost = _project_department(department, profile)
        dropped += lost
        if new_department.channels:
            departments.append(new_department)
    projected.departments = departments

    sites = []
    for site in system.sites:
        new_site: Site = copy.deepcopy(site)
        site_departments = []
        for department in site.departments:
            new_department, lost = _project_department(department, profile)
            dropped += lost
            if new_department.channels:
                site_departments.append(new_department)
        new_site.departments = site_departments
        if site_departments or site.id:
            sites.append(new_site)
    projected.sites = sites

    return projected, dropped


def project_favorites(
    favorites: List[FavoritesList], profile: RadioProfile
) -> ProjectionResult:
    """Return ``favorites`` reduced to what ``profile`` can actually use.

    Only lists marked ``reference_only`` are pruned. A band plan spans more
    spectrum than any one radio covers, so dropping the unreachable parts is
    correct. Anywhere else, a channel the target cannot use is a data error,
    and silently removing it would defeat the validation that exists to catch
    exactly that.
    """
    result = ProjectionResult()

    for favorite in favorites:
        if not favorite.reference_only:
            result.favorites.append(favorite)
            continue

        projected = copy.deepcopy(favorite)
        systems = []
        dropped = 0
        for system in favorite.systems:
            new_system, lost = _project_system(system, profile)
            dropped += lost
            has_content = (
                new_system.departments
                or any(site.departments for site in new_system.sites)
                or new_system.trunk_frequencies
            )
            if has_content:
                systems.append(new_system)
        projected.systems = systems
        result.dropped_channels += dropped

        if dropped and not systems:
            result.warnings.append(
                f"{favorite.favorite_key}: no channels are usable on the "
                f"{profile.label}; {dropped} dropped"
            )
        elif dropped:
            result.warnings.append(
                f"{favorite.favorite_key}: {dropped} channel(s) dropped as "
                f"outside {profile.label} coverage or modes"
            )

        result.favorites.append(projected)

    return result
