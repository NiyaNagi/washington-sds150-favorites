# Imagery

## Retrieved 2026-09-05 — King County 2025 orthomosaic

Three captures of the site, downloaded from the King County GIS aerial basemap
and **committed to this directory**. Earlier revisions of this file recorded
that no imagery could be saved; that is no longer true, and the georeferencing
problem it described is gone.

| File | Span | Centre (ENU from feed) | Scale | Size |
|---|---|---|---|---|
| `kc2025_wide.jpg` | 200 m | (0, 0) | 9.8 cm/px | 1.6 MB |
| `kc2025_close.jpg` | 90 m | (0, 0) | 4.4 cm/px | 987 KB |
| `kc2025_corridor.jpg` | 55 m | (14.6, −4.5) | 2.7 cm/px | 685 KB |
| `corridor_canopy.jpg` | 55 m | (14.6, −4.5) | 2.7 cm/px | generated overlay |

**Source.** `BaseMaps/KingCo_Aerial_2025` MapServer, a tile cache built from a
natural-colour orthomosaic flown by **EagleView Technologies** for King County.
3 in/px over urbanised western King County, **6 in/px over rural eastern King
County — which is this site.** The service is published openly by King County;
the underlying photography is governed by the county's licence agreement with
EagleView, so **credit both** wherever these are reproduced.

```
https://gismaps.kingcounty.gov/arcgis/rest/services/BaseMaps/
  KingCo_Aerial_2025/MapServer/export
    ?bbox=<xmin,ymin,xmax,ymax>&bboxSR=3857&imageSR=3857
    &size=2048,2048&format=jpg&f=image
```

Years 1936, 1998, 2000, 2002, 2005, 2007, 2009, 2012, 2013, 2015, 2017, 2019,
2021, 2023 and 2025 are all available under `BaseMaps/`. Older years would show
how the canopy around this site has changed, which nothing here has looked at.

### Georeferencing — exact by construction, not fitted

Each bbox was **requested** in EPSG:3857 around a computed centre, so the
pixel↔ground mapping is defined rather than estimated. There are no control
points and there is no residual to quote.

```
x = lon · 20037508.342789 / 180
y = ln(tan((90 + lat)·π/360)) · 20037508.342789 / π
```

Web Mercator units are metres only at the equator. At φ = 47.634° the local
scale factor is `1/cos φ = 1.48397`, so **1 real metre = 1.48397 map units**;
every bbox half-width below was computed as `span_m × 1.48397 / 2`.

Verified against all five operator-supplied points in
`../../tools/../deployment-siting-cn97ap/tools` (see `georef_check` output in
the session log): the feed lands on the north-east corner of the roof and the
front-yard/backyard corner marks fall along the east wall line, within the
±0.3 m the coordinates themselves are good for. Orthomosaic registration and
roof-overhang-versus-wall account for the rest.

---

## What the imagery changed

**62% of the antenna's ground path is over tree canopy**, measured by
`../tools/canopy_from_ortho.py`. Per span: 46%, 69%, 84%. The far support and
the end tie-off are both inside the woods.

**No open-ground route exists.** The mown lawn measures roughly 12 × 19 m
(40 × 62 ft), a 74 ft diagonal, against a 110 ft ground path. A radial scan
from the feed finds the longest clear run at about 24 ft, at 120°T.

This is the first direct evidence for a limitation `METHOD.md` had only been
able to state in general terms: **none of the models contain a tree-absorption
term**, and it now turns out that omission applies to most of the wire.

### Method, and its limits

`canopy_from_ortho.py` classifies canopy by **local texture**, not brightness —
mown grass is smooth at 2.7 cm/px and conifer canopy is not. Texture survives
the deep tree shadows lying across this lawn, which a brightness threshold does
not.

**It over-calls shadowed grass**, so the open-ground reaches it reports are
lower bounds. The headline conclusion does not rest on them: the lawn simply
measures smaller than the wire needs, which is direct measurement rather than
classification.

---

## Still missing: tree HEIGHTS

Positions can be read off the photograph. Heights cannot, and no canopy-height
model was obtainable:

| Source | Result |
|---|---|
| USDA FS `R06_lidar_R_CanopyHeight` ImageServer | HTTP 500 (2026-09-05, and previously) |
| USGS `3DEPElevation` ImageServer | **bare earth only** — no DSM, no surface return |
| WA DNR `lidarportal` / `Public_Lidar` | hillshade only; `Public_Lidar` folder is empty |
| King County `Imagery` folder | empty / restricted |

**Every tree height in this study is operator-supplied**: 50 ft usable at the
apex, 150 ft available at both yard corners. None is measured.

Two routes not yet tried, in order of promise:

1. **Shadow photogrammetry from these captures.** The shadows are long and
   sharp. With the acquisition date/time and sun elevation, `height = shadow
   length × tan(elevation)`. The capture time is not in the service metadata,
   but an orthomosaic tile's flight date usually is available from King County
   on request, and the house — whose footprint is known here to ±0.3 m — makes
   a usable calibration object.
2. **Raw LiDAR point clouds** from the WA DNR portal, which distributes tiles
   for manual download even where no DSM service exists.

---

## Superseded: the three chat screenshots

The original three captures in this session were chat attachments and could not
be written to disk. They are no longer needed — the county imagery is higher
resolution, exactly georeferenced, and reproducible from the URL above. Recorded
here only so a future agent does not go looking for them.

| Screenshot | Status |
|---|---|
| Oblique first capture (rotated ~90°) | not saved; superseded |
| North-up capture with 5 pins | not saved; superseded |
| Third capture with driveway corner | not saved; superseded |

The 11.73 px/m georeferencing figure quoted elsewhere in this study belongs to
those screenshots and is now irrelevant.
