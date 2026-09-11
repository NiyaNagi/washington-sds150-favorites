"""How local a DMR talkgroup's traffic is, for scan ordering.

A PNWDigital repeater carries forty-odd talkgroups. Sorted by frequency, a
radio stops on Hawaii and Michigan as readily as on Seattle, and the first
zone and scan list - the ones an operator actually starts - fill with
whatever sorted first. A tier puts local calling and conversation groups
first, regional groups next, wide-area groups after that and test groups
last, so the first scan list holds the calling groups on the nearest
machines (see ``SORT_TIER_DISTANCE`` in :mod:`wasds150.models.plan`).

Tiers are keyed by ``(network, talkgroup name)`` rather than by ID because
IDs are not unique across networks: TG 3166 is "Metro 2" on PNWDigital and
"Local 2" on SeattleDMR. The names are the ones the networks publish in their
layouts (see :mod:`wasds150.catalog.atd890_dmr`). The grouping is this
project's judgement of "how local", guided by the intended-use notes on the
two networks' talkgroup pages (linked from ``docs/at-d890uv-programming.md``);
it is not a classification either network publishes. A talkgroup the table
does not know is wide-area: it is still programmed, only later in the list.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

TIER_CORE = 0
TIER_REGIONAL = 1
TIER_WIDE = 2
TIER_TEST = 3
TIERS = (TIER_CORE, TIER_REGIONAL, TIER_WIDE, TIER_TEST)
DEFAULT_TIER = TIER_WIDE

_CORE = TIER_CORE
_REGIONAL = TIER_REGIONAL
_TEST = TIER_TEST

TIER_TABLE: Dict[Tuple[str, str], int] = {
    # PNWDigital: statewide/regional calling and the Puget Sound local groups.
    ("PNWDigital", "Washington 1"): _CORE,
    ("PNWDigital", "Washington 2"): _CORE,
    ("PNWDigital", "PNW 1"): _CORE,
    ("PNWDigital", "PNW 2"): _CORE,
    ("PNWDigital", "Local 1"): _CORE,
    ("PNWDigital", "Metro 2"): _CORE,
    ("PNWDigital", "TAC 310"): _CORE,
    ("PNWDigital", "TAC 311"): _CORE,
    ("PNWDigital", "TAC 312"): _CORE,
    ("PNWDigital", "Cascades 1"): _CORE,
    ("PNWDigital", "I-5 1"): _CORE,
    ("PNWDigital", "Oregon 1"): _REGIONAL,
    ("PNWDigital", "BC 1"): _REGIONAL,
    ("PNWDigital", "BC 2"): _REGIONAL,
    ("PNWDigital", "Net 2"): _REGIONAL,
    ("PNWDigital", "PNW Rgnl 2"): _REGIONAL,
    ("PNWDigital", "TAC 1"): _REGIONAL,
    ("PNWDigital", "TAC 2"): _REGIONAL,
    ("PNWDigital", "TAC 3"): _REGIONAL,
    ("PNWDigital", "Bridge 2"): _REGIONAL,
    ("PNWDigital", "Inland 2"): _REGIONAL,
    ("PNWDigital", "I-84 2"): _REGIONAL,
    ("PNWDigital", "RACOM ARC 2"): _REGIONAL,
    ("PNWDigital", "Parrot 1"): _TEST,
    ("PNWDigital", "Audio Test 2"): _TEST,
    # SeattleDMR: King County and Seattle groups, plus its linked set.
    ("SeattleDMR", "Washington 1"): _CORE,
    ("SeattleDMR", "Washington 2"): _CORE,
    ("SeattleDMR", "King County"): _CORE,
    ("SeattleDMR", "Seattle 1"): _CORE,
    ("SeattleDMR", "Seattle 2"): _CORE,
    ("SeattleDMR", "Puget Sound"): _CORE,
    ("SeattleDMR", "Local 1"): _CORE,
    ("SeattleDMR", "Local 2"): _CORE,
    ("SeattleDMR", "Link 1"): _REGIONAL,
    ("SeattleDMR", "Link 2"): _REGIONAL,
    ("SeattleDMR", "Link 3"): _REGIONAL,
    ("SeattleDMR", "Link 4"): _REGIONAL,
    ("SeattleDMR", "Link 5"): _REGIONAL,
    ("SeattleDMR", "Link 6"): _REGIONAL,
    ("SeattleDMR", "PNW Rgnl 2"): _REGIONAL,
    ("SeattleDMR", "TAC 313"): _REGIONAL,
    ("SeattleDMR", "BEARS 1"): _REGIONAL,
    ("SeattleDMR", "BEARS 2"): _REGIONAL,
    ("SeattleDMR", "Parrot 1"): _TEST,
    ("SeattleDMR", "Audio Test 2"): _TEST,
    # BrandMeister: the statewide group first, then the Pacific Northwest and
    # emergency groups the local repeaters carry statically.
    ("BrandMeister", "Washington - 10 Minute Limit"): _CORE,
    ("BrandMeister", "Olympic Peninsula"): _REGIONAL,
    ("BrandMeister", "PNW-West"): _REGIONAL,
    ("BrandMeister", "PNWR"): _REGIONAL,
    ("BrandMeister", "Washington TAC"): _REGIONAL,
    ("BrandMeister", "Washington State ARES"): _REGIONAL,
    ("BrandMeister", "Washington State ARES TAC"): _REGIONAL,
}

#: Echo/parrot and audio-test groups on networks the table does not list.
_TEST_NAME = re.compile(r"\b(parrot|audio test|echo test)\b", re.IGNORECASE)


def talkgroup_tier(network: str, name: str, tg_id: Optional[int] = None) -> int:
    """Tier of one talkgroup; unknown groups are :data:`DEFAULT_TIER`.

    A row with neither an ID nor a name is a bare colour-code entry (the
    coordinator's record of a repeater before any layout is applied); it has
    no talkgroup to rank and counts as wide-area.
    """
    name = (name or "").strip()
    if tg_id is None and not name:
        return DEFAULT_TIER
    tier = TIER_TABLE.get(((network or "").strip(), name))
    if tier is not None:
        return tier
    if _TEST_NAME.search(name):
        return TIER_TEST
    return DEFAULT_TIER


def channel_tier(channel: Any) -> int:
    """:func:`talkgroup_tier` of a catalog channel (any object with the
    ``network``/``dmr_talkgroup_name``/``dmr_talkgroup`` attributes)."""
    return talkgroup_tier(
        getattr(channel, "network", "") or "",
        getattr(channel, "dmr_talkgroup_name", "") or "",
        getattr(channel, "dmr_talkgroup", None),
    )
