# Imagery used in the CN97ap siting study

## The source images are NOT in this repository

The operator supplied three Google Earth screenshots as chat attachments during the
2026-09-05 session. They existed only in the conversation, never as files on disk, so
they could not be written here. **This directory documents them completely so the
analysis is reproducible, but the pixels themselves are missing.**

To complete the record, save the originals into this directory using the filenames in
the table below and delete this paragraph.

| Suggested filename | What it is | Status |
|---|---|---|
| `01-oblique-initial.png` | First screenshot, 2185×1632, rotated/oblique view with a blue path drawn | **missing** |
| `02-northup-pins.png` | Second screenshot, 2048×1464, north-up with 5 labelled pins | **missing** |
| `03-northup-pins-driveway.png` | Third screenshot, 2048×1463, north-up with 6 pins incl. `front yard drive way corner` | **missing** |

Imagery date on the north-up captures: **2026-06-06**. Attribution: Google Earth,
underlying imagery © 2026 Airbus (visible on the first capture).

---

## Image 1 — the rotated one (do not georeference from this)

The first screenshot was **not north-up**. Its blue path ran "up then bent right" while
the coordinates for the same points describe a run heading roughly east then southeast —
a discrepancy of about 90°.

This was caught, queried, and resolved: the operator confirmed **the coordinates are
authoritative and the view was rotated**. Google Earth screenshots after a rotate or tilt
are not north-up and may also be obliquely projected, so scale varies across the frame.

**Lesson for a future agent: never georeference from a Google Earth capture without
confirming north-up.** Ask for the compass rose to be visible, or verify against two
known points before trusting any pixel measurement.

---

## Images 2 and 3 — north-up, georeferenced and validated

North-up confirmed by the compass rose in the top-right corner.

### Scale derivation

Established from the `start`→`apex` pin pair, whose true separation is known from the
coordinates (16.01 m):

- Pin pixel positions (in the 2000 px-wide *displayed* frame): `start` ≈ (1192, 738–745),
  `apex` ≈ (1378, 712–718)
- Pixel delta ≈ (+186, −27), length ≈ 188 px
- **Scale ≈ 11.73 px/m** in the displayed frame
- Multiply by 1.02 to map displayed → original 2048 px coordinates

### Validation against every other pin

| Pin | From image (E, N) m | From coordinates (E, N) m | Agreement |
|---|---|---|---|
| `apex` | +15.9, +2.3 | +15.87, +2.16 | ✓ |
| `end` | +22.4, −5.7 | +22.13, −6.18 | ✓ |
| `backyard corner` | +5.1, −11.1 | +5.22, −11.12 | ✓ |
| `front yard corner` | −4.4, +6.0 | −3.97, +5.87 | ✓ |
| `front yard drive way corner` | −18.50, −4.43 | −18.37, −4.63 | ✓ |

All within ~0.5 m — comfortably inside the ±0.3 m precision of the operator's
0.01-arcsecond coordinates plus pixel-reading error. **The georeferencing is sound and
the coordinate math in `../data/site-points.json` is independently confirmed.**

### What the imagery established that coordinates alone could not

1. **`start` is the northeast corner of the house**; `backyard corner` is the southeast
   corner. This answered the "does the wire clear the house?" question.
2. **The wire run is entirely over open lawn.** The clearing extends from the house wall
   roughly 30 m southeast to a conifer treeline. Both legs stay on it.
3. **The far support lands right at the southeast treeline** — good news, because it
   means a tree is plausibly available where the design wants one. Still needs ground
   verification.
4. **A light cylindrical object** (propane tank?) sits roughly 9 m from the feed at
   bearing 142°, about 26 ft laterally from leg 1. Flagged as an unverified hazard in
   `../data/site-points.json`.
5. **A driveway corridor** runs northwest from the turnaround at roughly 320° for about
   60 m. This was evaluated as deployment option C and rejected — see
   `../data/deployment-options.json`.
6. **Dense conifer forest surrounds the clearing on all sides.** Relevant because the
   USGS terrain data is bare-earth and does not model canopy.

### House footprint

Traced by eye from image 2 and used only as context in the plan drawing. Approximate
local ENU polygon, metres from the feed:

```
(0, 0) → (−15.5, +0.3) → (−20, −12) → (−13, −24) → (+2, −20) → (+5.2, −11.1) → close
```

**This is not survey data.** King County parcel geometry was retrieved
(`../data/parcel-1117200390.json`) but building footprints were not. If precise house
clearance ever matters, query a building-footprint layer or measure on the ground.

---

## Published figures

The session produced two scale drawings, both authored as inline SVG in the published
artifact rather than as image files:

- **Plan view** — true scale, north up: parcel line, house, lawn, the four supports, span
  labels, clearance callouts, scale bar
- **Side elevation** — the wire unfolded along its path, 24 → 50 → 50 → 30 ft, vertical
  scale exaggerated ~2×
- **Horizon rose** — polar plot of terrain obstruction by bearing with the two wire legs
  overlaid

Artifact: <https://claude.ai/code/artifact/1128955c-5f0e-44c7-82a9-a08a9f9d2fa9>

The SVG source is embedded in that page. All three can be regenerated from
`../data/terrain-samples.json` and `../data/final-design.json`.
