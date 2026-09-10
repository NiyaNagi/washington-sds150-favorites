"""AT-D890UV-native channels no scanner source carries.

DMR simplex is a convention, not a coordinated allocation, so it appears in
no coordinator or scanner database. The Pacific Northwest networks' own
codeplug files name the simplex talkgroup ("Simplex 99" in the SeattleDMR
Config Builder talkgroup list) and the two UHF frequencies in common use.
"""
from __future__ import annotations

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.util.hashing import stable_id

SEATTLEDMR_TALKGROUPS_URL = "https://seattledmr.com/ConfigBuilder/Talkgroups-Merged.csv"

# frequency, label
_DMR_SIMPLEX = (
    (441.000, "DMR Simplex 441"),
    (446.500, "DMR Simplex 446"),
)


def _simplex(freq: float, label: str) -> Channel:
    return Channel(
        id=stable_id(f"atd890:dmr-simplex:{freq}", kind="channel"),
        label=label,
        freq_mhz=freq,
        mode="DMR",
        tone="ColorCode=1",
        service_type=13,
        notes=(
            "DMR simplex convention: talkgroup 99, timeslot 1, colour code 1. "
            "Talkgroup per " + SEATTLEDMR_TALKGROUPS_URL
        ),
        dmr_color_code=1,
        dmr_timeslot=1,
        dmr_talkgroup=99,
        dmr_talkgroup_name="Simplex 99",
        network="Simplex",
    )


def favorite() -> FavoritesList:
    simplex = Department(
        id=stable_id("atd890:dmr-simplex", kind="department"),
        label="DMR Simplex",
        channels=[_simplex(*row) for row in _DMR_SIMPLEX],
    )
    return FavoritesList(
        id=stable_id("atd890:local", kind="favorites-list"),
        slug="atd890local",
        favorite_key="ATD890LOCAL",
        favorite_name="AT-D890UV Native Channels",
        region="Puget Sound",
        counties="King, Snohomish, Pierce, Kitsap",
        scenario="DMR simplex for direct radio-to-radio contact",
        source_type="Regional DMR network convention",
        system_or_category="DMR simplex",
        sites_or_coverage="Simplex; no site",
        departments_or_channels="441.000 and 446.500 MHz, talkgroup 99, timeslot 1, colour code 1",
        mode="DMR",
        monitorability="Native on DMR transceivers",
        upgrade_required="DMR",
        source_url=SEATTLEDMR_TALKGROUPS_URL,
        notes="Amateur transmit only; a General-class licence covers 70 cm.",
        systems=[System(id=stable_id("atd890:local:system", kind="system"), label="AT-D890UV Native Channels", departments=[simplex])],
        provenance=[Provenance(source_adapter="seattledmr", source_url=SEATTLEDMR_TALKGROUPS_URL, confidence="community")],
    )
