# Open items

What is still unfinished across the radio fleet, grouped by what it takes to
close. Updated 2026-09-13, after the zone/scan-list rework, the DMR network
corrections and the SDS150 Near Me fixes. Everything not listed here is done
and tested.

## Needs a decision

| Item | Detail |
|---|---|
| Keep or retire the legacy plans | `h9-ozette`, `ftx1-wa`, `ftx1-local`, `ftx1-scan`, `thd75-ames-lake`, `thd75-scan` and `atd890-scan` predate the fleet template. The update wizard loads the `<radio>-fleet` plans instead. The legacy exports in `radio-configs/` were regenerated on 2026-09-10, so they are current, but nothing refreshes them automatically. Either keep them as alternatives (re-run the commands in [radio-configs/README.md](../radio-configs/README.md) after each refresh) or retire them and let the fleet plans stand alone. Their slot counts are pinned in `tests/test_fleet_template.py` (`LEGACY_SLOTS`). |
| `radio-configs/` provenance statement | [radio-configs/README.md](../radio-configs/README.md) says the committed files are built only from data committed to this repository. They are regenerated from the working home, whose catalog also holds the refreshed WWARA, IACC, NOAA and FCC data (RadioReference rows are excluded from the Anytone bundle, and the other plans do not select them). Review that paragraph against [NOTICE.md](../NOTICE.md) before making the repository public. |
| Sentinel profile | `sds150.sentinel_profile` is set to `Preset`, the only profile in the Sentinel workspace. If the scanner's lists live in another profile, change it on the Fleet tab before the first update with **Write to the radios** ticked. |
| Statewide SAR and interop at home | Seven Upper Lena trip-list channels (WA SAR 155.160, OSCCR 156.135, NIFC Air Guard 168.625, ONP Main, Command 7/8, USCG Air 2) stopped scanning at home when Near Me stopped merging stations whose fences merely touch; they only ever reached Ames Lake through that trip list's 85-mile fence. If statewide SAR/interop calling channels should be heard everywhere, place them "anywhere" as the ham calling frequencies are (`_placement` in `src/wasds150/radios/near_me.py`). |
| Untracked working folders | `radio-configs/contacts/` (the ~30 MB radioid.net download, refreshed daily) and `radio-configs/probes/` (FTX-1 probe files) are untracked. Either add them to `.gitignore` or commit what should be kept. |

## Needs the radio on the bench

| Item | Detail |
|---|---|
| TD-H9 programming port | `td-h9.com_port` is not set. Plug in the programming cable, find its port in Device Manager (a Prolific USB-to-Serial entry), and enter it on the Fleet tab. COM3 is an unrelated device. |
| AT-D890UV read-back of the new layout | The profile was verified on 2026-09-12 against the earlier layout. The bundle has since changed shape (Near Me zone of copies, one list per zone, Far zones, West Tiger added and the stale 442.075 rows removed): after the next write, read back and Export All into `radio-backups\at-d890uv\<date>-readback\` and let the compare step diff it. Confirm Digital Monitor reads back on (`DigiMoni`), which the 2026-09-12 read-back showed off. |
| AT-D890UV contact list format | The digital contact CSV's header and file name are unconfirmed (`CONTACT_FORMAT_VERIFIED=False` in `src/wasds150/export/atd890_contacts.py`). Export one from the CPS and compare. |
| AT-D890UV NXDN columns | NXDN channels put the RAN in the `EnRan`/`DeRan` columns, which has not been checked against a CPS export. |
| AT-D890UV Optional Settings template | Capture two CPS **Export All** folders (a fresh codeplug and your configured one) and run `scripts/radios/build_atd890_settings_template.py`, so the export can carry your hotkeys and settings. Then set `at-d890uv.rdt_base` to the saved `.rdt`. |
| FTX-1 profile | Built from documentation and never written to a radio. RT Systems will not send until it has read the radio once, so read first and keep that as `radio-backups\ftx1\` (none exists yet). After the first load, check a few memories against the export report. |
| FTX-1 MEM Group | `M-Grp` (bit 1 of record byte 0x00, decoded from a probe on 2026-09-13) is ticked on the 70 Near Me memories. What Set Menu `55: MEM Group` does with it on the radio - scan only the flagged memories, or merely display them apart - is not yet known; check it and record the answer in `docs/scan-groups.md`. |
| SDS150 scanner profile | The installer never writes `profile.cfg`. The Preset profile had Aircraft, Business, Railroad, Other, Interop, Federal and Military service types off (muting Near Me Air, Business & GMRS and most of Rail & Marine), `ScanHpdb` on, no SAME code, and Close Call and weather-alert priority off. Set them in Sentinel or on the scanner (the fleet checklist's "Set the scanner profile" step), then confirm on the scanner. |
| ID-52A CSV layout | The columns and defaults in `src/wasds150/export/id52_csv.py` come from Icom's documentation and real ID-52 CSV files, not from a file CS-52 itself wrote. The installer is downloaded (`Cs52_ver123.zip`); install it, import one memory group and the repeater list, then export a group back out and diff the two. Until that is done the profile stays `verified=False`. |
| ID-52A first write | The radio has not been written from this project. Read the radio into CS-52 first so the call sign, GPS and APRS settings survive, and check a few memories and a DR entry afterwards. |
| TH-D75 tracked image | `radio-configs/thd75-current.d75` and its power-on bitmap still carry the earlier callsign KM7HKM. Replace them after the next write and read-back. |
| GMRS repeater tones | The 17 repeaters in `GMRS01` (`src/wasds150/catalog/gmrs_repeaters.py`) were added by hand, and their access tones are not yet confirmed on the air. Key each one up and fix any that do not open. Auburn (WRBQ486, 254.1) and Gig Harbor (WRPR468, 173.8, possibly 141.3) are the doubtful ones. |

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
