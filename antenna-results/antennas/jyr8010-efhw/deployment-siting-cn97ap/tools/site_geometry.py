#!/usr/bin/env python3
"""Recompute every geometric result in the CN97ap siting study from raw inputs.

Standard library only - no dependencies, unlike the parent report's generator.

Run from the repository root:

    python3 antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap/tools/site_geometry.py

Everything printed here is derived, not stored. If a raw input in ../data/
changes, edit the constants below and re-run rather than hand-editing results.
"""

import math

# --------------------------------------------------------------------------
# Raw inputs. Operator-supplied unless noted.
# --------------------------------------------------------------------------

FEED = (47 + 38 / 60 + 2.61 / 3600, -(121 + 59 / 60 + 47.73 / 3600))
APEX = (47 + 38 / 60 + 2.68 / 3600, -(121 + 59 / 60 + 46.97 / 3600))
END_ORIG = (47 + 38 / 60 + 2.41 / 3600, -(121 + 59 / 60 + 46.67 / 3600))
FRONT_YARD = (47 + 38 / 60 + 2.80 / 3600, -(121 + 59 / 60 + 47.92 / 3600))
BACKYARD = (47 + 38 / 60 + 2.25 / 3600, -(121 + 59 / 60 + 47.48 / 3600))
DRIVEWAY = (47 + 38 / 60 + 2.46 / 3600, -(121 + 59 / 60 + 48.61 / 3600))

WIRE_M = 39.6          # verified vendor spec, NOT the 40.0 in the parent metadata
DECLINATION_E = 15.3   # 2026 epoch, Seattle area

FEED_H = 24 * 0.3048
APEX_H = 50 * 0.3048
FAR_H = 50 * 0.3048
END_H = 30 * 0.3048

LEG2_BEARING = 130.0   # selected; operator's original mark implied 143.1

# Terrain, USGS 3DEP 1 m bare earth. (bearing, range_m, elevation_m)
TERRAIN = [
    (30, 200, 112.446716309), (30, 500, 156.635284424),
    (30, 1000, 179.120346069), (30, 2000, 188.500778198),
    (60, 500, 136.904006958), (100, 500, 77.674270630),
    (130, 500, 108.406387329), (155, 500, 91.890235901),
    (210, 500, 36.462936401), (250, 200, 79.521751404),
    (250, 500, 38.040618896), (250, 1000, 111.260238647),
    (310, 500, 64.763870239), (326, 500, 101.440841675),
    (345, 500, 115.908088684),
]
FEED_GROUND_M = 97.240394592
PHASE_CENTRE_M = 107.1  # reference used throughout the session

TARGETS = {
    "Moscow": (55.75, 37.62), "Kyiv": (50.45, 30.52),
    "Central Europe": (50.11, 8.68), "United Kingdom": (51.50, -0.13),
    "Iberia": (40.40, -3.70), "South Africa": (-26.20, 28.05),
    "US Northeast": (40.71, -74.01), "US Midwest": (41.88, -87.63),
    "Caribbean": (18.22, -66.59), "US Southeast": (25.76, -80.19),
    "Denver": (39.74, -104.99), "Dallas": (32.78, -96.80),
    "South America": (-34.60, -58.38), "SoCal": (34.05, -118.24),
    "New Zealand": (-36.85, 174.76), "Hawaii": (21.31, -157.86),
    "Australia VK2": (-33.87, 151.21), "Australia VK4": (-27.47, 153.03),
    "Australia VK6": (-31.95, 115.86), "Japan": (35.68, 139.77),
    "Hong Kong": (22.32, 114.17), "Shanghai": (31.23, 121.47),
    "Vladivostok": (43.12, 131.89), "Beijing": (39.90, 116.41),
    "Alaska": (61.22, -149.90), "India": (28.61, 77.21),
    "Novosibirsk": (55.03, 82.92),
}


# --------------------------------------------------------------------------
# Geodesy
# --------------------------------------------------------------------------

def metres_per_degree(lat_deg):
    """Local scale factors. Series expansion, adequate over a few hundred metres."""
    p = math.radians(lat_deg)
    lat_m = 111132.95 - 559.85 * math.cos(2 * p) + 1.175 * math.cos(4 * p)
    lon_m = 111412.84 * math.cos(p) - 93.5 * math.cos(3 * p) + 0.118 * math.cos(5 * p)
    return lat_m, lon_m


LAT_M, LON_M = metres_per_degree(FEED[0])


def to_enu(pt, origin=FEED):
    """Return (east_m, north_m) of pt relative to origin."""
    return ((pt[1] - origin[1]) * LON_M, (pt[0] - origin[0]) * LAT_M)


def polar(e, n):
    """Return (distance_m, bearing_true_deg) from an ENU offset."""
    return math.hypot(e, n), math.degrees(math.atan2(e, n)) % 360


def offset(origin_en, bearing_deg, dist_m):
    b = math.radians(bearing_deg)
    return (origin_en[0] + dist_m * math.sin(b), origin_en[1] + dist_m * math.cos(b))


def to_latlon(e, n, origin=FEED):
    return (origin[0] + n / LAT_M, origin[1] + e / LON_M)


def dms(lat, lon):
    def f(v, pos, neg):
        h = pos if v >= 0 else neg
        v = abs(v)
        d = int(v)
        m = int((v - d) * 60)
        s = (v - d - m / 60) * 3600
        return f"{d}°{m:02d}'{s:05.2f}\"{h}"
    return f(lat, "N", "S"), f(lon, "E", "W")


def mag(true_deg):
    return (true_deg - DECLINATION_E) % 360


def great_circle_bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(y, x)) % 360


def great_circle_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------
# Antenna models
# --------------------------------------------------------------------------

def longwire_field(theta_deg, n_half_waves):
    """Standing-wave long-wire pattern. theta measured from the WIRE AXIS.

    F(theta) = |[cos(n*pi/2 * cos theta) - cos(n*pi/2)] / sin theta|
    """
    t = math.radians(theta_deg)
    if abs(math.sin(t)) < 1e-9:
        return 0.0
    k = n_half_waves * math.pi / 2
    return abs((math.cos(k * math.cos(t)) - math.cos(k)) / math.sin(t))


def longwire_peak(n):
    return max(longwire_field(t / 10, n) for t in range(1, 900))


def pattern_dB(target_bearing, wire_bearing, n):
    """Gain relative to that wire's own peak lobe, in dB."""
    theta = abs(target_bearing - wire_bearing) % 180
    if theta > 90:
        theta = 180 - theta
    f = longwire_field(theta, n)
    peak = longwire_peak(n)
    return -99.0 if f <= 1e-6 else 20 * math.log10(f / peak)


def ground_factor_dB(elev_deg, h_m, wavelength_m):
    """Horizontal wire over ground: 2*sin(2*pi*h*sin(theta)/lambda), vs peak 2."""
    v = 2 * math.sin(2 * math.pi * (h_m / wavelength_m) * math.sin(math.radians(elev_deg)))
    return -99.0 if v <= 1e-6 else 20 * math.log10(v / 2.0)


def takeoff_deg(h_m, wavelength_m):
    r = wavelength_m / (4 * h_m)
    return None if r > 1 else math.degrees(math.asin(r))


# --------------------------------------------------------------------------

def main():
    print(f"Local scale at {FEED[0]:.4f}N: {LAT_M:.1f} m/deg lat, {LON_M:.1f} m/deg lon")
    print(f"  = {LAT_M/3600:.4f} m/arcsec lat, {LON_M/3600:.4f} m/arcsec lon\n")

    print("=" * 74)
    print("OPERATOR-SUPPLIED POINTS (local ENU from feed)")
    print("=" * 74)
    named = [("apex", APEX), ("end_original", END_ORIG), ("front_yard_corner", FRONT_YARD),
             ("backyard_corner", BACKYARD), ("front_yard_driveway_corner", DRIVEWAY)]
    for name, pt in named:
        e, n = to_enu(pt)
        d, b = polar(e, n)
        print(f"  {name:28s} E{e:+8.3f} N{n:+8.3f}  {d:7.3f} m  {b:6.2f}T / {mag(b):6.2f}M")

    ae, an = to_enu(APEX)
    ee, en = to_enu(END_ORIG)
    d2, b2 = polar(ee - ae, en - an)
    _, b1 = polar(ae, an)
    print(f"\n  Original apex->end: {d2:.3f} m at {b2:.1f}T")
    print(f"  Original bend at apex: {(b2 - b1) % 360:.1f} deg clockwise")
    print(f"  (Operator estimated ~30 deg; coordinates are authoritative.)")

    print("\n" + "=" * 74)
    print("FINAL DESIGN GEOMETRY")
    print("=" * 74)
    run1 = math.hypot(ae, an)
    leg1 = math.hypot(run1, APEX_H - FEED_H)
    leg2 = WIRE_M - leg1
    # support 3 at 29.7 m of wire = the 40m/15m current maximum
    into_leg2 = 29.7 - leg1
    run_far = math.sqrt(max(into_leg2**2 - (APEX_H - FAR_H) ** 2, 0.0))
    tail = leg2 - into_leg2
    run_tail = math.sqrt(max(tail**2 - (FAR_H - END_H) ** 2, 0.0))

    print(f"  leg 1 (feed->apex)      wire {leg1:6.2f} m  run {run1:6.2f} m  "
          f"slope {math.degrees(math.atan2(APEX_H-FEED_H, run1)):.1f} deg up")
    print(f"  leg 2 total             wire {leg2:6.2f} m")
    print(f"  apex->far support       wire {into_leg2:6.2f} m  run {run_far:6.2f} m  (level)")
    print(f"  far support->end        wire {tail:6.2f} m  run {run_tail:6.2f} m  "
          f"slope {math.degrees(math.atan2(FAR_H-END_H, run_tail)):.1f} deg down")

    far_en = offset((ae, an), LEG2_BEARING, run_far)
    end_en = offset(far_en, LEG2_BEARING, run_tail)
    for label, en_pt, h in (("far_support", far_en, FAR_H), ("end_tieoff", end_en, END_H)):
        d, b = polar(*en_pt)
        la, lo = to_latlon(*en_pt)
        sa, so = dms(la, lo)
        print(f"\n  {label}: {sa} {so}")
        print(f"    {d:.2f} m ({d/0.3048:.0f} ft) from feed at {b:.1f}T / {mag(b):.0f}M, {h/0.3048:.0f} ft AGL")

    segs = [(leg1, (FEED_H + APEX_H) / 2), (into_leg2, APEX_H), (tail, (FAR_H + END_H) / 2)]
    avg_h = sum(w * h for w, h in segs) / WIRE_M
    print(f"\n  Weighted average height: {avg_h:.2f} m ({avg_h/0.3048:.1f} ft)")
    for band, lam in (("20m", 21.19), ("15m", 14.14), ("10m", 10.52)):
        t = takeoff_deg(avg_h, lam)
        print(f"    {band} take-off {t:.1f} deg" if t else f"    {band} no distinct lobe")

    print("\n" + "=" * 74)
    print("TERRAIN HORIZON (ref phase centre %.1f m AMSL)" % PHASE_CENTRE_M)
    print("=" * 74)
    horizon = {}
    for brg, rng, elev in TERRAIN:
        ang = math.degrees(math.atan2(elev - PHASE_CENTRE_M, rng))
        horizon[brg] = max(horizon.get(brg, -99), ang)
        print(f"  {brg:3d} deg @ {rng:5d} m  elev {elev:7.2f} m  angle {ang:+6.2f} deg")
    print("\n  Controlling horizon per bearing:")
    for brg in sorted(horizon):
        v = "BLOCKED" if horizon[brg] > 0.5 else "open"
        print(f"    {brg:3d} deg  {horizon[brg]:+6.2f} deg  {v}")

    print("\n" + "=" * 74)
    print("GREAT-CIRCLE BEARINGS AND 20 m PATTERN (legs 82.24 / 130.0)")
    print("=" * 74)
    print(f"  {'target':22s} {'brg T':>7s} {'brg M':>7s} {'km':>7s} {'leg1':>7s} {'leg2':>7s} {'best':>7s}")
    rows = []
    for name, (lat, lon) in TARGETS.items():
        b = great_circle_bearing(FEED[0], FEED[1], lat, lon)
        km = great_circle_km(FEED[0], FEED[1], lat, lon)
        g1 = pattern_dB(b, b1, 4)
        g2 = pattern_dB(b, LEG2_BEARING, 4)
        rows.append((max(g1, g2), name, b, km, g1, g2))
    for best, name, b, km, g1, g2 in sorted(rows, reverse=True):
        print(f"  {name:22s} {b:7.1f} {mag(b):7.1f} {km:7.0f} {g1:7.1f} {g2:7.1f} {best:7.1f}")

    print("\n  Note: 'best of two legs' approximates a bent wire as the union of two")
    print("  lobe sets. Real bent-wire patterns have some cancellation; null-filling")
    print("  is real but the exact depths are indicative, not modelled.")


if __name__ == "__main__":
    main()
