"""The DSTARInfo reference lists: ``DSTARINFO`` (the D-STAR directory, with
approximate positions) and ``DSTARFM`` (RepeaterBook's FM repeaters from
DSTARInfo's DR-radio download).

Both are rebuilt whenever their source ran, like FAAAIR, and a list whose
source did not run keeps its previous copy. They are disabled reference
lists: no radio or scanner list takes them directly. The amateur repeater
registry (:mod:`wasds150.catalog.repeater_registry`) reads them, merged with
WWARA, IACC and the rest.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, List

from wasds150.catalog.repeater_registry import DSTARFM_KEY, DSTARINFO_KEY, STATE_NOTE
from wasds150.models.catalog import ORIGIN_LOCAL, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.sources.facts import NormalizedFact
from wasds150.util.hashing import stable_id


def _state(country_state: str) -> str:
    return (country_state or "").split(",")[-1].strip()


def _dstar_channel(fact: NormalizedFact) -> Channel:
    raw = fact.raw
    details = raw.get("details") or {}
    city = raw.get("city", "")
    notes = [
        f"{STATE_NOTE}{_state(raw.get('country_state', ''))}",
        f"gateway: {', '.join(raw.get('directories') or [])}" if raw.get("directories") else "",
        f"sponsor: {details['Sponsor']}" if details.get("Sponsor") else "",
        f"site: {details['Location_Description']}" if details.get("Location_Description") else "",
        f"coverage: {details['Coverage_Description']}" if details.get("Coverage_Description") else "",
        f"updated {details['Last_Update']}" if details.get("Last_Update") else "",
        raw.get("offset_note", ""),
        fact.source_url,
    ]
    label = f"{raw['call']} {raw['module']}" + (f" - {city}" if city else "")
    return Channel(
        id=stable_id(f"dstarinfo:{raw['call']}:{raw['module']}", kind="channel"),
        label=label[:64],
        freq_mhz=fact.freq_mhz,
        tx_freq_mhz=fact.tx_freq_mhz,
        mode="DV",
        service_type=13,
        lat=fact.lat,
        lon=fact.lon,
        location_precision=fact.location_precision if fact.lat is not None else "",
        dv_urcall="CQCQCQ",
        dv_rpt1=raw.get("rpt1", ""),
        dv_rpt2=raw.get("rpt2", ""),
        notes="; ".join(part for part in notes if part),
    )


def _fm_channel(fact: NormalizedFact) -> Channel:
    raw = fact.raw
    call = (raw.get("Repeater Call Sign") or "").strip().upper()
    place = (raw.get("Name") or "").strip()
    notes = [
        f"{STATE_NOTE}{(raw.get('Sub Name') or '').strip()}",
        raw.get("tone_note", ""),
        "RepeaterBook data via DSTARInfo (personal use only)",
    ]
    return Channel(
        id=stable_id(f"dstarfm:{call}:{fact.freq_mhz:.4f}", kind="channel"),
        label=(f"{call} - {place}" if place else call)[:64],
        freq_mhz=fact.freq_mhz,
        tx_freq_mhz=fact.tx_freq_mhz,
        mode="FM",
        tone=fact.tone or "",
        tx_tone=raw.get("tx_tone", ""),
        service_type=13,
        lat=fact.lat,
        lon=fact.lon,
        location_precision=fact.location_precision if fact.lat is not None else "",
        notes="; ".join(part for part in notes if part),
    )


def _favorite(key: str, name: str, source_type: str, channels: List[Channel], adapter: str, url: str, notes: str) -> FavoritesList:
    by_state: "OrderedDict[str, List[Channel]]" = OrderedDict()
    for channel in sorted(channels, key=lambda c: (c.notes.split(";")[0], c.freq_mhz or 0.0)):
        by_state.setdefault(channel.notes.split(";")[0][len(STATE_NOTE):] or "Unknown", []).append(channel)
    departments = [
        Department(id=stable_id(f"{key.lower()}:{state}", kind="department"), label=state[:64] or "Unknown", channels=members)
        for state, members in by_state.items()
    ]
    return FavoritesList(
        id=stable_id(key.lower()),
        slug=key.lower(),
        favorite_key=key,
        favorite_name=name,
        region="Worldwide" if key == DSTARINFO_KEY else "Western North America",
        counties="Station locations",
        scenario="Reference data for the amateur repeater registry",
        source_type=source_type,
        system_or_category=f"{len(departments)} states and provinces",
        sites_or_coverage="Approximate positions",
        departments_or_channels=f"{len(channels)} repeaters",
        mode="DV" if key == DSTARINFO_KEY else "FM",
        monitorability="Reference only: read by HAMREG",
        upgrade_required="",
        source_url=url,
        notes=notes,
        enabled=False,
        reference_only=True,
        origin=ORIGIN_LOCAL,
        systems=[System(id=stable_id(f"{key.lower()}:system", kind="system"), label=name, departments=departments)],
        provenance=[Provenance(source_adapter=adapter, source_url=url, confidence="community")],
    )


def build_dstarinfo_favorites(facts: Iterable[NormalizedFact]) -> List[FavoritesList]:
    facts = list(facts)
    dstar = [f for f in facts if f.source_id == "dstarinfo" and f.mode == "DV" and f.freq_mhz is not None]
    fm = [f for f in facts if f.source_id == "dstarinfo_fm" and f.freq_mhz is not None]
    lists: List[FavoritesList] = []
    if dstar:
        lists.append(_favorite(
            DSTARINFO_KEY, "DSTARInfo D-STAR Directory", "DSTARInfo repeater directory (personal use only)",
            [_dstar_channel(f) for f in dstar], "dstarinfo", "http://apps.dstarinfo.com/D-STAR_Repeater_List.aspx",
            "Every D-STAR module in DSTARInfo's directory, with its approximate position where the DR download gives one.",
        ))
    if fm:
        lists.append(_favorite(
            DSTARFM_KEY, "DSTARInfo FM Repeaters (RepeaterBook)", "RepeaterBook FM data via DSTARInfo (personal use only)",
            [_fm_channel(f) for f in fm], "dstarinfo_fm", "http://appserver.dstarinfo.com/downloads/nearest.aspx",
            "The FM repeaters nearest home from DSTARInfo's DR-radio download. RepeaterBook's data: never committed.",
        ))
    return lists
