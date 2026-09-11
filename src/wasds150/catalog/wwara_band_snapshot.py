"""Coordinated repeaters on the bands the packaged catalog otherwise lacks.

Until ``sources update`` fetches WWARA, the packaged catalog holds almost
nothing on 6 m, 1.25 m, 33 cm or 23 cm: ``PSHAM01`` ships ten
operator-published channels, and the full coordination inventory is local,
refreshable data. ``PSHAM02`` keeps every current voice coordination on those
four bands within 60 miles of home (Ames Lake / Redmond, 47.6351 N,
121.9954 W) from the WWARA extract dated 2026-09-10, so a fresh checkout
programs them.

It is a narrow, cited subset in the spirit of
:mod:`wasds150.catalog.thd75_wwara_snapshot`, not a copy of WWARA's database:
2 m, 70 cm and everything beyond the radius still come only from the
refreshable extract. Rows go through the same code a refresh uses
(:func:`wasds150.sources.wwara.fact_from_row`, then
:func:`wasds150.catalog.puget_ham.system_from_wwara_facts`), so a snapshot
channel carries the same tones, input and notes as its refreshed counterpart,
and a coordination that lapses after the snapshot date is marked avoided the
same way. Programming plans keep the first of two identical memories, and
``PSHAM01`` is selected first, so a refresh supersedes these rows there.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from wasds150.catalog.puget_ham import system_from_wwara_facts
from wasds150.models.catalog import FavoritesList
from wasds150.models.provenance import Provenance
from wasds150.sources.facts import NormalizedFact
from wasds150.sources.wwara import DATABASE_EXTRACT_URL, fact_from_row
from wasds150.util.hashing import stable_id

SNAPSHOT_DATE = "2026-09-10"
SOURCE_SHA256 = "05E3C86DA26DD843C347071A9995ABDDD6FC84F4D1D8978B4C34E166D1D7BAE8"

# record, call, city, output, input, CTCSS in, CTCSS out, DCS, modes,
# DMR colour code, P25 NAC, latitude, longitude, coordination expires.
# Filter: Washington, coordination current on the snapshot date, a voice mode
# flag set, and a published position within 60 miles of home.
_Row = Tuple[str, str, str, float, float, str, str, str, str, str, str, float, float, str]
_ROWS: Tuple[_Row, ...] = (
    # 6 m
    ("2058", "WW7PSR", "Seattle", 52.8700, 51.1700, "103.5", "103.5", "", "FM_WIDE", "", "", 47.62384, -122.31519, "2027-04-25"),
    ("2015", "K7NP", "University Place", 53.0100, 51.3100, "100", "100", "", "FM_WIDE", "", "", 47.22774, -122.55786, "2028-08-19"),
    ("2055", "KC7IYE", "Redmond", 53.0700, 51.3700, "100", "179.9", "", "FM_WIDE", "", "", 47.69250, -122.11140, "2028-12-01"),
    ("2008", "KF7T", "Everett", 53.1300, 51.4300, "100", "100", "", "FM_WIDE", "", "", 47.92660, -122.23740, "2030-10-15"),
    ("2053", "K7LWH", "Kirkland", 53.1700, 51.4700, "100", "", "", "FM_WIDE", "", "", 47.66370, -122.16650, "2029-03-16"),
    ("2024", "K7HW", "Tacoma", 53.1900, 51.4900, "100", "100", "", "FM_WIDE", "", "", 47.22156, -122.45703, "2027-10-28"),
    ("2049", "K7TGU", "University Place", 53.2300, 51.5300, "100", "100", "", "FM_WIDE", "", "", 47.22747, -122.55777, "2027-03-01"),
    ("2050", "W7AW", "Seattle", 53.2900, 51.5900, "100", "103.5", "", "FM_WIDE", "", "", 47.54050, -122.37770, "2027-05-05"),
    ("2061", "W7JCR", "Port Townsend", 53.3700, 51.6700, "100", "100", "", "FM_WIDE", "", "", 48.12450, -122.76540, "2031-07-31"),
    ("2052", "K7TGU", "Ashford", 53.3900, 51.6900, "100", "", "", "FM_WIDE", "", "", 46.83403, -122.01733, "2026-11-20"),
    ("2007", "W7PFR", "Eatonville", 53.4100, 51.7100, "100", "100", "", "FM_WIDE", "", "", 46.83540, -122.28780, "2029-12-20"),
    ("2036", "W7NPC", "Bainbridge Island", 53.4300, 51.7300, "100", "100", "", "FM_WIDE", "", "", 47.65580, -122.54750, "2031-02-10"),
    ("2040", "K6AJV", "Vashon Island", 53.7900, 52.0900, "123", "123", "", "FM_WIDE", "", "", 47.45000, -122.46000, "2026-12-23"),
    ("2018", "WW7RG", "Grass Mtn", 53.8700, 52.1700, "100", "100", "", "FM_WIDE", "", "", 47.20420, -121.79501, "2028-02-01"),
    # 1.25 m
    ("4106", "WA7DMR", "Baldi Mtn", 223.8000, 222.2000, "", "", "", "DMR", "CC1", "", 47.21901, -121.84290, "2028-01-02"),
    ("4097", "W7EMD", "Camp Murray", 223.8400, 222.2400, "100", "100", "", "FM_WIDE", "", "", 47.11974, -122.56456, "2028-01-02"),
    ("4107", "K7AMF", "Cultas Mtn", 223.8600, 222.2600, "103.5", "", "", "FM_WIDE", "", "", 48.42446, -122.14335, "2031-07-28"),
    ("4070", "W7PIG", "Camano Island", 223.8800, 222.2800, "103.5", "103.5", "", "FM_WIDE", "", "", 48.22470, -122.49890, "2027-05-23"),
    ("4076", "WB7DOB", "Three Sisters", 223.9200, 222.3200, "103.5", "103.5", "", "FM_WIDE", "", "", 47.12000, -121.89000, "2027-07-02"),
    ("4094", "WA7TBP", "Carnation", 223.9600, 222.3600, "123", "123", "", "FM_WIDE", "", "", 47.63880, -121.94990, "2030-11-05"),
    ("4084", "W7AUX", "Shoreline", 224.0200, 222.4200, "103.5", "103.5", "", "FM_WIDE", "", "", 47.76000, -122.35000, "2027-05-14"),
    ("4015", "K7LED", "Tiger Mtn East", 224.1200, 222.5200, "103.5", "", "", "FM_WIDE", "", "", 47.48805, -121.94694, "2029-10-03"),
    ("4066", "W7EAT", "Graham", 224.1800, 222.5800, "103.5", "", "", "FM_WIDE", "", "", 47.02895, -122.29392, "2027-05-13"),
    ("4103", "W7SKY", "Sultan", 224.1800, 222.5800, "100", "100", "", "FM_WIDE", "", "", 47.88591, -121.79191, "2027-12-26"),
    ("4092", "W7TJL", "Gig Harbor", 224.2000, 222.6000, "123", "123", "", "FM_WIDE", "", "", 47.39370, -122.58654, "2030-06-12"),
    ("4069", "WA7FUS", "Lake Forest Park", 224.2200, 222.6200, "103.5", "103.5", "", "FM_WIDE", "", "", 47.77192, -122.28093, "2029-12-20"),
    ("4009", "NM7E", "Belfair", 224.2600, 222.6600, "103.5", "", "", "FM_WIDE", "", "", 47.38660, -122.86099, "2030-07-18"),
    ("4110", "N7IPB", "Haystack Mtn", 224.2800, 222.6800, "123", "123", "", "FM_WIDE", "", "", 47.80802, -121.72722, "2030-12-23"),
    ("4010", "K7NWS", "Tiger Mtn West", 224.3400, 222.7400, "110.9", "", "", "FM_WIDE", "", "", 47.50875, -121.98519, "2029-04-07"),
    ("4063", "WA7DEM", "Marysville", 224.3800, 222.7800, "103.5", "103.5", "", "FM_WIDE", "", "", 48.12000, -122.24000, "2027-02-12"),
    ("4085", "KF7BJI", "Cougar Mtn", 224.4400, 222.8400, "103.5", "103.5", "", "FM_WIDE", "", "", 47.54192, -122.10950, "2029-01-04"),
    ("4096", "WA7FUS", "Brier", 224.5200, 222.9200, "103.5", "103.5", "", "FM_WIDE", "", "", 47.80000, -122.27000, "2028-01-02"),
    ("4090", "W6AV", "Port Orchard", 224.6000, 223.0000, "100", "100", "", "FM_WIDE", "", "", 47.45847, -122.67204, "2029-06-20"),
    ("4029", "WW7MST", "Seattle", 224.6800, 223.0800, "103.5", "103.5", "", "FM_WIDE", "", "", 47.56271, -122.30839, "2031-08-26"),
    ("4012", "WB7DOB", "Baldi Mtn", 224.7600, 223.1600, "103.5", "103.5", "", "FM_WIDE", "", "", 47.21897, -121.84314, "2027-07-02"),
    # 33 cm
    ("6057", "WW7STR", "Cougar Mtn", 927.2125, 902.2125, "114.8", "114.8", "", "FM_NARROW P25_PHASE_1", "", "114", 47.54192, -122.10950, "2029-02-04"),
    ("6006", "K7CH", "South Mtn", 927.2500, 902.2500, "114.8", "114.8", "", "FM_NARROW", "", "", 47.32030, -122.33860, "2027-04-10"),
    ("6021", "K7TGU", "Ashford", 927.5250, 902.5250, "114.8", "114.8", "", "FM_WIDE", "", "", 46.83000, -122.02000, "2030-05-10"),
    ("6019", "K7OET", "Cultas Mtn", 927.5500, 902.5500, "114.8", "114.8", "", "FM_NARROW", "", "", 48.42000, -122.14000, "2031-07-28"),
    ("6009", "K7TGU", "University Place", 927.6000, 902.6000, "114.8", "114.8", "", "FM_NARROW P25_PHASE_1", "", "293", 47.22805, -122.55527, "2027-04-10"),
    ("6029", "W7AUX", "Shoreline", 927.6375, 902.6375, "114.8", "114.8", "", "FM_WIDE", "", "", 47.75619, -122.34575, "2029-11-08"),
    ("6059", "W7AAO", "Buckley", 927.8500, 902.8500, "114.8", "114.8", "", "FM_WIDE", "", "", 47.11670, -121.89250, "2030-10-30"),
    ("6060", "KF7ZBK", "Graham", 927.8750, 902.8750, "114.8", "114.8", "", "FM_WIDE", "", "", 47.04336, -122.27965, "2027-01-02"),
    # 23 cm
    ("6520", "N7IH", "Kirkland", 1290.2000, 1270.2000, "", "", "", "DSTAR_DV", "", "", 47.71194, -122.15583, "2026-12-04"),
    ("6518", "W7NPC", "Bainbridge Island", 1290.5000, 1270.5000, "", "", "", "DSTAR_DV", "", "", 47.65580, -122.54750, "2031-02-10"),
    ("6509", "N7FSP", "Baldi Mtn", 1292.3000, 1272.3000, "103.5", "", "", "FM_WIDE", "", "", 47.21890, -121.84319, "2027-02-19"),
)


def _raw(row: _Row) -> Dict[str, str]:
    (record, call, city, output, input_frequency, ctcss_in, ctcss_out, dcs, modes,
     color_code, nac, lat, lon, expires) = row
    raw = {
        "FC_RECORD_ID": record, "STATE": "WA", "CALL": call, "CITY": city,
        "OUTPUT_FREQ": f"{output:.4f}", "INPUT_FREQ": f"{input_frequency:.4f}",
        "CTCSS_IN": ctcss_in, "CTCSS_OUT": ctcss_out, "DCS_CDCSS": dcs,
        "DMR_COLOR_CODE": color_code, "P25_NAC": nac,
        "LATITUDE": f"{lat:.5f}", "LONGITUDE": f"{lon:.5f}", "EXPIRATION_DATE": expires,
    }
    raw.update({flag: "Y" for flag in modes.split()})
    return raw


def facts() -> List[NormalizedFact]:
    return [
        fact_from_row(_raw(row), source_updated=SNAPSHOT_DATE, retrieved_at=f"{SNAPSHOT_DATE}T00:00:00+00:00")
        for row in _ROWS
    ]


def favorite() -> FavoritesList:
    """The ``PSHAM02`` Favorites List."""
    fl = FavoritesList(
        id=stable_id("wwara-band-snapshot:PSHAM02", kind="favorites-list"),
        slug="psham02",
        favorite_key="PSHAM02",
        favorite_name="Puget Sound 6m, 1.25m, 33cm & 23cm Repeaters",
        region="Within 60 miles of Ames Lake / Redmond",
        counties="King, Snohomish, Pierce, Kitsap, Mason, Jefferson, Island, Skagit",
        scenario="Coordinated repeaters on the amateur bands the packaged catalog otherwise lacks",
        source_type="WWARA nightly coordination extract (checked-in snapshot)",
        system_or_category="Current WWARA voice coordinations on 6 m, 1.25 m, 33 cm and 23 cm",
        sites_or_coverage="60 miles of 47.6351 N, 121.9954 W; WWARA coordinates may be fuzzed",
        # Prose only: static_systems_for() reads any number here as a channel.
        departments_or_channels="Voice repeaters grouped by listening region and by band and mode",
        mode="FM/NFM + P25; one DMR machine on 1.25 m; D-STAR on 23 cm kept avoided",
        monitorability=(
            "Analog and P25 native on the SDS150, the only fleet radio that reaches 33 cm "
            "and 23 cm; 6 m on the FTX-1 and TH-D75; 1.25 m on the TD-H9 and TH-D75"
        ),
        upgrade_required="DMR upgrade for WA7DMR 223.800; D-STAR voice cannot be decoded by the SDS150",
        source_url=DATABASE_EXTRACT_URL,
        notes=(
            f"Snapshot of the WWARA extract dated {SNAPSHOT_DATE}, SHA-256 {SOURCE_SHA256}. "
            "A WWARA refresh (sources update) rebuilds PSHAM01 with these and every other "
            "coordination; radio plans select PSHAM01 first and keep the first of two identical memories."
        ),
        systems=[],
        provenance=[
            Provenance(
                source_adapter="wwara_snapshot",
                source_url=DATABASE_EXTRACT_URL,
                fetched_at=f"{SNAPSHOT_DATE}T00:00:00Z",
                confidence="verified",
            )
        ],
    )
    system = system_from_wwara_facts(fl, facts())
    # The refresh path names its ids after PSHAM01; give this list its own so
    # a refreshed PSHAM01 and this snapshot never share an id.
    system.id = stable_id("wwara-band-snapshot:system", kind="system")
    system.label = "WWARA Coordinated Repeaters, 6 m to 23 cm"
    for department in system.departments:
        department.id = stable_id(f"wwara-band-snapshot:{department.label}", kind="department")
        for channel in department.channels:
            channel.id = stable_id(f"wwara-band-snapshot:{channel.id}", kind="channel")
    fl.systems = [system]
    return fl
