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

import copy
import re
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
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


def _rollup_component_keys(text: str) -> tuple:
    legacy = re.search(r"\breuses\s+FL(\d+(?:/\d+)+)", text, re.IGNORECASE)
    if legacy:
        return tuple(f"FL{int(value):02d}" for value in legacy.group(1).split("/"))
    declaration = re.search(r"\breuses\s+([^\)]+)", text, re.IGNORECASE)
    if not declaration:
        return ()
    return tuple(
        key.upper()
        for key in re.findall(r"\b(?:FL|KC|LA|OUT|BAND|UL)\d+[A-Za-z]?\b", declaration.group(1), re.IGNORECASE)
    )


def populate_rollups(catalog: Catalog) -> Dict[str, tuple]:
    """Populate explicitly declared ``(reuses FLx/y/...)`` rollups.

    Component systems are deep-copied whole, preserving every verified
    identity, site, frequency, department, channel, and location field.
    The rollup is filled only when every named component exists and is
    populated; otherwise it remains fail-closed. No geographic filtering
    or radio fact is inferred from prose.

    Returns ``slug -> component keys`` for rollups that were populated.
    """
    by_key = {favorite.favorite_key.upper(): favorite for favorite in catalog.favorites}
    populated: Dict[str, tuple] = {}
    for favorite in catalog.favorites:
        component_keys = _rollup_component_keys(favorite.system_or_category)
        if not component_keys:
            continue
        components = [by_key.get(key) for key in component_keys]
        favorite.systems = []
        favorite.provenance = [
            item for item in favorite.provenance if item.source_adapter != "derived_rollup"
        ]
        if not components or any(component is None or not component.systems for component in components):
            continue
        favorite.systems = dedupe_systems([
            copy.deepcopy(system)
            for component in components
            for system in component.systems
        ])
        favorite.provenance.extend(
            Provenance(
                source_adapter="derived_rollup",
                source_url=f"catalog://{component.favorite_key}",
                confidence="derived",
            )
            for component in components
        )
        if favorite.favorite_key.upper().startswith("UL"):
            from wasds150.catalog.upper_lena_lake import apply_location
            apply_location(favorite)
        populated[favorite.slug] = component_keys
    return populated


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


def static_system_id(fl: FavoritesList) -> str:
    """The id Tier C gives a row's text-derived system. Stable across edits
    of the row's prose, so a persisted copy can be found and replaced -- or
    removed, once the prose no longer names any frequency."""
    return stable_id(f"{fl.slug}:static-text-channels", kind="system")


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
    seeds = seed_channels_for(fl.favorite_key, fl.departments_or_channels)
    seed_by_frequency = {_round_freq(channel.freq_mhz): channel for channel in seeds}
    parsed = [
        replace(
            channel,
            tone=channel.tone or seed_by_frequency[_round_freq(channel.freq_mhz)].tone,
            note="; ".join(filter(None, (channel.note, seed_by_frequency[_round_freq(channel.freq_mhz)].note))),
        )
        if _round_freq(channel.freq_mhz) in seed_by_frequency else channel
        for channel in parsed
    ]
    parsed_frequencies = {_round_freq(channel.freq_mhz) for channel in parsed}
    parsed.extend(
        channel
        for channel in seeds
        if _round_freq(channel.freq_mhz) not in parsed_frequencies
    )
    if not parsed:
        return []

    channels = dedupe_channels([_channel_from_parsed(fl, i, p) for i, p in enumerate(parsed)])
    if not channels:
        return []
    department = Department(id=stable_id(f"{fl.slug}:static-text-channels", kind="department"), label="Channels", channels=channels)
    system = System(
        id=static_system_id(fl),
        label=fl.favorite_name,
        departments=[department],
    )
    return [system]


# ---------------------------------------------------------------------------
# Tier A: matched local Sentinel HPDB record tree (richest)
# ---------------------------------------------------------------------------

# Public catalog intent only: these category words come from each row's
# departments_or_channels field, never from copied HPDB data. Unmatched
# talkgroups remain excluded rather than having an encryption state guessed.
_SPLIT_INTENT = {
    "FL09a": (("fire", "transit", "public works"), False),
    "FL09b": (("police", "sheriff", "law", "spd", "kcso"), True),
    "FL20a": (("dispatch", "fire", "mutual aid", "srma#"), False),
    "FL20b": (("tac4", "tac 4", "lops#", "inv#", "investigation", "investigations"), True),
    "FL25a": (("fire", "ems", "amr"), False),
    "FL25b": (("law", "police", "sheriff"), True),
    "FL50a": (("logistics", "support", "fire", "range"), False),
    "FL50b": (("command", "security"), True),
}


def _intent_matches(label: str, tokens: tuple) -> bool:
    normalized = label.casefold()
    return any(
        re.search(
            rf"(?<!\w){re.escape(token.removesuffix('#'))}{r'(?:[- ]?\d{1,2})(?!\w)' if token.endswith('#') else r'(?!\w)'}",
            normalized,
        )
        for token in tokens
    )


def curate_split_systems(fl: FavoritesList, systems: List[System]) -> List[System]:
    """Apply explicit public intent to a clear/encrypted split row.

    Only departments or talkgroups whose labels match the row's documented
    categories are retained. Encrypted-side departments are clearly marked
    and avoided. No unmatched item is classified by inference.
    """
    intent = _SPLIT_INTENT.get(fl.favorite_key)
    if intent is None:
        return systems
    tokens, encrypted = intent
    curated: List[System] = []
    for system in systems:
        for site in system.sites:
            kept_departments = []
            for department in site.departments:
                department_match = _intent_matches(department.label, tokens)
                channels = [
                    channel
                    for channel in department.channels
                    if department_match or _intent_matches(channel.label, tokens)
                ]
                if not channels:
                    continue
                department.channels = channels
                if encrypted:
                    if not department.label.startswith("[E]-ENCRYPTED "):
                        department.label = f"[E]-ENCRYPTED {department.label}"
                    department.encrypted_bucket = True
                    department.avoid = True
                kept_departments.append(department)
            site.departments = kept_departments
        if any(site.departments for site in system.sites):
            curated.append(system)
    return curated


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
    ``facts`` carry a frequency. A tone the scanner cannot parse is dropped
    rather than copied: one source's free text in the tone field would
    otherwise fail validation for the whole list."""
    from wasds150.hpe.validation import tone_is_valid

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
                tone=fact.tone if fact.tone and tone_is_valid(fact.tone) else "",
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


# ---------------------------------------------------------------------------
# Rebuild policy: how a refresh treats the systems a row already carries
# ---------------------------------------------------------------------------

ACCUMULATE = "accumulate"
REPLACE_SYSTEMS = "replace-systems"
REPLACE_TRUNK_FREQUENCIES = "replace-trunk-frequencies"
_RR_SOURCE_IDS = ("radioreference_premium", "radioreference_api")


@dataclass(frozen=True)
class RebuildPolicy:
    """``accumulate`` keeps every system and adds what is new (a locally
    enriched HPDB system is precious and must survive a refresh that cannot
    see it). ``replace-systems`` lets freshly built systems win by id, for a
    row rebuilt wholly from one public source. ``replace-trunk-frequencies``
    keeps a trunked system's sites, departments and talkgroups and replaces
    only its frequency table, which is the part a RadioReference export
    refreshes."""

    source_ids: Tuple[str, ...]
    mode: str


def rebuild_policy(fl: FavoritesList) -> RebuildPolicy:
    if fl.favorite_key == "PSHAM01":
        # Every channel comes from the WWARA extract and the system id is
        # deterministic, so merging by id would let the previous run's copy
        # win forever and never pick up a new coordination or corrected tone.
        return RebuildPolicy(("wwara",), REPLACE_SYSTEMS)
    from wasds150.recipes.default_recipes import _detect_sids

    if _detect_sids(fl.system_or_category, fl.source_url):
        return RebuildPolicy(_RR_SOURCE_IDS, REPLACE_TRUNK_FREQUENCIES)
    return RebuildPolicy((), ACCUMULATE)


def rebuilds_systems_from_facts(fl: FavoritesList) -> bool:
    """True when a row's systems are derived wholly from a public source
    (see :func:`rebuild_policy`)."""
    return rebuild_policy(fl).mode == REPLACE_SYSTEMS


# ---------------------------------------------------------------------------
# Tier D: RadioReference trunked-site rows -> a system's frequency table
# ---------------------------------------------------------------------------

_PAREN = re.compile(r"\(([^)]*)\)")
_WORD = re.compile(r"[A-Za-z0-9]+")
#: RadioReference mode -> the trunk technology tag the HPE writer uses.
_TECH_BY_MODE = {"P25": "P25Standard"}


def _name_key(text: str) -> str:
    return " ".join(_WORD.findall(_PAREN.sub(" ", text or "").lower()))


#: Capitalised words that name a technology or band, not a system. Matching
#: on them would tie every "(P25)" system to every row that mentions P25.
_NOT_SYSTEM_ACRONYMS = frozenset({"P25", "DMR", "NXDN", "TRBO", "LMR", "UHF", "VHF", "EMS", "SID", "TRS", "USA"})


def _acronyms(text: str) -> set:
    """Acronyms: tokens written in capitals, three or more characters with
    at least two letters, wherever they appear - ``(PSERN)``, ``TCERN (...)``,
    ``MACC 911``. Mixed-case words such as ``(SeaTac Airport)`` are not
    acronyms and never match, and neither are technology names."""
    return {
        token
        for token in re.findall(r"\b[A-Z0-9]{3,}\b", text or "")
        if sum(c.isalpha() for c in token) >= 2 and token not in _NOT_SYSTEM_ACRONYMS
    }


def _names_match(row_texts: List[str], category: str) -> bool:
    """A RadioReference system category names the same system as a row when
    one name contains the other (ignoring parentheses and punctuation, both
    at least ten characters) or they share a parenthesised acronym
    (``Justice Integrated Wireless Network`` / ``... (JIWN)``)."""
    category_key = _name_key(category)
    for text in row_texts:
        key = _name_key(text)
        if len(category_key) >= 10 and len(key) >= 10 and (category_key in key or key in category_key):
            return True
    row_words = {w.upper() for text in row_texts for w in _WORD.findall(text or "")}
    category_words = {w.upper() for w in _WORD.findall(category or "")}
    row_acronyms = set().union(*(_acronyms(text) for text in row_texts)) if row_texts else set()
    return bool((_acronyms(category) & row_words) or (row_acronyms & category_words))


def rr_site_facts_for(fl: FavoritesList, facts: List[NormalizedFact], sids: tuple) -> List[NormalizedFact]:
    """RadioReference trunked-site facts describing ``fl``'s system: by SID
    when the fact carries one (the web-service API does), else by name."""
    texts = [fl.favorite_name, fl.system_or_category]
    matched = []
    for fact in facts:
        if fact.fact_type != "site" or fact.source_id not in _RR_SOURCE_IDS:
            continue
        raw = fact.raw if isinstance(fact.raw, dict) else {}
        try:
            if raw.get("sid") is not None and int(raw["sid"]) in sids:
                matched.append(fact)
                continue
        except (TypeError, ValueError):
            pass
        if _names_match(texts, str(raw.get("rr_category", ""))):
            matched.append(fact)
    return matched


def systems_from_rr_site_facts(fl: FavoritesList, site_facts: List[NormalizedFact], *, sids: tuple) -> List[System]:
    """One system per RadioReference category: its sites (county-centre
    fences; the export gives no site position) and every site frequency in
    one table. Exports do not mark control channels, so ``lcn`` stays unset
    and ``usage`` records the site."""
    from collections import OrderedDict

    from wasds150.catalog.wa_counties import county_point
    from wasds150.models.catalog import Site, TrunkFrequency

    by_category: "OrderedDict[str, List[NormalizedFact]]" = OrderedDict()
    for fact in site_facts:
        raw = fact.raw if isinstance(fact.raw, dict) else {}
        by_category.setdefault(str(raw.get("rr_category") or "RadioReference system").strip(), []).append(fact)

    systems: List[System] = []
    for category, facts in by_category.items():
        sites: "OrderedDict[str, NormalizedFact]" = OrderedDict()
        table: List[TrunkFrequency] = []
        seen = set()
        for fact in facts:
            raw = fact.raw if isinstance(fact.raw, dict) else {}
            site_label = str(raw.get("rr_description") or fact.name or "Site").strip()[:64]
            sites.setdefault(site_label, fact)
            freq = _round_freq(fact.freq_mhz)
            if freq is None or (freq, site_label) in seen:
                continue
            seen.add((freq, site_label))
            table.append(
                TrunkFrequency(
                    id=stable_id(f"{fl.slug}:rr-site:{category}:{site_label}:{freq}", kind="trunk_frequency"),
                    freq_mhz=freq,
                    lcn=None,
                    usage=f"site:{site_label}",
                )
            )
        site_objects = []
        for label, fact in sites.items():
            point = county_point(fact.county) if fact.county else None
            site_objects.append(
                Site(
                    id=stable_id(f"{fl.slug}:rr-site:{category}:{label}", kind="site"),
                    label=label,
                    lat=point.lat if point else None,
                    lon=point.lon if point else None,
                    range_miles=point.radius_miles if point else None,
                    shape="Circle" if point else "",
                )
            )
        modes = {(fact.mode or "").upper() for fact in facts}
        systems.append(
            System(
                id=stable_id(f"{fl.slug}:rr-sites:{category}", kind="system"),
                label=category[:64],
                sid=sids[0] if len(sids) == 1 else None,
                tech=next((_TECH_BY_MODE[m] for m in sorted(modes) if m in _TECH_BY_MODE), None),
                sites=site_objects,
                trunk_frequencies=table,
            )
        )
    return systems


def _has_talkgroups(system: System) -> bool:
    departments = list(system.departments) + [d for site in system.sites for d in site.departments]
    return any(channel.tgid is not None for department in departments for channel in department.channels)


def refresh_trunk_frequencies(
    fl: FavoritesList, site_facts: List[NormalizedFact], *, sids: tuple
) -> Tuple[bool, str]:
    """Replace the frequency table of ``fl``'s trunked systems with the
    RadioReference site rows, keeping their sites and talkgroups.

    A trunked system without talkgroups is nothing a scanner can use (the
    HPE validator rejects it as missing talkgroups), so when the row has none
    no system is built; the message says where talkgroups come from.
    """
    from wasds150.sources.radioreference_api import SYSTEM_ID_PREFIX as live_prefix

    table = [tf for system in systems_from_rr_site_facts(fl, site_facts, sids=sids) for tf in system.trunk_frequencies]
    # A system fetched live from the web service already carries the site
    # table with channel numbers; an export's frequency list would only
    # replace it with a poorer one.
    targets = [
        system for system in fl.systems
        if _has_talkgroups(system) and not system.id.startswith(live_prefix)
        and (system.sid is None or not sids or system.sid in sids)
    ]
    if not targets:
        return False, (
            f"{fl.favorite_key}: {len(table)} RadioReference site frequencies matched, but the row has no "
            "talkgroups to go with them; talkgroups come from a Sentinel HPDB import or the RadioReference "
            "web-service API (needs an application key), so no trunked system was built"
        )
    for system in targets:
        system.trunk_frequencies = [copy.deepcopy(tf) for tf in table]
    return True, f"{fl.favorite_key}: trunk frequency table replaced with {len(table)} RadioReference site frequencies"


def systems_defined_in_code(fl: FavoritesList) -> bool:
    """True when a row's systems are hand-authored, individually cited channel
    tables in :mod:`wasds150.catalog` rather than anything a source enriches.

    ``OZ01`` is built wholly in :mod:`wasds150.catalog.olympic_coast`. A
    persisted catalog keeps systems by id, so without this a corrected tone or
    a withdrawn channel would never reach a catalog saved before the fix.
    """
    return fl.favorite_key == "OZ01"


def systems_from_matched_facts(fl: FavoritesList, matched_facts: List[NormalizedFact]) -> List[System]:
    """Tiers A + B together, as used by
    :func:`wasds150.recipes.engine.enrich_catalog`: every HPDB system
    slice among ``matched_facts`` converted losslessly (Tier A), plus one
    aggregate System for every other matched fact that carries an explicit
    frequency (Tier B). Order is deterministic (input order preserved);
    combine with :func:`dedupe_systems` when merging into a row that may
    already carry systems from a prior run."""
    if fl.favorite_key == "PSHAM01":
        from wasds150.catalog.puget_ham import system_from_wwara_facts
        system = system_from_wwara_facts(fl, matched_facts)
        return [system] if system is not None else []

    systems: List[System] = []
    for fact in matched_facts:
        system = system_from_hpdb_fact(fact)
        if system is not None:
            systems.append(system)
    # A live RadioReference web-service system arrives already whole; it is
    # curated below exactly as an HPDB system is, so a row that keeps only
    # part of a shared system (PSERN fire vs law) still keeps only that part.
    for fact in matched_facts:
        if fact.source_id == "radioreference_api" and isinstance(fact.raw, dict) and fact.raw.get("system"):
            systems.append(System.from_dict(copy.deepcopy(fact.raw["system"])))
    systems.extend(systems_from_flat_facts(fl, matched_facts))
    systems = curate_split_systems(fl, systems)
    from wasds150.recipes.local_area import curate_local_area_systems
    return curate_local_area_systems(fl, systems)
