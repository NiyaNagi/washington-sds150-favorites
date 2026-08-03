"""Structured ``System`` construction: turning a matched fact — or a
baseline row's own already-checked-in free text — into a populated
:class:`wasds150.models.catalog.System`, rather than the provenance-only
enrichment :mod:`wasds150.recipes.engine` used to be limited to (see this
module's use from there).

Three independent, additive tiers, richest first — a Favorites List can
end up with systems from more than one tier (see
:func:`wasds150.recipes.engine.enrich_catalog`'s "Multiple systems may
populate one Favorites List" behavior):

* **Tier A** (:func:`system_from_hpdb_fact`) — a matched local Sentinel
  HPDB (or, in principle, any future adapter that carries a full record
  tree the same way) fact's own ``Conventional``/``Trunk`` record tree,
  converted losslessly via
  :func:`wasds150.hpe.hpdb.system_slice_to_system`. Full site/department/
  channel/talkgroup detail, real RadioReference ids preserved as merge
  keys.
* **Tier B** (:func:`systems_from_flat_facts`) — every other matched fact
  that already carries an explicit ``freq_mhz`` (NOAA, USCG, FCC ULS, FAA
  NASR, a RadioReference Premium import, ...): no free-text parsing
  needed, just grouped into one conventional System/Department for this
  Favorites List.
* **Tier C** (:func:`static_systems_for`) — no fact matching required at
  all, and no local/private input needed: literal channels already
  spelled out in the row's own checked-in
  ``departments_or_channels`` text (:mod:`wasds150.sources.static_channels`)
  plus, for a small curated set of rows whose text only gives a range, a
  hand-verified national public channel-plan seed
  (:mod:`wasds150.sources.static_seeds`). Pure and deterministic --
  callers that must stay I/O-free (:func:`wasds150.generate.pipeline.apply_profile`,
  :func:`wasds150.catalog.baseline.generate_baseline_from_csv`) call this
  tier directly.

:func:`dedupe_systems` makes combining tiers (and re-running any of them,
e.g. once when a catalog is enriched and again at generate time) safe and
idempotent.
"""
from __future__ import annotations

from typing import List, Optional

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.sources.facts import NormalizedFact
from wasds150.sources.static_channels import ParsedChannel, parse_department_text
from wasds150.sources.static_metadata import (
    channel_is_priority,
    channel_mode,
    channel_service_type,
    channel_should_avoid,
)
from wasds150.sources.static_seeds import seed_channels_for
from wasds150.util.hashing import stable_id


def _round_freq(freq_mhz: Optional[float]) -> Optional[float]:
    return round(freq_mhz, 6) if freq_mhz is not None else None


def _hpe_tone(tone: str) -> str:
    """Convert the parser's readable tone notation to BCDx36HP syntax."""
    if tone.startswith("CTCSS "):
        return f"TONE=C{tone.removeprefix('CTCSS ')}"
    if tone.startswith("DCS "):
        return f"D{tone.removeprefix('DCS ')}"
    return tone


def dedupe_channels(channels: List[Channel]) -> List[Channel]:
    """Deterministic de-duplication of channels within one Department, by
    ``(freq_mhz, tgid, label)`` — first-seen order preserved."""
    seen = set()
    result: List[Channel] = []
    for channel in channels:
        key = (_round_freq(channel.freq_mhz), channel.tgid, channel.label.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(channel)
    return result


def dedupe_systems(systems: List[System]) -> List[System]:
    """Deterministic de-duplication by system id, preserving first-seen
    order — safe to call repeatedly (once when a catalog is enriched,
    again at generate time via :func:`wasds150.generate.pipeline.apply_profile`)
    without ever growing a list of duplicate systems."""
    seen = set()
    result: List[System] = []
    for system in systems:
        if system.id in seen:
            continue
        seen.add(system.id)
        result.append(system)
    return result


# ---------------------------------------------------------------------------
# Tier C: static free text + seed (pure, no I/O, no local/private input)
# ---------------------------------------------------------------------------


def _channel_from_parsed(fl: FavoritesList, index: int, parsed: ParsedChannel) -> Channel:
    return Channel(
        id=stable_id(f"{fl.slug}:static:{index}:{parsed.label}:{parsed.freq_mhz}", kind="channel"),
        label=parsed.label,
        freq_mhz=parsed.freq_mhz,
        mode=channel_mode(fl, parsed),
        tone=_hpe_tone(parsed.tone),
        service_type=channel_service_type(fl, parsed),
        priority=channel_is_priority(fl, parsed),
        avoid=channel_should_avoid(fl, parsed),
        notes=parsed.note,
    )


def static_systems_for(fl: FavoritesList) -> List[System]:
    """Tier C. Returns ``[]`` if neither the free-text parser nor a seed
    table produces anything for this row (e.g. a purely trunked row whose
    detail can only come from a local HPDB/RadioReference Premium match --
    see :func:`wasds150.recipes.engine.evaluate_recipe`'s coverage warning
    for that case). Pure function of ``fl`` alone; safe to call on every
    ``generate``/``preview`` run regardless of catalog freshness."""
    parsed = [
        channel
        for channel in parse_department_text(fl.departments_or_channels).channels
        if "unverified" not in channel.note.lower()
    ]
    # Curated seeds fill ranges/plans that prose cannot safely expand. If
    # the prose already names a literal frequency, prefer that richer,
    # row-specific entry instead of adding a second generic seed channel
    # at the same frequency (FL65/FRS Ch7 is the canonical overlap).
    parsed_frequencies = {_round_freq(channel.freq_mhz) for channel in parsed}
    parsed.extend(
        channel
        for channel in seed_channels_for(fl.favorite_key, fl.departments_or_channels)
        if _round_freq(channel.freq_mhz) not in parsed_frequencies
    )
    if not parsed:
        return []

    channels = dedupe_channels([_channel_from_parsed(fl, i, p) for i, p in enumerate(parsed)])
    if not channels:
        return []
    department = Department(id=stable_id(f"{fl.slug}:static-text-channels", kind="department"), label="Channels", channels=channels)
    system = System(
        id=stable_id(f"{fl.slug}:static-text-channels", kind="system"),
        label=fl.favorite_name,
        departments=[department],
    )
    return [system]


# ---------------------------------------------------------------------------
# Tier A: matched local Sentinel HPDB record tree (richest)
# ---------------------------------------------------------------------------


def system_from_hpdb_fact(fact: NormalizedFact) -> Optional[System]:
    """Tier A. ``None`` if ``fact`` is not a ``sentinel_local`` fact (or
    carries no record tree, e.g. a hand-built test fact) rather than
    raising -- callers are expected to try every matched fact and only use
    what actually converts."""
    if fact.source_id != "sentinel_local":
        return None
    raw = fact.raw if isinstance(fact.raw, dict) else {}
    records = raw.get("records")
    if not records:
        return None

    from wasds150.hpe.hpdb import deserialize_system_slice, system_slice_to_system

    system_slice = deserialize_system_slice(records)
    if not system_slice.records:
        return None
    return system_slice_to_system(system_slice)


# ---------------------------------------------------------------------------
# Tier B: matched flat frequency facts (public online adapters, RR Premium)
# ---------------------------------------------------------------------------


def systems_from_flat_facts(fl: FavoritesList, facts: List[NormalizedFact]) -> List[System]:
    """Tier B. Every matched fact that already carries an explicit
    ``freq_mhz`` (excluding ``sentinel_local`` facts, which
    :func:`system_from_hpdb_fact` handles instead) becomes one
    :class:`~wasds150.models.catalog.Channel` in a single aggregate
    conventional System for this Favorites List. Returns ``[]`` if none of
    ``facts`` carry a frequency."""
    channels: List[Channel] = []
    for fact in facts:
        if fact.source_id == "sentinel_local" or fact.freq_mhz is None:
            continue
        channels.append(
            Channel(
                id=stable_id(f"{fl.slug}:{fact.source_id}:{fact.entity_key}", kind="channel"),
                label=fact.name or fact.entity_key,
                freq_mhz=fact.freq_mhz,
                mode=fact.mode,
                tone=fact.tone or "",
            )
        )
    channels = dedupe_channels(channels)
    if not channels:
        return []
    department = Department(id=stable_id(f"{fl.slug}:public-facts:channels", kind="department"), label="Channels", channels=channels)
    system = System(
        id=stable_id(f"{fl.slug}:public-facts", kind="system"),
        label=fl.favorite_name,
        departments=[department],
    )
    return [system]


def systems_from_matched_facts(fl: FavoritesList, matched_facts: List[NormalizedFact]) -> List[System]:
    """Tiers A + B together, as used by
    :func:`wasds150.recipes.engine.enrich_catalog`: every HPDB system
    slice among ``matched_facts`` converted losslessly (Tier A), plus one
    aggregate System for every other matched fact that carries an explicit
    frequency (Tier B). Order is deterministic (input order preserved);
    combine with :func:`dedupe_systems` when merging into a row that may
    already carry systems from a prior run."""
    systems: List[System] = []
    for fact in matched_facts:
        system = system_from_hpdb_fact(fact)
        if system is not None:
            systems.append(system)
    systems.extend(systems_from_flat_facts(fl, matched_facts))
    return systems
