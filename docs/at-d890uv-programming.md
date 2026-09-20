# Programming the Anytone AT-D890UV

The AT-D890UV is a dual-band DMR/analog handheld with NXDN (via a firmware
overlay), an AM air-band receiver and an FM broadcast receiver. This guide
takes it from the box to a fully programmed scanner-with-transmit built from
this repository's catalog: every conventional channel within 60 miles of home,
one zone per service, composite scan lists, and transmit enabled only on the
amateur channels a General-class licence covers.

Everything marked **verified** was checked against the CPS, the firmware change
logs or a real codeplug export. The radio profile is `verified=True` as of
**2026-09-12**: the fleet bundle was written to the radio, read back and
exported, and every channel, zone, scan list, talkgroup, receive group, AM
memory and FM station matched. Bundle SHA-256
`EAC0872812F9EFBA2623033C03A6336CA7C33C5AB345381DC92596E850E4592F`.

---

## What you need

| Item | Notes |
|---|---|
| Anytone AT-D890UV | Band mode **00014**: Rx and Tx 136-174, 220-225 and 400-520. Check **Menu > Settings > Device Info > Frequency Range**, or the CPS title bar. The plan assumes it - a radio still in the factory US mode 00007 (Rx 136-174 / 400-480, Tx 144-148 / 420-450) has no 220 MHz and cannot key GMRS. Mode 14 is not in the CPS's Model Information dropdown; set it with the AT Options utility, whose band descriptor and password are in `radio-data/at-d890uv/firmware/options/AT_BANDS.txt`. |
| Programming cable | The USB-C to USB-A cable in the box. Windows needs the virtual COM driver from the firmware package (`official-1.05/A READ FIRST - Update Instructions/Virtual Driver Installation.pdf`). |
| D890UV CPS **1.05** | Installed by this project into `C:\D890UV\D890UV.exe` (Inno Setup, silent). CPS and firmware versions must match exactly. |
| Firmware **1.05** (2026-05-20) | Official DMR build. Its change log says "Modify the scan groups 50 channels limit to 100 channels limit", but that is the **radio**: the CPS's CSV importer still refuses a scan list of 51, so the export ships 50 of each and the .rdt patcher restores the rest. See [Scan lists hold 100, and the importer only reads 50](#scan-lists-hold-100-and-the-importer-only-reads-50). |
| NX_DMR **1.05** overlay | The NXDN+DMR firmware Anytone distributes through dealers (Wouxun.us mirror). Flashed *after* official 1.05. |
| DMR ID | `3227807`, registered to `WA7DAM` at <https://radioid.net>. Every bundle carries it (`src/wasds150/station.py`). |
| NXDN ID | `16240`, registered at <https://radioid.net>. Set once in the CPS at NX Setting > Unit ID(Own); the fleet checklist has a step for it (`src/wasds150/station.py`). |

All packages, change logs and manuals are fetched by
`radio-data/at-d890uv/firmware/download.ps1` into the git-ignored
`radio-data/at-d890uv/firmware/` folder; `SHA256SUMS.txt` there records what was
downloaded on 2026-09-10.

---

## The short version

```powershell
# 1. Refresh the catalog (RadioReference export + DMR network files), then export
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources update --only radioreference_premium,seattledmr --apply
.\.venv\Scripts\wasds150.exe --home .wasds150-home plan export atd890-scan --target atd890-cps

# 2. In the CPS (C:\D890UV\D890UV.exe): File > New, then Tool > Import > choose
#    radio-data\at-d890uv\exports\atd890-scan\atd890-scan.LST > Import All
# 3. Set the handful of Optional Settings listed below, then write.
```

The full bundle lands in `radio-data/at-d890uv/exports/atd890-scan/` (git-ignored
because it contains RadioReference rows). A redistributable copy without those
rows is committed under `radio-data/shared/legacy-plans/atd890-scan/`:

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home plan export atd890-scan --target atd890-cps --out radio-data/shared/legacy-plans --exclude-licensed
```

---

## Firmware: official 1.05, then the NXDN overlay

Back up first: **Read from radio** in the CPS, save the `.rdt`, and Tool >
Export > Export All into `radio-data/at-d890uv/readbacks/<date>-export-all/`.

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
DMR as the default; the NXDN channels - `Business Digital` and `Ham NXDN` on the
fleet plan, `Comm Digital` on `atd890-scan` - are silent until you switch. Optional Setting > Digital Function > **Dig Protocol = DMR**
and **Reset Digi. Protocol = DMR** keep that default across resets.

### Is NXDN actually enabled?

**On this radio, yes** - the NX_DMR overlay was flashed on 2026-09-11, and the
Export All kept alongside it carries `NXSetting.CSV`, `NXTalkGroup.CSV` and the
rest. So `NX Setting > Unit ID(Own) = 16240` is a real step again.

There is no CPS switch for it: **NXDN exists only when the NX_DMR firmware is
flashed.** The official 1.05 build is DMR-only, and on it the CPS hides every
NXDN page. Two ways to tell without guessing:

- **Left-hand tree.** With the overlay, it carries `NX Setting`, `NX Receive
  Group Call List`, `NX Contact/Talk Group`, `NX Encryption Code`, `NX State
  MSG` and `NX Digital Contact List`. Without it, none of them appear - the
  tree jumps from `QDC 1200` straight to `Master ID`.
- **Tool > Import.** With the overlay the dialog offers NX tables alongside the
  DMR ones. A dialog whose rows stop at `Encryption Code` with no NX row is a
  DMR-only radio.

To enable it, flash `nx-dmr-1.05/D890UV_V1.05_NX_DMR_FW/D890UV_V1.05_20260521.spi`
by the firmware procedure above - official 1.05 first, then the overlay.
**The MCU reset in that procedure wipes the codeplug**, so decide before
programming, not after: flashing afterwards means importing the whole bundle
again.

Nothing in the generated bundle depends on it. All NXDN content is receive
only: `Business Digital` (hospital, school and event users) and `Ham NXDN` -
KC7BAE on 443.050, RAN 5, from WWARA's pending coordination, which publishes
no group ID to key up with. The NXDN unit ID, 16240, matters once that group
is known and the memory can transmit. On a DMR-only radio, skip the unit ID
step and those channels simply stay quiet.

---

## What the bundle contains

`wasds150 plan export atd890-scan --target atd890-cps` writes a directory:

| File | Contents |
|---|---|
| `Channel.CSV` | 77-column channel table: every VHF/UHF memory, ordered by zone. Analog rows carry the transmit CTCSS/DCS; DMR rows carry contact, colour code and timeslot; receive-only rows have `PTT Prohibit = On`. |
| `DMRZone.CSV` | One zone per scan group that fits a list (`Near Me`, `Ham DMR`, `Rail & Marine`, `Personal`, as copies), then one zone per plan bank, split into `Name 01`, `Name 02` at 100 members; beyond-radius fill in `Far Ham Analog`, `Far Ham DMR`, `Far Public Svc`, `Far Other`; blocks that never scan (`Weather`, `Data`) with no list. |
| `ScanList.CSV` | Exactly one scan list per scanned zone, same name. Same members too, except that several DMR talkgroups on one repeater timeslot are one RF channel, so the list carries one of them and the zone keeps them all. No list exists without a zone. |
| `DMRTalkGroups.CSV` | Every talkgroup any channel references, with a `Simplex 99` default. |
| `DMRReceiveGroupCallList.CSV` | One receive group per network (`PNWDigital RX`, `SeattleDMR RX`, ...) so a DMR channel hears every talkgroup carried on its network. |
| `RadioIDList.CSV` | `3227807, WA7DAM` - the registered DMR ID. |
| (none) | The NXDN unit ID, **16240**, is a radio-wide setting rather than an import table: CPS **NX Setting > Unit ID(Own)**. The fleet checklist has a step for it; a codeplug opened from your saved `.rdt` already carries it. |
| `AMAir.CSV`, `AMZone.CSV` | Air-band memories and zones (`Air Civil 01..`, `Air Mil SAR`); the zone's scan member list is the whole zone. |
| `FM.CSV` | FM broadcast stations, all with `Scan = Del`. |
| `DMRDigitalContactList.CSV`, `NXDigitalContactList.CSV` | Fleet export only: the radioid.net DMR and NXDN contact lists (see [Contact list](#contact-list)), listed in the `.LST` at slots 15 and 31. |
| `atd890-scan.LST` | Manifest for Tool > Import > Import All, naming every CSV in the bundle. |

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

Scan groups: every group that fits one scan list is built, as a zone of copies
with its own list, in plan order ahead of the per-service zones. PF1 only ever
sweeps the list named on the channel under the cursor, so a composite list is
reachable only through a zone of its own, and a group over 100 channels could
only become arbitrary slices that no zone led to.

The fleet plan builds four: `Near Me` (82), **`Ham DMR` (46)**, `Rail & Marine`
(82) and `Personal` (47). `Ham DMR` fits only because a repeater timeslot
counts once - 416 talkgroup channels across the DMR Core, Local and Wide blocks
are **46 channels to sweep, covering 23 machines on all three networks, both
timeslots**. `Ham All`, `Ham Analog`, `Pub Svc` and `Everything` are still too
big and are not exported, with a warning naming each.

The **first** group is the exception to the fit rule: it is the zone the knob
lands on, so it is built short rather than not at all (`Ham All` on the legacy
`atd890-scan` plan, capped at 100). Its quota has already ranked it - pinned
first, then nearest - so its first hundred are its best hundred.

---

## Import into the CPS

1. `C:\D890UV\D890UV.exe` > File > New.
2. Model > Model Information: confirm the frequency range matches the radio
   (read the radio first if unsure; a mismatch produces "Band Error").
3. Tool > Import > **Import From File List** > choose `at-d890uv-fleet.LST` >
   **Import All**. A name that does not resolve (a zone member missing from
   `Channel.CSV`) is reported by the CPS - it means the export is stale, so
   re-export rather than editing in place.
4. If the manifest is ever refused, every table can be imported on its own from
   the same dialog, each row with its own button:

   | Import dialog row | File | Slot |
   |---|---|---:|
   | Channel | `Channel.CSV` | 0 |
   | Radio ID List | `RadioIDList.CSV` | 1 |
   | DMR Zone | `DMRZone.CSV` | 2 |
   | Scan List | `ScanList.CSV` | 3 |
   | DMR Talk Groups | `DMRTalkGroups.CSV` | 5 |
   | FM | `FM.CSV` | 7 |
   | DMR Receive Group Call List | `DMRReceiveGroupCallList.CSV` | 8 |
   | AM Air | `AMAir.CSV` | 27 |
   | AM Zone | `AMZone.CSV` | 30 |
   | DMR Digital Contact List | `DMRDigitalContactList.CSV` | 15 |
   | NX Digital Contact List | `NXDigitalContactList.CSV` | 31 |

   Channel first and the zone and scan lists after the channels they name.
5. Digital > Radio ID List shows `3227807` / `WA7DAM`; nothing to change.

### Scan lists hold 100, and the importer only reads 50

Firmware 1.05's change log line 10 reads "Modify the scan groups 50 channels
limit to 100 channels limit". The radio holds 100. **The CPS's CSV importer
does not**: a 51st member raises

    Runtime error 9, subscript out of range

which is Visual Basic 6 for an array index past the end - the CPS is a VB6
binary (`MSVBVM60.DLL`), and its import routine dimensions the member array at
fifty. Tested against this radio one member at a time, a single scan list
imported alone: 35 and 50 pass, 51 and 100 fail, and shortening the names does
not help, so it is a count and not a string length. The per-table `Scan List`
button fails the same way; it is the same parser.

Nothing else is affected. The CPS's own editor takes a 51st member happily, and
saves and reloads it, so only the CSV path is broken.

So the plan is built at the radio's 100, `ScanList.CSV` carries the first
:data:`~wasds150.export.atd890_cps.CSV_SCANLIST_MAX` of each list, and
`scanlists.json` beside it records the full membership for
`scripts/radios/patch_atd890_scanlists.py` to restore afterwards - see
[Longer scan lists](#longer-scan-lists). The fleet plan is 37 zones and 35 scan
lists (every scanned zone has one), against the 250 of each the manual allows;
12 of the lists are over 50 and need the patch. None of the DMR lists do any
more - one channel per repeater timeslot brought every one of them under 50.

This is the failure that looks like something else. `Channel.CSV` is ~1,500
rows and fills nearly the whole progress bar, so the scan-list table is always
processed last and a rejection of the *whole table* reads as "failed towards
the end". Importing fewer lists does not help, because the first oversized list
kills it whatever its position; importing the scan list on its own with no
channels in the codeplug fails instantly instead, because no member resolves.

### Longer scan lists

After importing the bundle and saving the codeplug:

```powershell
.\.venv\Scripts\python.exe scripts\radios\patch_atd890_scanlists.py `
    --rdt radio-data\at-d890uv\backups\<saved>.rdt `
    --sidecar radio-data\at-d890uv\exports\at-d890uv-fleet\scanlists.json `
    --output radio-data\at-d890uv\backups\<saved>-full.rdt
```

Open the `-full.rdt` in the CPS and write that. The `.rdt` is a plain
uncompressed container with **no checksum**; its scan-list section is a chain of

    [index:1] [name:16] [settings:10] [count:uint16le] [count x member]
    member = [channel:uint16le] [sep:1]

where `sep` is zero except on a record's last member, which carries the *next*
record's index byte - a separator, not a flag. A `uint32le` at offset 5 holds
the container length, the file size less its fourteen-byte header.

Only member arrays grow. No record is added, removed or renumbered, so nothing
that refers to a scan list by index - every channel does - is disturbed. The
patcher refuses a codeplug whose lists are not the head of what the sidecar
expects, which is what catches a `.rdt` built from a different export, and it
re-parses its own output before writing.

The format was established from two codeplugs that differed by exactly one
scan-list member: rebuilding the second from the first reproduced it byte for
byte, which is what says there is nothing else to maintain.
`tests/test_atd890_rdt_patch.py` keeps that check.

### The same lists on the other radios

The Anytone is the only radio in the fleet with real scan lists, so it holds
`Near Me` as a scan list of up to a hundred channels. The TH-D75A and ID-52A
hold it as a memory group of copies (the D75's Memory Group Link names that
group alone), the FTX-1 flags its memories with M-Grp, and the TD-H9 has
nothing to express it with. See [scan-groups.md](scan-groups.md) for how the
list is filled.

### Priority Channel 1/2 must be `Off`

The CPS writes a real channel name and its frequencies into `Priority Channel
1` and `Priority Channel 2` when it exports. **It will not import that back.**
A single scan list that differs only in carrying those names is refused; the
same list with `Off` and empty frequency cells imports. So the exporter's `Off`
is not a placeholder to improve on - do not "fix" it to match what Export All
writes.

### The manifest index is a slot, not a position

Every `.LST` line is `<index>,"<file>"`, and the index selects one of the CPS's
**fixed** import slots - the "Slot" column above. It belongs to the table, not
to the manifest: a manifest listing nine tables still has to give each file its
own number. Numbering a nine-file subset `0..8` matches only as far as
`ScanList.CSV` and then hands `DMRTalkGroups.CSV` to slot 4, *Analog Address
Book*, which is where Import All stops with `ImportFromFileListError` - about
halfway through, which is where it was seen.

The full table is :data:`LST_INDEX` in `src/wasds150/export/atd890_cps.py`, all
38 slots, captured from a `Tool > Export > Export All` of CPS 1.05 on firmware
1.05 + NX_DMR and kept verbatim at
`radio-data/at-d890uv/readbacks/2026-09-11-export-all-fw105-nxdn/export.LST`. Slots are
stable across firmware: the six NX tables keep their numbers (23-26, 31, 34)
whether or not the NXDN overlay is flashed, and the Import dialog simply hides
the rows it cannot use. An export naming a file the table does not know fails
at export time rather than in the CPS.

Re-capture it if the CPS is ever upgraded, and diff it against that file.

### Optional Settings to set by hand

These live in the CPS's `OptionalSetting.CSV`, an opaque numeric table this
project does not generate. Set them once; they persist in your saved `.rdt`.

| Page | Setting | Value | Why |
|---|---|---|---|
| Digital Function | Digital Monitor | **Double Slot** | Hear both timeslots while scanning |
| Digital Function | Digital Monitor CC / ID | **Any / Any** | Promiscuous receive - required for scanner use |
| Digital Function | Dig Protocol / Reset Digi. Protocol | DMR / DMR | Default protocol |
| Work Mode | Sub-Channel Mode | **On** | Dual watch |
| Work Mode | VFO/MEM A, MEM Zone A | MEM, `Near Me` | Main receiver starts on the list worth leaving running |
| Work Mode | VFO/MEM B | MEM | |
| AM/FM | AM/FM Function | **AM(B)** | B receiver becomes the air-band receiver |
| AM/FM | AM Work Zone | `Air Civil 01` | Start zone for the AM scan |
| AM/FM | AM Squelch Level | 2 (adjust) | |
| Other | Scan Mode (VFO scan type) | CO | Resume 2 s after the carrier drops |
| Other | Priority Zone A | `Near Me` | "Prior Zone" side key jumps back to it |
| Other | TOT | 180 s | |
| Key Functions | PF1 short / long | Scan / Nuisance Delete | |
| Key Functions | PF2 short / long | Sub CH Switch / Main Channel Switch | Toggle dual watch, swap A/B |
| Key Functions | PF3 short | AM/FM | Toggle the air-band receiver |
| Key Functions | P1 short | Zone Select | |
| Key Functions | P2 short | Digital Monitor | |
| Power On | Power-on Display Char | `WA7DAM` | |
| GPS/Ranging | Time Zone | UTC-8 (UTC-7 in summer) | |

Save the codeplug (`radio-data/at-d890uv/backups/atd890-scan-<date>.rdt`), then
**Write to radio** (Other Data; Digital Contact List only if you loaded one).

### Capture the settings once instead

Setting the table above by hand after every fresh import is error-prone.
Capture it once and every export carries it:

1. In the CPS: File > New, then Tool > Export > Export All into
   `radio-data/at-d890uv/readbacks/settings-fresh/`.
2. Apply the settings table above, then Export All again into
   `radio-data/at-d890uv/readbacks/settings-configured/`.
3. Build the template:

   ```powershell
   .\.venv\Scripts\python.exe scripts\radios\build_atd890_settings_template.py `
       --fresh radio-data\at-d890uv\readbacks\settings-fresh `
       --configured radio-data\at-d890uv\readbacks\settings-configured
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
radioid.net, checking with the server on every update (radioid.net republishes
daily; an unchanged file is not downloaded again), and the fleet export writes
it into the bundle and its `.LST`, every entry a Private Call, split into numbered files if
it ever exceeds the radio's 500,000 contacts.

The two protocols do **not** share a format; both headers below are from the
captured Export All:

| File | Slot | Header |
|---|---:|---|
| `DMRDigitalContactList.CSV` | 15 | `No., Radio ID, Callsign, Name, City, State, Country, Remarks, Call Type, Call Alert` |
| `NXDigitalContactList.CSV` | 31 | `RADIO_ID, CALLSIGN, FIRST_NAME, LAST_NAME, CITY, STATE, COUNTRY, Attr, TxForbid, Ring` |

The NXDN table has no `No.` column, splits the name, and ends in three columns
of its own. The captured table was empty, so `Attr`, `TxForbid` and `Ring` have
a confirmed name but no confirmed value and are written empty
(`NXDN_TRAILING_VERIFIED` is `False`); add one NXDN contact by hand, export
again, and paste the values in to close that.

Both are listed in the fleet bundle's `.LST` at those slots, so Import All
loads them with every other table; a worldwide list makes the import take
several minutes. A list split into numbered files lists only its first file;
import the others on their own (Tool > Import > DMR Digital Contact List).

### Using it as a scanner

- **A zone and its scan list are the same thing.** Pick a zone with the
  up/down key and press PF1: it sweeps exactly that zone. The radio has no
  zone scan and no radio-wide scan list - PF1 sweeps the list named on the
  channel under the cursor, and answers "Scan List No Select" on a channel
  naming none (measured on this radio) - so the export makes every scanned
  zone's channels name one list. The list holds exactly them, except on a DMR
  zone: several talkgroups on one repeater timeslot are the same RF channel,
  so the list carries one of them and sweeps the machine once instead of
  seven times. The others are still in the zone to dial up and transmit on.
- The first four zones are the ready-made sweeps, copies of channels that live
  elsewhere, named with a trailing ` N` and each naming its own list:
  `Near Me` (the nearest of every local amateur service), **`Ham DMR`** (every
  DMR machine in the plan, both timeslots, all three networks - 46 channels),
  `Rail & Marine` and `Personal` (GMRS/FRS/MURS). The originals stay in their
  own zones and keep scanning those.
- `Far Ham Analog`, `Far Ham DMR`, `Far Public Svc` and `Far Other` hold the
  stations the fill pass found beyond the radius: out of their own blocks so
  the local sweep stays quick, but scannable in zones of their own, each
  named for the narrowest scan group its block is in (a service with fewer
  than ten such stations joins `Far Other`).
- `Weather` and `Data` scan nothing on purpose (continuous carriers, packet).
  A channel the operator locked out by label would land in `Not Scanned`,
  also with no list; the fleet plan currently has none. Nuisance Delete
  (PF1 long) drops a busy channel for the session.
- **Digital Monitor must be on to hear DMR.** Optional Settings > Digital
  Function > Digital Monitor = Double Slot, CC = Any, ID = Any. With it off
  (`DigiMoni 0` - how the radio came from the factory, and still how it read
  back after the 2026-09-12 write), a DMR channel opens only for talkgroups in
  its receive group list on its own timeslot, and most traffic on these
  networks is someone keying a talkgroup that list does not name. It is an
  Optional Setting, not an import table, so the bundle cannot set it.
- Receiver B on AM air: Menu > Settings > Radio Set > Other Func > AM Air/FM
  > AM Air on B, then the AM zone's own scan menu.
- NOAA, FM broadcast and the packet zone are selected by hand and never
  interrupt a scan.
- Switch Protocol to NXDN (menu item 33) to hear the NXDN users in `Business
  Digital` (`Comm Digital` on `atd890-scan`) and KC7BAE in `Ham NXDN`; DMR is
  silent while NXDN is selected.

### The AM zones' scan members do not survive the import

The one thing the 2026-09-12 round trip found. Every AM zone came back holding
all of its channels, and their `A Channel` is right, but the **`Scan Channel`
column is empty** on every one - the CPS's import does not carry it. It is in
:data:`~wasds150.export.atd890_diff.CPS_NORMALIZED_COLUMNS` so the rest of the
comparison can be read, but unlike the entries beside it that is a *loss*, not
a normalisation.

What it costs is not yet established: the air band may scan the whole AM zone
regardless of that column, in which case nothing is wrong. Check on the radio -
Menu > Settings > Radio Set > Other Func > AM Air/FM, pick `Air Local 01` and
start its scan. If it sweeps the zone, the column is decorative. If it sits on
one channel, the scan members have to be set on the radio or in the CPS by
hand, and this is worth solving properly.

### Read back and verify

After writing: Read from radio, Tool > Export > Export All into
`radio-data/at-d890uv/readbacks/<date>-readback/`, then compare it with the bundle:

```powershell
.\.venv\Scripts\python.exe scripts\radios\diff_atd890_export.py `
    --bundle radio-data\at-d890uv\exports\at-d890uv-fleet `
    --readback radio-data\at-d890uv\readbacks\<date>-readback
```

Rows are matched by name (channel, zone, scan list, talkgroup ID), `No.` is
ignored, frequencies compare numerically, and
zone/scan members that only changed order are listed but do not count. It exits
0 when the read-back matches and prints the SHA-256 of the bundle and each file.
Any other column the CPS rewrote is a bug in `CHANNEL_DEFAULTS`
(`src/wasds150/export/atd890_cps.py`), not something to ignore; a column the
CPS legitimately normalises goes in `CPS_NORMALIZED_COLUMNS`
(`src/wasds150/export/atd890_diff.py`) with the reason. The fleet update's
optional **Compare the read-back** step runs the same comparison. That round trip was made on 2026-09-12 and the profile is `verified=True`; the bundle hash is at the top of this page.

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
- **Scan lists hold 50 members**; long groups are chunked and the operator
  picks the chunk. The radio has no group-link scan across lists.
- **Air band is a separate receiver.** AM channels cannot be mixed into a
  VHF/UHF scan list; they scan from the B receiver's AM zone.
- **220 MHz** needs band mode 14, and the plan now assumes it: the `Ham 1.25m`
  zone is 28 coordinated repeaters within the radius. In mode 00007 the whole
  block drops out, which is the correct behaviour rather than an error.
- **Names are 16 characters**; labels are shortened readably
  (`W7JCR Prt Twnsnd`) and made unique per bundle.
