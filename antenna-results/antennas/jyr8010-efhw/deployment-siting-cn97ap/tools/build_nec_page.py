#!/usr/bin/env python3
"""Every wire on one lot: the lineup page, re-ranked by NEC-2.

Reads ../data/nec-scores.json (tools/nec_search.py) and
../data/nec-validation.json (tools/nec_validate.py); runs no search itself.
Keeps the lineup page's format - aerial maps with badges, legends, scorecard,
band table, heat map, cards, 40+20 m section, trust notes - and adds the model
check, NEC-vs-analytic columns, the roof additions and the full ranking.

Requires Pillow. Run from the repository root:

    python .../tools/build_nec_page.py [out.html]

Also writes ../imagery/nec_top.jpg, nec_roof.jpg and nec_40_20.jpg.
"""

import base64
import io
import json
import math
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont            # noqa: E402
import compare_options as C                            # noqa: E402
import canopy_from_ortho as K                          # noqa: E402
from site_geometry import polar, mag                   # noqa: E402

FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
IMGDIR = os.path.join(HERE, "..", "imagery")
# The wide 200 m capture: several NEC winners run past the 90 m frame's edge.
CAP_FN, CAP_SPAN = "kc2025_wide.jpg", 200.0
SIZE = 1600
PPM = SIZE / CAP_SPAN
B3, B2 = ["40m", "20m", "15m"], ["40m", "20m"]

with open(os.path.join(DATA, "nec-scores.json"), encoding="utf-8") as fh:
    S = json.load(fh)
with open(os.path.join(DATA, "nec-validation.json"), encoding="utf-8") as fh:
    V = json.load(fh)
THR = S["workable_nec_dBi"]


def _wire(d):
    o = SimpleNamespace(**d)
    o.supports = [(nm, int(round(h)), (e, n)) for nm, h, e, n in d["supports"]]
    o.feed = (tuple(d["feed"][0]), d["feed"][1])
    return o


WIRES = [_wire(d) for d in S["wires"]]            # already in NEC 3-band order
BY = {o.key: o for o in WIRES}
ALIAS = {a: o for o in WIRES for a in o.aliases}
N_ALL = len(WIRES)


def get(k):
    return BY.get(k) or ALIAS.get(k)


def sg(v, fmt="+.2f"):
    return format(v, fmt).replace("-", "−")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def is_L(o):
    return o.family == "inverted-L"


def at_transformer(o):
    return math.dist(o.feed[0], (0.0, 0.0)) < 0.5


def elevated(o):
    pts = {}
    for nm, h, en in o.supports[1:]:
        k = (round(en[0], 1), round(en[1], 1))
        if h > pts.get(k, (0, ""))[0]:
            pts[k] = (h, nm)
    return [v for v in pts.values() if v[0] > 15]


def effort(o):
    el = elevated(o)
    throws = [h for h, nm in el if nm != "post"]
    posts = [h for h, nm in el if nm == "post"]
    s = f"{len(throws)} throw{'s' if len(throws) != 1 else ''}"
    if posts:
        s += f" + {posts[0]} ft post"
    return s, (max(throws) if throws else max((h for h, _ in el), default=0))


def hi(o):
    return effort(o)[1]


def throw_word(h):
    return ("easy" if h <= 55 else "hard" if h <= 90 else
            "very hard" if h <= 130 else "climb")


FIXED = {"CURRENT": "Up now", "BASE": "BASE · original plan"}
PRE = {"SRCH": "", "W": "40/20 ", "R": "Roof ", "N": "NEC ", "N2": "NEC 40/20 ",
       "NR": "NEC roof "}
KIND = {"SL": "sloper", "V": "inverted-V", "L": "inverted-L", "DN": "down-sloper"}


def name_of(o):
    k = o.key
    if k in FIXED:
        return FIXED[k]
    if "existing" in o.groups:
        return k
    pre, rest = k.split("-", 1)
    if rest.startswith("RB"):
        return ("NEC " if pre.startswith("N") else "") + "RB-POST20, post re-placed" + \
            (" for 40/20" if "2" in pre or pre == "W" else "")
    if rest.startswith("F10A"):
        return ("NEC " if pre.startswith("N") else "") + "F10-A, leg 2 re-aimed" + \
            (" for 40/20" if "2" in pre or pre == "W" else "")
    kind = "".join(ch for ch in rest if ch.isalpha())
    num = rest[len(kind):]
    nm = f"{PRE.get(pre, '')}{KIND.get(kind, kind)} {num}".strip()
    return nm[0].upper() + nm[1:]


def old_model(o):
    m = o.model
    return ("bent wire" if m.startswith("bent") else "slant §9" if m.startswith("slant")
            else "hybrid L" if m.startswith("hybrid") else "horizontal")


def near(a, b, tol=6.0):
    return (math.dist(a.supports[1][2], b.supports[1][2]) < tol and
            math.dist(a.supports[-1][2], b.supports[-1][2]) < tol and
            math.dist(a.feed[0], b.feed[0]) < 0.5)


def distinct(seq, n, pred=lambda o: True, start=()):
    out = list(start)
    for o in seq:
        if pred(o) and o not in out and not any(near(o, w) for w in out):
            out.append(o)
        if len(out) >= n + len(start):
            break
    return out[len(start):]


def uniq(seq):
    out = []
    for o in seq:
        if o is not None and o not in out:
            out.append(o)
    return out


# --------------------------------------------------------------------------
# Selections
# --------------------------------------------------------------------------

REFS = uniq(get(k) for k in ("CURRENT", "BASE", "RB-POST20", "F10-A"))
LINEUP_TX = [o for o in WIRES if "analytic:lineup" in o.groups]
ROOF_KEPT = uniq(get(k) for k in ("R-SL1", "R-SL2", "R-SL3", "R-L1", "R-L2", "R-L3"))


def roof_adds(prefix, n):
    out = []
    for i in range(1, 7):
        o = get(f"{prefix}{i}")
        if o is not None and o not in ROOF_KEPT and o not in out:
            out.append(o)
        if len(out) == n:
            break
    return out


ADD_SL, ADD_L, ADD_V = roof_adds("NR-SL", 3), roof_adds("NR-L", 3), roof_adds("NR-V", 3)
ROOF_SL = [o for o in ROOF_KEPT if o.family == "sloper"] + ADD_SL
ROOF_L = [o for o in ROOF_KEPT if is_L(o)] + ADD_L
ROOF_V = ADD_V
ROOF_DOWN = get("NR-DN1")
NEC_TOP = distinct(WIRES, 12)
BY2 = sorted(WIRES, key=lambda o: o.nec_rank2)
WIN2 = distinct(BY2, 5)
for _x in (next((o for o in BY2 if o.family == "sloper"), None),
           next((o for o in BY2 if hi(o) <= 55 and not is_L(o)), None)):
    if _x is not None and _x not in WIN2 and not any(near(_x, w) for w in WIN2):
        WIN2.append(_x)
LISTED = uniq(REFS + LINEUP_TX + ROOF_KEPT + ADD_SL + ADD_L + ADD_V + NEC_TOP)
SHOWN = uniq(LISTED + WIN2 + ROOF_SL + ROOF_L + ROOF_V + [ROOF_DOWN])

print("classifying canopy ...")
_im, _ppm, _cen = K.load("close")
_mask = K.canopy_mask(_im)
CANOPY = {}
for _o in WIRES:
    _prof = []
    for _i in range(len(_o.supports) - 1):
        _a, _b = _o.supports[_i][2], _o.supports[_i + 1][2]
        if math.dist(_a, _b) > 0.01:
            _prof += K.profile_along(_mask, _ppm, _cen, _im.size, _a, _b)
    CANOPY[_o.key] = sum(v for _, v in _prof) / max(len(_prof), 1)


# --------------------------------------------------------------------------
# Colour: by shape. Documented slots 1-3, validated all-pairs both themes.
# --------------------------------------------------------------------------

COL = {"sloper": "#2a78d6", "bent": "#d95926", "ell": "#1baf7a",
       "now": "#ffffff", "plan": "#c3c2b7"}
INK = {"#2a78d6": "#ffffff"}
DASHES = ["", "16 9", "5 7"]


def group_of(o):
    if o.key == "CURRENT":
        return "now"
    if o.key == "BASE":
        return "plan"
    if o.family == "sloper":
        return "sloper"
    if is_L(o):
        return "ell"
    return "bent"


def items_for(opts, labels):
    count, out = {}, []
    for lab, o in zip(labels, opts):
        g = group_of(o)
        i = count.get(g, 0)
        count[g] = i + 1
        dash = "" if g == "now" else "12 8" if g == "plan" else DASHES[i % 3]
        out.append((lab, o, COL[g], dash))
    return out


def P(en):
    return (SIZE / 2 + en[0] * PPM, SIZE / 2 - en[1] * PPM)


def crop_for(opts, margin_m=7.0, min_m=26.0):
    pts = [P(en) for o in opts for _, _, en in o.supports] + [P((0.0, 0.0))]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    side = min(max(x1 - x0, y1 - y0, min_m * PPM) + 2 * margin_m * PPM, SIZE)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return (min(max(cx - side / 2, 0), SIZE - side),
            min(max(cy - side / 2, 0), SIZE - side), side, side)


def far_end(o):
    pts = [en for _, _, en in o.supports]
    d = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, d[-1]) > 0.01:
            d.append(p)
    return d[-1], d[-2]


def ortho_defs():
    im = Image.open(os.path.join(IMGDIR, CAP_FN)).convert("RGB").resize(
        (SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    return (f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
            f'<defs><image id="ortho" x="0" y="0" width="{SIZE}" height="{SIZE}" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>'
            f'<filter id="sh" x="-40%" y="-40%" width="180%" height="180%">'
            f'<feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#000" '
            f'flood-opacity=".95"/></filter></defs></svg>')


def map_svg(items, faded=(), crop=None, aria="", map_id=None, small=False):
    x, y, w, h = crop
    s = w / 700
    o = [f'<svg viewBox="{x:.1f} {y:.1f} {w:.1f} {h:.1f}" '
         f'xmlns="http://www.w3.org/2000/svg" class="plan"'
         + (f' id="{map_id}"' if map_id else "")
         + f' role="img" aria-label="{esc(aria)}"><use href="#ortho"/>'
         f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
         f'fill="#000" opacity=".12"/>']
    se, sw, ne = P((46.9, -32.0)), P((-69.9, -6.8)), P((53.5, 99.2))
    o.append(f'<polyline points="{sw[0]:.1f},{sw[1]:.1f} {se[0]:.1f},{se[1]:.1f} '
             f'{ne[0]:.1f},{ne[1]:.1f}" fill="none" stroke="#fff" '
             f'stroke-width="{2.2*s:.2f}" stroke-dasharray="{9*s:.1f} {6*s:.1f}" '
             f'opacity=".8"/>')
    rb = " ".join(f"{P(p)[0]:.1f},{P(p)[1]:.1f}" for p in C.RED_BOX)
    o.append(f'<polygon points="{rb}" fill="none" stroke="#ff4b4b" '
             f'stroke-width="{2*s:.2f}" opacity=".7"/>')
    for fo in faded:
        pts = " ".join(f"{P(en)[0]:.1f},{P(en)[1]:.1f}" for _, _, en in fo.supports)
        o.append(f'<polyline points="{pts}" fill="none" stroke="#fff" '
                 f'stroke-width="{2*s:.2f}" opacity=".35" stroke-linejoin="round"/>')
    placed = []
    for lab, ob, col, dash in items:
        pts = " ".join(f"{P(en)[0]:.1f},{P(en)[1]:.1f}" for _, _, en in ob.supports)
        da = (f' stroke-dasharray="{" ".join(f"{float(v)*s:.1f}" for v in dash.split())}"'
              if dash else "")
        g = [f'<g class="wire" data-k="{ob.key}">',
             f'<polyline points="{pts}" fill="none" stroke="#0b0d0f" '
             f'stroke-width="{9*s:.2f}" opacity=".6" stroke-linejoin="round"/>',
             f'<polyline points="{pts}" fill="none" stroke="{col}" '
             f'stroke-width="{4.6*s:.2f}" stroke-linejoin="round" '
             f'stroke-linecap="round"{da}/>']
        for i, (nm, hgt, en) in enumerate(ob.supports[1:], 1):
            px, py = P(en)
            if math.dist(en, ob.supports[i - 1][2]) < 0.01:
                g.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{12*s:.1f}" '
                         f'fill="none" stroke="#0b0d0f" stroke-width="{5*s:.1f}"/>'
                         f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{12*s:.1f}" '
                         f'fill="none" stroke="{col}" stroke-width="{2.6*s:.1f}"/>')
                if not small:
                    g.append(f'<text x="{px + 16*s:.1f}" y="{py + 5*s:.1f}" class="lp" '
                             f'style="font-size:{13*s:.1f}px" filter="url(#sh)">'
                             f'↓{ob.supports[i - 1][1] - hgt} ft</text>')
            else:
                g.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{4.5*s:.1f}" '
                         f'fill="{col}" stroke="#0b0d0f" stroke-width="{2*s:.1f}"/>')
        end, prev = far_end(ob)
        ex, ey = P(end)
        qx, qy = P(prev)
        dx, dy = ex - qx, ey - qy
        L = math.hypot(dx, dy) or 1
        bx, by = ex + dx / L * 20 * s, ey + dy / L * 20 * s
        for _ in range(10):
            if not [q for q in placed if math.dist(q, (bx, by)) < 27 * s]:
                break
            bx, by = bx - dy / L * 26 * s, by + dx / L * 26 * s
        bx = min(max(bx, x + 16 * s), x + w - 16 * s)
        by = min(max(by, y + 16 * s), y + h - 16 * s)
        placed.append((bx, by))
        g.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{12.5*s:.1f}" fill="{col}" '
                 f'stroke="#0b0d0f" stroke-width="{2.5*s:.1f}"/><text x="{bx:.1f}" '
                 f'y="{by + 4.4*s:.1f}" text-anchor="middle" font-family="IBM Plex Mono, '
                 f'ui-monospace, monospace" font-weight="600" '
                 f'font-size="{(12 if len(lab) < 3 else 10)*s:.1f}" '
                 f'fill="{INK.get(col, "#0b0d0f")}">{lab}</text></g>')
        o.extend(g)
    fx, fy = P((0.0, 0.0))
    o.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{7*s:.1f}" fill="#fff" '
             f'stroke="#0b0d0f" stroke-width="{3*s:.1f}"/>')
    for ren in {ob.feed[0] for _, ob, _, _ in items if not at_transformer(ob)}:
        rx, ry = P(ren)
        o.append(f'<rect x="{rx - 7*s:.1f}" y="{ry - 7*s:.1f}" width="{14*s:.1f}" '
                 f'height="{14*s:.1f}" fill="#fff" stroke="#0b0d0f" '
                 f'stroke-width="{3*s:.1f}"/>')
    bar = 10 * PPM
    x0, y0 = x + 18 * s, y + h - 20 * s
    o.append(f'<g filter="url(#sh)"><line x1="{x0:.1f}" y1="{y0:.1f}" '
             f'x2="{x0 + bar:.1f}" y2="{y0:.1f}" stroke="#fff" stroke-width="{3.5*s:.1f}"/>'
             f'<text x="{x0:.1f}" y="{y0 - 8*s:.1f}" class="lp" '
             f'style="font-size:{12.5*s:.1f}px">10 m · 33 ft</text>'
             f'<path d="M{x + w - 24*s:.1f} {y + 40*s:.1f} L{x + w - 24*s:.1f} '
             f'{y + 14*s:.1f} M{x + w - 31*s:.1f} {y + 23*s:.1f} L{x + w - 24*s:.1f} '
             f'{y + 13*s:.1f} L{x + w - 17*s:.1f} {y + 23*s:.1f}" fill="none" '
             f'stroke="#fff" stroke-width="{3*s:.1f}"/><text x="{x + w - 24*s:.1f}" '
             f'y="{y + 56*s:.1f}" class="lp" style="font-size:{12.5*s:.1f}px" '
             f'text-anchor="middle">N</text></g></svg>')
    return "".join(o)


# --------------------------------------------------------------------------
# JPEGs
# --------------------------------------------------------------------------

def _font(sz, bold=False):
    for fn in ("arialbd.ttf" if bold else "arial.ttf",
               "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(fn, sz)
        except Exception:
            continue
    return ImageFont.load_default()


def _dashed(d, pts, fill, width, dash):
    if not dash:
        d.line(pts, fill=fill, width=width, joint="curve")
        return
    on, off = dash
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        t = 0.0
        while t < L:
            t1 = min(t + on, L)
            d.line([(x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L),
                    (x0 + (x1 - x0) * t1 / L, y0 + (y1 - y0) * t1 / L)],
                   fill=fill, width=width)
            t += on + off


def render_jpeg(items, faded, crop, title, rows, path, out_px=1600):
    x, y, w, h = crop
    k = out_px / w
    base = Image.open(os.path.join(IMGDIR, CAP_FN)).convert("RGB").resize(
        (SIZE, SIZE), Image.LANCZOS)
    im = base.crop((int(x), int(y), int(x + w), int(y + h))).resize(
        (out_px, out_px), Image.LANCZOS)
    d = ImageDraw.Draw(im, "RGBA")

    def Q(en):
        px, py = P(en)
        return ((px - x) * k, (py - y) * k)

    _dashed(d, [Q((-69.9, -6.8)), Q((46.9, -32.0)), Q((53.5, 99.2))],
            (255, 255, 255, 200), 4, (18, 12))
    for fo in faded:
        d.line([Q(en) for _, _, en in fo.supports], fill=(255, 255, 255, 110), width=3)
    for lab, ob, col, dash in items:
        rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
        pts = [Q(en) for _, _, en in ob.supports]
        d.line(pts, fill=(11, 13, 15, 170), width=15, joint="curve")
        _dashed(d, pts, rgb + (255,), 8,
                tuple(int(float(v) * 1.6) for v in dash.split()) if dash else None)
        if is_L(ob):
            px, py = Q(ob.supports[1][2])
            d.ellipse([px - 18, py - 18, px + 18, py + 18], outline=rgb, width=5)
        end, prev = far_end(ob)
        ex, ey = Q(end)
        qx, qy = Q(prev)
        L = math.hypot(ex - qx, ey - qy) or 1
        bx = min(max(ex + (ex - qx) / L * 34, 24), out_px - 24)
        by = min(max(ey + (ey - qy) / L * 34, 24), out_px - 24)
        d.ellipse([bx - 21, by - 21, bx + 21, by + 21], fill=rgb + (255,),
                  outline=(11, 13, 15), width=4)
        d.text((bx, by), lab, fill=(255, 255, 255) if INK.get(col) else (11, 13, 15),
               font=_font(19 if len(lab) < 3 else 15, True), anchor="mm")
    fx, fy = Q((0.0, 0.0))
    d.ellipse([fx - 11, fy - 11, fx + 11, fy + 11], fill=(255, 255, 255),
              outline=(11, 13, 15), width=4)
    for ren in {ob.feed[0] for _, ob, _, _ in items if not at_transformer(ob)}:
        rx, ry = Q(ren)
        d.rectangle([rx - 11, ry - 11, rx + 11, ry + 11], fill=(255, 255, 255),
                    outline=(11, 13, 15), width=4)
    pad, lh = 22, 34
    panel_h = pad * 2 + 44 + lh * len(rows)
    canvas = Image.new("RGB", (out_px, out_px + panel_h), (11, 13, 15))
    canvas.paste(im, (0, 0))
    d = ImageDraw.Draw(canvas, "RGBA")
    d.text((pad, out_px + pad), title, fill=(255, 255, 255), font=_font(28, True))
    for i, (lab, col, text) in enumerate(rows):
        yy = out_px + pad + 50 + i * lh
        rgb = tuple(int(col[j:j + 2], 16) for j in (1, 3, 5))
        d.ellipse([pad, yy, pad + 28, yy + 28], fill=rgb, outline=(255, 255, 255), width=2)
        d.text((pad + 14, yy + 14), lab, fill=(255, 255, 255) if INK.get(col)
               else (11, 13, 15), font=_font(13, True), anchor="mm")
        d.text((pad + 42, yy + 3), text, fill=(235, 235, 230), font=_font(21))
    canvas.save(path, quality=88)
    print("  wrote", os.path.normpath(path))


def jpeg_rows(items, metric="3"):
    out = []
    for lab, o, col, dash in items:
        m = o.nec3 if metric == "3" else o.nec2
        rank = o.nec_rank3 if metric == "3" else o.nec_rank2
        old = o.ana_rank3 if metric == "3" else o.ana_rank2
        out.append((lab, col, f"{name_of(o)}  ·  NEC #{rank} (was #{old})  ·  "
                              f"{m['n_workable']}/{m['n_cells']} cells  ·  "
                              f"{m['mean_power_dBi']:+.2f} dBi  ·  high point {hi(o)} ft"))
    return out


# --------------------------------------------------------------------------
# Heat map + scatter
# --------------------------------------------------------------------------

def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _oklab(hx):
    r, g, b = (_lin(int(hx[i:i + 2], 16)) for i in (1, 3, 5))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _hex(L, a, b):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    out = "#"
    for x in (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
              -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
              -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s):
        x = min(1.0, max(0.0, x))
        out += f"{round((12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055) * 255):02x}"
    return out


def _lum(hx):
    r, g, b = (_lin(int(hx[i:i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


HEAT = {"light": ("#e34948", "#f0efec", "#256abf"),
        "dark": ("#e66767", "#383835", "#3987e5")}


def heat(v, mode):
    poor, mid, good = HEAT[mode]
    t, pole = ((min((v - THR) / 8.0, 1.0), good) if v >= THR
               else (min((THR - v) / 20.0, 1.0), poor))
    a, b = _oklab(mid), _oklab(pole)
    c = _hex(*(a[i] + (b[i] - a[i]) * t for i in range(3)))
    ink = ("#0b0b0b" if (_lum(c) + 0.05) / (_lum("#0b0b0b") + 0.05) >=
           1.05 / (_lum(c) + 0.05) else "#ffffff")
    return c, ink


def region_means(o, bands=B3):
    return [10 * math.log10(sum(10 ** (o.nec[b][i] / 10) for b in bands) / len(bands))
            for i in range(len(S["targets"]))]


SCAT_COL = {"bent wire": "#d95926", "slant §9": "#2a78d6", "hybrid L": "#1baf7a",
            "horizontal": "#d95926"}


def scatter_svg():
    w, h = 640, 430
    L, R, T, B = 58, 22, 18, 52
    sx, sy = (w - L - R) / 75, (h - T - B) / 75

    def X(v):
        return L + v * sx

    def Y(v):
        return h - B - v * sy

    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
         f'class="chart" role="img" aria-label="Workable cells per wire, analytic '
         f'model against NEC-2">']
    for v in (0, 25, 50, 75):
        o.append(f'<line x1="{X(0)}" y1="{Y(v):.1f}" x2="{X(75):.1f}" y2="{Y(v):.1f}" '
                 f'class="gl"/><text x="{L - 8}" y="{Y(v) + 4:.1f}" class="ax" '
                 f'text-anchor="end">{v}</text>')
        o.append(f'<line x1="{X(v):.1f}" y1="{Y(0):.1f}" x2="{X(v):.1f}" y2="{Y(75):.1f}" '
                 f'class="gl"/><text x="{X(v):.1f}" y="{h - B + 18}" class="ax" '
                 f'text-anchor="middle">{v}</text>')
    o.append(f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(75):.1f}" y2="{Y(75):.1f}" '
             f'class="diag"/><text x="{X(71):.1f}" y="{Y(73):.1f}" class="ax" '
             f'text-anchor="end">same score</text>')
    o.append(f'<text x="{(L + w - R) / 2:.0f}" y="{h - 10}" class="ax" '
             f'text-anchor="middle">old analytic score · cells of 75</text>'
             f'<text x="16" y="{(T + h - B) / 2:.0f}" class="ax" text-anchor="middle" '
             f'transform="rotate(-90 16 {(T + h - B) / 2:.0f})">NEC-2 score · cells of 75'
             f'</text>')
    for o_ in WIRES:
        grp = old_model(o_)
        jit = ((hash(o_.key) % 7) - 3) * 0.12
        cx, cy = X(o_.ana3["n_workable"] + jit), Y(o_.nec3["n_workable"] - jit)
        o.append(f'<g class="pt"><title>{esc(name_of(o_))} ({grp}): analytic '
                 f'{o_.ana3["n_workable"]}/75 (#{o_.ana_rank3}) → NEC '
                 f'{o_.nec3["n_workable"]}/75 (#{o_.nec_rank3})</title>'
                 f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10" fill="transparent"/>'
                 f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="{SCAT_COL[grp]}" '
                 f'class="dot"/></g>')
    o.append('</svg>')
    return "".join(o)


# --------------------------------------------------------------------------
# HTML pieces
# --------------------------------------------------------------------------

EXTRA_CSS = """
.lay{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(270px,1fr);gap:18px;align-items:start}
@media(max-width:900px){.lay{grid-template-columns:1fr}}
.tri{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;align-items:start}
.plan text.lp{font-family:var(--ff-m);fill:#fff}
.plan g.wire{transition:opacity .15s}
.plan.dim g.wire{opacity:.16}
.plan.dim g.wire.on{opacity:1}
.legend{list-style:none;margin:0;padding:6px;display:flex;flex-direction:column;gap:2px;
  background:var(--surf);border:1px solid var(--rule);border-radius:5px}
.legend li{display:grid;grid-template-columns:30px 46px minmax(0,1fr);gap:10px;align-items:center;
  padding:6px 8px;border-radius:4px}
.legend li:hover,.legend li:focus-visible{background:var(--surf2);outline:none}
.legend li:focus-visible{box-shadow:inset 0 0 0 2px var(--wire)}
.legend .nm{font-weight:600;color:var(--ink);font-size:14px;line-height:1.25}
.legend .sub{font-family:var(--ff-m);font-size:11.5px;color:var(--muted)}
.badge{min-width:24px;height:24px;padding:0 4px;border-radius:12px;display:inline-flex;
  align-items:center;justify-content:center;font-family:var(--ff-m);font-size:11px;
  font-weight:600;box-shadow:0 0 0 2px var(--ink)}
.sw{display:block;width:44px;height:0;border-top-width:5px;border-top-style:solid}
.chip{display:inline-block;font-family:var(--ff-m);font-size:11px;padding:2px 8px;
  border-radius:10px;border:1px solid var(--rule);color:var(--ink2);white-space:nowrap}
.chip.bad{border-color:var(--alarm);color:var(--alarm)}
td.nm{font-weight:600;color:var(--ink);white-space:nowrap}
td .badge{margin-right:8px;vertical-align:middle;height:22px}
tr.ref td{color:var(--muted)}
tr[data-hl]:hover td,tr[data-hl]:focus-visible td{background:var(--surf2)}
.up{color:var(--ink)} .down{color:var(--alarm)}
table.heat{font-size:13px}
table.heat th,table.heat td{padding:5px 6px}
table.heat th.o{text-align:center}
table.heat td.h{font-family:var(--ff-m);text-align:center;background:var(--c);color:var(--t);
  border:2px solid var(--surf);border-radius:4px}
.scale{display:flex;flex-direction:column;gap:6px;max-width:520px}
.scale .bar{height:12px;border-radius:4px;background:linear-gradient(90deg,var(--hp) 0%,var(--hm) 71.4%,var(--hg) 100%)}
.scale .ticks{position:relative;height:16px;font-family:var(--ff-m);font-size:11px;color:var(--muted)}
.scale .ticks span{position:absolute;transform:translateX(-50%)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:16px}
.card{background:var(--surf);border:1px solid var(--rule);border-radius:5px;overflow:hidden;
  display:flex;flex-direction:column}
.card svg{display:block;width:100%;height:auto}
.card .body{padding:13px 15px 15px;display:flex;flex-direction:column;gap:9px}
.card .hd{display:flex;align-items:center;gap:10px}
.card h3{margin:0;font-size:17px}
.kv{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.kv div{background:var(--surf2);padding:6px 8px;border-radius:3px;display:flex;flex-direction:column;gap:1px}
.kv b{font-family:var(--ff-m);font-size:14.5px;color:var(--ink);font-variant-numeric:tabular-nums}
.kv span{font-family:var(--ff-m);font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}
ul.sched{margin:0;padding-left:17px;font-size:13.5px;color:var(--ink2);display:flex;flex-direction:column;gap:2px}
svg.chart{display:block;width:100%;height:auto;max-width:720px}
svg.chart .gl{stroke:var(--rule);stroke-width:1}
svg.chart .diag{stroke:var(--muted);stroke-width:1.5}
svg.chart .ax{font-family:var(--ff-m);font-size:11px;fill:var(--muted)}
svg.chart .dot{stroke:var(--surf);stroke-width:2}
svg.chart g.pt:hover .dot{stroke:var(--ink)}
.keyrow{display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:var(--ink2)}
.keyrow span{display:inline-flex;align-items:center;gap:6px}
.keyrow i{width:10px;height:10px;border-radius:50%;display:inline-block}
details.all summary{cursor:pointer;font-weight:600;color:var(--ink);padding:10px 0}
details.all summary:focus-visible{outline:2px solid var(--wire);outline-offset:2px}
"""

HEAT_CSS = """
:root{--hp:#e34948;--hm:#f0efec;--hg:#256abf}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--hp:#e66767;--hm:#383835;--hg:#3987e5}
  :root:not([data-theme="light"]) table.heat td.h{background:var(--cd);color:var(--td)}}
:root[data-theme="dark"]{--hp:#e66767;--hm:#383835;--hg:#3987e5}
:root[data-theme="dark"] table.heat td.h{background:var(--cd);color:var(--td)}
"""

JS = """
<script>
document.querySelectorAll('[data-hl]').forEach(function(el){
  var map=document.getElementById(el.getAttribute('data-map'));
  if(!map)return;
  var k=el.getAttribute('data-hl');
  function on(){map.classList.add('dim');map.querySelectorAll('g.wire').forEach(function(g){
    g.classList.toggle('on',g.getAttribute('data-k')===k);});}
  function off(){map.classList.remove('dim');}
  el.addEventListener('mouseenter',on);el.addEventListener('mouseleave',off);
  el.addEventListener('focus',on);el.addEventListener('blur',off);
});
</script>
"""


def badge(lab, col):
    return (f'<span class="badge" style="background:{col};color:{INK.get(col, "#0b0d0f")}">'
            f'{lab}</span>')


def swatch(col, dash):
    style = ("dashed" if dash and dash.split()[0] in ("16", "12") else
             "dotted" if dash else "solid")
    return f'<span class="sw" style="border-top-color:{col};border-top-style:{style}"></span>'


def legend(items, map_id, metric="3"):
    rows = []
    for lab, o, col, dash in items:
        m = o.nec3 if metric == "3" else o.nec2
        r, old = ((o.nec_rank3, o.ana_rank3) if metric == "3"
                  else (o.nec_rank2, o.ana_rank2))
        rows.append(f'<li tabindex="0" data-hl="{o.key}" data-map="{map_id}">'
                    f'{badge(lab, col)}{swatch(col, dash)}<div><div class="nm">'
                    f'{esc(name_of(o))}</div><div class="sub">NEC #{r} of {N_ALL} · '
                    f'{m["n_workable"]}/{m["n_cells"]} · was #{old}</div></div></li>')
    return f'<ul class="legend">{"".join(rows)}</ul>'


def move(o, metric="3"):
    d = (o.ana_rank3 - o.nec_rank3) if metric == "3" else (o.ana_rank2 - o.nec_rank2)
    if d > 0:
        return f'<span class="up">▲ {d}</span>'
    if d < 0:
        return f'<span class="down">▼ {-d}</span>'
    return "–"


def schedule(o):
    out = []
    fen = o.feed[0]
    for i, (nm, h, en) in enumerate(o.supports):
        d, b = polar(en[0] - fen[0], en[1] - fen[1])
        if i == 0:
            td, tb = polar(*fen)
            where = ("at the transformer" if td < 0.5 else
                     f"on the roof, {td/FT:.0f} ft from the transformer @ {mag(tb):.0f}°M")
            out.append(f"<li>{esc(nm)} · {h} ft · {where}</li>")
        elif math.dist(en, o.supports[i - 1][2]) < 0.01:
            out.append(f"<li>then hangs straight down to {h} ft</li>")
        else:
            out.append(f"<li>{esc(nm)} · <b>{h} ft</b> · {d/FT:.0f} ft @ "
                       f"<b>{mag(b):.0f}°M</b></li>")
    return "".join(out)


def score_row(o, lab, col, map_id, cls=""):
    m, m2 = o.nec3, o.nec2
    eff, h = effort(o)
    return (f'<tr tabindex="0" data-hl="{o.key}" data-map="{map_id}"{cls}>'
            f'<td class="nm">{badge(lab, col) if lab else ""}{esc(name_of(o))}</td>'
            f'<td class="n"><b>{o.nec_rank3}</b></td>'
            f'<td class="n"><b>{m["n_workable"]}</b> / 75</td>'
            f'<td class="n">{m["n_regions_covered"]} / 25</td>'
            f'<td class="n">{sg(m["mean_power_dBi"])}</td>'
            f'<td class="n">{sg(m["worst_dBi"], "+.1f")}</td>'
            f'<td class="n">{o.nec_rank2} · {m2["n_workable"]}/50</td>'
            f'<td class="n">{o.ana_rank3} · {o.ana3["n_workable"]}/75</td>'
            f'<td class="n">{move(o)}</td>'
            f'<td class="n">{h} ft · {throw_word(h)}</td><td>{eff}</td>'
            f'<td class="n">{CANOPY[o.key]*100:.0f}%</td><td>{esc(o.parcel)}</td></tr>')


SCORE_HEAD = ('<thead><tr><th>Wire</th><th>NEC rank</th><th>Cells</th><th>Regions</th>'
              '<th>dBi</th><th>Worst</th><th>40+20 rank · cells</th>'
              '<th>Old rank · cells</th><th>Moved</th><th>Highest</th><th>Effort</th>'
              '<th>Canopy</th><th>Lot</th></tr></thead>')


def card(lab, o, col, dash, faded):
    m, m2 = o.nec3, o.nec2
    thumb = map_svg([(lab, o, col, dash)], [x for x in faded if x is not o],
                    crop_for([o], 6.0, 30.0), name_of(o), small=True)
    h = hi(o)
    if is_L(o):
        take = (f"One attachment at {h} ft, then "
                f"{o.supports[1][1] - o.supports[2][1]} ft of wire hangs straight down. "
                f"The hanging end is the ~1 kV voltage maximum; keep it out of reach.")
    elif o.family == "sloper":
        take = f"One attachment at {h} ft — a {throw_word(h)} throw."
    else:
        take = f"{effort(o)[0]}, highest {h} ft."
    if not at_transformer(o):
        take = f"Fed from the roof at {o.feed[1]:.0f} ft (assumed). " + take
    if "past" in o.parcel:
        take += " Lands past the lot line."
    return (f'<article class="card">{thumb}<div class="body"><div class="hd">'
            f'{badge(lab, col)}<h3>{esc(name_of(o))}</h3></div><div class="kv">'
            f'<div><span>NEC rank</span><b>{o.nec_rank3} / {N_ALL}</b></div>'
            f'<div><span>cells</span><b>{m["n_workable"]} / 75</b></div>'
            f'<div><span>dBi</span><b>{sg(m["mean_power_dBi"])}</b></div>'
            f'<div><span>worst</span><b>{sg(m["worst_dBi"], "+.1f")}</b></div>'
            f'<div><span>40+20</span><b>{m2["n_workable"]} / 50</b></div>'
            f'<div><span>was</span><b>#{o.ana_rank3}</b></div></div>'
            f'<ul class="sched">{schedule(o)}</ul><p style="font-size:14px">{take}</p>'
            f'<div><span class="chip">canopy {CANOPY[o.key]*100:.0f}%</span> '
            f'<span class="chip{" bad" if "past" in o.parcel else ""}">'
            f'{esc(o.parcel)}</span></div></div></article>')


def heat_table(opts, labels_cols):
    head = "".join(f'<th class="o">{badge(*labels_cols[o.key])}</th>' for o in opts)
    means = {o.key: region_means(o) for o in opts}
    rows = []
    for i, name in enumerate(S["targets"]):
        cells = []
        for o in opts:
            v = means[o.key][i]
            c, t = heat(v, "light")
            cd, td = heat(v, "dark")
            per = " / ".join(f"{b} {sg(o.nec[b][i], '+.1f')}" for b in B3)
            cells.append(f'<td class="h" style="--c:{c};--t:{t};--cd:{cd};--td:{td}" '
                         f'title="{esc(name)} · {esc(name_of(o))}: {sg(v, "+.1f")} dBi '
                         f'({per})">{sg(v, "+.0f")}</td>')
        rows.append(f'<tr><td style="white-space:nowrap">{esc(name)}</td>'
                    f'<td class="n" style="color:var(--muted)">'
                    f'{C.TARGET_BEARINGS[name]:.0f}°</td>{"".join(cells)}</tr>')
    return (f'<div class="tbl"><table class="heat"><caption>NEC 40/20/15 m mean dBi per '
            f'region · columns match the map badges</caption><thead><tr><th>Region</th>'
            f'<th>Brg T</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def build():
    import build_deployment_guide as G

    # --- maps -----------------------------------------------------------
    top_items = items_for(NEC_TOP, [str(i) for i in range(1, len(NEC_TOP) + 1)])
    refs_out = [o for o in REFS if o not in NEC_TOP]
    ref_items = items_for(refs_out, [["NOW", "BASE", "RB", "A"][REFS.index(o)]
                                     for o in refs_out])
    map_top = map_svg(top_items + ref_items, (), crop_for(NEC_TOP + refs_out),
                      "The best wires on NEC, with what is up now and the plans", "mtop")
    col_top = {o.key: (lab, col) for lab, o, col, _ in top_items + ref_items}

    lin_items = items_for(LINEUP_TX, [f"L{i}" for i in range(1, len(LINEUP_TX) + 1)])
    map_lin = map_svg(lin_items, (), crop_for(LINEUP_TX),
                      "Your transformer-fed lineup, re-ranked by NEC", "mlin")

    roof_maps = []
    for title, group, pre in (("Slopers", ROOF_SL, "S"), ("Inverted-Ls", ROOF_L, "L"),
                              ("Inverted-Vs", ROOF_V, "V")):
        if not group:
            continue
        its = items_for(group, [f"R{pre}{i}" for i in range(1, len(group) + 1)])
        mid = f"mroof{pre}"
        roof_maps.append((title, its, map_svg(its, (), crop_for(group),
                                              f"Roof-fed {title.lower()}", mid), mid))

    w2_items = items_for(WIN2, [chr(ord("A") + i) for i in range(len(WIN2))])
    map_w2 = map_svg(w2_items, [o for o in REFS if o not in WIN2],
                     crop_for(WIN2 + REFS), "Best wires for 40 and 20 m on NEC", "mw2")

    # --- facts ----------------------------------------------------------
    top = WIRES[0]
    top_nonL = next(o for o in WIRES if not is_L(o))
    easy = next(o for o in WIRES if hi(o) <= 55)
    easy_lot = next((o for o in WIRES if hi(o) <= 55 and o.parcel.startswith("on the lot")
                     and not is_L(o)), None)
    rp, fa, cur, base = (get("RB-POST20"), get("F10-A"), get("CURRENT"), get("BASE"))
    best_L = next(o for o in WIRES if is_L(o))
    ag = {a["model"]: a for a in S["agreement"]}
    allag = ag["all"]
    movers = sorted(LINEUP_TX + ROOF_KEPT, key=lambda o: o.ana_rank3 - o.nec_rank3)
    faller, riser = movers[0], movers[-1]
    pat = {p["band"]: p for p in V["pattern"]}

    def best_where(pred):
        return next((o for o in WIRES if pred(o)), None)

    tx = {"sloper": best_where(lambda o: o.family == "sloper" and at_transformer(o)
                               and o.feed[1] == 10),
          "inverted-V": best_where(lambda o: o.family == "inverted-V" and at_transformer(o)
                                   and o.feed[1] == 10),
          "inverted-L": best_where(lambda o: is_L(o) and at_transformer(o))}
    rf = {"sloper": best_where(lambda o: o.family == "sloper" and not at_transformer(o)
                               and "DOWN" not in o.label),
          "inverted-V": best_where(lambda o: o.family == "inverted-V" and not at_transformer(o)),
          "inverted-L": best_where(lambda o: is_L(o) and not at_transformer(o))}
    down = ROOF_DOWN or best_where(lambda o: "DOWN" in o.label)

    def four(o):
        if o is None:
            return '<td class="n">—</td>' * 4
        return (f'<td class="n"><b>{o.nec3["n_workable"]}</b> / 75 (#{o.nec_rank3})</td>'
                f'<td class="n">{sg(o.nec3["mean_power_dBi"])}</td>'
                f'<td class="n">{sg(o.nec3["worst_dBi"], "+.1f")}</td>'
                f'<td class="n">{hi(o)} ft</td>')

    roof_cmp = "".join(
        f'<tr><td class="nm">Best {fam}</td>{four(tx[fam])}{four(rf[fam])}<td class="n">'
        + (f'<b>{rf[fam].nec3["n_workable"] - tx[fam].nec3["n_workable"]:+d}</b>'
           if tx[fam] and rf[fam] else "—") + '</td></tr>'
        for fam in ("sloper", "inverted-V", "inverted-L"))
    roof_cmp += (f'<tr><td class="nm">Best sloping <em>down</em></td>{four(None)}'
                 f'{four(down)}<td class="n">—</td></tr>')

    # --- tables ---------------------------------------------------------
    listed_rows = []
    lin_col = {o.key: (lab, col) for lab, o, col, _ in lin_items}
    roof_col = {o.key: (lab, col) for _, its, _, _ in roof_maps for lab, o, col, _ in its}
    for o in sorted(LISTED, key=lambda o: o.nec_rank3):
        lab, col = (col_top.get(o.key) or lin_col.get(o.key) or roof_col.get(o.key)
                    or ("", COL[group_of(o)]))
        listed_rows.append(score_row(o, lab, col,
                                     "mtop" if o.key in col_top else
                                     "mlin" if o.key in lin_col else ""))

    band_rows = "".join(
        f'<tr><td class="nm">{esc(name_of(o))}</td>'
        + "".join(f'<td class="n">{sg(o.nec_band[b]["mean_power_dBi"])} '
                  f'<span style="color:var(--muted)">({o.nec_band[b]["n_workable"]})</span>'
                  f'</td>' for b in C.BAND_KEYS) + '</tr>'
        for o in sorted(LISTED, key=lambda o: o.nec_rank3))

    all_rows = "".join(
        f'<tr><td class="n">{o.nec_rank3}</td><td class="nm">{esc(name_of(o))}</td>'
        f'<td>{esc(o.family)}</td><td class="n">{o.feed[1]:.0f} ft'
        f'{"" if at_transformer(o) else " roof"}</td>'
        f'<td class="n"><b>{o.nec3["n_workable"]}</b></td>'
        f'<td class="n">{sg(o.nec3["mean_power_dBi"])}</td>'
        f'<td class="n">{sg(o.nec3["worst_dBi"], "+.1f")}</td>'
        f'<td class="n">{o.nec_rank2} · {o.nec2["n_workable"]}</td>'
        f'<td class="n">{o.ana_rank3} · {o.ana3["n_workable"]}</td>'
        f'<td class="n">{move(o)}</td><td class="n">{hi(o)} ft</td>'
        f'<td>{esc(o.parcel)}</td></tr>' for o in WIRES)

    w2_rows = "".join(
        f'<tr tabindex="0" data-hl="{o.key}" data-map="mw2"'
        f'{"" if o in WIN2 else " class=\"ref\""}><td class="nm">'
        + (badge(*next((lab, col) for lab, x, col, _ in w2_items if x is o))
           if o in WIN2 else "") + f'{esc(name_of(o))}</td>'
        f'<td class="n"><b>{o.nec_rank2}</b></td>'
        f'<td class="n"><b>{o.nec2["n_workable"]}</b> / 50</td>'
        f'<td class="n">{sg(o.nec2["mean_power_dBi"])}</td>'
        f'<td class="n">{sg(o.nec2["worst_dBi"], "+.1f")}</td>'
        + "".join(f'<td class="n">{sg(o.nec_band[b]["mean_power_dBi"])} '
                  f'<span style="color:var(--muted)">({o.nec_band[b]["n_workable"]})</span>'
                  f'</td>' for b in B2)
        + f'<td class="n">{o.nec_rank3}</td><td class="n">{o.ana_rank2} {move(o, "2")}</td>'
        f'<td class="n">{hi(o)} ft</td><td>{esc(o.parcel)}</td></tr>'
        for o in sorted(uniq(WIN2 + REFS), key=lambda o: o.nec_rank2))

    ag_rows = "".join(
        f'<tr><td class="nm">{esc(a["model"])}</td><td class="n">{a["wires"]}</td>'
        f'<td class="n">{a["corr"]:.2f}</td>'
        f'<td class="n">{sg(a["mean_nec_minus_analytic_dB"], "+.1f")} dB</td>'
        f'<td class="n">{a["mean_abs_diff_dB"]:.1f} dB</td>'
        f'<td class="n">{a["workable_agreement"]*100:.0f}%</td></tr>'
        for a in S["agreement"])
    pat_rows = "".join(
        f'<tr><td class="n">{p["band"]}</td><td class="n">{p["nec_lobe_deg"]:.0f}°</td>'
        f'<td class="n">{p["section3_lobe_deg"]}°</td><td class="n">{p["end_fed_lobe_deg"]}°</td>'
        f'<td class="n">{p["arrl_lobe_deg"]}°</td>'
        f'<td class="n">{float(p["shape_corr_section3"]):.2f}</td>'
        f'<td class="n"><b>{float(p["shape_corr_end_fed"]):.2f}</b></td></tr>'
        for p in V["pattern"])
    bm = V["benchmarks"]
    bench_rows = (
        f'<tr><td>Half-wave dipole resonance</td><td class="n">'
        f'{bm["dipole"]["resonance"]["length_lambda"]} λ, {bm["dipole"]["resonance"]["R_ohm"]} Ω'
        f'</td><td class="n">0.47–0.49 λ, ~70 Ω</td></tr>'
        f'<tr><td>λ/2 dipole impedance</td><td class="n">{bm["dipole"]["half_wave_Z"][0]} + '
        f'j{bm["dipole"]["half_wave_Z"][1]} Ω</td><td class="n">73 + j42 Ω</td></tr>'
        f'<tr><td>Dipole gain</td><td class="n">{bm["dipole"]["gain_dBi"]} dBi</td>'
        f'<td class="n">2.15 dBi</td></tr>'
        + "".join(f'<tr><td>Take-off over perfect ground, h = {r["h_lambda"]} λ</td>'
                  f'<td class="n">{r["nec_elev"]}°</td><td class="n">{r["section4_elev"]}°</td>'
                  f'</tr>' for r in bm["takeoff_perfect_ground"])
        + f'<tr><td>80 m resonance with 1 m counterpoise</td><td class="n">'
        f'{V["resonances"]["with_counterpoise"]["80m"]} MHz</td><td class="n">3.6056 MHz '
        f'measured on your antenna</td></tr>')
    sens_rows = "".join(
        f'<tr><td>{esc(r["variant"])}</td><td class="n">{r["rank_spearman"]:.2f}</td>'
        f'<td class="n">{r["cell_mean_abs_dB"]:.2f} dB</td><td class="n">'
        + (f'{r["workable_agreement"]*100:.0f}%' if r["workable_agreement"] is not None else "—")
        + '</td></tr>' for r in V["sensitivity"]["rows"])

    top_col = {o.key: (lab, col) for lab, o, col, _ in top_items + ref_items}
    cards_html = "".join(card(lab, o, col, dash, NEC_TOP + refs_out)
                         for lab, o, col, dash in top_items + ref_items)
    css = G.CSS + EXTRA_CSS + HEAT_CSS

    roof_html = "".join(
        f'<div><h3 style="margin:0 0 8px">{title}</h3><figure>{svg}</figure>'
        f'{legend(its, mid)}</div>' for title, its, svg, mid in roof_maps)

    word = lambda a, b: ("better" if b > a else "worse" if b < a else "tied")  # noqa: E731

    return f"""<title>Every Wire on One Lot</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{css}</style>
{ortho_defs()}
<div class="wrap">

<header class="mast">
  <div class="eyebrow">Comparison · JYR8010 EFHW · CN97ap · ranked by NEC-2</div>
  <h1>Every wire<br>on one lot</h1>
  <p class="lede">All {N_ALL} distinct wires this study has ever scored — your lineup, the
  roof feeds, and a fresh search — re-scored by a full NEC-2 antenna simulation instead of the
  study's shortcut formulas, and re-ranked. The simulation found a formula error that had been
  steering every earlier ranking.</p>
  <div class="meta">
    <span>Wires scored <b>{N_ALL}</b></span>
    <span>Engine <b>NEC-2 · PyNEC 2.3.4</b></span>
    <span>Ground <b>average, ε 13, 5 mS/m</b></span>
    <span>Workable <b>≥ {THR:+.1f} dBi</b></span>
    <span>Imagery <b>King County 2025</b></span>
  </div>
</header>

<section>
  <div class="sec-head">
    <div class="eyebrow">Model check · read this first</div>
    <h2>The study's pattern formula was wrong on four bands</h2>
  </div>
  <p>NEC-2 solves for the actual current on the wire and computes the field from it — no
  formula. It reproduces the textbook where the textbook is known (dipole impedance and gain,
  take-off angles to 0.2°) and puts your antenna's 80 m resonance within 1.2% of what you
  measured. Checked against it, the study's long-wire formula is the <b>centre-fed</b> pattern,
  and this antenna is <b>end-fed</b>. On 40, 20, 15 and 10 m that puts every lobe in the
  wrong place.</p>
  <div class="tbl"><table>
    <caption>Main-lobe angle from the wire, free space · and how closely each formula's whole
    pattern matches NEC</caption>
    <thead><tr><th>Band</th><th>NEC-2</th><th>Study formula</th><th>End-fed formula</th>
      <th>ARRL</th><th>Match · study</th><th>Match · end-fed</th></tr></thead>
    <tbody>{pat_rows}</tbody>
  </table></div>
  <div class="note alarm">
    <b>What that did to the rankings.</b> Every earlier ranking used the wrong lobe angles on
    three of the three bands it aggregated. Across all {allag["wires"]} wires the old and NEC
    rankings correlate at only <b>ρ = {S["rank_corr"]["3band"]:.2f}</b> on 40/20/15 m and
    {S["rank_corr"]["40+20"]:.2f} on 40/20 m, and the old and new scores for individual
    band-and-region cells correlate at {allag["corr"]:.2f}, agreeing on "workable or not"
    {allag["workable_agreement"]*100:.0f}% of the time. <b>Treat every ranking from before
    today as superseded.</b>
  </div>
  <div class="lay">
    <figure>{scatter_svg()}<figcaption>One dot per wire. On the diagonal, the old model
    and NEC agree; above it, NEC scores the wire higher. Colour is the shortcut model that
    scored it before. Hover a dot for its old and new rank.
    <div class="keyrow" style="margin-top:8px"><span><i style="background:#d95926"></i>bent-wire
    model</span><span><i style="background:#2a78d6"></i>slant model</span><span><i
    style="background:#1baf7a"></i>hybrid L model</span></div></figcaption></figure>
    <div class="tbl"><table>
      <caption>Old models against NEC, every cell</caption>
      <thead><tr><th>Model</th><th>Wires</th><th>Corr</th><th>NEC − old</th><th>Avg gap</th>
        <th>Workable agree</th></tr></thead>
      <tbody>{ag_rows}</tbody>
    </table></div>
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Overhead · NEC 40 + 20 + 15 m</div>
    <h2>The best wires on your lot, by NEC</h2>
  </div>
  <div class="lay">
    <figure>{map_top}<figcaption>The twelve best distinct wires on NEC (numbers), plus what is
    up now, your original plan and both earlier recommendations where they are not already in
    the twelve. <b>Blue</b> straight slopers, <b>orange</b> bent wires (Vs, flat-tops, the
    garden post), <b>aqua</b> inverted-Ls with a ring where the wire hangs down, <b>white</b>
    what is up now. White square = roof feed. Point at a name to isolate its wire.
    </figcaption></figure>
    {legend(top_items + ref_items, "mtop")}
  </div>
  <div class="note">
    <b>The top of the list.</b> #1 is {esc(name_of(top))}: {top.nec3["n_workable"]} / 75 cells,
    {sg(top.nec3["mean_power_dBi"])} dBi, highest attachment {hi(top)} ft
    ({throw_word(hi(top))}). It was #{top.ana_rank3} on the old model. The best that is not an
    L is {esc(name_of(top_nonL))} at #{top_nonL.nec_rank3} ({top_nonL.nec3["n_workable"]} / 75,
    {hi(top_nonL)} ft). The best that needs nothing above a 55 ft throw is
    {esc(name_of(easy))} at #{easy.nec_rank3} ({easy.nec3["n_workable"]} / 75)
    {"— " + ("and it is on the lot." if easy.parcel.startswith("on the lot") else esc(easy.parcel) + ".")}
    {("The best easy-throw, on-lot, non-L wire is " + esc(name_of(easy_lot)) + f" at #{easy_lot.nec_rank3} ({easy_lot.nec3['n_workable']} / 75).") if easy_lot and easy_lot is not easy else ""}
  </div>
  <div class="note">
    <b>The earlier recommendations on NEC.</b> RB-POST20 is #{rp.nec_rank3} ({rp.nec3["n_workable"]}
    / 75, was #{rp.ana_rank3}); F10-A is #{fa.nec_rank3} ({fa.nec3["n_workable"]} / 75, was
    #{fa.ana_rank3}); your original plan is #{base.nec_rank3}; what is up now is
    #{cur.nec_rank3} ({cur.nec3["n_workable"]} / 75, was #{cur.ana_rank3}). Inverted-Ls are now
    scored by NEC itself rather than the hybrid model: the best, {esc(name_of(best_L))}, is
    #{best_L.nec_rank3}.
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Your lineup, re-ranked</div>
    <h2>The transformer-fed list on NEC</h2>
  </div>
  <div class="lay">
    <figure>{map_lin}<figcaption>The ten wires from your first request, unchanged, with their
    NEC rank in the list. Biggest riser: {esc(name_of(riser))} ({move(riser)}). Biggest
    faller: {esc(name_of(faller))} ({move(faller)}).</figcaption></figure>
    {legend(lin_items, "mlin")}
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">From the red dot on the roof</div>
    <h2>Roof feeds: the first six plus nine more</h2>
  </div>
  <p>Feed {math.dist(S["roof_feed"][0], (0, 0))/FT:.0f} ft from the transformer on the roof,
  height <b>assumed {S["roof_feed"][1]:.0f} ft</b>. The three slopers and three Ls from last
  time are kept; <b>three more slopers, three more Ls and three inverted-Vs</b> come from the
  NEC search from that point. The white square is the roof feed.</p>
  <div class="tri">{roof_html}</div>
  <div class="tbl"><table>
    <caption>Best of each shape on NEC · transformer (10 ft) against the roof (25 ft)</caption>
    <thead><tr><th rowspan="2">Shape</th><th colspan="4">From the transformer</th>
      <th colspan="4">From the roof</th><th rowspan="2">Δ cells</th></tr>
      <tr><th>Cells (rank)</th><th>dBi</th><th>Worst</th><th>Highest</th>
      <th>Cells (rank)</th><th>dBi</th><th>Worst</th><th>Highest</th></tr></thead>
    <tbody>{roof_cmp}</tbody>
  </table></div>
  <div class="note">
    <b>Is the roof better on NEC?</b> Slopers: {word(tx["sloper"].nec3["n_workable"], rf["sloper"].nec3["n_workable"])};
    Vs: {word(tx["inverted-V"].nec3["n_workable"], rf["inverted-V"].nec3["n_workable"]) if tx["inverted-V"] and rf["inverted-V"] else "—"};
    Ls: {word(tx["inverted-L"].nec3["n_workable"], rf["inverted-L"].nec3["n_workable"]) if tx["inverted-L"] and rf["inverted-L"] else "—"}.
    Sloping <em>down</em> off the house is geometrically limited to within about 7.5° of level
    from 25 ft; its best NEC score is {down.nec3["n_workable"] if down else "—"} / 75. The
    height of 25 ft is still an assumption, and the feed end on a roof is a ~700 V point beside
    gutters and house wiring that no model here knows about.
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Scorecard</div>
    <h2>Side by side, old rank beside new</h2>
  </div>
  <p>Ranked the study's way on NEC: <b>workable cells first</b>, then regions reachable, then
  mean power. "Old" is the rank the shortcut models gave. Rows a couple of cells apart are
  effectively tied — the ranking moves noticeably if the workable threshold moves 2 dB.</p>
  <div class="tbl"><table>
    <caption>Your lineup, the roof feeds and NEC's top twelve · {len(LISTED)} wires</caption>
    {SCORE_HEAD}<tbody>{"".join(listed_rows)}</tbody>
  </table></div>
  <div class="tbl"><table>
    <caption>Every band on NEC · mean dBi (regions workable of 25)</caption>
    <thead><tr><th>Wire</th>{"".join(f"<th>{b.replace('m', ' m')}</th>" for b in C.BAND_KEYS)}</tr></thead>
    <tbody>{band_rows}</tbody>
  </table></div>
  <details class="all"><summary>All {N_ALL} wires, ranked by NEC</summary>
  <div class="tbl"><table>
    <caption>Every wire the study has scored · NEC 40+20+15 m order</caption>
    <thead><tr><th>#</th><th>Wire</th><th>Shape</th><th>Feed</th><th>Cells</th><th>dBi</th>
      <th>Worst</th><th>40+20</th><th>Old</th><th>Moved</th><th>Highest</th><th>Lot</th></tr></thead>
    <tbody>{all_rows}</tbody>
  </table></div></details>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Region by region</div>
    <h2>Where the best wires put their power</h2>
  </div>
  <p>NEC mean of 40, 20 and 15 m for each region. <b>Grey is the workable line</b>
  ({THR:+.1f} dBi on NEC's scale); blue is better, red worse. Hover for the bands.</p>
  <div class="scale" aria-hidden="true"><div class="bar"></div><div class="ticks">
    <span style="left:0%">{THR - 20:+.0f}</span><span style="left:71.4%">{THR:+.0f} workable</span>
    <span style="left:100%">{THR + 8:+.0f}</span></div></div>
  {heat_table(NEC_TOP + refs_out, top_col)}
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">One at a time</div>
    <h2>Each of the best wires on its own</h2>
  </div>
  <div class="cards">{cards_html}</div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">If only 40 m and 20 m mattered</div>
    <h2>The best wires for 40 + 20 m, by NEC</h2>
  </div>
  <div class="lay">
    <figure>{map_w2}<figcaption>Letters: the five best distinct wires on NEC 40 + 20 m, plus the
    best sloper and the best wire needing nothing above a 55 ft throw that is not an L, where
    those are not already in. Earlier recommendations faint.</figcaption></figure>
    {legend(w2_items, "mw2", "2")}
  </div>
  <div class="tbl"><table>
    <caption>NEC 40 + 20 m · winners and the earlier recommendations</caption>
    <thead><tr><th>Wire</th><th>Rank</th><th>Cells</th><th>dBi</th><th>Worst</th><th>40 m</th>
      <th>20 m</th><th>3-band rank</th><th>Old rank</th><th>Highest</th><th>Lot</th></tr></thead>
    <tbody>{w2_rows}</tbody>
  </table></div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Before you believe a row</div>
    <h2>How far to trust NEC here</h2>
  </div>
  <div class="tri">
    <div class="tbl"><table><caption>Engine against textbook</caption>
      <thead><tr><th>Check</th><th>NEC</th><th>Expected</th></tr></thead>
      <tbody>{bench_rows}</tbody></table></div>
    <div class="tbl"><table><caption>How much NEC's own choices move its ranking</caption>
      <thead><tr><th>Change</th><th>Rank ρ</th><th>Cell change</th><th>Workable agree</th></tr></thead>
      <tbody>{sens_rows}</tbody></table></div>
  </div>
  <ul class="tight">
    <li><b>NEC validates the physics, not the site.</b> It knows nothing of the trees, the house,
      its wiring, or the real transformer; a 1 m counterpoise stands in for the feed.</li>
    <li><b>The workable line matters more than any modelling choice.</b> Moving it ±2 dB drops
      the rank correlation to about 0.8. Rows within a few cells are ties.</li>
    <li><b>Terrain is still the study's arrival-angle adjustment,</b> not a terrain model.</li>
    <li><b>Heights of trees and the roof are operator-supplied or assumed.</b></li>
    <li><b>Nothing here says whether a band is open.</b></li>
    <li><b>The one measurement that settles it</b> is still a NanoVNA sweep and an on-air A/B.</li>
  </ul>
</section>

<footer>
  <p><b>This is simulation, not measurement.</b> Scores from tools/nec_search.py (NEC-2 via
  PyNEC), validation from tools/nec_validate.py; page from tools/build_nec_page.py.</p>
  <p>Aerial imagery: King County GIS 2025 orthomosaic (EagleView). Parcel lines from King County
  KingCo_Parcels. Canopy texture-classified from the same photograph.</p>
</footer>
</div>
{JS}
""", (top_items + ref_items, [x for _, x, _, _ in roof_maps], w2_items)


if __name__ == "__main__":
    html, (top_items, roof_item_groups, w2_items) = build()
    tops = [o for _, o, _, _ in top_items]
    render_jpeg(top_items, (), crop_for(tops), "Best wires on NEC-2 · 40 + 20 + 15 m",
                jpeg_rows(top_items), os.path.join(IMGDIR, "nec_top.jpg"))
    roof_items = [it for g in roof_item_groups for it in g]
    render_jpeg(roof_items, (), crop_for([o for _, o, _, _ in roof_items]),
                "Roof feeds on NEC-2 · 25 ft assumed", jpeg_rows(roof_items),
                os.path.join(IMGDIR, "nec_roof.jpg"))
    render_jpeg(w2_items, REFS, crop_for([o for _, o, _, _ in w2_items] + REFS),
                "Best for 40 + 20 m on NEC-2", jpeg_rows(w2_items, "2"),
                os.path.join(IMGDIR, "nec_40_20.jpg"))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "nec-page.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print(f"wrote {os.path.normpath(out)} ({len(html)/1024:.0f} KB)")
