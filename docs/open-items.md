# Open items

What is still unfinished across the radio fleet, grouped by what it takes to
close. Updated 2026-09-10, after the full source refresh and the regeneration
of the legacy radio exports. Everything not listed here is done and tested.

## Needs a decision

| Item | Detail |
|---|---|
| Keep or retire the legacy plans | `h9-ozette`, `ftx1-wa`, `ftx1-local`, `ftx1-scan`, `thd75-ames-lake`, `thd75-scan` and `atd890-scan` predate the fleet template. The update wizard loads the `<radio>-fleet` plans instead. The legacy exports in `radio-configs/` were regenerated on 2026-09-10, so they are current, but nothing refreshes them automatically. Either keep them as alternatives (re-run the commands in [radio-configs/README.md](../radio-configs/README.md) after each refresh) or retire them and let the fleet plans stand alone. Their slot counts are pinned in `tests/test_fleet_template.py` (`LEGACY_SLOTS`). |
| `radio-configs/` provenance statement | [radio-configs/README.md](../radio-configs/README.md) says the committed files are built only from data committed to this repository. They are regenerated from the working home, whose catalog also holds the refreshed WWARA, IACC, NOAA and FCC data (RadioReference rows are excluded from the Anytone bundle, and the other plans do not select them). Review that paragraph against [NOTICE.md](../NOTICE.md) before making the repository public. |
| Sentinel profile | `sds150.sentinel_profile` is set to `Preset`, the only profile in the Sentinel workspace. If the scanner's lists live in another profile, change it on the Fleet tab before the first update with **Write to the radios** ticked. |

## Needs the radio on the bench

| Item | Detail |
|---|---|
| TD-H9 programming port | `td-h9.com_port` is not set. Plug in the programming cable, find its port in Device Manager (a Prolific USB-to-Serial entry), and enter it on the Fleet tab. COM3 is an unrelated device. |
| AT-D890UV first write and read-back | The profile stays unverified until a written bundle reads back clean. Write it, read it back, Export All into `radio-backups\at-d890uv\<date>-readback\`, and let the wizard's compare step diff it; then set the profile's `verified=True`. |
| AT-D890UV contact list format | The digital contact CSV's header and file name are unconfirmed (`CONTACT_FORMAT_VERIFIED=False` in `src/wasds150/export/atd890_contacts.py`). Export one from the CPS and compare. |
| AT-D890UV NXDN columns | NXDN channels put the RAN in the `EnRan`/`DeRan` columns, which has not been checked against a CPS export. |
| AT-D890UV Optional Settings template | Capture two CPS **Export All** folders (a fresh codeplug and your configured one) and run `scripts/radios/build_atd890_settings_template.py`, so the export can carry your hotkeys and settings. Then set `at-d890uv.rdt_base` to the saved `.rdt`. |
| FTX-1 profile | Built from documentation and never written to a radio. After the first load, check a few memories against the export report. |
| TH-D75 tracked image | `radio-configs/thd75-current.d75` and its power-on bitmap still carry the earlier callsign KM7HKM. Replace them after the next write and read-back. |
| GMRS repeater tones | The 17 repeaters in `GMRS01` (`src/wasds150/catalog/gmrs_repeaters.py`) were added by hand, and their access tones are not yet confirmed on the air. Key each one up and fix any that do not open. Auburn (WRBQ486, 254.1) and Gig Harbor (WRPR468, 173.8, possibly 141.3) are the doubtful ones. |

## Needs an API key or an outside approval

| Item | Detail |
|---|---|
| RadioReference login | The app key is configured (local `state/sources.json`) and the `radioreference_api` connector is built, but every data call also needs your RadioReference username and password. Store them once with `cmdkey /generic:wasds150-radioreference /user:<RadioReference username> /pass` (it prompts for the password; nothing reaches the repository). The next update then refreshes all 16 trunked systems the catalog names - sites, frequencies and every talkgroup - and replaces their older Sentinel HPDB copies. See [radioreference-api-application.md](radioreference-api-application.md). |
| RepeaterBook API (request #229) | Would replace the GMRS directory data with owner-maintained tones and real coordinates, and cross-check WWARA's status data. |

## Code follow-ups

| Item | Detail |
|---|---|
| Novice privileges | The band plan gives Novices 6 m, 2 m and 70 cm transmit privileges they do not hold under 47 CFR 97.301(f). No shipped plan is affected (the operator is General class). |
| PSHAM02 after a refresh | Once WWARA is refreshed, PSHAM01 holds the same 6 m to 23 cm repeaters as the `PSHAM02` snapshot. Memory radios keep only one copy, but the SDS150 receives both lists. Disable PSHAM02 in the profile, or teach generation to drop it when PSHAM01 is populated. |
| NWAC and NIFC sources | Both change-detection sources fail with HTTP 404: NWAC's backcountry-radio page (`https://nwac.us/backcountry-radio-channels/`) is gone from its sitemap, and NIFC's `https://www.nifc.gov/nicc-files/radio` no longer exists, with no NIRSC document linked from the NICC reference pages. They only raise "document changed" alerts, never catalog data, so nothing else is affected. Point `src/wasds150/sources/nwac.py` and `nifc.py` at the new pages if they reappear, or retire them. |
| FCC ULS scope | The working home keeps FCC land-mobile licences within 60 miles with DMR, NXDN or P25 emissions. Widen with `sources configure --fcc-within-miles 0 --fcc-emissions ""` if analog business channels are wanted too. |

## Routine

- Run the update (double-click `Update Radios.cmd`) whenever the catalog
  changes, and at least monthly: WWARA regenerates nightly, the FAA publishes a
  new NASR cycle every 28 days, and RadioReference exports go stale as
  agencies rebuild their systems.
- Tick the two bulk sources (FCC ULS, FAA NASR) about once a month; they are
  hundreds of megabytes each and unticked by default.
- Re-export RadioReference CSVs into `.wasds150-home\rr-exports\` when you want
  newer county data; the refresh imports whatever is there.
