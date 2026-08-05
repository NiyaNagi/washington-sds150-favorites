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

The browser previews use the same canonical item indices as that export rather
than a separate approximation. Every XML item appears exactly once: 40 items
for each Simple screen, 50 for each Detail screen, and 45 for Search, Weather,
and Tone Out. Repeated names such as the three `Avoid` fields remain distinct
by index. Text and background colors are always previewed in the same direction
written to XML; `Func` has no special inversion.

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
least 4.5:1; preset minimums range from 5.07:1 to 7.99:1. Scanner brightness,
viewing angle, direct sunlight, and color vision still affect practical
readability, so the tab provides full visual previews before export.

## Included palettes

| Palette | Background | System | Department/site | Channel | Metadata | Alert | Minimum contrast |
|---|---|---|---|---|---|---|---:|
| Night Ops | `#000000` | `#00BDFF` | `#FF8800` | `#FFD600` | `#E79473` | `#FF108C` | 5.70:1 |
| Daylight High Contrast | `#FFFFFF` | `#000084` | `#840000` | `#526B29` | `#4A007B` | `#AD2121` | 6.01:1 |
| Colorblind Dark | `#000000` | `#00BDFF` | `#FFA100` | `#FFFF00` | `#D66FD6` | `#FF7F4A` | 7.10:1 |
| Low-Light Amber | `#000000` | `#FF4600` | `#FFA100` | `#FFD600` | `#E79473` | `#FF108C` | 5.70:1 |
| Oceanic | `#00007B` | `#84CAF7` | `#FFA100` | `#FFD600` | `#D6BDD6` | `#FF7F4A` | 6.52:1 |
| Forest Watch | `#000000` | `#8CEB8C` | `#FFA100` | `#FFFF00` | `#DEE3F7` | `#EF7F7B` | 7.99:1 |
| Cyber Neon | `#000000` | `#00FFFF` | `#FF8800` | `#FFFF00` | `#E780E7` | `#FF108C` | 5.70:1 |
| Solar Dark | `#294E4A` | `#84CAF7` | `#FFE3BD` | `#FFF7C6` | `#D6BDD6` | `#FFB1BD` | 5.16:1 |
| Solar Light | `#FFF7D6` | `#000084` | `#840000` | `#526B29` | `#4A007B` | `#AD2121` | 5.59:1 |
| Monochrome Ice | `#18186B` | `#ADD6DE` | `#84CAF7` | `#DEFFFF` | `#D6BDD6` | `#EF7F7B` | 5.78:1 |
| Purple Dusk | `#4A007B` | `#ADD6DE` | `#FF9C73` | `#FFFF00` | `#D6BDD6` | `#FFB1BD` | 6.50:1 |
| Slate Professional | `#294E4A` | `#84CAE7` | `#FFE3BD` | `#FFFFDE` | `#D6BDD6` | `#FFB1BD` | 5.07:1 |

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
items below 4.5:1 immediately; custom combinations are permitted so users can
make intentional tradeoffs, but low-contrast items are clearly flagged.

Custom palettes can be named and saved in browser local storage, reloaded or
deleted, and exported/imported as JSON for backup or sharing. Sentinel XML is
always generated server-side from the current semantic and item overrides and
validated before download.

Every field in every visual preview is clickable and keyboard-accessible.
Selecting a field opens a focused editor with:

- all 147 colors from Sentinel's exact internal display-color table, grouped
  into neutrals and hue families and ordered from dark to light within each
  family;
- search by color name, hue family, or hexadecimal value;
- remembered recently selected supported colors across pages and browser
  sessions;
- supported-only text/background selectors for semantic, item, and view edits;
- live contrast feedback;
- a synchronized/per-view application switch; and
- a **Displayed item** selector when Sentinel allows that field to change.

The item editor uses a bounded, scrollable color browser so the action buttons
remain available even with all 147 colors. Current text/background colors are
shown as compact target cards, selected swatches are outlined, and the editor
becomes a full-height sheet on small screens. The same controls remain usable
with touch, mouse, or keyboard, including focus trapping and Escape-to-close.

Displayed-item choices follow the supplied screenshots, Sentinel export, and
official available-item list. Small option areas include Date, Time, Digital
Status, TDMA Slot, Bluetooth, Attenuator, GPS, IFX, modulation, priority,
recording, Close Call, Weather Priority, volume, and squelch. Larger areas can
show Favorites List, site, frequency, TGID, service type, tone/NAC, system and
site IDs, WACN, battery, unit ID, RSSI, number tag, and volume/squelch details.
Icon areas are restricted to the compatible icon choices.

Choices are constrained per field and screen rather than exposing one unsafe
global list. Metadata slots can keep their exported item or be emptied;
frequency/TGID and site/department fields only offer their evidenced variants.
As specified by the official manual, Weather and Tone Out retain fixed items
and support color customization only. Synchronized item choices are limited to
the intersection supported by all compatible editable views.

With synchronization enabled, both the color and displayed-item selection are
remembered for the same field across all seven modes. Disable synchronization
to customize one screen only. Preview labels update immediately to reflect the
actual selected element that will be written into the XML.

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
attributes, seven-screen set, exact item names/options/order, membership in
Sentinel's 147-color table, and minimum palette contrast. Unsupported RGB
values are rejected from API payloads, imported JSON, and saved browser data
rather than being written into XML that Sentinel may silently ignore.

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
The exact color names, values, and ordering were extracted from the installed
Sentinel `DispColorItemList.table`; no screenshot approximation or generated
RGB interpolation is used.
