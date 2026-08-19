"""Turn a :class:`~wasds150.models.plan.ChannelPlan` into concrete memories.

Resolution is deliberately lossy in one direction only: a channel the target
radio cannot use is *dropped with a stated reason*, never silently coerced
into something the radio will accept.  A scanner catalog contains 800 MHz
trunked talkgroups and P25 systems; a TD-H9 can do nothing with either, and
quietly rewriting them as analog FM would produce a radio full of dead
channels that look programmed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import (
    TX_NONE,
    TX_REPEATER,
    TX_SIMPLEX,
    ChannelPlan,
    PlanBlock,
    SORT_FREQ,
    SORT_LABEL,
    SORT_NATURAL,
    natural_key,
)
from wasds150.plan.naming import NameAllocator
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
    transmit: bool = False
    tx_freq_mhz: Optional[float] = None
    rx_tone: ToneSpec = NO_TONE
    tx_tone: ToneSpec = NO_TONE
    power: str = "5.0W"
    skip_scan: bool = False
    comment: str = ""


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


def _select_for_block(
    block: PlanBlock,
    candidates: List[Tuple[FavoritesList, System, Department, Channel]],
) -> List[Tuple[FavoritesList, Department, Channel]]:
    picked: List[Tuple[FavoritesList, Department, Channel]] = []
    for favorite, _system, department, channel in candidates:
        for selector in block.selectors:
            if selector.matches(favorite.favorite_key, department.label, channel):
                picked.append((favorite, department, channel))
                break

    if block.sort == SORT_FREQ:
        picked.sort(key=lambda item: (item[2].freq_mhz or 0.0, item[2].label))
    elif block.sort == SORT_LABEL:
        picked.sort(key=lambda item: (item[2].label.upper(), item[2].freq_mhz or 0.0))
    elif block.sort == SORT_NATURAL:
        picked.sort(key=lambda item: (natural_key(item[2].label), item[2].freq_mhz or 0.0))
    return picked


def _resolve_tones(
    channel: Channel, transmit: bool
) -> Tuple[ToneSpec, ToneSpec, List[str]]:
    """Decide receive and transmit tones.

    Receive squelch is left open on monitoring channels on purpose: a CTCSS
    receive tone makes the radio ignore every transmission that does not carry
    it, which is the opposite of what you want when the reason the channel is
    programmed at all is to hear what is happening.
    """
    notes: List[str] = []
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


def resolve_plan(
    plan: ChannelPlan,
    catalog: Catalog,
    profile: Optional[RadioProfile] = None,
) -> ResolvedPlan:
    """Resolve ``plan`` against ``catalog`` for its target radio."""
    profile = profile or get_profile(plan.radio_id)
    result = ResolvedPlan(plan=plan, profile=profile)

    if not profile.verified:
        result.warnings.append(
            f"radio profile {profile.id!r} is unverified; check its capabilities "
            "against the manual before programming a radio from this plan"
        )

    candidates = list(iter_catalog_channels(catalog))
    allocator = NameAllocator(
        profile.name_max_len or 64, charset=profile.name_charset
    )
    capacity = result.capacity
    seen_frequencies: Dict[Tuple[float, Optional[float], bool, str], PlannedChannel] = {}
    slot = 0

    for block in plan.blocks:
        taken = 0
        for favorite, department, channel in _select_for_block(block, candidates):
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

            rx_tone, tx_tone, tone_notes = _resolve_tones(channel, transmit)
            result.warnings.extend(tone_notes)

            # Two memories are the same only if they tune identically. A GMRS
            # repeater channel shares its output frequency with the simplex
            # channel of the same number but transmits five megahertz up, and
            # two repeaters can share a pair while answering to different
            # access tones, so the receive frequency alone is not an identity.
            tuning_key = (
                freq,
                tx_freq if transmit else None,
                transmit,
                tx_tone.raw if transmit else "",
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
            planned = PlannedChannel(
                slot=slot,
                name=allocator.allocate(channel.label, key=channel.id),
                label=channel.label,
                rx_freq_mhz=freq,
                mode=mode,
                block=block.label,
                source=f"{favorite.favorite_key}/{department.label}",
                transmit=transmit,
                tx_freq_mhz=tx_freq,
                rx_tone=rx_tone,
                tx_tone=tx_tone,
                power=block.power,
                skip_scan=block.skip_scan,
                comment=channel.notes or "",
            )
            result.channels.append(planned)
            seen_frequencies[tuning_key] = planned

        result.block_counts[block.label] = taken

    if capacity is not None:
        remaining = capacity - slot
        if remaining < 0:
            raise AssertionError("resolver exceeded the radio's capacity")
        if remaining == 0:
            result.warnings.append(
                "plan filled every available slot; nothing was left for field additions"
            )

    return result
