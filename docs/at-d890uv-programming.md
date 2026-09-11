# Programming the Anytone AT-D890UV

The AT-D890UV is a dual-band DMR/analog handheld with NXDN (via a firmware
overlay), an AM air-band receiver and an FM broadcast receiver. This guide
takes it from the box to a fully programmed scanner-with-transmit built from
this repository's catalog: every conventional channel within 60 miles of home,
one zone per service, composite scan lists, and transmit enabled only on the
amateur channels a General-class licence covers.

Everything marked **verified** was checked against the CPS, the firmware
change logs or a real codeplug export. The radio profile is still marked
`verified=False` in `src/wasds150/radios/registry.py` until a generated bundle
has been written to the radio and read back.

---

## What you need

| Item | Notes |
|---|---|
| Anytone AT-D890UV | US band mode 00007 (Rx 136-174 / 400-480, Tx 144-148 / 420-450). Check **Menu > Settings > Device Info > Frequency Range**. Mode 14 adds 220 MHz but is not assumed by the plan. |
| Programming cable | The USB-C to USB-A cable in the box. Windows needs the virtual COM driver from the firmware package (`official-1.05/A READ FIRST - Update Instructions/Virtual Driver Installation.pdf`). |
| D890UV CPS **1.05** | Installed by this project into `C:\D890UV\D890UV.exe` (Inno Setup, silent). CPS and firmware versions must match exactly. |
| Firmware **1.05** (2026-05-20) | Official DMR build. Scan lists grew from 50 to 100 members in this release, which the exporter relies on. |
| NX_DMR **1.05** overlay | The NXDN+DMR firmware Anytone distributes through dealers (Wouxun.us mirror). Flashed *after* official 1.05. |
| DMR ID | `3227807`, registered to `WA7DAM` at <https://radioid.net>. Every bundle carries it (`src/wasds150/station.py`). |

All packages, change logs and manuals are fetched by
`radio-tools/anytone-d890uv/download.ps1` into the git-ignored
`radio-tools/anytone-d890uv/` folder; `SHA256SUMS.txt` there records what was
downloaded on 2026-09-10.

---

## The short version

```powershell
# 1. Refresh the catalog (RadioReference export + DMR network files), then export
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources update --only radioreference_premium,seattledmr --apply
.\.venv\Scripts\wasds150.exe --home .wasds150-home plan export atd890-scan --target atd890-cps --out wasds150-output\radios

# 2. In the CPS (C:\D890UV\D890UV.exe): File > New, then Tool > Import > choose
#    wasds150-output\radios\atd890-scan\atd890-scan.LST > Import All
# 3. Set the handful of Optional Settings listed below, then write.
```

The full bundle lands in `wasds150-output/radios/atd890-scan/` (git-ignored
because it contains RadioReference rows). A redistributable copy without those
rows is committed under `radio-configs/atd890-scan/`:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home plan export atd890-scan --target atd890-cps --out radio-configs --exclude-licensed
```

---

## Firmware: official 1.05, then the NXDN overlay

Back up first: **Read from radio** in the CPS, save the `.rdt`, and Tool >
Export > Export All into `radio-backups/at-d890uv/<date>/`.

1. Turn GPS and APRS off in the radio menu (the update instructions warn the
   radio can key up when connected otherwise).
2. CPS > Set > Set COM: pick the radio's port.
3. Hold **PTT + PF3** (top side key) and power on; the LED blinks red.
4. CPS > Tool > Firmware and Icon Update > Open Update File >
   `official-1.05/D890UV_V1.05_DMR FW/D890UV_V1.05_20260521.spi` > Write.
5. Power off, then hold **PTT + PF1** and power on: confirm the MCU reset,
   set the time zone, date and time. **This wipes the codeplug.**
6. Repeat steps 3-5 with the overlay:
   `nx-dmr-1.05/D890UV_V1.05_NX_DMR_FW/D890UV_V1.05_20260521.spi`.
7. Optional but recommended from the same package: the ICON V1.02 file, the NR
   board V112 file (`NR board FW upgrade instruction.pdf`), and the SCT3288
   baseband (`3288 base band upgrade.pdf`). Device Info should then show
   Firmware V1.05, ICON V1.02, NR V112, SCT V3_01_01A6.
8. Reinstall the CPS 1.05 if it was not already, and in the CPS Tool > Options
   tick GPS, Bluetooth, APRS and 500 Hour Record so those pages are visible.

The radio runs **one digital protocol at a time**: Menu > Settings > Radio Set
> Other Func > Protocol (item 33) switches DMR and NXDN. The plan ships with
DMR as the default; the NXDN channels in the `Comm Digital` zone are silent
until you switch. Optional Setting > Digital Function > **Dig Protocol = DMR**
and **Reset Digi. Protocol = DMR** keep that default across resets.

---

## What the bundle contains

`wasds150 plan export atd890-scan --target atd890-cps` writes a directory:

| File | Contents |
|---|---|
| `Channel.CSV` | 77-column channel table: every VHF/UHF memory, ordered by zone. Analog rows carry the transmit CTCSS/DCS; DMR rows carry contact, colour code and timeslot; receive-only rows have `PTT Prohibit = On`. |
| `DMRZone.CSV` | One zone per plan bank, split into `Name 01`, `Name 02` at 100 members. |
| `ScanList.CSV` | One scan list per zone (same name) plus the composite groups. |
| `DMRTalkGroups.CSV` | Every talkgroup any channel references, with a `Simplex 99` default. |
| `DMRReceiveGroupCallList.CSV` | One receive group per network (`PNWDigital RX`, `SeattleDMR RX`, ...) so a DMR channel hears every talkgroup carried on its network. |
| `RadioIDList.CSV` | `3227807, WA7DAM` - the registered DMR ID. |
| (none) | The NXDN unit ID, **16240**, is a radio-wide setting rather than an import table: CPS **NX Setting > Unit ID(Own)**. The fleet checklist has a step for it; a codeplug opened from your saved `.rdt` already carries it. |
| `AMAir.CSV`, `AMZone.CSV` | Air-band memories and zones (`Air Civil 01..`, `Air Mil SAR`); the zone's scan member list is the whole zone. |
| `FM.CSV` | FM broadcast stations, all with `Scan = Del`. |
| `atd890-scan.LST` | Manifest for Tool > Import > Import All. |

Zones, in scan-priority order:

| Zone | Transmit | What is in it |
|---|---|---|
| `Ham 2m`, `Ham 70cm` | yes | WWARA-coordinated analog repeaters within 60 miles, access tone on transmit |
| `DMR Puget Sound` | yes | PNWDigital and SeattleDMR repeaters, one channel per repeater/talkgroup as the network carries it |
| `DMR Other` | no | Western Washington network machines and coordinated DMR repeaters without a published layout |
| `Simplex` | yes | 2 m / 70 cm calling, operator-published simplex, DMR simplex 441.000 / 446.500 (TG 99), ACS simplex |
| `Seattle ACS` | yes | Seattle Auxiliary Communications Service repeater plan |
| `Air Civil`, `Air Mil SAR` | no | AM list (see below) |
| `SAR Interop`, `Wildfire`, `Marine`, `Rail`, `GMRS FRS MURS`, `Business`, `Pub Safety`, `Comm Digital` | no | Receive only |
| `ACS Data`, `NOAA WX`, `FM Bcast` | no | Programmed, never in any scan list |

Scan groups (composite lists, each chunked at 100 members: `Ham All 01`,
`Ham All 02`, ...):

- **Ham All** - analog repeaters, DMR Puget Sound, simplex, ACS
- **Ham Analog**, **Ham DMR**
- **Pub Svc** - SAR/interop, wildfire, public safety, commercial digital
- **Marine Rail**, **Personal Biz**
- **Everything** - all scannable zones

---

## Import into the CPS

1. `C:\D890UV\D890UV.exe` > File > New.
2. Model > Model Information: confirm the frequency range matches the radio
   (read the radio first if unsure; a mismatch produces "Band Error").
3. Tool > Import > select `atd890-scan.LST` > **Import All**. Each table loads
   in manifest order; a name that does not resolve (a zone member missing from
   `Channel.CSV`) is reported by the CPS - it means the export is stale, so
   re-export rather than editing in place.
4. If Import All refuses the manifest, import the files one at a time in the
   manifest order (Channel, RadioIDList, DMRZone, ScanList, DMRTalkGroups, FM,
   DMRReceiveGroupCallList, AMAir, AMZone).
5. Digital > Radio ID List shows `3227807` / `WA7DAM`; nothing to change.

### Optional Settings to set by hand

These live in the CPS's `OptionalSetting.CSV`, an opaque numeric table this
project does not generate. Set them once; they persist in your saved `.rdt`.

| Page | Setting | Value | Why |
|---|---|---|---|
| Digital Function | Digital Monitor | **Double Slot** | Hear both timeslots while scanning |
| Digital Function | Digital Monitor CC / ID | **Any / Any** | Promiscuous receive - required for scanner use |
| Digital Function | Dig Protocol / Reset Digi. Protocol | DMR / DMR | Default protocol |
| Work Mode | Sub-Channel Mode | **On** | Dual watch |
| Work Mode | VFO/MEM A, MEM Zone A | MEM, `Ham 2m` | Main receiver on the scan lists |
| Work Mode | VFO/MEM B | MEM | |
| AM/FM | AM/FM Function | **AM(B)** | B receiver becomes the air-band receiver |
| AM/FM | AM Work Zone | `Air Civil 01` | Start zone for the AM scan |
| AM/FM | AM Squelch Level | 2 (adjust) | |
| Other | Scan Mode (VFO scan type) | CO | Resume 2 s after the carrier drops |
| Other | Priority Zone A | `Ham 2m` | "Prior Zone" side key jumps back to it |
| Other | TOT | 180 s | |
| Key Functions | PF1 short / long | Scan / Nuisance Delete | |
| Key Functions | PF2 short / long | Sub CH Switch / Main Channel Switch | Toggle dual watch, swap A/B |
| Key Functions | PF3 short | AM/FM | Toggle the air-band receiver |
| Key Functions | P1 short | Zone Select | |
| Key Functions | P2 short | Digital Monitor | |
| Power On | Power-on Display Char | `WA7DAM` | |
| GPS/Ranging | Time Zone | UTC-8 (UTC-7 in summer) | |

Save the codeplug (`radio-backups/at-d890uv/atd890-scan-<date>.rdt`), then
**Write to radio** (Other Data; Digital Contact List only if you loaded one).

### Capture the settings once instead

Setting the table above by hand after every fresh import is error-prone.
Capture it once and every export carries it:

1. In the CPS: File > New, then Tool > Export > Export All into
   `radio-backups/at-d890uv/fixtures/fresh/`.
2. Apply the settings table above, then Export All again into
   `radio-backups/at-d890uv/fixtures/configured/`.
3. Build the template:

   ```powershell
   .\.venv\Scripts\python.exe scripts\radios\build_atd890_settings_template.py `
       --fresh radio-backups\at-d890uv\fixtures\fresh `
       --configured radio-backups\at-d890uv\fixtures\configured
   ```

This writes `src/wasds150/data/atd890_settings_template.json` - the configured
`OptionalSetting.CSV` and `HotKey_*.CSV` with every cell you changed. Your Radio
ID and call sign are blanked in the template and filled back in at export.
From then on every bundle includes those files and lists them in the `.LST`,
so Import All restores the settings. A zone the settings name (MEM Zone A,
Priority Zone A, AM Work Zone) must exist in the bundle; if it does not, the
export uses the first zone and says so in the report.

### Contact list

`wasds150 fleet update` downloads the worldwide DMR and NXDN ID registry from
radioid.net (through the HTTP cache: once a month at most) and the fleet
export writes it next to the bundle as `DigitalContactList.CSV` (and
`NXDNContactList.CSV`), every entry a Private Call, split into numbered files
if it ever exceeds the radio's 500,000 contacts. **Its column layout is not yet
confirmed against this CPS**, so it is deliberately left out of the `.LST`:
import it on its own (Tool > Import > Digital Contact List), then open a few
entries. Once an Export All of a codeplug with contacts confirms the header and
file name, set `CONTACT_FORMAT_VERIFIED` in
`src/wasds150/export/atd890_contacts.py` and paste the captured header over
`CONTACT_HEADER`. Importing ~300,000 contacts takes several minutes.

### Using it as a scanner

- Main receiver A: pick a zone with the up/down key; Menu > Scan > Scan List
  chooses which list a zone scans (`Ham All 01` is the recommended default),
  then PF1 starts it. Nuisance Delete (PF1 long) drops a busy channel for the
  session.
- Receiver B on AM air: Menu > Settings > Radio Set > Other Func > AM Air/FM
  > AM Air on B, then the AM zone's own scan menu.
- NOAA, FM broadcast and the packet zone are selected by hand and never
  interrupt a scan.
- Switch Protocol to NXDN (menu item 33) to hear the AMR and other NXDN users
  in `Comm Digital`; DMR is silent while NXDN is selected.

### Read back and verify

After writing: Read from radio, Tool > Export > Export All into
`radio-backups/at-d890uv/<date>-readback/`, then compare it with the bundle:

```powershell
.\.venv\Scripts\python.exe scripts\radios\diff_atd890_export.py `
    --bundle wasds150-output\radios\at-d890uv-fleet `
    --readback radio-backups\at-d890uv\<date>-readback
```

Rows are matched by name (channel, zone, scan list, talkgroup ID), `No.` is
ignored, frequencies compare numerically, and
zone/scan members that only changed order are listed but do not count. It exits
0 when the read-back matches and prints the SHA-256 of the bundle and each file.
Any other column the CPS rewrote is a bug in `CHANNEL_DEFAULTS`
(`src/wasds150/export/atd890_cps.py`), not something to ignore; a column the
CPS legitimately normalises goes in `CPS_NORMALIZED_COLUMNS`
(`src/wasds150/export/atd890_diff.py`) with the reason. The fleet update's
optional **Compare the read-back** step runs the same comparison. Once a round
trip is clean, flip `verified=True` on the profile and record the printed
SHA-256 lines here.

---

## Transmit policy and the law

Transmit is enabled only in `Ham 2m`, `Ham 70cm`, `DMR Puget Sound`,
`Simplex` and `Seattle ACS`, all inside 144-148 and 420-450 MHz. Every other
zone has `PTT Prohibit = On`. GMRS needs its own licence and the radio is not
Part 95 certified; MURS, marine and business channels are receive only.

DMR etiquette on the networks: PNW 1 (3187) is calling only; move to a TAC
talkgroup for a conversation; Washington 1 (3153, TS1) and Washington 2
(103153, TS2) are the statewide QSO groups. Rules and hold-off timers:
<https://pnwdigital.net/talkgroups/>. SeattleDMR-specific groups (King
County 333153, Seattle 1/2, Link 1-6): <https://seattledmr.com/>.

---

## Refreshing

| What changed | Command |
|---|---|
| New RadioReference export in `.wasds150-home/rr-exports/` | `wasds150 sources update --only radioreference_premium --apply` |
| PNWDigital / SeattleDMR repeater or talkgroup changes | `wasds150 sources update --only seattledmr --apply`, and `scripts/radios/build_atd890_dmr_snapshot.py` to refresh the committed snapshot |
| BrandMeister repeater or static talkgroup changes | `scripts/radios/build_brandmeister_snapshot.py`, then commit `src/wasds150/catalog/brandmeister_snapshot.py`; the fleet plan's DMR zones pick it up (network `BrandMeister`, its own receive group) |
| WWARA coordination changes | `wasds150 sources update --only wwara --apply` |
| Anything above | re-run the export, re-import in the CPS, write |

The radio keeps nothing between codeplug writes, so the `.rdt` you saved after
setting the Optional Settings is the file to re-import the fresh CSV bundle
into.

---

## Known limits

- **No P25.** The radio's baseband cannot decode it; the trunked systems the
  county actually dispatches on (PSERN, Sno911, SS911) are dropped with the
  reason `unsupported-mode` in the report. Use the SDS150 for those.
- **DMR Tier I/II conventional only**: Capacity Plus and other trunked DMR
  systems appear as individual frequencies at best.
- **NXDN conventional only**, and only with the overlay firmware active.
- **NXDN column mapping is unverified.** The exporter writes the RAN into the
  `EnRan`/`DeRan` columns; check one NXDN channel in the CPS after import.
- **Scan lists hold 100 members**; long groups are chunked and the operator
  picks the chunk. The radio has no group-link scan across lists.
- **Air band is a separate receiver.** AM channels cannot be mixed into a
  VHF/UHF scan list; they scan from the B receiver's AM zone.
- **220 MHz** needs band mode 14 and is not programmed.
- **Names are 16 characters**; labels are shortened readably
  (`W7JCR Prt Twnsnd`) and made unique per bundle.
