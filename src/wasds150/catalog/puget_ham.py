"""Puget Sound amateur repeater monitoring intent and WWARA curation.

The committed row contains only a small set of repeater/net facts published by
their operators. The comprehensive repeater inventory is derived locally from
WWARA's nightly coordination extract, which is licensed for radio programming
but not republished wholesale by this repository.
"""
from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.sources.facts import NormalizedFact
from wasds150.util.hashing import stable_id

WWARA_URL = "https://www.wwara.org/DataBaseExtract.zip"
PSRG_NETS_URL = "https://web.psrg.org/net_schedule/"
PSRG_REPEATER_URL = "https://web.psrg.org/repeater-system/"
MIKE_KEY_URL = "https://mikeandkey.org/repeaters.php"
MIKE_KEY_NETS_URL = "https://mikeandkey.org/nets.php"
MASON_NETS_URL = "https://mc-arc.org/nets/"
ISLAND_REPEATER_URL = "https://www.w7avm.org/repeater-system"
#: How a WWARA channel's note records its coverage (the extract's LOCALE).
COVERAGE_NOTE = "coverage "
#: The system a WWARA refresh builds.
WWARA_SYSTEM_ID = stable_id("puget-ham:wwara-current", kind="system")

# Broad Puget Sound / eastern Olympic / Cascade-crest listening region.
#
# The east and south edges are drawn wide enough to contain a 75-mile radius
# from the Redmond / Union Hill area, so the I-90 (Cle Elum), US-2
# (Leavenworth) and Centralia corridors are inside the box. WWARA coordinates
# all of western Washington and every record is kept: one outside the box is
# filed by region (the Olympic coast, or Southwest & Coast for Grays Harbor,
# Pacific, Wahkiakum and Cowlitz). The per-plan ``within_miles`` filter does
# the real circular cut.
PUGET_BOUNDS = (46.5, 49.1, -123.7, -120.3)
_REGION_SPECS = {
    "Southwest & Coast": (46.55, -123.45, 90.0),
    "North Sound & Islands": (48.45, -122.55, 80.0),
    "Olympic & Kitsap": (47.75, -122.95, 90.0),
    "South Sound": (47.15, -122.65, 90.0),
    "Eastside & Cascades": (47.55, -121.95, 115.0),
    "Seattle Metro": (47.62, -122.33, 55.0),
}


def _ascii(value: str) -> str:
    return (value or "").encode("ascii", "replace").decode("ascii")


def _channel(
    label: str,
    frequency: float,
    tone: str,
    mode: str,
    notes: str,
    *,
    priority: bool = False,
    tx: Optional[float] = None,
) -> Channel:
    return Channel(
        id=stable_id(f"puget-ham:official:{label}:{frequency}", kind="channel"),
        label=label,
        freq_mhz=frequency,
        tx_freq_mhz=tx,
        mode=mode,
        tone=tone,
        service_type=13,
        priority=priority,
        notes=notes,
    )


def favorite() -> FavoritesList:
    net_channels = [
        _channel("WW7PSR Seattle 2m", 146.960, "TONE=C103.5", "FM",
                 "PSRG: daily 07:47 Boaters, 09:00/12:00/21:00 social; Mon 19:00 Seattle ACS and 19:30 PSRG", priority=True, tx=146.360),
        _channel("WW7PSR Seattle 6m", 52.870, "TONE=C103.5", "FM",
                 "PSRG 6m voter/AllStar; linked to 2m for Monday 19:00/19:30 nets", tx=51.170),
        _channel("WW7PSR Seattle DMR", 440.775, "ColorCode=2", "DMR",
                 "PSRG dedicated DMR repeater; paid DMR upgrade required", tx=445.775),
        _channel("PSRG Saturday Simplex Net", 146.560, "", "FM",
                 "Official PSRG weekly simplex voice net, Saturday 20:00 Pacific"),
        _channel("K7LED Mike & Key 2m", 146.820, "TONE=C103.5", "FM",
                 "Nightly 19:30 social except Wed technical; Wed 19:00 emergency; Thu 18:30 check-in", priority=True, tx=146.220),
        _channel("K7LED Mike & Key 1.25m", 224.120, "TONE=C103.5", "FM",
                 "Mike & Key informal net Sunday 19:00 Pacific", tx=222.520),
        _channel("Mason County ARC 2m", 146.720, "TONE=C103.5", "FM",
                 "MCARC weekly ragchew net Sunday 19:00 Pacific", priority=True, tx=146.120),
        _channel("W7AVM Oak Harbor", 146.8625, "TONE=C114.8", "NFM",
                 "Island County ARC north repeater; official site reports normal operation", tx=146.2625),
        _channel("W7AVM Clinton", 147.220, "TONE=C127.3", "FM",
                 "Island County ARC south repeater; RF-linked to Oak Harbor", tx=147.820),
        _channel("N7KN Greenbank", 441.425, "TONE=C110.9", "FM",
                 "Island County ARC; official page reports repeater operational, linking temporarily disabled",
                 tx=446.425),
        # --- researched 2026-09-12 from operator and club pages ---------------
        # Every row below names a club or operator source in the notes. Times
        # are Pacific. A repeater carrying several nets lists them together.
        _channel("W7DX Union Hill", 147.000, "TONE=C103.5", "FM",
                 "LWHC Health & Wellness Net daily 11:00; KC ARES/RACES backup for Sun 20:00",
                 priority=True, tx=146.400),
        _channel("N9VW Cougar Mtn", 443.325, "TONE=C103.5", "FM",
                 "LWHC Welcoming Net Tue 19:00; Louie Net Wed 19:00; Redmond ARES Sun 19:30",
                 priority=True, tx=448.325),
        _channel("WW7STR Cougar 2m", 147.080, "TONE=C103.5", "FM",
                 "KC ARES/RACES Sun 20:00; Puget Sound Digital Hams Mon 20:00; WWATS ATV Wed & Sat 20:00",
                 priority=True, tx=147.680),
        _channel("WW7STR Cougar 70cm", 441.550, "TONE=C103.5", "FM",
                 "Red Cross King County Net Tue 20:00 (SeaTac Repeater Assn)", tx=446.550),
        # WW7MST 443.550 carries the MST Weekly Net on Thursdays, but the
        # operator wants it with the other 70cm repeaters rather than in the
        # nets zone; the WWARA layer already programs it, note and all.
        _channel("KC7BAE E Tiger", 443.050, "TONE=C103.5", "FM",
                 "Issaquah / East Tiger Mtn; operator-supplied. No net schedule confirmed against "
                 "a club source - kept here because the operator uses it.",
                 priority=True, tx=448.050),
        _channel("W7ACS Magnolia", 443.475, "TONE=C141.3", "FM",
                 "Seattle ACS CW Sector Net Mon 18:30; frequency carried over from the prior calendar series",
                 tx=448.475),
        _channel("KE7GFZ Cougar Mtn", 441.825, "TONE=C103.5", "FM",
                 "SnoVARC check-in Thu 19:00 except 1st; Morning Round-Table rag chew Mon-Fri 08:00",
                 tx=446.825),
        _channel("K6RFK Woodinville", 147.340, "TONE=C100.0", "FM",
                 "Woodinville ARES/RACES Mon 19:00; Bothell ARES Thu 19:00", tx=147.940),
        _channel("WA7DEM Mtlk Terr", 443.725, "TONE=C156.7", "FM",
                 "NEMCo RACES Resource Net Sun 19:00; Edway Net Tue 19:00", tx=448.725),
        _channel("WA7DEM Granite Fl", 146.925, "TONE=C156.7", "FM",
                 "Snohomish County ACS OPS-2 Tue 09:30 and OPS-3 Tue 20:00; sources disagree on the tone, 156.7 per WA7DEM",
                 tx=146.325),
        _channel("WA7LAW Everett 2m", 147.180, "TONE=C103.5", "FM",
                 "Snohomish County Hams Club Sunday Evening Net 19:00", tx=147.780),
        _channel("K7BEL Bellevue", 441.100, "TONE=C156.7", "FM",
                 "Bellevue Communications Support Net Thu 20:00, except 2nd Thu which starts on 146.580 simplex",
                 tx=446.100),
        _channel("N7KGJ Squak Mtn", 444.525, "TONE=C103.5", "FM",
                 "Issaquah Citizen Corps Net Wed 19:00 except 1st Wed", tx=449.525),
        _channel("KF7NPL Mpl Valley", 147.260, "TONE=C103.5", "FM",
                 "Maple Valley ARES Tue 19:30 and Maple Valley ARC Tue 20:00", tx=147.860),
        _channel("N7ERP Cougar Mtn", 440.250, "TONE=C123.0", "FM",
                 "Eastside Fire & Rescue ARC net Sun 19:00", tx=445.250),
        _channel("W7SKY Sultan", 444.125, "TONE=C103.5", "FM",
                 "Sky Valley ARC weekly net Tue 19:30", tx=449.125),
        _channel("K7FDF Renton", 443.600, "TONE=C103.5", "FM",
                 "Renton Emergency Communication Service Net Thu 19:00", tx=448.600),
        _channel("W7MIR Mercer Is", 147.160, "TONE=C146.2", "FM",
                 "Mercer Island Radio Operators Net 2nd Thu 19:00", tx=147.760),
        _channel("NC7G SeaTac", 146.660, "TONE=C103.5", "FM",
                 "Highline ARC Net Tue 19:00", tx=146.060),
        _channel("W7AW West Seattle", 145.130, "TONE=C103.5", "FM",
                 "West Seattle ARC weekly net Mon 18:30", tx=144.530),
        # Named by the call WWARA coordinates the pair to; the club that runs
        # the net is in the note.
        _channel("N7RHE Kent", 147.320, "TONE=C103.5", "FM",
                 "Puget Sound Fire Communications Support Team (K7CST) Mon 19:00", tx=147.920),
        _channel("W7PSE Rattlesnake", 441.775, "TONE=C103.5", "FM",
                 "Puget Sound Energy ARG net Tue 12:30", tx=446.775),
        _channel("W7FLY Lynnwood", 443.925, "TONE=C100.0", "FM",
                 "Boeing Employees ARO North BEARONS Net Wed 19:00", tx=448.925),
        _channel("W7AUX Shoreline", 442.825, "TONE=C103.5", "FM",
                 "Shoreline ACS Net Mon 19:30", tx=447.825),
        _channel("W7VMI Vashon", 443.500, "TONE=C103.5", "FM",
                 "Vashon-Maury ARC ARES net Sun 19:30", tx=448.500),
        _channel("K7SYE Auburn", 147.240, "TONE=C123.0", "FM",
                 "Auburn Area Emergency Communications Team Sun 19:00", tx=147.840),
        _channel("KC7Z Gold Mtn", 146.620, "TONE=C103.5", "FM",
                 "Kitsap County ARC (WW7RA) Wed 19:00; Greater Kingston RC Tue 19:00 (clubs disagree on the day)",
                 tx=146.020),
        _channel("KD7WDG Silverdale", 145.425, "TONE=C88.5", "FM",
                 "Kitsap County Emergency Comms Sun 19:30; West Sound ARC 2m Tue 19:00", tx=144.825),
        _channel("W7NPC Bainbridge", 444.475, "TONE=C103.5", "FM",
                 "Bainbridge Amateur Hour / BEARS Net Tue 19:30", tx=449.475),
        _channel("W7DK Tacoma", 147.280, "TONE=C103.5", "FM",
                 "Radio Club of Tacoma 2 Meter Net Tue 19:30", tx=147.880),
        _channel("W7AAO Grass Mtn", 145.370, "TONE=C136.5", "FM",
                 "Pierce County ARES District Net Tue 19:00", tx=144.770),
        _channel("W7PIG Camano", 147.0125, "TONE=C127.3", "FM",
                 "Stanwood-Camano ARC general club net Mon about 20:10, after the simplex net",
                 tx=147.6125),
        _channel("SCARC Simplex Net", 147.570, "", "FM",
                 "Stanwood-Camano ARC ARES simplex net Mon 20:00"),
        _channel("Double Nickel Net", 146.550, "", "FM",
                 "Saturday 20:00 simplex net, listed by Kitsap County ARC"),
        _channel("BCS Simplex Start", 146.580, "", "FM",
                 "Bellevue Communications Support 2nd Thu 18:30 starts here before moving to K7BEL 441.100"),
    ]
    net_department = Department(
        id=stable_id("puget-ham:official-nets", kind="department"),
        label="Operator-Published Repeaters & Nets",
        channels=net_channels,
        lat=47.62,
        lon=-122.33,
        range_miles=120.0,
        shape="Circle",
    )
    net_system = System(
        id=stable_id("puget-ham:official-nets", kind="system"),
        label="Puget Sound Published Net Channels",
        departments=[net_department],
    )
    return FavoritesList(
        id=stable_id("puget-ham:PSHAM01", kind="favorites-list"),
        slug="psham01",
        favorite_key="PSHAM01",
        favorite_name="Puget Sound Ham Repeaters & Nets",
        region="Puget Sound / eastern Olympic Peninsula / western Cascades",
        counties="King, Snohomish, Pierce, Thurston, Kitsap, Mason, Jefferson, Clallam, Island, San Juan, Skagit, Whatcom",
        scenario="Amateur repeater coordination / linked systems / emergency and social nets",
        source_type="WWARA nightly coordination + operator-published net channels",
        system_or_category="All current Puget-region WWARA coordinated repeaters, grouped by region and mode",
        sites_or_coverage="Puget/Cascade bounding box 46.5-49.1 N, 123.7-120.3 W; broad location groups because WWARA coordinates may be fuzzed",
        departments_or_channels="Analog FM/NFM; linked analog; P25; DMR; unsupported D-Star/Fusion carriers avoided; official PSRG/Mike & Key/Mason/Island net channels",
        mode="FM/NFM + P25 + DMR; AUTO/avoided for unsupported D-Star/Fusion-only carriers",
        monitorability="Analog and P25 native; DMR requires paid upgrade; D-Star/Fusion voice unsupported",
        upgrade_required="DMR upgrade for DMR repeaters; D-Star/YSF cannot be decoded by SDS150",
        source_url=WWARA_URL,
        notes="Run sources update with WWARA to populate the full list. Net times are Pacific local time and may change; verify operator pages.",
        systems=[net_system],
        provenance=[
            Provenance(source_adapter="operator_pages", source_url=PSRG_NETS_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=PSRG_REPEATER_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=MIKE_KEY_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=MIKE_KEY_NETS_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=MASON_NETS_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=ISLAND_REPEATER_URL, confidence="verified"),
        ],
    )


def _wwara_located(fact: NormalizedFact) -> bool:
    return fact.source_id == "wwara" and fact.freq_mhz is not None and fact.lat is not None and fact.lon is not None


def _scanner_frequency(frequency: float) -> bool:
    return any(low <= frequency <= high for low, high in (
        (25.0, 512.0), (758.0, 824.0), (849.0, 869.0), (894.0, 960.0), (1240.0, 1300.0),
    ))


def _region(fact: NormalizedFact) -> str:
    south, north, west, east = PUGET_BOUNDS
    if fact.lon > east:
        return "Eastside & Cascades"
    if not (south <= fact.lat <= north and west <= fact.lon):
        return "Olympic & Kitsap" if fact.lat >= 47.6 else "Southwest & Coast"
    if fact.lat >= 48.10:
        return "North Sound & Islands"
    if fact.lon <= -122.75:
        return "Olympic & Kitsap"
    if fact.lat < 47.35:
        return "South Sound"
    if fact.lon >= -122.15:
        return "Eastside & Cascades"
    return "Seattle Metro"


def _mode_group(fact: NormalizedFact) -> str:
    raw = fact.raw if isinstance(fact.raw, dict) else {}
    linked = bool((raw.get("LINK") or "").strip())
    if (raw.get("LOCALE") or "").strip().upper() == "LINK":
        # A link between repeaters, not a machine anyone accesses: a scanner
        # may listen, and no transceiver plan selects this department.
        return "Link Frequencies"
    if fact.mode == "NXDN":
        return "NXDN Digital"
    if fact.mode == "DMR":
        return "DMR (Upgrade Required)"
    if fact.mode == "P25":
        return "P25 Digital"
    if fact.mode == "AUTO":
        digital = "/".join(name for name, field in (("D-Star", "DSTAR_DV"), ("Fusion", "FUSION")) if raw.get(field) == "Y")
        return f"Unsupported Digital - {digital or 'Other'}"
    if linked:
        return "Linked Analog"
    if fact.freq_mhz < 54:
        return "Analog 6 Meter"
    if fact.freq_mhz < 148:
        return "Analog 2 Meter"
    if fact.freq_mhz < 230:
        return "Analog 1.25 Meter"
    if fact.freq_mhz < 500:
        return "Analog 70 Centimeter"
    if fact.freq_mhz < 1000:
        return "Analog 33 Centimeter"
    return "Analog 23 Centimeter"


def coordination_expired(raw: Dict[str, str], today: Optional[datetime.date] = None) -> bool:
    """Has this repeater's WWARA coordination lapsed?

    WWARA has no "on the air" flag. The coordination expiry is the closest
    published proxy: a machine whose coordination has run out is usually off
    the air or unmaintained, because keeping it current is a condition of
    holding the pair. Roughly one in seven Washington entries is lapsed at any
    time, so ignoring the field means programming a meaningful number of dead
    channels.

    An unparseable or missing date is treated as **current**. Guessing that a
    malformed field means "dead" would silently drop live repeaters.
    """
    text = (raw.get("EXPIRATION_DATE") or "").strip()
    if not text:
        return False
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(text, fmt).date() < (
                today or datetime.date.today()
            )
        except ValueError:
            continue
    return False


def _fact_channel(fact: NormalizedFact) -> Channel:
    raw = fact.raw if isinstance(fact.raw, dict) else {}
    city = _ascii((raw.get("CITY") or "").strip())
    call = _ascii((raw.get("CALL") or fact.name or "Repeater").strip())
    offset = f"{fact.offset_mhz:+.4f} MHz" if fact.offset_mhz is not None else "offset unknown"
    modes = [label for label, field in (("FM", "FM_WIDE"), ("NFM", "FM_NARROW"), ("P25", "P25_PHASE_1"), ("DMR", "DMR"), ("NXDN", "NXDN_DIGITAL"), ("D-Star", "DSTAR_DV"), ("Fusion", "FUSION")) if raw.get(field) == "Y"]
    locale = _ascii((raw.get("LOCALE") or "").strip())
    details = [
        f"input {(raw.get('INPUT_FREQ') or '').strip()}", offset, "/".join(modes),
        f"RAN {fact.nxdn_ran}" if fact.mode == "NXDN" and fact.nxdn_ran is not None else "",
        (raw.get("LINK") or "").strip(), (raw.get("SPONSOR") or "").strip(), (raw.get("COMMENT") or "").strip(),
        # WWARA's coverage: wasds150.catalog.wwara_coverage files the machine
        # into the county or city list it names.
        f"{COVERAGE_NOTE}{locale}" if locale else "",
        "coordination pending" if raw.get("WWARA_LIST") == "pending" else "",
        fact.source_url,
    ]
    # WWARA publishes the repeater input and its access tone, which a scanner
    # ignores but a transceiver needs.  Record them structurally so a channel
    # plan never has to re-derive a shift from a band-plan convention.
    try:
        input_freq = float((raw.get("INPUT_FREQ") or "").strip())
    except (TypeError, ValueError):
        input_freq = None
    input_tone = (raw.get("CTCSS_IN") or "").strip()
    try:
        tx_tone = f"TONE=C{float(input_tone):g}" if input_tone else ""
    except ValueError:
        tx_tone = ""
    expired = coordination_expired(raw)
    if expired:
        details.append("coordination expired")
    link = locale.upper() == "LINK"
    label = f"{call} - {city}" if city else call
    return Channel(
        id=stable_id(f"puget-ham:wwara:{fact.entity_key}", kind="channel"),
        # The NXDN side of a dual-mode machine shares its FM memory's output.
        label=f"{label} NXDN" if fact.mode == "NXDN" else label,
        freq_mhz=fact.freq_mhz,
        mode=fact.mode or "AUTO",
        tone=fact.tone or "",
        service_type=13,
        # Avoided either because the radio cannot decode the mode, or because
        # the coordination has lapsed and the machine is probably not there.
        # Marking rather than dropping keeps the record visible for anyone
        # who wants to look, while keeping it out of a generated channel list.
        # A link frequency joins two repeaters; no radio should key on it.
        avoid=fact.mode == "AUTO" or expired or link,
        notes=_ascii("; ".join(value for value in details if value)),
        tx_freq_mhz=input_freq,
        tx_tone=tx_tone,
        # WWARA publishes a position per repeater. Keeping it on the channel
        # lets a plan ask "what can I work from here" rather than only "which
        # region is this in", and carries the precision caveat with it.
        lat=fact.lat,
        lon=fact.lon,
        location_precision=fact.location_precision or "",
        nxdn_ran=fact.nxdn_ran,
    )


def system_from_wwara_facts(favorite: FavoritesList, facts: Iterable[NormalizedFact]) -> Optional[System]:
    grouped: Dict[Tuple[str, str], List[Channel]] = defaultdict(list)
    seen = set()
    for fact in facts:
        if not _wwara_located(fact) or not _scanner_frequency(fact.freq_mhz):
            continue
        channel = _fact_channel(fact)
        key = (round(channel.freq_mhz, 6), channel.mode, channel.label.casefold())
        if key in seen:
            continue
        seen.add(key)
        grouped[(_region(fact), _mode_group(fact))].append(channel)
    if not grouped:
        return None

    departments = []
    for (region, mode_group), channels in sorted(grouped.items()):
        lat, lon, radius = _REGION_SPECS[region]
        departments.append(Department(
            id=stable_id(f"puget-ham:{region}:{mode_group}", kind="department"),
            label=f"{region} - {mode_group}",
            channels=sorted(channels, key=lambda channel: (channel.freq_mhz or 0, channel.label)),
            lat=lat,
            lon=lon,
            range_miles=radius,
            shape="Circle",
            avoid=mode_group.startswith("Unsupported Digital"),
        ))
    return System(
        id=WWARA_SYSTEM_ID,
        label="WWARA Current Puget Sound Coordinated Repeaters",
        departments=departments,
    )
