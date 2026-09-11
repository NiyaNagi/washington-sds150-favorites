"""Reviewed RepeaterBook records as a local-only Favorites List.

The list is built from the store each time a plan export asks for it
(``plan export --with-repeaterbook``) and is never saved into the catalog, so
retention and Delete All reach every copy. It is marked ``licensed`` so the
``--exclude-licensed`` path that produces committable files can never include
it, and each channel note carries its RepeaterBook id, retrieval date and the
attribution.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from wasds150.models.catalog import ORIGIN_LOCAL, Channel, Department, FavoritesList, System
from wasds150.models.plan import SORT_FREQ, TX_REPEATER, ChannelSelector, PlanBlock
from wasds150.sources.repeaterbook.policy import (
    ATTRIBUTION_TEXT,
    ATTRIBUTION_URL,
    DETAIL_URL_CONFIRMED,
    DETAIL_URL_TEMPLATE,
)
from wasds150.util.hashing import stable_id

FAVORITE_KEY = "RB01"
BLOCK_LABEL = "RepeaterBook Reviewed"


def detail_url(state_id: str, rb_id: str) -> str:
    """The record's RepeaterBook page once that URL form is confirmed;
    RepeaterBook's home page until then."""
    if DETAIL_URL_CONFIRMED and state_id and rb_id:
        return DETAIL_URL_TEMPLATE.format(state_id=state_id, rb_id=rb_id)
    return ATTRIBUTION_URL


def _channel(record: Dict[str, Any]) -> Channel:
    retrieved = (record.get("retrieved_at") or "")[:10]
    label = " ".join(part for part in (record.get("callsign"), record.get("city")) if part) or record["rb_key"]
    return Channel(
        id=stable_id(f"repeaterbook:{record['rb_key']}", kind="channel"),
        label=label,
        freq_mhz=record["output_mhz"],
        mode=record.get("mode") or "FM",
        tone=record.get("rx_tone") or "",
        tx_tone=record.get("tx_tone") or "",
        tx_freq_mhz=record.get("input_mhz"),
        service_type=13,
        lat=record.get("lat"),
        lon=record.get("lon"),
        location_precision="unknown",
        notes=(
            f"RepeaterBook record {record['rb_key']}, retrieved {retrieved}; "
            f"{ATTRIBUTION_TEXT} {detail_url(record.get('state_id', ''), record.get('rb_id', ''))}"
        ),
    )


def favorite_from_records(records: List[Dict[str, Any]]) -> Optional[FavoritesList]:
    if not records:
        return None
    by_region: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        by_region.setdefault(record.get("region") or "Other", []).append(record)
    departments = [
        Department(
            id=stable_id(f"repeaterbook:dept:{region}", kind="department"),
            label=f"RepeaterBook {region}",
            channels=[_channel(r) for r in sorted(rows, key=lambda r: r["output_mhz"])],
        )
        for region, rows in sorted(by_region.items())
    ]
    return FavoritesList(
        id=stable_id("rb01"),
        slug="rb01",
        favorite_key=FAVORITE_KEY,
        favorite_name="RepeaterBook reviewed repeaters",
        region="Operator-chosen centre and radius",
        counties="",
        scenario="Operator-reviewed amateur repeaters, for travel",
        source_type="RepeaterBook Export API, reviewed locally",
        system_or_category="RepeaterBook reviewed records",
        sites_or_coverage="Operator-chosen centre and radius",
        departments_or_channels="Operator-reviewed RepeaterBook records",
        mode="FM",
        monitorability="Full - unencrypted",
        upgrade_required="None",
        source_url=ATTRIBUTION_URL,
        notes=f"{ATTRIBUTION_TEXT} ({ATTRIBUTION_URL}). Local only: never committed, bundled or shared.",
        origin=ORIGIN_LOCAL,
        licensed=True,
        systems=[
            System(
                id=stable_id("repeaterbook:system", kind="system"),
                label="RepeaterBook reviewed",
                departments=departments,
            )
        ],
    )


def plan_block() -> PlanBlock:
    """Appended to a plan only by ``--with-repeaterbook``."""
    return PlanBlock(
        label=BLOCK_LABEL,
        selectors=(ChannelSelector(favorite_keys=(FAVORITE_KEY,)),),
        tx_policy=TX_REPEATER,
        sort=SORT_FREQ,
        notes=f"Operator-reviewed RepeaterBook records. {ATTRIBUTION_TEXT}.",
    )
