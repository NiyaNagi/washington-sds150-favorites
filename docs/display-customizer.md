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

## Layout starting points

Layout templates and color themes are independent. Changing themes preserves
the selected data layout; changing layouts preserves the theme. A template
sets displayed-item choices, then each selected data type inherits its logical
semantic color from the active theme.

| Template | Scenario |
|---|---|
| Sentinel Export | Exact attached export, including its intentional blanks |
| Dispatch Essentials | Service, tone, channel, system, site, and signal identification |
| Technical Diagnostics | RF noise, filter, error count, RSSI, network, and decoding diagnostics |
| Mobile & GPS | Coordinates, active site, GPS, signal, and power while roaming |
| Unit Identification | Unit ID/name fragments, TGID, system, site, service, and RSSI |
| SDS150 Telemetry | Battery current/temperature, USB voltage, filter, RF health, and power |
| Discovery & Close Call | Unknown-signal capture, search, repeater finding, and RF quality |
| Trunk Network Analysis | P25 network, site, talkgroup, unit, and decoding context |
| Aviation & Marine | Frequency, modulation, service, location, and signal strength |
| Recording & Alerts | Recording, priority, Close Call, weather, and active-state indicators |

Every scenario template except Sentinel Export fills every editable option
slot with a supported non-empty choice. Templates are starting points:
synchronized or per-screen edits remain available afterward, and reset returns
a field or view to the selected template rather than discarding the template.

## Color grouping choices

Color grouping is a third independent choice: **layout** selects the data,
**theme** supplies the actual supported colors, and **grouping** assigns those
theme colors to related fields. Changing any one preserves the other two.

| Grouping | Style | Behavior |
|---|---|---|
| Balanced Semantic | Basic | Logical color follows the selected data type |
| Basic Hierarchy | Basic | Distinct hierarchy and alerts with restrained secondary data |
| Full Spectrum Granular | Colorful | Colors every visible field by granular functional family |
| Maximum Spectrum Rows | Colorful | One distinct spectrum color per physical row |
| Rainbow Data Matrix | Colorful | Cycles all 18 spectrum colors across visible fields |
| Colorful Row Bands | Colorful | Distinct top, utility, hierarchy, detail, icon, and bottom rows |
| Top & Bottom Contrast | Rows | Strong top and bottom bands around semantic center rows |
| Alternating Data Rows | Rows | Alternating detail-row colors for horizontal scanning |
| Technical Heatmap | Scenario | Prominent receiver diagnostics and RF warnings |
| Activity & Alerts | Scenario | Prominent active channel, recording, and alert states |
| Hierarchy Focus | Scenario | Emphasized system/department/channel identity |
| Uniform Minimal | Accessibility | One foreground color except alerts |

Each theme now includes a generated 18-color extended spectrum. Every spectrum
color is an exact Sentinel-supported swatch with at least 4.5:1 contrast against
that theme's background. Full Spectrum Granular uses all 18 colors while related
fields still match: controls, date/time, signal/decoding, power, hierarchy
levels, info areas, icons, and soft keys receive consistent functional roles.
Near-white and near-black candidates are excluded when enough saturated choices
exist. Maximum Spectrum Rows preserves row relationships; Rainbow Data Matrix
prioritizes the strongest possible field-to-field separation.

Generated scenario layouts also deduplicate displayed Huge/Large data within
each individual screen. A hierarchy field such as Frequency, TGID, Site Name,
or System ID is therefore not repeated in a secondary data slot; a different
supported scenario-relevant field is substituted automatically. Repeated fixed
controls and independent status icons remain intentional.

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
the exact option tables extracted from the installed Sentinel application.
Small option areas include Date, Time, Digital
Status, TDMA Slot, Bluetooth, Attenuator, GPS, IFX, modulation, priority,
recording, Close Call, Weather Priority, volume, and squelch. Larger areas can
show Favorites List, site, frequency, TGID, service type, tone/NAC, system and
site IDs, WACN, battery current/temperature/voltage, USB voltage, filter,
noise, error count, coordinates, unit ID/name fragments, RSSI, number tag, and
volume/squelch details.
Icon areas are restricted to the compatible icon choices.

Choices are constrained by Sentinel's actual field type: Huge, Large, Small,
Icon, or fixed. This safely unlocks editable blank option and icon slots in
Search, Weather, and Tone Out while preserving fixed labels and geometry.
Synchronized choices are limited to the intersection supported by all matching
editable fields.

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
- Weather and Tone Out retain their fixed geometry while templates may populate
  their supported Small, Large, and Icon option slots.
- Icons consistently expose modulation, priority channel, IFX, level, record,
  GPS, priority, Close Call, and Weather Priority where the mode supports them.

The official manual notes that conventional and trunk modes share colors while
allowing different items, that not every item fits every field, and that the
scanner can switch between Simple/Detail with **F+DISP**. It also provides
black-on-white and white-on-black sunlight modes through **F**, then holding
**DISP** for three seconds.

## Preview and import

1. Start the local dashboard and open **Display**.
2. Select a scenario layout starting point.
3. Select a color theme and preview all seven modes on one page.
4. Inspect the displayed minimum contrast and individual swatch ratios.
5. Select **Download selected Sentinel XML**.
6. In Sentinel use **File > Import Display Customizing Settings**.
7. Open the display customizer, inspect every mode, save the profile, and write
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
