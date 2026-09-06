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
    FEED, APEX, BACKYARD, FRONT_YARD, LAT_M, LON_M, WIRE_M, DECLINATION_E,
    to_enu, polar, offset, to_latlon, dms, mag,
    great_circle_bearing, great_circle_km,
    pattern_dB, ground_factor_dB, takeoff_deg,
    longwire_field, longwire_peak,
)

FT = 0.3048
APEX_EN = to_enu(APEX)
APEX_DIST, APEX_BRG = polar(*APEX_EN)

# --------------------------------------------------------------------------
# Support points the operator has confirmed (2026-09-05): 150 ft trees exist at
# BOTH yard corners as well as at the apex. Those two coordinates were
# originally recorded as house corners in data/site-points.json; they are
# treated here as tree positions on the operator's statement.
#
# The roof ridge is now a REAL candidate feed position on the operator's
# instruction, not just a side-question. Derived in tools/endpoint_study.py
# from the house corner marks: long axis 154.9/334.9T, ridge offset 4 m onto
# the centreline. The 4 m half-width is ASSUMED.
# --------------------------------------------------------------------------
BACK_EN = to_enu(BACKYARD)
FRONT_EN = to_enu(FRONT_YARD)
BACK_DIST, BACK_BRG = polar(*BACK_EN)
FRONT_DIST, FRONT_BRG = polar(*FRONT_EN)

ROOF_EN = offset(offset((0, 0), 154.9, 6.1), 244.9, 4.0)
ROOF_DIST, ROOF_BRG = polar(*ROOF_EN)
ROOF_FEED_FT = 25.0

# Tallest attachment a throw line can reach in the available conifer.
TREE_MAX_FT = 150.0


def sloper_geometry(feed_en, feed_ft, top_en):
    """A straight sloper is fully determined by where its support stands.

    With the wire length fixed there is no free parameter: the run sets the
    rise, which sets the slope and the attachment height.

        rise = sqrt(WIRE^2 - run^2)

    Returns (run_m, bearing_deg, rise_m, top_ft, slope_deg), or None if the
    support is further away than the wire is long.
    """
    run, brg = polar(top_en[0] - feed_en[0], top_en[1] - feed_en[1])
    if run >= WIRE_M:
        return None
    rise = math.sqrt(WIRE_M ** 2 - run ** 2)
    return (run, brg, rise, feed_ft + rise / FT,
            math.degrees(math.atan2(rise, run)))

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
# Bands. The JYR8010 is an 80 m EFHW; a 1:64 transformer feeds a 39.6 m wire
# that is resonant on the HARMONIC bands only. n = number of half-waves the
# wire carries = round(2 * 39.6 / lambda).
#
# 30 m, 17 m and 12 m are NOT here. The odd harmonics land at roughly 10.65,
# 17.75 and 24.85 MHz, which miss the 30 m (10.10) and 17 m (18.07) allocations
# entirely; 24.85 grazes the bottom of 12 m (24.89) but is out of band. Those
# three need a tuner and are outside this model.
#
# Wavelengths are the exact values already used elsewhere in this study so that
# every previously published 20 m and 15 m number reproduces bit for bit.
#
# peak_dBi is the free-space peak directivity of a resonant wire of n
# half-waves (standard long-wire directivity table). It is needed ONLY for
# cross-band comparison: pattern_dB() from site_geometry normalises each wire to
# its OWN peak, which silently throws away the fact that a 4-lambda wire has
# ~5 dB more peak gain than a half-wave one. Per-band net_dB keeps the old
# normalised convention; net_dBi adds this back.
#   CONFIDENCE: MODERATE. Textbook values for a thin resonant wire in free
#   space, not computed for this installation.
# --------------------------------------------------------------------------
BANDS = [
    # key   f_MHz  lambda_m  n   peak_dBi  arrival_scale  in_multiband
    ("80m",  3.550,   84.45,  1,   2.15,     1.90,        False),
    ("40m",  7.100,   42.22,  2,   3.80,     1.45,        True),
    ("20m", 14.150,   21.19,  4,   5.30,     1.00,        True),
    ("15m", 21.200,   14.14,  6,   6.40,     0.88,        True),
    ("10m", 28.500,   10.52,  8,   7.10,     0.80,        False),
]
BAND_KEYS = [b[0] for b in BANDS]
BAND = {b[0]: dict(zip(
    ("key", "f", "lam", "n", "peak_dBi", "arr_scale", "mb"), b)) for b in BANDS}

# The three bands aggregated together, per the operator's request: 40 m and
# 20 m (the two they named) plus 15 m. 15 m is the next most-used band that
# this antenna is actually RESONANT on - 17 m sees comparable on-air traffic
# but is not a harmonic of a 39.6 m wire, so it cannot be scored here.
MULTIBAND = [k for k in BAND_KEYS if BAND[k]["mb"]]

# Workability thresholds on the absolute (dBi) scale. -5.0 dBi on 20 m is
# -10.3 dB relative to that wire's own peak, i.e. essentially the -10 dB
# threshold used in every earlier revision, so the 20 m counts are unchanged.
WORKABLE_dBi = -5.0
HOLE_dBi = -10.0


def imax_positions(n):
    """Current-maxima positions along the wire, metres from the feed.

    A wire carrying n half-waves has current maxima at the centre of each
    half-wave: (2k+1) * L / (2n). For n = 4 this returns the familiar
    4.95 / 14.85 / 24.75 / 34.65 m used throughout this study.
    """
    return [(2 * k + 1) * WIRE_M / (2 * n) for k in range(n)]


# 20 m current maxima along a 39.6 m EFHW, metres from the feed. These are the
# points that actually radiate; their MEAN HEIGHT predicts low-angle
# performance better than plain average wire height, and it is pure arithmetic.
I_MAX_20M = imax_positions(4)


def arrival_for_band(arr20_deg, band):
    """Scale a 20 m arrival angle to another band.

    Lower bands support shorter hops and arrive higher; higher bands arrive
    lower. A single multiplier per band, clamped to a plausible range.

    CONFIDENCE: LOW. This is a rule of thumb, not a propagation model. It
    encodes the right DIRECTION of the effect and roughly the right size. It
    does not know about hop count, season, or solar flux, and it deliberately
    says nothing about whether a band is OPEN to a given path - see the
    band-availability notes in README.md. Treat cross-band deltas of a couple
    of dB as noise.
    """
    return min(60.0, max(3.0, arr20_deg * BAND[band]["arr_scale"]))

# Ground LOSS for the vertically polarised part of a slant wire, over average
# ground (sigma 5 mS/m, eps_r 13). This is loss ONLY - the elevation SHAPE now
# comes from the 3-D wire pattern and the reflection phase, not from here. A
# flat ~3 dB of average-ground loss plus the pseudo-Brewster rolloff below ~15
# deg.
#
# CONFIDENCE: LOW. Traced from standard published curves, NOT computed from soil
# constants. See METHOD.md section 9.
VERT_GROUND_LOSS_dB = [
    (3, -9.0), (5, -7.0), (10, -4.5), (15, -3.5), (20, -3.3),
    (30, -3.0), (45, -3.0), (60, -3.0), (90, -3.0),
]


def _interp(pts, x):
    if x <= pts[0][0]:
        return pts[0][1]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if a[0] <= x <= b[0]:
            f = (x - a[0]) / (b[0] - a[0])
            return a[1] + f * (b[1] - a[1])
    return pts[-1][1]


def vert_ground_loss_dB(elev_deg):
    return _interp(VERT_GROUND_LOSS_dB, elev_deg)


def slant_axis_angle(target_bearing, elev_deg, wire_bearing, slope_deg):
    """True 3-D angle between the wire axis and the ray to the target, degrees.

    The azimuth-only pattern used for the flat options is a 2-D shortcut that is
    fine for a wire lying within a few degrees of horizontal. A wire tilted 66
    deg needs the real thing: the long-wire pattern is a function of the angle
    from the WIRE AXIS in three dimensions, and for a steep wire that angle
    barely resembles the azimuth difference.
    """
    b, s = math.radians(wire_bearing), math.radians(slope_deg)
    u = (math.sin(b) * math.cos(s), math.cos(b) * math.cos(s), math.sin(s))
    t, a = math.radians(target_bearing), math.radians(elev_deg)
    d = (math.sin(t) * math.cos(a), math.cos(t) * math.cos(a), math.sin(a))
    dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(u, d))))
    return math.degrees(math.acos(dot))


# --------------------------------------------------------------------------

class Option:
    """A deployment. segments = [(wire_m, mean_height_m, bearing_deg), ...]

    slope_deg > 0 marks a STEEP SLANT wire, which is modelled as a mix of
    vertical and horizontal polarisation rather than as a horizontal wire over
    ground. Above roughly 30 deg the horizontal-wire model stops applying.
    """

    def __init__(self, key, label, segments, supports, note="",
                 slope_deg=0.0, feed_h=None, top_h=None):
        self.key, self.label, self.note = key, label, note
        self.segments, self.supports = segments, supports
        self.slope_deg, self.feed_h, self.top_h = slope_deg, feed_h, top_h
        self.wire_total = sum(s[0] for s in segments)
        self.avg_h = sum(w * h for w, h, _ in segments) / self.wire_total
        self.legs = sorted({round(b, 1) for _, _, b in segments})

    @property
    def is_slant(self):
        return self.slope_deg > 0.5

    # ----------------------------------------------------------------------
    # Deployment effort. The operator's point is that option A "will be much
    # harder to deploy" than a sloper, and nothing in the scoring knew that.
    # Two numbers, both arithmetic:
    #
    #   n_anchors     elevated attachments other than the feed - each one is a
    #                 separate line over a separate limb.
    #   max_anchor_ft the highest of them. This is the one that actually
    #                 decides difficulty: a 50 ft throw is a routine afternoon
    #                 with a slingshot and a weight; 120 ft is a different
    #                 activity, and 150 ft is a climbing job.
    #
    # A sloper needs ONE anchor, which is why it looks easy - but a straight
    # 39.6 m sloper puts that one anchor very high, because the rise is forced
    # by the run. Fewer anchors does not automatically mean less work.
    # ----------------------------------------------------------------------
    @property
    def n_anchors(self):
        return sum(1 for _, h, _ in self.supports[1:] if h > 15)

    @property
    def max_anchor_ft(self):
        hs = [h for _, h, _ in self.supports[1:]]
        return max(hs) if hs else 0

    @property
    def throw_class(self):
        h = self.max_anchor_ft
        if h == 0:
            return "-"
        if h <= 55:
            return "easy"          # slingshot and a weight
        if h <= 90:
            return "hard"          # big slingshot, good line, some luck
        if h <= 130:
            return "very hard"     # arborist launcher territory
        return "climb"             # not a throw any more

    def height_at_wire(self, s):
        """Height above ground at distance s along the wire from the feed."""
        if self.is_slant:
            return self.feed_h + s * math.sin(math.radians(self.slope_deg))
        # Walk the segments, interpolating linearly within each.
        run = 0.0
        for i, (w, hmean, _) in enumerate(self.segments):
            if s <= run + w or i == len(self.segments) - 1:
                return hmean          # segment mean is adequate here
            run += w
        return self.avg_h

    def mean_imax_height(self, band="20m"):
        pos = imax_positions(BAND[band]["n"])
        return sum(self.height_at_wire(s) for s in pos) / len(pos)

    def takeoff(self, lam):
        if self.is_slant:
            return None               # not a horizontal-wire lobe
        return takeoff_deg(self.avg_h, lam)

    def peak_elev(self, band):
        """Elevation of the pattern's global peak, degrees.

        For flat options this is the closed-form ground-reflection lobe. For
        slant options there is none, so scan elevation against the BEST
        azimuth at each elevation. Scanning a single azimuth is wrong for a
        sloper: looking along the wire's own bearing at low elevation puts you
        close to the wire axis, which is a null, and the scan then reports an
        almost-vertical "take-off" that the antenna does not actually have.
        """
        if not self.is_slant:
            return self.takeoff(BAND[band]["lam"])
        return max(range(1, 90), key=lambda a: max(
            self.score(float(b), a, band, raw_elev=True)[2]
            for b in range(0, 360, 10)))

    def score(self, bearing, arrival_deg, band="20m", raw_elev=False):
        """Return (pattern_dB, elev_dB, net_dB) on one band for one target.

        net_dB is relative to an ideal horizontal wire's own peak, the same
        normalisation every earlier revision used. Add BAND[band]["peak_dBi"]
        to get the absolute scale used for cross-band comparison.
        """
        bd = BAND[band]
        lam, n = bd["lam"], bd["n"]
        if raw_elev:
            eff = arrival_deg
        else:
            horizon, slope = terrain_at(bearing)
            eff = max(arrival_for_band(arrival_deg, band), horizon) + slope

        if not self.is_slant:
            pat = max(pattern_dB(bearing, b, n) for _, _, b in self.segments)
            elev = ground_factor_dB(eff, self.avg_h, lam)
            return pat, elev, pat + elev

        # -------------------------------------------------------------
        # Slant wire. See METHOD.md section 9 (rewritten 2026-09-05).
        #
        # Direct ray: the exact free-space long-wire pattern, evaluated at the
        # TRUE 3-D angle from the wire axis. Ground: an image at the mean
        # height of that band's current maxima, with the two polarisations
        # reflecting differently - horizontal inverts (sin), vertical does not
        # (cos), which is why a steep wire keeps low-angle response where a low
        # horizontal wire cannot. Polarisation split is sin^2 / cos^2 of slope.
        # -------------------------------------------------------------
        th = math.radians(self.slope_deg)
        fv, fh = math.sin(th) ** 2, math.cos(th) ** 2
        b0 = self.segments[0][2]
        psi = slant_axis_angle(bearing, eff, b0, self.slope_deg)
        pat_lin = (longwire_field(psi, n) / longwire_peak(n)) ** 2

        h_eff = max(self.mean_imax_height(band), 0.5)
        ph = 2 * math.pi * (h_eff / lam) * math.sin(math.radians(eff))
        gh = math.sin(ph) ** 2                       # horizontal image, ref 1.0
        gv = math.cos(ph) ** 2 * 10 ** (vert_ground_loss_dB(eff) / 10)

        vlin = fv * pat_lin * gv
        hlin = fh * pat_lin * gh
        net = 10 * math.log10(max(vlin + hlin, 1e-12))
        # Report the split for diagnostics; pattern/elev are not separable here.
        return (10 * math.log10(max(vlin, 1e-12)),
                10 * math.log10(max(hlin, 1e-12)), net)


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

    # ---------------------------------------------------------------------
    # T class: TALL slopers. Height unconstrained (150 ft trees available) and
    # the parcel boundary is NOT enforced - out-of-parcel supports are reported
    # instead. Above ~30 deg these stop behaving as horizontal wires and become
    # slant/vertical radiators, so they use the slant model.
    # ---------------------------------------------------------------------
    f = 24 * FT
    tall = [("T30", 30.0), ("T45", 45.0), ("T60", 60.0), ("T75", 75.0)]

    # T-APEX: the slope you get for free from the EXISTING apex tree.
    rise_apex = math.sqrt(max(WIRE_M**2 - run1**2, 0))
    tall.append(("T-APEX", math.degrees(math.atan2(rise_apex, run1))))

    for key, slope in tall:
        th = math.radians(slope)
        run = WIRE_M * math.cos(th)
        top = f + WIRE_M * math.sin(th)
        extra = ""
        if key == "T-APEX":
            brg, top_en = APEX_BRG, APEX_EN
        else:
            # Scanned on the THREE-BAND metric now, not 20 m alone. The 20 m
            # optimum is computed too and reported, so the cost of the change
            # is visible rather than silent.
            best = {}
            for b in range(0, 360):           # NO parcel constraint here
                o = Option(key, key, [(WIRE_M, (f + top) / 2, float(b))], [],
                           slope_deg=slope, feed_h=f, top_h=top)
                m = aggregate_multiband(o)
                a20 = aggregate(o, "20m")
                for tag, rank in (
                    ("mb", (m["n_workable"], m["n_regions_covered"],
                            m["mean_power_dBi"])),
                    ("20", (a20["n_workable"], a20["mean_power_dB"]))):
                    if tag not in best or rank > best[tag][0]:
                        best[tag] = (rank, float(b))
            brg, brg20 = best["mb"][1], best["20"][1]
            top_en = offset((0, 0), brg, run)
            if abs((brg - brg20 + 180) % 360 - 180) >= 3:
                extra = (f" 20 m-only optimum was {brg20:.0f}T; the 3-band "
                         f"scan moved it to {brg:.0f}T.")
        where = "IN parcel" if inside_parcel(top_en) else "OUT OF PARCEL"
        opts.append(Option(
            key,
            f"Tall sloper, {slope:.0f} deg slope, top {top/FT:.0f} ft"
            + (" (existing apex tree)" if key == "T-APEX" else f", bearing {brg:.0f}T"),
            [(WIRE_M, (f + top) / 2, brg)],
            [("feed", 24, (0, 0)), ("tree top", int(round(top / FT)), top_en)],
            f"Support {run:.1f} m ({run/FT:.0f} ft) from the feed, {where}. "
            f"Slant model - see METHOD.md section 9.{extra}",
            slope_deg=slope, feed_h=f, top_h=top))

    opts.extend(build_sloper_classes())
    opts.extend(build_feed10_class())
    opts.extend(build_redbox_class())
    return opts


# --------------------------------------------------------------------------
# RB class: supports on the operator's pre-staked garden posts.
#
# The operator marked a strip on the plan view where posts already stand and
# PVC or similar can be attached. Georeferenced from that annotation against
# the four support markers (similarity fit, worst residual 6 cm on the ground):
# a strip 3.3-4.1 m wide and 17-18 m long, long axis 139T, centroid 30.4 m
# (100 ft) from the feed at 115T / 100M. Entirely inside the parcel.
#
# This class matters for a reason no dB figure captures: a post you can walk to
# is not a 50 ft rope throw into a conifer. Every other support in this study
# is a tree.
#
# Feed is held at 10 ft throughout - the operator's current constraint.
# --------------------------------------------------------------------------
RED_BOX = [(23.07, -5.62), (20.30, -7.39), (31.99, -20.88), (34.73, -17.85)]
POST_HEIGHTS_FT = (12.0, 16.0, 20.0, 25.0, 30.0)


def in_red_box(en):
    """Point in the operator's staked strip (convex quad, winding test)."""
    e, n = en
    sign = 0
    for i in range(4):
        ax, ay = RED_BOX[i]
        bx, by = RED_BOX[(i + 1) % 4]
        cross = (bx - ax) * (n - ay) - (by - ay) * (e - ax)
        s = (cross > 0) - (cross < 0)
        if s == 0:
            continue
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True


def red_box_points(step=0.75):
    """Candidate post positions on a grid inside the strip."""
    es = [p[0] for p in RED_BOX]
    ns = [p[1] for p in RED_BOX]
    out = []
    e = min(es)
    while e <= max(es):
        n = min(ns)
        while n <= max(ns):
            if in_red_box((e, n)):
                out.append((e, n))
            n += step
        e += step
    return out


def build_redbox_class():
    FEED_FT = 10.0
    f = FEED_FT * FT
    apex_h = 50.0 * FT
    leg1 = math.hypot(APEX_DIST, apex_h - f)
    rest = WIRE_M - leg1
    # 0.5 m grid for the single-post scans - coarser than this and the reported
    # post position moves by a metre or two between runs, which is enough to
    # make the documented figures disagree with the tool.
    grid = red_box_points(0.5)
    coarse = red_box_points(1.0)          # the two-post scan is O(n^2)
    out = []

    def score_of(o):
        m = aggregate_multiband(o)
        return (m["n_workable"], m["n_regions_covered"], m["mean_power_dBi"])

    # -- RB-1TREE: feed -> apex tree -> ONE post. One throw, one post. ------
    #
    # Two keys. RB-1TREE is the optimiser's best over all post heights, which
    # always picks the tallest allowed. RB-POST20 fixes the post at 20 ft
    # because that is the height actually recommended: the whole 10-36 ft range
    # spans 0.83 dB, 20 ft already matches F10-A's cell count and beats its
    # worst case, and a taller mast on a garden stake is a windstorm problem
    # rather than a dB problem. The two are kept separate so the recommendation
    # and the scored geometry can never drift apart.
    def best_post(fixed_ft=None):
        b_ = None
        for post_ft in ([fixed_ft] if fixed_ft else POST_HEIGHTS_FT):
            ph = post_ft * FT
            for pe, pn in grid:
                run = math.hypot(pe - APEX_EN[0], pn - APEX_EN[1])
                if abs(math.hypot(run, apex_h - ph) - rest) > 0.45:
                    continue                   # wire must actually reach
                brg = polar(pe - APEX_EN[0], pn - APEX_EN[1])[1]
                o = Option("x", "x", [(leg1, (f + apex_h) / 2, APEX_BRG),
                                      (rest, (apex_h + ph) / 2, brg)], [])
                r = score_of(o)
                if b_ is None or r > b_[0]:
                    b_ = (r, post_ft, (pe, pn), brg, run)
        return b_

    for key, fixed, note in (
        ("RB-POST20", 20.0, "RECOMMENDED BUILD. "),
        ("RB-1TREE", None, ""),
    ):
        b_ = best_post(fixed)
        if not b_:
            continue
        _, post_ft, pen, brg, run = b_
        d, b = polar(*pen)
        out.append(Option(
            key,
            f"Apex tree at 50 ft, then ONE post at {post_ft:.0f} ft in the "
            f"staked strip" + (" (recommended)" if fixed else " (best found)"),
            [(leg1, (f + apex_h) / 2, APEX_BRG),
             (rest, (apex_h + post_ft * FT) / 2, brg)],
            [("feed", 10, (0.0, 0.0)), ("apex tree", 50, APEX_EN),
             ("post", int(post_ft), pen)],
            f"{note}Post {d:.1f} m ({d/FT:.0f} ft) from the feed at {b:.0f}T / "
            f"{mag(b):.0f}M, {run:.1f} m from the apex. ONE rope throw and one "
            f"post you can walk to."))

    # -- RB-2POST: apex tree, then two posts, support 3 at the 29.7 m -------
    #    current maximum exactly as option A places it.
    best = None
    into = 29.7 - leg1
    tail = rest - into
    for h3 in POST_HEIGHTS_FT:
        for h4 in POST_HEIGHTS_FT:
            if h4 > h3:
                continue
            for p3 in coarse:
                run3 = math.hypot(p3[0] - APEX_EN[0], p3[1] - APEX_EN[1])
                if abs(math.hypot(run3, apex_h - h3 * FT) - into) > 0.45:
                    continue
                b3 = polar(p3[0] - APEX_EN[0], p3[1] - APEX_EN[1])[1]
                for p4 in coarse:
                    run4 = math.hypot(p4[0] - p3[0], p4[1] - p3[1])
                    if abs(math.hypot(run4, (h3 - h4) * FT) - tail) > 0.45:
                        continue
                    b4 = polar(p4[0] - p3[0], p4[1] - p3[1])[1]
                    o = Option("RB-2POST", "x",
                               [(leg1, (f + apex_h) / 2, APEX_BRG),
                                (into, (apex_h + h3 * FT) / 2, b3),
                                (tail, ((h3 + h4) / 2) * FT, b4)], [])
                    r = score_of(o)
                    if best is None or r > best[0]:
                        best = (r, h3, h4, p3, p4, b3, b4)
    if best:
        _, h3, h4, p3, p4, b3, b4 = best
        d3 = polar(*p3)[0]
        out.append(Option(
            "RB-2POST",
            f"Apex tree at 50 ft, then TWO posts ({h3:.0f} / {h4:.0f} ft) in "
            f"the staked strip",
            [(leg1, (f + apex_h) / 2, APEX_BRG),
             (into, (apex_h + h3 * FT) / 2, b3),
             (tail, ((h3 + h4) / 2) * FT, b4)],
            [("feed", 10, (0.0, 0.0)), ("apex tree", 50, APEX_EN),
             ("post 3", int(h3), p3), ("post 4", int(h4), p4)],
            f"Support 3 stays at 29.7 m of wire - the 40 m and 15 m current "
            f"maximum - but on a post {d3/FT:.0f} ft out instead of a tree limb. "
            f"One rope throw."))

    # -- RB-NOTREE: feed straight to a post. NO rope throw at all. ---------
    best = None
    for post_ft in POST_HEIGHTS_FT:
        ph = post_ft * FT
        for pe, pn in grid:
            run = math.hypot(pe, pn)
            if abs(math.hypot(run, ph - f) - WIRE_M) > 0.45:
                continue
            brg = polar(pe, pn)[1]
            slope = math.degrees(math.atan2(ph - f, run))
            o = Option("RB-NOTREE", "x", [(WIRE_M, (f + ph) / 2, brg)], [],
                       slope_deg=slope, feed_h=f, top_h=ph)
            r = score_of(o)
            if best is None or r > best[0]:
                best = (r, post_ft, (pe, pn), brg, run, slope)
    if best:
        _, post_ft, pen, brg, run, slope = best
        d, b = polar(*pen)
        out.append(Option(
            "RB-NOTREE",
            f"NO trees at all - single span, feed 10 ft to a {post_ft:.0f} ft "
            f"post",
            [(WIRE_M, (f + post_ft * FT) / 2, brg)],
            [("feed", 10, (0.0, 0.0)), ("post", int(post_ft), pen)],
            f"Post {d:.1f} m ({d/FT:.0f} ft) from the feed at {b:.0f}T / "
            f"{mag(b):.0f}M. Slope {slope:.1f} deg. ZERO rope throws - the "
            f"whole antenna is reachable from the ground.",
            slope_deg=slope, feed_h=f, top_h=post_ft * FT))
    return out


# --------------------------------------------------------------------------
# F10 class: everything re-scored with the feed held at 10 ft.
#
# The operator has to leave the transformer at 10 ft for now. That is a
# different constraint from every other class here, which assumes the feed can
# be lifted to 24 ft, so it gets its own family rather than being mixed in.
#
# Expect the penalty to be modest and unevenly distributed. The feed is a
# voltage maximum - a current null - so its own height matters little (see
# tools/endpoint_study.py). What actually costs is that lowering the feed drags
# the first part of the wire down with it, and on a flat-top that is where two
# of the four 20 m current maxima live.
# --------------------------------------------------------------------------

def build_feed10_class():
    F10 = 10.0
    out = []
    run1 = APEX_DIST

    # -- F10-A: the recommended flat-top, feed dropped to 10 ft --------------
    f, a, fs, e = F10 * FT, 50 * FT, 50 * FT, 30 * FT
    leg1 = math.hypot(run1, a - f)
    leg2 = WIRE_M - leg1
    into = 29.7 - leg1
    run_far = math.sqrt(max(into ** 2 - (a - fs) ** 2, 0))
    tail = leg2 - into
    run_tail = math.sqrt(max(tail ** 2 - (fs - e) ** 2, 0))
    far_en = offset(APEX_EN, 130.0, run_far)
    out.append(Option(
        "F10-A", "Bent flat-top (option A geometry) with the feed at 10 ft",
        [(leg1, (f + a) / 2, APEX_BRG), (into, (a + fs) / 2, 130.0),
         (tail, (fs + e) / 2, 130.0)],
        [("feed", 10, (0, 0)), ("apex tree", 50, APEX_EN),
         ("far support", 50, far_en),
         ("end", 30, offset(far_en, 130.0, run_tail))],
        "Same four points as option A, feed lowered 24 -> 10 ft."))

    # -- F10-V: inverted-V off the apex tree. This is exactly option V2, ----
    # kept under an F10 key so the 10 ft family is complete on its own.
    leg2 = WIRE_M - leg1
    run2 = math.sqrt(max(leg2 ** 2 - (a - F10 * FT) ** 2, 0))
    out.append(Option(
        "F10-V", "Inverted-V, one 50 ft support, feed 10 ft (same as V2)",
        [(leg1, (f + a) / 2, APEX_BRG), (leg2, (a + f) / 2, 130.0)],
        [("feed", 10, (0, 0)), ("apex tree", 50, APEX_EN),
         ("end", 10, offset(APEX_EN, 130.0, run2))],
        "Identical to V2; duplicated here so the 10 ft family stands alone."))

    # -- F10 slopers to the three trees that are known to exist -------------
    for key, label, top_en in (
        ("F10-APEX", "Sloper to the APEX tree, feed 10 ft", APEX_EN),
        ("F10-BACK", "Sloper to the BACKYARD-corner tree, feed 10 ft", BACK_EN),
        ("F10-FRONT", "Sloper to the FRONT-YARD-corner tree, feed 10 ft",
         FRONT_EN),
    ):
        o = _sloper(key, label, (0.0, 0.0), F10, top_en,
                    "Support already exists.")
        if o:
            out.append(o)

    # -- F10 rotation locked to a corner bearing ----------------------------
    for key, label, brg in (
        ("F10-CB", "Sloper, feed 10 ft, locked to the BACKYARD bearing",
         BACK_BRG),
        ("F10-CF", "Sloper, feed 10 ft, locked to the FRONT-YARD bearing",
         FRONT_BRG),
    ):
        o = _best_sloper(key, f"{label} ({brg:.0f}T)", (0.0, 0.0), F10, [brg])
        if o:
            out.append(o)

    # -- F10-G: the best buildable sloper at 10 ft. The answer to "what is --
    # the best thing I can do right now".
    g = _best_sloper("F10-G", "BEST single-support sloper with a 10 ft feed",
                     (0.0, 0.0), F10, range(0, 360, 5),
                     "Azimuth and distance both optimised.")
    if g:
        out.append(g)
    return out


# --------------------------------------------------------------------------
# Single-support sloper classes.
#
# The operator's point: option A needs FOUR supports and two rope throws, and
# is much harder to deploy than a sloper, which needs one. So the question that
# matters is not "what is the best antenna" but "what is the best antenna with
# ONE support" - and then how much option A is really worth over it.
#
# Three sub-classes, deliberately separated:
#   K-*  supports that are KNOWN to exist (the three 150 ft trees). Geometry is
#        forced - no free parameter at all.
#   C-*  azimuth locked to a yard-corner bearing, support distance free. This
#        is the "constrain the rotation" question.
#   G-*  best buildable sloper found by unconstrained search, subject to the
#        parcel and a 150 ft attachment cap. The benchmark the others are
#        measured against.
# --------------------------------------------------------------------------

def _sloper(key, label, feed_en, feed_ft, top_en, note=""):
    g = sloper_geometry(feed_en, feed_ft, top_en)
    if g is None:
        return None
    run, brg, rise, top_ft, slope = g
    over = "" if top_ft <= TREE_MAX_FT else \
        f" NEEDS {top_ft:.0f} ft - EXCEEDS the {TREE_MAX_FT:.0f} ft tree cap."
    where = "IN parcel" if inside_parcel(top_en) else "OUT OF PARCEL"
    feed_pt = ("feed", int(round(feed_ft)), feed_en)
    return Option(
        key, label,
        [(WIRE_M, (feed_ft * FT + top_ft * FT) / 2, brg)],
        [feed_pt, ("tree top", int(round(top_ft)), top_en)],
        f"Support {run:.1f} m ({run/FT:.0f} ft) from the feed at {brg:.0f}T, "
        f"{where}. Slope {slope:.1f} deg, attach at {top_ft:.0f} ft.{over} "
        f"{note} Slant model - see METHOD.md section 9.",
        slope_deg=slope, feed_h=feed_ft * FT, top_h=top_ft * FT)


def _best_sloper(key, label, feed_en, feed_ft, bearings, note="",
                 enforce_parcel=True, cap_height=True):
    """Scan support distance (and azimuth, where free) on the 3-band metric.

    Coarse pass then a fine pass around the winner. Ranked the way METHOD.md
    section 7 requires: workable cells first, regions second, power last.
    """
    def evaluate(brg, run):
        top_en = offset(feed_en, brg, run)
        if enforce_parcel and not inside_parcel(top_en):
            return None
        rise = math.sqrt(max(WIRE_M ** 2 - run ** 2, 0))
        top_ft = feed_ft + rise / FT
        if cap_height and top_ft > TREE_MAX_FT:
            return None
        o = Option(key, label, [(WIRE_M, (feed_ft * FT + top_ft * FT) / 2, brg)],
                   [], slope_deg=math.degrees(math.atan2(rise, run)),
                   feed_h=feed_ft * FT, top_h=top_ft * FT)
        m = aggregate_multiband(o)
        return ((m["n_workable"], m["n_regions_covered"], m["mean_power_dBi"]),
                brg, run)

    best = None
    for brg in bearings:
        for run10 in range(100, int(WIRE_M * 10), 10):     # 10.0 .. 39.5 m
            r = evaluate(float(brg), run10 / 10.0)
            if r and (best is None or r[0] > best[0]):
                best = r
    if best is None:
        return None
    for run10 in range(max(100, int(best[2] * 10) - 10),
                       min(int(WIRE_M * 10), int(best[2] * 10) + 11)):
        r = evaluate(best[1], run10 / 10.0)
        if r and r[0] > best[0]:
            best = r
    return _sloper(key, label, feed_en, feed_ft,
                   offset(feed_en, best[1], best[2]), note)


def build_sloper_classes():
    out = []

    # -- K: the three trees that are known to exist. Geometry is forced. -----
    for key, label, top_en, note in (
        ("K-BACK", "Sloper to the BACKYARD-corner tree", BACK_EN,
         "Support already exists - no new anchor needed."),
        ("K-FRONT", "Sloper to the FRONT-YARD-corner tree", FRONT_EN,
         "Support already exists - no new anchor needed."),
    ):
        o = _sloper(key, label, (0.0, 0.0), 24.0, top_en, note)
        if o:
            out.append(o)

    # -- C: rotation locked to a yard-corner bearing, distance free. --------
    for key, label, brg, corner in (
        ("C-BACK", "Sloper, rotation locked to the BACKYARD-corner bearing",
         BACK_BRG, "backyard"),
        ("C-FRONT", "Sloper, rotation locked to the FRONT-YARD-corner bearing",
         FRONT_BRG, "front yard"),
    ):
        o = _best_sloper(key, f"{label} ({brg:.0f}T)", (0.0, 0.0), 24.0,
                         [brg], f"Runs over the {corner}.")
        if o:
            out.append(o)
        # The same bearing with the parcel constraint lifted, to show what the
        # boundary is actually costing on that heading.
        ou = _best_sloper(key + "-X", f"{label} ({brg:.0f}T), parcel IGNORED",
                          (0.0, 0.0), 24.0, [brg],
                          "Shows what the boundary costs on this heading.",
                          enforce_parcel=False)
        if ou and abs(ou.supports[1][2][0] - o.supports[1][2][0]) > 1.0:
            out.append(ou)

    # -- G: best buildable sloper, azimuth free. The benchmark. -------------
    every = range(0, 360, 5)
    g1 = _best_sloper("G-FEED", "BEST single-support sloper, existing feed",
                      (0.0, 0.0), 24.0, every,
                      "Azimuth and distance both optimised.")
    if g1:
        out.append(g1)
    g2 = _best_sloper("G-ROOF", "BEST single-support sloper, ROOF feed",
                      ROOF_EN, ROOF_FEED_FT, every,
                      "Requires relocating the transformer to the roof ridge "
                      "and re-routing coax.")
    if g2:
        out.append(g2)

    # -- Roof feed to the tree that already exists. -------------------------
    rf = _sloper("RF-APEX", "Sloper to the APEX tree from a ROOF feed",
                 ROOF_EN, ROOF_FEED_FT, APEX_EN,
                 "Requires relocating the transformer to the roof ridge.")
    if rf:
        out.append(rf)
    return out


TARGET_BEARINGS = {t[0]: great_circle_bearing(FEED[0], FEED[1], t[1], t[2])
                   for t in TARGETS}


def band_nets(opt, band):
    """Per-region net dB on one band, in the normalised (own-peak) convention."""
    return [opt.score(TARGET_BEARINGS[name], arr, band)[2]
            for name, lat, lon, arr in TARGETS]


def aggregate(opt, band="20m"):
    """Single-band aggregate.

    mean_power_dB keeps the historical normalised convention so every 20 m
    figure published earlier still reproduces. mean_power_dBi adds that band's
    peak directivity and is the ONLY one of the two that may be compared
    across bands.
    """
    bd = BAND[band]
    nets = band_nets(opt, band)
    lin = [10 ** (n / 10) for n in nets]
    s = sorted(nets)
    dbi = [n + bd["peak_dBi"] for n in nets]
    return {
        "band": band,
        "mean_power_dB": 10 * math.log10(sum(lin) / len(lin)),
        "mean_power_dBi": 10 * math.log10(sum(lin) / len(lin)) + bd["peak_dBi"],
        "median_dB": s[len(s) // 2],
        "worst_dB": s[0],
        "n_workable": sum(1 for v in dbi if v >= WORKABLE_dBi),
        "n_holes": sum(1 for v in dbi if v < HOLE_dBi),
    }


def aggregate_multiband(opt, bands=None):
    """Aggregate linear power over every (band, region) pair.

    Equal weight per band. This is the ranking metric the operator asked for:
    'aggregate across 40 m and 20 m and the next most popular band ... based on
    linear power to regions'. It is computed on the ABSOLUTE (dBi) scale,
    because the normalised per-band figures deliberately discard the peak-gain
    difference between a 1-lambda and a 3-lambda wire.

    The same trap as the single-band metric applies, only more so: mean linear
    power rewards concentration. Read n_workable (out of bands x regions)
    beside it. See METHOD.md section 7.
    """
    bands = bands or MULTIBAND
    lin, dbi = [], []
    for band in bands:
        g = BAND[band]["peak_dBi"]
        for n in band_nets(opt, band):
            lin.append(10 ** ((n + g) / 10))
            dbi.append(n + g)
    s = sorted(dbi)
    return {
        "bands": list(bands),
        "n_cells": len(dbi),
        "mean_power_dBi": 10 * math.log10(sum(lin) / len(lin)),
        "median_dBi": s[len(s) // 2],
        "worst_dBi": s[0],
        "n_workable": sum(1 for v in dbi if v >= WORKABLE_dBi),
        "n_holes": sum(1 for v in dbi if v < HOLE_dBi),
        # A region counts as covered only if at least one of the three bands
        # gets there. This is the number that matters operationally: you can
        # change band, you cannot change antenna.
        "n_regions_covered": sum(
            1 for i in range(len(TARGETS))
            if max(dbi[j * len(TARGETS) + i] for j in range(len(bands)))
            >= WORKABLE_dBi),
    }


# --------------------------------------------------------------------------
# KML
# --------------------------------------------------------------------------

# KML colours are aabbggrr, not rrggbb.
KML_STYLES = [
    ("optR",  "ff2020ff", 7),   # red            - GARDEN-POST options
    ("optF",  "ff40ff80", 6),   # spring green   - 10 FT FEED family
    ("optG",  "ffffffff", 6),   # white          - ONE-SUPPORT slopers, K/C/G/RF
    ("optT",  "ff0080ff", 6),   # bright orange  - TALL sloper
    ("optA",  "ff00ff00", 5),   # bright green   - recommended flat-top
    ("optV",  "ffffff00", 4),   # cyan           - inverted-V
    ("optS",  "ffff00ff", 4),   # magenta        - short sloper
    ("base",  "ff0000ff", 4),   # red            - baseline
    ("ref",   "ff00ffff", 3),   # yellow         - reference points
    ("parcel", "ff909090", 3),  # grey           - parcel line
    ("ray",   "ff606060", 2),   # dark grey      - bearing rays
]


def kml_style_for(key):
    """Style id for an option key. Checked most-specific first."""
    if key.startswith("RB-"):
        return "optR"
    if key.startswith("F10-"):
        return "optF"
    if key.startswith(("K-", "C-", "G-", "RF-")):
        return "optG"
    if key.startswith("T"):
        return "optT"
    if key == "A":
        return "optA"
    if key == "BASE":
        return "base"
    if key.startswith("V"):
        return "optV"
    return "optS"


def kml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def write_kml(opts, path, ranked=None):
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
         '<name>JYR8010 EFHW deployment options - CN97ap</name>',
         '<description>Every candidate deployment for the 39.6 m EFHW, plus '
         'reference points, parcel line and target bearing rays. '
         'Folders are numbered by three-band rank. '
         'WHITE = ONE-SUPPORT sloper (K = known tree, C = rotation locked to a '
         'yard corner, G = best found by search, RF = roof feed), '
         'ORANGE = tall sloper (T class), GREEN = recommended flat-top, '
         'CYAN = inverted-V, MAGENTA = short sloper, RED = baseline, '
         'YELLOW = operator reference points.</description>']

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

    ranked = ranked or opts
    for o in ranked:
        st = kml_style_for(o.key)
        if not o.supports:
            continue
        m = aggregate_multiband(o)
        rank = ranked.index(o) + 1
        t20 = o.takeoff(LAMBDA_20M)
        t20s = f"{t20:.1f}&#176;" if t20 else "no lobe (peaks at zenith)"
        rows = "".join(
            "<tr><td>%s</td><td align=right>%+.2f dBi</td>"
            "<td align=right>%d/%d</td><td align=right>%.0f ft</td>"
            "<td align=right>%s</td></tr>" % (
                b, aggregate(o, b)["mean_power_dBi"],
                aggregate(o, b)["n_workable"], len(TARGETS),
                o.mean_imax_height(b) / FT,
                (f"{o.peak_elev(b):.0f}&#176;" if o.peak_elev(b) else "zenith"))
            for b in BAND_KEYS)
        deploy = (f"<b>Deployment:</b> {o.n_anchors} elevated anchor"
                  f"{'s' if o.n_anchors != 1 else ''}, highest "
                  f"{o.max_anchor_ft} ft ({o.throw_class} throw)")
        hdr = (f"<b>#{rank} of {len(ranked)}</b> on the 3-band ranking<br/>"
               f"{o.label}<br/>{deploy}<br/>"
               f"Average height {o.avg_h/FT:.1f} ft<br/>"
               f"20 m take-off {t20s}<br/><br/>"
               f"<b>3-band (40/20/15 m): {m['mean_power_dBi']:+.2f} dBi, "
               f"{m['n_workable']}/{m['n_cells']} cells, "
               f"{m['n_regions_covered']}/{len(TARGETS)} regions reachable on at "
               f"least one band</b><br/><br/>"
               f"<table border=1 cellpadding=3><tr><th>band</th><th>agg dBi</th>"
               f"<th>regions</th><th>Imax ht</th><th>peak elev</th></tr>"
               f"{rows}</table>")
        L.append(f'<Folder><name>#{rank} {o.key} - {kml_escape(o.label)}</name>'
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
    print(f"{'key':7s} {'avg ht':>8s} {'Imax ht':>8s} {'slope':>6s} {'20m TO':>7s}"
          f" {'15m TO':>7s} {'legs':>10s}  supports")
    for o in opts:
        # For slant options takeoff() has no closed form; peak_elev() scans the
        # pattern instead. Marked with a leading "~" to keep the two apart.
        def f(band, o=o):
            if o.is_slant:
                return f"~{o.peak_elev(band):.0f}"
            v = o.takeoff(BAND[band]["lam"])
            return f"{v:.1f}" if v else "zenith"
        legs = "/".join(f"{b:.0f}" for b in o.legs)
        sup = ", ".join(f"{n} {h}ft" for n, h, _ in o.supports) or "-"
        sl = f"{o.slope_deg:5.1f}" if o.is_slant else "    -"
        print(f"{o.key:7s} {o.avg_h/FT:7.1f}f {o.mean_imax_height()/FT:7.1f}f "
              f"{sl:>6s} {f('20m'):>7s} {f('15m'):>7s} {legs:>10s}  {sup}")
    print("\nImax ht = mean height of the four 20 m current maxima. This is the")
    print("quantity that actually sets low-angle performance, and it is arithmetic.")

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

    out = [(o, nm, en) for o in opts for nm, h, en in o.supports
           if not inside_parcel(en)]
    print("\n" + "=" * 100)
    print("SUPPORTS THAT ARE NOT ON THE PARCEL  (%d)" % len(out))
    print("=" * 100)
    if not out:
        print("  none")
    for o, nm, en in out:
        d, b = polar(*en)
        # inside_parcel() enforces a 5 m setback. Separate "past the actual
        # boundary" from "on the lot but inside the setback" - they are very
        # different conversations with a neighbour.
        hard = not inside_parcel(en, margin_m=0.0)
        e, n = en
        t = (e - 46.9) / -116.8
        gap = n - (-32.0 + t * 25.2)          # +ve = north of the south line
        where = (f"OFF THE LOT by {-gap:.1f} m ({-gap/FT:.0f} ft)" if hard
                 else f"on the lot, {gap:.1f} m ({gap/FT:.0f} ft) inside the "
                      f"south line - fails the 5 m setback")
        print(f"  {o.key:7s} {nm:12s} {d:6.1f} m ({d/FT:5.1f} ft) at {b:5.1f}T"
              f"   {where}")
    print("\nThe T class is scored WITHOUT a parcel constraint by design, so this")
    print("list is expected to be non-empty. It is printed here because a stale")
    print("'none of them leave the parcel' claim survived a bearing change once.")

    print("\n" + "=" * 100)
    print("BANDS THIS ANTENNA IS RESONANT ON")
    print("=" * 100)
    print(f"{'band':6s} {'MHz':>7s} {'lambda':>8s} {'L/lambda':>9s} {'n':>3s} "
          f"{'lobe from axis':>15s} {'peak dBi':>9s}  in 3-band aggregate")
    for k in BAND_KEYS:
        bd = BAND[k]
        n = bd["n"]
        lobe = min(range(1, 90),
                   key=lambda t: -longwire_field(t, n)) if n > 1 else 90
        print(f"{k:6s} {bd['f']:7.3f} {bd['lam']:7.2f}m {WIRE_M/bd['lam']:9.3f} "
              f"{n:3d} {lobe:14d}d {bd['peak_dBi']:9.2f}  "
              f"{'YES' if bd['mb'] else 'no'}")
    print("\n30m / 17m / 12m are absent because the odd harmonics of a 39.6 m")
    print("wire land at ~10.65 / 17.75 / 24.85 MHz - outside those allocations.")
    print("They need a tuner and are not modelled here.")

    print("\n" + "=" * 100)
    print("PER-REGION NET dB, ALL BANDS (relative to each wire's own peak)")
    print("=" * 100)
    keys = [o.key for o in opts]
    for band in BAND_KEYS:
        print(f"\n--- {band} (lambda {BAND[band]['lam']:.2f} m, n={BAND[band]['n']}, "
              f"peak {BAND[band]['peak_dBi']:+.2f} dBi, arrival x{BAND[band]['arr_scale']}) ---")
        print(f"{'region':18s} {'brg':>5s} {'arr':>5s} "
              + " ".join(f"{k:>7s}" for k in keys))
        for name, lat, lon, arr in TARGETS:
            b = TARGET_BEARINGS[name]
            row = [o.score(b, arr, band)[2] for o in opts]
            print(f"{name:18s} {b:5.0f} {arrival_for_band(arr, band):5.1f} "
                  + " ".join(f"{v:7.1f}" for v in row))

    print("\n" + "=" * 100)
    print("PER-BAND AGGREGATE ACROSS ALL %d REGIONS" % len(TARGETS))
    print("=" * 100)
    for band in BAND_KEYS:
        print(f"\n--- {band} ---")
        print(f"{'key':7s} {'agg dB':>8s} {'agg dBi':>8s} {'median':>8s} "
              f"{'worst':>8s} {'workable':>9s} {'holes':>6s} {'Imax ht':>8s} "
              f"{'peak el':>8s}")
        for o in opts:
            a = aggregate(o, band)
            pe = o.peak_elev(band)
            pes = f"{pe:.0f}d" if pe else "zenith"
            print(f"{o.key:7s} {a['mean_power_dB']:8.2f} {a['mean_power_dBi']:8.2f} "
                  f"{a['median_dB']:8.1f} {a['worst_dB']:8.1f} "
                  f"{a['n_workable']:6d}/{len(TARGETS)} {a['n_holes']:6d} "
                  f"{o.mean_imax_height(band)/FT:7.1f}f {pes:>8s}")

    print("\n" + "=" * 100)
    print("THREE-BAND AGGREGATE (%s) - THE RANKING" % ", ".join(MULTIBAND))
    print("=" * 100)
    ref = aggregate([o for o in opts if o.key == "A"][0])["mean_power_dB"]
    # Sort on SPREAD first, exactly as METHOD.md s7 requires: the count of
    # band x region cells that actually work. Then the number of regions
    # reachable on at least one band, then mean linear power last. Leading
    # with regions-covered would have ranked a sloper above the flat-top on
    # one extra marginal region while it lost on every other measure - the
    # same metric trap that section already documents.
    ranked = sorted(opts, key=lambda o: (
        -aggregate_multiband(o)["n_workable"],
        -aggregate_multiband(o)["n_regions_covered"],
        -aggregate_multiband(o)["mean_power_dBi"]))
    print(f"{'#':>2s} {'key':8s} {'agg dBi':>8s} {'median':>8s} {'worst':>8s} "
          f"{'cells ok':>9s} {'holes':>6s} {'regions':>8s} {'anch':>5s} "
          f"{'highest':>8s} {'throw':>10s}  label")
    prev = None
    for i, o in enumerate(ranked, 1):
        m = aggregate_multiband(o)
        # Mark where the primary key changes. Everything inside one band is
        # tied on the metric the ranking is built on, and the tiebreaks below
        # it are not precise enough to separate them - say so rather than let
        # the row number imply an ordering the model cannot support.
        if prev is not None and m["n_workable"] != prev:
            print(f"   {'-' * 108}")
        prev = m["n_workable"]
        print(f"{i:2d} {o.key:8s} {m['mean_power_dBi']:8.2f} "
              f"{m['median_dBi']:8.1f} {m['worst_dBi']:8.1f} "
              f"{m['n_workable']:5d}/{m['n_cells']:<3d} {m['n_holes']:6d} "
              f"{m['n_regions_covered']:5d}/{len(TARGETS)} {o.n_anchors:5d} "
              f"{o.max_anchor_ft:6d}ft {o.throw_class:>10s}  {o.label}")
    print("\nagg dBi   = 10*log10(mean linear power over %d band x region cells)"
          % (len(MULTIBAND) * len(TARGETS)))
    print("cells ok  = band/region pairs at or above %.1f dBi. PRIMARY SORT KEY."
          % WORKABLE_dBi)
    print("regions   = regions reachable on AT LEAST ONE of the three bands.")
    print("            Second key. You can change band; you cannot change antenna.")
    print("agg dBi is the LAST key, not the first - see METHOD.md section 7.")
    print()
    print("anch      = elevated attachments other than the feed. Each is a")
    print("            separate line over a separate limb.")
    print("highest   = the tallest of them, which is what really sets effort:")
    print("            easy <=55 ft, hard <=90, very hard <=130, climb above.")
    print("            A sloper needs ONE anchor but puts it very high, because")
    print("            a straight 39.6 m wire has rise = sqrt(39.6^2 - run^2).")
    print("            Fewer anchors is NOT automatically less work.")
    print()
    print("Rows between dashed lines are TIED on the primary key. The")
    print("tiebreaks below it cannot separate them at this model's precision -")
    print("read the whole row, not the rank number.")

    # ------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("10 FT FEED CATEGORY - what is available while the feed stays low")
    print("=" * 100)
    f10 = [o for o in opts if o.key.startswith("F10-")]
    a24 = [o for o in opts if o.key == "A"][0]
    ma = aggregate_multiband(a24)
    print(f"{'key':11s} {'agg dBi':>8s} {'cells':>7s} {'regs':>6s} {'worst':>8s}"
          f" {'anch':>5s} {'highest':>8s} {'vs A':>7s}  label")
    for o in sorted(f10, key=lambda o: (-aggregate_multiband(o)["n_workable"],
                                        -aggregate_multiband(o)["mean_power_dBi"])):
        m = aggregate_multiband(o)
        print(f"{o.key:11s} {m['mean_power_dBi']:8.2f} {m['n_workable']:4d}/75 "
              f"{m['n_regions_covered']:4d}/25 {m['worst_dBi']:8.1f} "
              f"{o.n_anchors:5d} {o.max_anchor_ft:6d}ft "
              f"{m['mean_power_dBi']-ma['mean_power_dBi']:+7.2f}  {o.label}")
    print(f"{'A (24 ft)':11s} {ma['mean_power_dBi']:8.2f} {ma['n_workable']:4d}/75 "
          f"{ma['n_regions_covered']:4d}/25 {ma['worst_dBi']:8.1f} "
          f"{a24.n_anchors:5d} {a24.max_anchor_ft:6d}ft {0.0:+7.2f}  "
          f"<-- the 24 ft benchmark")

    best10 = max(f10, key=lambda o: (aggregate_multiband(o)["n_workable"],
                                     aggregate_multiband(o)["mean_power_dBi"]))
    mb = aggregate_multiband(best10)
    print(f"\nBEST WITH A 10 FT FEED: {best10.key} - {best10.label}")
    print(f"  {mb['mean_power_dBi']:+.2f} dBi, {mb['n_workable']}/75 cells, "
          f"{mb['n_regions_covered']}/25 regions, worst {mb['worst_dBi']:.1f}")
    print(f"  Cost of the 10 ft feed versus option A at 24 ft: "
          f"{mb['mean_power_dBi']-ma['mean_power_dBi']:+.2f} dB, "
          f"{mb['n_workable']-ma['n_workable']:+d} cells")
    print("  Per band, dBi:")
    for b in BAND_KEYS:
        x, y = aggregate(best10, b), aggregate(a24, b)
        print(f"    {b:4s} {x['mean_power_dBi']:+6.2f} ({x['n_workable']:2d}/25)"
              f"   vs A {y['mean_power_dBi']:+6.2f} ({y['n_workable']:2d}/25)"
              f"   {x['mean_power_dBi']-y['mean_power_dBi']:+6.2f}")
    print("\nThe feed is a voltage maximum - a current NULL - so its own height")
    print("costs little directly. What costs is that it drags the first part of")
    print("the wire down with it, and on a flat-top that is where two of the")
    print("four 20 m current maxima live.")

    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

    with open(os.path.join(data, "option-comparison.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write("# Per-region net dB on 20 m. Generated by tools/compare_options.py.\n")
        fh.write("# net = long-wire pattern (best leg) + ground-reflection response at\n")
        fh.write("# the terrain-adjusted arrival angle. See METHOD.md for confidence.\n")
        fh.write("# 20 m ONLY, kept for continuity. For every band see\n")
        fh.write("# option-comparison-multiband.csv.\n")
        fh.write("region,bearing_true_deg," + ",".join(keys) + "\n")
        for name, lat, lon, arr in TARGETS:
            b = TARGET_BEARINGS[name]
            fh.write(f"{name},{b:.1f}," +
                     ",".join(f"{o.score(b, arr, '20m')[2]:.1f}" for o in opts) + "\n")

    with open(os.path.join(data, "option-comparison-multiband.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write("# Per-region net dB for EVERY resonant band. Long format.\n")
        fh.write("# net_dB  = relative to that wire's own peak lobe (historical\n")
        fh.write("#           convention; comparable ACROSS OPTIONS on one band).\n")
        fh.write("# To compare ACROSS BANDS add the band's peak_dBi:\n")
        fh.write("#   " + "  ".join(f"{k}={BAND[k]['peak_dBi']:+.2f}"
                                    for k in BAND_KEYS) + "\n")
        fh.write("# arrival_deg is the 20 m arrival angle scaled by the band's\n")
        fh.write("# arrival multiplier - a rule of thumb, LOW confidence.\n")
        fh.write("# 30m/17m/12m are not harmonics of a 39.6 m wire and are absent.\n")
        fh.write("band,freq_MHz,n_half_waves,region,bearing_true_deg,arrival_deg,"
                 + ",".join(keys) + "\n")
        for band in BAND_KEYS:
            bd = BAND[band]
            for name, lat, lon, arr in TARGETS:
                b = TARGET_BEARINGS[name]
                fh.write(f"{band},{bd['f']:.3f},{bd['n']},{name},{b:.1f},"
                         f"{arrival_for_band(arr, band):.1f}," +
                         ",".join(f"{o.score(b, arr, band)[2]:.1f}" for o in opts)
                         + "\n")

    with open(os.path.join(data, "option-band-aggregate.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write("# Aggregate per option per band, across all 25 regions.\n")
        fh.write("# aggregate_dB  = normalised to the wire's own peak (compare options\n")
        fh.write("#                 within one band only).\n")
        fh.write("# aggregate_dBi = aggregate_dB + band peak directivity. THIS is the\n")
        fh.write("#                 one to compare across bands.\n")
        fh.write("# n_workable counts regions at or above %.1f dBi; holes below %.1f.\n"
                 % (WORKABLE_dBi, HOLE_dBi))
        fh.write("# mean_imax_height_ft is band-specific: the current maxima move with\n")
        fh.write("# the harmonic number. Pure arithmetic, HIGH confidence.\n")
        fh.write("# peak_elev_deg: ground-reflection lobe for flat options; for slant\n")
        fh.write("# options a numeric scan of the slant model (METHOD.md s9, LOW).\n")
        fh.write("key,band,freq_MHz,n_half_waves,aggregate_dB,aggregate_dBi,"
                 "median_dB,worst_dB,n_workable,n_holes,mean_imax_height_ft,"
                 "peak_elev_deg,label\n")
        for o in opts:
            for band in BAND_KEYS:
                a = aggregate(o, band)
                pe = o.peak_elev(band)
                pes = f"{pe:.0f}" if pe else "zenith"
                fh.write(f"{o.key},{band},{BAND[band]['f']:.3f},{BAND[band]['n']},"
                         f"{a['mean_power_dB']:.2f},{a['mean_power_dBi']:.2f},"
                         f"{a['median_dB']:.1f},{a['worst_dB']:.1f},"
                         f"{a['n_workable']},{a['n_holes']},"
                         f"{o.mean_imax_height(band)/FT:.1f},{pes},"
                         f"\"{o.label}\"\n")

    with open(os.path.join(data, "option-aggregate.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write("# Headline table. 20 m single-band columns plus the three-band\n")
        fh.write("# aggregate the ranking is built on.\n")
        fh.write("# aggregate_dB = 10*log10(mean linear power). NOTE: this metric\n")
        fh.write("# rewards concentrating power into a few bearings, so a spiky\n")
        fh.write("# straight wire can score near a broad one. Read it alongside\n")
        fh.write("# n_workable and n_holes, which capture spread.\n")
        fh.write("# mb3_* columns aggregate 40m + 20m + 15m on the ABSOLUTE (dBi)\n")
        fh.write("# scale over 75 band x region cells. mb3_regions_covered counts\n")
        fh.write("# regions reachable on at least ONE of the three - that is the\n")
        fh.write("# primary sort key, then mb3_workable, then mb3_aggregate_dBi.\n")
        fh.write("# takeoff 'slant' = slope > 30 deg, modelled as a slant radiator\n")
        fh.write("# (METHOD.md s9, LOW confidence) - not a horizontal-wire lobe.\n")
        fh.write("# 'zenith' = h < lambda/4, so no distinct lobe exists.\n")
        fh.write("# mean_imax_height_ft = mean height of the four 20 m current maxima.\n")
        fh.write("# That column is pure arithmetic and HIGH confidence; prefer it.\n")
        fh.write("# n_anchors / max_anchor_ft / throw_class describe DEPLOYMENT\n")
        fh.write("# effort, not performance. A sloper needs one anchor but puts\n")
        fh.write("# it very high; fewer anchors is not automatically less work.\n")
        fh.write("# in_parcel is false when any support falls outside the lot or\n")
        fh.write("# inside the 5 m setback - see the parcel block in stdout.\n")
        fh.write("mb3_rank,key,avg_height_ft,mean_imax_height_ft,slope_deg,"
                 "takeoff_20m_deg,takeoff_15m_deg,legs_true_deg,"
                 "n_anchors,max_anchor_ft,throw_class,in_parcel,"
                 "aggregate_dB,median_dB,worst_dB,n_workable,n_holes,delta_vs_A_dB,"
                 "mb3_aggregate_dBi,mb3_median_dBi,mb3_worst_dBi,mb3_workable_of_75,"
                 "mb3_holes,mb3_regions_covered,label\n")
        for o in opts:
            a = aggregate(o)
            m = aggregate_multiband(o)
            t20, t15 = o.takeoff(21.19), o.takeoff(14.14)
            if o.is_slant:
                # "~NN" = scanned peak of the slant model, not a closed-form
                # ground-reflection lobe. Different quantity, marked as such.
                s20 = f"~{o.peak_elev('20m'):.0f}"
                s15 = f"~{o.peak_elev('15m'):.0f}"
            else:
                s20 = f"{t20:.1f}" if t20 else "zenith"
                s15 = f"{t15:.1f}" if t15 else "zenith"
            legs = "/".join(f"{b:.0f}" for b in o.legs)
            ok = all(inside_parcel(en) for _, _, en in o.supports) \
                if o.supports else True
            fh.write(f"{ranked.index(o)+1},{o.key},{o.avg_h/FT:.1f},"
                     f"{o.mean_imax_height()/FT:.1f},"
                     f"{o.slope_deg:.0f},{s20},{s15},{legs},"
                     f"{o.n_anchors},{o.max_anchor_ft},{o.throw_class},"
                     f"{'yes' if ok else 'no'},"
                     f"{a['mean_power_dB']:.2f},{a['median_dB']:.1f},"
                     f"{a['worst_dB']:.1f},{a['n_workable']},{a['n_holes']},"
                     f"{a['mean_power_dB']-ref:+.1f},"
                     f"{m['mean_power_dBi']:.2f},{m['median_dBi']:.1f},"
                     f"{m['worst_dBi']:.1f},{m['n_workable']},{m['n_holes']},"
                     f"{m['n_regions_covered']},\"{o.label}\"\n")

    out = os.path.join(data, "deployment-options.kml")
    print("\nWrote option-comparison.csv, option-comparison-multiband.csv,")
    print("      option-band-aggregate.csv, option-aggregate.csv")
    print("KML written to", os.path.normpath(write_kml(opts, out, ranked)))


if __name__ == "__main__":
    main()
