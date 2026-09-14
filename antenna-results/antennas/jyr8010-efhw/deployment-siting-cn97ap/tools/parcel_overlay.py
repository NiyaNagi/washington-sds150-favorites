"""Pull the King County parcel for the QTH and draw it on the study's aerial.

Fetches, live, from King County GIS (no key):
  * Property/KingCo_PropertyInfo layer 2 - address, plat, zoning, lot size,
    assessed values for PIN 1117200390;
  * Property/KingCo_Parcels layer 0 - the parcel ring, and every parcel
    ring inside the 200 m frame (neighbours drawn as outlines only).

Writes data/parcel-live-2026-09-13.json and imagery/parcel_overlay.jpg,
drawn on kc2025_wide.jpg (200 m, centred on the feed, exact EPSG:3857
georeference - see imagery/README.md).

Also draws the straight south and east edges compare_options.inside_parcel()
used, so the difference is visible.
"""
import json
import math
import os
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import site_geometry as G  # noqa: E402

DATA = os.path.join(HERE, "..", "data")
IMG = os.path.join(HERE, "..", "imagery")
PIN = "1117200390"
FT = 0.3048
PARCELS = ("https://gismaps.kingcounty.gov/arcgis/rest/services/Property/"
           "KingCo_Parcels/MapServer/0/query")
INFO = ("https://gismaps.kingcounty.gov/arcgis/rest/services/Property/"
        "KingCo_PropertyInfo/MapServer/2/query")
SPAN_M, SRC_PX, OUT_PX = 200.0, 2048, 1600
PPM = OUT_PX / SPAN_M

# Deployment 1 and the roof feed, from data/deployment1.json when present.
ROOF_EN = (-10.7, -10.5)


def query(url, **params):
    params.setdefault("f", "json")
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=60) as r:
        return json.load(r)


def fetch():
    lat, lon = G.FEED
    own = query(PARCELS, geometry=f"{lon},{lat}", geometryType="esriGeometryPoint",
                inSR=4326, spatialRel="esriSpatialRelIntersects", outFields="*",
                returnGeometry="true", outSR=4326)
    info = query(INFO, where=f"PIN='{PIN}'", outFields="*", returnGeometry="false")
    half_lat = SPAN_M / 2 / G.LAT_M
    half_lon = SPAN_M / 2 / G.LON_M
    env = f"{lon - half_lon},{lat - half_lat},{lon + half_lon},{lat + half_lat}"
    area = query(PARCELS, geometry=env, geometryType="esriGeometryEnvelope", inSR=4326,
                 spatialRel="esriSpatialRelIntersects", outFields="PIN",
                 returnGeometry="true", outSR=4326)
    a = info["features"][0]["attributes"]
    rec = {
        "_comment": "Retrieved live from King County GIS by tools/parcel_overlay.py. "
                    "Supersedes the ring in parcel-1117200390.json, which mistyped vertex 10 "
                    "(47.634001 for 47.635001). GIS parcel lines are not a survey.",
        "sources": {"parcel_ring": PARCELS, "attributes": INFO},
        "attributes": {k: (v.strip() if isinstance(v, str) else v) for k, v in a.items()},
        "ring_wgs84": own["features"][0]["geometry"]["rings"][0],
        "neighbours": [{"PIN": f["attributes"]["PIN"], "rings": f["geometry"]["rings"]}
                       for f in area["features"] if f["attributes"]["PIN"] != PIN],
    }
    with open(os.path.join(DATA, "parcel-live-2026-09-13.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return rec


def enu(ring):
    return [G.to_enu((la, lo)) for lo, la in ring]


def px(p):
    return (OUT_PX / 2 + p[0] * PPM, OUT_PX / 2 - p[1] * PPM)


def inside(p, ring):
    x, y = p
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def area_m2(ring):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]))) / 2


def font(size, bold=False):
    for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def halo_line(dr, pts, fill, width, halo="#000000", dash=None):
    segs = []
    for a, b in zip(pts, pts[1:]):
        if not dash:
            segs.append((a, b))
            continue
        L = math.dist(a, b)
        on, off = dash
        t = 0.0
        while t < L:
            t2 = min(L, t + on)
            segs.append(((a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L),
                         (a[0] + (b[0] - a[0]) * t2 / L, a[1] + (b[1] - a[1]) * t2 / L)))
            t += on + off
    for a, b in segs:
        dr.line([a, b], fill=halo, width=width + 4)
    for a, b in segs:
        dr.line([a, b], fill=fill, width=width)


def label(dr, xy, text, f, fill="#ffffff", anchor="mm"):
    dr.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=4, stroke_fill="#000000")


def main():
    rec = fetch()
    own = enu(rec["ring_wgs84"])
    # drop the duplicated closing / near-duplicate vertices for edge labels
    clean = [own[0]]
    for p in own[1:]:
        if math.dist(p, clean[-1]) > 0.05:
            clean.append(p)
    if math.dist(clean[0], clean[-1]) < 0.05:
        clean.pop()

    base = Image.open(os.path.join(IMG, "kc2025_wide.jpg")).convert("RGB")
    assert base.size == (SRC_PX, SRC_PX)
    im = base.resize((OUT_PX, OUT_PX), Image.LANCZOS)
    # dim the photo slightly outside the lot so the line reads
    shade = Image.new("L", im.size, 90)
    ImageDraw.Draw(shade).polygon([px(p) for p in clean], fill=0)
    im = Image.composite(Image.new("RGB", im.size, "#000000"), im, shade.point(lambda v: v))
    dr = ImageDraw.Draw(im)

    for nb in rec["neighbours"]:
        for ring in nb["rings"]:
            pts = [px(p) for p in enu(ring)]
            dr.line(pts + pts[:1], fill="#e8e6dc", width=2)

    # the simplified edges the study's inside_parcel() used
    old = [(-69.9, -6.8), (46.9, -32.0), (53.5, 99.2)]
    halo_line(dr, [px(p) for p in old], "#d95926", 4, dash=(18, 12))

    pts = [px(p) for p in clean]
    halo_line(dr, pts + pts[:1], "#ffd23f", 6)

    f_s, f_m, f_b = font(24), font(28, True), font(40, True)
    # edge lengths
    for a, b in zip(clean, clean[1:] + clean[:1]):
        L = math.dist(a, b)
        if L < 12:
            continue
        mx, my = px(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        ang = math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
        brg = (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360) % 360
        txt = f"{L / FT:.0f} ft"
        tw = dr.textlength(txt, font=f_m) + 16
        lab = Image.new("RGBA", (int(tw), 40), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lab)
        ld.text((tw / 2, 20), txt, font=f_m, fill="#ffd23f", anchor="mm",
                stroke_width=4, stroke_fill="#000000")
        if ang > 90 or ang < -90:
            ang += 180
        lab = lab.rotate(ang, expand=True, resample=Image.BICUBIC)
        # push the label a little outside the lot
        nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if inside((cx + nx * 2, cy + ny * 2), clean):
            nx, ny = -nx, -ny
        ox, oy = px((cx + nx * 4.5, cy + ny * 4.5))
        im.paste(lab, (int(ox - lab.width / 2), int(oy - lab.height / 2)), lab)

    # Deployment 1, if built
    d1p = os.path.join(DATA, "deployment1.json")
    if os.path.exists(d1p):
        with open(d1p, encoding="utf-8") as fh:
            d1 = json.load(fh)
        g = d1["geometry"]
        fe = G.to_enu((g["feed"]["lat"], g["feed"]["lon"]))
        ee = G.to_enu((g["end"]["lat"], g["end"]["lon"]))
        if ee:
            halo_line(dr, [px(fe), px(ee)], "#2a78d6", 5)
            x, y = px(ee)
            dr.ellipse([x - 9, y - 9, x + 9, y + 9], fill="#2a78d6", outline="#000000", width=3)
            label(dr, (x, y + 30), "Deployment 1 support", f_s, anchor="mt")

    for name, p, col in (("Transformer (surveyed feed)", (0.0, 0.0), "#ffffff"),
                         ("Roof feed", ROOF_EN, "#2a78d6")):
        x, y = px(p)
        dr.ellipse([x - 8, y - 8, x + 8, y + 8], fill=col, outline="#000000", width=3)
    label(dr, (px((0, 0))[0] + 16, px((0, 0))[1] - 14), "Transformer", f_s, anchor="ls")
    label(dr, (px(ROOF_EN)[0] - 16, px(ROOF_EN)[1] + 10), "Roof feed", f_s, anchor="rt")

    a = rec["attributes"]
    lot_ft2 = area_m2(clean) / FT ** 2
    label(dr, (40, 44), a.get("ADDR_FULL", ""), f_b, anchor="lt")
    label(dr, (40, 96), f"King County parcel {PIN} · {lot_ft2:,.0f} ft² ({lot_ft2 / 43560:.2f} ac)"
          f" · zoned {a.get('KCA_ZONING', '')}", f_s, anchor="lt")

    # north arrow + scale bar
    x0, y0 = OUT_PX - 70, 70
    dr.polygon([(x0, y0 - 34), (x0 - 16, y0 + 12), (x0, y0 + 2), (x0 + 16, y0 + 12)],
               fill="#ffffff", outline="#000000")
    label(dr, (x0, y0 + 36), "N", f_m)
    sb = 100 * FT * PPM
    y = OUT_PX - 60
    dr.rectangle([40, y - 6, 40 + sb, y + 6], fill="#ffffff", outline="#000000", width=2)
    label(dr, (40 + sb / 2, y - 16), "100 ft", f_s, anchor="md")

    # legend
    lx, ly = OUT_PX - 520, OUT_PX - 170
    dr.rectangle([lx - 20, ly - 20, OUT_PX - 24, OUT_PX - 24], fill="#101010")
    rows = (("#ffd23f", None, 6, "Your lot - King County parcel line"),
            ("#d95926", (18, 12), 4, "Edges the siting study assumed"),
            ("#e8e6dc", None, 2, "Neighbouring parcels"),
            ("#2a78d6", None, 5, "Deployment 1 wire"))
    for i, (col, dash, wd, txt) in enumerate(rows):
        yy = ly + i * 34
        halo_line(dr, [(lx, yy + 14), (lx + 60, yy + 14)], col, wd, halo="#101010", dash=dash)
        dr.text((lx + 76, yy + 14), txt, font=f_s, fill="#ffffff", anchor="lm")
    dr.text((24, OUT_PX - 12), "Imagery: King County GIS 2025 orthomosaic (EagleView). "
            "Parcels: King County GIS. Parcel lines are not a survey.",
            font=font(18), fill="#d0d0d0", anchor="lb")

    out = os.path.join(IMG, "parcel_overlay.jpg")
    im.save(out, quality=90)
    print("wrote", out)
    print("lot area from ring:", round(lot_ft2), "ft²; county:", round(a["Shape.STArea()"]))
    print("ENU vertices (m):", [(round(e, 1), round(n, 1)) for e, n in clean])


if __name__ == "__main__":
    main()
