"""Turn the generated :mod:`wasds150.catalog.atd890_dmr` snapshot into lists.

Kept separate from the generated module so the generator only ever writes
data. The snapshot rows are replayed through the same
:mod:`wasds150.sources.k7abd` fact shape and
:func:`wasds150.recipes.dmr_networks.build_network_favorites` that the live
``seattledmr`` source uses, so a plan resolves identically from either.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from wasds150.models.catalog import FavoritesList
from wasds150.recipes.dmr_networks import build_network_favorites
from wasds150.sources.k7abd import AnalogDef, RepeaterDef, TalkgroupDef, facts_from_k7abd

RepeaterRow = Tuple[str, str, float, float, int, Optional[float], Optional[float], Dict[str, int]]
AnalogRow = Tuple[str, str, str, str, float, float, str, str, bool]


def favorites_from_snapshot(
    talkgroups: Dict[str, int],
    repeaters: Sequence[RepeaterRow],
    analog: Sequence[AnalogRow],
    retrieved: str,
) -> List[FavoritesList]:
    defs = [
        RepeaterDef(label=label, code=code, rx_mhz=rx, tx_mhz=tx, color_code=cc, slots=dict(slots))
        for label, code, rx, tx, cc, _lat, _lon, slots in repeaters
    ]
    points = {
        (round(rx, 4), cc): (lat, lon)
        for _label, _code, rx, _tx, cc, lat, lon, _slots in repeaters
        if lat is not None and lon is not None
    }
    tg_defs = {name: TalkgroupDef(name=name, tg_id=tg_id) for name, tg_id in talkgroups.items()}
    analog_defs = [AnalogDef(*row) for row in analog]
    facts = facts_from_k7abd(defs, tg_defs, analog_defs, retrieved_at=retrieved, source_id="atd890_dmr_snapshot")

    def coords(freq_mhz: float, color: Optional[int], _site_words):
        return points.get((round(freq_mhz, 4), color))

    return build_network_favorites(facts, coords=coords, retrieved_at=retrieved)
