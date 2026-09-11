"""FCC-licensed digital voice systems as one public Favorites List.

FCC ULS emission designators say what a licensee transmits: ``7K60FXE`` is
DMR, ``4K00F1E`` NXDN, ``8K10F1E`` P25. The ULS adapter turns those into a
mode per frequency (see :func:`wasds150.sources.fcc_uls.mode_from_emission`);
this recipe collects every digital-voice frequency into ``FCCDIG``, one
department per radio service, each channel at the licence's own location so
radio plans can select it by distance.

The list is public data (US federal work) with ``origin=local`` because it
is built on this machine from a download. It is rebuilt whenever the FCC
source ran, like the RadioReference county lists. A statewide extract with no
distance or emission filter holds thousands of frequencies, so the list
starts disabled above :data:`ENABLE_LIMIT` channels; narrow the source
(``wasds150 sources configure --fcc-within-miles 60``) or enable it by hand.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, List, Optional

from wasds150.hpe.validation import frequency_is_scannable
from wasds150.models.catalog import ORIGIN_LOCAL, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.recipes.systems import dedupe_channels
from wasds150.sources.facts import NormalizedFact
from wasds150.util.hashing import stable_id

FCC_DIGITAL_KEY = "FCCDIG"
DIGITAL_MODES = ("DMR", "NXDN", "P25")
#: Above this many channels the list starts disabled.
ENABLE_LIMIT = 500
_SOURCE_URL = "https://data.fcc.gov/download/pub/uls/complete/"

_SERVICE_NAMES = {
    "IG": "Industrial/Business Pool",
    "YG": "Industrial/Business Pool, Trunked",
    "PW": "Public Safety Pool",
    "YW": "Public Safety Pool, Trunked",
}
#: Uniden service type 17 is Business.
_BUSINESS = {"IG", "YG"}


def _clean(text: str) -> str:
    return " ".join((text or "").replace("\t", " ").split())[:64]


def build_fcc_digital_favorite(facts: Iterable[NormalizedFact]) -> Optional[FavoritesList]:
    rows = [
        fact for fact in facts
        if fact.source_id == "fcc_uls"
        and fact.fact_type == "frequency"
        and fact.freq_mhz is not None
        and (fact.mode or "").upper() in DIGITAL_MODES
        and frequency_is_scannable(fact.freq_mhz)
    ]
    if not rows:
        return None

    by_service: "OrderedDict[str, List[Channel]]" = OrderedDict()
    for fact in sorted(rows, key=lambda f: (str((f.raw or {}).get("radio_service_code", "")), f.freq_mhz, f.name)):
        raw = fact.raw if isinstance(fact.raw, dict) else {}
        code = str(raw.get("radio_service_code") or "??")
        notes = "; ".join(
            part for part in (
                f"FCC ULS {code}",
                f"call sign {raw['call_sign']}" if raw.get("call_sign") else "",
                f"emissions {', '.join(raw['emissions'])}" if raw.get("emissions") else "",
            ) if part
        )
        by_service.setdefault(code, []).append(
            Channel(
                id=stable_id(f"fccdig:{fact.entity_key}", kind="channel"),
                label=_clean(fact.name) or f"{fact.freq_mhz:.4f}",
                freq_mhz=round(fact.freq_mhz, 6),
                mode=(fact.mode or "").upper(),
                notes=notes,
                service_type=17 if code in _BUSINESS else None,
                lat=fact.lat,
                lon=fact.lon,
                location_precision="exact" if fact.location_precision == "exact" else "unknown",
            )
        )

    departments = [
        Department(
            id=stable_id(f"fccdig:dept:{code}", kind="department"),
            label=_SERVICE_NAMES.get(code, f"Radio service {code}"),
            channels=dedupe_channels(channels),
        )
        for code, channels in by_service.items()
    ]
    total = sum(len(d.channels) for d in departments)
    modes = {}
    for department in departments:
        for channel in department.channels:
            modes[channel.mode] = modes.get(channel.mode, 0) + 1
    newest = max((f.retrieved_at for f in rows if f.retrieved_at), default=None)
    return FavoritesList(
        id=stable_id(FCC_DIGITAL_KEY.lower()),
        slug=FCC_DIGITAL_KEY.lower(),
        favorite_key=FCC_DIGITAL_KEY,
        favorite_name="FCC-Licensed Digital Voice",
        region="Washington",
        counties="Licence locations",
        scenario="Licensed DMR, NXDN and P25 conventional systems from the FCC ULS",
        source_type="FCC ULS bulk data (public domain)",
        system_or_category=f"{len(departments)} radio services",
        sites_or_coverage="Each channel at its licence location",
        departments_or_channels=f"{total} digital voice frequencies",
        mode=", ".join(f"{mode} {count}" for mode, count in sorted(modes.items(), key=lambda kv: -kv[1])),
        monitorability="Digital decode required; some licensees encrypt or trunk",
        upgrade_required="DMR/NXDN upgrade on the SDS150",
        source_url=_SOURCE_URL,
        notes=(
            "Built from FCC ULS licences whose emission designators name a digital voice mode. "
            + (f"Starts disabled: {total} channels exceed {ENABLE_LIMIT}." if total > ENABLE_LIMIT else "")
        ).strip(),
        enabled=total <= ENABLE_LIMIT,
        origin=ORIGIN_LOCAL,
        systems=[
            System(id=stable_id("fccdig:system", kind="system"), label="FCC-Licensed Digital Voice", departments=departments)
        ],
        provenance=[Provenance(source_adapter="fcc_uls", source_url=_SOURCE_URL, fetched_at=newest, confidence="community")],
    )
