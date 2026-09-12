#!/usr/bin/env python3
"""NEC-2 scoring for the CN97ap study, via PyNEC.

Every analytic score in compare_options.py / topology_search.py is a shortcut:
a closed-form long-wire pattern, a closed-form ground factor, and (for steep
or L-shaped wires) the section 9 slant model. This module replaces all of them
with a method-of-moments solution of the actual wire over real ground, and
scores it exactly the way the study scores anything: gain toward each of the
25 regions at that band's terrain-adjusted arrival angle, then cells, regions
and mean power.

What NEC does NOT know, and nothing here pretends it does:
  - trees, the house, gutters, house wiring - free space plus a flat ground
  - the terrain beyond the arrival-angle adjustment the study already uses
  - the JYR8010 transformer itself (a 1 m counterpoise stands in for the
    transformer case and coax shield at the feed)

Model choices (each is checked for sensitivity in nec_validate.py):
  wire        39.6 m, radius 0.89 mm (2.5 mm^2). A straight polyline through
              the option's supports; if that is shorter than 39.6 m the slack
              is hung as a sag point in the longest span.
  segments    lambda/20 at the modelled frequency.
  ground      NEC "finite ground, reflection-coefficient" (GN 0) at the
              study's average ground, eps_r 13, sigma 5 mS/m. Sommerfeld (GN 2)
              agrees to ~0.3 dB at these heights and is ~50% slower.
  frequency   each band is modelled at the 39.6 m wire's own free-space
              harmonic resonance (RES_MHZ), not at the band frequency: the
              bare wire resonates ~6% low in NEC, while the real antenna was
              measured resonant in-band. Modelling at resonance gives the wire
              exactly n half-waves, which is what sets the pattern.
  threshold   WORKABLE_NEC_dBi = study threshold + 6.02 dB. The study's dBi
              scale normalises the ground factor to 0 dB at its peak; a real
              NEC gain includes the up-to-6.02 dB ground reflection.

Standard library + PyNEC + multiprocessing.
"""

import math
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compare_options as C          # noqa: E402

C0 = 299.792458
FT = 0.3048
WIRE_R = 0.00089
EPS_R, SIGMA = 13.0, 0.005
SEG_PER_LAMBDA = 20
COUNTERPOISE_M = 1.0
GROUND_TYPE = 0                      # 0 reflection-coefficient, 2 Sommerfeld
WORKABLE_NEC_dBi = C.WORKABLE_dBi + 6.02
HOLE_NEC_dBi = C.HOLE_dBi + 6.02

# Free-space harmonic resonances of a straight 39.6 m, 0.89 mm wire with the
# same 1 m counterpoise feed, written by nec_validate.py (peak of R near each
# harmonic - NOT peak |Z|, which runs away to low frequency on an end-fed
# wire and gave wrong answers on the first try).
HERE = os.path.dirname(os.path.abspath(__file__))
RES_FILE = os.path.join(HERE, "..", "data", "nec-resonances.json")


def model_freqs(policy="resonant"):
    if policy == "band" or not os.path.exists(RES_FILE):
        if policy != "band":
            print("nec_engine: no data/nec-resonances.json - run nec_validate.py; "
                  "using band frequencies")
        return {b: C.BAND[b]["f"] for b in C.BAND_KEYS}
    import json
    with open(RES_FILE, encoding="utf-8") as fh:
        return {k: float(v) for k, v in json.load(fh)["with_counterpoise"].items()}


def targets():
    """[(name, bearing_T, {band: elevation_deg})] - the study's own angles."""
    out = []
    for name, lat, lon, arr in C.TARGETS:
        brg = C.TARGET_BEARINGS[name]
        hz, sl = C.terrain_at(brg)
        out.append((name, brg, {b: max(1.0, max(C.arrival_for_band(arr, b), hz)
                                       + sl) for b in C.BAND_KEYS}))
    return out


TARGETS = targets()


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def polyline(o, wire=C.WIRE_M):
    """The option's supports as a 3-D polyline 39.6 m long.

    Shorter: hang the slack as a sag point mid-way along the longest span.
    Longer (construction round-off): pull the last point back along its span.
    """
    pts = [(en[0], en[1], h * FT) for _, h, en in o.supports]
    dedup = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, dedup[-1]) > 0.01:
            dedup.append(p)
    pts = dedup

    def length(ps):
        return sum(math.dist(ps[i], ps[i + 1]) for i in range(len(ps) - 1))

    total = length(pts)
    if total < wire - 0.05:
        i = max(range(len(pts) - 1), key=lambda k: math.dist(pts[k], pts[k + 1]))
        a, b = pts[i], pts[i + 1]
        L = math.dist(a, b)
        d = math.sqrt(((L + wire - total) / 2) ** 2 - (L / 2) ** 2)
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2,
             max((a[2] + b[2]) / 2 - d, 0.5))
        pts = pts[:i + 1] + [m] + pts[i + 1:]
    elif total > wire + 0.05:
        a, b = pts[-2], pts[-1]
        L = math.dist(a, b)
        keep = max(L - (total - wire), 0.05) / L
        pts[-1] = tuple(a[k] + (b[k] - a[k]) * keep for k in range(3))
    return tuple(tuple(round(v, 3) for v in p) for p in pts)


# --------------------------------------------------------------------------
# Solver
# --------------------------------------------------------------------------

def _build(pts, freq, gtype=GROUND_TYPE, seg_per_lambda=SEG_PER_LAMBDA,
           counterpoise=COUNTERPOISE_M):
    import PyNEC as P
    c = P.nec_context()
    g = c.get_geometry()
    lam = C0 / freq
    fp = pts[0]
    dx, dy = pts[1][0] - fp[0], pts[1][1] - fp[1]
    d = math.hypot(dx, dy)
    ux, uy = (dx / d, dy / d) if d > 1e-6 else (1.0, 0.0)
    cpe = (fp[0] - ux * counterpoise, fp[1] - uy * counterpoise, fp[2])
    g.wire(1, 1, *cpe, *fp, WIRE_R, 1.0, 1.0)
    tag = 1
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.dist(a, b)
        tag += 1
        g.wire(tag, max(1, math.ceil(L / (lam / seg_per_lambda))), *a, *b,
               WIRE_R, 1.0, 1.0)
    c.geometry_complete(0)
    if gtype is None:
        c.gn_card(-1, 0, 0, 0, 0, 0, 0, 0)
    else:
        c.gn_card(gtype, 0, EPS_R, SIGMA, 0, 0, 0, 0)
    c.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    c.fr_card(0, 1, freq, 0)
    return c


def gains(pts, freqs, bands=None, gtype=GROUND_TYPE,
          seg_per_lambda=SEG_PER_LAMBDA, counterpoise=COUNTERPOISE_M):
    """{band: [gain dBi toward each target]} for one polyline."""
    bands = bands or list(freqs)
    out = {}
    for b in bands:
        c = _build(pts, freqs[b], gtype, seg_per_lambda, counterpoise)
        row = []
        for k, (_, brg, el) in enumerate(TARGETS):
            c.rp_card(0, 1, 1, 0, 5, 0, 0, 90.0 - el[b], 90.0 - brg, 0, 0, 0, 0)
            row.append(float(c.get_radiation_pattern(k).get_gain()[0, 0]))
        out[b] = row
    return out


def _job(args):
    pts, freqs, bands, kw = args
    return gains(pts, freqs, bands, **kw)


def gains_many(polys, freqs, bands=None, procs=30, **kw):
    """Parallel gains() over many polylines, order preserved."""
    bands = bands or list(freqs)
    jobs = [(p, freqs, bands, kw) for p in polys]
    if len(jobs) < 8:
        return [_job(j) for j in jobs]
    with Pool(procs) as pool:
        return pool.map(_job, jobs, chunksize=max(1, len(jobs) // (procs * 8)))


# --------------------------------------------------------------------------
# Scoring - identical rules to compare_options.aggregate_multiband
# --------------------------------------------------------------------------

def aggregate(g, bands, threshold=None):
    thr = WORKABLE_NEC_dBi if threshold is None else threshold
    vals = [v for b in bands for v in g[b]]
    lin = [10 ** (v / 10) for v in vals]
    s = sorted(vals)
    n = len(TARGETS)
    return {
        "mean_power_dBi": 10 * math.log10(sum(lin) / len(lin)),
        "median_dBi": s[len(s) // 2],
        "worst_dBi": s[0],
        "n_workable": sum(1 for v in vals if v >= thr),
        "n_holes": sum(1 for v in vals if v < HOLE_NEC_dBi),
        "n_regions_covered": sum(1 for i in range(n)
                                 if max(g[b][i] for b in bands) >= thr),
        "n_cells": len(vals),
    }


def rank_key(g, bands, threshold=None):
    m = aggregate(g, bands, threshold)
    return (m["n_workable"], m["n_regions_covered"], m["mean_power_dBi"])
