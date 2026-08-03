# Washington SDS150 Programming Checklist

Concise, step-by-step Sentinel build procedure. Pairs with `washington-sds150-favorites-master.md` (full reference) and `washington-sds150-favorites.csv` (machine-readable inventory). The Uniden SDS150 is a **handheld**, battery-powered, true I/Q trunk-tracking scanner with built-in GPS, an SMA antenna connector, and microSD storage.

---

## 1. Before You Start

- [ ] Install **Uniden Sentinel** (free, Windows) — https://uniden.com/products/sds150 . This is the only practical way to program a build of this size; front-panel entry does not scale past a handful of channels.
- [ ] Update Sentinel's integrated RadioReference database; this is free and does not require a RadioReference account. Premium is optional for direct RR downloads/APIs or compatible third-party programming software.
- [ ] Decide upgrades now (see Section 8) so you don't re-import systems twice.
- [ ] Update SDS150 firmware via Sentinel **before** any large database import — firmware updates can change GPS/location-control behavior.
- [ ] Verify the built-in GPS gets a fix (allow roughly 30–90 seconds for a cold start) before relying on location-gated systems.

## 2. Build Order (Sentinel)

Work in Sentinel on a local project file; only write to the scanner once each phase is verified.

1. **Phase 1 — Home core.** Update Sentinel's master database, create your home Favorites List (e.g., `09-KING-PS-PSERN`), browse the database tree, and use **Append to Favorites List** for your home county's trunked system. Never hand-type a large trunked system when the current database entry is available. Configure Department Quick Keys, group encrypted talkgroups into DQK 0, and add conventional fire/EMS backup channels.
2. **Phase 2 — Statewide skeleton.** Add WSP (SID 7971) and WSDOT (SID 10705) with sites filtered to your region; add WA SAR (155.160 suite), DNR Wildfire, NIFC cache, and NOAA Weather Radio — none of these use location control.
3. **Phase 3 — Regional expansion.** Add neighboring counties' trunked/conventional systems (see the master guide's Groups B–D) with Location Control enabled, radius per the decision tree in Section 2.6 of the master guide.
4. **Phase 4 — Special interest.** Aviation, marine, rail, military, amateur, GMRS/FRS/MURS/CB, business/utilities, hospitals — add per your actual interests from the master guide's Groups E–M.
5. **Phase 5 — Optimization.** Permanently avoid confirmed-encrypted talkgroups, set CTCSS/DCS tones on conventional systems, flag priority channels, configure recording per Section 5 of the master guide, and assign Startup Keys (Section 2.5).

## 3. Naming and Quick-Key Discipline

- Favorites List: `##-REGION-TIER-DESC` (e.g., `35-MTN-SAR-I90PASS`).
- System: `COUNTY/REGION_AGENCY_TYPE` (e.g., `KING_PSERN_P25II`).
- Department: `AGENCY-FUNCTION`, ≤16 characters; encrypted groups always prefixed `[E]-` and mapped to **DQK 0**.
- Follow the FLQK/SQK/DQK/Startup-Key numbering in the master guide (Section 2) so any list can be located from its key alone. Sharing one FLQK across related lists (e.g., a pass's SAR and fire lists) is expected — you do not need a live key for every list in the CSV inventory, only the ~15–25 you keep "hot" day to day.

## 4. Profiles and Travel Use (Startup Keys)

- [ ] Program Startup Keys 0–9 per the master guide's Section 2.5 (Home Default, I-90 East, US-2, I-5 South, North Cascades Loop, Olympic Peninsula, Eastern WA, SAR/Wildfire Response, Aviation/Military).
- [ ] Verify the exact SDS150 startup-key activation sequence against its current owner’s manual and firmware; the architecture follows the established SDS-series/Sentinel convention.
- [ ] Verify each profile at power-on: hold the digit key during boot until the display confirms the startup key, then confirm the expected FLQKs are armed.
- [ ] Keep one **MINIMAL/QUIET** profile (Startup Key 0, home FLQK only) for low-battery or low-priority situations.

## 5. GPS / Location Control Setup

- [ ] Location control is set **per system**, not per Favorites List.
- [ ] Leave location control **OFF** (always active) for: statewide SAR, DNR/NIFC wildfire, NOAA Weather, marine VHF, national interop (VTAC/VCALL/LERN/REDNET/CEMNET), and WSP/WSDOT (gate at the *site* level instead of the whole system).
- [ ] Turn location control **ON** with a 35–60 mile radius for county trunked/conventional systems outside your home county and for USFS/NPS conventional systems.
- [ ] Use a **tight 15–25 mile radius** for municipal city systems, local utilities, and Discovery-venue lists.
- [ ] Expect GPS dropout in tunnels, urban canyons, and dense forest — get a fix before entering a known dead zone (e.g., before a mountain pass) since the scanner holds last-known position during an outage.

## 6. Quick Keys — Verification Pass

- [ ] Every trunked system has all confirmed-encrypted talkgroups grouped under **DQK 0** and can be silenced with one keypress.
- [ ] No single system has more than ~8–10 active trunked sites in the live scan pass at once (use Location Control/site filtering to enforce this).
- [ ] FLQKs 0 and 99 remain reserved (all-off / debug-scratch) and are never left active in a production profile.

## 7. Service Types, Priority, and Recording

- [ ] **Priority (not Priority Plus)** is the default mode; flag Marine Ch16 (156.800), aviation Guard (121.5), SAR primary (155.160), and each active county's fire/EMS dispatch as Priority.
- [ ] Reserve **Priority Plus** for active-incident monitoring only (SAR callout, wildfire, major event) — never leave it on for routine scanning.
- [ ] Recording defaults: **ON** for fire/EMS dispatch, SAR channels, and event-specific channels; **OFF** for transit/public works, encrypted talkgroups, amateur/GMRS personal use, rail, and commercial DMR.
- [ ] Use **Global Avoid → Service Types** to suppress paging (POCSAG/FLEX) fleet-wide rather than locking out channels one at a time.
- [ ] Set CTCSS/DCS decode (not open squelch) on populated-area conventional systems; keep a duplicate CSQ entry for SAR/wildfire channels since incident radios may not carry your tone.

## 8. DMR / NXDN Decision

**Recommendation: buy both if you plan to monitor transit, EMS, or rail in Washington; DMR alone is a reasonable minimum.**

| Upgrade | Cost (one-time) | Unlocks in this guide | Verdict |
|---|---|---|---|
| **DMR digital upgrade** | ~$50–75 | Supported single-channel DMR, Tier II/III systems, Hytera XPT, PNWDigital, and commercial/industrial digital voice | **Recommended** — broadest payoff for the price |
| **NXDN 4800/9600** | ~$50–75 | AMR Seattle EMS dispatch, WTA (Whatcom) transit, Cowlitz County fire digital channels, YCSO ALS dispatch (Yakima) | **Recommended if you monitor EMS/fire** in King, Whatcom, Cowlitz, or Yakima counties; skip if purely rural-conventional focus elsewhere |
| **P25 Phase I & II** | Included | Nearly every Washington public-safety trunked system (PSERN, WSP, WSDOT, SREC, SS911, Sno911, CRESA, MACC 911, JBLM ACE LMR, etc.) | Already native — no purchase needed |
| **EDACS ProVoice digital voice** | ~$50–75 | Not needed for anything confirmed in this guide; analog EDACS trunking is already native | Skip unless you have a specific known ProVoice target |

Both upgrade keys are tied to your scanner's serial number and purchased/activated at my.uniden.com — buy once per unit, not per Favorites List.

## 9. Update Cadence

- [ ] **Quarterly:** Re-import every trunked system from RadioReference via Sentinel (site lists, talkgroups, and encryption flags change without notice).
- [ ] **Before any road trip:** re-verify the Startup Key profile you'll use and confirm GPS is functioning.
- [ ] **Annually:** re-check event-specific frequencies (Seafair, WA State Fair, airshows) — FCC temporary licenses are reissued yearly and channels can change.
- [ ] **After firmware updates:** re-test location-control behavior on at least one always-on and one gated system.
- [ ] **Ongoing:** move newly confirmed-encrypted talkgroups into DQK 0 and Avoid them; do not leave dead-air talkgroups in the active scan pass.

## 10. Testing

- [ ] After each build phase, time a full scan pass — target **under ~4 seconds** for the home profile and **under ~5 seconds** for any single active profile.
- [ ] Confirm at least one known-active fire/EMS talkgroup produces audio in each newly imported trunked system.
- [ ] Confirm encrypted talkgroups show carrier/ID with no audio (expected behavior, not a fault).
- [ ] Drive or walk a planned route once with the relevant Startup Key active to confirm GPS-gated systems activate and deactivate at the expected points (e.g., Snoqualmie Pass summit crossing).
- [ ] Verify NOAA Weather Alert / SAME triggers a test alert interrupt (NOAA broadcasts a weekly test tone; confirm your county FIPS code is set correctly).

## 11. Backup

- [ ] Keep the Sentinel project file (`.sns`/backup) in a version-controlled or dated folder — name it `WA-SDS150-[date]-[version]` per the master guide's Sentinel workflow notes.
- [ ] Export/save a copy immediately after every successful phase, before making further changes.
- [ ] Periodically back up the scanner's microSD card (recordings + config) separately from the Sentinel project file.

## 12. Discovery and Close Call

- [ ] Enable **Broadcast Screen** to suppress FM broadcast (88–108 MHz) and pager band (152–153 MHz) false positives.
- [ ] Use **Close Call** (VHF-Lo/VHF-Hi/UHF sub-bands, DND mode) for strong nearby unknowns at events, incidents, and unfamiliar venues.
- [ ] Use **Discovery Mode** for systematic sweeps: 150–174 MHz and 450–470 MHz at venues (malls/hospitals/stadiums/ski areas, 15–30 min, threshold 20–25 dB); 150–160 MHz along highways; 144–148 MHz and 440–450 MHz for new amateur repeaters (lock out 146.520/446.000 first); 118–136 MHz and 220–400 MHz (forced AM) for airshows/military events.
- [ ] Promote confirmed Discovery hits into a named Favorites List; cross-check any new amateur repeater against WWARA/RepeaterBook before trusting it.

---

**See also:** `washington-sds150-favorites-master.md` Section 1 for corrected hardware facts (handheld, built-in GPS, paid DMR/NXDN digital upgrades, AM aviation support) and honest limitations (encryption, RRDB drift, unpublished ICS-205/ski-patrol channels).
