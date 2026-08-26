"""Puget Sound broadcast stations for wideband-capable receivers.

This fills a deliberate scanner-catalog gap: ordinary AM/FM broadcast radio
is not useful to an SDS150 Favorites List, but it is useful on a TH-D75 Band B
receiver. The list is a 50-mile FCC AM/FM Query snapshot centered on Ames
Lake. FM auxiliary records are collapsed to their primary call/frequency and
co-channel low-power stations are represented by the strongest/local call.
"""
from __future__ import annotations

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.util.hashing import stable_id

FCC_FM_QUERY = "https://www.fcc.gov/media/radio/fm-query"
FCC_AM_QUERY = "https://www.fcc.gov/media/radio/am-query"

# One useful primary/local station per receivable frequency. City is the FCC
# community of license, not a claim about studio location or programming.
_FM = (
    (88.5, "KNKX", "Tacoma"),
    (88.9, "KMIH", "Mercer Island"),
    (89.5, "KNHC", "Seattle"),
    (89.9, "KASB", "Bellevue"),
    (90.1, "KUPS", "Tacoma"),
    (90.3, "KEXP-FM", "Seattle"),
    (90.7, "KSER", "Everett"),
    (90.9, "KVTI", "Tacoma"),
    (91.3, "KBCS", "Bellevue"),
    (91.5, "KQXI", "Granite Falls"),
    (91.7, "KYFQ", "Tacoma"),
    (92.5, "KQMV", "Bellevue"),
    (93.3, "KJR-FM", "Seattle"),
    (94.1, "KSWD", "Seattle"),
    (94.9, "KUOW-FM", "Seattle"),
    (95.7, "KJEB", "Seattle"),
    (96.5, "KJAQ", "Seattle"),
    (97.3, "KIRO-FM", "Tacoma"),
    (98.1, "KING-FM", "Seattle"),
    (98.9, "KPNW-FM", "Seattle"),
    (99.9, "KISW", "Seattle"),
    (100.7, "KKWF", "Seattle"),
    (101.5, "KPLZ-FM", "Seattle"),
    (101.9, "KQES-LP", "Bellevue"),
    (102.5, "KZOK-FM", "Seattle"),
    (103.7, "KHTP", "Tacoma"),
    (104.5, "KLSW", "Covington"),
    (104.9, "KAPY-LP", "Duvall"),
    (105.3, "KCMS", "Edmonds"),
    (106.1, "KBKS-FM", "Tacoma"),
    (106.9, "KRWM", "Bremerton"),
    (107.7, "KNDD", "Seattle"),
)

_AM = (
    (0.570, "KVI", "Seattle"),
    (0.630, "KCIS", "Edmonds"),
    (0.710, "KIRO", "Seattle"),
    (0.770, "KTTH", "Seattle"),
    (0.820, "KGNW", "Burien-Seattle"),
    (0.850, "KHHO", "Tacoma"),
    (0.880, "KIXI", "Mercer Island-Seattle"),
    (0.950, "KJR", "Seattle"),
    (1.000, "KNWN", "Seattle"),
    (1.050, "KBLE", "Seattle"),
    (1.090, "KPTR", "Seattle"),
    (1.150, "KKNW", "Seattle"),
    (1.180, "KLAY", "Lakewood"),
    (1.210, "KMIA", "Auburn-Federal Way"),
    (1.230, "KWYZ", "Everett"),
    (1.250, "KKDZ", "Seattle"),
    (1.300, "KKOL", "Seattle"),
    (1.330, "KGRG", "Enumclaw"),
    (1.360, "KKMO", "Tacoma"),
    (1.380, "KRKO", "Everett"),
    (1.420, "KRIZ", "Renton"),
    (1.450, "KSUH", "Puyallup"),
    (1.480, "KBRO", "Bremerton"),
    (1.520, "KKXA", "Snohomish"),
    (1.540, "KXPA", "Bellevue"),
    (1.560, "KZIZ", "Pacific"),
    (1.590, "KLFE", "Seattle"),
    (1.620, "KYIZ", "Renton"),
    (1.680, "KNTS", "Seattle"),
)


def _channels(rows, mode: str, source: str):
    return [
        Channel(
            id=stable_id(f"fcc-broadcast:{mode}:{call}:{frequency}", kind="channel"),
            label=f"{call} {city}",
            freq_mhz=frequency,
            mode=mode,
            service_type=9,
            notes=f"FCC licensed broadcast station within 50 miles of Ames Lake; {source} snapshot 2026-08-25.",
        )
        for frequency, call, city in rows
    ]


def favorite() -> FavoritesList:
    system = System(
        id=stable_id("puget-broadcast:system", kind="system"),
        label="Puget Sound Broadcast Radio",
        departments=[
            Department(
                id=stable_id("puget-broadcast:fm", kind="department"),
                label="FM Broadcast Within 50 Miles",
                channels=_channels(_FM, "WFM", "FCC FM Query"),
                lat=47.633966,
                lon=-121.960584,
                range_miles=50.0,
                shape="Circle",
            ),
            Department(
                id=stable_id("puget-broadcast:am", kind="department"),
                label="AM Broadcast Within 50 Miles",
                channels=_channels(_AM, "AM", "FCC AM Query"),
                lat=47.633966,
                lon=-121.960584,
                range_miles=50.0,
                shape="Circle",
            ),
        ],
    )
    return FavoritesList(
        id=stable_id("puget-broadcast:THD75BC", kind="favorites-list"),
        slug="thd75bc",
        favorite_key="THD75BC",
        favorite_name="Ames Lake Broadcast Radio",
        region="Central Puget Sound",
        counties="King, Snohomish, Pierce, Kitsap",
        scenario="Broadcast news, public radio, music, and emergency information",
        source_type="FCC AM Query + FM Query",
        system_or_category="Licensed AM and FM broadcast transmitters",
        sites_or_coverage="FCC transmitters within 50 miles of 47.633966,-121.960584",
        departments_or_channels="32 WFM and 29 AM memories",
        mode="WFM/AM",
        monitorability="Native on TH-D75 Band B",
        upgrade_required="None",
        source_url=FCC_FM_QUERY,
        notes="FCC engineering data are refreshed daily; formats and branding can change without a license change.",
        systems=[system],
        provenance=[
            Provenance(source_adapter="fcc_fm_query", source_url=FCC_FM_QUERY, confidence="verified"),
            Provenance(source_adapter="fcc_am_query", source_url=FCC_AM_QUERY, confidence="verified"),
        ],
    )
