#!/usr/bin/env python3
"""Every straight sloper off the roof point, on NEC-2 - exhaustively.

A straight 39.6 m sloper from a fixed feed has exactly two free parameters:
the bearing and the horizontal run to its far end. The run fixes the far
end's height (rise = sqrt(39.6^2 - run^2)), up or down. So the whole design
space is a 2-D sheet per feed height, and it can be covered completely:

  1. FULL GRID at the assumed 25 ft roof height: every 1 deg of bearing x
     every 0.25 m of run, sloping UP (to the 150 ft tree cap) and DOWN (to an
     8 ft minimum end). ~44k wires, NEC on 40/20/15 m.
  2. REFINE the best seeds of every category to 0.25 deg x 0.05 m.
  3. CATEGORIES, on both rankings (40+20+15 m and 40+20 m): overall; on the
     lot; on the lot and clear of the 5 m setback; on the lot by attachment
     height (throw class); sloping down.
  4. ROBUSTNESS: each grid point's neighbourhood mean of workable cells over
     +/-2 deg and +/-0.5 m. A winner that is a lone spike is flagged; the most
     robust point of each category is reported beside the sharpest.
  5. STRESS TEST the winners against the 50 best distinct candidates under
     every NEC modelling change nec_validate.py checks, plus roof heights of
     20 and 30 ft and the workable threshold +/-2 dB.
  6. HEIGHT: full 2 deg x 0.5 m grids at 20 and 30 ft.

Run from the repository root (a few minutes on 32 cores):

    python .../tools/nec_roof_sloper_scan.py

Writes ../data/nec-roof-sloper-scan.json, ../data/nec-roof-sloper-grid.csv and
../imagery/nec_roof_sloper_landscape.png.
"""

import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                   # noqa: E402
from PIL import Image                # noqa: E402
import compare_options as C          # noqa: E402
import topology_search as T          # noqa: E402
import nec_engine as N               # noqa: E402
from site_geometry import offset, mag, to_latlon, dms   # noqa: E402

FT = 0.3048
W = C.WIRE_M
B3, B2 = ["40m", "20m", "15m"], ["40m", "20m"]
FREQS = N.model_freqs()
ROOF_EN, ROOF_FT = T.ROOF_FEED
THR = N.WORKABLE_NEC_dBi
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
IMGDIR = os.path.join(HERE, "..", "imagery")
T0 = time.time()


def say(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


# --------------------------------------------------------------------------
# Geometry and scoring
# --------------------------------------------------------------------------

def run_limits(fft):
    """(min run going up under the 150 ft cap, min run going down to 8 ft)."""
    up_min = math.sqrt(max(W * W - ((C.TREE_MAX_FT - fft) * FT) ** 2, 0.0))
    down_min = (math.sqrt(max(W * W - ((fft - T.L_BOTTOM_FT) * FT) ** 2, 0.0))
                if fft - T.L_BOTTOM_FT > 0 else None)
    return up_min, down_min


def make(fft, brg, run, direction):
    brg %= 360.0
    if not 0 < run < W:
        return None
    d = math.sqrt(W * W - run * run)
    z_end = fft * FT + (d if direction == "up" else -d)
    if direction == "up" and z_end / FT > C.TREE_MAX_FT + 1e-6:
        return None
    if direction == "down" and z_end / FT < T.L_BOTTOM_FT - 1e-6:
        return None
    e = offset(ROOF_EN, brg, run)
    return {"fft": fft, "brg": round(brg, 4), "run": round(run, 4), "dir": direction,
            "poly": ((round(ROOF_EN[0], 4), round(ROOF_EN[1], 4), round(fft * FT, 4)),
                     (round(e[0], 4), round(e[1], 4), round(z_end, 4)))}


def score(cands, freqs=None, **kw):
    todo = [c for c in cands if "g" not in c]
    if todo:
        res = N.gains_many([c["poly"] for c in todo], freqs or FREQS, B3, **kw)
        for c, g in zip(todo, res):
            c["g"] = g
    for c in cands:
        enrich(c)
    return cands


def south_gap(en):
    t = (en[0] - 46.9) / -116.8
    return en[1] - (-32.0 + t * 25.2)


def enrich(c):
    m3, m2 = N.aggregate(c["g"], B3), N.aggregate(c["g"], B2)
    c["m3"], c["m2"] = m3, m2
    c["k3"] = (m3["n_workable"], m3["n_regions_covered"], round(m3["mean_power_dBi"], 4))
    c["k2"] = (m2["n_workable"], m2["n_regions_covered"], round(m2["mean_power_dBi"], 4))
    c["c3_lo"] = N.aggregate(c["g"], B3, THR - 2)["n_workable"]
    c["c3_hi"] = N.aggregate(c["g"], B3, THR + 2)["n_workable"]
    end = c["poly"][1]
    c["end_en"] = (end[0], end[1])
    c["end_ft"] = end[2] / FT
    c["attach_ft"] = max(c["end_ft"], 0.0) if c["dir"] == "up" else c["fft"]
    c["slope"] = math.degrees(math.atan2(abs(end[2] - c["fft"] * FT), c["run"]))
    c["on_lot"] = C.inside_parcel(c["end_en"], 0.0)
    c["setback_ok"] = C.inside_parcel(c["end_en"])
    gap = south_gap(c["end_en"])
    c["parcel"] = ("on the lot, clear of the setback" if c["setback_ok"] else
                   "on the lot, inside the 5 m setback" if c["on_lot"] else
                   f"end {-gap/FT:.0f} ft past the south line" if gap < 0 else
                   "end past the east line")


CATS = [
    ("overall", lambda c: True),
    ("on the lot", lambda c: c["on_lot"]),
    ("on the lot, clear of the setback", lambda c: c["setback_ok"]),
    ("on the lot, attachment <= 55 ft (easy throw)",
     lambda c: c["on_lot"] and c["attach_ft"] <= 55.5),
    ("on the lot, attachment <= 70 ft", lambda c: c["on_lot"] and c["attach_ft"] <= 70.5),
    ("on the lot, attachment <= 90 ft (hard throw)",
     lambda c: c["on_lot"] and c["attach_ft"] <= 90.5),
    ("sloping down off the roof", lambda c: c["dir"] == "down"),
]


def distinct(pool, key, pred, n, sep_brg=6.0, sep_run=2.0):
    out = []
    for c in sorted((c for c in pool if pred(c)), key=key, reverse=True):
        if all(c["dir"] != o["dir"] or
               min(abs(c["brg"] - o["brg"]), 360 - abs(c["brg"] - o["brg"])) >= sep_brg or
               abs(c["run"] - o["run"]) >= sep_run for o in out):
            out.append(c)
        if len(out) == n:
            break
    return out


# --------------------------------------------------------------------------
# Stages
# --------------------------------------------------------------------------

def full_grid(fft, dbrg, drun, drun_down):
    up_min, down_min = run_limits(fft)
    runs_up = np.arange(math.ceil(up_min / drun) * drun, 39.5 + 1e-9, drun)
    brgs = np.arange(0.0, 360.0, dbrg)
    up = [[make(fft, b, r, "up") for r in runs_up] for b in brgs]
    down = []
    if down_min is not None and fft >= T.DOWN_MIN_FEED_FT:
        runs_dn = np.arange(math.ceil(down_min / drun_down) * drun_down, W - 0.02, drun_down)
        down = [make(fft, b, r, "down") for b in brgs for r in runs_dn]
    flat = [c for row in up for c in row if c] + [c for c in down if c]
    say(f"{fft:.0f} ft grid: {len(brgs)} bearings x {len(runs_up)} runs up + "
        f"{len(down)} down = {len(flat)} wires")
    score(flat)
    return {"brgs": brgs, "runs_up": runs_up, "up": up, "down": [c for c in down if c],
            "all": flat}


def neighbourhood(grid, half_b=2, half_r=2):
    """Mean and min of 3-band workable cells over +/-half steps, bearing wraps."""
    nb, nr = len(grid["brgs"]), len(grid["runs_up"])
    cells = np.full((nb, nr), np.nan)
    for i in range(nb):
        for j in range(nr):
            c = grid["up"][i][j]
            if c:
                cells[i, j] = c["m3"]["n_workable"]
    mean = np.full_like(cells, np.nan)
    mn = np.full_like(cells, np.nan)
    for i in range(nb):
        rows = [(i + d) % nb for d in range(-half_b, half_b + 1)]
        for j in range(nr):
            if np.isnan(cells[i, j]):
                continue
            blk = cells[np.ix_(rows, range(max(0, j - half_r), min(nr, j + half_r + 1)))]
            mean[i, j] = np.nanmean(blk)
            mn[i, j] = np.nanmin(blk)
    for i in range(nb):
        for j in range(nr):
            c = grid["up"][i][j]
            if c:
                c["nbr_mean"], c["nbr_min"] = float(mean[i, j]), float(mn[i, j])
    return cells, mean


def refine(pool, fft):
    seeds = []
    for key in (lambda c: c["k3"], lambda c: c["k2"]):
        for _, pred in CATS:
            seeds += distinct(pool, key, pred, 8)
    seen, fine = set(), []
    for s in seeds:
        if (s["brg"], s["run"], s["dir"]) in seen:
            continue
        seen.add((s["brg"], s["run"], s["dir"]))
        dr = (np.arange(-0.25, 0.2501, 0.05) if s["dir"] == "up"
              else np.arange(-0.05, 0.0501, 0.01))
        for db in np.arange(-1.0, 1.001, 0.25):
            for d in dr:
                c = make(fft, s["brg"] + db, s["run"] + d, s["dir"])
                if c:
                    fine.append(c)
    uniq = {c["poly"]: c for c in fine}
    have = {c["poly"] for c in pool}
    new = [c for p, c in uniq.items() if p not in have]
    say(f"refining {len(seeds)} seeds: {len(new)} new wires at 0.25 deg x 0.05 m")
    score(new)
    return pool + new


def winners(pool):
    out = []
    for metric, key in (("3band", lambda c: c["k3"]), ("40+20", lambda c: c["k2"])):
        for name, pred in CATS:
            best = distinct(pool, key, pred, 1)
            if best:
                out.append({"metric": metric, "category": name, "wire": best[0]})
    return out


def stress(pool, wins, n=50):
    cands = distinct(pool, lambda c: c["k3"], lambda c: True, n // 2)
    cands += distinct(pool, lambda c: c["k3"], lambda c: c["on_lot"], n // 2)
    for w in wins:
        cands.append(w["wire"])
    cands = list({c["poly"]: c for c in cands}.values())
    variants = [("baseline", {}), ("Sommerfeld ground", {"gtype": 2}),
                ("lambda/40 segments", {"seg_per_lambda": 40}),
                ("0.5 m counterpoise", {"counterpoise": 0.5}),
                ("2.0 m counterpoise", {"counterpoise": 2.0}),
                ("band frequencies", {"freqs": N.model_freqs("band")})]
    say(f"stress test: {len(cands)} candidates x {len(variants) + 4} variants")
    table = {}
    for name, kw in variants:
        if name == "baseline":
            keys = [c["k3"] for c in cands]
        else:
            freqs = kw.pop("freqs", None)
            res = N.gains_many([c["poly"] for c in cands], freqs or FREQS, B3, **kw)
            keys = [(lambda m: (m["n_workable"], m["n_regions_covered"],
                                m["mean_power_dBi"]))(N.aggregate(g, B3)) for g in res]
        table[name] = keys
    for name, fft in (("roof 20 ft", 20.0), ("roof 30 ft", 30.0)):
        alt = [make(fft, c["brg"], c["run"], c["dir"]) for c in cands]
        ok = [a for a in alt if a]
        res = N.gains_many([a["poly"] for a in ok], FREQS, B3)
        it = iter(res)
        keys = []
        for a in alt:
            if a:
                m = N.aggregate(next(it), B3)
                keys.append((m["n_workable"], m["n_regions_covered"], m["mean_power_dBi"]))
            else:
                keys.append((-1, 0, -99.0))
        table[name] = keys
    for name, thr in (("threshold -2 dB", THR - 2), ("threshold +2 dB", THR + 2)):
        table[name] = [(lambda m: (m["n_workable"], m["n_regions_covered"],
                                   m["mean_power_dBi"]))(N.aggregate(c["g"], B3, thr))
                       for c in cands]
    out = []
    for w in wins:
        if w["metric"] != "3band":
            continue
        i = cands.index(w["wire"])
        row = {"category": w["category"]}
        for name, keys in table.items():
            row[name] = {"rank": 1 + sum(1 for k in keys if k > keys[i]),
                         "cells": keys[i][0]}
        out.append(row)
    return {"n_candidates": len(cands), "rows": out}


def landscape(grid, mean, path):
    """Workable cells over bearing (magnetic) x attachment height, 25 ft roof."""
    brgs, runs = grid["brgs"], grid["runs_up"]
    nr = len(runs)
    cells = np.full((len(brgs), nr), np.nan)
    lot = np.zeros((len(brgs), nr), dtype=bool)
    for i in range(len(brgs)):
        for j in range(nr):
            c = grid["up"][i][j]
            if c:
                cells[i, j] = c["m3"]["n_workable"]
                lot[i, j] = c["on_lot"]
    cmax = np.nanmax(cells)
    cmin = np.nanmin(cells)
    ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    rgb = [tuple(int(h[k:k + 2], 16) for k in (1, 3, 5)) for h in ramp]

    def colour(v):
        # Stretch over the range actually present: 0-max left most of the
        # sheet in the same mid blue on the first render.
        t = max(0.0, min(1.0, (v - cmin) / max(cmax - cmin, 1))) * (len(rgb) - 1)
        a = int(t)
        b = min(a + 1, len(rgb) - 1)
        f = t - a
        return tuple(int(rgb[a][k] + (rgb[b][k] - rgb[a][k]) * f) for k in range(3))

    px_w, px_h = 2, 4
    im = Image.new("RGB", (360 * px_w, nr * px_h), (252, 252, 251))
    pix = im.load()
    for x in range(360 * px_w):
        true_b = (x / px_w + C.DECLINATION_E if hasattr(C, "DECLINATION_E") else x / px_w) % 360
        i = int(round(true_b / (brgs[1] - brgs[0]))) % len(brgs)
        for j in range(nr):
            v = cells[i, j]
            if np.isnan(v):
                continue
            col = colour(v)
            if not lot[i, j]:
                col = tuple(int(0.45 * ch + 0.55 * 252) for ch in col)
            edge = (lot[i, j] != lot[i, min(j + 1, nr - 1)] or
                    lot[i, j] != lot[(i + 1) % len(brgs), j])
            for y in range(j * px_h, (j + 1) * px_h):
                pix[x, y] = (82, 81, 78) if edge and y == (j + 1) * px_h - 1 else col
    im.save(path)
    return {"px_per_deg": px_w, "px_per_run_step": px_h, "cells_max": float(cmax),
            "cells_min": float(cmin),
            "rows_runs_m": [float(r) for r in runs],
            "rows_attach_ft": [float(ROOF_FT + math.sqrt(W * W - r * r) / FT) for r in runs],
            "ramp": ramp}


def pack(c, wires103=None):
    e = c["end_en"]
    la, lo = to_latlon(*e)
    d = {k: c[k] for k in ("fft", "brg", "run", "dir", "end_ft", "attach_ft", "slope",
                           "on_lot", "setback_ok", "parcel", "c3_lo", "c3_hi")}
    d.update({"brg_mag": round(mag(c["brg"]), 2), "run_ft": round(c["run"] / FT, 1),
              "end_en": list(e), "end_dms": list(dms(la, lo)), "poly": [list(p) for p in c["poly"]],
              "m3": c["m3"], "m2": c["m2"], "g": c["g"],
              "nbr_mean": c.get("nbr_mean"), "nbr_min": c.get("nbr_min")})
    if wires103:
        k3 = c["k3"]
        d["rank_among_103"] = 1 + sum(
            1 for w in wires103 if (w["nec3"]["n_workable"], w["nec3"]["n_regions_covered"],
                                    w["nec3"]["mean_power_dBi"]) > k3)
    return d


def main():
    with open(os.path.join(DATA, "nec-scores.json"), encoding="utf-8") as fh:
        wires103 = json.load(fh)["wires"]

    g25 = full_grid(ROOF_FT, 1.0, 0.25, 0.05)
    cells, mean = neighbourhood(g25)
    pool = refine(g25["all"], ROOF_FT)
    wins = winners(pool)

    # Most robust point per category: best neighbourhood mean on the grid.
    robust = []
    for name, pred in CATS[:-1]:
        grid_pts = [c for c in g25["all"] if c["dir"] == "up" and pred(c) and "nbr_mean" in c]
        if grid_pts:
            r = max(grid_pts, key=lambda c: (c["nbr_mean"], c["k3"]))
            robust.append({"category": name, "wire": r})

    # Attach neighbourhood stats to refined winners from their nearest grid point.
    for w in wins:
        c = w["wire"]
        if c["dir"] == "up" and "nbr_mean" not in c:
            i = int(round(c["brg"])) % 360
            j = int(round((c["run"] - g25["runs_up"][0]) / 0.25))
            j = max(0, min(j, len(g25["runs_up"]) - 1))
            near = g25["up"][i][j]
            if near:
                c["nbr_mean"], c["nbr_min"] = near["nbr_mean"], near["nbr_min"]

    st = stress(pool, wins)

    heights = []
    for fft in (20.0, 25.0, 30.0):
        g = full_grid(fft, 2.0, 0.5, 0.05) if fft != ROOF_FT else None
        pts = g["all"] if g else [c for c in g25["all"]
                                  if abs(c["brg"] / 2 - round(c["brg"] / 2)) < 1e-6 and
                                  (c["dir"] == "down" or abs(c["run"] * 2 - round(c["run"] * 2)) < 1e-6)]
        row = {"roof_ft": fft, "grid": "2 deg x 0.5 m", "wires": len(pts)}
        for name, pred in CATS[:3] + CATS[-1:]:
            b = distinct(pts, lambda c: c["k3"], pred, 1)
            row[name] = pack(b[0]) if b else None
        heights.append(row)

    land = landscape(g25, mean, os.path.join(IMGDIR, "nec_roof_sloper_landscape.png"))

    with open(os.path.join(DATA, "nec-roof-sloper-grid.csv"), "w", encoding="utf-8",
              newline="") as fh:
        fh.write("# Every straight sloper off the roof point on NEC-2 "
                 "(tools/nec_roof_sloper_scan.py).\n")
        fh.write(f"# Roof feed ENU {ROOF_EN}, cells workable >= {THR:.2f} dBi. "
                 "brg in degrees true.\n")
        fh.write("roof_ft,dir,brg_true,brg_mag,run_m,end_ft,slope_deg,cells3,regions3,dBi3,"
                 "worst3,cells2,dBi2,cells3_thr_minus2,cells3_thr_plus2,nbr_mean3,on_lot,"
                 "setback_ok\n")
        for c in sorted(pool + [x for h in (20.0, 30.0) for x in []],
                        key=lambda c: (c["dir"], c["brg"], c["run"])):
            fh.write(f"{c['fft']:.0f},{c['dir']},{c['brg']:.2f},{mag(c['brg']):.2f},"
                     f"{c['run']:.2f},{c['end_ft']:.1f},{c['slope']:.1f},"
                     f"{c['m3']['n_workable']},{c['m3']['n_regions_covered']},"
                     f"{c['m3']['mean_power_dBi']:.2f},{c['m3']['worst_dBi']:.1f},"
                     f"{c['m2']['n_workable']},{c['m2']['mean_power_dBi']:.2f},"
                     f"{c['c3_lo']},{c['c3_hi']},"
                     f"{'' if c.get('nbr_mean') is None else round(c['nbr_mean'], 2)},"
                     f"{int(c['on_lot'])},{int(c['setback_ok'])}\n")

    summary = {
        "generated_by": "tools/nec_roof_sloper_scan.py",
        "roof_feed": [list(ROOF_EN), ROOF_FT], "threshold_dBi": THR, "freqs_MHz": FREQS,
        "grid": {"roof_ft": ROOF_FT, "bearing_step_deg": 1.0, "run_step_m": 0.25,
                 "down_run_step_m": 0.05, "wires": len(g25["all"]),
                 "refined_total": len(pool),
                 "run_up_min_m": float(g25["runs_up"][0]), "run_up_max_m": 39.5},
        "winners": [{"metric": w["metric"], "category": w["category"],
                     "wire": pack(w["wire"], wires103)} for w in wins],
        "robust": [{"category": r["category"], "wire": pack(r["wire"], wires103)}
                   for r in robust],
        "stress": st, "heights": heights, "landscape": land,
        "references": {k: next((w for w in wires103 if w["key"] == k), None)["nec3"]
                       for k in ("NR-SL1", "NR-SL2", "CURRENT", "RB-POST20", "F10-A")},
        "elapsed_s": round(time.time() - T0),
    }
    with open(os.path.join(DATA, "nec-roof-sloper-scan.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=0)

    say("WINNERS")
    for w in summary["winners"]:
        c = w["wire"]
        m = c["m3"] if w["metric"] == "3band" else c["m2"]
        print(f"  {w['metric']:5s} {w['category']:46s} {c['dir']:4s} {c['brg_mag']:6.2f}M "
              f"run {c['run_ft']:5.1f} ft end {c['end_ft']:5.1f} ft slope {c['slope']:4.1f} | "
              f"{m['n_workable']}/{m['n_cells']} {m['mean_power_dBi']:+.2f} worst "
              f"{m['worst_dBi']:+.1f} | thr-2/+2 {c['c3_lo']}/{c['c3_hi']} | nbr "
              f"{c['nbr_mean'] if c['nbr_mean'] is None else round(c['nbr_mean'], 1)}"
              f"/{c['nbr_min']} | #{c.get('rank_among_103')} | {c['parcel']}")
    say("MOST ROBUST")
    for r in summary["robust"]:
        c = r["wire"]
        print(f"  {r['category']:46s} {c['brg_mag']:6.2f}M run {c['run_ft']:5.1f} ft end "
              f"{c['end_ft']:5.1f} ft | {c['m3']['n_workable']}/75 {c['m3']['mean_power_dBi']:+.2f} "
              f"| nbr mean {c['nbr_mean']:.1f} min {c['nbr_min']:.0f} | {c['parcel']}")
    say("STRESS (rank among candidates / cells)")
    for row in st["rows"]:
        print("  " + row["category"][:40].ljust(40) + " " + "  ".join(
            f"{k[:10]}:{v['rank']}/{v['cells']}" for k, v in row.items() if k != "category"))
    say("HEIGHTS")
    for h in heights:
        print(f"  roof {h['roof_ft']:.0f} ft: " + " | ".join(
            f"{k}: {v['m3']['n_workable']}/75 @ {v['brg_mag']:.0f}M end {v['end_ft']:.0f} ft"
            for k, v in h.items() if isinstance(v, dict) and v))
    say("wrote data/nec-roof-sloper-scan.json, data/nec-roof-sloper-grid.csv, "
        "imagery/nec_roof_sloper_landscape.png")


if __name__ == "__main__":
    main()
