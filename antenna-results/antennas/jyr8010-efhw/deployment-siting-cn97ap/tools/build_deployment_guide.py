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
from site_geometry import polar, mag, to_latlon, dms     # noqa: E402

FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, "..", "imagery")

# The corridor capture: 55 m across, centred on ENU (14.6, -4.5).
CORRIDOR = ("kc2025_corridor.jpg", 55.0, (14.6, -4.5))
WIDE = ("kc2025_close.jpg", 90.0, (0.0, 0.0))

OPTS = {o.key: o for o in C.build_options()}
PLAN = OPTS["F10-A"]
PLAN24 = OPTS["A"]


def sup3d(opt):
    """[(name, height_ft, (E, N))] -> [(name, E, N, U_ft)]."""
    return [(nm, en[0], en[1], float(h)) for nm, h, en in opt.supports]


PTS = sup3d(PLAN)
PTS24 = sup3d(PLAN24)


def wire_len_to(i):
    """Wire length consumed up to support i, metres."""
    s = 0.0
    for k in range(i):
        a, b = PTS[k], PTS[k + 1]
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

def plan_svg(capture, size=1400, show24=False):
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
        pts24 = " ".join(f"{P(p[1], p[2])[0]:.1f},{P(p[1], p[2])[1]:.1f}"
                         for p in PTS24)
        o.append(f'<polyline points="{pts24}" fill="none" stroke="#7de2ff" '
                 f'stroke-width="4" stroke-dasharray="12 9" opacity=".85"/>')

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
        u = PLAN.height_at_wire(s) / FT
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
    wide = plan_svg(WIDE, 1200)
    out = {
        "plan": plan, "wide": wide, "iso": iso_svg(),
        "profile": profile_svg(),
    }
    views = []
    for nm, en, brg, cap in (
        ("From the feed, looking out along leg 1", (0.0, 0.0), 82.2,
         "Stand at the transformer with your back to the house."),
        ("From the lawn, looking back at the whole run", (8.0, -12.0), 55.0,
         "Stand in the middle of the lawn, southeast of the feed."),
        ("Under the apex, looking down leg 2", (15.87, 2.16), 130.0,
         "Stand at the base of the apex tree."),
        ("From the end, looking back up the wire", (29.16, -9.03), 287.0,
         "Stand at the end tie-off, looking back toward the house."),
    ):
        views.append((nm, cap, en, brg, eye_svg(en, brg, nm)))
    return out, views


CSS = """
:root{
  --bg:#f2f0ea; --surf:#ffffff; --surf2:#e9e6dd; --ink:#171b17; --ink2:#3f463e;
  --muted:#6d7568; --rule:#d3cec2; --grid:#c2bcae; --mast:#8d9585;
  --wire:#e0620d; --accent:#c8811a; --alt:#0f7fa6; --alarm:#b3372a;
  --sky:#dfe6ea; --ground:#dcdccb;
  --ff-d:"Archivo",system-ui,sans-serif;
  --ff-b:"IBM Plex Sans",system-ui,sans-serif;
  --ff-m:"IBM Plex Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#12150f; --surf:#1a1e17; --surf2:#232820; --ink:#eceadf; --ink2:#c3c6b8;
  --muted:#8d9481; --rule:#333a2e; --grid:#3d4536; --mast:#6d7663;
  --wire:#ff9142; --accent:#e2ab4c; --alt:#5cc4e6; --alarm:#e8705f;
  --sky:#1d2630; --ground:#242a1e;
}}
:root[data-theme="dark"]{
  --bg:#12150f; --surf:#1a1e17; --surf2:#232820; --ink:#eceadf; --ink2:#c3c6b8;
  --muted:#8d9481; --rule:#333a2e; --grid:#3d4536; --mast:#6d7663;
  --wire:#ff9142; --accent:#e2ab4c; --alt:#5cc4e6; --alarm:#e8705f;
  --sky:#1d2630; --ground:#242a1e;
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


def schedule_rows():
    r = []
    for i, (nm, e, n, u) in enumerate(PTS):
        d, b = polar(e, n)
        la, lo = to_latlon(e, n)
        sa, so = dms(la, lo)
        dist = "—" if d < 0.01 else f"{d/FT:.1f} ft"
        brg = "—" if d < 0.01 else f"{b:.0f}° / <b>{mag(b):.0f}°</b>"
        hi = ' class="hi"' if i in (1, 2) else ""
        r.append(
            f"<tr{hi}><td class='n'>{i+1}</td><td>{nm}</td>"
            f"<td class='n'>{u:.0f} ft</td><td class='n'>{dist}</td>"
            f"<td class='n'>{brg}</td>"
            f"<td class='n'>{wire_len_to(i)/FT:.1f} ft</td>"
            f"<td class='n' style='font-size:12.5px'>{sa}<br>{so}</td></tr>")
    return "\n".join(r)


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
    return f"""<title>Threading 130 Feet Into the Woods</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">

<header class="mast">
  <div class="eyebrow">Deployment guide · F10-A · JYR8010 EFHW · CN97ap</div>
  <h1>Threading 130 feet<br>into the woods</h1>
  <p class="lede">The bent flat-top, feed at 10 ft. Every position below is
  computed from the survey and checked against the 2025 King County aerial —
  which shows something none of the earlier analysis could: <b>this is a forest
  installation, not a lawn installation.</b></p>
  <div class="meta">
    <span>Wire used <b>{total_ft:.0f} ft</b> of 130</span>
    <span>Supports <b>4</b></span>
    <span>Highest throw <b>50 ft</b></span>
    <span>Declination <b>+15.3°E</b></span>
    <span>Imagery <b>King County 2025, 3–6 in/px</b></span>
  </div>
</header>

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
    <b>And there is no way to avoid it.</b> The mown lawn measures roughly
    <b>12 × 19 m (40 × 62 ft)</b>, a 74 ft diagonal. The wire needs
    <b>110 ft of ground path</b>. It does not fit in the open, at any bearing.
    A radial scan of open ground from the feed confirms it: the longest clear
    run in any direction is about 24 ft, at 120°T.
    <br><br>
    So this is not a choice between lawn and forest. Every option in the study
    — flat-top, inverted-V, sloper, all of them — puts most of the wire in or
    above canopy. <b>None of the dB figures anywhere in this project include a
    tree-absorption term.</b> Treat them as an optimistic ceiling, and treat the
    post-installation sweep as the real measurement.
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Overhead</div>
    <h2>Where every point lands</h2>
  </div>
  <figure>{parts['plan']}<figcaption><b>Solid orange</b> is F10-A with the
  feed at 10 ft. <b>Dashed blue</b> is the same design with the feed at 24 ft —
  only support 3 moves, and only by 6 ft 7 in. Bearings are given true first,
  <b>magnetic second in bold</b>; set your compass to the bold number.
  Aerial: King County GIS 2025 orthomosaic (EagleView), 3–6 in/px, requested in
  EPSG:3857 about a computed centre, so the overlay is georeferenced by
  construction rather than fitted to control points.</figcaption></figure>
  <figure>{parts['wide']}<figcaption>Wider view, 90 m across, showing how
  little open ground there is. The driveway, both yard corners and the
  original end mark are all inside this frame.</figcaption></figure>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">The numbers you take outside</div>
    <h2>Support schedule</h2>
  </div>
  <div class="tbl"><table>
    <caption>F10-A · feed fixed at 10 ft · bearings true / <b>magnetic</b></caption>
    <thead><tr><th>#</th><th>Point</th><th>Height</th><th>From feed</th>
      <th>Bearing T / <b>M</b></th><th>Wire used</th><th>Coordinates</th></tr>
    </thead>
    <tbody>{schedule_rows()}</tbody>
  </table></div>
  <p>Highlighted rows are the two that carry the design. <b>Support 3 sits at
  97.4 ft of wire</b> — that is deliberately the 40 m and 15 m current maximum,
  and it is why the end tie-off barely matters. Add <b>2–3% slack</b> beyond
  the tabulated wire lengths and expect 8–12 in of sag mid-span.</p>
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
      <p>Work from the transformer. Put a stake at each of these, measured with
      a tape and a compass set to <b>magnetic</b>:</p>
      <ul class="tight">
        <li><b>52 ft 6 in at 67°M</b> — under the apex tree</li>
        <li><b>77 ft 2 in at 85°M</b> — under the far support</li>
        <li><b>100 ft 2 in at 92°M</b> — under the end tie-off</li>
      </ul>
      <p style="margin-top:7px">If a stake lands where no usable trunk stands,
      stop here — that is the whole plan's assumption and it is cheaper to find
      out now. Support 3 in particular has never been ground-verified; it is a
      computed position, not an observed tree.</p></li>

    <li><h3>Pick the limbs and confirm they clear 50 ft</h3>
      <p>Both the apex and the far support want <b>50 ft</b>. Sight up from
      each stake and find a limb you can actually get a line over at that
      height. Ten feet low on either one costs about 0.9 dB — not fatal, but
      keep them even with each other so the middle span stays level.</p></li>

    <li><h3>Throw both lines before attaching any wire</h3>
      <p>Two throws, both at 50 ft, both routine with a slingshot and a
      12 oz weight. Get both up and cleated off before the antenna comes out of
      the bag. Wrestling 130 ft of wire while you are still fighting a throw
      line is how wire gets kinked and insulators get dropped in the
      undergrowth.</p></li>

    <li><h3>Lay the wire out on the ground along the marked path</h3>
      <p>Flake it out from the feed stake toward the end, following your stakes.
      This is where you find out whether the run is really clear — <b>62% of it
      is under canopy</b>, so expect to route around trunks and through
      understory rather than pulling a straight line. Keep the transformer end
      at the house and do not let the wire cross itself.</p></li>

    <li><h3>Hang the apex, then the far support, then the end</h3>
      <p>In that order. Raise the apex to 50 ft first and let the wire hang;
      then take up leg 2 to the far support at 50 ft; then tension the tail to
      the end tie-off at 30 ft. <b>Two ceramic eggs in series at the apex.</b>
      With the feed at 10 ft the apex lands at <b>66.0 ft of wire</b> and the
      voltage maximum is at 65.0 ft — they are essentially on top of each other,
      closer than in the 24 ft version. Electrically the apex is an end, however
      much it looks like a mid-span support.</p></li>

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
    print("\nSupport schedule (F10-A):")
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
