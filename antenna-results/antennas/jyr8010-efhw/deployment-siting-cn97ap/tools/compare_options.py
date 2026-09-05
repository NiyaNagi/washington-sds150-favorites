#!/usr/bin/env python3
"""Compare deployment topologies for the 39.6 m JYR8010 EFHW at CN97ap.

Scores the recommended bent flat-top against a PVC-mast sloper, a tree-anchored
sloper, inverted-V variants, and the operator's as-described baseline. Emits a
per-region table, aggregate metrics, and a KML overlay.

Standard library only. Run from the repository root:

    python3 antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap/tools/compare_options.py

Writes ../data/deployment-options.kml
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_geometry import (  # noqa: E402
    FEED, APEX, LAT_M, LON_M, WIRE_M, DECLINATION_E,
    to_enu, polar, offset, to_latlon, dms, mag,
    great_circle_bearing, great_circle_km,
    pattern_dB, ground_factor_dB, takeoff_deg,
)

FT = 0.3048
APEX_EN = to_enu(APEX)
APEX_DIST, APEX_BRG = polar(*APEX_EN)

# --------------------------------------------------------------------------
# Terrain, per bearing. Two DIFFERENT quantities - see METHOD.md section 5.
#   horizon_block   : max obstruction angle over all sampled ranges. Signals
#                     cannot arrive below this.
#   foreground_slope: near-field (200-500 m) downslope. Lowers the effective
#                     take-off angle by roughly its own value.
# --------------------------------------------------------------------------
TERRAIN_BY_BEARING = [
    #  brg  horizon  foreground_downslope
    (  30,   5.7,   0.0),
    (  60,   3.4,   0.0),
    ( 100,   0.0,   3.4),
    ( 130,   0.15,  0.0),
    ( 155,   0.0,   1.7),
    ( 210,   0.0,   8.0),
    ( 250,   0.24,  7.9),
    ( 310,   0.0,   4.8),
    ( 326,   0.0,   0.65),
    ( 345,   1.0,   0.0),
]


def inside_parcel(en, margin_m=5.0):
    """Is this local-ENU point inside King County parcel 1117200390?

    Only the south and east edges can bind for supports placed east or south
    of the feed; the west and north boundaries are 70 m and 100 m away.
    Corners are from data/parcel-1117200390.json.
    """
    e, n = en
    # south edge, SE (46.9, -32.0) -> SW (-69.9, -6.8)
    t = (e - 46.9) / -116.8
    if n < (-32.0 + t * 25.2) + margin_m:
        return False
    # east edge, SE (46.9, -32.0) -> NE (53.5, 99.2)
    t = (n + 32.0) / 131.2
    if e > (46.9 + t * 6.6) - margin_m:
        return False
    return True


def terrain_at(bearing):
    """Linear interpolation around the compass."""
    pts = sorted(TERRAIN_BY_BEARING)
    b = bearing % 360
    for i in range(len(pts)):
        b0, h0, s0 = pts[i]
        b1, h1, s1 = pts[(i + 1) % len(pts)]
        span = (b1 - b0) % 360
        off = (b - b0) % 360
        if off <= span and span > 0:
            f = off / span
            return h0 + f * (h1 - h0), s0 + f * (s1 - s0)
    return 0.0, 0.0


# name, lat, lon, typical 20 m arrival elevation (deg)
TARGETS = [
    ("Moscow",            55.75,   37.62, 10),
    ("Kyiv",              50.45,   30.52, 10),
    ("Central Europe",    50.11,    8.68, 10),
    ("United Kingdom",    51.50,   -0.13, 11),
    ("Iberia",            40.40,   -3.70, 10),
    ("South Africa",     -26.20,   28.05,  5),
    ("US Northeast",      40.71,  -74.01, 15),
    ("US Midwest",        41.88,  -87.63, 21),
    ("Caribbean",         18.22,  -66.59, 11),
    ("US Southeast",      25.76,  -80.19, 15),
    ("Denver",            39.74, -104.99, 25),
    ("Dallas",            32.78,  -96.80, 25),
    ("South America",    -34.60,  -58.38,  7),
    ("SoCal",             34.05, -118.24, 30),
    ("New Zealand",      -36.85,  174.76,  7),
    ("Hawaii",            21.31, -157.86, 15),
    ("Australia VK2",    -33.87,  151.21,  6),
    ("Australia VK6",    -31.95,  115.86,  5),
    ("Japan",             35.68,  139.77, 10),
    ("Shanghai",          31.23,  121.47,  8),
    ("Vladivostok",       43.12,  131.89, 10),
    ("Beijing",           39.90,  116.41,  9),
    ("Alaska",            61.22, -149.90, 25),
    ("India",             28.61,   77.21,  6),
    ("Novosibirsk",       55.03,   82.92, 10),
]

LAMBDA_20M = 21.19


# --------------------------------------------------------------------------

class Option:
    """A deployment. segments = [(wire_m, mean_height_m, bearing_deg), ...]"""

    def __init__(self, key, label, segments, supports, note=""):
        self.key, self.label, self.note = key, label, note
        self.segments, self.supports = segments, supports
        self.wire_total = sum(s[0] for s in segments)
        self.avg_h = sum(w * h for w, h, _ in segments) / self.wire_total
        self.legs = sorted({round(b, 1) for _, _, b in segments})

    def takeoff(self, lam):
        return takeoff_deg(self.avg_h, lam)

    def score(self, bearing, arrival_deg):
        """Return (pattern_dB, elev_dB, net_dB) on 20 m for one target."""
        pat = max(pattern_dB(bearing, b, 4) for _, _, b in self.segments)
        horizon, slope = terrain_at(bearing)
        real = max(arrival_deg, horizon)
        eff = real + slope
        elev = ground_factor_dB(eff, self.avg_h, LAMBDA_20M)
        return pat, elev, pat + elev


def build_options():
    opts = []
    run1 = APEX_DIST

    # -- 0. As-described baseline: feed 10 ft, apex 35 ft, leg 2 at 143.1 --
    f, a, e = 10 * FT, 35 * FT, 10 * FT
    leg1 = math.hypot(run1, a - f)
    leg2 = WIRE_M - leg1
    opts.append(Option(
        "BASE", "Baseline as first described (feed 10 ft, apex 35 ft)",
        [(leg1, (f + a) / 2, APEX_BRG), (leg2, (a + e) / 2, 143.1)],
        [("feed", 10, (0, 0)), ("apex tree", 35, APEX_EN),
         ("end", 10, offset(APEX_EN, 143.1, math.sqrt(max(leg2**2 - (a - e)**2, 0))))],
        "The configuration implied by the operator's first three points."))

    # -- A. Recommended bent flat-top --
    f, a, fs, e = 24 * FT, 50 * FT, 50 * FT, 30 * FT
    leg1 = math.hypot(run1, a - f)
    leg2 = WIRE_M - leg1
    into = 29.7 - leg1                      # the 40m/15m current maximum
    run_far = math.sqrt(max(into**2 - (a - fs)**2, 0))
    tail = leg2 - into
    run_tail = math.sqrt(max(tail**2 - (fs - e)**2, 0))
    far_en = offset(APEX_EN, 130.0, run_far)
    opts.append(Option(
        "A", "Bent flat-top, 2 tree supports (RECOMMENDED)",
        [(leg1, (f + a) / 2, APEX_BRG), (into, (a + fs) / 2, 130.0),
         (tail, (fs + e) / 2, 130.0)],
        [("feed", 24, (0, 0)), ("apex tree", 50, APEX_EN),
         ("far support", 50, far_en), ("end", 30, offset(far_en, 130.0, run_tail))],
        "Committed design. Two rope supports at 50 ft."))

    # -- V1. Inverted-V, single tree apex, feed raised --
    f, a, e = 24 * FT, 50 * FT, 10 * FT
    leg1 = math.hypot(run1, a - f)
    leg2 = WIRE_M - leg1
    run2 = math.sqrt(max(leg2**2 - (a - e)**2, 0))
    opts.append(Option(
        "V1", "Inverted-V, ONE tree support at 50 ft, feed 24 ft",
        [(leg1, (f + a) / 2, APEX_BRG), (leg2, (a + e) / 2, 130.0)],
        [("feed", 24, (0, 0)), ("apex tree", 50, APEX_EN),
         ("end", 10, offset(APEX_EN, 130.0, run2))],
        "Drops support 3; leg 2 droops from 50 ft to a ground anchor."))

    # -- V2. Inverted-V, single tree apex, feed left at 10 ft --
    f, a, e = 10 * FT, 50 * FT, 10 * FT
    leg1 = math.hypot(run1, a - f)
    leg2 = WIRE_M - leg1
    run2 = math.sqrt(max(leg2**2 - (a - e)**2, 0))
    opts.append(Option(
        "V2", "Inverted-V, ONE tree support at 50 ft, feed 10 ft",
        [(leg1, (f + a) / 2, APEX_BRG), (leg2, (a + e) / 2, 130.0)],
        [("feed", 10, (0, 0)), ("apex tree", 50, APEX_EN),
         ("end", 10, offset(APEX_EN, 130.0, run2))],
        "As V1 but without raising the feed."))

    # -- V3. Inverted-V on a 24 ft PVC mast --
    f, a, e = 10 * FT, 24 * FT, 10 * FT
    half = WIRE_M / 2
    d = math.sqrt(max(half**2 - (a - f)**2, 0))
    mast_en = offset((0, 0), 110.0, d)
    opts.append(Option(
        "V3", "Inverted-V on a 24 ft PVC mast (symmetric)",
        [(half, (f + a) / 2, 110.0), (half, (a + e) / 2, 110.0)],
        [("feed", 10, (0, 0)), ("PVC mast apex", 24, mast_en),
         ("end", 10, offset(mast_en, 110.0, d))],
        "Both legs on the same axis, so it is electrically a straight wire."))

    # -- S1/S2/S3. Straight slopers, best bearing chosen by scan --
    # "sector" limits the bearing scan. LAWN is the ground verified clear from
    # imagery; ANY only guarantees the support lands inside the parcel, which
    # for this lot means it may sit in dense forest or across the driveway.
    LAWN, ANY = (70, 135), (0, 359)
    for key, mast_ft, feed_ft, sector, label in (
        ("S1", 24, 10, ANY,  "Straight sloper to a 24 ft PVC mast, feed 10 ft"),
        ("S2", 24, 24, ANY,  "Straight sloper to a 24 ft PVC mast, feed 24 ft"),
        ("S3", 50, 24, ANY,  "Straight sloper to a 50 ft TREE, feed 24 ft"),
        ("S4", 50, 24, LAWN, "Straight sloper to a 50 ft tree, feed 24 ft, over the LAWN"),
        ("S5", 24, 24, LAWN, "Straight sloper to a 24 ft PVC mast, feed 24 ft, over the LAWN"),
    ):
        f, top = feed_ft * FT, mast_ft * FT
        run = math.sqrt(max(WIRE_M**2 - (top - f)**2, 0))
        # Scan only bearings whose support lands inside the parcel. Rank by
        # regions workable first, aggregate power second - optimising on
        # aggregate alone picks a bearing that concentrates power into a few
        # directions and drops deep nulls on the rest (see METHOD.md).
        best = None
        for brg in range(sector[0], sector[1] + 1):
            if not inside_parcel(offset((0, 0), float(brg), run)):
                continue
            o = Option(key, label, [(WIRE_M, (f + top) / 2, float(brg))], [])
            a = aggregate(o)
            rank = (a["n_workable"], a["mean_power_dB"])
            if best is None or rank > best[0]:
                best = (rank, float(brg))
        if best is None:
            raise SystemExit(f"{key}: no in-parcel bearing for a {run:.1f} m run")
        brg = best[1]
        top_en = offset((0, 0), brg, run)
        opts.append(Option(
            key, label + f", bearing {brg:.0f}T",
            [(WIRE_M, (f + top) / 2, brg)],
            [("feed", feed_ft, (0, 0)), ("high support", mast_ft, top_en)],
            f"Support sits {run:.1f} m from the feed. Slope "
            f"{math.degrees(math.atan2(top - f, run)):.1f} deg - a 39.6 m wire "
            f"cannot form a steep sloper at these heights."))
    return opts


def aggregate(opt):
    nets = []
    for name, lat, lon, arr in TARGETS:
        b = great_circle_bearing(FEED[0], FEED[1], lat, lon)
        nets.append(opt.score(b, arr)[2])
    lin = [10 ** (n / 10) for n in nets]
    nets_sorted = sorted(nets)
    return {
        "mean_power_dB": 10 * math.log10(sum(lin) / len(lin)),
        "median_dB": nets_sorted[len(nets_sorted) // 2],
        "worst_dB": nets_sorted[0],
        "n_workable": sum(1 for n in nets if n >= -10),
        "n_holes": sum(1 for n in nets if n < -15),
    }


# --------------------------------------------------------------------------
# KML
# --------------------------------------------------------------------------

KML_STYLES = [
    ("optA",  "ff00ff00", 5),   # bright green   - recommended
    ("optV",  "ffffff00", 4),   # cyan           - inverted-V
    ("optS",  "ffff00ff", 4),   # magenta        - sloper
    ("base",  "ff0000ff", 4),   # red            - baseline
    ("ref",   "ff00ffff", 3),   # yellow         - reference points
    ("parcel", "ff00a5ff", 3),  # orange         - parcel line
    ("ray",   "ffffffff", 2),   # white          - bearing rays
]


def kml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def write_kml(opts, path):
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
         '<name>JYR8010 EFHW deployment options - CN97ap</name>',
         '<description>Every candidate deployment for the 39.6 m EFHW, plus '
         'reference points, parcel line and target bearing rays. '
         'Green = recommended, cyan = inverted-V, magenta = sloper, '
         'red = baseline.</description>']

    for sid, colour, width in KML_STYLES:
        L.append(
            f'<Style id="{sid}"><LineStyle><color>{colour}</color>'
            f'<width>{width}</width></LineStyle>'
            f'<PolyStyle><fill>0</fill></PolyStyle>'
            f'<IconStyle><color>{colour}</color><scale>1.1</scale><Icon>'
            f'<href>http://maps.google.com/mapfiles/kml/paddle/wht-blank.png</href>'
            f'</Icon></IconStyle></Style>')

    def pt(name, en, desc, style, height_ft=None):
        lat, lon = to_latlon(*en)
        d, b = polar(*en)
        extra = f"<br/>Height: {height_ft} ft AGL" if height_ft is not None else ""
        return (f'<Placemark><name>{kml_escape(name)}</name><styleUrl>#{style}</styleUrl>'
                f'<description><![CDATA[{desc}{extra}<br/>'
                f'{d:.1f} m ({d/FT:.0f} ft) from feed at {b:.1f}&#176;T / '
                f'{mag(b):.0f}&#176;M<br/>{dms(lat, lon)[0]} {dms(lat, lon)[1]}]]>'
                f'</description>'
                f'<Point><coordinates>{lon:.8f},{lat:.8f},0</coordinates></Point>'
                f'</Placemark>')

    def line(name, ens, desc, style):
        c = " ".join(f"{to_latlon(*e)[1]:.8f},{to_latlon(*e)[0]:.8f},0" for e in ens)
        return (f'<Placemark><name>{kml_escape(name)}</name><styleUrl>#{style}</styleUrl>'
                f'<description><![CDATA[{desc}]]></description>'
                f'<LineString><tessellate>1</tessellate>'
                f'<coordinates>{c}</coordinates></LineString></Placemark>')

    # Reference points supplied by the operator
    L.append('<Folder><name>Reference points (operator supplied)</name>')
    for nm, p, note in (
        ("feed / start (FIXED)", FEED, "Transformer location. NE corner of the house."),
        ("apex tree", APEX, "Primary high support. 50 ft+ by throw line."),
        ("end (original mark)", (47 + 38/60 + 2.41/3600, -(121 + 59/60 + 46.67/3600)),
         "Superseded - the 39.6 m wire does not fit the path this implied."),
        ("front yard corner", (47 + 38/60 + 2.80/3600, -(121 + 59/60 + 47.92/3600)),
         "Candidate anchor. Rejected - nulls Asia."),
        ("backyard corner", (47 + 38/60 + 2.25/3600, -(121 + 59/60 + 47.48/3600)),
         "SE corner of the house."),
        ("front yard driveway corner", (47 + 38/60 + 2.46/3600, -(121 + 59/60 + 48.61/3600)),
         "Candidate anchor. Rejected."),
    ):
        L.append(pt(nm, to_enu(p), note, "ref"))
    L.append('</Folder>')

    for o in opts:
        st = ("optA" if o.key == "A" else "base" if o.key == "BASE"
              else "optV" if o.key.startswith("V") else "optS")
        if not o.supports:
            continue
        agg = aggregate(o)
        t20 = o.takeoff(LAMBDA_20M)
        t20s = f"{t20:.1f}&#176;" if t20 else "no lobe (peaks at zenith)"
        hdr = (f"{o.label}<br/>Average height {o.avg_h/FT:.1f} ft<br/>"
               f"20 m take-off {t20s}<br/>"
               f"Aggregate {agg['mean_power_dB']:+.1f} dB, "
               f"{agg['n_workable']}/{len(TARGETS)} regions workable")
        L.append(f'<Folder><name>{o.key} - {kml_escape(o.label)}</name>'
                 f'<description><![CDATA[{hdr}]]></description>')
        for nm, h, en in o.supports:
            L.append(pt(f"{o.key} {nm}", en, hdr + "<br/><br/>", st, h))
        L.append(line(f"{o.key} wire", [s[2] for s in o.supports], hdr, st))
        L.append('</Folder>')

    # Target bearing rays
    L.append('<Folder><name>Target bearings from the feed</name>'
             '<description>2 km rays on the great-circle bearing to each '
             'region.</description>')
    for name, lat, lon, _ in TARGETS:
        b = great_circle_bearing(FEED[0], FEED[1], lat, lon)
        km = great_circle_km(FEED[0], FEED[1], lat, lon)
        h, s = terrain_at(b)
        L.append(line(f"-> {name} ({b:.0f}T)", [(0, 0), offset((0, 0), b, 2000)],
                      f"{name}<br/>{b:.1f}&#176;T / {mag(b):.0f}&#176;M<br/>"
                      f"{km:.0f} km<br/>Terrain horizon {h:+.1f}&#176;, "
                      f"foreground downslope {s:.1f}&#176;", "ray"))
    L.append('</Folder>')

    L.append('</Document></kml>')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return path


# --------------------------------------------------------------------------

def main():
    opts = build_options()

    print("=" * 100)
    print("DEPLOYMENT GEOMETRY")
    print("=" * 100)
    print(f"{'key':5s} {'avg ht':>8s} {'20m TO':>7s} {'15m TO':>7s} {'10m TO':>7s}"
          f" {'legs':>16s}  supports")
    for o in opts:
        t20, t15, t10 = (o.takeoff(x) for x in (21.19, 14.14, 10.52))
        f = lambda v: f"{v:.1f}" if v else "zenith"
        legs = "/".join(f"{b:.0f}" for b in o.legs)
        sup = ", ".join(f"{n} {h}ft" for n, h, _ in o.supports) or "-"
        print(f"{o.key:5s} {o.avg_h/FT:7.1f}f {f(t20):>7s} {f(t15):>7s} "
              f"{f(t10):>7s} {legs:>16s}  {sup}")

    print("\n" + "=" * 100)
    print("SUPPORT POSITIONS")
    print("=" * 100)
    for o in opts:
        print(f"\n{o.key} - {o.label}")
        for nm, h, en in o.supports:
            d, b = polar(*en)
            lat, lon = to_latlon(*en)
            sa, so = dms(lat, lon)
            if d < 0.01:
                print(f"    {nm:16s} {h:3d} ft  (fixed feed point)")
            else:
                print(f"    {nm:16s} {h:3d} ft  {d:6.2f} m / {d/FT:5.1f} ft  "
                      f"{b:5.1f}T / {mag(b):5.1f}M  {sa} {so}"
                      f"  {'IN' if inside_parcel(en) else 'OUT OF'} parcel")

    print("\n" + "=" * 100)
    print("PER-REGION NET dB ON 20 m (pattern + terrain + elevation response)")
    print("=" * 100)
    keys = [o.key for o in opts]
    print(f"{'region':18s} {'brg':>5s} " + " ".join(f"{k:>7s}" for k in keys))
    for name, lat, lon, arr in TARGETS:
        b = great_circle_bearing(FEED[0], FEED[1], lat, lon)
        row = [o.score(b, arr)[2] for o in opts]
        print(f"{name:18s} {b:5.0f} " + " ".join(f"{v:7.1f}" for v in row))

    print("\n" + "=" * 100)
    print("AGGREGATE ACROSS ALL %d REGIONS" % len(TARGETS))
    print("=" * 100)
    print(f"{'key':5s} {'aggregate':>10s} {'median':>8s} {'worst':>8s} "
          f"{'workable':>9s} {'holes':>6s}  {'vs A':>6s}  label")
    ref = aggregate([o for o in opts if o.key == "A"][0])["mean_power_dB"]
    for o in opts:
        a = aggregate(o)
        print(f"{o.key:5s} {a['mean_power_dB']:9.2f}d {a['median_dB']:8.1f} "
              f"{a['worst_dB']:8.1f} {a['n_workable']:6d}/{len(TARGETS)} "
              f"{a['n_holes']:6d}  {a['mean_power_dB']-ref:+6.1f}  {o.label}")
    print("\naggregate = 10*log10(mean linear power across all regions)")
    print("workable  = regions at or above -10 dB;  holes = below -15 dB")

    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

    with open(os.path.join(data, "option-comparison.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write("# Per-region net dB on 20 m. Generated by tools/compare_options.py.\n")
        fh.write("# net = long-wire pattern (best leg) + ground-reflection response at\n")
        fh.write("# the terrain-adjusted arrival angle. See METHOD.md for confidence.\n")
        fh.write("region,bearing_true_deg," + ",".join(keys) + "\n")
        for name, lat, lon, arr in TARGETS:
            b = great_circle_bearing(FEED[0], FEED[1], lat, lon)
            fh.write(f"{name},{b:.1f}," +
                     ",".join(f"{o.score(b, arr)[2]:.1f}" for o in opts) + "\n")

    with open(os.path.join(data, "option-aggregate.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write("# Aggregate scores across all 25 regions on 20 m.\n")
        fh.write("# aggregate_dB = 10*log10(mean linear power). NOTE: this metric\n")
        fh.write("# rewards concentrating power into a few bearings, so a spiky\n")
        fh.write("# straight wire can score near a broad one. Read it alongside\n")
        fh.write("# n_workable and n_holes, which capture spread.\n")
        fh.write("key,avg_height_ft,takeoff_20m_deg,takeoff_15m_deg,legs_true_deg,"
                 "aggregate_dB,median_dB,worst_dB,n_workable,n_holes,delta_vs_A_dB,label\n")
        for o in opts:
            a = aggregate(o)
            t20, t15 = o.takeoff(21.19), o.takeoff(14.14)
            s20 = f"{t20:.1f}" if t20 else "zenith"
            s15 = f"{t15:.1f}" if t15 else "zenith"
            legs = "/".join(f"{b:.0f}" for b in o.legs)
            fh.write(f"{o.key},{o.avg_h/FT:.1f},{s20},{s15},{legs},"
                     f"{a['mean_power_dB']:.2f},{a['median_dB']:.1f},"
                     f"{a['worst_dB']:.1f},{a['n_workable']},{a['n_holes']},"
                     f"{a['mean_power_dB']-ref:+.1f},\"{o.label}\"\n")

    out = os.path.join(data, "deployment-options.kml")
    print("\nWrote option-comparison.csv, option-aggregate.csv")
    print("KML written to", os.path.normpath(write_kml(opts, out)))


if __name__ == "__main__":
    main()
