"""Turn RadioReference frequency facts into per-county Favorites Lists.

RadioReference's county and state exports are the most complete public-ish
description of who is on the air in Washington, but they are licensed to
the subscriber who downloaded them.  This recipe therefore builds a separate,
``licensed=True`` Favorites List per county (``RRC-KING``, ``RRC-SNOHOMISH``,
...) plus one for the state-wide category (``RRWA``) instead of rewriting any
of the checked-in public lists.  The lists live only in the user's local
catalog; every radio plan can select from them by favorite key.

Structure of one list::

    FavoritesList RRC-KING ("RadioReference - King County")
      System "RadioReference King County"
        Department "<Agency/Category>"   geo-fence = county centre + radius
          Channel per frequency row     mode, tone, input, DMR/NXDN identity

Trunked-system site rows (``Tag == TRS``) are not channels: they are kept as
``fact_type="site"`` facts and summarised in the list notes, because the
scanner already reads full trunked systems from the Sentinel database and a
memory-list transceiver cannot use them at all.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, List, Optional, Tuple

from wasds150.catalog.wa_counties import CountyPoint, county_point
from wasds150.hpe import schema
from wasds150.hpe.validation import frequency_is_scannable, tone_is_valid
from wasds150.models.catalog import ORIGIN_LOCAL, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.recipes.systems import dedupe_channels
from wasds150.sources.facts import NormalizedFact
from wasds150.util.geo import haversine_miles
from wasds150.util.hashing import stable_id

RR_SOURCE_IDS = ("radioreference_premium", "radioreference_api")
STATEWIDE = "Statewide"
STATE_KEY = "RRWA"
COUNTY_KEY_PREFIX = "RRC-"

_SERVICE_TYPE_BY_TAG: Dict[str, int] = {name.lower(): code for code, name in schema.SERVICE_TYPES.items()}
#: RadioReference tags the scanner's service-type table has no exact entry
#: for, mapped to the nearest one so plans can still select by service.
_SERVICE_TYPE_BY_TAG.update({
    "schools": 17,       # Business
    "security": 17,      # Business
    "utilities": 14,     # Public Works
    "corrections": 23,   # Law Talk
    "data": 21,          # Other
})


def county_key(county: str) -> str:
    if county == STATEWIDE:
        return STATE_KEY
    return COUNTY_KEY_PREFIX + county.upper().replace(" ", "")


def is_rr_key(favorite_key: str) -> bool:
    key = favorite_key.upper()
    return key == STATE_KEY or key.startswith(COUNTY_KEY_PREFIX)


def _service_type(tag: str) -> Optional[int]:
    return _SERVICE_TYPE_BY_TAG.get(tag.strip().lower())


def _channel_from_fact(fact: NormalizedFact, county: str) -> Optional[Channel]:
    freq = fact.freq_mhz
    if freq is None or not frequency_is_scannable(freq):
        return None
    raw = fact.raw if isinstance(fact.raw, dict) else {}
    tone = fact.tone or ""
    if tone and not tone_is_valid(tone):
        tone = ""
    tx_tone = raw.get("tx_tone") or ""
    if tx_tone and not tone_is_valid(tx_tone):
        tx_tone = ""
    # RadioReference descriptions can hold tabs and line breaks, which the
    # scanner's list format cannot carry; collapse every run to one space.
    label = " ".join((fact.name or "").split()) or " ".join(str(raw.get("rr_alpha") or "").split()) or f"{freq:.4f}"
    notes = "; ".join(
        part
        for part in (
            f"RadioReference {county} County export" if county != STATEWIDE else "RadioReference Washington state export",
            f"category: {raw.get('rr_category')}" if raw.get("rr_category") else "",
            f"alpha: {raw.get('rr_alpha')}" if raw.get("rr_alpha") else "",
            f"callsign: {raw.get('rr_callsign')}" if raw.get("rr_callsign") else "",
            f"RR mode: {raw.get('rr_mode')}" if raw.get("rr_mode") and raw.get("rr_mode", "").upper() != (fact.mode or "") else "",
            f"tone: {raw.get('rr_tone_out')}" if raw.get("rr_tone_out") and not tone else "",
            f"tag: {raw.get('rr_tag')}" if raw.get("rr_tag") else "",
            fact.source_url,
        )
        if part
    )
    return Channel(
        id=stable_id(f"rr:{county}:{fact.entity_key}", kind="channel"),
        label=label[:64],
        freq_mhz=round(freq, 6),
        mode=fact.mode or "AUTO",
        notes=notes,
        tone=tone,
        service_type=_service_type(raw.get("rr_tag", "")),
        tx_freq_mhz=round(fact.tx_freq_mhz, 6) if fact.tx_freq_mhz is not None else None,
        tx_tone=tx_tone,
        location_precision="unknown",
        dmr_color_code=fact.dmr_color_code,
        dmr_timeslot=fact.dmr_timeslot,
        dmr_talkgroup=fact.dmr_talkgroup,
        nxdn_ran=fact.nxdn_ran,
    )


def _county_of(fact: NormalizedFact) -> str:
    county = (fact.county or "").strip()
    if not county or county.upper() == "UNKNOWN":
        return STATEWIDE
    return county


def build_rr_favorites(
    facts: Iterable[NormalizedFact],
    *,
    home: Optional[Tuple[float, float]] = None,
    enable_within_miles: Optional[float] = None,
) -> List[FavoritesList]:
    """One licensed Favorites List per county seen in the RadioReference facts.

    ``home``/``enable_within_miles`` decide which county lists start enabled:
    a state-wide import produces every county in Washington, and a user near
    Seattle does not want Asotin County's channels on a scanner by default.
    Counties are always *built*; only the initial ``enabled`` flag differs.
    """
    by_county: "OrderedDict[str, List[NormalizedFact]]" = OrderedDict()
    sites_by_county: Dict[str, int] = {}
    facts = list(facts)
    # The live web service covers the whole state; when it ran, a downloaded
    # export would only add a second, older copy of the same rows.
    live = any(f.source_id == "radioreference_api" and f.fact_type == "frequency" for f in facts)
    for fact in facts:
        if fact.source_id not in RR_SOURCE_IDS:
            continue
        if live and fact.source_id != "radioreference_api" and fact.fact_type == "frequency":
            continue
        county = _county_of(fact)
        if fact.fact_type == "site":
            sites_by_county[county] = sites_by_county.get(county, 0) + 1
            continue
        if fact.fact_type != "frequency" or fact.freq_mhz is None:
            continue
        by_county.setdefault(county, []).append(fact)

    favorites: List[FavoritesList] = []
    for county, county_facts in by_county.items():
        point = county_point(county)
        departments: "OrderedDict[str, List[Channel]]" = OrderedDict()
        skipped = 0
        for fact in county_facts:
            channel = _channel_from_fact(fact, county)
            if channel is None:
                skipped += 1
                continue
            raw = fact.raw if isinstance(fact.raw, dict) else {}
            category = " ".join(str(raw.get("rr_category") or "").split()) or "Uncategorized"
            departments.setdefault(category, []).append(channel)
        if not departments:
            continue

        dept_objs: List[Department] = []
        modes: Dict[str, int] = {}
        total = 0
        for category, channels in departments.items():
            channels = dedupe_channels(channels)
            total += len(channels)
            for channel in channels:
                modes[channel.mode or "AUTO"] = modes.get(channel.mode or "AUTO", 0) + 1
            dept_objs.append(
                Department(
                    id=stable_id(f"rr:{county}:dept:{category}", kind="department"),
                    label=category[:64],
                    channels=channels,
                    lat=point.lat if point else None,
                    lon=point.lon if point else None,
                    range_miles=point.radius_miles if point else None,
                    shape="Circle" if point else "",
                )
            )

        key = county_key(county)
        slug = key.lower()
        enabled = True
        if home is not None and enable_within_miles is not None:
            if county == STATEWIDE:
                enabled = True
            elif point is None:
                enabled = False
            else:
                distance = haversine_miles(home[0], home[1], point.lat, point.lon)
                enabled = distance <= enable_within_miles + point.radius_miles
        mode_summary = ", ".join(f"{mode} {count}" for mode, count in sorted(modes.items(), key=lambda kv: -kv[1]))
        site_rows = sites_by_county.get(county, 0)
        favorites.append(
            FavoritesList(
                id=stable_id(slug),
                slug=slug,
                favorite_key=key,
                favorite_name=(
                    "RadioReference - Washington Statewide" if county == STATEWIDE
                    else f"RadioReference - {county} County"
                ),
                region="Washington" if county == STATEWIDE else county,
                counties="Statewide" if county == STATEWIDE else county,
                scenario="Everything RadioReference lists as conventional in this area",
                source_type="RadioReference Premium export (licensed; local catalog only)",
                system_or_category=f"{len(dept_objs)} RadioReference categories",
                sites_or_coverage=(
                    f"{county} County (centre {point.lat:.4f}, {point.lon:.4f}, ~{point.radius_miles:.0f} mi)"
                    if point else "Washington"
                ),
                departments_or_channels=(
                    f"{total} conventional channels; {site_rows} trunked-system site rows kept as facts only"
                    + (f"; {skipped} rows outside scanner coverage skipped" if skipped else "")
                ),
                mode=mode_summary,
                monitorability="Conventional rows program directly; DMR/NXDN need the scanner upgrade",
                upgrade_required="DMR/NXDN where listed",
                source_url="https://www.radioreference.com/db/browse/stid/53",
                notes=(
                    "Built from the user's own RadioReference Premium export. Licensed data: "
                    "stays in the local catalog and is never committed or redistributed."
                ),
                enabled=enabled,
                origin=ORIGIN_LOCAL,
                licensed=True,
                systems=[
                    System(
                        id=stable_id(f"rr:{county}:system", kind="system"),
                        label=(
                            "RadioReference Washington Statewide" if county == STATEWIDE
                            else f"RadioReference {county} County"
                        ),
                        departments=dept_objs,
                    )
                ],
                provenance=[
                    Provenance(
                        source_adapter=county_facts[0].source_id,
                        source_url=county_facts[0].source_url or None,
                        fetched_at=county_facts[0].retrieved_at or None,
                        confidence="verified",
                    )
                ],
            )
        )
    return favorites


TRUNKED_KEY_PREFIX = "RRT-"
TRUNKED_STATE_KEY = "RRT-WA"
_RR_STATE_URL = "https://www.radioreference.com/db/browse/stid/53"


def trunked_key(county: str) -> str:
    if county == STATEWIDE:
        return TRUNKED_STATE_KEY
    return TRUNKED_KEY_PREFIX + county.upper().replace(" ", "")


def build_rr_trunked_favorites(
    facts: Iterable[NormalizedFact],
    *,
    home: Optional[Tuple[float, float]] = None,
    enable_within_miles: Optional[float] = None,
    exclude_sids: Iterable[int] = (),
) -> List[FavoritesList]:
    """One licensed ``RRT-<COUNTY>`` list per county of the P25 trunked
    systems the RadioReference web service returned, leaving out any system
    a catalog row names by SID (that row already carries it, curated).

    A system on one county goes to that county's list; one spanning several
    (or none) goes to ``RRT-WA``. Start-enabled follows the county lists:
    only near home. Each list is its own file on the scanner, so one very
    large trunked system cannot push a county's conventional list over the
    scanner's file size.
    """
    import copy

    exclude = {int(sid) for sid in exclude_sids}
    by_county: "OrderedDict[str, List[System]]" = OrderedDict()
    for fact in facts:
        if fact.source_id != "radioreference_api" or fact.fact_type != "system":
            continue
        raw = fact.raw if isinstance(fact.raw, dict) else {}
        try:
            sid = int(raw.get("sid"))
        except (TypeError, ValueError):
            continue
        if sid in exclude or not raw.get("system"):
            continue
        county = (fact.county or STATEWIDE).strip() or STATEWIDE
        by_county.setdefault(county, []).append(System.from_dict(copy.deepcopy(raw["system"])))

    favorites: List[FavoritesList] = []
    for county, systems in sorted(by_county.items()):
        point = county_point(county) if county != STATEWIDE else None
        enabled = True
        if home is not None and enable_within_miles is not None and county != STATEWIDE:
            enabled = point is not None and (
                haversine_miles(home[0], home[1], point.lat, point.lon) <= enable_within_miles + point.radius_miles
            )
        talkgroups = sum(len(d.channels) for s in systems for site in s.sites for d in site.departments)
        key = trunked_key(county)
        favorites.append(
            FavoritesList(
                id=stable_id(key.lower()),
                slug=key.lower(),
                favorite_key=key,
                favorite_name=(
                    "RadioReference Trunked - Washington Statewide" if county == STATEWIDE
                    else f"RadioReference Trunked - {county} County"
                ),
                region="Washington" if county == STATEWIDE else county,
                counties="Statewide" if county == STATEWIDE else county,
                scenario="Every P25 trunked system RadioReference lists here that no curated list already carries",
                source_type="RadioReference Database Web Service (licensed; local catalog only)",
                system_or_category=f"{len(systems)} trunked systems",
                sites_or_coverage="Each system's own site coverage circles",
                departments_or_channels=f"{talkgroups} talkgroups",
                mode="P25",
                monitorability="Native P25 on the scanner; trunked, so scanner only",
                upgrade_required="None",
                source_url=_RR_STATE_URL,
                notes=(
                    "Built live from the RadioReference web service. Licensed data: stays in the local "
                    "catalog and is never committed or redistributed."
                ),
                enabled=enabled,
                origin=ORIGIN_LOCAL,
                licensed=True,
                systems=sorted(systems, key=lambda s: s.label),
                provenance=[Provenance(source_adapter="radioreference_api", source_url=_RR_STATE_URL, confidence="verified")],
            )
        )
    return favorites
