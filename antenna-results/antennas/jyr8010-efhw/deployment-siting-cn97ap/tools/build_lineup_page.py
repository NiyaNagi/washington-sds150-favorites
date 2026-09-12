#!/usr/bin/env python3
"""Ten wires on one lot: the operator's lineup drawn on the aerial and compared.

Asked 2026-09-12. The lineup is what is up now (CURRENT), the original plan
(BASE), the two recommendations (RB-POST20, F10-A), the top three slopers and
the top three inverted-V-or-L deployments from tools/topology_search.py. A
second map re-ranks everything on 40 m + 20 m alone.

Every number is computed here from the same code compare_options.py and
topology_search.py use, so the page cannot drift from the tools. Also writes
two annotated JPEGs to ../imagery/.

Requires Pillow. Run from the repository root:

    python3 .../tools/build_lineup_page.py [out.html]
"""

import base64
import io
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont            # noqa: E402
import compare_options as C                            # noqa: E402
import topology_search as T                            # noqa: E402
import canopy_from_ortho as K                          # noqa: E402
from site_geometry import polar, mag                   # noqa: E402

FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, "..", "imagery")
CAP_FN, CAP_SPAN = "kc2025_close.jpg", 90.0         # centred on the feed
SIZE = 1200
PPM = SIZE / CAP_SPAN
M3, M2 = T.METRICS["3band"], T.METRICS["40+20"]

# Family colours: documented categorical slots 1-3, validated all-pairs
# (scripts/validate_palette.js) because any two wires can touch on a map.
# Reference wires (up now, original plan) stay neutral rather than taking a
# fourth slot, which would fail the all-pairs floor.
# Orange is the documented dark step: the light step sat 0.001 above the dark
# lightness band, and these colours must hold on both page themes.
FAMILY_COLOUR = {"sloper": "#2a78d6", "recommended": "#d95926",
                 "inverted-L": "#1baf7a", "inverted-V": "#1baf7a",
                 "now": "#ffffff", "plan": "#c3c2b7"}
BADGE_INK = {"#2a78d6": "#ffffff"}
DASHES = ["", "16 9", "5 7"]


def P(en):
    return (SIZE / 2 + en[0] * PPM, SIZE / 2 - en[1] * PPM)


def sig(o):
    return tuple((int(h), round(en[0] * 2) / 2, round(en[1] * 2) / 2)
                 for _, h, en in o.supports)


def unique_ranked(opts, bands):
    """Deduplicate identical wires (the search re-finds F10-G) and rank."""
    seen, out, alias = {}, [], {}
    for o in opts:
        s = sig(o)
        if s in seen:
            alias[o.key] = seen[s]
            continue
        seen[s] = o
        out.append(o)
    out.sort(key=lambda o: T.rank_key(o, bands), reverse=True)
    return out, alias


def sg(v, fmt="+.2f"):
    return format(v, fmt).replace("-", "−")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

print("running topology search ...")
RES = T.run(verbose=False)
E = RES["existing"]
LINEUP = T.lineup(RES)
BEST_V = RES["3band:vee"][0]

U3, A3 = unique_ranked(list(E.values()) + RES["3band:sloper"]
                       + RES["3band:vee"] + RES["3band:ell"], M3)
U2, A2 = unique_ranked(list(E.values()) + RES["3band:sloper"]
                       + RES["3band:vee"] + RES["3band:ell"]
                       + RES["40+20:sloper"] + RES["40+20:vee"]
                       + RES["40+20:ell"] + [RES["40+20:rb"],
                                             RES["40+20:f10a"]], M2)


def rank(o, uniq, alias):
    """Rank within a pool. A wire searched for the OTHER metric is not in the
    pool; place it by how many pooled wires beat it."""
    c = alias.get(o.key, o)
    if c in uniq:
        return uniq.index(c) + 1
    bands = M3 if uniq is U3 else M2
    k = T.rank_key(o, bands)
    return 1 + sum(1 for u in uniq if T.rank_key(u, bands) > k)


def family_of(o):
    if o.key == "CURRENT":
        return "now"
    if o.key == "BASE":
        return "plan"
    if o.key in ("RB-POST20", "F10-A") or o.key in ("W-RB20", "W-F10A"):
        return "recommended"
    return o.family


def name_of(o):
    fixed = {"CURRENT": "Up now", "BASE": "BASE · original plan",
             "RB-POST20": "RB-POST20", "F10-A": "F10-A",
             "W-RB20": "RB-POST20, post re-placed",
             "W-F10A": "F10-A, leg 2 re-aimed"}
    if o.key in fixed:
        return fixed[o.key]
    if "-" not in o.key or o.key in E:
        return o.key
    pre, rest = o.key.split("-", 1)
    kind = "".join(ch for ch in rest if ch.isalpha())
    num = rest[len(kind):]
    nm = {"SL": "Sloper", "V": "Inverted-V", "L": "Inverted-L"}[kind] + " " + num
    if pre == "W":
        nm = "40/20 " + nm
    dup = A3.get(o.key) or A2.get(o.key)
    if dup is not None and dup.key in E:
        nm += f" (= {dup.key})"
    return nm


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
    hi = max((h for h, _ in el), default=0)
    s = f"{len(throws)} throw{'s' if len(throws) != 1 else ''}"
    if posts:
        s += f" + {posts[0]} ft post"
    return s, max(throws, default=0) or hi


def throw_word(h):
    return ("easy" if h <= 55 else "hard" if h <= 90 else
            "very hard" if h <= 130 else "climb")


def confidence(o):
    if isinstance(o, T.InvertedL):
        return "hybrid model · unvalidated", "bad"
    if o.is_slant:
        return "slant model · LOW", "warn"
    return "bent-wire model · moderate", ""


def schedule(o):
    out = []
    for i, (nm, h, en) in enumerate(o.supports):
        d, b = polar(*en)
        if d < 0.01:
            out.append(f"<li>{esc(nm)} · {h} ft · at the transformer</li>")
        elif i and math.dist(en, o.supports[i - 1][2]) < 0.01:
            out.append(f"<li>then hangs straight down to {h} ft</li>")
        else:
            out.append(f"<li>{esc(nm)} · <b>{h} ft</b> · {d/FT:.0f} ft @ "
                       f"<b>{mag(b):.0f}°M</b></li>")
    return "".join(out)


def region_means(o, bands):
    nets = {b: C.band_nets(o, b) for b in bands}
    return [10 * math.log10(sum(10 ** ((nets[b][i] + C.BAND[b]["peak_dBi"]) / 10)
                                for b in bands) / len(bands))
            for i in range(len(C.TARGETS))]


def canopy_all(opts):
    im, ppm, centre = K.load("close")
    mask = K.canopy_mask(im)
    out = {}
    for o in opts:
        prof = []
        for i in range(len(o.supports) - 1):
            a, b = o.supports[i][2], o.supports[i + 1][2]
            if math.dist(a, b) > 0.01:
                prof += K.profile_along(mask, ppm, centre, im.size, a, b)
        out[o.key] = sum(v for _, v in prof) / max(len(prof), 1)
    return out


def _near(a, b, tol=6.0):
    """Same design within a few metres at both the first support and the end.
    The first build showed five 'winners' that were two Ls drawn twice."""
    return (math.dist(a.supports[1][2], b.supports[1][2]) < tol
            and math.dist(a.supports[-1][2], b.supports[-1][2]) < tol)


# 40+20 m winners: the three best DISTINCT wires, then the best sloper and the
# best wire needing nothing above a 55 ft throw that is not an L.
WIN = []
for _o in U2:
    if not any(_near(_o, w) for w in WIN):
        WIN.append(_o)
    if len(WIN) == 3:
        break
BEST_SL2 = next(o for o in U2 if o.family == "sloper")
EASY = next(o for o in U2 if effort(o)[1] <= 55
            and not isinstance(o, T.InvertedL))
for _o in (BEST_SL2, EASY):
    if _o not in WIN and not any(_near(_o, w) for w in WIN):
        WIN.append(_o)

print("classifying canopy ...")
CANOPY = canopy_all({o.key: o for o in LINEUP + WIN + [BEST_V]}.values())


# --------------------------------------------------------------------------
# Heat-map colour: diverging about the -5 dBi workable threshold, OKLab mix
# between the documented blue and red poles and the neutral grey midpoint.
# --------------------------------------------------------------------------

def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _oklab(hexs):
    r, g, b = (_lin(int(hexs[i:i + 2], 16)) for i in (1, 3, 5))
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
    rgb = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
           -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
           -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
    out = ""
    for x in rgb:
        x = min(1.0, max(0.0, x))
        v = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
        out += f"{round(v * 255):02x}"
    return "#" + out


def _lum(hexs):
    r, g, b = (_lin(int(hexs[i:i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ink(bg):
    lb = _lum(bg)
    dark = (lb + 0.05) / (_lum("#0b0b0b") + 0.05)
    light = (1.05) / (lb + 0.05)
    return "#0b0b0b" if dark >= light else "#ffffff"


HEAT = {"light": ("#e34948", "#f0efec", "#256abf"),
        "dark": ("#e66767", "#383835", "#3987e5")}
THRESH, GOOD_SPAN, POOR_SPAN = C.WORKABLE_dBi, 8.0, 20.0


def heat(v, mode):
    poor, mid, good = HEAT[mode]
    if v >= THRESH:
        t, pole = min((v - THRESH) / GOOD_SPAN, 1.0), good
    else:
        t, pole = min((THRESH - v) / POOR_SPAN, 1.0), poor
    a, b = _oklab(mid), _oklab(pole)
    c = _hex(*(a[i] + (b[i] - a[i]) * t for i in range(3)))
    return c, _ink(c)


# --------------------------------------------------------------------------
# Maps (SVG) - the ortho is embedded once and <use>d by every map
# --------------------------------------------------------------------------

def ortho_defs():
    im = Image.open(os.path.join(IMGDIR, CAP_FN)).convert("RGB")
    im = im.resize((SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    data = base64.b64encode(buf.getvalue()).decode()
    print(f"  ortho {len(buf.getvalue())/1024:.0f} KB")
    return (f'<svg width="0" height="0" style="position:absolute" '
            f'aria-hidden="true"><defs><image id="ortho" x="0" y="0" '
            f'width="{SIZE}" height="{SIZE}" '
            f'href="data:image/jpeg;base64,{data}"/></defs></svg>')


def crop_for(opts, margin_m=7.0, min_m=26.0):
    pts = [P(en) for o in opts for _, _, en in o.supports]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    side = max(x1 - x0, y1 - y0, min_m * PPM) + 2 * margin_m * PPM
    side = min(side, SIZE)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x = min(max(cx - side / 2, 0), SIZE - side)
    y = min(max(cy - side / 2, 0), SIZE - side)
    return x, y, side, side


def far_end(o):
    """Last support that is a distinct point, and the one before it."""
    pts = [en for _, _, en in o.supports]
    dedup = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, dedup[-1]) > 0.01:
            dedup.append(p)
    return dedup[-1], dedup[-2]


def items_for(opts, labels):
    fam_count, out = {}, []
    for lab, o in zip(labels, opts):
        fam = family_of(o)
        i = fam_count.get(fam, 0)
        fam_count[fam] = i + 1
        col = FAMILY_COLOUR.get(fam, "#1baf7a")
        dash = "" if fam in ("now", "plan") and fam == "now" else \
            ("12 8" if fam == "plan" else DASHES[i % 3])
        out.append((lab, o, col, dash))
    return out


def map_svg(items, faded=(), crop=None, aria="", map_id=None, small=False):
    x, y, w, h = crop
    s = w / 700
    o = [f'<svg viewBox="{x:.1f} {y:.1f} {w:.1f} {h:.1f}" '
         f'xmlns="http://www.w3.org/2000/svg" class="plan"'
         + (f' id="{map_id}"' if map_id else "")
         + f' role="img" aria-label="{esc(aria)}">',
         '<use href="#ortho"/>',
         f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
         f'fill="#000" opacity=".12"/>']
    se, sw, ne = P((46.9, -32.0)), P((-69.9, -6.8)), P((53.5, 99.2))
    o.append(f'<polyline points="{sw[0]:.1f},{sw[1]:.1f} {se[0]:.1f},'
             f'{se[1]:.1f} {ne[0]:.1f},{ne[1]:.1f}" fill="none" stroke="#fff" '
             f'stroke-width="{2.2*s:.2f}" stroke-dasharray="{9*s:.1f} {6*s:.1f}" '
             f'opacity=".8"/>')
    rb = " ".join(f"{P(p)[0]:.1f},{P(p)[1]:.1f}" for p in C.RED_BOX)
    o.append(f'<polygon points="{rb}" fill="none" stroke="#ff4b4b" '
             f'stroke-width="{2*s:.2f}" opacity=".7"/>')
    for fo in faded:
        pts = " ".join(f"{P(en)[0]:.1f},{P(en)[1]:.1f}" for _, _, en in fo.supports)
        o.append(f'<polyline points="{pts}" fill="none" stroke="#fff" '
                 f'stroke-width="{2*s:.2f}" opacity=".38" '
                 f'stroke-linejoin="round"/>')

    placed = []
    for lab, ob, col, dash in items:
        pts = " ".join(f"{P(en)[0]:.1f},{P(en)[1]:.1f}" for _, _, en in ob.supports)
        g = [f'<g class="wire" data-k="{ob.key}">',
             f'<polyline points="{pts}" fill="none" stroke="#0b0d0f" '
             f'stroke-width="{9*s:.2f}" opacity=".6" stroke-linejoin="round"/>',
             f'<polyline points="{pts}" fill="none" stroke="{col}" '
             f'stroke-width="{4.6*s:.2f}" stroke-linejoin="round" '
             f'stroke-linecap="round"'
             + (f' stroke-dasharray="{" ".join(f"{float(v)*s:.1f}" for v in dash.split())}"'
                if dash else "") + '/>']
        for i, (nm, hgt, en) in enumerate(ob.supports[1:], 1):
            px, py = P(en)
            if math.dist(en, ob.supports[i - 1][2]) < 0.01:
                g.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{12*s:.1f}" '
                         f'fill="none" stroke="#0b0d0f" stroke-width="{5*s:.1f}"/>'
                         f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{12*s:.1f}" '
                         f'fill="none" stroke="{col}" stroke-width="{2.6*s:.1f}"/>')
                vert = (ob.supports[i - 1][1] - hgt)
                g.append(f'<text x="{px + 16*s:.1f}" y="{py + 5*s:.1f}" '
                         f'class="lp" style="font-size:{13*s:.1f}px" '
                         f'filter="url(#sh)">↓{vert} ft</text>')
            else:
                g.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{4.5*s:.1f}" '
                         f'fill="{col}" stroke="#0b0d0f" stroke-width="{2*s:.1f}"/>')
        end, prev = far_end(ob)
        ex, ey = P(end)
        pxp, pyp = P(prev)
        dx, dy = ex - pxp, ey - pyp
        L = math.hypot(dx, dy) or 1
        bx, by = ex + dx / L * 20 * s, ey + dy / L * 20 * s
        for _ in range(8):
            clash = [q for q in placed if math.dist(q, (bx, by)) < 27 * s]
            if not clash:
                break
            bx, by = bx - dy / L * 26 * s, by + dx / L * 26 * s
        placed.append((bx, by))
        g.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{12.5*s:.1f}" '
                 f'fill="{col}" stroke="#0b0d0f" stroke-width="{2.5*s:.1f}"/>'
                 f'<text x="{bx:.1f}" y="{by + 4.6*s:.1f}" text-anchor="middle" '
                 f'font-family="IBM Plex Mono, ui-monospace, monospace" '
                 f'font-weight="600" font-size="{13*s:.1f}" '
                 f'fill="{BADGE_INK.get(col, "#0b0d0f")}">{lab}</text>')
        g.append("</g>")
        o.extend(g)

    fx, fy = P((0.0, 0.0))
    o.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{7*s:.1f}" fill="#fff" '
             f'stroke="#0b0d0f" stroke-width="{3*s:.1f}"/>')
    if not small:
        o.append(f'<text x="{fx - 12*s:.1f}" y="{fy - 12*s:.1f}" class="lp" '
                 f'style="font-size:{14*s:.1f}px" text-anchor="end" filter="url(#sh)">'
                 f'transformer · 10 ft</text>')
    bar = 10 * PPM
    x0, y0 = x + 18 * s, y + h - 20 * s
    o.append(f'<g filter="url(#sh)"><line x1="{x0:.1f}" y1="{y0:.1f}" '
             f'x2="{x0 + bar:.1f}" y2="{y0:.1f}" stroke="#fff" '
             f'stroke-width="{3.5*s:.1f}"/><text x="{x0:.1f}" y="{y0 - 8*s:.1f}" '
             f'class="lp" style="font-size:{12.5*s:.1f}px">10 m · 33 ft</text>'
             f'<path d="M{x + w - 24*s:.1f} {y + 40*s:.1f} L{x + w - 24*s:.1f} '
             f'{y + 14*s:.1f} M{x + w - 31*s:.1f} {y + 23*s:.1f} L{x + w - 24*s:.1f} '
             f'{y + 13*s:.1f} L{x + w - 17*s:.1f} {y + 23*s:.1f}" fill="none" '
             f'stroke="#fff" stroke-width="{3*s:.1f}"/><text x="{x + w - 24*s:.1f}" '
             f'y="{y + 56*s:.1f}" class="lp" style="font-size:{12.5*s:.1f}px" '
             f'text-anchor="middle">N</text></g>')
    o.append('</svg>')
    return "".join(o)


# --------------------------------------------------------------------------
# Annotated JPEGs for the repo
# --------------------------------------------------------------------------

def _font(sz, bold=False):
    for fn in (("arialbd.ttf" if bold else "arial.ttf"),
               ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")):
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
        if L < 1:
            continue
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
    base = Image.open(os.path.join(IMGDIR, CAP_FN)).convert("RGB")
    base = base.resize((SIZE, SIZE), Image.LANCZOS)
    im = base.crop((int(x), int(y), int(x + w), int(y + h))).resize(
        (out_px, out_px), Image.LANCZOS)
    d = ImageDraw.Draw(im, "RGBA")

    def Q(en):
        px, py = P(en)
        return ((px - x) * k, (py - y) * k)

    se, sw, ne = Q((46.9, -32.0)), Q((-69.9, -6.8)), Q((53.5, 99.2))
    _dashed(d, [sw, se, ne], (255, 255, 255, 200), 4, (18, 12))
    for fo in faded:
        d.line([Q(en) for _, _, en in fo.supports], fill=(255, 255, 255, 110),
               width=3)
    f_badge, f_small = _font(22, True), _font(22)
    for lab, ob, col, dash in items:
        rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
        pts = [Q(en) for _, _, en in ob.supports]
        d.line(pts, fill=(11, 13, 15, 170), width=15, joint="curve")
        _dashed(d, pts, rgb + (255,), 8,
                tuple(int(float(v) * 1.6) for v in dash.split()) if dash else None)
        end, prev = far_end(ob)
        ex, ey = Q(end)
        qx, qy = Q(prev)
        L = math.hypot(ex - qx, ey - qy) or 1
        bx, by = ex + (ex - qx) / L * 34, ey + (ey - qy) / L * 34
        d.ellipse([bx - 20, by - 20, bx + 20, by + 20], fill=rgb + (255,),
                  outline=(11, 13, 15), width=4)
        ink = (255, 255, 255) if BADGE_INK.get(col) else (11, 13, 15)
        d.text((bx, by), lab, fill=ink, font=f_badge, anchor="mm")
        if isinstance(ob, T.InvertedL):
            px, py = Q(ob.supports[1][2])
            d.ellipse([px - 18, py - 18, px + 18, py + 18], outline=rgb, width=5)
    fx, fy = Q((0.0, 0.0))
    d.ellipse([fx - 11, fy - 11, fx + 11, fy + 11], fill=(255, 255, 255),
              outline=(11, 13, 15), width=4)

    # Legend BELOW the photo - laid over it, it hid the south ends of three
    # wires on the first render.
    pad, lh = 22, 34
    panel_h = pad * 2 + 44 + lh * len(rows)
    canvas = Image.new("RGB", (out_px, out_px + panel_h), (11, 13, 15))
    canvas.paste(im, (0, 0))
    im = canvas
    d = ImageDraw.Draw(im, "RGBA")
    top = out_px
    d.text((pad, top + pad), title, fill=(255, 255, 255), font=_font(28, True))
    for i, (lab, col, text) in enumerate(rows):
        yy = top + pad + 50 + i * lh
        rgb = tuple(int(col[j:j + 2], 16) for j in (1, 3, 5))
        d.ellipse([pad, yy, pad + 26, yy + 26], fill=rgb, outline=(255, 255, 255),
                  width=2)
        d.text((pad + 13, yy + 13), lab, fill=(11, 13, 15) if not
               BADGE_INK.get(col) else (255, 255, 255), font=_font(16, True),
               anchor="mm")
        d.text((pad + 40, yy + 2), text, fill=(235, 235, 230), font=f_small)
    im.save(path, quality=88)
    print("  wrote", os.path.normpath(path))


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------

EXTRA_CSS = """
.lay{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(270px,1fr);
  gap:18px;align-items:start}
@media(max-width:900px){.lay{grid-template-columns:1fr}}
.plan text.lp{font-family:var(--ff-m);fill:#fff}
.plan g.wire{transition:opacity .15s}
.plan.dim g.wire{opacity:.16}
.plan.dim g.wire.on{opacity:1}
.legend{list-style:none;margin:0;padding:6px;display:flex;flex-direction:column;
  gap:2px;background:var(--surf);border:1px solid var(--rule);border-radius:5px}
.legend li{display:grid;grid-template-columns:26px 46px minmax(0,1fr);gap:10px;
  align-items:center;padding:7px 8px;border-radius:4px}
.legend li:hover,.legend li:focus-visible{background:var(--surf2);outline:none}
.legend li:focus-visible{box-shadow:inset 0 0 0 2px var(--wire)}
.legend .nm{font-weight:600;color:var(--ink);font-size:14.5px;line-height:1.25}
.legend .sub{font-family:var(--ff-m);font-size:11.5px;color:var(--muted)}
.badge{width:24px;height:24px;border-radius:50%;display:inline-flex;
  align-items:center;justify-content:center;font-family:var(--ff-m);
  font-size:12px;font-weight:600;box-shadow:0 0 0 2px var(--ink)}
.sw{display:block;width:44px;height:0;border-top-width:5px;
  border-top-style:solid}
.chip{display:inline-block;font-family:var(--ff-m);font-size:11px;
  padding:2px 8px;border-radius:10px;border:1px solid var(--rule);
  color:var(--ink2);white-space:nowrap}
.chip.warn{border-color:var(--accent);color:var(--ink)}
.chip.bad{border-color:var(--alarm);color:var(--alarm)}
td.nm{font-weight:600;color:var(--ink);white-space:nowrap}
td .badge{margin-right:8px;vertical-align:middle;width:22px;height:22px;
  font-size:11px}
tr.ref td{color:var(--muted)}
tr[data-hl]{cursor:default}
tr[data-hl]:hover td,tr[data-hl]:focus-visible td{background:var(--surf2)}
table.heat{font-size:13px}
table.heat th,table.heat td{padding:5px 6px}
table.heat th.o{text-align:center}
table.heat td.h{font-family:var(--ff-m);text-align:center;background:var(--c);
  color:var(--t);border:2px solid var(--surf);border-radius:4px}
table.heat td.rg{white-space:nowrap}
.scale{display:flex;flex-direction:column;gap:6px;max-width:520px}
.scale .bar{height:12px;border-radius:4px;background:linear-gradient(90deg,
  var(--hp) 0%,var(--hm) 71.4%,var(--hg) 100%)}
.scale .ticks{position:relative;height:16px;font-family:var(--ff-m);
  font-size:11px;color:var(--muted)}
.scale .ticks span{position:absolute;transform:translateX(-50%)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));
  gap:16px}
.card{background:var(--surf);border:1px solid var(--rule);border-radius:5px;
  overflow:hidden;display:flex;flex-direction:column}
.card svg{display:block;width:100%;height:auto}
.card .body{padding:13px 15px 15px;display:flex;flex-direction:column;gap:9px}
.card .hd{display:flex;align-items:center;gap:10px}
.card h3{margin:0;font-size:17px}
.kv{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.kv div{background:var(--surf2);padding:6px 8px;border-radius:3px;
  display:flex;flex-direction:column;gap:1px}
.kv b{font-family:var(--ff-m);font-size:14.5px;color:var(--ink);
  font-variant-numeric:tabular-nums}
.kv span{font-family:var(--ff-m);font-size:10.5px;letter-spacing:.07em;
  text-transform:uppercase;color:var(--muted)}
ul.sched{margin:0;padding-left:17px;font-size:13.5px;color:var(--ink2);
  display:flex;flex-direction:column;gap:2px}
.card p.take{font-size:14px}
"""

HEAT_CSS = """
:root{--hp:#e34948;--hm:#f0efec;--hg:#256abf}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --hp:#e66767;--hm:#383835;--hg:#3987e5}
  :root:not([data-theme="light"]) table.heat td.h{background:var(--cd);
  color:var(--td)}}
:root[data-theme="dark"]{--hp:#e66767;--hm:#383835;--hg:#3987e5}
:root[data-theme="dark"] table.heat td.h{background:var(--cd);color:var(--td)}
"""

JS = """
<script>
document.querySelectorAll('[data-hl]').forEach(function(el){
  var map=document.getElementById(el.getAttribute('data-map'));
  if(!map)return;
  var k=el.getAttribute('data-hl');
  function on(){map.classList.add('dim');
    map.querySelectorAll('g.wire').forEach(function(g){
      g.classList.toggle('on',g.getAttribute('data-k')===k);});}
  function off(){map.classList.remove('dim');}
  el.addEventListener('mouseenter',on);el.addEventListener('mouseleave',off);
  el.addEventListener('focus',on);el.addEventListener('blur',off);
});
</script>
"""


def badge(lab, col):
    ink = BADGE_INK.get(col, "#0b0d0f")
    return (f'<span class="badge" style="background:{col};color:{ink}">'
            f'{lab}</span>')


def swatch(col, dash):
    style = "dashed" if dash and dash.split()[0] in ("16", "12") else \
        "dotted" if dash else "solid"
    return f'<span class="sw" style="border-top-color:{col};border-top-style:{style}"></span>'


def legend(items, map_id, bands, uniq, alias, cells_of):
    rows = []
    for lab, o, col, dash in items:
        m = C.aggregate_multiband(o, bands)
        rows.append(
            f'<li tabindex="0" data-hl="{o.key}" data-map="{map_id}">'
            f'{badge(lab, col)}{swatch(col, dash)}<div><div class="nm">'
            f'{esc(name_of(o))}</div><div class="sub">#{rank(o, uniq, alias)} '
            f'of {len(uniq)} · {m["n_workable"]}/{cells_of} cells · '
            f'{sg(m["mean_power_dBi"])} dBi</div></div></li>')
    return f'<ul class="legend">{"".join(rows)}</ul>'


def build():
    labels = [str(i) for i in range(1, len(LINEUP) + 1)]
    items = items_for(LINEUP, labels)
    col_of = {o.key: (lab, col, dash) for lab, o, col, dash in items}
    crop1 = crop_for(LINEUP)
    map1 = map_svg(items, (), crop1, "All ten wires on the aerial photo",
                   "map1")

    wl = [chr(ord("A") + i) for i in range(len(WIN))]
    items2 = items_for(WIN, wl)
    crop2 = crop_for(WIN + LINEUP)
    map2 = map_svg(items2, [o for o in LINEUP if o not in WIN], crop2,
                   "The best wires for 40 m and 20 m, with the lineup faded",
                   "map2")

    # --- scorecard ------------------------------------------------------
    def score_row(o, lab, col, extra_cls=""):
        m = C.aggregate_multiband(o, M3)
        m2 = C.aggregate_multiband(o, M2)
        eff, hi = effort(o)
        conf, cc = confidence(o)
        return (f'<tr tabindex="0" data-hl="{o.key}" data-map="map1"'
                f'{extra_cls}><td class="nm">{badge(lab, col) if lab else ""}'
                f'{esc(name_of(o))}</td>'
                f'<td class="n"><b>{rank(o, U3, A3)}</b></td>'
                f'<td class="n"><b>{m["n_workable"]}</b> / 75</td>'
                f'<td class="n">{m["n_regions_covered"]} / 25</td>'
                f'<td class="n">{sg(m["mean_power_dBi"])}</td>'
                f'<td class="n">{sg(m["median_dBi"], "+.1f")}</td>'
                f'<td class="n">{sg(m["worst_dBi"], "+.1f")}</td>'
                f'<td class="n">{rank(o, U2, A2)}</td>'
                f'<td class="n">{hi} ft · {throw_word(hi)}</td>'
                f'<td>{eff}</td>'
                f'<td class="n">{CANOPY[o.key]*100:.0f}%</td>'
                f'<td>{esc(T.parcel_status(o))}</td>'
                f'<td><span class="chip {cc}">{conf}</span></td></tr>')

    score_rows = "".join(score_row(o, *col_of[o.key][:2]) for o in LINEUP)
    score_rows += score_row(BEST_V, "", "#1baf7a", ' class="ref"')

    band_rows = "".join(
        f'<tr tabindex="0" data-hl="{o.key}" data-map="map1"><td class="nm">'
        f'{badge(col_of[o.key][0], col_of[o.key][1])}{esc(name_of(o))}</td>'
        + "".join(f'<td class="n">{sg(C.aggregate(o, b)["mean_power_dBi"])} '
                  f'<span style="color:var(--muted)">'
                  f'({C.aggregate(o, b)["n_workable"]})</span></td>'
                  for b in C.BAND_KEYS) + "</tr>" for o in LINEUP)

    # --- heat map -------------------------------------------------------
    means = {o.key: region_means(o, M3) for o in LINEUP}
    head = "".join(f'<th class="o">{badge(col_of[o.key][0], col_of[o.key][1])}'
                   f'</th>' for o in LINEUP)
    hrows = []
    for i, (name, lat, lon, arr) in enumerate(C.TARGETS):
        cells = []
        for o in LINEUP:
            v = means[o.key][i]
            c, t = heat(v, "light")
            cd, td = heat(v, "dark")
            per = " / ".join(
                f"{b} {sg(C.band_nets(o, b)[i] + C.BAND[b]['peak_dBi'], '+.1f')}"
                for b in M3)
            cells.append(f'<td class="h" style="--c:{c};--t:{t};--cd:{cd};'
                         f'--td:{td}" title="{esc(name)} · {esc(name_of(o))}: '
                         f'{sg(v, "+.1f")} dBi ({per})">{sg(v, "+.0f")}</td>')
        hrows.append(f'<tr><td class="rg">{esc(name)}</td><td class="n" '
                     f'style="color:var(--muted)">'
                     f'{C.TARGET_BEARINGS[name]:.0f}°</td>{"".join(cells)}</tr>')

    # --- cards ----------------------------------------------------------
    cards = []
    for lab, o, col, dash in items:
        m = C.aggregate_multiband(o, M3)
        m2 = C.aggregate_multiband(o, M2)
        eff, hi = effort(o)
        conf, cc = confidence(o)
        thumb = map_svg([(lab, o, col, dash)], [x for x in LINEUP if x is not o],
                        crop_for([o], 6.0, 30.0), name_of(o), small=True)
        fam = family_of(o)
        if o.key == "CURRENT":
            take = ("What is hung today. Straight down the lawn, which keeps it "
                    "out of the trees, but both ends point at target regions.")
        elif o.key == "BASE":
            take = "Your original three-point plan, apex at 35 ft."
        elif o.key == "RB-POST20":
            take = ("The current recommendation: one 50 ft throw, then a 20 ft "
                    "post you can walk to.")
        elif o.key == "F10-A":
            take = ("The fallback: three tree attachments, none above 50 ft.")
        elif fam == "sloper":
            dup = A3.get(o.key)
            take = (f"One attachment at {hi} ft, a {throw_word(hi)} throw."
                    + (f" The search re-found {dup.key} exactly." if dup else "")
                    + (" Lands past the lot line." if "past" in
                       T.parcel_status(o) else ""))
        else:
            take = (f"One attachment at {hi} ft, then "
                    f"{o.supports[1][1] - o.supports[2][1]} ft of wire hangs "
                    f"straight down. The hanging end is the ~1 kV voltage "
                    f"maximum; keep it out of reach. Scored on the new, "
                    f"unvalidated model.")
        cards.append(
            f'<article class="card">{thumb}<div class="body"><div class="hd">'
            f'{badge(lab, col)}<h3>{esc(name_of(o))}</h3></div>'
            f'<div class="kv"><div><span>rank</span><b>{rank(o, U3, A3)} / '
            f'{len(U3)}</b></div><div><span>cells</span><b>{m["n_workable"]} / '
            f'75</b></div><div><span>3-band</span><b>'
            f'{sg(m["mean_power_dBi"])}</b></div><div><span>worst</span><b>'
            f'{sg(m["worst_dBi"], "+.1f")}</b></div><div><span>40+20</span><b>'
            f'{m2["n_workable"]} / 50</b></div><div><span>canopy</span><b>'
            f'{CANOPY[o.key]*100:.0f}%</b></div></div>'
            f'<ul class="sched">{schedule(o)}</ul>'
            f'<p class="take">{take}</p>'
            f'<div><span class="chip {cc}">{conf}</span> '
            f'<span class="chip">{esc(T.parcel_status(o))}</span></div>'
            f'</div></article>')

    # --- 40+20 table ----------------------------------------------------
    col2 = {o.key: (lab, col) for lab, o, col, dash in items2}
    rows2_opts = sorted({o.key: o for o in WIN + LINEUP}.values(),
                        key=lambda o: rank(o, U2, A2))
    rows2 = []
    for o in rows2_opts:
        m2 = C.aggregate_multiband(o, M2)
        eff, hi = effort(o)
        conf, cc = confidence(o)
        lab, col = col2.get(o.key) or col_of[o.key][:2]
        winner = o.key in col2
        rows2.append(
            f'<tr tabindex="0" data-hl="{o.key}" data-map="map2"'
            f'{"" if winner else " class=ref"}><td class="nm">{badge(lab, col)}'
            f'{esc(name_of(o))}</td><td class="n"><b>{rank(o, U2, A2)}</b></td>'
            f'<td class="n"><b>{m2["n_workable"]}</b> / 50</td>'
            f'<td class="n">{m2["n_regions_covered"]} / 25</td>'
            f'<td class="n">{sg(m2["mean_power_dBi"])}</td>'
            f'<td class="n">{sg(m2["worst_dBi"], "+.1f")}</td>'
            + "".join(f'<td class="n">{sg(C.aggregate(o, b)["mean_power_dBi"])} '
                      f'<span style="color:var(--muted)">'
                      f'({C.aggregate(o, b)["n_workable"]})</span></td>'
                      for b in M2)
            + f'<td class="n">{rank(o, U3, A3)}</td>'
            f'<td class="n">{hi} ft</td><td>{esc(T.parcel_status(o))}</td>'
            f'<td><span class="chip {cc}">{conf}</span></td></tr>')

    # --- facts for the prose --------------------------------------------
    L1 = RES["3band:vee_or_ell"][0]
    mL1 = C.aggregate_multiband(L1, M3)
    mV = C.aggregate_multiband(BEST_V, M3)
    rp, fa, cur = E["RB-POST20"], E["F10-A"], E["CURRENT"]
    all_L = all(isinstance(o, T.InvertedL) for o in RES["3band:vee_or_ell"])
    top_non_l_3 = next(o for o in U3 if not isinstance(o, T.InvertedL))
    top_non_l_2 = next(o for o in U2 if not isinstance(o, T.InvertedL))
    wf = RES["40+20:f10a"]
    d_wf = sorted(((a - b, C.TARGETS[i][0]) for i, (a, b) in enumerate(
        zip(region_means(wf, M2), region_means(fa, M2)))), reverse=True)
    gains = ", ".join(f"{n} {sg(v, '+.1f')}" for v, n in d_wf[:3])
    losses = ", ".join(f"{n} {sg(v, '+.1f')}" for v, n in d_wf[::-1][:3])

    legend2 = legend(items2, "map2", M2, U2, A2, 50)
    css = G_CSS + EXTRA_CSS + HEAT_CSS

    return f"""<title>Ten Wires on One Lot</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{css}</style>
{ortho_defs()}
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><filter id="sh" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#000" flood-opacity=".95"/></filter></defs></svg>
<div class="wrap">

<header class="mast">
  <div class="eyebrow">Comparison · JYR8010 EFHW · CN97ap · feed at 10 ft in every line</div>
  <h1>Ten wires<br>on one lot</h1>
  <p class="lede">What is up now, your original plan, both current
  recommendations, and the best slopers and V-or-L shapes a fresh search could
  find — drawn on the 2025 King County aerial and scored the same way. Then
  the whole search again, as if only 40 m and 20 m mattered.</p>
  <div class="meta">
    <span>Distinct wires scored <b>{len(U2)}</b></span>
    <span>Three-band cells <b>75</b></span>
    <span>40 + 20 m cells <b>50</b></span>
    <span>Declination <b>+15.3°E</b></span>
    <span>Imagery <b>King County 2025</b></span>
  </div>
</header>

<section>
  <div class="sec-head">
    <div class="eyebrow">Overhead · 40 + 20 + 15 m</div>
    <h2>The lineup, on your property</h2>
  </div>
  <div class="lay">
    <figure>{map1}<figcaption><b>Colour is the family</b>: orange for the two
    recommendations, blue for slopers, aqua for inverted-Ls, white for what is
    up now and grey dashes for the original plan. Solid, dashed and dotted
    lines tell members of one family apart; the numbered badge sits past each
    wire's far end. A <b>ring with ↓</b> marks where an L's wire hangs straight
    down. White dashes are the lot's south and east lines; the red outline is
    your staked strip. Point at a name to isolate its wire.</figcaption></figure>
    {legend(items, "map1", M3, U3, A3, 75)}
  </div>
  <div class="note alarm">
    <b>{"All three V-or-L picks are inverted-Ls" if all_L else "The inverted-Ls lead"}
    — and they are the least trustworthy numbers in this whole study.</b>
    The best, {esc(name_of(L1))}, scores {mL1["n_workable"]} / 75 cells and ranks
    first of {len(U3)}. But nothing in the study could score an L before today:
    both of its legs are scored on the slant model, which has already been
    wrong once, and they are combined as a union that ignores how the two legs
    interact — at a 90° bend, which the study's own filter classes as
    overstated. The best inverted-V, scored on the steadier bent-wire model,
    manages {mV["n_workable"]} / 75 ({sg(mV["mean_power_dBi"])} dBi). Treat the
    L result as <b>a reason to run NEC on one L</b>, not as a reason to hang
    one. The best non-L in the study remains {esc(name_of(top_non_l_3))} at
    {C.aggregate_multiband(top_non_l_3, M3)["n_workable"]} / 75.
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Scorecard</div>
    <h2>Side by side</h2>
  </div>
  <p>Ranked the study's way: <b>workable band-and-region cells first</b>, then
  regions reachable, then mean power. Rows that tie on cells are not ordered
  meaningfully. The last row is the best inverted-V, for reference — it is not
  on the map.</p>
  <div class="tbl"><table>
    <caption>40 + 20 + 15 m · 25 regions · {len(U3)} distinct wires ranked</caption>
    <thead><tr><th>Wire</th><th>Rank</th><th>Cells</th><th>Regions</th>
      <th>dBi</th><th>Median</th><th>Worst</th><th>40+20 rank</th>
      <th>Highest</th><th>Effort</th><th>Canopy</th><th>Lot</th>
      <th>Model</th></tr></thead>
    <tbody>{score_rows}</tbody>
  </table></div>
  <div class="tbl"><table>
    <caption>Every band · mean dBi (regions workable of 25)</caption>
    <thead><tr><th>Wire</th>{"".join(f"<th>{b.replace('m', ' m')}</th>" for b in C.BAND_KEYS)}</tr></thead>
    <tbody>{band_rows}</tbody>
  </table></div>
  <p>Up now ranks <b>{rank(cur, U3, A3)} of {len(U3)}</b>. RB-POST20 and F10-A
  rank {rank(rp, U3, A3)} and {rank(fa, U3, A3)}: they sit behind the slopers
  on cells because a single high wire reaches more regions, and ahead of them
  on everything else — a worst region of {sg(C.aggregate_multiband(rp, M3)["worst_dBi"], "+.0f")}
  dBi against the slopers' {sg(min(C.aggregate_multiband(o, M3)["worst_dBi"] for o in RES["3band:sloper"]), "+.0f")},
  and a 50 ft throw against 87–107 ft.</p>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Region by region</div>
    <h2>Where each wire puts its power</h2>
  </div>
  <p>Mean of 40, 20 and 15 m for each region, in dBi. <b>Grey is the
  −5 dBi line</b> the study counts as workable; blue is better, red is worse.
  Hover a cell for the three bands separately.</p>
  <div class="scale" aria-hidden="true"><div class="bar"></div>
    <div class="ticks"><span style="left:0%">−25</span>
    <span style="left:35.7%">−15</span><span style="left:71.4%">−5 workable</span>
    <span style="left:100%">+3</span></div></div>
  <div class="tbl"><table class="heat">
    <caption>3-band mean dBi per region · columns match the map badges</caption>
    <thead><tr><th>Region</th><th>Brg T</th>{head}</tr></thead>
    <tbody>{"".join(hrows)}</tbody>
  </table></div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">One at a time</div>
    <h2>Each wire on its own</h2>
  </div>
  <p>Same aerial, cropped to each wire, with the rest of the lineup faint
  behind it. Bearings are magnetic — set your compass to those.</p>
  <div class="cards">{"".join(cards)}</div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">If only 40 m and 20 m mattered</div>
    <h2>The best wires for 40 + 20 m</h2>
  </div>
  <p>Same ranking method with 15 m dropped: 50 cells instead of 75. Every
  family was searched again for this measure — slopers, Vs and Ls — and
  RB-POST20's post and F10-A's second leg were re-placed for it too. Letters
  mark the winners; the lineup is drawn faint behind them.</p>
  <div class="lay">
    <figure>{map2}<figcaption>In colour: the <b>three best distinct wires</b>
    on 40 + 20 m (near-identical copies dropped), the <b>best sloper</b>, and
    {esc(name_of(EASY))} — the best wire that needs nothing above a 55 ft
    throw and is not an L. Family colours as above; the lineup is faint
    behind.</figcaption>
    </figure>
    {legend2}
  </div>
  <div class="tbl"><table>
    <caption>40 + 20 m ranking · {len(U2)} distinct wires · faint rows are the lineup</caption>
    <thead><tr><th>Wire</th><th>Rank</th><th>Cells</th><th>Regions</th>
      <th>dBi</th><th>Worst</th><th>40 m</th><th>20 m</th><th>3-band rank</th>
      <th>Highest</th><th>Lot</th><th>Model</th></tr></thead>
    <tbody>{"".join(rows2)}</tbody>
  </table></div>
  <div class="note">
    <b>What changes when 15 m drops out.</b> The recommendations slide:
    RB-POST20 goes from {rank(rp, U3, A3)} to {rank(rp, U2, A2)}, F10-A from
    {rank(fa, U3, A3)} to {rank(fa, U2, A2)}. Their strength was 15 m. The
    best non-L on 40 + 20 m is {esc(name_of(top_non_l_2))}
    ({C.aggregate_multiband(top_non_l_2, M2)["n_workable"]} / 50, a
    {effort(top_non_l_2)[1]} ft attachment). Up now stays near the bottom at
    {rank(cur, U2, A2)} of {len(U2)}.
  </div>
  <div class="note">
    <b>F10-A with its second leg re-aimed</b> to
    {mag(wf.segments[1][2]):.0f}°M is the best thing on 40 + 20 m that is
    built entirely from 50 ft throws. The study already rejected that re-aim
    once, on three bands, because it gives up the south-west. On 40 + 20 m the
    trade against F10-A is: better toward {gains}; worse toward {losses}.
  </div>
</section>

<section>
  <div class="sec-head">
    <div class="eyebrow">Before you believe a row</div>
    <h2>How far to trust each number</h2>
  </div>
  <ul class="tight">
    <li><b>Bent-wire model</b> (RB-POST20, F10-A, BASE, inverted-Vs) —
      moderate. Lobe positions are sound; the union of legs overstates null
      filling as bends sharpen.</li>
    <li><b>Slant model</b> (every sloper, including what is up now) — LOW.
      It has been wrong once already and moved 6 dB when fixed.</li>
    <li><b>Hybrid model</b> (inverted-Ls) — new today and never validated.
      The Ls may be real or an artefact of combining two models. NEC would
      settle it.</li>
    <li><b>No model charges for trees.</b> Canopy over each ground path is
      shown for that reason: what is up now is almost all over lawn, most
      other wires are not.</li>
    <li><b>Tree heights are operator-supplied</b> and no attachment above
      50 ft has been verified. Every support the search placed is a position
      where a limb would have to exist.</li>
    <li><b>Nothing here says whether a band is open.</b> These are antenna
      figures.</li>
  </ul>
</section>

<footer>
  <p><b>This is modelling, not measurement.</b> No NEC model was run. Every
  figure comes from tools/compare_options.py and tools/topology_search.py;
  this page is generated by tools/build_lineup_page.py.</p>
  <p>Aerial imagery: King County GIS 2025 orthomosaic (EagleView), 90 m frame
  centred on the transformer, georeferenced by construction. Parcel lines
  from King County KingCo_Parcels. Canopy is texture-classified from the same
  photograph.</p>
</footer>
</div>
{JS}
"""


def jpeg_rows(items, bands, uniq, alias, cells_of):
    out = []
    for lab, o, col, dash in items:
        m = C.aggregate_multiband(o, bands)
        out.append((lab, col, f"{name_of(o)}  ·  #{rank(o, uniq, alias)}  ·  "
                              f"{m['n_workable']}/{cells_of} cells  ·  "
                              f"{m['mean_power_dBi']:+.2f} dBi  ·  "
                              f"high point {effort(o)[1]} ft"))
    return out


import build_deployment_guide as G    # noqa: E402  (shared visual system)
G_CSS = G.CSS

if __name__ == "__main__":
    html = build()
    items = items_for(LINEUP, [str(i) for i in range(1, len(LINEUP) + 1)])
    render_jpeg(items, (), crop_for(LINEUP),
                "The lineup · ranked on 40 + 20 + 15 m",
                jpeg_rows(items, M3, U3, A3, 75),
                os.path.join(IMGDIR, "lineup_3band.jpg"))
    items2 = items_for(WIN, [chr(ord("A") + i) for i in range(len(WIN))])
    render_jpeg(items2, [o for o in LINEUP if o not in WIN],
                crop_for(WIN + LINEUP), "Best for 40 + 20 m · lineup faded",
                jpeg_rows(items2, M2, U2, A2, 50),
                os.path.join(IMGDIR, "lineup_40_20.jpg"))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "lineup.html")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print(f"wrote {os.path.normpath(out)} ({len(html)/1024:.0f} KB)")
