# Open items

What is still unfinished across the radio fleet, grouped by what it takes to
close. Updated 2026-09-13, after the zone/scan-list rework, the DMR network
corrections and the SDS150 Near Me fixes. Everything not listed here is done
and tested.

## Needs a decision

| Item | Detail |
|---|---|
| Keep or retire the legacy plans | `h9-ozette`, `ftx1-wa`, `ftx1-local`, `ftx1-scan`, `thd75-ames-lake`, `thd75-scan` and `atd890-scan` predate the fleet template. The update wizard loads the `<radio>-fleet` plans instead. The legacy exports in `radio-data/shared/legacy-plans/` were regenerated on 2026-09-10, so they are current, but nothing refreshes them automatically. Either keep them as alternatives (re-run the commands in [radio-data/shared/legacy-plans/README.md](../radio-data/shared/legacy-plans/README.md) after each refresh) or retire them and let the fleet plans stand alone. Their slot counts are pinned in `tests/test_fleet_template.py` (`LEGACY_SLOTS`). |
| `radio-data/shared/legacy-plans/` provenance statement | [radio-data/shared/legacy-plans/README.md](../radio-data/shared/legacy-plans/README.md) says the committed files are built only from data committed to this repository. They are regenerated from the working home, whose catalog also holds the refreshed WWARA, IACC, NOAA and FCC data (RadioReference rows are excluded from the Anytone bundle, and the other plans do not select them). Review that paragraph against [NOTICE.md](../NOTICE.md) before making the repository public. |
| Sentinel profile | `sds150.sentinel_profile` is set to `Preset`, the only profile in the Sentinel workspace. If the scanner's lists live in another profile, change it on the Fleet tab before the first update with **Write to the radios** ticked. |
| Statewide SAR and interop at home | Seven Upper Lena trip-list channels (WA SAR 155.160, OSCCR 156.135, NIFC Air Guard 168.625, ONP Main, Command 7/8, USCG Air 2) stopped scanning at home when Near Me stopped merging stations whose fences merely touch; they only ever reached Ames Lake through that trip list's 85-mile fence. If statewide SAR/interop calling channels should be heard everywhere, place them "anywhere" as the ham calling frequencies are (`_placement` in `src/wasds150/radios/near_me.py`). |

## Needs the radio on the bench

| Item | Detail |
|---|---|
| TD-H9 programming port | `td-h9.com_port` is not set. Plug in the programming cable, find its port in Device Manager (a Prolific USB-to-Serial entry), and enter it on the Fleet tab. COM3 is an unrelated device. |
| AT-D890UV read-back of the new layout | The profile was verified on 2026-09-12 against the earlier layout. The bundle has since changed shape (Near Me zone of copies, one list per zone, Far zones, West Tiger added and the stale 442.075 rows removed): after the next write, read back and Export All into `radio-data\at-d890uv\readbacks\<date>-readback\` and let the compare step diff it. Confirm Digital Monitor reads back on (`DigiMoni`), which the 2026-09-12 read-back showed off. |
| AT-D890UV contact list format | The digital contact CSV's header and file name are unconfirmed (`CONTACT_FORMAT_VERIFIED=False` in `src/wasds150/export/atd890_contacts.py`). Export one from the CPS and compare. |
| AT-D890UV NXDN columns | NXDN channels put the RAN in the `EnRan`/`DeRan` columns, which has not been checked against a CPS export. |
| AT-D890UV Optional Settings template | Capture two CPS **Export All** folders (a fresh codeplug and your configured one) and run `scripts/radios/build_atd890_settings_template.py`, so the export can carry your hotkeys and settings. Then set `at-d890uv.rdt_base` to the saved `.rdt`. |
| FTX-1 profile | Built from documentation and never written to a radio. RT Systems will not send until it has read the radio once, so read first and keep that as `radio-data\ftx1\backups\` (none exists yet). After the first load, check a few memories against the export report. |
| FTX-1 MEM Group | `M-Grp` (bit 1 of record byte 0x00, decoded from a probe on 2026-09-13) is ticked on the 70 Near Me memories. What Set Menu `55: MEM Group` does with it on the radio - scan only the flagged memories, or merely display them apart - is not yet known; check it and record the answer in `docs/scan-groups.md`. |
| SDS150 scanner profile | The installer never writes `profile.cfg`. The Preset profile had Aircraft, Business, Railroad, Other, Interop, Federal and Military service types off (muting Near Me Air, Business & GMRS and most of Rail & Marine), `ScanHpdb` on, no SAME code, and Close Call and weather-alert priority off. Set them in Sentinel or on the scanner (the fleet checklist's "Set the scanner profile" step), then confirm on the scanner. |
| ID-52A CSV layout | The columns and defaults in `src/wasds150/export/id52_csv.py` come from Icom's documentation and real ID-52 CSV files, not from a file CS-52 itself wrote. The installer is downloaded (`Cs52_ver123.zip`); install it, import one memory group and the repeater list, then export a group back out and diff the two. Until that is done the profile stays `verified=False`. |
| ID-52A first write | The radio has not been written from this project. Read the radio into CS-52 first so the call sign, GPS and APRS settings survive, and check a few memories and a DR entry afterwards. |
| TH-D75 tracked image | `radio-data/th-d75/reference/current/thd75-current.d75` and its power-on bitmap still carry the earlier callsign KM7HKM. Replace them after the next write and read-back. |
| GMRS repeater tones | The 17 repeaters in `GMRS01` (`src/wasds150/catalog/gmrs_repeaters.py`) were added by hand, and their access tones are not yet confirmed on the air. Key each one up and fix any that do not open. Auburn (WRBQ486, 254.1) and Gig Harbor (WRPR468, 173.8, possibly 141.3) are the doubtful ones. |

## Radio audit: reprogram and review

`wasds150 --home .wasds150-home fleet audit` reports **0 errors** on every
radio as of 2026-09-13; the full list is in
`radio-data\shared\checklists\radio-audit-2026-09-13.md`. The warnings below
need a human, not a code change.

| Item | Detail |
|---|---|
| TH-D75 on the radio | The image written on 2026-09-11 has about 22 amateur memories programmed receive only with the out-of-band split - 443.050 (slot 943, then named N7MTC Bremerton) among them - so PTT beeps. Write the current export (`docs/guides/th-d75.md`); every other radio should be rewritten from its current export too. |
| Lapsed coordinations | WWARA lists these as expired: W7PSE 441.700 Baldi Mtn, 441.725 Anacortes, 441.775 North Bend, 443.625 Sumner (2024-08-17); K7FDF Renton 443.600 (2026-06-05); W7SKY Sultan 444.125 (2026-07-11); W6MPD Port Angeles 224.060 (2026-01-21); WA7FW Federal Way 443.850 (2026-08-30). Key each up; drop any that no longer answer. W7PSE North Bend, K7FDF and W7SKY carry scheduled nets. |
| Seattle ACS tones WWARA does not confirm | V42 SARRTL 145.110 (127.3), V71 Lynwood 146.780 (DCS 172), V73 Kitsap 145.430 (88.5), V78 Kittitas 147.360 (131.8), V84 Stampede 147.360 (141.3), V85 Ellensburg 146.720 (131.8). Most are east of the Cascades, outside WWARA's area, where the pair belongs to another machine. Check each against the current Seattle ACS channel plan; a confirmed wrong tone goes in `ANALOG_TONES` (`src/wasds150/recipes/dmr_corrections.py`), as U71 Mountlake did. |
| RadioReference rows WWARA contradicts | KC7VCR Wenatchee Mtn 444.450 (same pair and tone as KD7HTE Baw Faw - fine if it is the eastern machine); W7UDI Whiskey Dick 441.750 with a 446.775 input (WWARA: W7PSE on 446.750); Myrtle Reservoir 6 m 53.290 at 103.5 (WWARA: W7AW, access tone 100, output tone 103.5); Evergreen Intertie 147.260 (156.7) and Upper Kittitas Co 147.160 (131.8), both eastern. These come from your RadioReference export, so they are fixed there or accepted. |
| KC7BAE NXDN group ID | WWARA's pending record for 443.050 publishes NXDN on RAN 5 but no group ID, so the AT-D890UV's Ham NXDN memory is receive only (the NXDN radio ID 16240 is set). Ask KC7BAE which group the machine uses; with it the memory can transmit. |
| Anytone DMR rows with no talkgroup | Removed 2026-09-13: amateur DMR memories with no talkgroup (WW7STR 146.875, W7BPD 440.375, N7ER 440.700, WA7DMR 440.7125, K7TGU 442.5875, NB7AT 442.850 among them) are no longer programmed. Where the machine is in the DMR network lists, the talkgroup channels transmit; add a talkgroup to the rest only if you want to key them. |
| D-STAR routing calls | The TH-D75/ID-52A D-STAR memories use Kenwood's routing calls, which the audit deliberately does not compare with the licensee. Four differ from WWARA's licensee on the same output - KF7CLD 443.425 (KI7PCT), NR7SS 440.350 (WA7DEM), K7GKR 444.725 (NW7DR/W7MSH), WA7DR 442.925 (WA7FW) - and K7LWH C 146.125 +1.0 and KK7PPV 443.000 have no WWARA record. Confirm them on dstarinfo.com before relying on DR routing. N7IH C was corrected to 147.4875. |

## Needs an API key or an outside approval

| Item | Detail |
|---|---|
| RadioReference login | The app key is configured (local `state/sources.json`) and the `radioreference_api` connector is built, but every data call also needs your RadioReference username and password. Store them once with `cmdkey /generic:wasds150-radioreference /user:<RadioReference username> /pass` (it prompts for the password; nothing reaches the repository). The next update then pulls everything RadioReference holds for Washington - every county's and statewide agency's conventional frequencies and every trunked system's sites, frequencies and talkgroups - and each later run reports what changed since the last one in `.wasds150-home\radioreference\runs\`. See [radioreference-api-application.md](radioreference-api-application.md). |
| RepeaterBook API (request #229) | Would replace the GMRS directory data with owner-maintained tones and real coordinates, and cross-check WWARA's status data. |

## Code follow-ups

| Item | Detail |
|---|---|
| Novice privileges | The band plan gives Novices 6 m, 2 m and 70 cm transmit privileges they do not hold under 47 CFR 97.301(f). No shipped plan is affected (the operator is General class). |
| Learn which channels talk | The Near Me lists rank by distance and service type, not by activity. After a few drives with the SDS150 recording or Discovery logging to its card, read the hits back and demote channels that never transmit. |
| NWAC and NIFC sources | Both change-detection sources fail with HTTP 404: NWAC's backcountry-radio page (`https://nwac.us/backcountry-radio-channels/`) is gone from its sitemap, and NIFC's `https://www.nifc.gov/nicc-files/radio` no longer exists, with no NIRSC document linked from the NICC reference pages. They only raise "document changed" alerts, never catalog data, so nothing else is affected. Point `src/wasds150/sources/nwac.py` and `nifc.py` at the new pages if they reappear, or retire them. |
| FCC ULS scope | The working home keeps FCC land-mobile licences within 60 miles with DMR, NXDN or P25 emissions. Widen with `sources configure --fcc-within-miles 0 --fcc-emissions ""` if analog business channels are wanted too. |
| DMR corrections to revisit | `src/wasds150/recipes/dmr_corrections.py` drops SeattleDMR's stale "BEARS W.Tiger" 442.075 row, adds K7NWS West Tiger 440.3375 with SeattleDMR's published layout, and sets N7QT Redmond to colour code 1 (BrandMeister) over the coordination record's 2. Recheck against seattledmr.org, the Config Builder file and the BrandMeister API when any of them changes; remove a correction once its source agrees. |
| DMR activity | Talkgroup tiers follow what PNWDigital publishes as full-time and the networks' nets (see `docs/puget-sound-nets.md`), not measured traffic: BrandMeister's per-talkgroup last-heard is a live dashboard with no history API. |

## Routine

- Run the update (double-click `Update Radios.cmd`) whenever the catalog
  changes, and at least monthly: WWARA regenerates nightly, the FAA publishes a
  new NASR cycle every 28 days, and RadioReference exports go stale as
  agencies rebuild their systems.
- Tick the bulk source (FCC ULS) about once a month; it is hundreds of
  megabytes and unticked by default. FAA NASR needs nothing: every update
  checks for a new cycle and rebuilds the `FAAAIR` airband list.
- Re-export RadioReference CSVs into `.wasds150-home\rr-exports\` when you want
  newer county data; the refresh imports whatever is there.
