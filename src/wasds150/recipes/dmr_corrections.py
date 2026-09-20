"""Corrections to the regional DMR layout where a network's own site disagrees.

The PNWDigital / SeattleDMR layout comes from the community Config Builder
files (:mod:`wasds150.sources.k7abd`). They are the best single source for
which talkgroup is on which timeslot of which machine, but they lag the
networks: a repeater that moved keeps its old frequency there, and one that
joined may not be there at all. A wrong row is worse than a missing one, since
it programs a zone of DMR talkgroups onto a machine that will never decode
them.

Each correction here names the network page that contradicts the file. They
are applied to any ``DMRNET`` list - the one :func:`build_network_favorites`
rebuilds when the ``seattledmr`` source runs, the checked-in snapshot, and
(through :func:`wasds150.plan.service.resolve_named_plan`) a copy already in
the operator's catalog that was built before the correction existed - so no
refresh, and no regenerated snapshot, can bring a corrected row back.
"""
from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from wasds150.models.catalog import Channel, Department, FavoritesList
from wasds150.util.hashing import stable_id

DMRNET_KEY = "DMRNET"

SEATTLEDMR_REPEATERS_URL = "https://seattledmr.org/"
RETRIEVED = "2026-09-13"

#: PNWDigital's own live records: the repeater roster, and one talkgroup deck
#: per site reached by clicking a frequency on it. These are the network
#: operator writing down what its machines are doing right now, so where they
#: contradict the Config Builder file or a coordination extract, they win.
PNWDIGITAL_REPEATERS_URL = "https://pnwdigital.net/services/repeaters.php"
PNWDIGITAL_SITE_URL = "https://pnwdigital.net/sv/siteinfo2.php?site={site}"
PNW_RETRIEVED = "2026-09-19"

#: Repeater rows to leave out, keyed by (site code, output MHz).
SUPERSEDED: Dict[Tuple[str, float], str] = {
    ("BWT", 442.075): (
        "'BEARS W.Tiger' as a SeattleDMR DMR repeater on 442.075, CC2. SeattleDMR's own "
        f"repeater list ({SEATTLEDMR_REPEATERS_URL}, retrieved {RETRIEVED}) has K7NWS West "
        "Tiger Mountain on 440.3375, CC2, and nothing on 442.075 - which the coordinated "
        "catalog holds as K7NWS's analog repeater, CTCSS 110.9."
    ),
    ("KNW", 440.3375): (
        "'Seattle/East' as a SeattleDMR repeater on 440.3375, CC2, carrying the SeattleDMR "
        "deck. The machine is K7NWS West Tiger Mtn 2 UHF and PNWDigital runs it as site STU "
        "on colour code 1 with its own deck, which holds none of those talkgroups; it is "
        "re-added below from the network's live record."
    ),
    ("SHR", 440.125): (
        "Shoreline, K7LFP 440.125. PNWDigital took the repeater off the air on 2026-07-09 "
        "and is looking for a new site (https://pnwdigital.net/shoreline-repeater/); it is "
        f"gone from the roster ({PNWDIGITAL_REPEATERS_URL}, retrieved {PNW_RETRIEVED}) "
        "although RepeaterBook still shows it. Twenty-three dead channels, seven of them in "
        "the first DMR scan list, were costing scan time on a machine that cannot answer."
    ),
}

#: Output/input pairs a list's source has stale, keyed by (site code or
#: callsign, the output MHz it currently carries). A repeater that moved keeps
#: its old pair in both the Config Builder file and, until the coordinator
#: catches up, in WWARA's extract - and a radio 5 kHz off hears nothing at all.
PAIRS: Dict[Tuple[str, float], Tuple[float, float, str]] = {
    key: (
        147.025,
        147.625,
        "WA7DMR Cougar Mtn (PNWDigital 'Cougar VHF', RID 312947) moved to 147.0250 +0.600 "
        "when the repeater was replaced on 2025-06-22. PNWDigital's roster "
        f"({PNWDIGITAL_REPEATERS_URL}, 'New Rptr installed 6-22-25') and its site deck "
        f"({PNWDIGITAL_SITE_URL.format(site=2)}) both say 147.0250/147.6250 CC1, retrieved "
        f"{PNW_RETRIEVED}. The Config Builder file and WWARA's extract both still carry "
        "147.0200, the pair the machine no longer uses.",
    )
    for key in (("BVV", 147.02), ("WA7DMR", 147.02))
}


@dataclass(frozen=True)
class AddedRepeater:
    """A network repeater the Config Builder file lacks.

    ``layout_from`` names a repeater on the same network whose talkgroups and
    timeslots it carries; that is only sound where the network publishes one
    talkgroup table for all of its machines, as SeattleDMR does. Where the
    network publishes a deck for this machine, ``deck`` lists the talkgroup
    ids on it, and only those are copied - so a repeater is never given a
    talkgroup its own operator does not show. A deck entry the template
    repeater lacks is simply absent rather than invented.
    """

    code: str
    site: str
    rx_mhz: float
    tx_mhz: float
    color_code: int
    lat: float
    lon: float
    layout_from: str
    department: str
    citation: str
    deck: Tuple[int, ...] = ()


#: The talkgroup ids on both West Tiger decks, which are identical
#: (``siteinfo2.php?site=312488`` and ``?site=314972``, retrieved 2026-09-19).
#: Cougar UHF, the layout template, does not carry TAC 3 (8953), Montana 2
#: (3130), N.America 2 (3163), Utah 2 (3149) or Worldwide 2 (3161), so those
#: five wide-area groups are left off rather than guessed onto the machine.
_WEST_TIGER_DECK: Tuple[int, ...] = (
    3153, 103153, 3187, 103187, 31771, 3181, 3166, 3168, 3191, 3141, 3027, 3106, 3116,
    3100, 302, 3130, 3163, 3177, 3149, 3161, 31002, 8951, 8952, 8953, 310, 311, 312,
    1776, 9998, 9999,
)

ADDED: Tuple[AddedRepeater, ...] = (
    AddedRepeater(
        code="STU",
        site="K7NWS West Tiger Mtn 2 UHF",
        rx_mhz=440.3375,
        tx_mhz=445.3375,
        # CC1, not the CC2 that SeattleDMR and WWARA's extract carry.
        color_code=1,
        # West Tiger Mountain, as the checked-in snapshot's Seattle/East row gives it.
        lat=47.50875,
        lon=-121.98519,
        layout_from="BVC",
        department="Puget Sound",
        deck=_WEST_TIGER_DECK,
        citation=(
            "PNWDigital runs K7NWS West Tiger Mtn 2 UHF, 440.3375 +5 MHz, as site STU "
            f"(RID 312488) on colour code 1: {PNWDIGITAL_REPEATERS_URL} and its deck at "
            f"{PNWDIGITAL_SITE_URL.format(site=312488)}, both retrieved {PNW_RETRIEVED}, and "
            "RadioID and the owner (Boeing Employees ARS) agree. SeattleDMR lists the same "
            f"machine as one of its four repeaters on CC2 ({SEATTLEDMR_REPEATERS_URL}, "
            f"retrieved {RETRIEVED}), and WWARA's extract also says CC2; a radio on the wrong "
            "colour code decodes nothing, and the SeattleDMR talkgroups (King County, Seattle "
            "1/2, Puget Sound, BEARS, Link 1-6, TAC 313) are not on this deck at all."
        ),
    ),
    AddedRepeater(
        code="STV",
        site="K7NWS West Tiger Mtn 2 VHF",
        # WWARA coordinates K7NWS Tiger Mtn West as 146.500 out, 147.500 in,
        # +1.0 MHz, which is how the roster reads it; the site page prints the
        # pair the other way round.
        rx_mhz=146.5,
        tx_mhz=147.5,
        color_code=1,
        lat=47.50875,
        lon=-121.98519,
        layout_from="BVC",
        department="Puget Sound",
        deck=_WEST_TIGER_DECK,
        citation=(
            "PNWDigital installed K7NWS West Tiger Mtn 2 VHF, 146.500 +1.000 MHz CC1, as site "
            f"STV (RID 314972) on 2026-05-06 - after the Config Builder snapshot, so no row "
            f"for it exists ({PNWDIGITAL_REPEATERS_URL} and "
            f"{PNWDIGITAL_SITE_URL.format(site=314972)}, retrieved {PNW_RETRIEVED}; WWARA "
            "coordinates the pair to K7NWS). It is deliberately co-channel with Bellingham "
            "and BawFaw for single-channel I-5 coverage, so its rows carry the local site: "
            "nine miles from home against Bellingham's seventy-five."
        ),
    ),
)


def _site_code(channel: Channel) -> str:
    """``King County BWT`` -> ``BWT``: the layout names channels "<talkgroup> <code>"."""
    return (channel.label or "").rsplit(" ", 1)[-1]


def _is_dmr(channel: Channel) -> bool:
    return (channel.mode or "").upper() == "DMR"


def _departments(fl: FavoritesList) -> List[Department]:
    departments: List[Department] = []
    for system in fl.systems:
        departments.extend(system.departments)
        for site in system.sites:
            departments.extend(site.departments)
    return departments


def _superseded(channel: Channel) -> bool:
    if not _is_dmr(channel) or channel.freq_mhz is None:
        return False
    return (_site_code(channel), round(channel.freq_mhz, 4)) in SUPERSEDED


def correct_network_list(fl: FavoritesList) -> FavoritesList:
    """``fl`` with the corrections applied; any list but ``DMRNET`` unchanged."""
    if (fl.favorite_key or "").upper() != DMRNET_KEY:
        return fl
    fl = copy.deepcopy(fl)
    departments = _departments(fl)
    for department in departments:
        department.channels = [c for c in department.channels if not _superseded(c)]
    for added in ADDED:
        channels = [c for d in departments for c in d.channels if _is_dmr(c)]
        if any(_site_code(c) == added.code and c.freq_mhz is not None
               and abs(c.freq_mhz - added.rx_mhz) < 5e-4 for c in channels):
            continue
        template = [c for c in channels if _site_code(c) == added.layout_from]
        if added.deck:
            wanted = set(added.deck)
            template = [c for c in template if c.dmr_talkgroup in wanted]
        if not template:
            continue
        target = next((d for d in departments if d.label == added.department), None)
        if target is None:
            continue
        for channel in template:
            tone = channel.tone or ""
            target.channels.append(dataclasses.replace(
                channel,
                id=stable_id(
                    f"dmrnet:added:{added.code}:{channel.dmr_talkgroup}:{channel.dmr_timeslot}", kind="channel"
                ),
                label=channel.label[: -len(added.layout_from)] + added.code,
                freq_mhz=added.rx_mhz,
                tx_freq_mhz=added.tx_mhz,
                dmr_color_code=added.color_code,
                tone=f"ColorCode={added.color_code}" if tone.startswith("ColorCode=") else tone,
                lat=added.lat,
                lon=added.lon,
                location_precision="unknown",
                notes=(
                    f"{channel.network} repeater {added.site} ({added.code}); talkgroup "
                    f"{channel.dmr_talkgroup_name} on timeslot {channel.dmr_timeslot}; {added.citation}"
                ),
            ))
    return fl


#: DMR colour codes the coordinator's record gets wrong, keyed by (callsign,
#: output MHz). Every copy of these rows in the catalog descends from one
#: coordination entry, so fixing the catalog would mean fixing every list
#: that repeats it; the correction is applied to every list instead. A
#: colour code matters: a scanner or radio set to the wrong one decodes
#: nothing from the repeater.
COLOR_CODES: Dict[Tuple[str, float], Tuple[int, str]] = {
    ("N7QT", 442.325): (
        1,
        "N7QT Redmond reports colour code 1 to BrandMeister (api.brandmeister.network/v2/"
        f"device/311757, last seen {RETRIEVED}, both slots linked); the coordination record "
        "every other list copies says 2.",
    ),
}


def _color_fix(channel: Channel) -> Optional[int]:
    if not _is_dmr(channel) or channel.freq_mhz is None:
        return None
    label = (channel.label or "").upper()
    for (call, mhz), (color, _why) in COLOR_CODES.items():
        if abs(channel.freq_mhz - mhz) < 5e-4 and call in label:
            current = channel.dmr_color_code
            tone = channel.tone or ""
            if current is None and tone.startswith("ColorCode="):
                try:
                    current = int(tone.split("=", 1)[1])
                except ValueError:
                    current = None
            return color if current != color else None
    return None


def correct_color_codes(fl: FavoritesList) -> FavoritesList:
    """``fl`` with :data:`COLOR_CODES` applied; the same object when nothing matches."""
    if not any(_color_fix(c) is not None for d in _departments(fl) for c in d.channels):
        return fl
    fl = copy.deepcopy(fl)
    for department in _departments(fl):
        for index, channel in enumerate(department.channels):
            color = _color_fix(channel)
            if color is None:
                continue
            tone = channel.tone or ""
            department.channels[index] = dataclasses.replace(
                channel,
                dmr_color_code=color,
                tone=f"ColorCode={color}" if (not tone or tone.startswith("ColorCode=")) else tone,
            )
    return fl


def _pair_fix(channel: Channel) -> Optional[Tuple[float, float]]:
    """The pair :data:`PAIRS` moves this channel to, or ``None``.

    A row is matched by its site code (the Config Builder layout names
    channels ``"<talkgroup> <code>"``) or by a callsign in its label, so one
    entry corrects the network list and the coordination record together.
    """
    if not _is_dmr(channel) or channel.freq_mhz is None:
        return None
    freq = round(channel.freq_mhz, 4)
    label = (channel.label or "").upper()
    for (name, mhz), (rx, tx, _why) in PAIRS.items():
        if abs(freq - mhz) > 5e-4:
            continue
        if _site_code(channel) == name or name.upper() in label:
            return (rx, tx)
    return None


def correct_pairs(fl: FavoritesList) -> FavoritesList:
    """``fl`` with :data:`PAIRS` applied; the same object when nothing matches."""
    if not any(_pair_fix(c) for d in _departments(fl) for c in d.channels):
        return fl
    fl = copy.deepcopy(fl)
    for department in _departments(fl):
        for index, channel in enumerate(department.channels):
            pair = _pair_fix(channel)
            if pair is None:
                continue
            rx, tx = pair
            notes = channel.notes or ""
            # The note spells out the input the coordinator published; leaving
            # the old pair in it would contradict the row it now describes.
            moved = f"moved to {rx:.4f}/{tx:.4f} (repeater registry: PNWDigital site record)"
            department.channels[index] = dataclasses.replace(
                channel,
                freq_mhz=rx,
                tx_freq_mhz=tx,
                notes=f"{notes}; {moved}" if notes else moved,
            )
    return fl


#: Analog access tones a list's source gets wrong, keyed by (list key, channel
#: label, output MHz). The Seattle ACS channel plan is rebuilt from the
#: SeattleDMR source, so the correction has to follow every rebuild.
ANALOG_TONES: Dict[Tuple[str, str, float], Tuple[str, str]] = {
    ("SEAACS", "U71 Mountlake", 443.725): (
        "TONE=C156.7",
        "WA7DEM Mountlake Terrace, 443.725 +5 MHz: WWARA's coordination (CTCSS_IN 156.7, extract "
        f"{RETRIEVED}) and WA7DEM's own net listing agree; the ACS plan's copy carries 103.5.",
    ),
    ("SEAACS", "U04N Beacon2", 442.3): (
        "TONE=C141.3",
        "W7ACS Beacon Hill, 442.300 +5 MHz: WWARA coordinates the pair at CTCSS_IN 141.3, and the "
        "ACS plan's own 'U04 Beacon2' on the same pair carries 141.3. Only the 'U04N' row carries "
        "123, which matches no coordinated machine on the pair - the project's rule is that a "
        "memory transmits the access tone of the machine it names (CLAUDE.md).",
    ),
}


def correct_analog_tones(fl: FavoritesList) -> FavoritesList:
    """``fl`` with :data:`ANALOG_TONES` applied; the same object when nothing matches."""
    key = (fl.favorite_key or "").upper()
    wanted = {(label.casefold(), mhz): tone for (list_key, label, mhz), (tone, _why) in ANALOG_TONES.items()
              if list_key == key}
    if not wanted:
        return fl

    def fix(channel: Channel) -> Optional[str]:
        if channel.freq_mhz is None:
            return None
        for (label, mhz), tone in wanted.items():
            if abs(channel.freq_mhz - mhz) < 5e-4 and (channel.label or "").casefold() == label:
                return tone if (channel.tx_tone or channel.tone) != tone else None
        return None

    if not any(fix(c) for d in _departments(fl) for c in d.channels):
        return fl
    fl = copy.deepcopy(fl)
    for department in _departments(fl):
        department.channels = [
            dataclasses.replace(channel, tone=tone, tx_tone=tone) if (tone := fix(channel)) else channel
            for channel in department.channels
        ]
    return fl


def correct_network_lists(favorites: Iterable[FavoritesList]) -> List[FavoritesList]:
    return [
        correct_analog_tones(correct_pairs(correct_color_codes(correct_network_list(fl))))
        for fl in favorites
    ]
