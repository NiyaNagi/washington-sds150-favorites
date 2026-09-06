#!/usr/bin/env python3
"""Estimate tree heights from shadows in the King County 2025 ortho.

No canopy-height model was obtainable for this site (four sources tried, see
imagery/README.md) and no LAZ reader is available in this environment, so the
point-cloud route is closed too. Shadows are what is left, and the imagery is
unusually good for it: 2.7 cm/px with long, sharp shadows.

    height = shadow_length * tan(solar_elevation)

Two unknowns, obtained separately:

  SOLAR AZIMUTH is measured from the image, by cross-correlating a mask of
  sunlit roof against a mask of deep shadow. The house casts a shadow of its
  own shape; the offset that best aligns the two masks is the shadow vector.
  This needs no external data at all.

  SOLAR ELEVATION cannot be measured without one known height or the flight
  date, neither of which is available - King County publishes no flight index
  for this basemap. But it is not free either: for a given latitude, azimuth
  and solar declination, elevation follows from spherical astronomy

      sin(dec) = sin(lat) sin(h) + cos(lat) cos(h) cos(azimuth)

  so the leaf-on state of the canopy (which brackets the date) brackets the
  elevation, and therefore brackets every height. The bracket is reported
  rather than hidden in a point estimate.

CONFIDENCE: MODERATE for relative heights, LOW-MODERATE for absolute. The
shadow lengths are measured at 2.7 cm/px; the elevation bracket is the
dominant error. ONE number from the operator - the height of their own roof
ridge or eave - collapses the bracket to a single value and turns every figure
here from an estimate into a measurement.

    python3 .../tools/shadow_heights.py
"""

import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_geometry import FEED                                   # noqa: E402

FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, "..", "imagery")
LAT = FEED[0]

# Neighbouring house in the 200 m frame - isolated, simple roof, clean ground
# around it, which is what the correlation needs. Pixel box in kc2025_wide.jpg.
BOX = (1230, 300, 1780, 760)
WIDE_SPAN_M = 200.0

# Leaf-on brackets the flight window. Solar declination at the extremes.
LEAFON = [("early May / early Aug", 16.0), ("mid May / late Jul", 19.5),
          ("June solstice", 23.44)]

# Physically possible sun azimuths at 47.6 N. At the June solstice the sun
# rises about 55 deg and sets about 305 deg; it is never north of that, so a
# shadow implying a sun outside this arc is a false correlation lock.
SUN_AZ_MIN, SUN_AZ_MAX = 55.0, 305.0


def solar_elevation(lat_deg, dec_deg, azimuth_deg):
    """Elevation at which the sun sits at this azimuth, for this declination.

    Solves sin(dec) = sin(lat) sin(h) + cos(lat) cos(h) cos(az) for h.
    Written as R*cos(h - phi) = sin(dec) and solved directly.
    """
    lat, dec, az = map(math.radians, (lat_deg, dec_deg, azimuth_deg))
    a = math.sin(lat)                      # coefficient of sin h
    b = math.cos(lat) * math.cos(az)       # coefficient of cos h
    r = math.hypot(a, b)
    if abs(math.sin(dec) / r) > 1:
        return None
    phi = math.atan2(b, a)                 # a sin h + b cos h = r sin(h + phi)
    h = math.asin(math.sin(dec) / r) - phi
    return math.degrees(h)


def shadow_vector(img_path, box, span_m):
    """Measured shadow offset in metres (east, north) and its azimuth."""
    im = Image.open(img_path).convert("RGB")
    ppm = im.size[0] / span_m
    crop = im.crop(box)
    a = np.asarray(crop).astype(np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    sat = a.max(2) - a.min(2)

    # Sunlit roof: bright and grey (low saturation). Deep shadow: very dark.
    roof = ((lum > 118) & (sat < 34)).astype(np.float32)
    shade = (lum < 62).astype(np.float32)
    roof -= roof.mean()
    shade -= shade.mean()

    # Brute-force correlation over plausible shadow offsets (<= 25 m).
    #
    # CONSTRAINED to physically possible sun positions. The first run of this
    # tool locked onto tree canopy south of the house and reported a sun
    # azimuth of 341 deg - the sun is never in the north at 47.6 N, and the
    # leaf-on elevation solver returned "no solution", which is how the error
    # was caught. Offsets implying an impossible sun are now rejected outright
    # rather than left for a sanity check downstream.
    def sun_az_of(dx, dy):
        return (math.degrees(math.atan2(dx, -dy)) + 180.0) % 360

    lim = int(min(25.0 * ppm, min(crop.size) * 0.42))
    best = None
    step = 2
    for dy in range(-lim, lim + 1, step):
        for dx in range(-lim, lim + 1, step):
            if dx * dx + dy * dy < (3 * ppm) ** 2:
                continue
            if not (SUN_AZ_MIN <= sun_az_of(dx, dy) <= SUN_AZ_MAX):
                continue
            rs = roof[max(0, -dy):roof.shape[0] - max(0, dy),
                      max(0, -dx):roof.shape[1] - max(0, dx)]
            ss = shade[max(0, dy):shade.shape[0] - max(0, -dy),
                       max(0, dx):shade.shape[1] - max(0, -dx)]
            if rs.size < 5000:
                continue
            score = float((rs * ss).sum()) / rs.size
            if best is None or score > best[0]:
                best = (score, dx, dy)
    _, dx, dy = best
    # refine at 1 px
    for ddy in range(-step, step + 1):
        for ddx in range(-step, step + 1):
            x, y = dx + ddx, dy + ddy
            if not (SUN_AZ_MIN <= sun_az_of(x, y) <= SUN_AZ_MAX):
                continue
            rs = roof[max(0, -y):roof.shape[0] - max(0, y),
                      max(0, -x):roof.shape[1] - max(0, x)]
            ss = shade[max(0, y):shade.shape[0] - max(0, -y),
                       max(0, x):shade.shape[1] - max(0, -x)]
            if rs.size < 5000:
                continue
            score = float((rs * ss).sum()) / rs.size
            if score > best[0]:
                best = (score, x, y)
    _, dx, dy = best
    east, north = dx / ppm, -dy / ppm          # image y is south-positive
    length = math.hypot(east, north)
    shadow_az = math.degrees(math.atan2(east, north)) % 360
    sun_az = (shadow_az + 180.0) % 360
    return east, north, length, shadow_az, sun_az, ppm


def main():
    path = os.path.join(IMGDIR, "kc2025_wide.jpg")
    e, n, L, saz, sunaz, ppm = shadow_vector(path, BOX, WIDE_SPAN_M)
    print("=" * 74)
    print("SOLAR GEOMETRY, measured from the image")
    print("=" * 74)
    print(f"  scale                 {ppm:.3f} px/m ({100/ppm:.1f} cm/px)")
    print(f"  shadow offset         E{e:+.2f} m, N{n:+.2f} m")
    print(f"  shadow length         {L:.2f} m ({L/FT:.1f} ft)")
    print(f"  shadow points toward  {saz:.1f} deg true")
    print(f"  SUN AZIMUTH           {sunaz:.1f} deg true")
    print(f"  -> sun is in the "
          f"{'east' if 45 < sunaz < 135 else 'south' if 135 <= sunaz <= 225 else 'west' if 225 < sunaz < 315 else 'north'}"
          f", so this is a "
          f"{'morning' if sunaz < 180 else 'afternoon'} capture")

    print("\n" + "=" * 74)
    print("SOLAR ELEVATION - bracketed by the leaf-on flight window")
    print("=" * 74)
    print("  The canopy is in full leaf, so the flight is May-August.")
    print(f"  {'window':24s} {'declination':>12s} {'elevation':>10s} "
          f"{'tan(h)':>8s}")
    elevs = []
    for name, dec in LEAFON:
        h = solar_elevation(LAT, dec, sunaz)
        if h is None or h <= 2:
            print(f"  {name:24s} {dec:11.2f}d   no solution")
            continue
        elevs.append((name, dec, h))
        print(f"  {name:24s} {dec:11.2f}d {h:9.2f}d {math.tan(math.radians(h)):8.3f}")
    if not elevs or sunaz >= SUN_AZ_MAX - 1 or sunaz <= SUN_AZ_MIN + 1:
        print(f"""
  FAILED - and deliberately not papered over.

  The correlation pinned to the edge of the physically allowed arc, which
  means it never found the house shadow at all. It is matching dark tree
  canopy, not shadow cast by the roof.

  WHY THIS SCENE DEFEATS THE METHOD. The direction can be settled by
  elimination from the imagery: the driveway north-east of the reference
  house is fully lit while the strip north-west of it is dark, so shadows
  fall toward the north-west and the sun is in the SOUTH-EAST - a morning
  capture. But that puts the house's shadow onto dark asphalt driveway and
  into the treeline, with no bright uniform surface behind it. The lawn,
  which is the one good projection screen on this property, is on the
  sunlit side. There is nothing for a shadow-length measurement to bite on.

  SO: sun in the south-east, morning. Elevation unknown, and therefore no
  tree heights. Rather than publish a number this scene cannot support,
  this tool stops here.

  WHAT WOULD FIX IT, cheapest first:

  1. Measure ONE height on the ground - your own roof ridge or eave, or any
     fence post - and pair it with its shadow on a day you note the time.
     Two minutes with a tape. That calibrates every shadow in the frame.
  2. Better still, skip the photogrammetry: measure the trees directly with
     a phone clinometer app, or the stick method. More accurate than
     anything derivable from this image, and it also answers the question
     that actually matters - whether a usable limb exists at 50 ft - which
     no overhead view can ever show.
  3. The flight date from King County would give the elevation outright,
     but they publish no flight index for this basemap.

  The 62% canopy finding does NOT depend on any of this. It is measured
  from the plan view alone and stands on its own.""")
        return
    hlo = min(h for _, _, h in elevs)
    hhi = max(h for _, _, h in elevs)
    print(f"\n  Elevation bracket: {hlo:.1f} to {hhi:.1f} deg")

    print("\n" + "=" * 74)
    print("HEIGHT PER METRE OF SHADOW, and what the reference house implies")
    print("=" * 74)
    tlo, thi = math.tan(math.radians(hlo)), math.tan(math.radians(hhi))
    print(f"  height = shadow_length x tan(h)  ->  "
          f"{min(tlo,thi):.3f} to {max(tlo,thi):.3f} m per metre of shadow")
    print(f"\n  The reference house's own shadow is {L:.2f} m long, which makes")
    print(f"  its height {L*min(tlo,thi):.1f} to {L*max(tlo,thi):.1f} m "
          f"({L*min(tlo,thi)/FT:.0f} to {L*max(tlo,thi)/FT:.0f} ft).")
    print("  A two-storey house with a pitched roof is about 25-30 ft to the")
    print("  ridge. If that bracket does not contain 25-30 ft, the correlation")
    print("  has locked onto the wrong feature and nothing below is usable.")

    print("\n" + "=" * 74)
    print("WHAT ONE NUMBER FROM THE OPERATOR WOULD DO")
    print("=" * 74)
    for hft in (22, 25, 28, 32):
        h = math.degrees(math.atan2(hft * FT, L))
        print(f"  if that roof is {hft:2d} ft ->  solar elevation {h:5.2f} deg, "
              f"tan {math.tan(math.radians(h)):.3f}, so a 100 ft shadow is a "
              f"{100*math.tan(math.radians(h)):.0f} ft tree")
    print("\n  Measuring one roof or one fence post on the ground collapses the")
    print("  bracket entirely and turns every tree height here into a")
    print("  measurement rather than an estimate.")


if __name__ == "__main__":
    main()
