# TH-D75A programming reference folder

An inventory of every file in this folder: what it is, where it came from, and
whether it is worth anything to this project. Verified by reading each file on
2026-09-05 — the `.d75` contents below were decoded with the record layout in
[thd75_target.py](../src/wasds150/export/thd75_target.py), not assumed.

## Quick verdict

| File | What it is | Useful? |
| --- | --- | --- |
| `KWD_20240116_E.tsv` | Kenwood worldwide D-STAR repeater list, 1457 rows | **Yes — high.** Upstream source of `radio-backups/th-d75/dstar-within-50.tsv` |
| `Satellite_D75A.d75` | 83 Doppler-split satellite memories, slots 600–744, **US market** | **Yes — high.** Drop-in content for a satellite channel plan |
| `TH_D75_Commands.pdf` | Third-party serial command reference (KI4LAX) | **Yes — high.** The only doc for CAT/serial control |
| `TH-D75AE_IDM Operating Tips May_2024.pdf` | Kenwood's 68-page APRS/D-STAR/TNC deep dive | **Yes — medium.** Best APRS/KISS/reflector reference |
| `B5A-4505-00_01_EN.pdf` | Official 132-page TH-D75A/E User Manual | **Yes — medium.** Authoritative menu-number lookup |
| `NOCALL_DEFAULT.d75` | Factory-default MCP image, all 1000 memories empty | **Yes — narrow.** Clean-room export template |
| `ISS_D75_APRS_Default.d75` | Someone else's APRS-via-ISS config, incl. their callsign | **Marginal.** Read for settings, never write to the radio |
| `Kenwood-75a-part1.pdf` / `Kenwood 75A-part2.pdf` | The short printed User Guide, split in two | **No.** Subset of the full manual above |
| `Satellite_D75E/J/M.d75` | Europe / Japan / other-market satellite images | **No.** Wrong market for a TH-D75**A** |
| `Satellite_D74E.d74` | Same satellite set for the older TH-D74E | **No.** Previous-generation format |
| `VM_Instructions.txt` | Mac VM + USB passthrough notes for MCP | **No.** You already run MCP-D75 natively on Windows |
| `kenwoodkvm.txt` | Fedora/QEMU KVM version of the same | **No.** Same reason |

---

## Documentation

### `B5A-4505-00_01_EN.pdf` — 4.8 MB, 132 pages
The official **TH-D75A/E User Manual** (JVCKENWOOD, doc B5A-4505-00/01, Feb 2024).
The complete reference: every menu number, all memory/DV/GPS/APRS/TNC/Bluetooth
settings, band plans, and specifications.

**Useful.** This is the authority when a channel plan needs to justify a setting
by menu number — the repo's habit of citing sources maps onto it directly. Keep.

### `TH-D75AE_IDM Operating Tips May_2024.pdf` — 2.5 MB, 68 pages
Kenwood's **Operating Tips** supplement (April 2024). Goes past the manual into
practice: APRS operation and digipeater paths, D-STAR including the new
Reflector Terminal Mode, MMDVM serial compliance, the built-in KISS TNC and
standalone digipeater, the 1500-entry repeater list, and the 30-entry hotspot
list.

**Useful.** This is the document that explains *why* the D75's APRS/D-STAR
settings are shaped the way they are. Best single reference if you extend the
exporter past ordinary memories into APRS or D-STAR configuration.

### `Kenwood-75a-part1.pdf` (27 pp) + `Kenwood 75A-part2.pdf` (25 pp)
The short printed **User Guide** (B5A-4344-00, Oct 2023) split across two files
— part 1 is the cover, open-source licences and basic operation; part 2 picks up
mid-document at the GPS section (page 26 onward). Basic operations only, and it
points at the full manual URL on its own first page.

**Not useful.** Everything here is in `B5A-4505-00_01_EN.pdf` in more detail.
Safe to delete if you want the folder tidy.

### `TH_D75_Commands.pdf` — 253 KB, 16 pages
Third-party **serial command reference** by KI4LAX (Kevin Wnuk, May 2024).
Documents the TH-D75's two-letter CAT commands with read/set syntax, parameter
widths and value tables — `AE` serial number, `AG` volume, `BC` band control,
`BL` battery level, `BT` Bluetooth, `BY` squelch status, and so on.

**Useful — arguably the most useful PDF here.** Nothing in the official manuals
documents the serial protocol. If you ever want to read or poke live radio state
from Python (verify a write, capture current settings, drive the radio for the
antenna-measurement work) this is the spec you'd build against. Note it is
community-reverse-engineered, not vendor-guaranteed.

## Memory images (MCP-D75 `.d75` files)

All five `.d75` files are exactly 500,736 bytes — the same 256-byte header +
500,480-byte image format the exporter already reads and writes, so any of them
can be used as an export template without conversion.

### `Satellite_D75A.d75` — US-market satellite memory set
**83 ordinary memories at slots 600–744**, laid out as Doppler-tuning blocks:
each satellite gets ~5 consecutive channels stepped 5 kHz apart with the middle
one named `... Zen` (zenith / centre of the pass), so you rotate the dial
through the block as the bird moves. Contents:

- ISS: SSTV downlink (145.795–145.805), cross-band repeater (437.79–437.81),
  packet on 2 m (145.82–145.83) and 70 cm (437.54–437.56)
- FM/linear birds: SO-50, AO-27, AO-91, AO-92, AO-85, AO-95, PO-101, IO-86,
  RS-44 (plus a beacon channel), LilacSat-2, UVSQ-Sat, FO-118, TEVEL (9k6)
- US-only extras also present in this image: the 10 NOAA weather channels
  (`WX 1`–`WX 10`), 1.25 m call channels (`Call 220M FM/DV`), and APRS paths
  `ARISS` / `RS0ISS` / `APRSAT`

The ordinary memories below slot 600 are empty, and the D-STAR repeater list is
empty — so this file is a clean satellite overlay, not a full config.

**Useful — high.** It is a ready-made, correctly-Doppler-stepped satellite
channel block for exactly your market, sitting in slots your existing plans
don't use. Two ways to take it: decode the 83 records into catalog rows and
generate them like everything else (fits the repo's "one database" model), or
use this file as the export template so the satellite block survives untouched
while your plan writes the lower slots. Frequencies are 2024-vintage — AO-85,
AO-92 and PO-101 in particular are worth re-checking against AMSAT before you
count on them.

### `Satellite_D75E.d75`, `Satellite_D75J.d75`, `Satellite_D75M.d75`
The same 83 satellite memories for other market variants. Confirmed differences
from the `A` image: `E` (Europe) drops the NOAA weather channels, the 220 MHz
call channels and the US APRS paths; `J` (Japan) drops those too and adds 21
`TR1/TR2/TR3-Ch..` train channels; `M` is a third market variant, also without
the US extras but with the train group. Byte deltas vs. `A`: E 10,505, J 3,185,
M 826.

**Not useful.** Your radio is a TH-D75**A**. Writing a non-A image risks channels
outside your transmit bands. Keep only as evidence of what the `A` variant adds.

### `Satellite_D74E.d74`
The identical satellite list for the previous-generation **TH-D74E**, in
MCP-D74 V1.03 format. No 220 MHz channels, no weather channels.

**Not useful.** Wrong radio and wrong file format — the exporter's validator
rejects it.

### `NOCALL_DEFAULT.d75` — factory-default image
A pristine MCP-D75 read with **zero populated ordinary memories** and MYCALL
left at `NOCALL`. It does carry the full factory worldwide D-STAR repeater list
(Japanese repeaters, `JP1YLA`, `JR1VF`, etc.) and the default group names.

**Useful, narrowly.** [thd75_target.py](../src/wasds150/export/thd75_target.py)
picks the newest `.d75` in `radio-backups/th-d75/` as its template, which means
exports inherit whatever personal settings that backup carried. This file is the
alternative: a known-clean baseline for producing a shareable `.d75` with no
callsign, APRS identity or Bluetooth pairings in it. Worth keeping as a
`radio-templates/thd75-factory-default.d75` companion to the FTX-1 templates
that already live there.

### `ISS_D75_APRS_Default.d75` — someone else's APRS-via-ISS config
A complete personal configuration, not a template. One ordinary memory
(slot 0, 145.825 MHz, `ISS APRS`), APRS path set to `ARISS`, status text
"VIA ISS QSL contact information here", MYCALL/D-STAR fields set to `W1IXU`,
and roughly 4,500 strings including a captured APRS station list from the
US Southeast (`KI4LAX`, `AK4ZX-15`, `KF4TJY-9`, Georgia digipeaters, a personal
email address).

**Marginal, and do not upload it.** Writing it would put another operator's
callsign in your radio. The one thing worth extracting is the ISS APRS setup
itself — 145.825 simplex with the `ARISS` path — which is two settings you can
apply by hand or add to a plan. Treat this file as read-only reference.

## VM / connectivity notes

### `VM_Instructions.txt` — 3.5 KB
Written by Dylan Hawkins, 2024-10-20. How to run a Windows VM on a **MacBook**
(Parallels / VMware Fusion / VirtualBox) and pass a USB radio through to it for
firmware upgrades and MCP.

### `kenwoodkvm.txt` — 1.8 KB
The Linux equivalent: a Fedora 41 + QEMU/KVM host running a Windows 10/11 guest,
with the Kenwood `USB_CDC_Driver_TH-D75_V100` and `MCP-D75_V100` installed in the
guest and the radio redirected in via *View → Redirect USB device*. Also
mentions `ARFC-D75_V100` for computer control of the radio.

**Neither is useful to you.** You are on Windows 10 natively, so MCP-D75 and the
CDC driver install directly with no virtualization layer. Two details are worth
salvaging before you delete them: the exact Kenwood download names
(`USB_CDC_Driver_TH-D75_V100`, `MCP-D75_V100`, `ARFC-D75_V100`), and the tip
that MCP's channel grid hides the Tone column by default.

## Repeater data

### `KWD_20240116_E.tsv` — 456 KB, 1457 repeaters
Kenwood's official **worldwide D-STAR repeater list**, dated 2024-01-16, in the
tab-separated format MCP-D75 imports directly. 31 columns: world region, country,
group, callsign, gateway, name/sub-name, frequency, shift/offset, mode, tones,
position precision, latitude/longitude, time zone, and per-model flags. 953 US
entries, 99 Japan, 89 Canada, then Europe and Australia. Washington appears
under group `W7` — Seattle `WA7HJR B` on 444.6375, Bainbridge `W7NPC`, Bellevue
`K7LWH`, and so on.

**Useful — high, and it is already load-bearing.** `radio-backups/th-d75/dstar-within-50.tsv`
(21 repeaters) is a filtered subset of this exact file in this exact format —
I verified `W7NPC B` and `K7LWH B` match row-for-row. That means this TSV is the
upstream source for the D-STAR side of your catalog, and it is the file to
re-download when you want to refresh it. Two caveats: it is dated January 2024,
and its per-model flag columns are still `TH-D74A/E/74` — Kenwood had not added
D75 columns yet at that revision. Check
[manual.kenwood.com](https://manual.kenwood.com/) for a newer `KWD_*` release
before regenerating.

## Suggested cleanup

If you want to reduce this folder to what earns its place:

**Keep** — `KWD_20240116_E.tsv`, `Satellite_D75A.d75`, `NOCALL_DEFAULT.d75`,
`TH_D75_Commands.pdf`, `TH-D75AE_IDM Operating Tips May_2024.pdf`,
`B5A-4505-00_01_EN.pdf`.

**Drop** — `Kenwood-75a-part1.pdf`, `Kenwood 75A-part2.pdf`,
`Satellite_D75E/J/M.d75`, `Satellite_D74E.d74`, `VM_Instructions.txt`,
`kenwoodkvm.txt`. That removes about 8 MB and leaves nothing you can't
re-download from Kenwood.

**Before deleting `ISS_D75_APRS_Default.d75`**, note the one setting worth
keeping: ISS APRS is 145.825 MHz simplex with path `ARISS`.
