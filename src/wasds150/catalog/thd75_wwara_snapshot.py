"""Small current WWARA snapshot filling confirmed gaps in the TH-D75 image.

The full WWARA extract remains refreshable local data and is not vendored.
These five WW7MST coordinations are retained as a narrowly curated snapshot so
a fresh checkout reproduces the repeaters found during the 2026-08-27 audit.
"""
from __future__ import annotations

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.util.hashing import stable_id

WWARA_URL = "https://www.wwara.org/DataBaseExtract.zip"
SOURCE_SHA256 = "CE204B5E0DCB63FBCF65C3CCA110D4880E4CBED12852AC723E157E454820C6FE"

# output, input, site, latitude, longitude
_WW7MST = (
    (146.900, 146.300, "Seattle", 47.562710, -122.308390),
    (224.680, 223.080, "Seattle", 47.562710, -122.308390),
    (443.550, 448.550, "Seattle", 47.562710, -122.308390),
    (443.675, 448.675, "Tacoma", 47.259370, -122.455160),
    (444.825, 449.825, "Seattle", 47.713830, -122.337500),
)


def _channel(output: float, input_frequency: float, site: str, lat: float, lon: float) -> Channel:
    return Channel(
        id=stable_id(f"thd75-wwara:WW7MST:{output}:{site}", kind="channel"),
        label=f"WW7MST {site}",
        freq_mhz=output,
        tx_freq_mhz=input_frequency,
        mode="FM",
        tone="TONE=C103.5",
        service_type=13,
        lat=lat,
        lon=lon,
        location_precision="unknown",
        notes=(
            "Current WWARA coordination snapshot dated 2026-08-27; transmit "
            "CTCSS 103.5 Hz. Refreshable full source: " + WWARA_URL
        ),
    )


def favorite() -> FavoritesList:
    departments = []
    for label, low, high in (
        ("2 Meter Snapshot", 144.0, 148.0),
        ("1.25 Meter Snapshot", 222.0, 225.0),
        ("70 Centimeter Snapshot", 430.0, 450.0),
    ):
        rows = [_channel(*row) for row in _WW7MST if low <= row[0] <= high]
        departments.append(
            Department(
                id=stable_id(f"thd75-wwara:{label}", kind="department"),
                label=label,
                channels=rows,
            )
        )
    return FavoritesList(
        id=stable_id("thd75-wwara:2026-08-27", kind="favorites-list"),
        slug="thd75wwara",
        favorite_key="THD75WWARA",
        favorite_name="TH-D75 Current WWARA Gap Snapshot",
        region="Seattle and Tacoma",
        counties="King, Pierce",
        scenario="Confirmed coordinated repeaters missing from the prior radio image",
        source_type="WWARA nightly coordination extract",
        system_or_category="WW7MST analog repeaters",
        sites_or_coverage="16.9 to 34.7 miles from Ames Lake",
        departments_or_channels="146.900; 224.680; 443.550; 443.675; 444.825 MHz",
        mode="FM",
        monitorability="Native on TH-D75",
        upgrade_required="None",
        source_url=WWARA_URL,
        notes=f"Source ZIP SHA-256 {SOURCE_SHA256}; coordinates may be fuzzed by WWARA.",
        systems=[
            System(
                id=stable_id("thd75-wwara:WW7MST", kind="system"),
                label="WW7MST Coordinated Repeaters",
                departments=departments,
            )
        ],
        provenance=[
            Provenance(
                source_adapter="wwara_snapshot",
                source_url=WWARA_URL,
                fetched_at="2026-08-28T02:55:15Z",
                confidence="verified",
            )
        ],
    )
