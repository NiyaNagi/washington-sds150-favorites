"""Turn a :class:`~wasds150.models.plan.ChannelPlan` into concrete memories.

Resolution is deliberately lossy in one direction only: a channel the target
radio cannot use is *dropped with a stated reason*, never silently coerced
into something the radio will accept.  A scanner catalog contains 800 MHz
trunked talkgroups and P25 systems; a TD-H9 can do nothing with either, and
quietly rewriting them as analog FM would produce a radio full of dead
channels that look programmed.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from typing import Dict, Iterator, List, Optional, Tuple

from wasds150.catalog.dmr_talkgroup_tiers import channel_tier
from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import (
    TX_AUTO,
    TX_NONE,
    TX_REPEATER,
    TX_SIMPLEX,
    ChannelPlan,
    PlanBlock,
    SORT_FREQ,
    SORT_LABEL,
    SORT_NATURAL,
    SORT_NEAREST,
    SORT_TIER_DISTANCE,
    natural_key,
)
from wasds150.radios.bandplan import band_for, may_transmit
from wasds150.util.geo import haversine_miles
from wasds150.plan.naming import NameAllocator
from wasds150.radios.digital import DIGITAL_MODES, DigitalSpec, digital_identity, digital_spec
from wasds150.radios.profile import RadioProfile
from wasds150.radios.registry import get_profile
from wasds150.radios.tones import NO_TONE, ToneSpec, parse_tone

#: Bands where a plain analog radio should use AM rather than FM, because the
#: services there are amplitude modulated.  Used only when the catalog does
#: not state a mode the target radio understands.
_AM_BANDS = ((108.0, 137.0), (225.0, 400.0))

#: Bands that conventionally run wide FM (5 kHz deviation).  Everything else
#: in the land-mobile spectrum has migrated to narrowband.
_WIDE_FM_BANDS = (
    (28.0, 29.7),
    (50.0, 54.0),
    (144.0, 148.0),
    (156.0, 163.0),
    (222.0, 225.0),
    (420.0, 450.0),
    (462.0, 467.8),
)


@dataclass
class PlannedChannel:
    """One programmed memory slot."""

    slot: int
    name: str
    label: str
    rx_freq_mhz: float
    mode: str
    block: str
    source: str
    bank: str = ""
    transmit: bool = False
    tx_freq_mhz: Optional[float] = None
    rx_tone: ToneSpec = NO_TONE
    tx_tone: ToneSpec = NO_TONE
    power: str = "5.0W"
    skip_scan: bool = False
    comment: str = ""
    dv_urcall: str = ""
    dv_rpt1: str = ""
    dv_rpt2: str = ""
    #: DMR/NXDN identity for digital-capable targets; ``None`` for analog.
    digital: Optional[DigitalSpec] = None
    #: The repeater input the source publishes, kept even on receive-only
    #: memories (``tx_freq_mhz`` is only set when transmit is allowed). A DMR
    #: radio still wants it so a monitored repeater is programmed in repeater
    #: mode rather than as a simplex frequency.
    input_freq_mhz: Optional[float] = None
    #: Miles from the plan's home to the channel (its own site, else its
    #: department's fence centre); ``None`` when neither is known.
    distance_miles: Optional[float] = None
    #: The station's own position, when the catalog publishes one. Exporters
    #: that write a located table (the ID-52A's DR repeater list) need it.
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass
class DroppedChannel:
    label: str
    freq_mhz: Optional[float]
    block: str
    reason: str
    detail: str = ""

    def __str__(self) -> str:
        freq = f"{self.freq_mhz:g} MHz" if self.freq_mhz is not None else "no frequency"
        suffix = f" ({self.detail})" if self.detail else ""
        return f"{self.reason}: {self.label} [{freq}]{suffix}"


@dataclass
class ResolvedPlan:
    plan: ChannelPlan
    profile: RadioProfile
    channels: List[PlannedChannel] = field(default_factory=list)
    dropped: List[DroppedChannel] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    block_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def slots_used(self) -> int:
        return len(self.channels)

    @property
    def capacity(self) -> Optional[int]:
        if self.profile.max_channels is None:
            return None
        return self.profile.max_channels - self.plan.reserve_slots

    def drop_reasons(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in self.dropped:
            counts[item.reason] = counts.get(item.reason, 0) + 1
        return counts


def _iter_departments(system: System) -> Iterator[Department]:
    for department in system.departments:
        yield department
    for site in system.sites:
        for department in site.departments:
            yield department


def iter_catalog_channels(
    catalog: Catalog,
) -> Iterator[Tuple[FavoritesList, System, Department, Channel]]:
    """Walk every structured channel in the catalog in a stable order."""
    for favorite in catalog.favorites:
        for system in favorite.systems:
            for department in _iter_departments(system):
                for channel in department.channels:
                    yield favorite, system, department, channel


def _in_any(freq_mhz: float, bands: Tuple[Tuple[float, float], ...]) -> bool:
    return any(low <= freq_mhz <= high for low, high in bands)


def resolve_mode(channel: Channel, profile: RadioProfile) -> Optional[str]:
    """Choose a modulation the target radio understands.

    Returns ``None`` when the catalog states a mode the radio cannot
    demodulate, which is the signal to drop the channel rather than guess.
    """
    stated = (channel.mode or "").strip().upper()

    # A mode the radio supports outright is always honoured.
    if stated and profile.supports_mode(stated):
        return stated

    # "AUTO"/"ALL" are scanner instructions meaning "work it out", and an
    # absent mode says nothing at all; both are safe to infer from the band.
    if stated and stated not in {"AUTO", "ALL", ""}:
        return None

    freq = channel.freq_mhz
    if freq is None:
        return None

    if _in_any(freq, _AM_BANDS) and profile.supports_mode("AM"):
        return "AM"
    if _in_any(freq, _WIDE_FM_BANDS) and profile.supports_mode("FM"):
        return "FM"
    if profile.supports_mode("NFM"):
        return "NFM"
    if profile.supports_mode("FM"):
        return "FM"
    return None


#: Uniden service types in the order an operator most wants to hear them:
#: dispatch, then interop and emergency operations, tactical, hospitals,
#: talk-around; everything else after.
_SERVICE_RANK = {1: 0, 2: 0, 3: 0, 4: 0, 11: 1, 29: 1, 6: 2, 7: 2, 8: 2, 9: 2, 12: 3, 22: 4, 23: 4, 24: 4, 25: 4}
_OTHER_SERVICE = 5

Selected = Tuple[FavoritesList, Department, Channel, Optional[float]]


def service_rank(service_type: Optional[int]) -> int:
    return _SERVICE_RANK.get(service_type, _OTHER_SERVICE) if service_type is not None else _OTHER_SERVICE


def channel_position(department: Optional[Department], channel: Channel) -> Optional[Tuple[float, float]]:
    """The channel's own site, else its department's geo-fence centre."""
    if channel.lat is not None and channel.lon is not None:
        return channel.lat, channel.lon
    if department is not None and department.lat is not None and department.lon is not None:
        return department.lat, department.lon
    return None


def _select_for_block(
    block: PlanBlock,
    candidates: List[Tuple[FavoritesList, System, Department, Channel]],
    home: Optional[Tuple[float, float]] = None,
    radius: Optional[float] = None,
) -> List[Selected]:
    """The block's channels in its sort order, each with its distance from
    home (``None`` when unknown)."""
    picked = []
    for favorite, _system, department, channel in candidates:
        for rank, selector in enumerate(block.selectors):
            if selector.matches(favorite.favorite_key, department.label, channel, department):
                picked.append((favorite, department, channel, rank, selector.anywhere))
                break

    centre = home or next(
        ((s.within_miles[0], s.within_miles[1]) for s in block.selectors if s.within_miles is not None), None
    )

    def _distance(department: Department, channel: Channel, anywhere: bool) -> Optional[float]:
        if centre is None:
            return None
        where = channel_position(department, channel)
        if where is not None:
            return haversine_miles(centre[0], centre[1], where[0], where[1])
        # Unlocated: here if the list is relevant anywhere, else farthest.
        return 0.0 if anywhere else math.inf

    rows = [(f, d, c, rank, _distance(d, c, anywhere)) for f, d, c, rank, anywhere in picked]
    if block.sort == SORT_FREQ:
        rows.sort(key=lambda row: (row[2].freq_mhz or 0.0, row[2].label))
    elif block.sort == SORT_LABEL:
        rows.sort(key=lambda row: (row[2].label.upper(), row[2].freq_mhz or 0.0))
    elif block.sort == SORT_NATURAL:
        rows.sort(key=lambda row: (natural_key(row[2].label), row[2].freq_mhz or 0.0))
    elif block.sort in (SORT_TIER_DISTANCE, SORT_NEAREST):

        def _nearest(row: tuple) -> tuple:
            _favorite, _department, channel, rank, distance = row
            if distance is None:
                miles, bucket = 0.0, 0
            elif math.isinf(distance):
                # Unlocated rows of a regional list: probably near, but not
                # known to be - after the stations known to be inside the
                # radius, before those known to be outside it.
                miles, bucket = distance, 1
            else:
                miles = distance
                bucket = 2 if radius is not None and miles > radius else 0
            return (
                bucket,
                channel_tier(channel),
                miles,
                rank,
                service_rank(channel.service_type),
                channel.freq_mhz or 0.0,
                channel.label,
            )

        rows.sort(key=_nearest)
    return [
        (f, d, c, distance if distance is not None and math.isfinite(distance) else None)
        for f, d, c, _rank, distance in rows
    ]


def _resolve_tones(
    channel: Channel, transmit: bool, mode: str = ""
) -> Tuple[ToneSpec, ToneSpec, List[str]]:
    """Decide receive and transmit tones.

    Receive squelch is left open on monitoring channels on purpose: a CTCSS
    receive tone makes the radio ignore every transmission that does not carry
    it, which is the opposite of what you want when the reason the channel is
    programmed at all is to hear what is happening.

    Digital modes carry their access identity (colour code, RAN, NAC) in
    :class:`~wasds150.radios.digital.DigitalSpec` instead, so no analog tone
    is programmed and no warning is raised about the tone string.
    """
    notes: List[str] = []
    if (mode or "").upper() in DIGITAL_MODES:
        return NO_TONE, NO_TONE, notes
    output_tone = parse_tone(channel.tone)
    input_tone = parse_tone(channel.tx_tone) if channel.tx_tone else output_tone

    if not transmit:
        return NO_TONE, NO_TONE, notes

    if input_tone.is_analog_squelch:
        return NO_TONE, input_tone, notes

    if input_tone.kind not in ("none",):
        notes.append(
            f"{channel.label}: tone {input_tone.raw!r} is not analog squelch and was not programmed"
        )
    return NO_TONE, NO_TONE, notes


def _resolve_once(
    plan: ChannelPlan,
    profile: RadioProfile,
    candidates: List[Tuple[FavoritesList, System, Department, Channel]],
    *,
    enforce_capacity: bool = True,
    cache: Optional[Dict[tuple, List[Selected]]] = None,
    labels: Optional[object] = None,
) -> ResolvedPlan:
    """One pass over the blocks. ``enforce_capacity=False`` lets every block
    take up to its limit regardless of the radio's size, which is how the
    fill pass sees what each block would take next."""
    result = ResolvedPlan(plan=plan, profile=profile)

    if not profile.verified:
        result.warnings.append(
            f"radio profile {profile.id!r} is unverified; check its capabilities "
            "against the manual before programming a radio from this plan"
        )

    allocator = NameAllocator(
        profile.name_max_len or 64,
        charset=profile.name_charset,
        readable=(profile.name_style == "readable"),
    )
    capacity = result.capacity if enforce_capacity else None
    radius = plan.radius_miles
    seen_frequencies: Dict[Tuple, PlannedChannel] = {}
    #: Digital memories that carry a contact identity, keyed by
    #: ``(frequency, mode)``. A bare digital row (colour code only, as the
    #: coordinator publishes it) adds nothing once a talkgroup channel for the
    #: same repeater is programmed, so it is dropped as covered.
    seen_digital_identity: Dict[Tuple[float, str], PlannedChannel] = {}
    #: Every signal some memory already receives, keyed without transmit
    #: settings. A receive-only memory for a signal already in the radio adds
    #: nothing - the usual case is a catch-all block meeting a channel an
    #: earlier block programmed with transmit.
    seen_receive: Dict[Tuple, PlannedChannel] = {}
    slot = 0

    #: With a fill pass, every group's stations inside the radius are placed
    #: before any group's stations beyond it, so a nearer copy of a frequency
    #: always wins over a far one some earlier group would have reached first.
    two_pass = plan.fill_to_capacity and radius is not None
    phases = [(block, "near" if two_pass and block.fill else "all") for block in plan.blocks]
    if two_pass:
        phases += [(block, "far") for block in plan.blocks if block.fill]
    taken_by_block: Dict[str, int] = {}
    for block, phase in phases:
        taken = taken_by_block.get(block.label, 0)
        #: Channels held back by licence class, reported once per block: a
        #: warning per channel would bury the ones that need attention.
        licence_blocked = 0
        # The selection depends on the selectors and sort alone, so the fill
        # rounds, which only move limits, reuse it.
        key = (block.selectors, block.sort, plan.home, radius)
        selected = cache.get(key) if cache is not None else None
        if selected is None:
            selected = _select_for_block(block, candidates, home=plan.home, radius=radius)
            if cache is not None:
                cache[key] = selected
        for favorite, department, channel, distance in selected:
            beyond = distance is not None and radius is not None and distance > radius
            if (phase == "near" and beyond) or (phase == "far" and not beyond):
                continue
            if block.limit is not None and taken >= block.limit:
                result.dropped.append(
                    DroppedChannel(
                        channel.label, channel.freq_mhz, block.label,
                        "block-limit", f"block capped at {block.limit}",
                    )
                )
                continue

            if channel.tgid is not None or channel.freq_mhz is None:
                result.dropped.append(
                    DroppedChannel(
                        channel.label, channel.freq_mhz, block.label,
                        "not-conventional",
                        "talkgroup or trunked entry has no tunable frequency",
                    )
                )
                continue

            freq = round(float(channel.freq_mhz), 6)

            if not profile.can_receive(freq):
                result.dropped.append(
                    DroppedChannel(
                        channel.label, freq, block.label, "no-rx-coverage",
                        f"outside {profile.model} receive coverage",
                    )
                )
                continue

            mode = resolve_mode(channel, profile)
            if mode is None:
                result.dropped.append(
                    DroppedChannel(
                        channel.label, freq, block.label, "unsupported-mode",
                        f"{profile.model} cannot demodulate {channel.mode!r}",
                    )
                )
                continue

            transmit = block.tx_policy != TX_NONE
            tx_freq: Optional[float] = None

            if transmit and mode == "AM":
                transmit = False
                result.warnings.append(
                    f"{channel.label}: AM channels are receive-only; transmit disabled"
                )
            if transmit and block.tx_policy == TX_AUTO and channel.tx_freq_mhz is not None:
                tx_freq = round(float(channel.tx_freq_mhz), 6)
            if transmit and block.tx_policy == TX_REPEATER:
                if channel.tx_freq_mhz is None:
                    transmit = False
                    result.warnings.append(
                        f"{channel.label}: no published repeater input, programmed receive-only"
                    )
                else:
                    tx_freq = round(float(channel.tx_freq_mhz), 6)
            if transmit and not profile.can_transmit(tx_freq if tx_freq is not None else freq):
                transmit = False
                tx_freq = None
                result.warnings.append(
                    f"{channel.label}: outside {profile.model} transmit coverage, "
                    "programmed receive-only"
                )
            if transmit and plan.license_class:
                tx_at = tx_freq if tx_freq is not None else freq
                if band_for(tx_at) is not None and not may_transmit(tx_at, plan.license_class):
                    transmit = False
                    tx_freq = None
                    licence_blocked += 1

            spec = digital_spec(channel, mode)
            if transmit and mode == "DMR" and (spec is None or not spec.has_contact):
                transmit = False
                tx_freq = None
                result.warnings.append(
                    f"{channel.label}: DMR channel has no talkgroup; programmed receive-only"
                )
            if transmit and mode == "NXDN":
                transmit = False
                tx_freq = None
                result.warnings.append(
                    f"{channel.label}: NXDN channels are receive-only in this project"
                )

            rx_tone, tx_tone, tone_notes = _resolve_tones(channel, transmit, mode)
            result.warnings.extend(tone_notes)

            # Two memories are the same only if they tune identically. A GMRS
            # repeater channel shares its output frequency with the simplex
            # channel of the same number but transmits five megahertz up, and
            # two repeaters can share a pair while answering to different
            # access tones, so the receive frequency alone is not an identity.
            # Two talkgroups on one DMR repeater are likewise two memories.
            identity = digital_identity(spec)
            tuning_key = (
                freq,
                tx_freq if transmit else None,
                transmit,
                tx_tone.raw if transmit else "",
                mode if spec is not None else "",
                identity,
            )
            existing = seen_frequencies.get(tuning_key)
            if existing is not None:
                result.dropped.append(
                    DroppedChannel(
                        channel.label, freq, block.label, "duplicate",
                        f"already programmed in slot {existing.slot} as {existing.label!r}",
                    )
                )
                continue
            receive_key = (freq, mode if spec is not None else "", identity)
            receiving = seen_receive.get(receive_key)
            if plan.skip_receive_duplicates and not transmit and receiving is not None:
                result.dropped.append(
                    DroppedChannel(
                        channel.label, freq, block.label, "duplicate",
                        f"already received in slot {receiving.slot} as {receiving.label!r}",
                    )
                )
                continue
            if spec is not None and not spec.has_contact:
                covering = seen_digital_identity.get((freq, mode))
                if covering is not None:
                    result.dropped.append(
                        DroppedChannel(
                            channel.label, freq, block.label, "duplicate",
                            f"covered by talkgroup channel in slot {covering.slot} "
                            f"as {covering.label!r}",
                        )
                    )
                    continue

            if capacity is not None and slot >= capacity:
                result.dropped.append(
                    DroppedChannel(
                        channel.label, freq, block.label, "capacity",
                        f"{profile.model} holds {capacity} channels for this plan",
                    )
                )
                continue

            slot += 1
            taken += 1
            label = labels.label(department, channel) if labels is not None else channel.label
            planned = PlannedChannel(
                slot=slot,
                # Keyed per block: one channel programmed in two blocks (receive
                # only, then with transmit) is two memories and needs two names.
                name=allocator.allocate(label, key=f"{block.label}\x00{channel.id}"),
                label=label,
                rx_freq_mhz=freq,
                mode=mode,
                block=block.label,
                source=f"{favorite.favorite_key}/{department.label}",
                bank=block.bank or block.label,
                transmit=transmit,
                tx_freq_mhz=tx_freq,
                rx_tone=rx_tone,
                tx_tone=tx_tone,
                power=block.power,
                skip_scan=(
                    block.skip_scan
                    or bool(
                        block.skip_label_pattern
                        and re.search(block.skip_label_pattern, channel.label, re.IGNORECASE)
                    )
                    # A station the fill pass added from beyond the radius is
                    # there to browse, not to slow every scan.
                    or bool(plan.fill_to_capacity and radius is not None and distance is not None and distance > radius)
                ),
                comment=channel.notes or "",
                dv_urcall=getattr(channel, "dv_urcall", ""),
                dv_rpt1=getattr(channel, "dv_rpt1", ""),
                dv_rpt2=getattr(channel, "dv_rpt2", ""),
                digital=spec,
                input_freq_mhz=(
                    round(float(channel.tx_freq_mhz), 6) if channel.tx_freq_mhz is not None else None
                ),
                distance_miles=round(distance, 1) if distance is not None else None,
                lat=channel.lat,
                lon=channel.lon,
            )
            result.channels.append(planned)
            seen_frequencies[tuning_key] = planned
            seen_receive.setdefault(receive_key, planned)
            if spec is not None and spec.has_contact:
                seen_digital_identity.setdefault((freq, mode), planned)

        taken_by_block[block.label] = taken
        result.block_counts[block.label] = taken
        if licence_blocked:
            result.warnings.append(
                f"{block.label}: {licence_blocked} channel(s) outside "
                f"{plan.license_class}-class privileges, programmed receive-only"
            )

    if capacity is not None:
        remaining = capacity - slot
        if remaining < 0:
            raise AssertionError("resolver exceeded the radio's capacity")
        if remaining == 0:
            result.warnings.append(
                "plan filled every available slot; nothing was left for field additions"
            )

    return result


#: How far a fill pass may reach: all of Washington from anywhere in it.
FILL_RADIUS_MILES = 500.0
#: Dedupe between blocks can leave a slot or two after a round; a few more
#: rounds pick those up.
_FILL_ROUNDS = 3


def resolve_plan(
    plan: ChannelPlan,
    catalog: Catalog,
    profile: Optional[RadioProfile] = None,
) -> ResolvedPlan:
    """Resolve ``plan`` against ``catalog`` for its target radio.

    With ``plan.fill_to_capacity``, slots the budgeted blocks leave empty go
    to the next-nearest stations any ``fill`` block would take, wherever in
    the state they are, until the radio (less its reserve) is full.
    """
    profile = profile or get_profile(plan.radio_id)
    candidates = list(iter_catalog_channels(catalog))
    cache: Dict[tuple, List[Selected]] = {}
    labels = None
    if plan.canonical_labels:
        from wasds150.catalog.labels import StationLabels

        labels = StationLabels(((f.favorite_key, d, c) for f, _s, d, c in candidates), home=plan.home)
    result = _resolve_once(plan, profile, candidates, cache=cache, labels=labels)
    if plan.fill_to_capacity and result.capacity is not None:
        result = _fill_spare_capacity(plan, profile, candidates, result, cache, labels)
    return result


def _widened(block: PlanBlock, limit: Optional[int]) -> PlanBlock:
    selectors = tuple(
        replace(s, within_miles=(s.within_miles[0], s.within_miles[1], max(s.within_miles[2], FILL_RADIUS_MILES)))
        if s.within_miles is not None
        else s
        for s in block.selectors
    )
    return replace(block, selectors=selectors, limit=limit)


def _fill_spare_capacity(
    plan: ChannelPlan,
    profile: RadioProfile,
    candidates: List[Tuple[FavoritesList, System, Department, Channel]],
    result: ResolvedPlan,
    cache: Dict[tuple, List[Selected]],
    labels: Optional[object] = None,
) -> ResolvedPlan:
    capacity = result.capacity
    current, added = plan, 0
    budgeted = result.slots_used
    for _round in range(_FILL_ROUNDS):
        free = capacity - result.slots_used
        if free <= 0 or not any(block.fill for block in current.blocks):
            break
        # What every fill block would take next with no limit but its fill
        # ceiling and no radius but the state's.
        probe_blocks = tuple(
            _widened(block, max(block.fill_limit, block.limit or 0) if block.fill_limit else None)
            if block.fill else block
            for block in current.blocks
        )
        probe = _resolve_once(replace(current, blocks=probe_blocks), profile, candidates, enforce_capacity=False, cache=cache,
                              labels=labels)
        order = {block.label: index for index, block in enumerate(current.blocks)}
        fillable = {block.label for block in current.blocks if block.fill}
        seen: Dict[str, int] = {}
        extras = []
        for channel in probe.channels:
            seen[channel.block] = seen.get(channel.block, 0) + 1
            if channel.block in fillable and seen[channel.block] > result.block_counts.get(channel.block, 0):
                miles = channel.distance_miles if channel.distance_miles is not None else math.inf
                extras.append((miles, order[channel.block], seen[channel.block], channel.block))
        extras.sort()
        granted: Dict[str, int] = {}
        for _miles, _order, _index, label in extras[:free]:
            granted[label] = granted.get(label, 0) + 1
        if not granted:
            break
        current = replace(
            current,
            blocks=tuple(
                _widened(block, result.block_counts.get(block.label, 0) + granted[block.label])
                if block.label in granted else block
                for block in current.blocks
            ),
        )
        before = result.slots_used
        result = _resolve_once(current, profile, candidates, cache=cache, labels=labels)
        if result.slots_used <= before:
            break
    added = result.slots_used - budgeted
    if added > 0:
        far = sum(1 for channel in result.channels if plan.radius_miles is not None
                  and channel.distance_miles is not None and channel.distance_miles > plan.radius_miles)
        result.warnings.append(
            f"filled {added} spare slot(s) with the next-nearest stations; "
            f"{far} beyond {plan.radius_miles:g} miles are programmed but not scanned"
        )
    return result
