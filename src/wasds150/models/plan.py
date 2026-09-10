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

from wasds150.catalog.dmr_talkgroup_tiers import channel_tier
from wasds150.util.geo import haversine_miles

#: Transmit policy for a block.  Receive-only is the default everywhere,
#: because keying up on a frequency you are not authorized for is the one
#: mistake this project must never make on a user's behalf.
TX_NONE = "none"
TX_SIMPLEX = "simplex"
TX_REPEATER = "repeater"
#: Repeater when the channel publishes an input, simplex otherwise - for
#: services whose channels are both (the main GMRS channels are also
#: repeater outputs).
TX_AUTO = "auto"
TX_POLICIES = (TX_NONE, TX_SIMPLEX, TX_REPEATER, TX_AUTO)

SORT_CATALOG = "catalog"
SORT_FREQ = "freq"
SORT_LABEL = "label"
#: Digit-aware label order, so "GMRS 2" comes before "GMRS 15" and marine
#: channels run in channel-number order. Plain alphabetical sorting puts 15
#: before 2, and frequency order interleaves services that share a band.
SORT_NATURAL = "natural"
#: DMR talkgroup tier first (see :mod:`wasds150.catalog.dmr_talkgroup_tiers`),
#: then distance from the block's radius centre, then frequency, so the first
#: zone and scan list hold the calling groups on the nearest machines.
SORT_TIER_DISTANCE = "tier-distance"
SORT_ORDERS = (SORT_CATALOG, SORT_FREQ, SORT_LABEL, SORT_NATURAL, SORT_TIER_DISTANCE)

_DIGITS = re.compile(r"(\d+)")

#: How a radius filter treats a channel's department geo-fence.
#:
#: ``"channel"`` uses the channel's own position only and drops unlocated
#: channels (the original, strict rule). ``"department"`` falls back to the
#: department geo-fence for channels with no position of their own - the
#: shape of RadioReference county lists, where every channel inherits the
#: county centre and radius. ``"either"`` also admits a located channel whose
#: department fence overlaps the circle, for catch-all blocks that would
#: rather keep a borderline list than lose it.
GEO_CHANNEL = "channel"
GEO_DEPARTMENT = "department"
GEO_EITHER = "either"
GEO_FALLBACKS = (GEO_CHANNEL, GEO_DEPARTMENT, GEO_EITHER)


def _fence_overlaps(department: Any, lat: float, lon: float, miles: float) -> bool:
    """True when ``department``'s geo-fence circle overlaps the radius circle."""
    if department is None:
        return False
    fence_lat = getattr(department, "lat", None)
    fence_lon = getattr(department, "lon", None)
    if fence_lat is None or fence_lon is None:
        return False
    reach = miles + float(getattr(department, "range_miles", None) or 0.0)
    return haversine_miles(lat, lon, fence_lat, fence_lon) <= reach


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
    #: ``(latitude, longitude, miles)`` - keep only channels whose own
    #: transmitter site is within ``miles`` of that point.
    #:
    #: This filters on the channel's position, not its department's. A
    #: department geo-fence is one circle around a whole region, which
    #: answers "should this list be active near here"; a repeater list needs
    #: "can I work this particular machine from here", which is per station.
    #:
    #: A channel with no coordinates is **dropped** when this is set. Silently
    #: keeping unlocated channels would quietly turn a radius filter into no
    #: filter at all for any source that omits positions.
    within_miles: Optional[Tuple[float, float, float]] = None
    #: Channels the catalog marks as avoided are excluded unless asked for.
    include_avoided: bool = False
    #: Regular expression over the favorite key, for a naming family rather
    #: than a fixed list of keys (``^RRC-`` is every RadioReference county).
    favorite_key_pattern: str = ""
    #: Departments to leave out, such as far-away counties in a statewide list.
    exclude_department_pattern: str = ""
    #: See :data:`GEO_FALLBACKS`; consulted only when ``within_miles`` is set.
    geo_fallback: str = GEO_CHANNEL
    #: Keep only channels whose DMR talkgroup falls in these tiers (see
    #: :mod:`wasds150.catalog.dmr_talkgroup_tiers`); a channel with no
    #: talkgroup counts as wide-area.
    dmr_tiers: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.geo_fallback not in GEO_FALLBACKS:
            raise ValueError(f"geo_fallback must be one of {GEO_FALLBACKS}")

    def is_empty(self) -> bool:
        # Exclusions never make a selector non-empty: an exclude-only
        # selector would otherwise match the whole catalog.
        return not any(
            (
                self.favorite_keys,
                self.favorite_key_pattern,
                self.dmr_tiers,
                self.department_pattern,
                self.label_pattern,
                self.freq_ranges,
                self.modes,
                self.service_types,
                self.within_miles,
            )
        )

    def matches(
        self,
        favorite_key: str,
        department_label: str,
        channel: Any,
        department: Any = None,
    ) -> bool:
        if self.is_empty():
            return False
        if self.favorite_keys and favorite_key.upper() not in {
            key.upper() for key in self.favorite_keys
        }:
            return False
        if self.favorite_key_pattern and not re.search(
            self.favorite_key_pattern, favorite_key, re.IGNORECASE
        ):
            return False
        if self.department_pattern and not re.search(
            self.department_pattern, department_label, re.IGNORECASE
        ):
            return False
        if self.exclude_department_pattern and re.search(
            self.exclude_department_pattern, department_label, re.IGNORECASE
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
        if self.dmr_tiers and channel_tier(channel) not in self.dmr_tiers:
            return False
        if self.within_miles is not None and not self._in_radius(channel, department):
            return False
        if channel.avoid and not self.include_avoided:
            return False
        return True

    def _in_radius(self, channel: Any, department: Any) -> bool:
        lat, lon, miles = self.within_miles
        channel_lat = getattr(channel, "lat", None)
        channel_lon = getattr(channel, "lon", None)
        located = channel_lat is not None and channel_lon is not None
        if located and haversine_miles(lat, lon, channel_lat, channel_lon) <= miles:
            return True
        if self.geo_fallback == GEO_CHANNEL:
            return False
        if located and self.geo_fallback == GEO_DEPARTMENT:
            return False
        return _fence_overlaps(department, lat, lon, miles)


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
    #: Optional channel-label pattern for individual scan lockouts inside an
    #: otherwise scannable block.
    skip_label_pattern: str = ""
    notes: str = ""
    #: Optional radio bank/group name. Blocks remain distinct in reports and
    #: ordering while sharing a physical group when this names another block.
    bank: str = ""

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
class ScanGroup:
    """A named scan list composed from several blocks.

    Radios with explicit scan lists (Anytone, Kenwood group link) get one
    list per block automatically; a scan group is the operator's own
    combination - "everything amateur", "public service" - built from the
    non-``skip_scan`` channels of the named blocks in plan order. A target
    with a per-list member ceiling splits the group into numbered lists.
    """

    name: str
    blocks: Tuple[str, ...]
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("scan group needs a name")
        if not self.blocks:
            raise ValueError(f"scan group {self.name!r} names no blocks")


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
    #: Composite scan lists; ignored by targets whose radio has no scan lists.
    scan_groups: Tuple[ScanGroup, ...] = ()
    #: Amateur licence class. When set, transmitting inside an amateur band
    #: also needs that class's privileges there (see
    #: :mod:`wasds150.radios.bandplan`); empty leaves the check to the blocks.
    license_class: str = ""
    #: The operator's GMRS call sign, carried into reports. Whether a block
    #: transmits on GMRS is still that block's policy.
    gmrs_call: str = ""

    def __post_init__(self) -> None:
        if self.reserve_slots < 0:
            raise ValueError("reserve_slots must not be negative")
        seen = set()
        for block in self.blocks:
            if block.label in seen:
                raise ValueError(f"duplicate block label {block.label!r}")
            seen.add(block.label)
        group_names = set()
        for group in self.scan_groups:
            if group.name in group_names:
                raise ValueError(f"duplicate scan group {group.name!r}")
            group_names.add(group.name)
            missing = [label for label in group.blocks if label not in seen]
            if missing:
                raise ValueError(
                    f"scan group {group.name!r} names unknown blocks: {', '.join(missing)}"
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "radio_id": self.radio_id,
            "label": self.label,
            "description": self.description,
            "reserve_slots": self.reserve_slots,
            "license_class": self.license_class,
            "gmrs_call": self.gmrs_call,
            "scan_groups": [
                {"name": group.name, "blocks": list(group.blocks), "notes": group.notes}
                for group in self.scan_groups
            ],
            "blocks": [
                {
                    "label": block.label,
                    "tx_policy": block.tx_policy,
                    "power": block.power,
                    "sort": block.sort,
                    "limit": block.limit,
                    "skip_scan": block.skip_scan,
                    "skip_label_pattern": block.skip_label_pattern,
                    "notes": block.notes,
                    "bank": block.bank,
                }
                for block in self.blocks
            ],
        }
