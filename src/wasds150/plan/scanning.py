"""Turn a plan's scan groups into channels, once, for every radio.

A :class:`~wasds150.models.plan.ScanGroup` names blocks and optionally how
many of each to take. Resolving that into channels is the same operation
whatever the target is, and the targets then express it however the radio
allows:

* the AT-D890UV has real scan lists, so a group becomes one;
* the TH-D75A and ID-52A scan one memory group at a time, so a group becomes
  a memory group of its own, holding a second copy of each channel;
* the FTX-1 flags the group's memories with M-Grp;
* the TD-H9 has nothing to express it with.

A quota picks, within each block, the pinned stations first (the ones the
operator always wants), then the stations within the group's reach, nearest
first - a DMR talkgroup by its tier before its distance - then stations whose
distance is unknown (a simplex frequency has no site). A station known to be
beyond reach is never picked unless it is pinned. The chosen channels are
listed in frequency order when the group asks for it.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from wasds150.models.plan import ScanGroup
from wasds150.plan.resolve import PlannedChannel

_WITHIN, _UNKNOWN, _BEYOND = 0, 1, 2


def is_pinned(channel: PlannedChannel, pinned: Sequence[Tuple[float, str]]) -> bool:
    """A repeater memory on a pinned output whose name carries the pinned call."""
    if channel.tx_freq_mhz is None:
        return False
    label = (channel.label or "").upper()
    return any(abs(channel.rx_freq_mhz - freq) < 0.0006 and call.upper() in label for freq, call in pinned)


def _reach(channel: PlannedChannel, group: ScanGroup) -> int:
    if channel.distance_miles is None:
        return _UNKNOWN
    if group.reach_miles is None or channel.distance_miles <= group.reach_miles:
        return _WITHIN
    return _BEYOND


def quota_rank(channel: PlannedChannel, group: ScanGroup) -> tuple:
    """How a quota chooses among a block's channels: lowest first."""
    distance = channel.distance_miles if channel.distance_miles is not None else math.inf
    return (
        0 if is_pinned(channel, group.pinned) else 1,
        _reach(channel, group),
        # A machine whose coordination has lapsed is probably off the air.
        1 if channel.lapsed else 0,
        channel.tier,
        distance,
        channel.rank,
        channel.rx_freq_mhz,
    )


def group_members(group: ScanGroup, channels: Sequence[PlannedChannel]) -> List[PlannedChannel]:
    """The scannable channels of ``group``.

    With quotas, each block contributes at most its quota, chosen by
    :func:`quota_rank`; without, every scannable channel of each block.
    """
    quotas = group.quotas
    members: List[PlannedChannel] = []
    for block_label in group.blocks:
        block = [c for c in channels if c.block == block_label and not c.skip_scan]
        if quotas:
            ranked = sorted(block, key=lambda c: quota_rank(c, group))
            ranked = [c for c in ranked if _reach(c, group) != _BEYOND or is_pinned(c, group.pinned)]
            block = ranked[: quotas.get(block_label, 0)]
        members.extend(block)
    if group.frequency_order:
        members.sort(key=lambda c: (c.rx_freq_mhz, c.name))
    return members


def group_banks(
    group: ScanGroup,
    channels: Sequence[PlannedChannel],
    bank_of: Dict[str, int],
) -> List[int]:
    """The distinct memory groups ``group``'s channels landed in, in order.

    For a radio that scans whole memory groups rather than a channel list.
    ``bank_of`` maps a channel's bank name to the radio's group number.
    """
    banks: List[int] = []
    for channel in group_members(group, channels):
        number = bank_of.get(channel.bank or channel.block)
        if number is not None and number not in banks:
            banks.append(number)
    return sorted(banks)
