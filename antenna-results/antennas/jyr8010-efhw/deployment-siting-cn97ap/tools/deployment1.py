#!/usr/bin/env python3
"""Deployment 1 - build detail for the top NEC wire.

The exhaustive roof-sloper scan's overall winner (tools/nec_roof_sloper_scan.py):
a straight 39.6 m wire from the roof feed point up to a support at ~148.5 deg
magnetic. Chosen by the operator 2026-09-12 knowing the support lands on the
neighbouring parcel.

Computes every number needed to set it out and hang it, runs NEC-2 on the
exact geometry for patterns and expected resonances, and draws the diagrams:

  imagery/deployment1_plan.png         plan on the aerial, dimensioned
  imagery/deployment1_elevation.png    side elevation + end view, dimensioned
  imagery/deployment1_iso.png          two 3-D views
  imagery/deployment1_eyelevel.png     three perspective views from the ground
  imagery/deployment1_currents.png     current and voltage along the wire, all bands
  imagery/deployment1_patterns.png     NEC azimuth and elevation patterns
  imagery/deployment1_tolerance.png    score vs attachment height and bearing

and writes data/deployment1.json for the page.

Run from the repository root:

    python .../tools/deployment1.py
"""

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                                   # noqa: E402
import matplotlib                                    # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
from PIL import Image                                # noqa: E402
import compare_options as C                          # noqa: E402
import nec_engine as N                               # noqa: E402
import canopy_from_ortho as K                        # noqa: E402
from site_geometry import (polar, offset, mag, to_latlon, dms, to_enu,   # noqa: E402
                           APEX, BACKYARD, FRONT_YARD)

FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
IMG = os.path.join(HERE, "..", "imagery")

with open(os.path.join(DATA, "nec-roof-sloper-scan.json"), encoding="utf-8") as fh:
    SCAN = json.load(fh)
WIN = next(w["wire"] for w in SCAN["winners"]
           if w["metric"] == "3band" and w["category"] == "overall")
STRESS = next(r for r in SCAN["stress"]["rows"] if r["category"] == "overall")

F3 = tuple(WIN["poly"][0])
E3 = tuple(WIN["poly"][1])
FEED_EN, END_EN = F3[:2], E3[:2]
L = math.dist(F3, E3)
RUN, BRG = polar(END_EN[0] - FEED_EN[0], END_EN[1] - FEED_EN[1])
RISE = E3[2] - F3[2]
SLOPE = math.degrees(math.atan2(RISE, RUN))
FEED_FT, END_FT = F3[2] / FT, E3[2] / FT
U = ((END_EN[0] - FEED_EN[0]) / RUN, (END_EN[1] - FEED_EN[1]) / RUN)   # ground unit

PAL = {"wire": "#d95926", "blue": "#2a78d6", "aqua": "#1baf7a", "ink": "#0b0b0b",
       "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "base": "#c3c2b7",
       "surface": "#fcfcfb", "tree": "#6b5a3e", "canopy": "#37704f"}
plt.rcParams.update({
    "font.size": 9.5, "axes.edgecolor": PAL["base"], "axes.labelcolor": PAL["ink2"],
    "xtick.color": PAL["ink2"], "ytick.color": PAL["ink2"], "text.color": PAL["ink"],
    "figure.facecolor": PAL["surface"], "axes.facecolor": PAL["surface"],
    "savefig.dpi": 170, "axes.grid": False, "legend.frameon": False})


def at(s):
    """3-D point (m) at wire distance s from the feed."""
    t = s / L
    return tuple(F3[k] + (E3[k] - F3[k]) * t for k in range(3))


def south_gap(e, n):
    t = (e - 46.9) / -116.8
    return n - (-32.0 + t * 25.2)


def perp_to_south_line(e, n):
    d = (-116.8, 25.2)
    nn = (d[1], -d[0])
    ln = math.hypot(*nn)
    return ((e - 46.9) * nn[0] + (n + 32.0) * nn[1]) / ln   # +ve = north of line


def fmt_ftin(m):
    inches = m / FT * 12
    ft = int(inches // 12)
    return f"{ft} ft {inches - ft * 12:.0f} in"


def ll(en):
    la, lo = to_latlon(*en)
    a, b = dms(la, lo)
    return {"lat": round(la, 7), "lon": round(lo, 7), "dms": f"{a} {b}"}


# --------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------

def geometry():
    g = {"wire_m": round(L, 3), "wire_ft": round(L / FT, 1),
         "run_m": round(RUN, 3), "run_ft": round(RUN / FT, 1), "run_ftin": fmt_ftin(RUN),
         "bearing_true": round(BRG, 2), "bearing_mag": round(mag(BRG), 2),
         "back_bearing_mag": round(mag((BRG + 180) % 360), 2),
         "rise_m": round(RISE, 3), "rise_ft": round(RISE / FT, 1),
         "slope_deg": round(SLOPE, 2), "feed_ft": round(FEED_FT, 1),
         "end_ft": round(END_FT, 1), "feed": ll(FEED_EN), "end": ll(END_EN)}
    td, tb = polar(*FEED_EN)
    g["feed_from_transformer"] = {"ft": round(td / FT, 1), "mag": round(mag(tb), 1),
                                  "true": round(tb, 1)}
    marks = []
    for name, en in (("transformer (NE house corner)", (0.0, 0.0)),
                     ("backyard corner (SE house corner)", to_enu(BACKYARD)),
                     ("apex tree", to_enu(APEX)),
                     ("front-yard corner", to_enu(FRONT_YARD))):
        d, b = polar(END_EN[0] - en[0], END_EN[1] - en[1])
        marks.append({"from": name, "to": "support tree", "ft": round(d / FT, 1),
                      "ftin": fmt_ftin(d), "mag": round(mag(b), 1), "true": round(b, 1)})
    # parcel crossing along the ground track
    lo_, hi_ = 0.0, 1.0
    cross = None
    if south_gap(*FEED_EN) > 0 > south_gap(*END_EN):
        for _ in range(60):
            mid = (lo_ + hi_) / 2
            p = (FEED_EN[0] + U[0] * RUN * mid, FEED_EN[1] + U[1] * RUN * mid)
            if south_gap(*p) > 0:
                lo_ = mid
            else:
                hi_ = mid
        s_h = RUN * lo_
        p = (FEED_EN[0] + U[0] * s_h, FEED_EN[1] + U[1] * s_h)
        z = F3[2] + RISE * lo_
        cd, cb = polar(*p)
        cross = {"horizontal_ft_from_feed": round(s_h / FT, 1),
                 "wire_ft_from_feed": round(s_h / RUN * L / FT, 1),
                 "wire_height_ft": round(z / FT, 1),
                 "beyond_line_along_track_ft": round((RUN - s_h) / FT, 1),
                 "from_transformer": {"ft": round(cd / FT, 1), "mag": round(mag(cb), 1)},
                 **ll(p)}
        marks.append({"from": "transformer (NE house corner)", "to": "property-line crossing",
                      "ft": round(cd / FT, 1), "ftin": fmt_ftin(cd), "mag": round(mag(cb), 1),
                      "true": round(cb, 1)})
    g["crossing"] = cross
    g["support_perp_past_line_ft"] = round(-perp_to_south_line(*END_EN) / FT, 1)
    g["support_north_gap_ft"] = round(-south_gap(*END_EN) / FT, 1)
    g["marks"] = marks
    return g


def stations():
    out = []
    for hft in list(range(0, int(RUN / FT) + 1, 10)) + [round(RUN / FT, 1)]:
        s_h = hft * FT
        t = min(s_h / RUN, 1.0)
        p = (FEED_EN[0] + U[0] * RUN * t, FEED_EN[1] + U[1] * RUN * t)
        d, b = polar(*p)
        out.append({"horizontal_ft": hft, "wire_ft": round(t * L / FT, 1),
                    "height_ft": round((F3[2] + RISE * t) / FT, 1),
                    "from_transformer_ft": round(d / FT, 1),
                    "from_transformer_mag": round(mag(b), 1),
                    "past_line": south_gap(*p) < 0})
    return out


def maxima():
    out = {}
    for b in C.BAND_KEYS:
        n = C.BAND[b]["n"]
        imax = [(2 * k + 1) * L / (2 * n) for k in range(n)]
        vmax = [j * L / n for j in range(n + 1)]

        def row(s):
            p = at(s)
            d, br = polar(p[0], p[1])
            return {"wire_ft": round(s / FT, 1), "horizontal_ft": round(s / L * RUN / FT, 1),
                    "height_ft": round(p[2] / FT, 1), "past_line": south_gap(p[0], p[1]) < 0}
        out[b] = {"n": n, "current_max": [row(s) for s in imax],
                  "voltage_max": [row(s) for s in vmax]}
    return out


def slack_table():
    out = []
    for pct in (0.0, 1.0, 2.0, 3.0):
        chord = L / (1 + pct / 100)
        run = math.sqrt(max(chord ** 2 - RISE ** 2, 0))
        sag = chord * math.sqrt(3 * (L / chord - 1) / 8) if pct else 0.0
        e = offset(FEED_EN, BRG, run)
        d, b = polar(*e)
        out.append({"slack_pct": pct, "slack_ft": round((L - chord) / FT, 1),
                    "run_ft": round(run / FT, 1), "moves_in_ft": round((RUN - run) / FT, 1),
                    "mid_sag_ft": round(sag / FT, 1),
                    "support_from_transformer_ft": round(d / FT, 1),
                    "support_from_transformer_mag": round(mag(b), 1)})
    return out


def canopy():
    im, ppm, cen = K.load("close")
    mask = K.canopy_mask(im)
    prof = K.profile_along(mask, ppm, cen, im.size, FEED_EN, END_EN)
    sampled = prof[-1][0] if prof else 0.0
    return {"fraction": round(sum(v for _, v in prof) / max(len(prof), 1), 3),
            "sampled_ft": round(sampled / FT, 1), "track_ft": round(RUN / FT, 1),
            "enters_canopy_ft": (None if K.first_run(prof, True) is None
                                 else round(K.first_run(prof, True) / FT, 1))}


def tolerance():
    rows = [r for r in csv.DictReader(
        ln for ln in open(os.path.join(DATA, "nec-roof-sloper-grid.csv"), encoding="utf-8")
        if not ln.startswith("#")) if r["dir"] == "up" and r["roof_ft"] == "25"]
    # The 1 deg grid bearing nearest the winner carries the full height range;
    # the winner's own fractional bearing has only the local refinement rows.
    grid_brg = float(round(WIN["brg"]))
    along = sorted((r for r in rows if abs(float(r["brg_true"]) - grid_brg) < 0.01),
                   key=lambda r: float(r["run_m"]))
    across = sorted((r for r in rows if abs(float(r["run_m"]) - WIN["run"]) < 0.026),
                    key=lambda r: float(r["brg_mag"]))       # magnetic wraps; sort on it
    return {"along_bearing": [{"run_ft": round(float(r["run_m"]) / FT, 1),
                               "attach_ft": float(r["end_ft"]), "cells": int(r["cells3"]),
                               "dBi": float(r["dBi3"]), "on_lot": r["on_lot"] == "1"}
                              for r in along],
            "across_bearing": [{"brg_mag": float(r["brg_mag"]), "cells": int(r["cells3"]),
                                "dBi": float(r["dBi3"])} for r in across]}


def nec_detail():
    freqs = N.model_freqs()
    poly = (F3, E3)
    g = N.gains(poly, freqs, C.BAND_KEYS)
    bands = {}
    for b in C.BAND_KEYS:
        m = N.aggregate(g, [b])
        bands[b] = {"cells": m["n_workable"], "regions": m["n_regions_covered"],
                    "mean_dBi": round(m["mean_power_dBi"], 2), "worst": round(m["worst_dBi"], 1),
                    "median": round(m["median_dBi"], 1)}
    pats, res = {}, {}
    for b in C.BAND_KEYS:
        f = freqs[b]
        c = N._build(poly, f)
        az = {}
        for k, el in enumerate((10, 25)):
            c.rp_card(0, 1, 360, 0, 5, 0, 0, 90 - el, 0, 0, 1, 0, 0)
            gg = c.get_radiation_pattern(k).get_gain()[0]
            az[el] = [float(gg[int(round((90 - brg) % 360)) % 360]) for brg in range(360)]
        best_brg = int(np.argmax(az[10]))
        c.rp_card(0, 91, 1, 0, 5, 0, 0, 0, (90 - best_brg) % 360, 1, 0, 0, 0)
        el_best = [float(v) for v in c.get_radiation_pattern(2).get_gain()[:, 0]][::-1]
        c.rp_card(0, 91, 1, 0, 5, 0, 0, 0, (90 - BRG) % 360, 1, 0, 0, 0)
        el_axis = [float(v) for v in c.get_radiation_pattern(3).get_gain()[:, 0]][::-1]
        z = c.get_input_parameters(0).get_impedance()[0]
        pats[b] = {"az_el10": az[10], "az_el25": az[25], "best_bearing_true": best_brg,
                   "el_cut_best": el_best, "el_cut_along_wire": el_axis,
                   "Z": [round(z.real), round(z.imag)]}
        best = None
        for i in range(81):
            ff = f * (0.95 + 0.00125 * i)
            cz = N._build(poly, ff)
            cz.rp_card(0, 1, 1, 0, 5, 0, 0, 90, 0, 0, 0, 0, 0)
            r = cz.get_input_parameters(0).get_impedance()[0].real
            if best is None or r > best[0]:
                best = (r, ff)
        res[b] = {"model_MHz": round(best[1], 3), "R_peak_ohm": round(best[0]),
                  "scaled_to_measured_MHz": round(best[1] * 3.6056 /
                                                  json.load(open(os.path.join(
                                                      DATA, "nec-resonances.json")))[
                                                      "with_counterpoise"]["80m"], 3),
                  "band_MHz": C.BAND[b]["f"]}
    regions = [{"name": t[0], "bearing_true": round(t[1], 1),
                "bearing_mag": round(mag(t[1]), 1),
                **{b: round(g[b][i], 1) for b in C.BAND_KEYS}}
               for i, t in enumerate(N.TARGETS)]
    return g, bands, pats, res, regions


# --------------------------------------------------------------------------
# Diagrams
# --------------------------------------------------------------------------

def _save(fig, name):
    path = os.path.join(IMG, name)
    fig.savefig(path, bbox_inches="tight", facecolor=PAL["surface"])
    plt.close(fig)
    print("  wrote", os.path.normpath(path))
    return name


def plan(geo):
    im = Image.open(os.path.join(IMG, "kc2025_wide.jpg")).convert("RGB")
    half = 100.0 / FT
    fig, ax = plt.subplots(figsize=(8.6, 9.2))
    ax.imshow(im, extent=[-half, half, -half, half], origin="upper", zorder=0)
    fx, fy = FEED_EN[0] / FT, FEED_EN[1] / FT
    ex, ey = END_EN[0] / FT, END_EN[1] / FT
    xs = [0, fx, ex]
    ys = [0, fy, ey]
    pad = 45
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    # parcel
    for a, b in (((-69.9, -6.8), (46.9, -32.0)), ((46.9, -32.0), (53.5, 99.2))):
        ax.plot([a[0] / FT, b[0] / FT], [a[1] / FT, b[1] / FT], color="white", lw=2,
                ls=(0, (6, 4)), zorder=2)
    ax.text(fx - 60, (-32.0 + ((fx * FT - 46.9) / -116.8) * 25.2) / FT + 4,
            "south property line", color="white", fontsize=9, rotation=-12,
            path_effects=_halo(), zorder=6)
    # coax route: transformer -> along the wall -> under the roof feed
    ax.plot([0, fx], [0, fy], color="white", lw=1.6, ls=(0, (2, 3)), zorder=3)
    ax.text(fx / 2 + 3, fy / 2 + 3, f"coax to roof feed\n{geo['feed_from_transformer']['ft']:.0f} ft "
            f"@ {geo['feed_from_transformer']['mag']:.0f}°M", color="white", fontsize=8.5,
            path_effects=_halo(), zorder=6)
    # wire track
    ax.plot([fx, ex], [fy, ey], color="black", lw=7, alpha=.55, zorder=4,
            solid_capstyle="round")
    ax.plot([fx, ex], [fy, ey], color=PAL["wire"], lw=3.6, zorder=5, solid_capstyle="round")
    # 20 m current maxima
    for r in MAX["20m"]["current_max"]:
        t = r["horizontal_ft"] * FT / RUN
        px, py = fx + (ex - fx) * t, fy + (ey - fy) * t
        ax.scatter([px], [py], s=36, color=PAL["blue"], edgecolor="white", lw=1.2, zorder=7)
        ax.text(px + 5, py + 1, f"{r['height_ft']:.0f} ft", color="white", fontsize=8,
                path_effects=_halo(), zorder=8)
    # markers
    ax.scatter([0], [0], s=90, color="white", edgecolor="black", lw=2, zorder=8)
    ax.text(4, 4, "transformer now\n(NE house corner)", color="white", fontsize=8.5,
            path_effects=_halo(), zorder=8)
    ax.scatter([fx], [fy], s=110, marker="s", color="white", edgecolor="black", lw=2, zorder=8)
    ax.text(fx - 6, fy + 6, f"ROOF FEED\n{FEED_FT:.0f} ft (assumed)", color="white",
            fontsize=9, ha="right", fontweight="bold", path_effects=_halo(), zorder=8)
    ax.scatter([ex], [ey], s=150, color=PAL["wire"], edgecolor="white", lw=2.2, zorder=8)
    ax.text(ex + 7, ey - 2, f"SUPPORT TREE\nattach {END_FT:.0f} ft\n{geo['end']['dms']}",
            color="white", fontsize=9, fontweight="bold", path_effects=_halo(), zorder=8)
    if geo["crossing"]:
        c = geo["crossing"]
        t = c["horizontal_ft_from_feed"] * FT / RUN
        cx, cy = fx + (ex - fx) * t, fy + (ey - fy) * t
        ax.scatter([cx], [cy], s=120, marker="X", color="white", edgecolor="black", lw=1.2,
                   zorder=9)
        ax.text(cx + 7, cy + 3, f"crosses the line\nwire {c['wire_height_ft']:.0f} ft up",
                color="white", fontsize=8.5, path_effects=_halo(), zorder=9)
    # dimension line offset to the left of the wire
    nx, ny = -U[1], U[0]
    off = 30
    ax.annotate("", xy=(ex + nx * off, ey + ny * off), xytext=(fx + nx * off, fy + ny * off),
                arrowprops=dict(arrowstyle="<->", color="white", lw=1.4), zorder=6)
    mx, my = (fx + ex) / 2 + nx * (off + 7), (fy + ey) / 2 + ny * (off + 7)
    ax.text(mx, my, f"{geo['run_ftin']} horizontal\n{geo['bearing_mag']:.1f}°M "
            f"({geo['bearing_true']:.1f}°T)", color="white", fontsize=9.5, ha="center",
            va="center", rotation=math.degrees(math.atan2(ey - fy, ex - fx)) + 180,
            fontweight="bold", path_effects=_halo(), zorder=7)
    # north arrows + scale
    x0 = ax.get_xlim()[1] - 22
    y0 = ax.get_ylim()[1] - 50
    ax.annotate("", xy=(x0, y0 + 36), xytext=(x0, y0), arrowprops=dict(
        arrowstyle="-|>", color="white", lw=2), zorder=9)
    ax.text(x0, y0 + 40, "N true", color="white", ha="center", fontsize=8.5,
            path_effects=_halo(), zorder=9)
    dm = math.radians(-15.3)
    ax.annotate("", xy=(x0 + 36 * math.sin(dm), y0 + 36 * math.cos(dm)), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color="#ffd166", lw=1.6), zorder=9)
    ax.text(x0 - 16, y0 + 30, "N mag", color="#ffd166", ha="center", fontsize=8,
            path_effects=_halo(), zorder=9)
    sx, sy = ax.get_xlim()[0] + 10, ax.get_ylim()[0] + 10
    ax.plot([sx, sx + 50], [sy, sy], color="white", lw=3, zorder=9)
    ax.text(sx, sy + 4, "50 ft", color="white", fontsize=9, path_effects=_halo(), zorder=9)
    ax.set_xlabel("feet east of the transformer")
    ax.set_ylabel("feet north of the transformer")
    ax.set_aspect("equal")
    return _save(fig, "deployment1_plan.png")


def _halo():
    import matplotlib.patheffects as pe
    return [pe.withStroke(linewidth=2.6, foreground="black")]


def elevation(geo):
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.6),
                                  gridspec_kw={"width_ratios": [5.2, 1]})
    run_ft = RUN / FT
    ax.axhline(0, color=PAL["ink2"], lw=1.2)
    ax.fill_between([-12, run_ft + 18], -3, 0, color=PAL["grid"], zorder=0)
    # roof-feed stub and tree
    ax.plot([0, 0], [0, FEED_FT], color=PAL["base"], lw=6, solid_capstyle="butt")
    ax.text(-2, FEED_FT / 2, "house wall / roof\n(outline not surveyed)", ha="right",
            va="center", fontsize=8, color=PAL["muted"])
    ax.plot([run_ft + 3, run_ft + 3], [0, END_FT + 14], color=PAL["tree"], lw=5)
    ax.text(run_ft + 7, END_FT + 12, "support tree\nlimb ≥ %.0f ft\n(unverified)" % END_FT,
            fontsize=8, color=PAL["tree"], va="top")
    # halyard, pulley, counterweight
    ax.plot([run_ft, run_ft + 3], [END_FT, END_FT + 2], color=PAL["ink2"], lw=1)
    ax.scatter([run_ft + 3], [END_FT + 2], s=26, color="white", edgecolor=PAL["ink2"], zorder=5)
    ax.plot([run_ft + 3.6, run_ft + 3.6], [END_FT + 2, 6], color=PAL["ink2"], lw=1)
    ax.add_patch(plt.Rectangle((run_ft + 2.4, 2.5), 2.4, 3.5, color=PAL["ink2"]))
    ax.text(run_ft + 5.5, 4, "counterweight\n5–10 lb", fontsize=7.5, color=PAL["ink2"],
            va="center")
    # wire
    ax.plot([0, run_ft], [FEED_FT, END_FT], color=PAL["wire"], lw=3, zorder=4)
    ax.scatter([0], [FEED_FT], marker="s", s=60, color="white", edgecolor=PAL["ink"], zorder=6)
    ax.scatter([run_ft], [END_FT], s=60, color=PAL["wire"], edgecolor=PAL["ink"], zorder=6)
    ax.text(4, FEED_FT - 4, f"feed {FEED_FT:.0f} ft · 1:64 transformer\n~700 V RMS at 150 W",
            fontsize=8, va="top")
    ax.text(run_ft - 3, END_FT + 3, "2 ceramic eggs in series\n~1 kV RMS", fontsize=8,
            ha="right", va="bottom")
    # 20 m current maxima + 15 m
    for b, col, dy in (("20m", PAL["blue"], -6), ("15m", PAL["aqua"], 6)):
        for r in MAX[b]["current_max"]:
            ax.scatter([r["horizontal_ft"]], [r["height_ft"]], s=26, color=col,
                       edgecolor="white", lw=1, zorder=7)
    for r in MAX["20m"]["current_max"]:
        ax.text(r["horizontal_ft"], r["height_ft"] - 5, f"{r['height_ft']:.0f}", fontsize=7.5,
                color=PAL["blue"], ha="center", va="top")
    # property line
    if geo["crossing"]:
        cx = geo["crossing"]["horizontal_ft_from_feed"]
        ax.axvline(cx, color=PAL["ink2"], ls=(0, (5, 4)), lw=1)
        ax.text(cx + 1.5, 2, f"property line\n{cx:.0f} ft out · wire {geo['crossing']['wire_height_ft']:.0f} ft up",
                fontsize=7.5, color=PAL["ink2"])
    # dimensions
    ax.annotate("", xy=(run_ft, -9), xytext=(0, -9),
                arrowprops=dict(arrowstyle="<->", color=PAL["ink"], lw=1))
    ax.text(run_ft / 2, -12, f"{geo['run_ftin']} horizontal", ha="center", va="top", fontsize=9)
    ax.annotate("", xy=(run_ft + 16, END_FT), xytext=(run_ft + 16, FEED_FT),
                arrowprops=dict(arrowstyle="<->", color=PAL["ink"], lw=1))
    ax.text(run_ft + 18, (END_FT + FEED_FT) / 2, f"rise\n{RISE / FT:.1f} ft", fontsize=8.5,
            va="center")
    arc = np.linspace(0, math.radians(SLOPE), 30)
    ax.plot(22 * np.cos(arc), FEED_FT + 22 * np.sin(arc), color=PAL["ink"], lw=.8)
    ax.plot([0, 26], [FEED_FT, FEED_FT], color=PAL["ink"], lw=.6, ls=":")
    ax.text(25, FEED_FT + 3.5, f"{SLOPE:.1f}°", fontsize=9)
    ax.text(run_ft * .45, FEED_FT + RISE / FT * .45 + 11, f"{L / FT:.0f} ft of wire, straight",
            rotation=math.degrees(math.atan2(RISE / FT, run_ft)), fontsize=9, color=PAL["wire"],
            ha="center")
    ax.scatter([], [], s=26, color=PAL["blue"], label="20 m current maxima (height ft)")
    ax.scatter([], [], s=26, color=PAL["aqua"], label="15 m current maxima")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_xlim(-30, run_ft + 40)
    ax.set_ylim(-18, END_FT + 22)
    ax.set_aspect("equal")
    ax.set_xlabel(f"feet from the roof feed along {geo['bearing_mag']:.1f}°M")
    ax.set_ylabel("height above ground, ft")
    ax.set_title("Side elevation, looking at the wire from its left (true scale)", loc="left",
                 fontsize=10)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    # end view: looking along the wire from behind the feed
    ax2.axhline(0, color=PAL["ink2"], lw=1.2)
    ax2.plot([0, 0], [FEED_FT, END_FT], color=PAL["wire"], lw=3)
    ax2.scatter([0], [FEED_FT], marker="s", s=50, color="white", edgecolor=PAL["ink"], zorder=5)
    ax2.scatter([0], [END_FT], s=50, color=PAL["wire"], edgecolor=PAL["ink"], zorder=5)
    ax2.text(2, FEED_FT, f"feed {FEED_FT:.0f} ft", fontsize=8, va="center")
    ax2.text(2, END_FT, f"far end {END_FT:.0f} ft", fontsize=8, va="center")
    ax2.set_xlim(-15, 15)
    ax2.set_ylim(-18, END_FT + 22)
    ax2.set_aspect("equal")
    ax2.set_xticks([-10, 0, 10])
    ax2.set_title(f"End view, looking\n{geo['bearing_mag']:.0f}°M from behind the feed",
                  fontsize=9, loc="left")
    for spine in ("top", "right"):
        ax2.spines[spine].set_visible(False)
    return _save(fig, "deployment1_elevation.png")


def iso(geo):
    fig = plt.figure(figsize=(11, 5.4))
    for k, (azim, title) in enumerate(((-58, "From the south-west"), (125, "From the north-east"))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        xs = np.array([0, FEED_EN[0], END_EN[0]]) / FT
        ys = np.array([0, FEED_EN[1], END_EN[1]]) / FT
        x0, x1 = xs.min() - 25, xs.max() + 25
        y0, y1 = ys.min() - 25, ys.max() + 25
        for gx in np.arange(math.floor(x0 / 20) * 20, x1 + 1, 20):
            ax.plot([gx, gx], [y0, y1], [0, 0], color=PAL["grid"], lw=.6)
        for gy in np.arange(math.floor(y0 / 20) * 20, y1 + 1, 20):
            ax.plot([x0, x1], [gy, gy], [0, 0], color=PAL["grid"], lw=.6)
        # property line on the ground
        pl = np.array([(-69.9, -6.8), (46.9, -32.0)]) / FT
        tt = np.linspace(0, 1, 50)
        px = pl[0, 0] + (pl[1, 0] - pl[0, 0]) * tt
        py = pl[0, 1] + (pl[1, 1] - pl[0, 1]) * tt
        keep = (px > x0) & (px < x1) & (py > y0) & (py < y1)
        ax.plot(px[keep], py[keep], 0, color=PAL["ink2"], ls="--", lw=1.2)
        fx, fy, ex, ey = FEED_EN[0] / FT, FEED_EN[1] / FT, END_EN[0] / FT, END_EN[1] / FT
        ax.plot([fx, ex], [fy, ey], [FEED_FT, END_FT], color=PAL["wire"], lw=3)
        ax.plot([fx, ex], [fy, ey], [0, 0], color=PAL["wire"], lw=1, alpha=.4)
        ax.plot([fx, fx], [fy, fy], [0, FEED_FT], color=PAL["base"], lw=4)
        ax.plot([ex, ex], [ey, ey], [0, END_FT + 12], color=PAL["tree"], lw=4)
        ax.plot([0, fx, fx], [0, fy, fy], [0.5, 0.5, FEED_FT], color=PAL["ink2"], lw=1, ls=":")
        ax.scatter([0], [0], [0], s=30, color="white", edgecolor=PAL["ink"])
        ax.scatter([fx], [fy], [FEED_FT], s=40, marker="s", color="white", edgecolor=PAL["ink"])
        ax.scatter([ex], [ey], [END_FT], s=40, color=PAL["wire"], edgecolor=PAL["ink"])
        for r in MAX["20m"]["current_max"]:
            t = r["horizontal_ft"] * FT / RUN
            ax.plot([fx + (ex - fx) * t] * 2, [fy + (ey - fy) * t] * 2, [0, r["height_ft"]],
                    color=PAL["blue"], lw=.7, ls=":")
        ax.text(fx, fy, FEED_FT + 6, "roof feed", fontsize=8)
        ax.text(ex, ey, END_FT + 16, "support tree", fontsize=8)
        ax.text(0, 0, 4, "transformer now", fontsize=7.5, color=PAL["ink2"])
        ax.text(px[keep][len(px[keep]) // 3], py[keep][len(py[keep]) // 3], 2,
                "property line", fontsize=7.5, color=PAL["ink2"])
        ax.set_box_aspect((x1 - x0, y1 - y0, END_FT + 20))
        ax.set_zlim(0, END_FT + 20)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.view_init(elev=20, azim=azim)
        ax.set_xlabel("ft east", fontsize=8)
        ax.set_ylabel("ft north", fontsize=8)
        ax.set_zlabel("ft up", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_title(title + " · true scale · dotted = 20 m current maxima", fontsize=9.5)
        ax.xaxis.pane.set_facecolor(PAL["surface"])
        ax.yaxis.pane.set_facecolor(PAL["surface"])
        ax.zaxis.pane.set_facecolor(PAL["surface"])
    return _save(fig, "deployment1_iso.png")


def eyelevel(geo):
    eye = 5.6 * FT
    cross = geo["crossing"]
    t_cross = cross["horizontal_ft_from_feed"] * FT / RUN if cross else 0.6
    views = [
        ("Beside the house under the feed, facing the support",
         (FEED_EN[0] - U[0] * 4, FEED_EN[1] - U[1] * 4), BRG),
        ("At the property line, facing back to the house",
         (FEED_EN[0] + U[0] * RUN * t_cross + U[1] * 3, FEED_EN[1] + U[1] * RUN * t_cross - U[0] * 3),
         (BRG + 180) % 360),
        ("At the support tree, facing back up the wire",
         (END_EN[0] + U[0] * 3, END_EN[1] + U[1] * 3), (BRG + 180) % 360),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
    for ax, (title, obs, look) in zip(axes, views):
        az = math.radians(look)
        fwd = (math.sin(az), math.cos(az))
        rgt = (math.cos(az), -math.sin(az))
        f = 1 / math.tan(math.radians(40))

        def proj(e, n, z):
            d = (e - obs[0], n - obs[1], z - eye)
            depth = d[0] * fwd[0] + d[1] * fwd[1]
            if depth <= 0.4:
                return None
            return ((d[0] * rgt[0] + d[1] * rgt[1]) / depth * f, d[2] / depth * f)
        ax.axhspan(-1, 0, color="#dcdccb")
        ax.axhspan(0, 1.2, color="#dfe6ea")
        ax.axhline(0, color=PAL["base"], lw=1)
        for gd in range(5, 60, 5):
            pts = [proj(obs[0] + fwd[0] * gd + rgt[0] * w, obs[1] + fwd[1] * gd + rgt[1] * w, 0)
                   for w in (-60, 60)]
            if all(pts):
                ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]], color=PAL["base"], lw=.4)
        seg = [proj(*at(s)) for s in np.linspace(0, L, 120)]
        seg = [p for p in seg if p]
        if seg:
            ax.plot([p[0] for p in seg], [p[1] for p in seg], color=PAL["wire"], lw=2.4)
        for name, p3, base in (("feed", F3, (F3[0], F3[1], 0)), ("support", E3, (E3[0], E3[1], 0))):
            a, b = proj(*p3), proj(*base)
            # Points outside the frame drew labels far off-axis and blew up
            # the figure on the first render; only mark what is in view.
            if a and b and -1 <= a[0] <= 1 and -.55 <= a[1] <= 1.0:
                ax.plot([a[0], b[0]], [a[1], b[1]], color=PAL["muted"], lw=1, ls=":")
                ax.scatter([a[0]], [a[1]], s=28, color=PAL["wire"] if name == "support" else "white",
                           edgecolor=PAL["ink"], zorder=5)
                ax.text(a[0], a[1] + .05, f"{name} {p3[2] / FT:.0f} ft", fontsize=8,
                        ha="center", va="bottom")
        pl = [proj(e, n, 0) for e, n in
              [(-69.9 + (46.9 + 69.9) * t, -6.8 + (-32.0 + 6.8) * t) for t in np.linspace(0, 1, 80)]]
        pl = [p for p in pl if p and abs(p[0]) < 1.5]
        if len(pl) > 1:
            ax.plot([p[0] for p in pl], [p[1] for p in pl], color=PAL["ink2"], ls="--", lw=1)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-.55, 1.1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{title}\nfacing {mag(look):.0f}°M · eye 5 ft 7 in · 80° wide", fontsize=9,
                     loc="left")
        for sp in ax.spines.values():
            sp.set_color(PAL["base"])
    return _save(fig, "deployment1_eyelevel.png")


def currents():
    fig, axes = plt.subplots(5, 1, figsize=(10, 7.2), sharex=True)
    s = np.linspace(0, L, 400)
    for ax, b in zip(axes, C.BAND_KEYS):
        n = C.BAND[b]["n"]
        i = np.abs(np.sin(n * math.pi * s / L))
        ax.fill_between(s / FT, 0, i, color=PAL["blue"], alpha=.25, lw=0)
        ax.plot(s / FT, i, color=PAL["blue"], lw=1.6)
        ax.plot(s / FT, np.abs(np.cos(n * math.pi * s / L)), color=PAL["wire"], lw=1, ls="--")
        for r in MAX[b]["current_max"]:
            ax.text(r["wire_ft"], 1.05, f"{r['height_ft']:.0f} ft", fontsize=7.5, ha="center",
                    va="bottom", color=PAL["blue"])
        ax.set_ylim(0, 1.45)
        ax.set_yticks([])
        ax.text(-2, .5, b.replace("m", " m"), ha="right", va="center", fontsize=10,
                fontweight="bold")
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        if MAX["20m"] and geometry_cache["crossing"]:
            ax.axvline(geometry_cache["crossing"]["wire_ft_from_feed"], color=PAL["ink2"],
                       lw=.8, ls=":")
    axes[0].plot([], [], color=PAL["blue"], label="current (radiates) · labels = height of each maximum")
    axes[0].plot([], [], color=PAL["wire"], ls="--", label="voltage (insulate here)")
    axes[0].legend(loc="upper right", fontsize=8, ncol=2, bbox_to_anchor=(1, 1.55))
    axes[-1].set_xlabel("feet of wire from the feed · dotted line = property-line crossing")
    return _save(fig, "deployment1_currents.png")


def patterns(pats):
    fig = plt.figure(figsize=(12, 8.4))
    bands = ["40m", "20m", "15m"]
    keyreg = {"Central Europe": "EU", "Moscow": "UA", "Japan": "JA", "Australia VK2": "VK2",
              "US Northeast": "W1", "Caribbean": "KP4", "South America": "LU",
              "Alaska": "KL7", "Hawaii": "KH6", "India": "VU", "SoCal": "W6"}
    for k, b in enumerate(bands):
        ax = fig.add_subplot(2, 3, k + 1, projection="polar")
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        th = np.radians(np.arange(361) + 0.0)
        for key, col, lab in (("az_el10", PAL["blue"], "10° elevation"),
                              ("az_el25", PAL["wire"], "25° elevation")):
            v = np.clip(np.array(pats[b][key] + [pats[b][key][0]]), -20, 12)
            ax.plot(th, v, color=col, lw=1.6, label=lab)
        ax.set_ylim(-20, 12)
        ax.set_yticks([-10, 0, 10])
        ax.set_yticklabels(["−10", "0", "+10 dBi"], fontsize=7, color=PAL["muted"])
        ax.grid(color=PAL["grid"], lw=.6)
        wb = math.radians(BRG)
        for a in (wb, wb + math.pi):
            ax.plot([a, a], [-20, 12], color=PAL["ink2"], lw=.8, ls=":")
        for name, brg, el in N.TARGETS:
            if name in keyreg:
                ax.text(math.radians(brg), 15.5, keyreg[name], fontsize=7, ha="center",
                        va="center", color=PAL["ink2"])
        ax.set_xticks(np.radians([0, 90, 180, 270]))
        ax.set_xticklabels(["N", "E", "S", "W"], fontsize=8)
        ax.set_title(f"{b.replace('m', ' m')} · azimuth (true) · dotted = wire axis", fontsize=9.5,
                     pad=18)
        if k == 0:
            ax.legend(loc="lower left", fontsize=7.5, bbox_to_anchor=(-.25, -.2))
        ax2 = fig.add_subplot(2, 3, k + 4)
        el = np.arange(91)
        ax2.plot(el, np.clip(pats[b]["el_cut_best"], -30, 12), color=PAL["blue"], lw=1.6,
                 label=f"toward {mag(pats[b]['best_bearing_true']):.0f}°M (strongest at 10°)")
        ax2.plot(el, np.clip(pats[b]["el_cut_along_wire"], -30, 12), color=PAL["wire"], lw=1.2,
                 ls="--", label=f"along the wire, {mag(BRG):.0f}°M")
        ax2.axhline(N.WORKABLE_NEC_dBi, color=PAL["muted"], lw=.8, ls=":")
        ax2.text(88, N.WORKABLE_NEC_dBi + .6, "workable", fontsize=7, ha="right",
                 color=PAL["muted"])
        ax2.set_xlim(0, 90)
        ax2.set_ylim(-30, 12)
        ax2.set_xlabel("elevation angle, degrees")
        if k == 0:
            ax2.set_ylabel("gain, dBi")
        ax2.grid(color=PAL["grid"], lw=.5)
        ax2.legend(fontsize=7.5, loc="lower center")
        for sp in ("top", "right"):
            ax2.spines[sp].set_visible(False)
    fig.suptitle("NEC-2 patterns over average ground · exact deployment geometry", x=.01,
                 ha="left", fontsize=11)
    fig.tight_layout()
    return _save(fig, "deployment1_patterns.png")


def tolerance_plot(tol):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.6))
    al = tol["along_bearing"]
    a1.plot([r["attach_ft"] for r in al], [r["cells"] for r in al], color=PAL["blue"], lw=1.6)
    a1.scatter([END_FT], [WIN["m3"]["n_workable"]], s=40, color=PAL["wire"], zorder=5)
    a1.set_xlabel(f"attachment height at {mag(BRG):.1f}°M, ft (the support moves along the bearing)")
    a1.set_ylabel("workable cells of 75")
    a1.grid(color=PAL["grid"], lw=.5)
    ac = tol["across_bearing"]
    a2.plot([r["brg_mag"] for r in ac], [r["cells"] for r in ac], color=PAL["blue"], lw=1.6)
    a2.scatter([mag(BRG)], [WIN["m3"]["n_workable"]], s=40, color=PAL["wire"], zorder=5)
    a2.axvspan(mag(BRG) - 2, mag(BRG) + 2, color=PAL["grid"], alpha=.6, lw=0)
    a2.set_xlim(mag(BRG) - 25, mag(BRG) + 25)
    a2.set_xlabel(f"bearing, °M, support {RUN / FT:.0f} ft out (shaded ±2°)")
    a2.grid(color=PAL["grid"], lw=.5)
    for ax in (a1, a2):
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    return _save(fig, "deployment1_tolerance.png")


def main():
    global MAX, geometry_cache
    geo = geometry()
    geometry_cache = geo
    MAX = maxima()
    print("computing NEC detail ...")
    g, bands, pats, res, regions = nec_detail()
    tol = tolerance()
    can = canopy()
    files = [plan(geo), elevation(geo), iso(geo), eyelevel(geo), currents(), patterns(pats),
             tolerance_plot(tol)]
    out = {"generated_by": "tools/deployment1.py", "geometry": geo, "stations": stations(),
           "maxima": MAX, "slack": slack_table(), "canopy": can, "tolerance": tol,
           "nec_bands": bands, "nec_3band": WIN["m3"], "nec_40_20": WIN["m2"],
           "resonance": res, "impedance": {b: pats[b]["Z"] for b in pats},
           "regions": regions, "stress": STRESS,
           "robust": {"nbr_mean": WIN["nbr_mean"], "nbr_min": WIN["nbr_min"],
                      "thr_minus2": WIN["c3_lo"], "thr_plus2": WIN["c3_hi"]},
           "rank_among_103": WIN.get("rank_among_103"), "files": files,
           "workable_nec_dBi": N.WORKABLE_NEC_dBi}
    with open(os.path.join(DATA, "deployment1.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: out[k] for k in ("geometry", "canopy", "nec_bands", "resonance",
                                          "slack")}, indent=1))


MAX = None
geometry_cache = None

if __name__ == "__main__":
    main()
