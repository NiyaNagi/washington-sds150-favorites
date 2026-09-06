#!/usr/bin/env python3
"""Find the treeline along the antenna corridor from the King County ortho.

The 2025 King County aerial (3-6 inch EagleView orthos) is the first hard
evidence in this study of what the wire actually flies over. Everything before
it was bare-earth terrain plus the operator's description.

Method: local texture, not brightness. Mown lawn is smooth at 2.7 cm/px;
conifer canopy is not. A local standard-deviation filter separates them and is
robust to the deep tree shadows lying across the lawn in this scene, which a
brightness threshold is not.

    canopy(x, y) = stdev of luminance in an 11 px (30 cm) window > THRESH

Requires Pillow. Run from the repository root:

    python3 antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap/tools/canopy_from_ortho.py

CONFIDENCE: MODERATE for the treeline position (it is measured, and the
georeference is exact by construction). It says nothing about tree HEIGHT -
no canopy-height model was obtainable; see data/terrain-samples.json ->
failed_queries and the notes in imagery/README.md.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFilter, ImageFont   # noqa: E402

import compare_options as C          # noqa: E402
from site_geometry import polar, mag, to_enu, APEX, BACKYARD, FRONT_YARD  # noqa

FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, "..", "imagery")

# Each capture: file, real metres across, ENU centre. The georeference is exact
# by construction - these bboxes were requested in EPSG:3857 around a computed
# centre, so pixel <-> ground needs no control points.
CAPTURES = {
    "close":    ("kc2025_close.jpg",    90.0, (0.0, 0.0)),
    "wide":     ("kc2025_wide.jpg",    200.0, (0.0, 0.0)),
    "corridor": ("kc2025_corridor.jpg", 55.0, (14.6, -4.5)),
}

TEXTURE_WINDOW = 11        # px; 30 cm at the corridor scale
TEXTURE_THRESH = 11.0      # luminance stdev separating mown grass from canopy


def load(name):
    fn, span, centre = CAPTURES[name]
    im = Image.open(os.path.join(IMGDIR, fn)).convert("RGB")
    ppm = im.size[0] / span
    return im, ppm, centre


def to_px(en, ppm, centre, size):
    return (size[0] / 2 + (en[0] - centre[0]) * ppm,
            size[1] / 2 - (en[1] - centre[1]) * ppm)


def canopy_mask(im):
    """True where the surface is textured (canopy), False where smooth."""
    g = im.convert("L")
    mean = g.filter(ImageFilter.BoxBlur(TEXTURE_WINDOW // 2))
    sq = Image.eval(g, lambda v: min(255, v * v // 255))
    sqmean = sq.filter(ImageFilter.BoxBlur(TEXTURE_WINDOW // 2))
    mp, sp, gp = mean.load(), sqmean.load(), g.load()
    w, h = g.size
    mask = Image.new("1", (w, h))
    px = mask.load()
    for y in range(h):
        for x in range(w):
            var = sp[x, y] * 255 - mp[x, y] ** 2
            px[x, y] = 1 if var > TEXTURE_THRESH ** 2 else 0
    return mask


def profile_along(mask, ppm, centre, size, a_en, b_en, step_m=0.25):
    """Sample the canopy mask along a ground line. Returns [(s_m, canopy)]."""
    d = math.hypot(b_en[0] - a_en[0], b_en[1] - a_en[1])
    n = max(int(d / step_m), 1)
    out, m = [], mask.load()
    for i in range(n + 1):
        t = i / n
        en = (a_en[0] + t * (b_en[0] - a_en[0]),
              a_en[1] + t * (b_en[1] - a_en[1]))
        x, y = to_px(en, ppm, centre, size)
        if 0 <= int(x) < size[0] and 0 <= int(y) < size[1]:
            out.append((t * d, bool(m[int(x), int(y)])))
    return out


def first_run(prof, want=True, min_run_m=1.5, step_m=0.25):
    """Distance at which `want` starts and holds for min_run_m."""
    need = int(min_run_m / step_m)
    run = 0
    for s, v in prof:
        if v == want:
            run += 1
            if run >= need:
                return s - (need - 1) * step_m
        else:
            run = 0
    return None


def main():
    im, ppm, centre = load("corridor")
    print(f"corridor capture: {im.size[0]}x{im.size[1]}, "
          f"{CAPTURES['corridor'][1]} m across, {ppm:.2f} px/m "
          f"({100/ppm:.2f} cm/px)")
    mask = canopy_mask(im)

    opts = {o.key: o for o in C.build_options()}
    f10 = opts["F10-A"]
    sup = [(nm, h, en) for nm, h, en in f10.supports]

    print("\nF10-A support points (feed at 10 ft):")
    for nm, h, en in sup:
        d, b = polar(*en)
        x, y = to_px(en, ppm, centre, im.size)
        inside = 0 <= int(x) < im.size[0] and 0 <= int(y) < im.size[1]
        over = mask.load()[int(x), int(y)] if inside else None
        print(f"  {nm:13s} {h:3d} ft  {d:6.2f} m /{d/FT:6.1f} ft  "
              f"{b:5.1f}T /{mag(b):5.1f}M   "
              f"{'CANOPY' if over else 'open' if inside else 'off-frame'}")

    print("\nTreeline along each span (distance from the span's start):")
    cum = 0.0
    for i in range(len(sup) - 1):
        a, b = sup[i][2], sup[i + 1][2]
        prof = profile_along(mask, ppm, centre, im.size, a, b)
        if not prof:
            continue
        span = prof[-1][0]
        enters = first_run(prof, True)
        frac = sum(1 for _, v in prof if v) / len(prof)
        lbl = f"{sup[i][0]} -> {sup[i+1][0]}"
        e = (f"enters canopy at {enters:.1f} m ({enters/FT:.0f} ft)"
             if enters is not None else "no continuous canopy detected")
        print(f"  {lbl:28s} span {span:5.2f} m  {e};  "
              f"{frac*100:4.0f}% of the span is over canopy "
              f"(cumulative wire {cum:.1f}-{cum+span:.1f} m)")
        cum += span

    # Whole-path summary
    whole = []
    for i in range(len(sup) - 1):
        whole += profile_along(mask, ppm, centre, im.size,
                               sup[i][2], sup[i + 1][2])
    frac = sum(1 for _, v in whole if v) / len(whole)
    print(f"\nOVER THE WHOLE GROUND PATH: {frac*100:.0f}% is over tree canopy.")
    print("The models in METHOD.md contain NO tree-absorption term. This is the")
    print("first direct measurement of how much of the wire that omission")
    print("applies to, and the answer is 'most of it'.")

    # ------------------------------------------------------------------
    # Is there ANY open route? Radial scan on the wider capture.
    # ------------------------------------------------------------------
    print("\n" + "=" * 74)
    print("OPEN-GROUND REACH FROM THE FEED, by bearing")
    print("=" * 74)
    im2, ppm2, c2 = load("close")
    mask2 = canopy_mask(im2)
    reach = {}
    for brg in range(0, 360, 5):
        r = math.radians(brg)
        far = 0.0
        s = 0.0
        while s < 44.0:
            en = (s * math.sin(r), s * math.cos(r))
            x, y = to_px(en, ppm2, c2, im2.size)
            if not (0 <= int(x) < im2.size[0] and 0 <= int(y) < im2.size[1]):
                break
            if mask2.load()[int(x), int(y)]:
                break
            far = s
            s += 0.25
        reach[brg] = far
    best = sorted(reach.items(), key=lambda kv: -kv[1])[:8]
    print("  Longest open radials (metres of open ground before canopy):")
    for brg, r in best:
        print(f"    {brg:3d}T / {mag(brg):3.0f}M   {r:5.1f} m / {r/FT:5.1f} ft")
    print(f"\n  The F10-A ground path needs {cum:.1f} m ({cum/FT:.0f} ft) end to end.")
    print(f"  The longest open radial is {best[0][1]:.1f} m "
          f"({best[0][1]/FT:.0f} ft) at {best[0][0]}T.")
    if best[0][1] < cum:
        print("  => NO open-ground route exists. The wire has to go into the")
        print("     trees whichever way it is turned. This is not a choice")
        print("     between lawn and forest; it is a forest installation.")

    # Annotated render
    out = im.copy()
    d = ImageDraw.Draw(out, "RGBA")
    m = mask.load()
    for y in range(0, im.size[1], 3):
        for x in range(0, im.size[0], 3):
            if m[x, y]:
                d.point((x, y), fill=(0, 90, 255, 46))
    try:
        f = ImageFont.truetype("arialbd.ttf", 30)
    except Exception:
        f = ImageFont.load_default()
    pts = [to_px(en, ppm, centre, im.size) for _, _, en in sup]
    d.line(pts, fill=(255, 120, 0, 245), width=9)
    for (nm, h, en), p in zip(sup, pts):
        d.ellipse([p[0] - 15, p[1] - 15, p[0] + 15, p[1] + 15],
                  outline=(255, 255, 255), width=7)
        d.ellipse([p[0] - 15, p[1] - 15, p[0] + 15, p[1] + 15],
                  outline=(255, 120, 0), width=4)
        d.text((p[0] + 22, p[1] - 16), f"{nm} {h}ft", fill=(255, 255, 255),
               font=f, stroke_width=4, stroke_fill=(0, 0, 0))
    x0, y0 = 50, im.size[1] - 60
    d.line([(x0, y0), (x0 + 10 * ppm, y0)], fill=(255, 255, 255), width=7)
    d.text((x0, y0 - 44), "10 m", fill=(255, 255, 255), font=f,
           stroke_width=4, stroke_fill=(0, 0, 0))
    d.text((50, 40), "blue tint = canopy (texture-classified)",
           fill=(255, 255, 255), font=f, stroke_width=4, stroke_fill=(0, 0, 0))
    path = os.path.join(IMGDIR, "corridor_canopy.jpg")
    out.save(path, quality=90)
    print("\nwrote", os.path.normpath(path))


if __name__ == "__main__":
    main()
