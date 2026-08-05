# SDS100/SDS150 Display Customizer Palettes

The dashboard's **Display** tab previews and exports coordinated display
customizations for all seven Sentinel modes:

1. Simple Conventional
2. Simple Trunk
3. Detail Conventional
4. Detail Trunk
5. Search/Close Call
6. Weather
7. Tone Out

The checked-in [Sentinel export](display.xml) is the structural reference.
Generated files retain its exact seven screen names, item names, option codes,
ordering, `SDS100` model value, and Uniden's exported `UndienScanner` root
spelling. The current SDS-series specification identifies SDS150 support, but
the compatible display interchange format retains this established root/model
shape.

## Design goals

Colors have one meaning across every display mode:

| Semantic group | Content |
|---|---|
| System | System name and Favorites List name |
| Department/site | Department name, department detail, and site name |
| Channel | Channel name, frequency, TGID, primary result, and special-mode modulation/detail context |
| Metadata | Service type, tone/NAC, IDs, WACN, battery, RSSI, and detail information |
| Status | Time, date, signal, volume/squelch, and fixed utility labels |
| Alert | Avoid, Hold, Close Call, and Weather Priority |
| Active/accent | GPS, recording, priority, P-channel, IFX, and other active icons |

This grouping makes the hierarchy recognizable by color before the text is
read. Text/background pairs are checked with the WCAG relative-luminance
formula as a conservative readability heuristic. Every supplied pair is at
least 4.5:1; preset minimums range from 5.62:1 to 9.38:1. Scanner brightness,
viewing angle, direct sunlight, and color vision still affect practical
readability, so the tab provides full visual previews before export.

## Included palettes

| Palette | Background | System | Department/site | Channel | Metadata | Alert | Minimum contrast |
|---|---|---|---|---|---|---|---:|
| Night Ops | `#000000` | `#38BDF8` | `#FB923C` | `#FDE047` | `#C4B5FD` | `#FB7185` | 7.80:1 |
| Daylight High Contrast | `#FFFFFF` | `#075985` | `#9A3412` | `#713F12` | `#5B21B6` | `#B91C1C` | 6.47:1 |
| Colorblind Dark | `#0B0F14` | `#56B4E9` | `#E69F00` | `#F0E442` | `#CC79A7` | `#F25F5C` | 5.62:1 |
| Low-Light Amber | `#000000` | `#FF6B35` | `#FF9F1C` | `#FFD166` | `#E6A8D7` | `#FF4D6D` | 6.53:1 |
| Oceanic | `#001219` | `#5BC0EB` | `#F4A261` | `#E9C46A` | `#CDB4DB` | `#FF758F` | 7.44:1 |
| Forest Watch | `#071A12` | `#74C69D` | `#F4A261` | `#F9C74F` | `#B8C0FF` | `#FF6B6B` | 6.49:1 |
| Cyber Neon | `#090014` | `#00E5FF` | `#FF9E00` | `#F9F871` | `#D58BFF` | `#FF4D9D` | 6.66:1 |
| Solar Dark | `#002B36` | `#6FC2BB` | `#F4A261` | `#EBCB8B` | `#C7B5E8` | `#FF7B72` | 5.95:1 |
| Solar Light | `#FDF6E3` | `#075985` | `#9A3412` | `#6B4F00` | `#6D28D9` | `#B91C1C` | 6.00:1 |
| Monochrome Ice | `#06111C` | `#BDE0FE` | `#A2D2FF` | `#E0FBFC` | `#CDB4DB` | `#FF8FA3` | 8.79:1 |
| Purple Dusk | `#160B2D` | `#9BD1E5` | `#FFADAD` | `#FFE66D` | `#D0BFFF` | `#FF7096` | 7.15:1 |
| Slate Professional | `#111827` | `#7DD3FC` | `#FBBF24` | `#FDE68A` | `#C4B5FD` | `#FDA4AF` | 9.38:1 |

**Night Ops** is the balanced default. **Daylight High Contrast** is intended
for bright environments. **Colorblind Dark** uses an Okabe-Ito-inspired
separation. **Low-Light Amber** limits cool light while keeping alerts distinct.
Oceanic, Forest Watch, Cyber Neon, Solar Dark/Light, Monochrome Ice, Purple
Dusk, and Slate Professional provide additional environment and style choices.

## Full customization

Open **Customize palette** below the presets to edit at three levels:

1. **Semantic groups** — change system, department/site, channel, metadata,
  status, alert, accent, or background once and update every matching field.
2. **Matching items across views** — keep synchronization enabled, then change
  an item's text or background color to apply that item consistently to all
  seven modes where it appears.
3. **One item in one view** — disable synchronization and edit an individual
  field without affecting any other screen.

The view-level controls can apply one text or background color to every item
in the selected mode. Each item row displays its effective contrast and has a
reset button. The summary reports the minimum effective contrast and counts
items below 4.5:1 immediately; custom colors are permitted so users can make
intentional tradeoffs, but low-contrast items are clearly flagged.

Custom palettes can be named and saved in browser local storage, reloaded or
deleted, and exported/imported as JSON for backup or sharing. Sentinel XML is
always generated server-side from the current semantic and item overrides and
validated before download.

## Information layout

The item layout follows the supplied Sentinel export and the official list of
field capabilities:

- Simple screens prioritize Bluetooth, date/time, volume, squelch, P25 status,
  TDMA slot, Favorites List, service type, and tone/NAC.
- Conventional screens show frequency; trunk screens show TGID and site name.
- Detail screens add volume/squelch, number tag, system/network ID, RFSS/site
  ID, WACN, battery voltage, unit ID, and RSSI.
- Search adds system ID, unit ID, TGID, RSSI graph, Broadcast Screen, and
  Repeater Find.
- Weather and Tone Out retain their compatible fixed layout while suppressing
  search-only fields.
- Icons consistently expose modulation, priority channel, IFX, level, record,
  GPS, priority, Close Call, and Weather Priority where the mode supports them.

The official manual notes that conventional and trunk modes share colors while
allowing different items, that not every item fits every field, and that the
scanner can switch between Simple/Detail with **F+DISP**. It also provides
black-on-white and white-on-black sunlight modes through **F**, then holding
**DISP** for three seconds.

## Preview and import

1. Start the local dashboard and open **Display**.
2. Select each palette card to preview all seven modes on one page.
3. Inspect the displayed minimum contrast and individual swatch ratios.
4. Select **Download selected Sentinel XML**.
5. In Sentinel use **File > Import Display Customizing Settings**.
6. Open the display customizer, inspect every mode, save the profile, and write
   it to the scanner normally.

The generated XML is validated before download. Validation covers the root
attributes, seven-screen set, exact item names/options/order, RGB syntax, and
minimum palette contrast.

## Sources

- Uniden, *SDS100 Owner's Manual*, pp. 40-44, “Customizing the Display” and
  “Available Items”: https://www.uniden.info/download/ompdf/SDS100om.pdf
- Uniden America, *SDS100/150/200 File Specification*, version 2.00,
  `DispOptItems`, `DispColors`, display-layout IDs, and SDS150 support:
  https://info.uniden.com/twiki/pub/UnidenMan4/SDS100FirmwareUpdate/SDS_Series_File_Specification_V2_00.pdf
- RadioReference community thread confirming Sentinel XML import/export under
  the File menu and the exported `UndienScanner` spelling:
  https://forums.radioreference.com/threads/share-your-sds100-display-customizing-settings.373308/

Community examples informed usability review only. Screen structure and option
codes are grounded in the supplied Sentinel export and official Uniden material.
