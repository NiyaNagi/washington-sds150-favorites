"""Turn a plan's scan groups into channels, once, for every radio.

A :class:`~wasds150.models.plan.ScanGroup` names blocks and optionally how
many of each to take. Resolving that into channels is the same operation
whatever the target is, and the targets then express it however the radio
allows:

* the AT-D890UV has real scan lists, so a group becomes one;
* the TH-D75A scans linked *memory groups*, so a group becomes the link table
  - which reaches whole groups, a superset of the quota-trimmed channels;
* the ID-52A scans one memory group at a time, so a group becomes a memory
  group of its own, holding a second copy of each channel;
* the FTX-1 and TD-H9 have nothing to express it with.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from wasds150.models.plan import ScanGroup
from wasds150.plan.resolve import PlannedChannel


def group_members(group: ScanGroup, channels: Sequence[PlannedChannel]) -> List[PlannedChannel]:
    """The scannable channels of ``group``, in plan order.

    With quotas, each block contributes at most its quota - the first of
    them, which is the nearest, because blocks are ordered nearest-first.
    """
    quotas = group.quotas
    members: List[PlannedChannel] = []
    for block_label in group.blocks:
        block = [c for c in channels if c.block == block_label and not c.skip_scan]
        if quotas:
            block = block[: quotas.get(block_label, 0)]
        members.extend(block)
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
