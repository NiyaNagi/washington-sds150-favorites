"""Default recipes: one per baseline Favorites List, describing how public
sources / local HPDB / RadioReference Premium facts map onto it.

See :mod:`wasds150.recipes.engine` for how a recipe is evaluated against a
batch of :class:`~wasds150.sources.facts.NormalizedFact` objects, and the
package docstring in :mod:`wasds150.recipes` for the overall safety
philosophy (never rewrite the catalog's free-text fields automatically;
only attach traceable provenance and coverage warnings).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from wasds150.models.catalog import Catalog

#: Keyword -> adapter name(s) that plausibly supply facts relevant to a
#: Favorites List whose free-text fields mention that keyword. Deliberately
#: conservative (a handful of unambiguous terms per adapter) — a missed
#: match only means "no automatic provenance enrichment for this row yet",
#: never a wrong one.
_KEYWORD_SOURCES: Dict[str, str] = {
    "weather": "noaa_nwr",
    "nwr": "noaa_nwr",
    "marine": "uscg_navcen",
    "coast guard usaicg": "uscg_navcen",
    "vhf marine": "uscg_navcen",
    "satellite": "amsat",
    "amsat": "amsat",
    "iss": "amsat",
    "amateur": "wwara",
    "ham": "wwara",
    "repeater coordination": "wwara",
    "iacc": "iacc",
    "airport": "faa_nasr",
    "ctaf": "faa_nasr",
    "aviation": "faa_nasr",
    "faa": "faa_nasr",
    "gmrs": "fcc_uls",
    "frs/gmrs": "fcc_uls",
    "dnr": "wa_dnr",
    "nifc": "nifc",
    "nirsc": "nifc",
    "national interagency": "nifc",
    "incident radio cache": "nifc",
    "siec": "wa_emd",
    "cemnet": "wa_emd",
    "scip": "wa_emd",
}

_SID_RE = re.compile(r"\bSID\s+(\d+)\b", re.IGNORECASE)
_SID_URL_RE = re.compile(r"/sid/(\d+)(?:\b|/)", re.IGNORECASE)
_TRUNK_HINTS = ("trunk", "p25", "wacn")
_WASHINGTON_COUNTIES = (
    "Adams", "Asotin", "Benton", "Chelan", "Clallam", "Clark", "Columbia",
    "Cowlitz", "Douglas", "Ferry", "Franklin", "Garfield", "Grant",
    "Grays Harbor", "Island", "Jefferson", "King", "Kitsap", "Kittitas",
    "Klickitat", "Lewis", "Lincoln", "Mason", "Okanogan", "Pacific",
    "Pend Oreille", "Pierce", "San Juan", "Skagit", "Skamania", "Snohomish",
    "Spokane", "Stevens", "Thurston", "Wahkiakum", "Walla Walla", "Whatcom",
    "Whitman", "Yakima",
)


@dataclass
class RecipeMatch:
    """Matching rules used to decide which facts are relevant to a recipe's
    Favorites List: SID/TrunkId (exact), county (substring), or system
    name (a conservative, length-gated substring fallback for the many
    conventional rows that never cite a SID at all -- see
    :mod:`wasds150.recipes.engine`'s ``_fact_matches``). Any *one*
    configured condition matching is sufficient unless one or more SIDs
    are configured, in which case exact SID identity is authoritative and
    county/name fallbacks are not used. A recipe with no
    plausible automatic source (no condition configured at all) never
    matches anything, by design — a missed match only means "no automatic
    enrichment for this row yet", never a wrong one."""

    source_ids: tuple = ()
    sid: Optional[int] = None
    sids: tuple = ()
    county_contains: tuple = ()
    name_hint: Optional[str] = None

    def matches_source(self, source_id: str) -> bool:
        return not self.source_ids or source_id in self.source_ids

    def configured_sids(self) -> tuple:
        return self.sids or ((self.sid,) if self.sid is not None else ())


@dataclass
class Recipe:
    slug: str
    favorite_key: str
    label: str
    requires_local_hpdb: bool = False
    match: RecipeMatch = field(default_factory=RecipeMatch)
    notes: str = ""


def _detect_sids(system_or_category: str, source_url: str) -> tuple:
    """Return every distinct RR SID stated in the row or its source URL,
    preserving first-seen order."""
    values = [int(value) for value in _SID_RE.findall(system_or_category or "")]
    values.extend(int(value) for value in _SID_URL_RE.findall(source_url or ""))
    return tuple(dict.fromkeys(values))


def _detect_source_ids(*text_fields: str) -> tuple:
    haystack = " ".join(text_fields).lower()
    found = {
        source
        for keyword, source in _KEYWORD_SOURCES.items()
        if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", haystack)
    }
    return tuple(sorted(found))


def _detect_counties(counties_field: str) -> tuple:
    """Extract only real Washington county names from free-form coverage
    text. Regional values such as ``Statewide``, ``Puget Sound`` and
    ``Statewide airspace`` intentionally produce no county filter, while
    mixed prose such as ``Eastern counties (Spokane, Whitman)`` still
    yields the named counties."""
    if not counties_field:
        return ()
    haystack = counties_field.lower()
    found = []
    for county in _WASHINGTON_COUNTIES:
        match = re.search(rf"\b{re.escape(county.lower())}\b", haystack)
        if match:
            found.append((match.start(), county))
    return tuple(county for _, county in sorted(found))


def _detect_name_hint(favorite_name: str) -> Optional[str]:
    """A conservative system-name matching hint: the row's own
    ``favorite_name`` verbatim, gated to a minimum length by
    :mod:`wasds150.recipes.engine`'s ``_fact_matches`` so a short/generic
    name (unlikely for this catalog's rows, which are all specific agency/
    region names) can never cause an overly broad match."""
    name = favorite_name.strip()
    return name or None


def build_default_recipes(catalog: Catalog) -> List[Recipe]:
    """One :class:`Recipe` per row of ``catalog`` (typically the packaged
    baseline), derived purely from that row's own existing free-text
    fields — so every recipe is automatically kept in sync with the
    catalog's 75/78-row shape without hand-maintaining a parallel list."""
    recipes: List[Recipe] = []
    for fl in catalog.favorites:
        scenario_and_type = f"{fl.scenario} {fl.source_type} {fl.system_or_category}"
        requires_local_hpdb = any(hint in scenario_and_type.lower() for hint in _TRUNK_HINTS)
        sids = _detect_sids(fl.system_or_category, fl.source_url)
        source_ids = _detect_source_ids(
            fl.scenario, fl.source_type, fl.system_or_category, fl.departments_or_channels, fl.notes
        )
        counties = _detect_counties(fl.counties)
        name_hint = _detect_name_hint(fl.favorite_name)
        is_discovery_target = fl.source_type.strip().lower() == "discovery target"
        is_rollup = "rollup" in fl.favorite_name.lower() or "reuses fl" in fl.system_or_category.lower()
        if fl.favorite_key == "PSHAM01":
            source_ids = ("wwara",)
            counties = ()
            name_hint = None
        if is_discovery_target or is_rollup:
            source_ids = ()
            sids = ()
            counties = ()
            name_hint = None
        recipes.append(
            Recipe(
                slug=fl.slug,
                favorite_key=fl.favorite_key,
                label=fl.favorite_name,
                requires_local_hpdb=requires_local_hpdb,
                match=RecipeMatch(
                    source_ids=source_ids,
                    sid=sids[0] if sids else None,
                    sids=sids,
                    county_contains=counties,
                    name_hint=name_hint,
                ),
                notes=(
                    "Requires local Sentinel HPDB or RadioReference Premium data for full "
                    "site/talkgroup detail." if requires_local_hpdb else ""
                ),
            )
        )
    return recipes
