# RFH-2 — JLCPCB ordering

Three separate uploads. JLCPCB takes one board design per zip, so these
cannot be combined into a single order without panelizing.

All three share the same 76 x 90 mm outline and the same four 5.0 mm
mounting holes, verified identical to the micron across all three archives.

## Upload 1 — `JLCPCB-1-RFH-2-cover.zip`

The faceplate. Generated from `RFH-2.brd`, so its outline, mounting holes
and plunger cutouts match the main board by construction.

The silkscreen carries an operating reference in the three gaps between the
switch rows: CW numerals and prosigns, the ITU phonetic alphabet, and antenna
and signal formulas. Body text is 1.2 mm high with a 0.20 mm stroke, above
JLCPCB's 0.15 mm silkscreen minimum, so it will print — but it is small, and
white on a dark mask reads best.

| Option | Value |
|---|---|
| Layers | 2 |
| Dimensions | 76 × 90 mm (auto-detected) |
| Thickness | **1.6 mm** |
| Surface finish | HASL (lead-free is fine) |
| Solder mask | any colour — green matches Jim's build |
| Silkscreen | white |
| Copper weight | 1 oz |
| Remove order number | "Specify a location" or "Yes" if you care about looks |

There is no copper on this board at all. The copper and paste layers are
intentionally empty. If the DFM viewer shows a blank copper layer, that is
correct, not a missing file.

The 12 plunger cutouts are 7.0 mm and live on the **outline layer**
(`.GKO`), not in the drill file, because JLCPCB's maximum plated drill is
6.3 mm. They will be routed. Expect a ~0.5 mm internal corner radius on
routed features — irrelevant here since the cutouts are circular.

## Upload 2 — `JLCPCB-2-RFH-2-mainboard.zip`

The upstream PY2RAF board, Revision C, unmodified. This is the same set the
project ships; it has been fabbed successfully before. I only flattened the
`CAMOutputs/` folder structure and dropped the `.gbrjob` file. Filenames are
otherwise untouched.

| Option | Value |
|---|---|
| Layers | 2 |
| Dimensions | 76 × 90 mm |
| Thickness | 1.6 mm |
| Everything else | defaults are fine |

## Upload 3 — `JLCPCB-3-RFH-2-bottom.zip`

The back plate. Plain 76 x 90 mm rectangle, four 5.0 mm mounting holes, no
cutouts. Closes the sandwich and protects the solder side.

Same fab options as the cover. Silkscreen is on the **bottom** side and
mirrored, so it reads correctly when you turn the unit over. Copper layers
are empty here too.

It must stand off from the main board — clipped resistor and switch leads
protrude from the solder side. Do not let it sit flat against them.

## Before you order the cover

Measure a real TL6300 body height first.

The plunger sits 7.30 mm above the main PCB. Protrusion above the cover is
`7.30 − standoff − 1.6`. A 4.5–5.0 mm standoff gives roughly 0.7–1.2 mm of
protrusion against 0.3 mm of switch travel. The body height I used to sanity
check that came from an ambiguous dimension table, not a measurement.

Print test spacers at 4.0 / 4.5 / 5.0 mm and check the fit against one real
switch before spending money on fab. Boards are cheap but the lead time is
not.

## Hardware not from JLCPCB

- 4 × M4 screws, long enough for the whole stack: cover + gap + main board + gap + bottom plate
- 8 × standoffs — four above the main board (height per the test above), four below
- The lower standoffs only need to clear clipped lead length, so 3-5 mm is plenty
- 3.5 mm TRS cable — cut one end off, wire tip and sleeve, leave the ring floating

## Credits

Board and legends: PY2RAF (`github.com/rfrht/RFH-2`), GPL-3.0.
Faceplate concept: Jim N5JGE.
