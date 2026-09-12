#!/usr/bin/env python3
"""Generate the F10-A deployment guide: plan, 3-D, profile and eye-level views.

Everything drawn here is computed from the same geometry `compare_options.py`
scores, so the drawings cannot drift from the numbers. The plan view is laid
over the 2025 King County ortho, georeferenced by construction (the capture
bbox was requested in EPSG:3857 around a computed centre, so no control points
are involved and there is no fitting error to report).

Writes the HTML to the scratchpad path given as argv[1], or next to this file.

    python3 .../tools/build_deployment_guide.py [out.html]
"""

import base64
import io
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image                                    # noqa: E402
import compare_options as C                              # noqa: E402
from site_geometry import polar, mag, to_latlon, dms, offset  # noqa: E402

FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, "..", "imagery")

# The corridor capture: 55 m across, centred on ENU (14.6, -4.5).
CORRIDOR = ("kc2025_corridor.jpg", 55.0, (14.6, -4.5))
WIDE = ("kc2025_close.jpg", 90.0, (0.0, 0.0))

OPTS = {o.key: o for o in C.build_options()}

# Two buildable deployments, drawn side by side throughout. RB-POST20 leads:
# it beats F10-A on aggregate and worst case while needing one fewer rope
# throw, and its one new support is a post you walk to rather than a limb you
# have to hit with a weight.
PRIMARY = OPTS["RB-POST20"]
SECOND = OPTS["F10-A"]
PLAN24 = OPTS["A"]
# What is actually up (operator's GPX) and the original plan, for comparison.
CURRENT = OPTS["CURRENT"]
BASE = OPTS["BASE"]


def ranked():
    """Same three-band ordering compare_options.py prints."""
    return sorted(OPTS.values(), key=lambda o: (
        -C.aggregate_multiband(o)["n_workable"],
        -C.aggregate_multiband(o)["n_regions_covered"],
        -C.aggregate_multiband(o)["mean_power_dBi"]))


def sg(v, fmt="+.2f"):
    """Format with a true minus sign."""
    return format(v, fmt).replace("-", "−")


def canopy_fractions(opts):
    """Share of each option's ground path over canopy, corridor ortho."""
    import canopy_from_ortho as K
    im, ppm, centre = K.load("corridor")
    mask = K.canopy_mask(im)
    out = {}
    for o in opts:
        prof = []
        for i in range(len(o.supports) - 1):
            prof += K.profile_along(mask, ppm, centre, im.size,
                                    o.supports[i][2], o.supports[i + 1][2])
        out[o.key] = sum(v for _, v in prof) / len(prof)
    return out


def sup3d(opt):
    """[(name, height_ft, (E, N))] -> [(name, E, N, U_ft)]."""
    return [(nm, en[0], en[1], float(h)) for nm, h, en in opt.supports]


PTS = sup3d(PRIMARY)
PTS_B = sup3d(SECOND)
PTS24 = sup3d(PLAN24)


def wire_len_to(i, pts=None):
    """Wire length consumed up to support i, metres."""
    pts = pts or PTS
    s = 0.0
    for k in range(i):
        a, b = pts[k], pts[k + 1]
        s += math.sqrt((b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2
                       + ((b[3] - a[3]) * FT) ** 2)
    return s


def embed(fn, max_px, quality=82):
    im = Image.open(os.path.join(IMGDIR, fn)).convert("RGB")
    if im.size[0] > max_px:
        im = im.resize((max_px, max_px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    b = buf.getvalue()
    print(f"  {fn} -> {max_px}px, {len(b)/1024:.0f} KB "
          f"({len(b)*4//3/1024:.0f} KB base64)")
    return "data:image/jpeg;base64," + base64.b64encode(b).decode()


# ----------------------------------------------------------------------
# Plan view: ortho + overlay, in SVG user units = image pixels
# ----------------------------------------------------------------------

def plan_svg(capture, size=1400, show24=False, current=False):
    fn, span, centre = capture
    ppm = size / span

    def P(e, n):
        return (size / 2 + (e - centre[0]) * ppm,
                size / 2 - (n - centre[1]) * ppm)

    o = [f'<svg viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg" '
         f'class="plan" role="img" aria-label="Overhead plan of the antenna '
         f'over the 2025 King County aerial photograph">',
         f'<image href="{embed(fn, size)}" x="0" y="0" width="{size}" '
         f'height="{size}"/>',
         '<defs><filter id="sh" x="-40%" y="-40%" width="180%" height="180%">'
         '<feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#000" '
         'flood-opacity=".95"/></filter></defs>']

    if show24:
        # The operator's staked strip, in which the post stands.
        rb = " ".join(f"{P(e, n)[0]:.1f},{P(e, n)[1]:.1f}" for e, n in C.RED_BOX)
        o.append(f'<polygon points="{rb}" fill="#ff2f2f" fill-opacity=".16" '
                 f'stroke="#ff2f2f" stroke-width="4"/>')
        # Alternative deployment, dashed.
        ptsb = " ".join(f"{P(p[1], p[2])[0]:.1f},{P(p[1], p[2])[1]:.1f}"
                        for p in PTS_B)
        o.append(f'<polyline points="{ptsb}" fill="none" stroke="#000" '
                 f'stroke-width="9" opacity=".45"/>')
        o.append(f'<polyline points="{ptsb}" fill="none" stroke="#7de2ff" '
                 f'stroke-width="5" stroke-dasharray="14 10" '
                 f'stroke-linejoin="round"/>')
        for p in PTS_B[2:]:
            x, y = P(p[1], p[2])
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="none" '
                     f'stroke="#7de2ff" stroke-width="4"/>')

    if current:
        # The antenna actually up now, from the operator's GPX. Pink, so it
        # cannot be mistaken for either recommendation.
        cp = " ".join(f"{P(*en)[0]:.1f},{P(*en)[1]:.1f}"
                      for _, _, en in CURRENT.supports)
        o.append(f'<polyline points="{cp}" fill="none" stroke="#000" '
                 f'stroke-width="11" opacity=".5"/>')
        o.append(f'<polyline points="{cp}" fill="none" stroke="#ff4fb0" '
                 f'stroke-width="6" stroke-linecap="round"/>')
        ce, cn = CURRENT.supports[-1][2]
        x, y = P(ce, cn)
        d, b = polar(ce, cn)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#0b0d0f" '
                 f'stroke="#ff4fb0" stroke-width="4"/>')
        o.append(f'<text x="{x-20:.1f}" y="{y-16:.1f}" class="pl" '
                 f'text-anchor="end" filter="url(#sh)">up now · end '
                 f'{CURRENT.supports[-1][1]} ft</text>')
        o.append(f'<text x="{x-20:.1f}" y="{y+6:.1f}" class="ps" '
                 f'text-anchor="end" filter="url(#sh)">{d/FT:.0f} ft @ '
                 f'{b:.0f}°T / {mag(b):.0f}°M</text>')

    pts = " ".join(f"{P(p[1], p[2])[0]:.1f},{P(p[1], p[2])[1]:.1f}"
                   for p in PTS)
    o.append(f'<polyline points="{pts}" fill="none" stroke="#000" '
             f'stroke-width="11" opacity=".55"/>')
    o.append(f'<polyline points="{pts}" fill="none" stroke="#ff7a18" '
             f'stroke-width="6" stroke-linejoin="round"/>')

    for i, (nm, e, n, u) in enumerate(PTS):
        x, y = P(e, n)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#0b0d0f" '
                 f'stroke="#fff" stroke-width="4"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#ff7a18"/>')
        d, b = polar(e, n)
        lbl = f"{i+1}. {nm}  {u:.0f} ft"
        sub = ("fixed" if d < 0.01
               else f"{d/FT:.0f} ft @ {b:.0f}°T / {mag(b):.0f}°M")
        dx, dy = (18, -16) if i != 1 else (18, -34)
        o.append(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" class="pl" '
                 f'filter="url(#sh)">{lbl}</text>')
        o.append(f'<text x="{x+dx:.1f}" y="{y+dy+22:.1f}" class="ps" '
                 f'filter="url(#sh)">{sub}</text>')

    # scale bar + north
    x0, y0 = 34, size - 40
    o.append(f'<line x1="{x0}" y1="{y0}" x2="{x0+10*ppm:.1f}" y2="{y0}" '
             f'stroke="#fff" stroke-width="5" filter="url(#sh)"/>')
    for xx in (x0, x0 + 10 * ppm):
        o.append(f'<line x1="{xx:.1f}" y1="{y0-8}" x2="{xx:.1f}" y2="{y0+8}" '
                 f'stroke="#fff" stroke-width="5" filter="url(#sh)"/>')
    o.append(f'<text x="{x0}" y="{y0-16}" class="ps" filter="url(#sh)">'
             f'10 m / 33 ft</text>')
    o.append(f'<g filter="url(#sh)"><line x1="{size-44}" y1="72" '
             f'x2="{size-44}" y2="26" stroke="#fff" stroke-width="5"/>'
             f'<path d="M{size-56} 42 L{size-44} 24 L{size-32} 42" '
             f'fill="none" stroke="#fff" stroke-width="5"/>'
             f'<text x="{size-52}" y="94" class="ps">N</text></g>')
    o.append('</svg>')
    return "\n".join(o)


# ----------------------------------------------------------------------
# 3-D isometric
# ----------------------------------------------------------------------

def iso_svg(w=1120, h=620):
    """Simple axonometric: east right-and-down, north right-and-up, up = up."""
    ex, ey = 1.00, 0.50
    nx, ny = 0.92, -0.46
    s = 15.5                      # px per metre of ground
    vs = 15.5 * FT                # px per foot of height
    ox, oy = 150, 430

    def P(e, n, u_ft):
        return (ox + (e * ex + n * nx) * s,
                oy + (e * ey + n * ny) * s - u_ft * vs)

    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
         f'role="img" aria-label="Three-dimensional view of the antenna">']
    o.append(f'<rect width="{w}" height="{h}" fill="var(--surf)"/>')

    # ground grid, 5 m
    for gx in range(-5, 40, 5):
        a, b = P(gx, -15, 0), P(gx, 12, 0)
        o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" '
                 f'y2="{b[1]:.1f}" stroke="var(--grid)" stroke-width="1"/>')
    for gn in range(-15, 13, 5):
        a, b = P(-5, gn, 0), P(35, gn, 0)
        o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" '
                 f'y2="{b[1]:.1f}" stroke="var(--grid)" stroke-width="1"/>')

    # drop lines + masts
    for nm, e, n, u in PTS:
        g, t = P(e, n, 0), P(e, n, u)
        o.append(f'<line x1="{g[0]:.1f}" y1="{g[1]:.1f}" x2="{t[0]:.1f}" '
                 f'y2="{t[1]:.1f}" stroke="var(--mast)" stroke-width="3" '
                 f'stroke-dasharray="5 4"/>')
        o.append(f'<ellipse cx="{g[0]:.1f}" cy="{g[1]:.1f}" rx="6" ry="3" '
                 f'fill="var(--grid)"/>')

    pts = " ".join(f"{P(e, n, u)[0]:.1f},{P(e, n, u)[1]:.1f}"
                   for _, e, n, u in PTS)
    o.append(f'<polyline points="{pts}" fill="none" stroke="var(--wire)" '
             f'stroke-width="5" stroke-linejoin="round"/>')
    for i, (nm, e, n, u) in enumerate(PTS):
        x, y = P(e, n, u)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" '
                 f'fill="var(--wire)" stroke="var(--surf)" stroke-width="3"/>')
        o.append(f'<text x="{x+12:.1f}" y="{y-10:.1f}" class="i3">'
                 f'{i+1}. {nm}</text>')
        o.append(f'<text x="{x+12:.1f}" y="{y+8:.1f}" class="i3s">'
                 f'{u:.0f} ft</text>')

    # height ruler at the feed
    for ft_ in (0, 25, 50):
        a = P(-4, 0, ft_)
        o.append(f'<line x1="{a[0]-10:.1f}" y1="{a[1]:.1f}" x2="{a[0]:.1f}" '
                 f'y2="{a[1]:.1f}" stroke="var(--grid)" stroke-width="2"/>')
        o.append(f'<text x="{a[0]-16:.1f}" y="{a[1]+5:.1f}" class="i3s" '
                 f'text-anchor="end">{ft_} ft</text>')
    a, b = P(-4, 0, 0), P(-4, 0, 55)
    o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" '
             f'y2="{b[1]:.1f}" stroke="var(--grid)" stroke-width="2"/>')
    o.append(f'<text x="{ox-30}" y="{h-22}" class="i3s">'
             f'ground grid 5 m · vertical scale matches horizontal</text>')
    o.append('</svg>')
    return "\n".join(o)


# ----------------------------------------------------------------------
# Elevation profile along the wire
# ----------------------------------------------------------------------

def profile_svg(w=1120, h=340):
    total = wire_len_to(len(PTS) - 1)
    L, R, T, B = 78, 40, 34, 62
    sx = (w - L - R) / total
    sy = (h - T - B) / 60.0                    # 0..60 ft

    def P(s_m, u_ft):
        return (L + s_m * sx, h - B - u_ft * sy)

    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
         f'role="img" aria-label="Height of the wire along its length">']
    o.append(f'<rect width="{w}" height="{h}" fill="var(--surf)"/>')
    for ft_ in range(0, 61, 10):
        y = P(0, ft_)[1]
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{w-R}" y2="{y:.1f}" '
                 f'stroke="var(--grid)" stroke-width="1"/>')
        o.append(f'<text x="{L-10}" y="{y+5:.1f}" class="i3s" '
                 f'text-anchor="end">{ft_} ft</text>')
    # ground
    o.append(f'<line x1="{L}" y1="{P(0,0)[1]:.1f}" x2="{w-R}" '
             f'y2="{P(0,0)[1]:.1f}" stroke="var(--ink)" stroke-width="2"/>')

    poly = []
    for i, (nm, e, n, u) in enumerate(PTS):
        poly.append(P(wire_len_to(i), u))
    o.append('<polyline points="' +
             " ".join(f"{x:.1f},{y:.1f}" for x, y in poly) +
             '" fill="none" stroke="var(--wire)" stroke-width="5" '
             'stroke-linejoin="round"/>')

    # current maxima on 20 m
    for s in C.imax_positions(4):
        if s > wire_len_to(len(PTS) - 1):
            continue
        u = PRIMARY.height_at_wire(s) / FT
        x, y = P(s, u)
        o.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" '
                 f'y2="{P(0,0)[1]:.1f}" stroke="var(--accent)" '
                 f'stroke-width="2" stroke-dasharray="4 4"/>')
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" '
                 f'fill="var(--accent)"/>')
        o.append(f'<text x="{x:.1f}" y="{y-14:.1f}" class="i3s" '
                 f'text-anchor="middle" fill="var(--accent)">{u:.0f} ft</text>')

    for i, (nm, e, n, u) in enumerate(PTS):
        x, y = P(wire_len_to(i), u)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" '
                 f'fill="var(--wire)" stroke="var(--surf)" stroke-width="3"/>')
        o.append(f'<text x="{x:.1f}" y="{h-38}" class="i3s" '
                 f'text-anchor="middle">{wire_len_to(i)/FT:.0f} ft</text>')
        o.append(f'<text x="{x:.1f}" y="{h-20}" class="i3s" '
                 f'text-anchor="middle">{i+1}</text>')
    o.append(f'<text x="{L}" y="{T-12}" class="i3s">orange dots on the curve = '
             f'the four 20 m current maxima, the parts that actually '
             f'radiate</text>')
    o.append('</svg>')
    return "\n".join(o)


# ----------------------------------------------------------------------
# Eye-level views
# ----------------------------------------------------------------------

EYE_FT = 5.6


def eye_svg(obs_en, look_bearing, title, w=560, h=340, hfov=78.0):
    ox, oy, ou = obs_en[0], obs_en[1], EYE_FT * FT
    az = math.radians(look_bearing)
    fwd = (math.sin(az), math.cos(az), 0.0)
    rgt = (math.cos(az), -math.sin(az), 0.0)
    fx = (w / 2) / math.tan(math.radians(hfov / 2))

    def proj(e, n, u_ft):
        d = (e - ox, n - oy, u_ft * FT - ou)
        z = sum(a * b for a, b in zip(d, fwd))
        if z <= 0.35:
            return None
        x = sum(a * b for a, b in zip(d, rgt))
        return (w / 2 + fx * x / z, h / 2 - fx * d[2] / z)

    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
         f'role="img" aria-label="{title}">']
    o.append(f'<rect width="{w}" height="{h}" fill="var(--sky)"/>')
    o.append(f'<rect y="{h/2:.0f}" width="{w}" height="{h/2:.0f}" '
             f'fill="var(--ground)"/>')
    o.append(f'<line x1="0" y1="{h/2:.0f}" x2="{w}" y2="{h/2:.0f}" '
             f'stroke="var(--grid)" stroke-width="1.5"/>')

    # wire, subdivided so long spans project correctly
    seg = []
    for i in range(len(PTS) - 1):
        a, b = PTS[i], PTS[i + 1]
        for k in range(21):
            t = k / 20
            p = proj(a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2]),
                     a[3] + t * (b[3] - a[3]))
            seg.append(p)
        seg.append(None)
    run = []
    for p in seg + [None]:
        if p is None:
            if len(run) > 1:
                o.append('<polyline points="' +
                         " ".join(f"{x:.1f},{y:.1f}" for x, y in run) +
                         '" fill="none" stroke="var(--wire)" '
                         'stroke-width="3.5" stroke-linejoin="round"/>')
            run = []
        else:
            run.append(p)

    for i, (nm, e, n, u) in enumerate(PTS):
        p = proj(e, n, u)
        g = proj(e, n, 0.0)
        if g and p:
            o.append(f'<line x1="{g[0]:.1f}" y1="{g[1]:.1f}" x2="{p[0]:.1f}" '
                     f'y2="{p[1]:.1f}" stroke="var(--mast)" '
                     f'stroke-width="2" stroke-dasharray="4 4"/>')
        if p and 0 < p[0] < w:
            o.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="6" '
                     f'fill="var(--wire)" stroke="var(--surf)" '
                     f'stroke-width="2"/>')
            o.append(f'<text x="{p[0]:.1f}" y="{max(p[1]-13,14):.1f}" '
                     f'class="i3s" text-anchor="middle">{i+1}</text>')
    o.append(f'<text x="12" y="{h-12}" class="i3s">looking '
             f'{look_bearing:.0f}°T / {mag(look_bearing):.0f}°M '
             f'· eye height {EYE_FT} ft · {hfov:.0f}° '
             f'field of view</text>')
    o.append('</svg>')
    return "\n".join(o)


def main():
    print("Embedding imagery:")
    plan = plan_svg(CORRIDOR, 1400, show24=True)
    wide = plan_svg(WIDE, 1200, current=True)
    print("Classifying canopy along each path:")
    out = {
        "plan": plan, "wide": wide, "iso": iso_svg(),
        "profile": profile_svg(),
        "canopy": canopy_fractions((CURRENT, BASE, PRIMARY, SECOND)),
    }
    # Standpoints follow the PRIMARY deployment, so the last two are computed
    # from the post rather than hard-coded to F10-A's end tie-off.
    post = PTS[-1]
    apex = PTS[1]
    brg_apex_post = polar(post[1] - apex[1], post[2] - apex[2])[1]
    brg_post_feed = polar(-post[1], -post[2])[1]
    views = []
    for nm, en, brg, cap in (
        ("From the feed, looking out along leg 1", (0.0, 0.0), 82.2,
         "Stand at the transformer with your back to the house."),
        ("From the lawn, looking back at the whole run", (8.0, -12.0), 55.0,
         "Stand in the middle of the lawn, southeast of the feed."),
        ("Under the apex, looking down to the post", (apex[1], apex[2]),
         brg_apex_post, "Stand at the base of the apex tree."),
        ("From the post, looking back up the wire", (post[1], post[2]),
         brg_post_feed,
         "Stand at the post in your staked strip, looking back at the house."),
    ):
        views.append((nm, cap, en, brg, eye_svg(en, brg, nm)))
    return out, views


CSS = """
:root{
  --bg:#f2f0ea; --surf:#ffffff; --surf2:#e9e6dd; --ink:#171b17; --ink2:#3f463e;
  --muted:#6d7568; --rule:#d3cec2; --grid:#c2bcae; --mast:#8d9585;
  --wire:#e0620d; --accent:#c8811a; --alt:#0f7fa6; --alarm:#b3372a;
  --sky:#dfe6ea; --ground:#dcdccb; --now:#c2337a;
  --ff-d:"Archivo",system-ui,sans-serif;
  --ff-b:"IBM Plex Sans",system-ui,sans-serif;
  --ff-m:"IBM Plex Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#12150f; --surf:#1a1e17; --surf2:#232820; --ink:#eceadf; --ink2:#c3c6b8;
  --muted:#8d9481; --rule:#333a2e; --grid:#3d4536; --mast:#6d7663;
  --wire:#ff9142; --accent:#e2ab4c; --alt:#5cc4e6; --alarm:#e8705f;
  --sky:#1d2630; --ground:#242a1e; --now:#ff78c0;
}}
:root[data-theme="dark"]{
  --bg:#12150f; --surf:#1a1e17; --surf2:#232820; --ink:#eceadf; --ink2:#c3c6b8;
  --muted:#8d9481; --rule:#333a2e; --grid:#3d4536; --mast:#6d7663;
  --wire:#ff9142; --accent:#e2ab4c; --alt:#5cc4e6; --alarm:#e8705f;
  --sky:#1d2630; --ground:#242a1e; --now:#ff78c0;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--ff-b);
  font-size:16px;line-height:1.62;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:36px 22px 90px}
h1,h2,h3{font-family:var(--ff-d);text-wrap:balance;margin:0}
h1{font-size:clamp(30px,5vw,50px);font-weight:700;letter-spacing:-.02em;
  line-height:1.05}
h2{font-size:clamp(21px,2.8vw,30px);font-weight:650;letter-spacing:-.01em}
h3{font-size:18px;font-weight:650;margin-top:6px}
.eyebrow{font-family:var(--ff-m);font-size:11px;letter-spacing:.18em;
  text-transform:uppercase;color:var(--muted)}
header.mast{border-bottom:3px solid var(--ink);padding-bottom:22px;
  margin-bottom:14px;display:flex;flex-direction:column;gap:10px}
.lede{font-size:18.5px;color:var(--ink2);max-width:68ch;margin:0}
.meta{display:flex;flex-wrap:wrap;gap:8px;font-family:var(--ff-m);font-size:12px;
  color:var(--muted)}
.meta span{background:var(--surf2);padding:4px 10px;border-radius:3px}
.meta b{color:var(--ink)}
section{margin-top:52px;display:flex;flex-direction:column;gap:16px}
.sec-head{display:flex;flex-direction:column;gap:5px;
  border-left:4px solid var(--wire);padding-left:14px}
p{margin:0;max-width:72ch;color:var(--ink2)}
p b,li b{color:var(--ink)}
figure{margin:0;background:var(--surf);border:1px solid var(--rule);
  border-radius:5px;overflow:hidden}
figure svg{display:block;width:100%;height:auto}
figcaption{padding:11px 15px;font-size:13.5px;color:var(--muted);
  border-top:1px solid var(--rule);background:var(--surf2)}
figcaption b{color:var(--ink2)}
.plan text.pl{font-family:var(--ff-d);font-size:21px;font-weight:700;fill:#fff}
.plan text.ps{font-family:var(--ff-m);font-size:15px;fill:#fff}
text.i3{font-family:var(--ff-d);font-size:14px;font-weight:650;fill:var(--ink)}
text.i3s{font-family:var(--ff-m);font-size:11.5px;fill:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));
  gap:16px}
.tbl{overflow-x:auto;border:1px solid var(--rule);border-radius:5px;
  background:var(--surf)}
table{border-collapse:collapse;width:100%;font-size:14.5px;
  font-variant-numeric:tabular-nums}
caption{text-align:left;padding:11px 15px;font-family:var(--ff-m);font-size:11px;
  letter-spacing:.13em;text-transform:uppercase;color:var(--muted);
  background:var(--surf2);border-bottom:1px solid var(--rule)}
th,td{padding:9px 14px;text-align:left;border-bottom:1px solid var(--rule)}
th{font-family:var(--ff-m);font-size:11px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--muted);font-weight:500}
td.n{font-family:var(--ff-m);text-align:right;white-space:nowrap}
tr:last-child td{border-bottom:none}
tr.hi td{background:var(--surf2);font-weight:600;color:var(--ink)}
.note{border-left:4px solid var(--accent);background:var(--surf);
  padding:14px 17px;border-radius:0 5px 5px 0;font-size:15px;color:var(--ink2)}
.note.alarm{border-left-color:var(--alarm)}
.note.now,.sec-head.now{border-left-color:var(--now)}
th.now,td.now{color:var(--now)}
tr.hi td.now{color:var(--now)}
.note b{color:var(--ink)}
ol.steps{list-style:none;counter-reset:s;padding:0;margin:0;
  display:flex;flex-direction:column;gap:12px}
ol.steps>li{counter-increment:s;background:var(--surf);
  border:1px solid var(--rule);border-radius:5px;padding:15px 17px 15px 60px;
  position:relative}
ol.steps>li::before{content:counter(s);position:absolute;left:16px;top:14px;
  width:28px;height:28px;border-radius:50%;background:var(--wire);color:#fff;
  font-family:var(--ff-m);font-size:14px;font-weight:600;display:flex;
  align-items:center;justify-content:center}
ol.steps h3{margin-bottom:3px}
ol.steps p{font-size:15px}
ul.tight{margin:7px 0 0;padding-left:19px;font-size:14.5px;color:var(--ink2);
  display:flex;flex-direction:column;gap:4px}
.num{font-family:var(--ff-m)}
footer{margin-top:70px;padding-top:20px;border-top:1px solid var(--rule);
  font-size:13px;color:var(--muted);display:flex;flex-direction:column;gap:8px;
  max-width:78ch}
:focus-visible{outline:2px solid var(--wire);outline-offset:2px}
@media(prefers-reduced-motion:reduce){*{animation:none!important;
  transition:none!important}}
"""


def schedule_rows(pts=None, hi_rows=(1, 2)):
    pts = pts or PTS
    r = []
    for i, (nm, e, n, u) in enumerate(pts):
        d, b = polar(e, n)
        la, lo = to_latlon(e, n)
        sa, so = dms(la, lo)
        dist = "—" if d < 0.01 else f"{d/FT:.1f} ft"
        brg = "—" if d < 0.01 else f"{b:.0f}° / <b>{mag(b):.0f}°</b>"
        hi = ' class="hi"' if i in hi_rows else ""
        r.append(
            f"<tr{hi}><td class='n'>{i+1}</td><td>{nm}</td>"
            f"<td class='n'>{u:.0f} ft</td><td class='n'>{dist}</td>"
            f"<td class='n'>{brg}</td>"
            f"<td class='n'>{wire_len_to(i, pts)/FT:.1f} ft</td>"
            f"<td class='n' style='font-size:12.5px'>{sa}<br>{so}</td></tr>")
    return "\n".join(r)


def current_section(parts):
    """'What is up now' - the operator's as-built sloper against the plans."""
    cols = (CURRENT, BASE, PRIMARY, SECOND)
    rk = ranked()
    n = len(rk)
    M = {o.key: C.aggregate_multiband(o) for o in cols}
    R = {o.key: rk.index(o) + 1 for o in cols}
    cz = parts["canopy"]
    end_en = CURRENT.supports[-1][2]
    run, brg = polar(*end_en)
    back = (brg + 180) % 360
    rise = CURRENT.top_h - CURRENT.feed_h
    slack = C.WIRE_M - math.hypot(run, rise)

    shape = {CURRENT.key: "one straight run up to a tree",
             BASE.key: "bent at a 35 ft apex, down to 10 ft",
             PRIMARY.key: "50 ft apex tree, then a 20 ft post",
             SECOND.key: "50 ft apex, 50 ft far tree, 30 ft end"}

    def cell(o, txt):
        c = " now" if o is CURRENT else ""
        return f"<td class='n{c}'>{txt}</td>"

    def row(label, fn, hi=False):
        return (f"<tr{' class=\"hi\"' if hi else ''}><td>{label}</td>"
                + "".join(cell(o, fn(o)) for o in cols) + "</tr>")

    rows = ["<tr><td>Shape</td>" + "".join(
        f"<td style='font-size:13.5px'>{shape[o.key]}</td>" for o in cols)
        + "</tr>"]
    rows.append(row("Highest attachment", lambda o: f"{o.max_anchor_ft} ft"))
    rows.append(row(f"Three-band rank, of {n}", lambda o: f"<b>{R[o.key]}</b>",
                    hi=True))
    rows.append(row("3-band aggregate",
                    lambda o: f"{sg(M[o.key]['mean_power_dBi'])} dBi"))
    rows.append(row("Cells workable",
                    lambda o: f"{M[o.key]['n_workable']} / 75", hi=True))
    rows.append(row("Regions", lambda o: f"{M[o.key]['n_regions_covered']} / 25"))
    rows.append(row("Median cell", lambda o: sg(M[o.key]['median_dBi'], "+.1f")))
    rows.append(row("Worst region",
                    lambda o: f"{sg(M[o.key]['worst_dBi'], '+.1f')} dBi"))
    for b in C.BAND_KEYS:
        rows.append(row(b.replace("m", " m"), lambda o, b=b: (
            f"{sg(C.aggregate(o, b)['mean_power_dBi'])} "
            f"<span style='color:var(--muted)'>"
            f"({C.aggregate(o, b)['n_workable']}/25)</span>")))
    rows.append(row("Wire over canopy", lambda o: f"{cz[o.key]*100:.0f}%"))

    # Per-region 3-band mean dBi, CURRENT against the original plan.
    def mb_region(o):
        nets = {b: C.band_nets(o, b) for b in C.MULTIBAND}
        return [10 * math.log10(sum(
            10 ** ((nets[b][i] + C.BAND[b]["peak_dBi"]) / 10)
            for b in C.MULTIBAND) / len(C.MULTIBAND))
            for i in range(len(C.TARGETS))]
    cur_r, base_r = mb_region(CURRENT), mb_region(BASE)
    deltas = sorted(((cur_r[i] - base_r[i], C.TARGETS[i][0])
                     for i in range(len(C.TARGETS))), reverse=True)
    gains, losses = deltas[:5], deltas[::-1][:5]
    gl = "".join(
        f"<tr><td>{gn}</td><td class='n'>{sg(gd, '+.1f')}</td>"
        f"<td>{ln}</td><td class='n' style='color:var(--alarm)'>"
        f"{sg(ld, '+.1f')}</td></tr>"
        for (gd, gn), (ld, ln) in zip(gains, losses))

    # GPS sensitivity: the same construction as compare_options.py.
    sens = [C.aggregate_multiband(C.current_option(
        offset((0.0, 0.0), brg + db, run + dr)))
        for db in (-10, -5, 0, 5, 10) for dr in (-5.0, -2.5, 0.0)]
    s_cells = [m["n_workable"] for m in sens]
    s_dbi = [m["mean_power_dBi"] for m in sens]

    t = (end_en[0] - 46.9) / -116.8
    gap = end_en[1] - (-32.0 + t * 25.2)
    mc, mb, mp, ms = (M[k] for k in (CURRENT.key, BASE.key, PRIMARY.key,
                                     SECOND.key))
    side = "below" if R[CURRENT.key] > R[BASE.key] else "above"
    avg = {o.key: o.avg_h / FT for o in cols}

    return f"""
<section>
  <div class="sec-head now">
    <div class="eyebrow">What's up now · from your Garmin track</div>
    <h2>Your 45 ft sloper ranks {R[CURRENT.key]} of {n}</h2>
  </div>
  <p>You paced it from the far end back to the transformer: <b>{run/FT:.0f} ft
  out at {mag(brg):.0f}° magnetic</b> ({brg:.0f}°T), feed at 10 ft, end at
  about 45 ft, one straight run. That is a <b>{CURRENT.slope_deg:.0f}°
  sloper</b> with roughly {slack:.1f} m of slack in the wire — a hung wire,
  not a taut one, which is what the track and the heights together say.</p>

  <div class="tbl"><table>
    <caption>As built, against your original plan and both recommendations ·
    40 + 20 + 15 m, 25 regions · feed 10 ft in every column</caption>
    <thead><tr><th></th><th class="now">Up now</th><th>BASE · original
    plan</th><th>RB-POST20 · build this</th><th>F10-A · fallback</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>

  <div class="note alarm">
    <b>It ranks {side} your original plan, not just below the
    recommendations.</b> Against BASE it is
    <b>{sg(mc['mean_power_dBi'] - mb['mean_power_dBi'])} dB and
    {mc['n_workable'] - mb['n_workable']:+d} cells</b>, with a worst region
    {abs(mc['worst_dBi'] - mb['worst_dBi']):.0f} dB deeper. Against RB-POST20
    it is <b>{sg(mc['mean_power_dBi'] - mp['mean_power_dBi'])} dB and
    {mc['n_workable'] - mp['n_workable']:+d} cells</b>; against F10-A,
    {sg(mc['mean_power_dBi'] - ms['mean_power_dBi'])} dB and
    {mc['n_workable'] - ms['n_workable']:+d} cells.
  </div>

  <p><b>Why a sloper that reaches 45 ft does this badly.</b> Two reasons, and
  the first one is the big one. A straight 130 ft wire has deep nulls straight
  off both ends on every band, and this one points <b>{brg:.0f}° / {back:.0f}°
  true</b>. One end aims at South America ({C.TARGET_BEARINGS['South America']:.0f}°T);
  the other aims at Beijing, Shanghai and Vladivostok (310–318°T) — the same
  Asia null that ruled out the driveway layout at the very start of this
  study. Second, it is low where it matters: the wire averages
  <b>{avg[CURRENT.key]:.0f} ft</b>, against {avg[SECOND.key]:.0f} ft for
  F10-A, because the first half of it is still climbing out of a 10 ft
  feed.</p>

  <div class="tbl"><table>
    <caption>Region by region against your original plan · 3-band mean dBi
    change</caption>
    <thead><tr><th>Better now</th><th>Δ</th><th>Worse now</th><th>Δ</th></tr>
    </thead>
    <tbody>{gl}</tbody>
  </table></div>

  <figure>{parts['wide']}<figcaption><b>Pink</b> is the wire up now, drawn
  from the surveyed feed to the far end of your Garmin track. <b>Orange</b> is
  RB-POST20. The track's other end landed 4–8 m from the surveyed transformer,
  which is ordinary wrist-GPS error, so the feed is drawn at the survey point.
  90 m across; the driveway, both yard corners and the original end mark are
  all in frame.</figcaption></figure>

  <p><b>It is the one layout here that mostly stays out of the trees</b> —
  only {cz[CURRENT.key]*100:.0f}% of its ground path is over canopy, because it
  runs straight down the lawn along the house, against
  {cz[SECOND.key]*100:.0f}% for F10-A and {cz[PRIMARY.key]*100:.0f}% for
  RB-POST20. No model in this study charges anything for canopy, so the real
  gap between this wire and the recommendations is smaller than the table
  says. How much smaller is not something the study can tell you; an on-air
  A/B or a post-install sweep of both is.</p>

  <div class="note now">
    <b>The GPS point doesn't change the answer.</b> Swinging the far end
    ±10° and pulling it in up to 5 m moves the score between
    {sg(min(s_dbi))} and {sg(max(s_dbi))} dBi and {min(s_cells)}–{max(s_cells)}
    cells. Your original plan is {mb['n_workable']} cells, so
    {'no' if max(s_cells) < mb['n_workable'] else 'some'} reasonable error in the
    track closes that gap. (It can't be further out than the track says: at
    45 ft the wire only reaches {math.sqrt(C.WIRE_M**2 - rise**2)/FT:.0f} ft of
    ground run.)
  </div>

  <div class="note">
    <b>Check the far-end tree against the south line.</b> On the track it
    sits {abs(gap)/FT:.0f} ft {'inside' if gap > 0 else 'past'} the parcel's
    south boundary. That is well inside the watch's error, so this is a
    question for a tape and the property corners, not for the GPX.
  </div>

  <p style="font-size:14px;color:var(--muted)">Scored with the slant-wire
  model (METHOD.md §9, the study's lowest-confidence model). The same wire on
  the horizontal-wire model scores worse still, so the ranking is not an
  artefact of that choice.</p>
</section>
"""


def build_html(parts, views):
    vhtml = []
    for nm, cap, en, brg, svg in views:
        d, b = polar(*en)
        where = ("at the transformer" if d < 0.01
                 else f"{d/FT:.0f} ft from the feed at {b:.0f}°T")
        vhtml.append(
            f"<figure><div>{svg}</div><figcaption><b>{nm}</b> — {cap} "
            f"Stand {where}, face <b>{mag(brg):.0f}° magnetic</b>. "
            f"Numbers mark the supports.</figcaption></figure>")

    total_ft = wire_len_to(len(PTS) - 1) / FT
    total_b = wire_len_to(len(PTS_B) - 1, PTS_B) / FT
    post = PTS[-1]
    pd, pb = polar(post[1], post[2])
    pla, plo = to_latlon(post[1], post[2])
    psa, pso = dms(pla, plo)
    mP = C.aggregate_multiband(PRIMARY)
    mS = C.aggregate_multiband(SECOND)
    now_html = current_section(parts)
    return f"""<title>Threading 130 Feet Into the Woods</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">

<header class="mast">
  <div class="eyebrow">Deployment guide · RB-POST20 and F10-A · JYR8010 EFHW · CN97ap</div>
  <h1>Threading 130 feet<br>into the woods</h1>
  <p class="lede">Two buildable deployments, both with the feed at 10 ft, both
  computed from the survey and checked against the 2025 King County aerial —
  which shows something none of the earlier analysis could: <b>this is a forest
  installation, not a lawn installation.</b> The one to build uses your staked
  garden post and needs a single rope throw.</p>
  <div class="meta">
    <span>Wire used <b>{total_ft:.0f} ft</b> of 130</span>
    <span>Rope throws <b>1</b></span>
    <span>Highest attachment <b>50 ft</b></span>
    <span>Declination <b>+15.3°E</b></span>
    <span>Imagery <b>King County 2025, 3–6 in/px</b></span>
  </div>
</header>

<section>
  <div class="sec-head">
    <div class="eyebrow">Pick one</div>
    <h2>The post option, or the three-tree option</h2>
  </div>
  <p>Both start identically: transformer at 10 ft, one line over a 50 ft limb in
  the apex tree. They differ only in what happens after that.</p>
  <div class="tbl"><table>
    <caption>Both deployments, feed at 10 ft</caption>
    <thead><tr><th></th><th>RB-POST20 · build this</th><th>F10-A · the fallback</th></tr></thead>
    <tbody>
      <tr class="hi"><td>After the apex tree</td>
        <td><b>one 20 ft post</b> in your staked strip</td>
        <td>two more tree attachments, 50 ft and 30 ft</td></tr>
      <tr><td>Rope throws</td><td class="n"><b>1</b></td><td class="n">1, plus two more attachments</td></tr>
      <tr><td>3-band aggregate</td><td class="n">{sg(mP['mean_power_dBi'])} dBi</td><td class="n">{sg(mS['mean_power_dBi'])} dBi</td></tr>
      <tr><td>Cells workable</td><td class="n">{mP['n_workable']} / 75</td><td class="n">{mS['n_workable']} / 75</td></tr>
      <tr><td>Regions</td><td class="n">{mP['n_regions_covered']} / 25</td><td class="n">{mS['n_regions_covered']} / 25</td></tr>
      <tr class="hi"><td><b>Worst region</b></td><td class="n"><b>{sg(mP['worst_dBi'], '+.1f')} dBi</b></td><td class="n">{sg(mS['worst_dBi'], '+.1f')} dBi</td></tr>
      <tr><td>15 m</td><td class="n">{sg(C.aggregate(PRIMARY, '15m')['mean_power_dBi'])} dBi</td><td class="n">{sg(C.aggregate(SECOND, '15m')['mean_power_dBi'])} dBi</td></tr>
      <tr><td>Wire used</td><td class="n">{total_ft:.0f} ft</td><td class="n">{total_b:.0f} ft</td></tr>
    </tbody>
  </table></div>
  <div class="note">
    <b>They are within a third of a dB of each other, and the post option has the
    better worst case.</b> That is the whole argument: you are not trading
    performance for convenience here, you are trading a marginal region for a
    rope throw you do not have to make and an attachment you can reach with a
    stepladder. Build RB-POST20. Keep F10-A for the day you want the last
    region back, or if the post turns out not to stand.
  </div>
  <div class="note now">
    <b>Both are a large step up from what is up now.</b> The straight sloper
    you paced off scores {sg(C.aggregate_multiband(CURRENT)['mean_power_dBi'])}
    dBi and {C.aggregate_multiband(CURRENT)['n_workable']} / 75 — see the next
    section for why, and where it lands among all {len(OPTS)} options.
  </div>
  <div class="note">
    <b>And if you can get 30 ft of post up instead of 20:</b> the same design
    scores −0.40 dBi and 48 / 75, with the post moving out to 95.4 ft at
    <b>102° magnetic</b>. That is 0.35 dB for 10 more feet of PVC. Worth it if
    the post takes it safely; not worth a structure that will not survive a
    windstorm on a garden stake.
  </div>
</section>
{now_html}
<section>
  <div class="sec-head">
    <div class="eyebrow">Read this before you buy rope</div>
    <h2>62% of this antenna flies over tree canopy</h2>
  </div>
  <p>Texture-classifying the aerial photo along the wire path gives the number
  directly. It is not a small correction to the plan — it is the plan's main
  unmodelled risk, and it is the thing your very first question in this project
  was about.</p>
  <div class="tbl"><table>
    <caption>Canopy along each span, measured from the ortho</caption>
    <thead><tr><th>Span</th><th>Length</th><th>Enters canopy at</th>
      <th>Over canopy</th></tr></thead>
    <tbody>
      <tr><td>1 → 2 · feed to apex</td><td class="n">52.5 ft</td>
        <td class="n">8 ft</td><td class="n">46%</td></tr>
      <tr><td>2 → 3 · apex to far support</td><td class="n">31.4 ft</td>
        <td class="n">15 ft</td><td class="n">69%</td></tr>
      <tr class="hi"><td>3 → 4 · far support to end</td><td class="n">25.6 ft</td>
        <td class="n">0 ft</td><td class="n">84%</td></tr>
      <tr class="hi"><td><b>whole ground path</b></td><td class="n">110 ft</td>
        <td class="n">—</td><td class="n"><b>62%</b></td></tr>
    </tbody>
  </table></div>
  <div class="note alarm">
    <b>A correction to what this page said before.</b> It claimed no layout
    could avoid canopy, from a radial scan that stopped at the first textured
    pixel near the house. The straight sloper you have up now proves otherwise:
    it runs 120 ft down the lawn at only
    <b>{parts['canopy'][CURRENT.key]*100:.0f}% canopy</b>. What remains true is
    that both designs recommended here go through the apex tree by
    construction, so most of their wire is over trees.
    <br><br>
    <b>None of the dB figures anywhere in this project include a
    tree-absorption term.</b> Treat them as an optimistic ceiling for the
    recommended designs — less so for the lawn sloper — and treat the
    post-installation sweep as the real measurement.
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Overhead</div>
    <h2>Where every point lands</h2>
  </div>
  <figure>{parts['plan']}<figcaption><b>Solid orange</b> is RB-POST20 — apex
  tree, then the post. <b>Dashed blue</b> is F10-A, which carries on into the
  trees to two more attachments. The <b>red outline</b> is your staked strip,
  georeferenced from the annotation you drew with a 6 cm worst residual.
  Bearings are true first, <b>magnetic second in bold</b>; set your compass to
  the bold number.
  Aerial: King County GIS 2025 orthomosaic (EagleView), 3–6 in/px, requested in
  EPSG:3857 about a computed centre, so the overlay is georeferenced by
  construction rather than fitted to control points.</figcaption></figure>
  <p>The wider 90 m view is in the section above, with the wire that is up
  now drawn on it.</p>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">The numbers you take outside</div>
    <h2>Support schedule</h2>
  </div>
  <div class="tbl"><table>
    <caption>RB-POST20 · build this · feed fixed at 10 ft · bearings true / <b>magnetic</b></caption>
    <thead><tr><th>#</th><th>Point</th><th>Height</th><th>From feed</th>
      <th>Bearing T / <b>M</b></th><th>Wire used</th><th>Coordinates</th></tr>
    </thead>
    <tbody>{schedule_rows(PTS, (1, 2))}</tbody>
  </table></div>
  <p><b>The post goes at {pd/FT:.1f} ft from the transformer on a bearing of
  {mag(pb):.0f}° magnetic</b> — {psa} {pso}. That is inside the strip you
  marked. Add <b>2–3% slack</b> beyond the tabulated wire lengths and expect
  8–12 in of sag mid-span.</p>

  <div class="tbl"><table>
    <caption>F10-A · the fallback · same feed, two more tree attachments</caption>
    <thead><tr><th>#</th><th>Point</th><th>Height</th><th>From feed</th>
      <th>Bearing T / <b>M</b></th><th>Wire used</th><th>Coordinates</th></tr>
    </thead>
    <tbody>{schedule_rows(PTS_B, (1, 2))}</tbody>
  </table></div>
  <p>In F10-A, <b>support 3 sits at 97.4 ft of wire</b> — deliberately the 40 m
  and 15 m current maximum, which is why its end tie-off barely matters. The
  post option does not have that support at all; it runs the whole remaining
  {(total_ft - wire_len_to(1)/FT):.0f} ft in one span from the apex to the
  post.</p>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">The one thing you have to build</div>
    <h2>A 20 ft post that survives a windstorm</h2>
  </div>
  <p>Everything else in this plan is rope and wire. This is the only structure,
  and it is holding roughly half the tension of a 130 ft antenna at
  {pd/FT:.0f} ft from the house.</p>
  <ul class="tight">
    <li><b>Schedule 40 PVC, not thin-wall.</b> 2 in at the base stepped to
      1½ in and 1¼ in above. Thin-wall at 20 ft with a wire on top folds.</li>
    <li><b>Guy it at two-thirds height</b> — about 13 ft — with three lines at
      120°. On a garden stake this is not optional; the antenna pulls sideways
      on one bearing and nothing resists that but guys.</li>
    <li><b>Take the wire tension into the guys, not the post.</b> Terminate the
      antenna on a short halyard through a pulley or thimble at the top so the
      post carries compression, and let a guy anchor take the pull.</li>
    <li><b>An insulator at the top.</b> The wire arrives near a current maximum
      here rather than a voltage one, so this is less critical than the apex —
      but PVC gets conductive when it is filthy and wet, so use one anyway.</li>
    <li><b>Leave it lowerable.</b> A sleeve joint at the bottom section means
      you can drop the whole thing to re-tension after the first month of
      settling, which you will want to do.</li>
  </ul>
  <h3 style="margin-top:8px">Which stake — and pick the stake first</h3>
  <p>The wire length pins how far the post can be from the apex tree, so only a
  narrow band of your strip is usable: about <b>7 ft of its 59 ft length</b>, at
  the north-west end nearest the house. <b>Raising the post moves that band
  further along the strip</b>, which is the useful degree of freedom if your
  stakes are already in fixed places.</p>

  <div class="tbl"><table>
    <caption>Reachable band, by post height · apex tree at 50 ft, feed at 10 ft</caption>
    <thead><tr><th>Post height</th><th>Reachable band from the feed</th>
      <th>Best point</th><th>3-band</th><th>Cells</th></tr></thead>
    <tbody>
      <tr><td class="n">16 ft</td><td class="n">88.4 – 95.5 ft</td>
        <td class="n">88.7 ft @ 101°M</td><td class="n">−0.85</td><td class="n">46 / 75</td></tr>
      <tr class="hi"><td class="n"><b>20 ft</b></td><td class="n"><b>90.6 – 97.6 ft</b></td>
        <td class="n"><b>90.9 ft @ 101°M</b></td><td class="n"><b>−0.71</b></td><td class="n"><b>47 / 75</b></td></tr>
      <tr><td class="n">24 ft</td><td class="n">92.8 – 99.0 ft</td>
        <td class="n">93.5 ft @ 102°M</td><td class="n">−0.58</td><td class="n">47 / 75</td></tr>
      <tr><td class="n">30 ft</td><td class="n">94.6 – 101.1 ft</td>
        <td class="n">94.6 ft @ 102°M</td><td class="n">−0.40</td><td class="n">48 / 75</td></tr>
    </tbody>
  </table></div>

  <div class="note">
    <b>So: measure to your stakes, then choose the post height that reaches
    the one you like.</b> Roughly <b>2 ft of extra post buys 2 ft further out</b>
    along the strip. Within each band the near end always scores better — the
    numbers fall by about 0.2 dB and 5 cells across the 7 ft — so if two stakes
    both work, take the one closer to the house.
  </div>

  <div class="note">
    <b>Height is the least important variable here.</b> The whole 10 → 36 ft
    range spans <b>0.83 dB</b> — about 0.32 dB per 10 ft — and the post's
    position shifts by only 10 ft across it. Build the height that stands up
    safely and stop. There is no version of this where an extra 6 ft of PVC is
    worth a mast that comes down in a gale.
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">In three dimensions</div>
    <h2>What the wire actually looks like in space</h2>
  </div>
  <figure>{parts['iso']}<figcaption>Axonometric view, vertical scale equal to
  horizontal — so the shallow climb out of the feed and the drop to the end
  tie-off are true, not exaggerated. Dashed verticals are drop lines to ground.
  <b>Trees are not drawn</b>: their positions are known from the photo but their
  heights were never measured, and drawing guesses would be worse than drawing
  nothing.</figcaption></figure>
  <figure>{parts['profile']}<figcaption>Height along the wire, from the
  transformer to the far end. The orange dots are the <b>four 20 m current
  maxima</b> — the only parts of this antenna that meaningfully radiate. Their
  mean height is <b>37.5 ft</b>, and that single number predicts low-angle
  performance better than average wire height does.</figcaption></figure>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">From where you'll be standing</div>
    <h2>Eye-level views</h2>
  </div>
  <p>Computed perspective from 5 ft 7 in eye height. These show the
  <b>wire geometry only</b> — no trees, no house — so use them to understand
  where the wire sits relative to you, not to judge clearance.</p>
  <div class="grid2">{''.join(vhtml)}</div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Doing it</div>
    <h2>Deployment sequence</h2>
  </div>
  <ol class="steps">
    <li><h3>Mark the ground first, before any rope goes up</h3>
      <p>Work from the transformer with a tape and a compass set to
      <b>magnetic</b>. For the post option you need two marks:</p>
      <ul class="tight">
        <li><b>52 ft 6 in at 67°M</b> — under the apex tree</li>
        <li><b>{pd/FT:.0f} ft at {mag(pb):.0f}°M</b> — the post, in your staked
          strip</li>
      </ul>
      <p style="margin-top:7px">For F10-A instead, the two further marks are
      <b>77 ft 2 in at 85°M</b> and <b>100 ft 2 in at 92°M</b>. Neither has ever
      been ground-verified — they are computed positions, not observed trees,
      and that uncertainty is a large part of why the post option is the better
      build.</p></li>

    <li><h3>Confirm the apex limb clears 50 ft</h3>
      <p>Sight up from the apex stake and find a limb you can actually get a
      line over at <b>50 ft</b>. Ten feet low costs about 0.9 dB — not fatal,
      but this is the one attachment both plans depend on, so establish it
      before you commit to either. If there is no usable limb here, stop and
      tell me; the whole study is built on this tree.</p></li>

    <li><h3>Get the line up, and stand the post</h3>
      <p>One throw at 50 ft — routine with a slingshot and a 12 oz weight.
      Cleat it off before the antenna comes out of the bag. Then stand and guy
      the post at its stake. Do both before any wire is handled: wrestling
      130 ft of wire while you are still fighting a throw line is how wire gets
      kinked and insulators get dropped in the undergrowth.</p></li>

    <li><h3>Lay the wire out on the ground along the marked path</h3>
      <p>Flake it out from the feed stake toward the end, following your stakes.
      This is where you find out whether the run is really clear — <b>62% of it
      is under canopy</b>, so expect to route around trunks and through
      understory rather than pulling a straight line. Keep the transformer end
      at the house and do not let the wire cross itself.</p></li>

    <li><h3>Hang the apex first, then take up the span to the post</h3>
      <p>Raise the apex to 50 ft and let the rest of the wire hang. Then walk
      the far end to the post and take up the single
      {(total_ft - wire_len_to(1)/FT):.0f} ft span. <b>Two ceramic eggs in
      series at the apex.</b> With the feed at 10 ft the apex lands at
      <b>66.0 ft of wire</b> and the voltage maximum is at 65.0 ft — essentially
      on top of each other, closer than in the 24 ft version. Electrically the
      apex is an end, however much it looks like a mid-span support.</p>
      <p style="margin-top:7px">For F10-A: apex first, then leg 2 to the far
      support at 50 ft, then tension the tail to the end tie-off at 30 ft, in
      that order.</p></li>

    <li><h3>Set the sag, then choke the coax</h3>
      <p>2–3% slack per span, 8–12 in of sag. Trees move; a wire tensioned like
      a guitar string breaks at the first windstorm. Then put a common-mode
      choke at the transformer — with the feed at 10 ft on the side of the
      house, the coax shield is the thing most likely to bring RF back
      indoors.</p></li>

    <li><h3>Sweep it before you believe any of this</h3>
      <p>NanoVNA across 3.5, 7.1, 14.1, 21.2 and 28.4 MHz. Predicted resonances
      sit <b>1–2% low</b> of the vendor figures. Everything in this project is
      modelling; the sweep is the first real measurement, it costs nothing, and
      it is the only way to find out what the canopy is doing.</p></li>
  </ol>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Later</div>
    <h2>If the feed goes up to 24 ft</h2>
  </div>
  <p>Almost nothing changes. Raising the feed lengthens leg 1, so the 97.4 ft
  current maximum arrives slightly sooner along leg 2 and <b>support 3 moves out
  from 77 ft 2 in to 83 ft 9 in</b>, bearing 85°M to 87°M. The apex tree and the
  end tie-off do not move at all.</p>
  <div class="tbl"><table>
    <caption>What 14 ft of feed height buys</caption>
    <thead><tr><th>Band</th><th>Feed 10 ft</th><th>Feed 24 ft</th>
      <th>Gain</th></tr></thead>
    <tbody>
      <tr><td>80 m</td><td class="n">−8.68 dBi</td><td class="n">−7.83 dBi</td>
        <td class="n">+0.85</td></tr>
      <tr><td>40 m</td><td class="n">−5.47 dBi</td><td class="n">−4.80 dBi</td>
        <td class="n">+0.67</td></tr>
      <tr><td>20 m</td><td class="n">−0.67 dBi</td><td class="n">−0.21 dBi</td>
        <td class="n">+0.46</td></tr>
      <tr><td>15 m</td><td class="n">+1.93 dBi</td><td class="n">+2.06 dBi</td>
        <td class="n">+0.13</td></tr>
      <tr class="hi"><td>10 m</td><td class="n">+2.47 dBi</td>
        <td class="n">+2.26 dBi</td><td class="n">−0.21</td></tr>
    </tbody>
  </table></div>
  <p><b>0.30 dB overall</b>, and on 10 m the low feed is fractionally better.
  The feed is a voltage maximum — a current null — so its own height was never
  where the performance lived. Raise it when it is convenient, not as a
  project.</p>
</section>

<footer>
  <p><b>This is modelling, not measurement.</b> No NEC model was run and the
  antenna was not built as of 2026-09-05. The geometry is exact arithmetic and
  can be trusted; the dB figures cannot, and none of them include tree
  absorption — which the aerial photo now shows applies to most of the wire.</p>
  <p>Aerial imagery: King County GIS <span class="num">KingCo_Aerial_2025</span>
  orthomosaic, derived from EagleView Technologies photography and served
  publicly by King County. Parcel geometry from King County
  <span class="num">KingCo_Parcels</span>. Terrain from USGS 3DEP 1 m bare
  earth. Reproduce every drawing here with
  <span class="num">tools/build_deployment_guide.py</span>.</p>
  <p>Tree positions are read from the photograph; <b>tree heights are
  operator-supplied and were never measured</b> — no canopy-height model was
  obtainable for this site.</p>
</footer>
</div>
"""


if __name__ == "__main__":
    parts, views = main()
    print(f"\nSupport schedule ({PRIMARY.key}):")
    for i, (nm, e, n, u) in enumerate(PTS):
        d, b = polar(e, n)
        la, lo = to_latlon(e, n)
        sa, so = dms(la, lo)
        print(f"  {i+1}. {nm:13s} {u:5.1f} ft  {d/FT:6.1f} ft @ "
              f"{b:5.1f}T/{mag(b):5.1f}M  wire {wire_len_to(i)/FT:6.1f} ft  "
              f"{sa} {so}")
    print(f"  total wire used: {wire_len_to(len(PTS)-1)/FT:.1f} ft of 130 ft")

    out = (sys.argv[1] if len(sys.argv) > 1
           else os.path.join(HERE, "deployment-guide.html"))
    html = build_html(parts, views)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print(f"\nwrote {os.path.normpath(out)}  ({len(html)/1024:.0f} KB)")
