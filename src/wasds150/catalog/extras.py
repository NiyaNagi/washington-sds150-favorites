"""Radio-native catalog modules, handed to each radio by capability.

Some checked-in Favorites Lists are useful only to transceivers: a D-STAR
repeater table, the DMR network talkgroup layout, broadcast stations for a
radio with a broadcast receiver. They are added at plan-resolution time
rather than merged into the shared catalog every scanner build reads.

Which radio gets which list used to be an ``if radio_id == ...`` ladder, so a
new radio received nothing until someone remembered to extend it. Here each
module states what a radio needs to use it - a mode, an overlapping receive
range, or (only where the content is written by one specific exporter) a
radio id - and every registered radio gets exactly the modules it
qualifies for.

The order of :data:`EXTRAS` is the order lists are appended to the catalog,
and it matters: frequency-sorted blocks keep catalog order for ties, and the
first of two identical memories is the one programmed. The order below
reproduces what the TH-D75 and AT-D890UV received before this module existed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, FrozenSet, List, Tuple

from wasds150.models.catalog import FavoritesList
from wasds150.radios.profile import RadioProfile
from wasds150.radios.projection import project_favorites


def _broadcast() -> List[FavoritesList]:
    from wasds150.catalog.puget_broadcast import favorite

    return [favorite()]


def _thd75_local() -> List[FavoritesList]:
    from wasds150.catalog.thd75_local import favorite

    return [favorite()]


def _thd75_user() -> List[FavoritesList]:
    from wasds150.catalog.thd75_user import favorite

    return [favorite()]


def _wwara_snapshot() -> List[FavoritesList]:
    from wasds150.catalog.thd75_wwara_snapshot import favorite

    return [favorite()]


def _atd890_local() -> List[FavoritesList]:
    from wasds150.catalog.atd890_local import favorite

    return [favorite()]


def _dmr_networks() -> List[FavoritesList]:
    from wasds150.catalog.atd890_dmr import favorites

    return list(favorites())


def _brandmeister() -> List[FavoritesList]:
    from wasds150.catalog.brandmeister_snapshot import favorites

    return list(favorites())


@dataclass(frozen=True)
class ExtraCatalog:
    key: str
    loader: Callable[[], List[FavoritesList]]
    #: The radio must demodulate at least one of these modes.
    requires_modes: FrozenSet[str] = frozenset()
    #: The radio must receive somewhere inside at least one of these ranges.
    requires_rx_mhz: Tuple[Tuple[float, float], ...] = ()
    #: Only these radios, when the content is meaningful to one exporter only.
    radio_ids: Tuple[str, ...] = ()
    notes: str = ""

    def applies_to(self, profile: RadioProfile) -> bool:
        if self.radio_ids and profile.id not in self.radio_ids:
            return False
        if self.requires_modes and not ({m.upper() for m in self.requires_modes} & profile.modes):
            return False
        if self.requires_rx_mhz and not any(
            low <= band_high and band_low <= high
            for low, high in self.requires_rx_mhz
            for band_low, band_high in profile.rx_bands
        ):
            return False
        return True


EXTRAS: Tuple[ExtraCatalog, ...] = (
    ExtraCatalog(
        "THD75BC",
        _broadcast,
        requires_rx_mhz=((87.5, 108.0), (0.53, 1.71)),
        notes="FM and AM broadcast stations near home.",
    ),
    ExtraCatalog(
        "THD75LOCAL",
        _thd75_local,
        requires_modes=frozenset({"DV"}),
        radio_ids=("th-d75", "id-52a"),
        notes=(
            "D-STAR repeaters with URCALL/RPT1/RPT2 routing, and the source of "
            "the ID-52A's DR repeater list. Only the TH-D75 and ID-52A targets "
            "write D-STAR routing; the FTX-1's digital voice is C4FM."
        ),
    ),
    ExtraCatalog(
        "THD75USER",
        _thd75_user,
        radio_ids=("th-d75",),
        notes="Channels the operator programmed into this particular radio.",
    ),
    ExtraCatalog(
        "THD75WWARA",
        _wwara_snapshot,
        notes="Coordinated repeaters the enriched catalog may lack; steps aside for a refreshed copy.",
    ),
    ExtraCatalog(
        "ATD890LOCAL",
        _atd890_local,
        requires_modes=frozenset({"DMR"}),
        notes="DMR simplex calling channels.",
    ),
    ExtraCatalog(
        "DMRNET",
        _dmr_networks,
        requires_modes=frozenset({"DMR"}),
        notes="PNWDigital / SeattleDMR repeater and talkgroup layout.",
    ),
    ExtraCatalog(
        "BMNET",
        _brandmeister,
        requires_modes=frozenset({"DMR"}),
        notes="BrandMeister repeaters near home and their static talkgroups.",
    ),
)


def extras_for(profile: RadioProfile) -> List[FavoritesList]:
    """Every radio-native list ``profile`` qualifies for, in :data:`EXTRAS` order."""
    favorites = [fl for extra in EXTRAS if extra.applies_to(profile) for fl in extra.loader()]
    return project_favorites(favorites, profile).favorites


def extra_keys_for(profile: RadioProfile) -> List[str]:
    return [extra.key for extra in EXTRAS if extra.applies_to(profile)]
