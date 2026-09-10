"""Derive the Anytone AT-D890UV codeplug structure from a resolved plan.

The CPS wants nine related tables rather than one channel list: channels,
zones, scan lists, talkgroups, radio ids, receive-group lists, and two
separate lists for AM air-band and FM broadcast memories with their own
zones.  This module works out all of that as plain data and enforces the
radio's structural limits; :mod:`wasds150.export.atd890_cps` only formats
what comes out of here.

Routing rules:

* An AM channel between 108 and 137 MHz goes to the AM air list. The CPS has
  no AM channel type in the main table, and the radio can only listen to the
  air band from that list (dual-watch puts it on the B receiver).
* A broadcast channel between 87.5 and 108 MHz goes to the FM list.
* Everything else is an ordinary channel.

Zones come from the plan's block ``bank`` names in plan order. Scan lists
are one per zone (its non-``skip_scan`` members) plus one per
:class:`~wasds150.models.plan.ScanGroup`; any list longer than the radio's
per-list ceiling is split into numbered lists rather than truncated.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from wasds150.plan.resolve import PlannedChannel, ResolvedPlan

AM_AIR_MAX = 256
AM_ZONE_MAX = 16
AM_ZONE_MEMBER_MAX = 32
FM_MAX = 100
RX_GROUP_MEMBER_MAX = 64
SCAN_LIST_MAX = 250
NAME_MAX = 16

#: WA7DAM has no registered DMR ID yet; the CPS needs one on every channel,
#: so the bundle ships this placeholder and shouts about it.
RADIO_ID_PLACEHOLDER = 1
RADIO_ID_NAME = "WA7DAM"

#: Every channel row references a contact, analog rows included, so a
#: contact must exist even when the plan holds no DMR channel.
DEFAULT_CONTACT = ("Simplex 99", 99)

_FORBIDDEN_NAME_CHARS = ('|', ',', '"')


class Atd890ExportError(ValueError):
    """The plan cannot be expressed as an AT-D890UV codeplug."""


@dataclass(frozen=True)
class Contact:
    name: str
    dmr_id: int
    call_type: str = "Group Call"


@dataclass
class RxGroup:
    name: str
    contacts: List[Contact]


@dataclass
class Zone:
    name: str
    members: List[PlannedChannel]

    @property
    def a_channel(self) -> PlannedChannel:
        return self.members[0]

    @property
    def b_channel(self) -> PlannedChannel:
        return self.members[1] if len(self.members) > 1 else self.members[0]


@dataclass
class ScanList:
    name: str
    members: List[PlannedChannel]
    kind: str  # "zone" | "group"


@dataclass
class AmAirChannel:
    index: int
    freq_mhz: float
    name: str
    skip_scan: bool
    bank: str


@dataclass
class AmZone:
    name: str
    members: List[AmAirChannel]

    @property
    def scan_members(self) -> List[AmAirChannel]:
        return [m for m in self.members if not m.skip_scan]


@dataclass
class FmChannel:
    index: int
    freq_mhz: float
    name: str
    scan: bool


@dataclass
class Atd890Bundle:
    channels: List[PlannedChannel]
    contacts: List[Contact]
    rx_groups: List[RxGroup]
    zones: List[Zone]
    scan_lists: List[ScanList]
    am_air: List[AmAirChannel]
    am_zones: List[AmZone]
    fm: List[FmChannel]
    #: channel name -> scan list name written in Channel.CSV
    scan_list_by_channel: Dict[str, str]
    #: channel name -> receive group list name
    rx_group_by_channel: Dict[str, str]
    #: channel name -> contact name
    contact_by_channel: Dict[str, str]
    warnings: List[str] = field(default_factory=list)

    @property
    def rows(self) -> int:
        return len(self.channels) + len(self.am_air) + len(self.fm)


def route(channel: PlannedChannel) -> str:
    rx = channel.rx_freq_mhz
    if channel.mode == "AM" and 108.0 <= rx < 137.0:
        return "am-air"
    if 87.5 <= rx < 108.0 and channel.mode in ("WFM", "FMB", "FM", "AM"):
        return "fm"
    return "channel"


def _validate_name(name: str, what: str) -> None:
    if not name.strip():
        raise Atd890ExportError(f"{what} has an empty name")
    if len(name) > NAME_MAX:
        raise Atd890ExportError(f"{what} name {name!r} is longer than {NAME_MAX} characters")
    for ch in _FORBIDDEN_NAME_CHARS:
        if ch in name:
            raise Atd890ExportError(f"{what} name {name!r} contains {ch!r}, which the CPS uses as a separator")


def _chunk(items: List, size: Optional[int]) -> List[List]:
    if not size or len(items) <= size:
        return [items] if items else []
    return [items[i:i + size] for i in range(0, len(items), size)]


def _numbered(stem: str, count: int) -> List[str]:
    """``Ham All`` -> ``Ham All 01``, ``Ham All 02`` when split, else the stem."""
    if count <= 1:
        return [stem]
    width = 2 if count < 100 else 3
    names = []
    for index in range(1, count + 1):
        suffix = f" {index:0{width}d}"
        names.append(stem[: NAME_MAX - len(suffix)].rstrip() + suffix)
    return names


def _contact_for(channel: PlannedChannel) -> Optional[Contact]:
    spec = channel.digital
    if spec is None or spec.talkgroup is None:
        return None
    name = spec.talkgroup_name.strip() or f"TG {spec.talkgroup}"
    call_type = {"private": "Private Call", "all": "All Call"}.get(spec.call_type, "Group Call")
    return Contact(name=name[:NAME_MAX], dmr_id=spec.talkgroup, call_type=call_type)


def build_bundle(resolved: ResolvedPlan) -> Atd890Bundle:
    profile = resolved.profile
    plan = resolved.plan
    warnings: List[str] = []

    channels: List[PlannedChannel] = []
    am_air: List[AmAirChannel] = []
    fm: List[FmChannel] = []
    for channel in resolved.channels:
        where = route(channel)
        if where == "am-air":
            if len(am_air) >= AM_AIR_MAX:
                warnings.append(f"{channel.label}: AM air list is full ({AM_AIR_MAX}); not programmed")
                continue
            am_air.append(AmAirChannel(len(am_air) + 1, channel.rx_freq_mhz, channel.name, channel.skip_scan, channel.bank))
        elif where == "fm":
            if len(fm) >= FM_MAX:
                warnings.append(f"{channel.label}: FM broadcast list is full ({FM_MAX}); not programmed")
                continue
            fm.append(FmChannel(len(fm) + 1, channel.rx_freq_mhz, channel.name, not channel.skip_scan))
        else:
            channels.append(channel)

    for channel in channels:
        _validate_name(channel.name, "channel")
    seen_names = set()
    for channel in channels:
        if channel.name in seen_names:
            raise Atd890ExportError(f"duplicate channel name {channel.name!r}")
        seen_names.add(channel.name)

    # -- contacts and receive groups ---------------------------------------
    contacts: "OrderedDict[str, Contact]" = OrderedDict()
    contact_by_channel: Dict[str, str] = {}
    network_contacts: "OrderedDict[str, List[Contact]]" = OrderedDict()
    for channel in channels:
        contact = _contact_for(channel)
        if contact is None:
            continue
        existing = contacts.get(contact.name)
        if existing is not None and existing.dmr_id != contact.dmr_id:
            # Two networks naming different ids the same way; keep both.
            contact = Contact(name=f"{contact.name[:NAME_MAX - 7]} {contact.dmr_id}"[:NAME_MAX], dmr_id=contact.dmr_id, call_type=contact.call_type)
        contacts.setdefault(contact.name, contact)
        contact_by_channel[channel.name] = contact.name
        network = channel.digital.network if channel.digital else ""
        bucket = network_contacts.setdefault(network or "Other", [])
        if contact not in bucket:
            bucket.append(contact)
    default = Contact(*DEFAULT_CONTACT)
    if default.name not in contacts:
        contacts[default.name] = default
    for channel in channels:
        contact_by_channel.setdefault(channel.name, default.name)

    rx_groups: List[RxGroup] = []
    rx_group_by_channel: Dict[str, str] = {}
    group_name_by_network: Dict[str, str] = {}
    for network, members in network_contacts.items():
        stem = f"{network[:NAME_MAX - 3]} RX"
        chunks = _chunk(members, RX_GROUP_MEMBER_MAX)
        for name, chunk in zip(_numbered(stem, len(chunks)), chunks):
            rx_groups.append(RxGroup(name=name, contacts=chunk))
        group_name_by_network[network] = rx_groups[-len(chunks)].name if chunks else ""
    for channel in channels:
        if channel.digital is not None and channel.digital.talkgroup is not None:
            rx_group_by_channel[channel.name] = group_name_by_network.get(channel.digital.network or "Other", "")

    # -- zones ---------------------------------------------------------------
    by_bank: "OrderedDict[str, List[PlannedChannel]]" = OrderedDict()
    for channel in channels:
        by_bank.setdefault(channel.bank or channel.block, []).append(channel)
    zones: List[Zone] = []
    # A zone is split at the scan-list ceiling rather than the zone ceiling
    # so that every zone's scan list is exactly the zone: the operator sees
    # one name in both menus and no list ever needs a second split.
    zone_limit = min(x for x in (profile.zone_member_max, profile.scan_list_member_max) if x) if (
        profile.zone_member_max or profile.scan_list_member_max
    ) else None
    for bank, members in by_bank.items():
        _validate_name(bank, "zone")
        chunks = _chunk(members, zone_limit)
        for name, chunk in zip(_numbered(bank, len(chunks)), chunks):
            zones.append(Zone(name=name, members=chunk))
    if profile.zone_max is not None and len(zones) > profile.zone_max:
        raise Atd890ExportError(f"{len(zones)} zones exceed the radio's {profile.zone_max}")
    zone_names = [z.name for z in zones]
    if len(set(zone_names)) != len(zone_names):
        raise Atd890ExportError("zone names collide after splitting")

    # -- scan lists ------------------------------------------------------------
    scan_lists: List[ScanList] = []
    scan_list_by_channel: Dict[str, str] = {}
    limit = profile.scan_list_member_max
    for zone in zones:
        members = [m for m in zone.members if not m.skip_scan]
        chunks = _chunk(members, limit)
        names = _numbered(zone.name, len(chunks))
        for name, chunk in zip(names, chunks):
            scan_lists.append(ScanList(name=name, members=chunk, kind="zone"))
        for member in members:
            scan_list_by_channel.setdefault(member.name, names[0] if names else "")
    for group in plan.scan_groups:
        members: List[PlannedChannel] = []
        for block_label in group.blocks:
            members.extend(c for c in channels if c.block == block_label and not c.skip_scan)
        if not members:
            warnings.append(f"scan group {group.name!r} matched no scannable channels")
            continue
        _validate_name(group.name, "scan group")
        chunks = _chunk(members, limit)
        for name, chunk in zip(_numbered(group.name, len(chunks)), chunks):
            scan_lists.append(ScanList(name=name, members=chunk, kind="group"))
    list_names = [s.name for s in scan_lists]
    if len(set(list_names)) != len(list_names):
        dupes = sorted({n for n in list_names if list_names.count(n) > 1})
        raise Atd890ExportError(f"scan list names collide: {', '.join(dupes)}")
    if len(scan_lists) > SCAN_LIST_MAX:
        raise Atd890ExportError(f"{len(scan_lists)} scan lists exceed the radio's {SCAN_LIST_MAX}")

    # -- AM air zones ----------------------------------------------------------
    am_by_bank: "OrderedDict[str, List[AmAirChannel]]" = OrderedDict()
    for entry in am_air:
        am_by_bank.setdefault(entry.bank, []).append(entry)
    am_zones: List[AmZone] = []
    for bank, members in am_by_bank.items():
        _validate_name(bank, "AM zone")
        chunks = _chunk(members, AM_ZONE_MEMBER_MAX)
        for name, chunk in zip(_numbered(bank, len(chunks)), chunks):
            am_zones.append(AmZone(name=name, members=chunk))
    am_zone_names = [z.name for z in am_zones]
    if len(set(am_zone_names)) != len(am_zone_names):
        raise Atd890ExportError("AM zone names collide after splitting")
    if len(am_zones) > AM_ZONE_MAX:
        raise Atd890ExportError(f"{len(am_zones)} AM zones exceed the radio's {AM_ZONE_MAX}")

    warnings.append(
        f"RadioIDList.CSV carries placeholder DMR ID {RADIO_ID_PLACEHOLDER} for {RADIO_ID_NAME}; "
        "register at https://radioid.net and replace it in the CPS before transmitting on DMR"
    )
    nxdn = [c for c in channels if c.digital is not None and c.digital.protocol == "NXDN"]
    if nxdn:
        warnings.append(
            f"{len(nxdn)} NXDN channels written with the RAN in the EnRan/DeRan columns; that column "
            "mapping is unverified against a CPS export and the rows are silent until the radio is "
            "switched to the NXDN protocol"
        )

    return Atd890Bundle(
        channels=channels,
        contacts=list(contacts.values()),
        rx_groups=rx_groups,
        zones=zones,
        scan_lists=scan_lists,
        am_air=am_air,
        am_zones=am_zones,
        fm=fm,
        scan_list_by_channel=scan_list_by_channel,
        rx_group_by_channel=rx_group_by_channel,
        contact_by_channel=contact_by_channel,
        warnings=warnings,
    )
