"""Channel plans: a named, ordered selection of catalog channels for one radio.

The catalog answers "what exists".  A plan answers "what goes in this radio,
in what order, and may I transmit on it".  Keeping the two apart is what lets
one refreshable database drive an SDS150, a TD-H9 and eventually an FTX-1
without any of them contaminating the others.

A plan selects by *rule* rather than by listing frequencies.  That matters
because the database is refreshed periodically: when a new repeater is
coordinated, a plan that says "analog amateur repeaters within 60 miles of
Ozette" picks it up, whereas a hand-listed plan silently goes stale.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: Transmit policy for a block.  Receive-only is the default everywhere,
#: because keying up on a frequency you are not authorized for is the one
#: mistake this project must never make on a user's behalf.
TX_NONE = "none"
TX_SIMPLEX = "simplex"
TX_REPEATER = "repeater"
TX_POLICIES = (TX_NONE, TX_SIMPLEX, TX_REPEATER)

SORT_CATALOG = "catalog"
SORT_FREQ = "freq"
SORT_LABEL = "label"
#: Digit-aware label order, so "GMRS 2" comes before "GMRS 15" and marine
#: channels run in channel-number order. Plain alphabetical sorting puts 15
#: before 2, and frequency order interleaves services that share a band.
SORT_NATURAL = "natural"
SORT_ORDERS = (SORT_CATALOG, SORT_FREQ, SORT_LABEL, SORT_NATURAL)

_DIGITS = re.compile(r"(\d+)")


def natural_key(text: str) -> Tuple:
    """Sort key treating runs of digits as numbers.

    ``("GMRS ", 2)`` sorts before ``("GMRS ", 15)``, which is what an
    operator scrolling a channel list expects to see.
    """
    parts = _DIGITS.split(text.upper())
    return tuple(int(p) if p.isdigit() else p for p in parts)


@dataclass(frozen=True)
class ChannelSelector:
    """Matches catalog channels by where they live and what they are.

    Every criterion is optional; an empty selector matches nothing, which is
    deliberate so that a typo in a plan yields an obviously empty block rather
    than the entire catalog.
    """

    favorite_keys: Tuple[str, ...] = ()
    department_pattern: str = ""
    label_pattern: str = ""
    exclude_label_pattern: str = ""
    freq_ranges: Tuple[Tuple[float, float], ...] = ()
    modes: Tuple[str, ...] = ()
    service_types: Tuple[int, ...] = ()
    #: Channels the catalog marks as avoided are excluded unless asked for.
    include_avoided: bool = False

    def is_empty(self) -> bool:
        return not any(
            (
                self.favorite_keys,
                self.department_pattern,
                self.label_pattern,
                self.freq_ranges,
                self.modes,
                self.service_types,
            )
        )

    def matches(self, favorite_key: str, department_label: str, channel: Any) -> bool:
        if self.is_empty():
            return False
        if self.favorite_keys and favorite_key.upper() not in {
            key.upper() for key in self.favorite_keys
        }:
            return False
        if self.department_pattern and not re.search(
            self.department_pattern, department_label, re.IGNORECASE
        ):
            return False
        if self.label_pattern and not re.search(
            self.label_pattern, channel.label, re.IGNORECASE
        ):
            return False
        if self.exclude_label_pattern and re.search(
            self.exclude_label_pattern, channel.label, re.IGNORECASE
        ):
            return False
        if self.freq_ranges:
            freq = channel.freq_mhz
            if freq is None or not any(
                low <= freq <= high for low, high in self.freq_ranges
            ):
                return False
        if self.modes:
            mode = (channel.mode or "").upper()
            if mode not in {m.upper() for m in self.modes}:
                return False
        if self.service_types and channel.service_type not in self.service_types:
            return False
        if channel.avoid and not self.include_avoided:
            return False
        return True


@dataclass(frozen=True)
class PlanBlock:
    """One contiguous run of memory slots with a shared purpose."""

    label: str
    selectors: Tuple[ChannelSelector, ...] = ()
    tx_policy: str = TX_NONE
    #: Transmit power label passed through to the radio, when it has one.
    #: Use a value the target radio actually offers: a radio with fixed power
    #: steps will otherwise pick the nearest and warn.
    power: str = "1.0W"
    sort: str = SORT_CATALOG
    #: Hard ceiling on slots this block may consume.
    limit: Optional[int] = None
    #: Programmed but excluded from the scan sweep.
    skip_scan: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if self.tx_policy not in TX_POLICIES:
            raise ValueError(
                f"block {self.label!r}: tx_policy must be one of {TX_POLICIES}"
            )
        if self.sort not in SORT_ORDERS:
            raise ValueError(f"block {self.label!r}: sort must be one of {SORT_ORDERS}")
        if self.limit is not None and self.limit <= 0:
            raise ValueError(f"block {self.label!r}: limit must be positive")


@dataclass(frozen=True)
class ChannelPlan:
    """An ordered set of blocks targeting one radio."""

    id: str
    radio_id: str
    label: str
    description: str = ""
    blocks: Tuple[PlanBlock, ...] = ()
    #: Slots held back at the end of memory for field discoveries.
    reserve_slots: int = 0

    def __post_init__(self) -> None:
        if self.reserve_slots < 0:
            raise ValueError("reserve_slots must not be negative")
        seen = set()
        for block in self.blocks:
            if block.label in seen:
                raise ValueError(f"duplicate block label {block.label!r}")
            seen.add(block.label)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "radio_id": self.radio_id,
            "label": self.label,
            "description": self.description,
            "reserve_slots": self.reserve_slots,
            "blocks": [
                {
                    "label": block.label,
                    "tx_policy": block.tx_policy,
                    "power": block.power,
                    "sort": block.sort,
                    "limit": block.limit,
                    "skip_scan": block.skip_scan,
                    "notes": block.notes,
                }
                for block in self.blocks
            ],
        }
