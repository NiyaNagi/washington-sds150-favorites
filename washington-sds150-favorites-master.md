# Washington State Uniden SDS150 Favorites List Master Guide

Compiled from six research passes covering: SDS150 architecture and quick-key design; hobby/general-interest scenarios; mountain/outdoor/wilderness scenarios; air/marine/rail; eastern & central Washington public safety (20 counties); and western Washington public safety (19 counties). All 39 Washington counties are covered. This document consolidates, cross-checks, and corrects those six drafts into one usable reference. It is a planning and programming reference, not a certified frequency authority — see Section 1.3 for how to keep it current.

---

## 1. Scope, Corrections, and Limitations

### 1.1 What this guide covers
- Statewide interoperability, WSP, WSDOT, DNR wildfire, and federal (JIWN, NIFC) systems.
- All 39 counties' primary public-safety dispatch (trunked P25 where it exists, conventional VHF/UHF where it does not).
- Mountain/wilderness/SAR/wildfire monitoring by region (Olympics, Cascades, Rainier, Gorge, NE Highlands, Blue Mountains).
- Aviation (civil, military, ARTCC/FSS), marine/USCG/ferries, rail (BNSF/shortlines/transit), military ground/air.
- Amateur radio (repeaters, linked systems, ARES/RACES/ACS, satellites), GMRS/FRS/MURS/CB, business/industrial "color dot" and licensed channels, utilities/SCADA, hospitals/medevac, NOAA Weather Radio, and Discovery-only venues (schools, malls, stadiums, ski areas, events, news media, tow/road crews).

### 1.2 Corrections to source drafts
Two of the six source drafts contained hardware errors that are corrected throughout this guide:
- **The SDS150 is a handheld, battery-powered scanner**, not a desktop/base unit (one draft incorrectly called it "desktop/base"). It has an SMA antenna connector, built-in GPS for location-based scanning, and a microSD card for recording and firmware. Unlike the SDS100, it does not require an external GPS puck for normal location control. Do not conflate models when buying accessories (e.g., mag-mount antennas need an SMA adapter).
- **The SDS150 does receive the civil and military AM aviation bands** (108–137 MHz civil, 225–400 MHz military UHF) — one draft incorrectly claimed aviation reception was unsupported. Aviation, ARTCC, and FSS channels throughout this guide are fully receivable in AM mode.
- **DMR requires a paid upgrade**, contrary to one draft's claim that "DMR is included." P25 Phase I & Phase II are native; the **DMR digital upgrade** (covering supported single-channel DMR, XPT, and Tier III operation), **NXDN 4800/9600**, and **EDACS ProVoice digital voice** are separate paid upgrades. Analog EDACS trunking is native. Budget for DMR + NXDN together if you plan to monitor transit, utility, or rail systems that use them.
- Frequency coverage: 25–512 MHz, 758–824 MHz, 849–869 MHz, 894–960 MHz, and 1240–1300 MHz. No HF below 25 MHz; amateur HF nets and SSB are out of range regardless of upgrades.

### 1.3 Honest limitations — read before you build anything
- **Not exhaustive by design.** RadioReference (RRDB) is community-maintained; talkgroup lists, encryption flags, site lists, and frequencies change without notice. Every trunked-system entry below should be re-imported from RRDB via Sentinel, not hand-typed, and re-verified periodically (Section on update cadence in the checklist).
- **Encryption is a hard wall.** Nothing in this guide, and no legal consumer scanner, decodes AES-256/DES encrypted P25, DMR, or NXDN traffic. Where a category is marked "Encrypted," the scanner will show carrier activity with no audio — this is expected, not a malfunction.
- **Unpublished/dynamic content exists and cannot be pre-programmed.** Incident-specific ICS-205 wildfire frequencies, most ski-patrol operations channels, event-specific FCC temporary licenses, hospital/mall/school internal radio, and news-crew field channels are not published anywhere. These are called out as **Discovery targets** — use SDS150 Close Call/Discovery Mode on-site rather than expecting a pre-built channel list.
- **RadioReference Premium is optional for this build.** Sentinel's integrated weekly RadioReference database update and “Append to Favorites List” workflow do not require a RadioReference account. Premium is useful only for direct RR downloads, APIs, and compatible third-party programming software; some web-page details may also be subscriber-only.
- **Data-only signals cannot be decoded**: POCSAG/FLEX paging, SCADA/telemetry (4FSK, MDC-1200), AX.25/APRS packet, Winlink VHF packet, and SSB are all carrier-only hits with no intelligible audio — lock these out rather than leaving them in active scan lists.
- **Quality markers used throughout:** ✅ officially published/verified source, ⚠️ community/crowd-sourced (RadioReference, forums) — generally reliable but unverified by the licensee, 🚫 known not to be publicly published, 🔐 confirmed or likely encrypted.
- **Legal note (once, not repeated):** Passive scanner listening to unencrypted transmissions is broadly legal under federal ECPA and RCW 9.73.030; Washington requires all-party consent to *record and disseminate* private communications (not required merely to listen), and encrypted channels cannot legally or technically be decoded. Do not transmit outside your license class (GMRS/amateur/FRS/MURS/CB only, plus true emergencies under 47 CFR §97.403).

---

## 2. Deterministic Quick-Key Architecture

This numbering scheme is designed so any Favorites List, system, or department can be located from its name and quick key alone, without opening Sentinel. Not every Favorites List in Section 3 needs a live FLQK binding at once — home users typically keep ~15–25 FLQKs "hot" and leave the rest defined-but-unassigned (or sharing an FLQK with a related list) until traveled to. Sharing one FLQK across several related FLs (e.g., a mountain-pass FIRE list and SAR list under the same key) is expected and encouraged.

### 2.1 Naming convention
- **Favorites List:** `##-REGION-TIER-DESC` — e.g. `09-KING-PS-PSERN`, `35-MTN-SAR-I90PASS`, `75-WX-NOAA-STATEWIDE`.
- **System (within FL):** `COUNTY/REGION_AGENCY_TYPE` — e.g. `KING_PSERN_P25II`, `SPOKANE_SREC_P25I`, `NAT_NIFC_CONV`.
- **Department/Group (within system):** `AGENCY-FUNCTION`, ≤16 characters — e.g. `KCSO-PATROL`, `FIRE-DISPATCH`, `[E]-ENCRYPTED`.
- Encrypted talkgroups are always grouped into a dedicated department bucket prefixed `[E]-` so they can be avoided with one keypress instead of cluttering every scan pass.

### 2.2 Favorites List Quick Keys (FLQK 0–99) — master on/off per region
```
FLQK 0   RESERVED — all-off / safe mode
FLQK 1–8   Statewide/interop anchors (WSP, WSDOT, DNR, SAR, CEMNET, JIWN, NIFC, mutual aid) — see FL 1-8
FLQK 9–15  Western WA metro counties (King, Snohomish, Pierce, Clark/Skamania, Thurston/Mason, Kitsap/Jefferson)
FLQK 16–20 Western WA rural/conventional counties (Skagit/Island/San Juan, Whatcom, Clallam, SW-rural cluster)
FLQK 21–30 Eastern/Central WA counties (Spokane, Tri-Cities, Yakima/Kittitas, Wenatchee/Chelan-Douglas, Okanogan,
           Grant, NE Highlands, SE Washington, Klickitat, Adams/Lincoln)
FLQK 32–45 Mountain/wilderness/SAR/wildfire regions (Olympics through Gorge — see FL 32-45)
FLQK 46–51 Aviation (civil W/E, ARTCC/FSS, military air, JBLM LMR, satellites)
FLQK 52–55 Marine/USCG/Ferries/Ports/Medevac
FLQK 56–59 Rail and military ground
FLQK 60–64 Amateur radio (repeaters, linked systems, ARES/RACES/ACS, simplex, satellites)
FLQK 65–70 GMRS/FRS/MURS/CB, business/industrial, utilities, commercial DMR/NXDN
FLQK 71–74 Hospitals/medevac, Discovery venues (schools/malls/stadiums/ski/events/news/tow)
FLQK 75    NOAA Weather Radio (always-on; SAME alert priority)
FLQK 90–96 Travel/startup-key aggregator lists (see 2.5)
FLQK 99    DEBUG/scratch — never left active in production
```

### 2.3 System Quick Keys (SQK 0–99) — standard block, repeated per Favorites List
```
SQK 1  Primary local trunked system (PSERN/SS911/SREC/etc.)
SQK 2  Secondary/overlay trunked or transit system
SQK 3  County fire conventional
SQK 4  County EMS conventional
SQK 5  County law conventional (mutual aid / unencrypted remnants)
SQK 6  State system active in this region (WSP/WSDOT sites)
SQK 7  SAR / mountain rescue
SQK 8  Federal agency conventional (USFS/NPS/BLM/DNR)
SQK 9  Utilities/infrastructure
SQK 10 Interop/mutual aid cross-patch (VTAC/VCALL/REDNET/LERN)
SQK 11–20 Additional municipal/overlay systems
SQK 50 Monitoring-only/reference (low priority)
SQK 99 Avoided/parked systems (confirmed encrypted or defunct)
```

### 2.4 Department Quick Keys (DQK 0–9) — hardest constraint, apply to every trunked system
```
DQK 1  LAW (all unencrypted police/sheriff talkgroups)
DQK 2  FIRE-OPS (dispatch + fireground tactical)
DQK 3  EMS/MEDIC
DQK 4  COMMAND/EOC/tactical
DQK 5  TRANSIT/PUBLIC WORKS
DQK 6  INTEROP/MUTUAL AID
DQK 7  SPECIAL OPS (SWAT, marine unit, air ops)
DQK 8  UTILITIES/SUPPORT (hospitals, schools, utilities riding the system)
DQK 9  MONITORING/LOW PRIORITY
DQK 0  [E]-ENCRYPTED — group every confirmed-encrypted talkgroup here so one keypress silences them
```

### 2.5 Startup Keys (0–9) — travel profiles

Startup Keys are included here as a planning convention based on the SDS-series/Sentinel workflow. Verify the exact SDS150 power-on key sequence against the current owner’s manual and firmware before relying on it during travel.
```
0  MINIMAL/QUIET — home FLQKs only
1  HOME DEFAULT — home county + statewide anchors + NOAA
2  I-90 EAST (Seattle → Spokane) — home, WSP/WSDOT all sites, Kittitas, Grant, Spokane, SAR, rail
3  US-2 CORRIDOR (Everett → Wenatchee) — Snohomish, Chelan/Douglas, SAR, wildfire
4  I-5 SOUTH (Seattle → Vancouver WA) — Pierce, Thurston/Mason, Clark/Skamania, WSP/WSDOT
5  NORTH CASCADES LOOP (SR-20) — Whatcom/Skagit, Okanogan, SAR, wildfire, NOAA
6  OLYMPIC PENINSULA (US-101) — Kitsap/Jefferson, Clallam, SAR, marine
7  EASTERN WA (Spokane metro + rural east) — Spokane, NE Highlands, SE WA, WSP D4
8  SAR/WILDFIRE RESPONSE — all SAR/DNR/NIFC lists, no location gating
9  AVIATION/MILITARY MONITORING — all aviation + military FLs
```

### 2.6 GPS/location control decision tree
- **No location control (always active):** statewide SAR (155.160 suite), NIFC/DNR wildfire, WSP/WSDOT (system-wide; gate at the *site* level instead), NOAA Weather, marine VHF, national interop (VTAC/VCALL/LERN/REDNET/CEMNET), amateur simplex calling.
- **Location control ON, wide radius (35–60 mi):** county trunked systems outside your home county, USFS/NPS conventional systems, WSDOT regional site clusters, county fire/EMS conventional.
- **Location control ON, tight radius (15–25 mi):** municipal city systems, local utility/business channels, ski-area and event Discovery lists, local amateur repeaters.
- GPS fix takes 30–90 seconds cold; tunnels/canyons/dense forest cause dropout and the scanner holds last-known position — get a fix before entering a dead zone (e.g., before Snoqualmie Pass tunnels or deep valley trailheads).

---

## 3. Master Table of Favorites Lists

| FL | Name | Region / Counties | Scenario | Primary System(s) | Monitorability |
|----|------|--------------------|----------|--------------------|-----------------|
| 1 | WA SAR & Mutual Aid | Statewide | Public safety / SAR | 155.160 suite, LERN, FIRECOM/REDNET, OSCCR, HEAR | ✅ Full |
| 2 | WA 800MHz NPSPAC/STATEOPS | Statewide | Interop | ICALL/ITAC 1-4, STATEOPS 1-5 | ✅ Full |
| 3 | WA CEMNET/EM Nets | Statewide | Emergency mgmt | 45.20/45.36/45.48 MHz | ✅ Full (rare traffic) |
| 4 | WA State Patrol (WSP) | Statewide | Public safety | P25 II, SID 7971 | ✅ Dispatch mostly clear |
| 5 | WSDOT P25 | Statewide | Transportation | P25 II, SID 10705 | ✅ Full |
| 6 | WA DNR Wildfire | Statewide | Wildfire | Conventional VHF | ✅ Full |
| 7 | NIFC Federal Wildfire | Statewide (incident-deployed) | Wildfire | National cache conventional | ✅ Full (cache); 🚫 incident freqs |
| 8 | Justice IWN (Federal) | Statewide | Federal LE | P25 II, SID 3509 | 🔐 Mostly encrypted |
| 9 | Metro-King (PSERN) | King | Public safety | P25 II, SID 11628 | ✅ Fire/EMS/Transit; 🔐 Law |
| 10 | Metro-Snohomish (Sno911) | Snohomish | Public safety | P25 II, SID 13041 | ✅ Fire/EMS/SAR; 🔐 Law |
| 11 | Metro-Pierce (SS911/PSRS) | Pierce | Public safety | P25 II, SID 5480 / 8203 | ✅ Fire/EMS; 🔐 Law (trending) |
| 12 | SW-WA Clark/Skamania (CRESA) | Clark, Skamania | Public safety | P25 II, SID 9025 | ✅ Fire/EMS; 🔐 Law (100%) |
| 13 | Thurston/Mason (TCERN) | Thurston, Mason | Public safety | P25 II, SID 12945 + conv. | ✅ Fire/EMS (verify); 🔐 Law likely |
| 14 | Kitsap/Jefferson (Kitsap 911) | Kitsap, Jefferson | Public safety | P25 II, SID 13277 + conv. | ⚠️ Verify per-TG |
| 15 | Boeing / Port of Seattle P25 | King | Industrial/port | P25 I/II, SID 7665 / 11481 | ✅ Ops/maint; 🔐 security |
| 16 | NW-WA (Skagit/Island/San Juan) | Skagit, Island, San Juan | Public safety | Conventional | ✅ Full |
| 17 | Whatcom County | Whatcom | Public safety | Conventional + WTA NXDN SID 2704 | ✅ Full |
| 18 | Olympic Peninsula (Clallam) | Clallam | Public safety | Conventional | ✅ Full |
| 19 | SW-Rural (Lewis/GraysHarbor/Pacific/Wahkiakum/Cowlitz) | 5 counties | Public safety | Conventional + NXDN | ✅ Full |
| 20 | Spokane Regional (SREC) | Spokane | Public safety | P25 I, SID 6690 | ✅ Fire/EMS/Law disp.; 🔐 tac |
| 21 | Tri-Cities (Benton/Franklin) | Benton, Franklin | Public safety | P25 I, SID 6768 | ✅ Fire/EMS/Law; 🔐 Hanford |
| 22 | Yakima Valley (Yakima/Kittitas) | Yakima, Kittitas | Public safety | Conventional + NXDN migration | ✅ Mostly; ⚠️ NXDN ALS |
| 23 | Wenatchee/RiverCom (Chelan/Douglas) | Chelan, Douglas | Public safety | Conventional | ✅ Full |
| 24 | Okanogan County | Okanogan | Public safety | Conventional multi-zone | ✅ Full |
| 25 | Grant County (MACC 911) | Grant | Public safety | P25 I, SID 6979 | ✅ Fire/EMS; 🔐 Law |
| 26 | NE Highlands (Stevens/Pend Oreille/Ferry) | 3 counties | Public safety | Conventional + P25 digital | ✅ Full |
| 27 | SE Washington (WallaWalla/Columbia/Garfield/Asotin/Whitman) | 5 counties | Public safety | Conventional | ✅ Full |
| 28 | S-Central WA (Klickitat) | Klickitat | Public safety | Conventional | ✅ Full |
| 29 | Adams/Lincoln Counties | Adams, Lincoln | Public safety | Conventional + P25 digital | ✅ Full |
| 30 | Statewide E/C rollup (WSP D4/D6, WSDOT NC/SC, DNR, Mutual Aid) | E/C WA | Interop | See FL 4-6 | ✅ Full |
| 32 | Olympic Peninsula ONP+ONF | Clallam, Jefferson, Mason, Grays Harbor | Mountain/wildland | Conventional | ✅ Mostly |
| 33 | North Cascades/Mt Baker | Whatcom, Skagit, Snohomish | Mountain/wildland | Conventional + Sno911 | ✅ Mostly |
| 34 | Mountain Loop/US-2/Stevens Pass | Snohomish, King, Chelan | Mountain/wildland | Conventional + Sno911 | ✅ Mostly |
| 35 | I-90/Snoqualmie Pass/Alpine Lakes | King, Kittitas | Mountain/wildland | Conventional + PSERN | ✅ Mostly |
| 36 | Central Cascades/Enchantments/Wenatchee | Chelan, Kittitas | Mountain/wildland | Conventional + RiverCom | ✅ Mostly |
| 37 | Mount Rainier NP/Crystal Mountain | Pierce, Lewis, Yakima | Mountain/wildland | Conventional | ✅ Mostly |
| 38 | Goat Rocks/White Pass/US-12 | Yakima, Lewis | Mountain/wildland | Conventional | ✅ Mostly |
| 39 | Mt St Helens/Mt Adams/Gifford Pinchot | Skamania, Cowlitz, Klickitat | Mountain/wildland | Conventional | ✅ Mostly |
| 40 | Okanogan/Pasayten/Methow | Okanogan | Mountain/wildland | Conventional | ✅ Mostly |
| 41 | NE Highlands/Selkirks/Colville NF | Stevens, Pend Oreille, Ferry | Mountain/wildland | Conventional | ✅ Mostly |
| 42 | Blue Mountains/Umatilla NF/SE WA | Walla Walla, Columbia, Garfield, Asotin | Mountain/wildland | Conventional | ⚠️ Sparse data |
| 43 | Columbia Gorge/White Salmon/Klickitat | Klickitat, Skamania | Mountain/wildland | Conventional | ✅ Mostly |
| 44 | Rescue/SAR Aviation | Statewide | Aviation/SAR | Guard, SAR Air, Flight Following | ✅ Full |
| 45 | Ski Areas Statewide | 7 resorts | Discovery | Business VHF/UHF | 🚫 Unpublished — Discovery only |
| 46 | Civil Aviation — Western WA | King, Snohomish, Thurston, Whatcom, Clallam | Aviation | AM conventional | ✅ Full |
| 47 | Civil Aviation — Eastern WA | Spokane, Yakima, Franklin, Chelan, Whitman, Walla Walla | Aviation | AM conventional | ✅ Full |
| 48 | ARTCC Seattle Center (ZSE) & FSS | Statewide airspace | Aviation | AM conventional | ✅ Full |
| 49 | Military Aviation | Pierce, Island, Spokane | Aviation | AM/UHF conventional | ✅ Full |
| 50 | JBLM ACE LMR (Army P25) | Pierce, Yakima (YTC) | Military | P25 II, SID 8217 | 🔐 Partial |
| 51 | Amateur Satellites/ISS/ARISS | Statewide (overhead) | Amateur/hobby | FM conventional | ✅ Full |
| 52 | USCG & Marine VHF | Statewide waters | Marine | FM conventional + USCG P25 | ✅ Full; ⚠️ some CG P25 part-time enc. |
| 53 | WA State Ferries & Puget Sound VTS | Puget Sound | Marine | Conventional VHF | ✅ Full |
| 54 | Ports & Commercial Marine | King, Pierce | Marine/industrial | Conventional + Port of Seattle P25 | ✅ Mostly |
| 55 | Medevac & Rescue Aviation | Statewide | EMS/aviation | AM + P25 | ✅ Full where published |
| 56 | Rail — Western WA | 12+ counties | Rail | AAR conventional | ✅ Full |
| 57 | Rail — Eastern WA | 10+ counties | Rail | AAR conventional | ✅ Full |
| 58 | Transit Rail (Sound Transit/Sounder) | King, Snohomish, Pierce | Rail/transit | PSERN TGs + BNSF | ✅ Ops; 🔐 security |
| 59 | Military Ground (JBLM/Bangor/PSNS) | Pierce, Kitsap | Military | FM conventional | ✅ Mostly (some restricted) |
| 60 | WA Amateur Analog Repeaters | Statewide | Amateur | FM conventional | ✅ Full |
| 61 | Linked Amateur Systems (WIN/Evergreen/SRG/PNWDigital) | Statewide | Amateur | FM + DMR | ✅ FM; requires DMR upgrade for PNWDigital |
| 62 | ARES/RACES/ACS | Statewide | Amateur/EM | VHF/UHF (+HF out of range) | ✅ VHF/UHF portion |
| 63 | Simplex/Calling Frequencies | Statewide | Amateur | FM/SSB(n/a) | ✅ FM only |
| 64 | (reserved — merges with 51) | — | — | — | — |
| 65 | GMRS/FRS + NWAC Backcountry | Statewide | Outdoor/hobby | FM conventional | ✅ Full |
| 66 | MURS + CB | Statewide | Business/hobby | FM/AM conventional | ✅ Full (AM/SSB note) |
| 68 | Business/Industrial "Color Dot" | Statewide | Business | FM conventional | ✅ Full |
| 69 | Utilities & SCADA | Statewide | Utility | Conventional + MPT-1327 | ⚠️ Partial; SCADA undecoded |
| 70 | Commercial DMR/NXDN | King, Spokane, statewide | Commercial digital | DMR/NXDN | Requires paid upgrades |
| 71 | Hospitals & Medevac | Statewide | Medical | FM + NXDN + P25 | ✅ Mostly; NXDN needs upgrade |
| 72 | Schools/Malls/Stadiums | Statewide | Discovery | Business VHF/UHF | 🚫 Discovery only |
| 73 | Events (Seafair/Fairs/Airshows) | King, Pierce, Spokane | Discovery/event | FM/AM | ✅ Partial (licensed events) |
| 74 | News Media & Tow/Road Crews | Statewide | Discovery | FM/UHF + WSDOT conventional/P25 | ✅ WSDOT; 🚫 news/tow Discovery |
| 75 | NOAA Weather Radio | Statewide | Weather/SAME | WX conventional | ✅ Full |

---

## 4. Detailed Sections

### Group A — Statewide Interoperability & Core Systems (FL 1–8)

**FL 1 — WA SAR & Mutual Aid** (statewide; no location control)
Conventional VHF FM. Core channels: 155.160 (SAR-1, CSQ), 155.2425/155.3025/155.1675/155.1825 (SAR 2–5, PL 156.7), 155.370 (LERN), 153.830 (FIRECOM/REDNET), 156.135 (OSCCR, PL 203.5), 155.340 (HEAR), 154.280 (state fire tac). Departments: DQK1 SAR-primary, DQK2 interop/VTAC, DQK3 state-coord, DQK4 county-specific additions. Always-on priority channels. Source: WA Military Dept CEMP ESF-4 App.1 — https://mil.wa.gov/asset/610b02188b53e ; RadioReference WA Emergency Mgmt — https://www.radioreference.com/db/aid/6280

**FL 2 — WA 800MHz NPSPAC/STATEOPS** (statewide interop, program output freqs only)
ICALL 866.0125, ITAC1-4 866.5125/867.0125/867.5125/868.0125, STATEOPS1-5 867.5375/867.5625/867.5875/867.6125/867.6375 (all PL 156.7). Source: WA ESF-2 App.1 — https://mil.wa.gov/asset/610097d704789 ; WSDOT Region 43 800MHz Plan — https://www.wsdot.wa.gov/partners/region43//pdf/Region43-800MHz-Plan-PartB.pdf

**FL 3 — WA CEMNET/EM Nets** (statewide, low-band VHF — needs 25–50MHz capability, which SDS150 has)
45.200/45.360/45.480 (PL 127.3), 46.520 CMD, 46.000 RADEF (CSQ). Rarely active outside exercises/declared emergencies — always-on, no LC. Source: https://mil.wa.gov/asset/610097d704789

**FL 4 — WA State Patrol (WSP)** — P25 Phase II trunked, SID 7971, WACN BEE00, SysID 9CC. Districts: D1 Pierce/Olympia, D2 King (Seattle metro), D4 Spokane/Benton/Franklin/WallaWalla/Garfield/Columbia/Whitman/Adams/Lincoln, D6 Wenatchee/Chelan/Douglas/Grant/Kittitas/Okanogan, D7 Snohomish/Skagit/Whatcom, others statewide. **Sentinel action:** import the full system; filter sites to your travel region; enable district dispatch categories. Encryption: dispatch generally open; some tactical/car-to-car may be encrypted — verify per-TG. https://www.radioreference.com/db/sid/7971

**FL 5 — WSDOT P25** — P25 Phase II trunked, SID 10705, WACN C7D5A. Regions: NW (I-5 north/Puget Sound), SW (I-5 south/Vancouver), NC (mountain passes — Stevens/White/Snoqualmie), SC (SR-12/SR-14/Yakima). Also carries WA Dept. of Corrections transport and interop patches to WSF 151 MHz channels. **Sentinel action:** import full system, select regional talkgroup categories relevant to travel route; sites auto-affiliate. Encryption: generally open. https://www.radioreference.com/db/sid/10705

**FL 6 — WA DNR Wildfire** — Conventional VHF FM, statewide repeater network. Key: 159.420 (DNR Main/statewide tac, CSQ), 151.415 (DNR Common interop, PL 103.5), regional repeater outputs 159.4125/159.4275/159.240/159.330/159.375/159.3675/159.315/159.435/159.450/159.345 (PL varies by region), air-to-ground 151.310/151.340/151.385/151.2125/159.270/151.2875/156.0225. Seasonal — repeaters most active June–October. Official DNR Radio Channel Guide (Mar. 2024): https://dnr.wa.gov/sites/default/files/2025-03/rp_fire_radio_channel_guide.pdf ; Agreement: https://dnr.wa.gov/sites/default/files/2025-03/rp_fire_radio_agreement.pdf ; contact radio@dnr.wa.gov / 360-902-1480 for the cooperators' guide (🚫 not otherwise public).

**FL 7 — NIFC Federal Wildfire** — National interagency cache, conventional VHF, deployed to whichever WA incident is active. **168.625 Air Guard is mandatory to monitor near any aerial wildfire ops.** Command 1-9 (170.975/170.450/170.425/170.000/169.750/168.475/169.5375/170.0125), Air Tac 1-5 (166.6125/167.950/168.400/169.150/169.200), Flight Following 168.650, ICP 168.550, WA Region 6 project fire 170.125 (PL 146.2). Incident-specific ICS-205 assignments are **not published** — treat this list as the pre-loadable baseline and add ICS-205 channels as temporary/Priority entries once assigned at a briefing. Source: NIFC 2024 NIRSC User Guide — https://www.nifc.gov/sites/default/files/NIICD/docs/2024_NIRSC_User_Guide_Webview.pdf

**FL 8 — Justice Integrated Wireless Network (JIWN)** — Federal (FBI/HSI/ICE/CBP/US Marshals/FPS), P25 Phase II, SID 3509, WACN BEE0A. Sites across King, Pierce, Thurston, Skagit, Lewis, Spokane, Yakima, Benton, Adams counties. **Nearly all operational talkgroups are encrypted** — import for completeness/affiliate visibility only; do not expect audio. https://www.radioreference.com/db/sid/3509

### Group B — Western WA Metro Counties (FL 9–15)

**FL 9 — King County (PSERN)** — P25 Phase II, SID 11628, SysID 3AB, WACN BEE00. Multi-site simulcast (Seattle/Eastside core, NE King, Seattle perimeter, South King, Mercer Island, etc.) — import the whole system via Sentinel and let GPS auto-affiliate; do not hand-type control channels. Departments: Seattle Fire (SFD 1-6), Fire Tactical, NORCOM Fire (Bellevue/Redmond/Eastside), ValleyCom Fire (Auburn/Kent/Renton), Sound Transit (ops/admin mostly clear, security TG likely encrypted — see FL 58), KC Metro Transit (ops clear, PD encrypted), Public Works. 🔐 **All law enforcement — SPD, KCSO, every municipal PD — is encrypted on PSERN**; group in DQK 0 and avoid. Fire/EMS/transit-ops/public-works are clear and actively monitored. https://www.radioreference.com/db/sid/11628 ; Broadcastify calls: https://www.broadcastify.com/calls/tg/11628

**FL 10 — Snohomish County (Sno911)** — P25 Phase II, SID 13041, SysID 3AA. Sites: South Simulcast (Everett/Lynnwood), North Simulcast (Marysville/Arlington/Stanwood), Index, Skykomish, Darrington — pick sites by sub-area for tighter scan cycles. Fire dispatch by area (Everett, East County, North County) plus Fire Tac 1-3+ all clear. **Sheriff SAR talkgroup (TG 101) is explicitly unencrypted** — notable exception to the law-enforcement blackout. All other SO dispatch/tac and municipal PD encrypted. Interop IO-02 through IO-15 clear. https://www.radioreference.com/db/sid/13041

**FL 11 — Pierce County (South Sound 911 + PSRS)** — P25 Phase II, SID 5480 (SS911, sites: Tacoma/Orting/South/West-Seattle-border/Buckley) and SID 8203 (PSRS Tacoma/Puyallup). Fire/EMS dispatch (Central Pierce Fire & Rescue and district TGs) clear; PCSO dispatch mixed, tactical encrypted; Tacoma PD and Bonney Lake/Buckley PD encrypted. Import both SIDs — some agencies (Orting/Buckley PD dispatch on PCSO West TG 40107) appear on only one system. https://www.radioreference.com/db/sid/5480 ; https://www.radioreference.com/db/sid/8203

**FL 12 — Clark & Skamania Counties (CRESA 911)** — P25 Phase II, SID 9025, SysID 860. Sites include Washougal River, Rainier Hill, Cascade Locks, Nicolai Mtn, Speelyai, Skamania Mountain. Clark Co. Fire dispatch, Fire Ops 50-59, Camas-Washougal Fire Tac, REDNET, and AMR EMS dispatch are all clear. **100% of law enforcement (CCSO, Vancouver PD, all municipal PDs) is encrypted** — total LE blackout as of 2025. Skamania Co. also receives WSP and the Oregon State Radio Project (OR state agencies, border coverage). https://www.radioreference.com/db/sid/9025

**FL 13 — Thurston & Mason Counties (TCERN + conventional)** — P25 Phase II, SID 12945 (TCERN/TCOMM911), SysID AFD, sites North Thurston/South Thurston/SE County. Talkgroup-level encryption not fully confirmed in public sources — verify live on RRDB before assuming any TG is open; statewide trend is toward encrypted LE. Mason County has no trunked system; conventional key channels: Sheriff 460.225/460.5125, Fire District 5 dispatch 154.190, county fire 154.370, REDNET 153.830. https://www.radioreference.com/db/sid/12945 ; Mason: https://www.radioreference.com/db/browse/ctid/2980

**FL 14 — Kitsap & Jefferson Counties (Kitsap 911 + conventional)** — P25 Phase II, SID 13277, SysID C5F, WACN 92A97. Sites: Simulcast (Kitsap), Port Ludlow (N Jefferson/Hood Canal). Newer system (recent P25 cutover) — encryption breakdown not fully published; verify per-TG. Kitsap Transit uses a separate DMR Tier 3 system (generally unencrypted transit ops — requires DMR upgrade). Jefferson County has no countywide trunked network; key conventional: Sheriff/Port Townsend PD 453.575, Fire District 4 Brinnon 154.0925, Olympic Ambulance EMS 462.950. https://www.radioreference.com/db/sid/13277

**FL 15 — Boeing / Port of Seattle P25** (industrial, not public safety) — Boeing P25 Phase I, SID 7665, sites at Renton/Seattle/Auburn/Puyallup-Fredrickson/Sea-Tac/Everett; business/maintenance mostly clear, security likely encrypted. Port of Seattle P25 Phase II, SID 11481, covers airport/port police-fire-maintenance. https://www.radioreference.com/db/sid/7665 ; https://www.radioreference.com/db/sid/11481

### Group C — Western WA Rural/Conventional Counties (FL 16–19)

**FL 16 — Skagit / Island / San Juan (NW-WA conventional)** — No countywide trunked system in any of the three; JIWN and WSDOT P25 pass through. Skagit: Sheriff dispatch 155.8425 / dual-mode P25 453.400, Anacortes PD digital 453.950, fire dispatch 154.430/154.265, Fire Tac 3-9 (155.685/154.235/159.150/155.7675/153.785/155.6325). Island: Sheriff 453.050, Oak Harbor PD 460.575, fire paging 154.340 (NAS Whidbey military traffic separately encrypted/federal). San Juan: SJCSO dispatch 453.250, Orcas Fire Dist.2 154.205, San Juan Island Fire Dist.3 155.145/155.7975, Lopez Fire 155.100, EMS 155.280. All conventional, all unencrypted. https://www.radioreference.com/db/browse/ctid/2986 (Skagit) · /ctid/2972 (Island) · /ctid/2985 (San Juan)

**FL 17 — Whatcom County** — No single countywide P25 network as of the source date; primarily conventional VHF/UHF with partial digital overlay. Sheriff/Bellingham PD shared simulcast 453.325, Sheriff rural 155.610 (also simulcast-patched digitally at 453.925), Bellingham PD tac 154.025, countywide fire dispatch 154.430, Bellingham FD 453.2875. The legacy Bellingham/Whatcom LTR system (SID 2704) has migrated to **NXDN** and now serves Whatcom Transportation Authority (transit) only — requires the NXDN upgrade. Check ctid/2994/trs periodically for a new countywide trunked system. https://www.radioreference.com/db/browse/ctid/2994 ; https://www.radioreference.com/db/sid/2704

**FL 18 — Olympic Peninsula (Clallam County)** — No countywide trunked system. Sheriff/Forks PD/La Push PD West Dispatch 453.375, East Tac 453.275, Sequim PD 453.300, Port Angeles PD 460.100, Fire District 2 155.820, Sequim Fire 155.7825, Joyce Fire 154.445/155.7225, public works 158.940/155.925. All conventional and unencrypted. Wiztronics NXDN entries in this county are private/utility, not public safety. https://www.radioreference.com/db/browse/ctid/2962

**FL 19 — SW-Rural (Lewis / Grays Harbor / Pacific / Wahkiakum / Cowlitz)** — All five counties are predominantly conventional, no countywide P25. Lewis: Sheriff 155.625, Fire 154.190, Centralia PD 156.180, plus FleetNet/Silke NXDN (verify current assignment). Grays Harbor: Sheriff West/East 154.725/155.565, Fire Districts 1/3/10 154.190. Pacific: Sheriff North/South 460.075/460.225, Long Beach PD 159.210. Wahkiakum: Sheriff 150.8525 (analog) + 154.800 P25 NAC 293 tac, Fire/EMS 152.4125. Cowlitz: Sheriff 154.815 (shared w/ Woodland/Kalama/Castle Rock PD), Kelso PD 156.090, Longview PD 155.535, Fire dispatch 154.235 with NXDN-patched channels 154.3175/154.1825 (RAN 42), AMR EMS 155.325/155.220, HEAR 155.340. https://www.radioreference.com/db/browse/ctid/2978 (Lewis) · /ctid/2971 (Grays Harbor) · /ctid/2982 (Pacific) · /ctid/2992 (Wahkiakum) · /ctid/2965 (Cowlitz)

### Group D — Eastern/Central WA Counties (FL 20–30)

**FL 20 — Spokane Regional (SREC)** — P25 Phase I (Phase II capable), SID 6690, SysID 447, WACN BEE00. 11 sites (Simulcast, EWU, Tekoa, Williams Lake, Booth, Coe Road, Scoop, Hoodoo, Mt. Spokane, Upper Mica, Jail). Law dispatch (SPD North/South, SCSO North2/Valley1) open; law tactical/investigations encrypted. Fire dispatch/ops and mutual aid (SRMA 1-4) open. Also present in-county: Justice IWN (mostly encrypted), Spokane Transit Authority P25 (monitorable), WSP/WSDOT Spokane-area sites, Avista Utilities MPT-1327 (SDS150 cannot decode MPT-1327), Day Wireless DMR. Deprecated SID 8853 — do not use. https://www.radioreference.com/db/sid/6690

**FL 21 — Tri-Cities (Benton/Franklin)** — P25 Phase I, SID 6768, SysID 34A. Sites: Simulcast + Golgotha Butte IR. Fire dispatch/EMS (Med Ops 3/4/5) open; Med Ops 6 and Hanford/DOE encrypted. Sheriff dispatch open; warrant/tac channels verify per-TG. Energy Northwest (nuclear) expected encrypted. https://www.radioreference.com/db/sid/6768

**FL 22 — Yakima Valley (Yakima/Kittitas)** — No countywide trunked P25 for local agencies; conventional VHF with NXDN migration underway for YCSO (EMS ALS dispatch already NXDN48 RAN14 at 153.620). Yakima key channels: Upper/Lower Valley Fire dispatch 154.2575/155.0325, Sheriff (Little Bald/Bethel/Elephant/Eagle) 154.1375/155.730/156.000/155.535, AMR/ALS ambulance 155.220/155.400, Sunnyside PD 156.180. Kittitas key channels: Fire dispatch 154.205 (PL 151.4), Sheriff dispatch 155.5575/155.655/158.940, CWU Police 154.040. Both counties also carry Justice IWN (Sunnyside/Selah sites), WSDOT P25, and WSP D6. https://www.radioreference.com/db/browse/ctid/2996 (Yakima) · /ctid/2976 (Kittitas)

**FL 23 — Wenatchee/RiverCom (Chelan/Douglas)** — Consolidated dispatch (RiverCom 911), conventional VHF, no countywide P25. Fire 1/2 dispatch 154.430/155.685 (shared across both counties), tac colors Gold/Silver/Grey/Orange/Green (154.220/154.385/154.340/154.265/154.130), Chelan law dispatch 155.625, Douglas law dispatch 155.415. Also WSDOT P25 (Blag Mtn/Burch Mtn sites) and WSP D6. https://www.radioreference.com/db/browse/ctid/2961 (Chelan) · /ctid/2966 (Douglas)

**FL 24 — Okanogan County** — Conventional, four geographic sheriff zones: Omak/mid-valley 155.730, Oroville/Tonasket 155.640, Brewster/Pateros 156.240, Twisp/Winthrop 155.190; Sheriff Tac dual-mode analog/P25 at 153.7475 (enable digital decode). Main fire dispatch (OCFD) 154.415. Also WSDOT P25 (Aeneas Lookout/Bodie Mtn) and WSP D6. https://www.radioreference.com/db/browse/ctid/2981

**FL 25 — Grant County (MACC 911)** — P25 Phase I, SID 6979, SysID 29B, WACN 92768. Sites: Simulcast, Grant County, Vantage. All fire/EMS talkgroups open (Fire Emergency, Fire 1/2 Dispatch, North/South/East/West Tac 1, AMR EMS dispatch, EMS Common); **all law enforcement fully encrypted**. Also WSDOT P25 (Beezley Hill/Beverly-Mattawa) and Justice IWN. https://www.radioreference.com/db/sid/6979

**FL 26 — NE Highlands (Stevens/Pend Oreille/Ferry)** — Conventional, no countywide P25 for local agencies. Stevens: Sheriff dispatch 153.965 (dual analog/P25 NAC 200), fire north/south 154.400/154.415. Pend Oreille: Sheriff 155.3100 (analog) plus several P25-digital fire channels (154.7175/154.0325/154.0850/154.2350 — verify the unusual low-VHF Fire Tac 2 at 150.9950 against current RRDB). Ferry: Sheriff Dispatch A/B 156.090/155.250, Republic Fire 153.845. Data for Ferry County is comparatively sparse on RRDB — treat as ⚠️ lower confidence. https://www.radioreference.com/db/browse/ctid/2990 (Stevens) · /ctid/2983 (Pend Oreille) · /ctid/2967 (Ferry)

**FL 27 — SE Washington (Walla Walla/Columbia/Garfield/Asotin/Whitman)** — All five conventional, low encryption throughout. Walla Walla: Fire primary 154.430, Sheriff dispatch 155.250. Columbia: CCSO dispatch 155.145 (PL 67.0), CCFD3 dispatch 153.875. Garfield: GCSO dispatch 156.150 (dual analog/P25), GC Fire dispatch 156.180. Asotin: ACSO Ch.1 155.190, Clarkston PD 155.415. Whitman: WCSO North/West Law 154.785/154.8675, Pullman Fire/PD 154.145/155.640. Also WSDOT P25 (South Central) and WSP D4. https://www.radioreference.com/db/browse/ctid/2993 (WW) · /ctid/2964 (Columbia) · /ctid/2969 (Garfield) · /ctid/2959 (Asotin) · /ctid/2995 (Whitman)

**FL 28 — S-Central WA (Klickitat County)** — Conventional. Countywide fire dispatch 154.130 (PL 162.2), Fire Tac 1-3 154.070/154.355/154.400, SAR channel 154.1075 uses DCS-565 (program as digital code, not analog PL), Sheriff dispatch 153.845, Goldendale PD alt 154.025. https://www.radioreference.com/db/browse/ctid/2977

**FL 29 — Adams/Lincoln Counties** — Conventional with digital law dispatch. Adams: Fire dispatch 158.970, ACSO Law 1 (Ritzville) 158.760 P25 NAC 100, ACSO Law 2 (Othello) 158.805 P25 NAC 114, Othello PD 155.595 P25 NAC A21. Lincoln: Sheriff dispatch 156.030 (CSQ), Odessa PD 158.730/158.940, Fire East/West both at 154.205 MHz but different PL tones (151.4 vs 136.5 — CTCSS decode required to separate). https://www.radioreference.com/db/browse/ctid/2958 (Adams) · /ctid/2979 (Lincoln)

**FL 30 — Statewide E/C rollup** — Reuses FL 4 (WSP), FL 5 (WSDOT), FL 6 (DNR), and FL 1 (mutual aid/VTAC/VCALL/LERN/REDNET/OSCCR/HEAR) with eastern-WA site/talkgroup filters applied. Add these system-wide entries to every eastern-WA regional FL rather than duplicating full imports.

### Group E — Mountain / Outdoor / SAR / Wildfire Regional (FL 32–45)

These lists add trail-, pass-, and wilderness-specific USFS/NPS conventional channels and NOAA transmitters on top of the county dispatch systems already listed in Groups B–D. VHF (136–174 MHz) propagates furthest in WA mountain terrain via hilltop repeaters; 800 MHz trunked systems (PSERN, NPSPAC) have limited backcountry coverage and work best on major corridors.

| FL | Region | Key USFS/NPS conventional | County dispatch tie-in | NOAA WX | Notes |
|----|--------|---------------------------|------------------------|---------|-------|
| 32 | Olympic Peninsula (ONP/ONF) | ONP Main 168.525, ONP Maint 168.350, ONF West/East 164.825/164.800 | FL 18 (Clallam), Jefferson/Mason/Grays Harbor conv. | KXI27 Forks 162.425, KIH36 Neah Bay 162.550 | Air Guard 168.625 always |
| 33 | North Cascades/Mt Baker | MBSNF Mt Baker 169.925, Darrington 170.525, NOCA Common 168.6125/163.7125, NOCA LE 169.7250 | FL 17 (Whatcom), FL 10 (Sno911 SAR) | WNG604 Davis Peak 162.525, KAD93 Blaine 162.525 | Sno SAR 155.415 (PL 127.3) key mutual-aid channel |
| 34 | Mountain Loop/US-2/Stevens Pass | MBSNF Skykomish 169.575, Darrington 170.525 | FL 10 (Sno911) | WNG604 162.525 | Stevens Pass ski patrol freq 🚫 not published |
| 35 | I-90/Snoqualmie Pass/Alpine Lakes | MBSNF North Bend/Enumclaw 169.900 | FL 9 (PSERN — SAR TGs largely clear, law encrypted) | WXN21 Cle Elum 162.400 | King Co. SAR F-2/F-3 154.965/153.755, KC MARS 155.190; NWAC/SPART backcountry FRS Ch.7 (462.7125, CTCSS 71.9) legal party-to-party — https://nwac.us/backcountry-radio-channels/ |
| 36 | Central Cascades/Enchantments/Wenatchee | WenNF Main 171.500, Badger 173.050 | FL 23 (RiverCom) | WXM48 Wenatchee 162.475 | — |
| 37 | Mount Rainier NP/Crystal Mtn | MORA Main/LE 169.7250, Common1/2 168.6125/163.7125, Admin 163.0650 | FL 11 (Pierce), MBSNF Enumclaw 169.900 | WXN21 162.400, KHB49 Seattle 162.550, WXM62 Capitol Peak 162.475 | Site-switched repeater at Paradise/Tatoosh/Gobblers Knob/Crystal/Sunrise/Fremont/Tolmie; Crystal Mtn ski patrol 🚫 unpublished |
| 38 | Goat Rocks/White Pass/US-12 | GPNF North 171.425 | Yakima/Lewis conv. | KIG75 Yakima 162.550, WXM62 162.475 | White Pass ski area 🚫 unpublished |
| 39 | Mt St Helens/Mt Adams/Gifford Pinchot | GPNF West/MSH 172.225, East/Adams 172.325, North 171.425, digital link 406.425 (NAC 555) | FL 19 (Cowlitz), Skamania Sheriff 453.675/453.250, Fire 460.625 | WXK27 Portland-side 162.400, WZ2502 Randle 162.425 | USGS volcano telemetry is not on scannable voice — see https://volcanoes.usgs.gov |
| 40 | Okanogan/Pasayten/Methow | OkaNF Methow 172.350, regional 171.500 | FL 24 (Okanogan) | WWF49 Okanogan 162.525 | — |
| 41 | NE Highlands/Selkirks/Colville NF | ColNF East/West 171.475/170.550, Fire Tac 168.000, Central 172.375, Tonasket RD 170.475 | FL 26 (Stevens/PendOreille/Ferry) | KZZ73 Dayton 162.525, WXL86 Spokane 162.400 | — |
| 42 | Blue Mountains/Umatilla NF/SE WA | USFS R6 Pomeroy 164.825 (⚠️ unverified) | FL 27 (SE WA) | WWF56 Richland 162.450, WWH27 Plymouth 162.425 | Umatilla NF straddles OR/WA — some OR repeaters serve WA side; data sparse |
| 43 | Columbia Gorge/White Salmon/Klickitat | GPNF East 172.325 | FL 28 (Klickitat), Skamania Sheriff | WXK27 162.400, WWH27 162.425 | — |

All FL 32–43 entries share: Air Guard 168.625 (mandatory near aerial ops), statewide SAR 155.160, WA DNR Main 159.420, and NIFC ICP 168.550 during fire season — add these four to every mountain FL rather than repeating per row.

**FL 44 — Rescue/SAR Aviation** — 121.500 (GUARD, AM), 123.100 (SAR Air, AM), 156.800 (Marine-16, FM), 168.625 (USFS Air Guard, FM), 168.650 (Flight Following, FM), 155.340 (HEAR, FM). All statewide, no location control.

**FL 45 — Ski Areas Statewide (Discovery only)** — Crystal Mountain (Pierce), Stevens Pass (Chelan/King border), Snoqualmie Pass/Summit (Kittitas), White Pass (Yakima), Mt. Baker (Whatcom), 49° North (Spokane), Mission Ridge (Chelan). No resort has publicly documented ski-patrol frequencies (🚫 for all seven); expect private business VHF/UHF or DMR. Run Close Call/Discovery in 150–174 MHz and 450–470 MHz on-site December–April (active season only).

### Group F — Aviation (FL 46–51)

**FL 46 — Civil Aviation, Western WA** (AM mode) — Sea-Tac (KSEA): ATIS 118.0, Tower E/W 119.9/120.95, Ground 121.7, Approach/Departure spread 119.2–133.65, Guard 121.5. Boeing Field (KBFI): ATIS 126.0, Tower 118.3/120.6, Ground 121.9. Paine Field (KPAE): ATIS 132.95, Tower 120.2, Approach 128.5. Olympia (KOLM), Bellingham (KBLI), and uncontrolled fields (Skagit KBVS, Port Angeles KCLM, Friday Harbor KFHR, Arlington KAWO, Harvey S43, Kenmore S60, Lake Union W55) use CTAF/UNICOM (122.8 is the default uncontrolled CTAF for most small WA airports).

**FL 47 — Civil Aviation, Eastern WA** (AM mode) — Spokane Intl (KGEG): ATIS 124.325, Tower 118.3, Approach 123.75/133.35 (shared with Fairchild AFB). Yakima (KYKM), Tri-Cities/Pasco (KPSC), Wenatchee/Pangborn (KEAT), Pullman-Moscow (KPUW), Walla Walla (KALW) — all AM CTAF/tower per airport, Spokane Approach covers several as a shared TRACON.

**FL 48 — ARTCC Seattle Center (ZSE) & FSS** — Covers all of WA airspace, split into Areas A–D across many RCAG sites. Program the known set (119.1, 120.3, 124.85, 125.8, 126.1, 126.3 Mt.Vernon, 128.3, 128.5, 132.6 Yakima, 133.65, 269.35 UHF) — one will be active over your location at any time. FSS "Seattle Radio" 122.2 (universal call), Guard 121.5 (civil)/243.0 (military UHF).

**FL 49 — Military Aviation** — McChord/JBLM (KTCM): ATIS 109.6/270.1, Ground 118.175/279.65, Tower 124.8/259.3, Approach 126.5. NAS Whidbey (KNUW): ATIS 134.15, Tower 127.9, Approach 118.2/120.7 (EA-18G/EP-3E — expect heavy 225–400 MHz UHF traffic during workups). Fairchild AFB: shares Spokane Approach 123.75/133.35. Civil Air Patrol: 148.125 (Seattle primary FMN, PL 123.0; also P25 NAC 4CE), 148.150 (P25 NAC 4F9), Spokane squadron 148.125 (PL 136.5). Common nationwide military: Guard 243.0, SAR primary 282.8, Army Helo 242.4/242.5, USAF common 246.8/252.1/255.4/257.8.

**FL 50 — JBLM ACE LMR (Army P25)** — P25 Phase II trunked, SID 8217, SysID 98D, WACN BEE00. Sites: Davis Hill, Donovan Hill, Perimeter Road, Wescott Hills, Yakima Training Center (Cairn Hope Peak). **Sentinel action:** append the full system from Sentinel's updated database and add the relevant sites. Some web details may require RR Premium. Command/security likely encrypted; logistics/support/fire/range may be clear. Range control also reachable conventionally: 40.2/165.0875/173.5125 FM. https://www.radioreference.com/db/sid/8217

**FL 51 — Amateur Satellites/ISS/ARISS** — ISS voice/SSTV 145.800 FM, APRS downlink 145.825 FM (carrier-only, no AX.25 decode), cross-band repeater 437.800 FM (expect Doppler drift). FM satellites: SO-50 436.795 (most reliable), AO-91 145.960 (sunlight-only, degraded), TEVEL constellation 436.400. AO-92 (145.880) decommissioned — do not program. Use a pass-prediction app (Heavens-Above/AMSAT) for timing. https://www.ariss.org/current-status-of-iss-stations.html ; https://www.amsat.org/status/

### Group G — Marine (FL 52–55)

**FL 52 — USCG & Marine VHF** — Ch16/156.800 (distress, mandatory monitor), Ch13/156.650 (bridge-bridge), Ch22A/157.100 (USCG working), Ch5A/156.250 and Ch14/156.700 (Puget Sound VTS "Seattle Traffic," required for vessels >300GT), Ch6/156.300 and Ch67/156.375 (intership safety), Ch79A/156.975 and Ch78A/156.925 (WSF/port ops), Ch07A/156.350 (commercial/Foss tugs). USCG nationwide P25 nets (NAC 293) — full list at https://www.radioreference.com/db/aid/7760 ; import the whole "Coast Guard (United States)" agency via Sentinel. USCG aviation AM: 326.150/379.050/345.000/237.900. USCG Auxiliary: 143.475 (Yankee 3 nationwide simplex), 150.700 (WA repeater).

**FL 53 — WA State Ferries & Puget Sound VTS** — WSF deck/shore ops 151.040 FMN (not on standard marine handhelds — scanner-only), WSDOT V1/V2/V3 interop patches 151.070/151.025/156.120, plus Ch14/Ch16/Ch79A/Ch78A above. https://www.radioreference.com/db/aid/2299

**FL 54 — Ports & Commercial Marine** — Ch07A/Ch05A/Ch13/Ch16/Ch01A plus public telephone legacy channels 161.900/161.875. Port of Seattle P25 (SID 11481) covers police/fire/maintenance at port/airport facilities — see FL 15.

**FL 55 — Medevac & Rescue Aviation** — Airlift NW (UW/Harborview, statewide bases): 129.825 AM (air-to-ground/scene coordination), 155.295 P25 NAC 293 (dispatch, appears while airborne). USCG Air Station Port Angeles: 326.150/345.000 AM, Ch16 marine guard. General EMS interop: VMED28 155.340, MED-9 155.295, Life Flight Network 463.0375. Verify current entries in Sentinel/RRDB: https://www.radioreference.com/db/aid/11155

### Group H — Rail (FL 56–58)

**FL 56 — Rail, Western WA** — BNSF Seattle Sub (Seattle–Tacoma–Vancouver WA via Tukwila/Tenino): AAR 70/161.160, 87/161.415, 66/161.100, Balmer Yard hump 80/161.310, switching 36/160.650, Stacy Yard 60/161.010, MOW 54/160.920. BNSF Scenic Sub (Seattle/Everett–Wenatchee via Stevens Pass): AAR 70/76/66/54 as above. BNSF Bellingham Sub (Everett–Canadian border): AAR 76, Burlington Yard 70, Delta Yard 14/160.320. Sounder South rides Seattle Sub; Sounder North rides Bellingham Sub AAR76. All analog FMN; NXDN transition in progress for yard/MOW ops (upgrade needed if/when encountered).

**FL 57 — Rail, Eastern WA** — BNSF Stampede Sub (Auburn–Stampede Pass–Pasco): AAR 76 road, 54 MOW. Columbia River Sub (Wenatchee–Spokane via Latah Jct): AAR 66/70. Spokane Sub: AAR 76. Pasco Sub: AAR 70. Shortlines: Columbia Rail Group (Columbia-Walla Walla RR, Port of Royal Slope, Yakima Central RR) share two channels — 160.560/160.860 FMN (WRPX209). https://www.radioreference.com/db/aid/9298

**FL 58 — Transit Rail** — Sound Transit Link light rail rides PSERN talkgroups (Tunnel Ops, Mainline Ops 1/2, Maintenance, Fare Inspection — generally monitorable; Security and Security Emergency Button likely encrypted). Sounder commuter rail has no separate radio system — monitor the underlying BNSF AAR channels in FL 56 (Seattle Sub for South Line, Bellingham Sub for North Line).

### Group I — Military Ground (FL 59)

**FL 59 — Military Ground Ops** — JBLM Range Control 40.2/165.0875/173.5125 FM (150.0 PL on 41.1), Flight Following "Bullseye" 34.6 FM. Puget Sound Naval Shipyard (Bremerton) Police/Security/Fire 140.0 FMN (multi-dispatch). Naval Base Kitsap/Bangor: LC 20mi radius, largely federal/restricted. Sensitive operational traffic may be legal to receive but not to act on; much current military VHF/UHF traffic is encrypted P25 or frequency-hopping SINCGARS and will not decode regardless of upgrades.

### Group J — Amateur Radio (FL 60–64, 51)

**FL 60 — WA Amateur Analog Repeaters (curated statewide sample)** — Standard offsets: 2m −600kHz (some 147.xxx use +600kHz), 70cm +5MHz. Common PL tones: 100.0/103.5/107.2/114.8/127.3/136.5/141.3/156.7/167.9/173.8 Hz. Sample: 146.820/146.220 PL100.0 (Seattle, W7DK), 146.840/146.240 PL103.5 (Seattle/Bellevue Skywarn), 146.960/146.360 PL127.3 (Olympia ARES), 147.260/147.860 PL156.7 (Chelan/Naneum, Evergreen Intertie), 444.925/449.925 PL100.0 (Chinook Pass, WIN node), 145.170/144.570 PL114.8 (Liberty Lake/Spokane, IRLP/AllStar/EchoLink). Full directories: WWARA https://wwara.org/coordinations/ (west of Cascades), ERAC (east side), RepeaterBook https://www.repeaterbook.com/repeaters/Display_SS.php?state_id=53, RR Amateur https://www.radioreference.com/db/browse/stid/53/ham

**FL 61 — Linked Amateur Systems** — WIN System (Western Intertie Network): primary WA node 444.750/449.750 PL100.0 (Sequim, AllStar 1880), Chinook Pass node 444.925 (NM7R); https://winsystem.org/. Evergreen Intertie: WA/OR linked, anchored at Chelan/Naneum 147.260. SRG (Spokane Repeater Group): linked, eastern WA — RepeaterBook filter Spokane County. PNWDigital: PNW DMR linked network — **requires the paid DMR upgrade**; https://pnwdigital.net/repeaters-map/. EchoLink/IRLP/AllStar: program the local RF output frequency normally, no special scanner config — https://www.allstarlink.org/nodelist/

**FL 62 — ARES/RACES/ACS** — VHF/UHF simplex (in SDS150 range): 146.520 (national calling), 146.580 (common WA ARES/RACES/ACS), 146.505, 147.540, 145.510/145.650 (Eastside/King Co. tactical), 145.770 (Shoreline ACS), 446.000/445.000 (UHF calling/alternate). King County ARES full list: https://www.aresofkingcounty.org/resources/frequencies ; ETC (Eastside): https://etc-ares.org/. Winlink VHF gateways 144.950/145.630 (carrier-only, cannot decode packet — label "skip"). **HF nets (3.985/3.990/7.245/7.250 LSB) are below 25 MHz and out of SDS150 range** — document for a separate HF receiver, not the scanner.

**FL 63 — Simplex/Calling Frequencies** — 146.520 (2m national calling, most-monitored WA amateur freq), 446.000 (70cm national), 223.500 (1.25m national), 52.525 (6m national — worth a dedicated slot June–August for Sporadic-E). SSB calling frequencies (144.200, 432.100, 28.400) are out of scope — **the SDS150 does not demodulate SSB.**

### Group K — GMRS/FRS/MURS/CB & Business/Utilities (FL 65–70)

**FL 65 — GMRS/FRS + NWAC Backcountry** — FRS/GMRS shared channels 462.5500–462.7250 (Ch15-22) and 462.5625–462.7125 (Ch1-7 shared), FRS-only simplex Ch8-14 (467.5625-467.7125, 0.5W max), GMRS repeater inputs 467.5500-467.7250. NWAC/SPART Snoqualmie Pass backcountry safety program uses FRS Ch.7 (462.7125) with CTCSS tone 3 (71.9 Hz) — legal party-to-party transmit, not monitored by SAR/ski patrol: https://nwac.us/backcountry-radio-channels/. WA GMRS repeater directory: https://www.repeaterbook.com/gmrs/Display_SS.php?state_id=53

**FL 66 — MURS + CB** — MURS (no license): Ch1-3 (151.820/151.880/151.940) light use, Ch4 "Blue Dot" 154.570 and Ch5 "Green Dot" 154.600 — heaviest unlicensed VHF traffic in the US (retail/warehouse/construction). CB (no license, AM mode only — SDS150 cannot demodulate the SSB channels): Ch9/27.065 (emergency, monitor near highways), Ch19/27.185 (trucker highway — busiest US CB channel), Ch17/27.165 (alternate).

**FL 68 — Business/Industrial "Color Dot"** — Nationally shared itinerant channels, active daily statewide: 151.625 (Red Dot), 151.505/151.515/151.700/151.760, 154.570/154.600 (Blue/Green Dot — also MURS), 464.500 (Brown Dot), 464.550 (Yellow Dot), 467.7625/467.8125/467.850/467.875/467.900, 467.925 (Silver Star). Worth programming in every profile; expect heavy unrelated traffic in urban areas. https://wiki.radioreference.com/index.php/Common_Itinerant_and_Business

**FL 69 — Utilities & SCADA** — Seattle City Light 851.2875/851.5875/851.8625/852.3625 (conventional 800MHz FMN). Puget Sound Energy: mix of conventional and trunked MPT-1327 (**SDS150 cannot decode MPT-1327**) — verify per-district. SCADA/telemetry (pump stations, substations): data-only, no decodable audio — identify by data-noise signature during Discovery and lock out. FCC ULS search for local licensees: https://wireless.fcc.gov/uls/index.htm?job=home

**FL 70 — Commercial DMR/NXDN** — Both require paid SDS150 upgrades. King County Metro Transit DMR: 451.5125/451.6625/452.0875 (Atlantic Base + channels 2/4). AMR Seattle NXDN48: 152.3375 (Ch1 dispatch)/152.4425 (Ch2). Statewide search: https://digitalfrequencysearch.com/index.php (filter WA, DMR or NXDN); RR sort by system type at https://www.radioreference.com/db/browse/stid/53

### Group L — Hospitals/Medical & Discovery Venues (FL 71–74)

**FL 71 — Hospitals & Medevac** — HEAR (Hospital Emergency Admin Radio) 155.340 statewide hospital-to-EMS medical control, MED-1 463.000/468.000, MED-7 463.150/468.150, MED-9 163.000. County EMS/fire dispatch is location-dependent — see the county's FL in Groups B–D. AMR Seattle NXDN Ch1/Ch2 (152.3375/152.4425) needs the NXDN upgrade. Hospital internal ops (security, transport) are unpublished — Discovery target in 450–470 MHz on-campus.

**FL 72 — Schools/Malls/Stadiums (Discovery only)** — School districts: mostly MURS Ch4/5 or licensed VHF/UHF, district-specific — look up by district name in FCC ULS. Malls (Northgate, Bellevue Square, Tacoma Mall, Alderwood, Southcenter): on-site security typically 451-470 MHz licensed or itinerant dots; loss-prevention sometimes encrypted DMR. Stadiums (Lumen Field, T-Mobile Park, Climate Pledge Arena): event-leased frequencies, typically 451-469 MHz, vary per event — run Close Call in the parking-lot approach before programming anything.

**FL 73 — Events (Discovery + some verified)** — Seafair (Seattle, early August): FCC licensee WRYC378 verified — 451.4125/452.0125/452.6375/452.9750 + mobile 452.3750/456.4125/457.0125/457.1000/457.3375/457.3750/457.9750/461.6000/461.6250/461.7875/463.3000/463.3125. Blue Angels/USAF demo teams (AM): 237.800/251.600/284.250/346.500, Air Boss standard 123.150. WA State Fair (Puyallup): typical UHF 464.500/464.550/467.9375/467.850/462.7125/467.5625 (⚠️ may be NXDN/DMR); Pierce Co. public-safety context in FL 11. Spokane Interstate Fair: Spokane Co. fire mutual aid 153.935/154.010/154.055/154.220, Sheriff LERN 155.370. Verify current FCC licensee assignments each event year — event radio plans change annually.

**FL 74 — News Media & Tow/Road Crews** — News helicopters use civil aviation VHF (FL 46-48) plus informal air-to-air 123.025-123.075 AM. ENG/SNG field UHF is licensed per news org (450-451 MHz) — look up call signs (KOMO/KING/KIRO) in FCC ULS; microwave backhaul (1.6-2.5 GHz) is outside SDS150 range. Tow/road crews: WSDOT V1/V2/V3 conventional 151.070/151.025/156.120 (see FL 53), WSDOT P25 simplex digital channels 769.15625-774.84375 (8 channels, "Simplex 3"/769.91875 most used in SW WA — native P25, no upgrade needed), private tow companies are Discovery targets in 450-470 MHz.

### Group M — NOAA Weather Radio (FL 75)

**FL 75 — NOAA Weather Radio — complete WA catalog.** Program all applicable transmitters for your travel footprint and enable SAME by county FIPS code (WA counties are 53xxx, e.g., King 053033, Pierce 053053, Spokane 053063 — full list https://www.weather.gov/nwr/fips6). This is the one Favorites List that should always run with Weather Alert Priority enabled, interrupting any other scan activity.

| Callsign | Freq (MHz) | Site | Primary counties |
|----------|-----------|------|-------------------|
| KXI27 | 162.425 | Forks | Clallam, Jefferson (outer coast) |
| WNG604 | 162.525 | Davis Peak | Whatcom, Skagit, N. Cascades |
| KAD93 | 162.525 | Blaine area | Whatcom/I-5 north |
| KHB49 | 162.550 | Cougar Mtn (Issaquah) | King, Snohomish, Kitsap, Pierce |
| WXM62 | 162.475 | Capitol Peak | Thurston, Lewis, Mason, Grays Harbor |
| WXN21 | 162.400 | Cle Elum | Kittitas, SE King, SW Chelan |
| WXM48 | 162.475 | Wenatchee | Chelan, Douglas, N. Kittitas |
| KIG75 | 162.550 | Yakima | Yakima, parts of Kittitas/Benton |
| KIH36 | 162.550 | Neah Bay | Clallam outer coast |
| WWF49 | 162.525 | Okanogan | Okanogan |
| KEC83 | 162.550 | Spokane (Krell Hill) | Spokane, Lincoln, NE WA |
| KZZ73 | 162.525 | Dayton | Columbia, Walla Walla, Garfield |
| WXL86 | 162.400 | Spokane | Spokane, Adams, Whitman |
| WWF56 | 162.450 | Richland | Benton, Franklin, Yakima SE |
| WWH27 | 162.425 | Plymouth | Walla Walla, SE WA |
| WXK27 | 162.400 | Portland (West Hills) | Clark, Cowlitz, SW WA |
| WZ2502 | 162.425 | Randle | Lewis, Skamania, GPNF area |
| WWG24 | 162.425 | Puget Sound Marine | Marine forecasts/buoy data |

Full official listing: https://www.weather.gov/nwr/stations?State=WA

---

## 5. Avoid, Priority, and Recording Strategy

**Avoid (lockout) hierarchy:** temporary channel avoid (noisy/dead during a session — `L/O` key), temporary system avoid (skip a region — hold `L/O`), permanent channel avoid (confirmed-encrypted TG — set in Sentinel, name prefixed `[E]-`), permanent department avoid (entire `[E]` DQK bucket), permanent system avoid (defunct/offline system — keep the entry for reference, don't delete), global service-type avoid (e.g., turn off paging). Never permanently avoid an entire trunked system — new unencrypted talkgroups can appear; avoid at the talkgroup/department level instead.

**Priority:** flag Ch16 marine (156.800), 121.5 aviation guard, 155.160 SAR primary, each county's primary fire and EMS dispatch, and CEMNET Net 1 during declared emergencies. Do not priority-flag encrypted TGs, background monitoring channels (rail/amateur/utility), or high-volume transit/public-works TGs — they will dominate the scan. Reserve Priority Plus (interrupt-only-on-priority) for active-incident monitoring, not routine scanning.

**Recording:** default ON for fire/EMS dispatch (all counties), SAR channels, and event-specific channels. Default OFF for transit/public works (high volume, low value), encrypted TGs (would only record decode failures), amateur/GMRS personal use, rail, and commercial DMR. Archive and wipe the microSD card monthly; rename archives by date+event for retrieval.

---

## 6. Close Call & Discovery Strategy

Close Call is a background strong-signal detector (three sub-bands: VHF-Lo 25-88, VHF-Hi 108-174, UHF 216-512 MHz) that interrupts scanning for a nearby strong hit; enable Broadcast Screen to suppress FM broadcast (88-108) and pager band (152-153 MHz) false positives, and use DND mode so it only checks between scan stops. Discovery Mode sweeps a defined range and logs new signals for later review — use it for:
- **Venue sweeps** (malls/hospitals/stadiums/ski areas): 150-174 MHz and 450-470 MHz, threshold 20-25 dB, 15-30 min on-site, then promote confirmed voice channels to a venue Temporary Favorites List.
- **Highway sweeps**: 150-160 MHz for WSDOT/WSP/fire-EMS/tow; keep CB Ch19 (27.185) always-on separately.
- **Amateur repeater discovery**: 144-148 MHz and 440-450 MHz; lock out 146.520/446.000 first to avoid false-positive on your own monitoring; cross-check any find against WWARA/RepeaterBook.
- **Airshow/event military airband**: 118-136 MHz and 220-400 MHz, force AM mode.

---

## 7. Consolidated Limitations & Gaps

- **RR access:** Sentinel's weekly integrated database and Append-to-Favorites workflow are free. A paid RadioReference subscription is optional and is useful for direct CSV/XML/API downloads, compatible third-party software, and subscriber-only web details.
- **Deprecated/uncertain SIDs to double-check on live RRDB before importing:** old Spokane SREC SID 8853 (use 6690 instead); conflicting WSP SID citations (7971 is current); conflicting WSDOT SID citations (10705 is current, cross-check aid/2299).
- **Ski-patrol frequencies** for all seven major WA resorts (Crystal Mountain, Stevens Pass, Snoqualmie/Summit, White Pass, Mt. Baker, 49° North, Mission Ridge) are unpublished — Discovery-only.
- **Incident-specific ICS-205 wildfire assignments** are never public in advance — only the national NIFC cache baseline (FL 7) is programmable ahead of time.
- **DNR's detailed cooperators' channel guide** requires a direct request/MOU (radio@dnr.wa.gov) beyond the public PDF cited in FL 6.
- **Sparse/lower-confidence counties:** Ferry County and the Blue Mountains/Umatilla NF (WA side) have noticeably thinner published data than the rest of the state — treat FL 26 (Ferry portion) and FL 42 as ⚠️ lower confidence and verify locally.
- **Encryption status drifts over time** for every trunked system listed — Pierce, Thurston, and Kitsap in particular were noted mid-migration or with unconfirmed per-talkgroup encryption at research time; always re-check live RRDB before assuming a category is open.
- **Data-only modes** (SCADA, POCSAG/FLEX paging, APRS/AX.25, Winlink packet, MPT-1327, EDACS on some utility systems) cannot be decoded by the SDS150 regardless of upgrades and should be identified and locked out, not left in active scan lists.

---

## 8. Master Source URL Index

| Category | URL |
|---|---|
| RadioReference WA statewide | https://www.radioreference.com/db/browse/stid/53 |
| RadioReference WA trunked systems | https://www.radioreference.com/db/browse/stid/53/trs |
| RadioReference WA Amateur | https://www.radioreference.com/db/browse/stid/53/ham |
| WA Military Dept CEMP ESF-2 App.1 | https://mil.wa.gov/asset/610097d704789 |
| WA Military Dept CEMP ESF-4 App.1 | https://mil.wa.gov/asset/610b02188b53e |
| DNR Fire Radio Channel Guide | https://dnr.wa.gov/sites/default/files/2025-03/rp_fire_radio_channel_guide.pdf |
| DNR Radio Agreement | https://dnr.wa.gov/sites/default/files/2025-03/rp_fire_radio_agreement.pdf |
| NIFC 2024 NIRSC User Guide | https://www.nifc.gov/sites/default/files/NIICD/docs/2024_NIRSC_User_Guide_Webview.pdf |
| NOAA NWR WA stations | https://www.weather.gov/nwr/stations?State=WA |
| NOAA FIPS/SAME codes | https://www.weather.gov/nwr/fips6 |
| WSP P25 (SID 7971) | https://www.radioreference.com/db/sid/7971 |
| WSDOT P25 (SID 10705) | https://www.radioreference.com/db/sid/10705 |
| PSERN King Co. (SID 11628) | https://www.radioreference.com/db/sid/11628 |
| Sno911 (SID 13041) | https://www.radioreference.com/db/sid/13041 |
| South Sound 911 (SID 5480) | https://www.radioreference.com/db/sid/5480 |
| PSRS Tacoma/Puyallup (SID 8203) | https://www.radioreference.com/db/sid/8203 |
| CRESA 911 (SID 9025) | https://www.radioreference.com/db/sid/9025 |
| TCERN (SID 12945) | https://www.radioreference.com/db/sid/12945 |
| Kitsap 911 (SID 13277) | https://www.radioreference.com/db/sid/13277 |
| Spokane SREC (SID 6690) | https://www.radioreference.com/db/sid/6690 |
| Benton Co. 800 (SID 6768) | https://www.radioreference.com/db/sid/6768 |
| Grant Co. MACC 911 (SID 6979) | https://www.radioreference.com/db/sid/6979 |
| Justice IWN (SID 3509) | https://www.radioreference.com/db/sid/3509 |
| JBLM ACE LMR (SID 8217) | https://www.radioreference.com/db/sid/8217 |
| Boeing P25 (SID 7665) | https://www.radioreference.com/db/sid/7665 |
| Port of Seattle P25 (SID 11481) | https://www.radioreference.com/db/sid/11481 |
| Bellingham/Whatcom NXDN (SID 2704) | https://www.radioreference.com/db/sid/2704 |
| WA Mutual Aid (aid/2371) | https://www.radioreference.com/db/aid/2371 |
| WA Natural Resources/DNR (aid/2372) | https://www.radioreference.com/db/aid/2372 |
| WA Emergency Management (aid/6280) | https://www.radioreference.com/db/aid/6280 |
| WA Medevac (aid/11155) | https://www.radioreference.com/db/aid/11155 |
| WA Transportation/WSF (aid/2299) | https://www.radioreference.com/db/aid/2299 |
| WA Fish & Wildlife (aid/8885) | https://www.radioreference.com/db/aid/8885 |
| WA State Parks (aid/5583) | https://www.radioreference.com/db/aid/5583 |
| WA Corrections (aid/6276) | https://www.radioreference.com/db/aid/6276 |
| US Coast Guard nationwide (aid/7760, aid/8663) | https://www.radioreference.com/db/aid/7760 |
| Seattle ARTCC/ZSE (aid/2235) | https://www.radioreference.com/db/aid/2235 |
| WA Railroads (aid/9298) | https://www.radioreference.com/db/aid/9298 |
| Common Itinerant/Business Wiki | https://wiki.radioreference.com/index.php/Common_Itinerant_and_Business |
| Digital Frequency Search (DMR/NXDN) | https://digitalfrequencysearch.com/index.php |
| WWARA coordinations | https://wwara.org/coordinations/ |
| RepeaterBook WA | https://www.repeaterbook.com/repeaters/Display_SS.php?state_id=53 |
| RepeaterBook WA GMRS | https://www.repeaterbook.com/gmrs/Display_SS.php?state_id=53 |
| WIN System | https://winsystem.org/ |
| PNWDigital DMR | https://pnwdigital.net/repeaters-map/ |
| AllStarLink node list | https://www.allstarlink.org/nodelist/ |
| WA ARES/RACES | https://www.wastateares.org |
| King County ARES frequencies | https://www.aresofkingcounty.org/resources/frequencies |
| NWAC backcountry radio program | https://nwac.us/backcountry-radio-channels/ |
| ARISS ISS status | https://www.ariss.org/current-status-of-iss-stations.html |
| AMSAT FM satellite status | https://www.amsat.org/status/ |
| FCC ULS search | https://wireless.fcc.gov/uls/index.htm?job=home |
| Seafair FCC licensee (WRYC378) | https://www.radioreference.com/db/fcc/callsign/WRYC378 |
| RCW 9.73.030 (WA privacy law) | https://app.leg.wa.gov/rcw/default.aspx?cite=9.73.030 |
| Uniden SDS150 product page | https://uniden.com/products/sds150 |
| USGS volcano monitoring | https://volcanoes.usgs.gov |
| Broadcastify Calls (PSERN) | https://www.broadcastify.com/calls/tg/11628 |

*Every county-specific RadioReference `ctid` URL used above is also listed inline in its Group B/C/D section; consult the live RRDB page directly (not this document) before finalizing Sentinel imports, since site lists, talkgroups, and encryption flags change over time.*
