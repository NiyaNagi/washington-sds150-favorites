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

import dataclasses
import re

from wasds150 import station
from wasds150.plan.resolve import PlannedChannel, ResolvedPlan
from wasds150.plan.naming import shorten_name
from wasds150.plan.scanning import group_members

AM_AIR_MAX = 256
AM_ZONE_MAX = 16
AM_ZONE_MEMBER_MAX = 32
FM_MAX = 100
RX_GROUP_MEMBER_MAX = 64
SCAN_LIST_MAX = 250
NAME_MAX = 16

#: Where a channel the operator locked out of scanning lives when the rest of
#: its block is scanned: a zone that names no scan list, so pressing Scan on
#: it says "Scan List No Select" rather than sweeping something it is not in.
UNSCANNED_ZONE = "Not Scanned"

#: Stations the fill pass added from beyond the plan's radius are left out of
#: their own block's zones - they would slow the local sweep - but they are
#: still worth a scan of their own. They are zoned by the service they belong
#: to, "Far Public Svc", "Far Ham DMR", each with its identical scan list; a
#: service with fewer than FAR_MIN of them joins "Far Other" instead.
FAR_PREFIX = "Far "
FAR_OTHER = "Other"
FAR_MIN = 10

#: Marks a channel copied into the first scan group's zone. The CPS resolves
#: zone and scan-list members by name, so the copy cannot share its original's.
COPY_SUFFIX = " N"

#: The operator's registered DMR ID and the name the CPS files it under;
#: every channel row references it (see :mod:`wasds150.station`).
RADIO_ID = station.DMR_ID
RADIO_ID_NAME = station.CALLSIGN

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


def _copy_name(name: str, taken: Dict[str, str]) -> str:
    """The original's name with the copy suffix, numbered if that clashes.

    When it has to shrink, the shrinking comes out of everything before the
    last word, which is kept whole: DMR channels end in the repeater's site
    code ("Washington 1 BVC"), and a plain truncation left copies that named
    the talkgroup but not the machine ("Washington 1 N2"). The front is
    shortened the way every channel name is (vowels first, digits never), so
    "Washington 1" and "Washington 2" stay apart.
    """
    head, _, tail = name.rpartition(" ")
    for index in range(1, 100):
        suffix = COPY_SUFFIX if index == 1 else f"{COPY_SUFFIX}{index}"
        room = NAME_MAX - len(suffix) - len(tail) - 1
        if len(name) + len(suffix) <= NAME_MAX:
            candidate = name + suffix
        elif head and room >= 3:
            candidate = f"{shorten_name(head, room, readable=True).rstrip()} {tail}{suffix}"
        else:
            candidate = name[: NAME_MAX - len(suffix)].rstrip() + suffix
        if len(candidate) <= NAME_MAX and candidate.casefold() not in taken:
            return candidate
    raise Atd890ExportError(f"cannot find a free copy name for {name!r}")


def _contact_for(channel: PlannedChannel) -> Optional[Contact]:
    spec = channel.digital
    if spec is None or spec.talkgroup is None:
        return None
    name = spec.talkgroup_name.strip() or f"TG {spec.talkgroup}"
    call_type = {"private": "Private Call", "all": "All Call"}.get(spec.call_type, "Group Call")
    # Truncating can leave a trailing space the CPS keeps but never matches on.
    return Contact(name=name[:NAME_MAX].rstrip() or f"TG {spec.talkgroup}", dmr_id=spec.talkgroup, call_type=call_type)


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
    # Case-insensitively: the CPS resolves a zone or scan-list member by name
    # without case, so two channels differing only in case become one member
    # listed twice and Import All refuses the list.
    seen_names: Dict[str, str] = {}
    for channel in channels:
        clash = seen_names.get(channel.name.casefold())
        if clash is not None:
            raise Atd890ExportError(
                f"channel names {clash!r} and {channel.name!r} differ only in case; "
                "the CPS treats them as one channel"
            )
        seen_names[channel.name.casefold()] = channel.name

    # -- the first scan group, as a zone of its own ----------------------------
    # The radio has no zone scan and no radio-wide scan list: PF1 sweeps the
    # list named on the channel under the cursor. A composite list is only
    # reachable through a zone whose channels name it, and a channel names one
    # list - its own zone's - so the composite's zone holds copies. Only the
    # first group, and only one list's worth: the rest could never be swept
    # whole, and splitting them into arbitrary chunks gave lists no zone led to.
    near_name = ""
    if plan.scan_groups:
        group = plan.scan_groups[0]
        _validate_name(group.name, "scan group")
        wanted = group_members(group, channels)
        cap = profile.scan_list_member_max
        if cap and len(wanted) > cap:
            warnings.append(
                f"scan group {group.name!r} matched {len(wanted)} channels; its zone holds the "
                f"first {cap}, one scan list's worth"
            )
            wanted = wanted[:cap]
        if wanted:
            near_name = group.name
            copies = []
            for original in wanted:
                name = _copy_name(original.name, seen_names)
                seen_names[name.casefold()] = name
                copies.append(dataclasses.replace(original, name=name, bank=near_name))
            channels.extend(copies)
        else:
            warnings.append(f"scan group {group.name!r} matched no scannable channels")

    # -- contacts and receive groups ---------------------------------------
    contacts: "OrderedDict[str, Contact]" = OrderedDict()
    contact_by_channel: Dict[str, str] = {}
    network_contacts: "OrderedDict[str, List[Contact]]" = OrderedDict()
    #: The CPS files contacts by id, so one id can carry only one name. Two
    #: networks naming the same talkgroup differently must collapse to the
    #: first name seen, or Import All fails on DMRTalkGroups.CSV.
    contact_by_id: Dict[int, Contact] = {}
    aliases: Dict[int, set] = {}
    for channel in channels:
        contact = _contact_for(channel)
        if contact is None:
            continue
        canonical = contact_by_id.get(contact.dmr_id)
        if canonical is not None:
            if contact.name != canonical.name:
                aliases.setdefault(contact.dmr_id, set()).add(contact.name)
            contact = canonical
        else:
            existing = contacts.get(contact.name)
            if existing is not None and existing.dmr_id != contact.dmr_id:
                # Two networks naming different ids the same way; keep both.
                contact = Contact(name=f"{contact.name[:NAME_MAX - 7]} {contact.dmr_id}"[:NAME_MAX].rstrip(), dmr_id=contact.dmr_id, call_type=contact.call_type)
            contact_by_id[contact.dmr_id] = contact
        contacts.setdefault(contact.name, contact)
        contact_by_channel[channel.name] = contact.name
        network = channel.digital.network if channel.digital else ""
        bucket = network_contacts.setdefault(network or "Other", [])
        if contact not in bucket:
            bucket.append(contact)
    for dmr_id, names in sorted(aliases.items()):
        kept = contact_by_id[dmr_id].name
        warnings.append(
            f"talkgroup {dmr_id} is named {kept!r} and also "
            + ", ".join(repr(n) for n in sorted(names))
            + f"; the CPS files contacts by id, so every channel uses {kept!r}"
        )
    default = Contact(*DEFAULT_CONTACT)
    existing_default = contact_by_id.get(default.dmr_id)
    if existing_default is not None:
        default = existing_default
    elif default.name not in contacts:
        contacts[default.name] = default
        contact_by_id[default.dmr_id] = default
    for channel in channels:
        contact_by_channel.setdefault(channel.name, default.name)

    # The CPS aborts Import All with ImportFromFileListError when
    # DMRTalkGroups.CSV files one id under two names; fail here instead.
    name_by_id: Dict[int, str] = {}
    for contact in contacts.values():
        _validate_name(contact.name, "contact")
        clash = name_by_id.get(contact.dmr_id)
        if clash is not None:
            raise Atd890ExportError(
                f"two contacts share DMR id {contact.dmr_id}: {clash!r} and {contact.name!r}"
            )
        name_by_id[contact.dmr_id] = contact.name

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

    # -- zones and scan lists ---------------------------------------------------
    # One rule: a zone and its scan list are the same thing. Measured on the
    # radio, PF1 sweeps the scan list named on the channel under the cursor
    # and answers "Scan List No Select" on a channel naming none - there is no
    # zone scan. So every zone that scans has exactly one list of the same
    # name holding exactly its channels, every member names that list, and a
    # zone either scans all of its channels or none of them.
    #
    # A block's scanned channels are zoned at the scan-list ceiling (100)
    # rather than the zone ceiling (160), because a longer zone would need two
    # lists and scan only part of itself. Its unscanned channels - the far
    # fill beyond the radius, label lockouts - leave the block for
    # UNSCANNED_ZONE rather than sit in a scanned zone that skips them. A block
    # that scans nothing at all (weather, packet) keeps its own name, with no
    # list, at the zone ceiling.
    by_bank: "OrderedDict[str, List[PlannedChannel]]" = OrderedDict()
    for channel in channels:
        by_bank.setdefault(channel.bank or channel.block, []).append(channel)
    if near_name:
        # The list worth leaving running is the first zone the knob reaches.
        by_bank.move_to_end(near_name, last=False)
    zones: List[Zone] = []
    scan_lists: List[ScanList] = []
    scan_list_by_channel: Dict[str, str] = {}
    unscanned: List[PlannedChannel] = []
    far: List[PlannedChannel] = []
    limit = profile.scan_list_member_max
    blocks_by_label = {block.label: block for block in plan.blocks}

    def is_far(member: PlannedChannel) -> bool:
        """Unscanned only because the fill pass found it beyond the radius -
        not a block that never scans, and not a lockout the operator chose."""
        block = blocks_by_label.get(member.block)
        if block is None or block.skip_scan:
            return False
        if block.skip_label_pattern and re.search(block.skip_label_pattern, member.label, re.IGNORECASE):
            return False
        return (plan.radius_miles is not None and member.distance_miles is not None
                and member.distance_miles > plan.radius_miles)

    def add_scanned(stem: str, members: List[PlannedChannel], kind: str) -> None:
        chunks = _chunk(members, limit)
        for name, chunk in zip(_numbered(stem, len(chunks)), chunks):
            zones.append(Zone(name=name, members=chunk))
            scan_lists.append(ScanList(name=name, members=chunk, kind=kind))
            for member in chunk:
                scan_list_by_channel[member.name] = name

    for bank, members in by_bank.items():
        _validate_name(bank, "zone")
        scanned = [m for m in members if not m.skip_scan]
        far.extend(m for m in members if m.skip_scan and is_far(m))
        quiet = [m for m in members if m.skip_scan and not is_far(m)]
        if scanned:
            add_scanned(bank, scanned, "group" if bank == near_name else "zone")
            unscanned.extend(quiet)
        elif quiet:
            chunks = _chunk(quiet, profile.zone_member_max)
            for name, chunk in zip(_numbered(bank, len(chunks)), chunks):
                zones.append(Zone(name=name, members=chunk))

    if far:
        # A far station takes the name of the narrowest scan group its block is
        # in - "Ham DMR" before "Ham All" - never the first group (that is the
        # near list) and never the catch-all that holds every block.
        themes = [g for g in plan.scan_groups[1:]]
        catch_all = max(plan.scan_groups, key=lambda g: len(g.blocks)) if plan.scan_groups else None
        narrowest = sorted((g for g in themes if g is not catch_all), key=lambda g: len(g.blocks))
        by_theme: "OrderedDict[str, List[PlannedChannel]]" = OrderedDict(
            (g.name, []) for g in themes if g is not catch_all
        )
        by_theme[FAR_OTHER] = []
        for member in far:
            theme = next((g.name for g in narrowest if member.block in g.blocks), FAR_OTHER)
            by_theme[theme].append(member)
        for theme in list(by_theme):
            if theme != FAR_OTHER and 0 < len(by_theme[theme]) < FAR_MIN:
                by_theme[FAR_OTHER].extend(by_theme.pop(theme))
        for theme, members in by_theme.items():
            if members:
                add_scanned(f"{FAR_PREFIX}{theme}"[:NAME_MAX].rstrip(), members, "far")

    if unscanned:
        chunks = _chunk(unscanned, profile.zone_member_max)
        for name, chunk in zip(_numbered(UNSCANNED_ZONE, len(chunks)), chunks):
            zones.append(Zone(name=name, members=chunk))
    if profile.zone_max is not None and len(zones) > profile.zone_max:
        raise Atd890ExportError(f"{len(zones)} zones exceed the radio's {profile.zone_max}")
    zone_names = [z.name for z in zones]
    if len(set(zone_names)) != len(zone_names):
        raise Atd890ExportError("zone names collide after splitting")
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

    nxdn =[c for c in channels if c.digital is not None and c.digital.protocol == "NXDN"]
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
