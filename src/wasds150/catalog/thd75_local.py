"""TH-D75-native local channels not represented by scanner sources.

The D-STAR rows are the 2 m and 70 cm entries in Kenwood's current worldwide
repeater list whose published coordinates are within 50 miles of Ames Lake.
The radio's separate DR list should also receive the filtered Kenwood TSV; the
ordinary memories here make the same local repeaters available to group scan.
"""
from __future__ import annotations

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.util.hashing import stable_id

KENWOOD_DSTAR_URL = "https://www.kenwood.com/i/products/info/amateur/software_download.html"
AMES_LAKE_LAT = 47.633966
AMES_LAKE_LON = -121.960584

# call, gateway, city, output MHz, shift MHz, latitude, longitude
_DSTAR = (
    ("W7RNK  C", "W7RNK  G", "Newcastle", 147.9950, -0.6000, 47.542000, -122.108833),
    ("WA7HJR B", "WA7HJR G", "Seattle", 444.6375, 5.0000, 47.490500, -121.947167),
    ("N7IH   C", "N7IH   G", "Kirkland", 146.8750, 1.0000, 47.631000, -122.184500),
    ("N7IH   B", "N7IH   G", "Kirkland", 443.5750, 5.0000, 47.631000, -122.184500),
    ("K7LWH  C", "K7LWH  G", "Bellevue", 146.1250, 1.0000, 47.616500, -122.201667),
    ("K7LWH  B", "K7LWH  G", "Bellevue", 443.0625, 5.0000, 47.616500, -122.201667),
    ("N7SNO  B", "N7SNO  G", "Snoqualmie", 442.7000, 5.0000, 47.468500, -121.822333),
    ("KF7UUY B", "KF7UUY G", "Lake Stevens", 441.2625, 5.0000, 47.789000, -122.236000),
    ("KF7NPL B", "KF7NPL G", "Maple Valley", 442.6750, 5.0000, 47.387167, -122.061000),
    ("KF7BFT B", "KF7BFT G", "Tukwila", 440.4250, 5.0000, 47.471667, -122.259333),
    ("KF7BFS B", "KF7BFS G", "Tukwila", 440.2750, 5.0000, 47.450833, -122.286667),
    ("KF7CLD B", "KF7CLD G", "Burien", 443.4250, 5.0000, 47.497000, -122.336500),
    ("KG7QPU B", "KG7QPU G", "Snohomish", 443.9000, 5.0000, 47.940833, -122.023833),
    ("NR7SS  B", "NR7SS  G", "Everett", 440.3500, 5.0000, 47.906167, -122.281333),
    ("W7NPC  B", "W7NPC  G", "Bainbridge", 444.5625, 5.0000, 47.655833, -122.547500),
    ("WA7FW  C", "WA7FW  G", "Federal Way", 146.8400, -0.6000, 47.305667, -122.322833),
    ("WA7FW  B", "WA7FW  G", "Federal Way", 443.8500, 5.0000, 47.305667, -122.322833),
    ("K7GKR  B", "K7GKR  G", "Kingston", 444.7250, 5.0000, 47.844000, -122.542833),
    ("WA7DR  B", "WA7DR  G", "Graham", 442.9250, 5.0000, 47.029000, -122.299500),
    ("W7JD   B", "W7JD   G", "Enumclaw", 442.6250, 5.0000, 47.043500, -122.381833),
    ("KK7PPV B", "KK7PPV G", "Issaquah", 443.0000, 5.0000, 47.492167, -122.955667),
)


def _dstar_channel(call: str, gateway: str, city: str, frequency: float, shift: float,
                   lat: float, lon: float) -> Channel:
    tx = frequency + shift
    return Channel(
        id=stable_id(f"thd75:dstar:{call}:{frequency}", kind="channel"),
        label=f"{call.strip()} {city}",
        freq_mhz=frequency,
        tx_freq_mhz=tx,
        mode="DV",
        service_type=13,
        lat=lat,
        lon=lon,
        location_precision="unknown",
        notes="Kenwood worldwide D-STAR repeater list; published position is approximate.",
        dv_urcall="CQCQCQ",
        dv_rpt1=call,
        dv_rpt2=gateway,
    )


def favorite() -> FavoritesList:
    dstar = Department(
        id=stable_id("thd75:ames-lake:dstar", kind="department"),
        label="D-STAR Repeaters Within 50 Miles",
        channels=[_dstar_channel(*row) for row in _DSTAR],
        lat=AMES_LAKE_LAT,
        lon=AMES_LAKE_LON,
        range_miles=50.0,
        shape="Circle",
    )
    simplex = Department(
        id=stable_id("thd75:ames-lake:simplex", kind="department"),
        label="TH-D75 Calling and Packet",
        channels=[
            Channel(
                id=stable_id("thd75:223.5-calling", kind="channel"),
                label="1.25m FM Calling",
                freq_mhz=223.500,
                mode="FM",
                service_type=13,
                notes="National 1.25 m FM simplex calling frequency.",
            ),
        ],
    )
    return FavoritesList(
        id=stable_id("thd75:ames-lake", kind="favorites-list"),
        slug="thd75local",
        favorite_key="THD75LOCAL",
        favorite_name="TH-D75 Ames Lake Native Channels",
        region="Ames Lake / central Puget Sound",
        counties="King, Snohomish, Pierce, Kitsap",
        scenario="D-STAR DR and tri-band amateur operation",
        source_type="Kenwood D-STAR repeater list + amateur band plan",
        system_or_category="TH-D75-native D-STAR and 1.25 m channels",
        sites_or_coverage="50 miles from 47.633966,-121.960584",
        departments_or_channels="Local D-STAR repeaters; 1.25 m calling",
        mode="DV/FM",
        monitorability="Native on TH-D75",
        upgrade_required="None",
        source_url=KENWOOD_DSTAR_URL,
        notes="Snapshot from KWD_20260823_E.tsv; refresh the native DR list separately when Kenwood publishes a newer file.",
        systems=[System(
            id=stable_id("thd75:ames-lake:system", kind="system"),
            label="TH-D75 Local Native Channels",
            departments=[dstar, simplex],
        )],
        provenance=[Provenance(
            source_adapter="kenwood_dstar",
            source_url=KENWOOD_DSTAR_URL,
            confidence="verified",
        )],
    )
