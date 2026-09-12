#!/usr/bin/env python3
"""Re-run the topology search on NEC-2, and NEC-score every wire on the list.

The analytic search (topology_search.py) picked candidates with the section 3
long-wire formula, which nec_validate.py shows puts the even-harmonic lobes in
the wrong place. Here the SAME candidate grids are scored by NEC instead:

  from the transformer (10 ft)   slopers, inverted-Vs, inverted-Ls
  from the roof point (25 ft)    slopers up and down, inverted-Vs, inverted-Ls
  RB-POST20                      post re-placed in the staked strip
  F10-A                          leg 2 re-aimed (bend <= 70 deg)

each ranked on NEC 40+20+15 m and on NEC 40+20 m. Family limits are exactly
topology_search.py's (feed heights, 8 ft minimum ends, 30 deg L rise, 40 deg V
legs, parcel rules, 150 ft cap).

Then EVERY wire scored anywhere in the study - compare_options.py's 35, the
analytic search picks, the roof picks and the NEC picks - is scored by NEC on
all five bands, deduplicated, and ranked. The analytic scores ride along so
the page can show what changed.

Run from the repository root (about 5 minutes on 32 cores):

    python .../tools/nec_search.py

Writes ../data/nec-scores.json, ../data/nec-ranking.csv, ../data/nec-ranking.kml.
"""

import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compare_options as C          # noqa: E402
import topology_search as T          # noqa: E402
import nec_engine as N               # noqa: E402
from site_geometry import polar, offset, mag, to_latlon   # noqa: E402

FT = 0.3048
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
B3, B2, ALLB = ["40m", "20m", "15m"], ["40m", "20m"], list(C.BAND_KEYS)
FREQS = N.model_freqs()
CACHE = {}


def nec_batch(opts, bands=B3):
    for o in opts:
        o.poly = N.polyline(o)
    todo = list(dict.fromkeys(o.poly for o in opts
                              if (o.poly, tuple(bands)) not in CACHE))
    if todo:
        for p, g in zip(todo, N.gains_many(todo, FREQS, bands)):
            CACHE[(p, tuple(bands))] = g
    for o in opts:
        o.nec = CACHE[(o.poly, tuple(bands))]
    return opts


def k3(o):
    return N.rank_key(o.nec, B3)


def k2(o):
    return N.rank_key(o.nec, B2)


def nec_search(cands, key, n, far, neighbours, seeds=12):
    cands = [c for c in cands if c is not None]
    nec_batch(cands)
    cands.sort(key=key, reverse=True)
    top = []
    for c in cands:
        if all(far(c, s) for s in top):
            top.append(c)
        if len(top) == seeds:
            break
    nb = [x for s in top for x in neighbours(s) if x is not None]
    nec_batch(nb)
    pool = sorted(cands[:300] + nb, key=key, reverse=True)
    picks = []
    for c in pool:
        if all(far(c, p) for p in picks):
            picks.append(c)
        if len(picks) == n:
            break
    return picks


# --------------------------------------------------------------------------
# Candidate grids - topology_search.py's families, parameters kept on o.param
# --------------------------------------------------------------------------

def sloper_cands(feed):
    fen, fft = feed
    out = []
    for b in range(0, 360, 5):
        for run in [10.0 + i for i in range(30)]:
            if fft + math.sqrt(C.WIRE_M ** 2 - run ** 2) / FT > C.TREE_MAX_FT:
                continue
            o = T.make_sloper(offset(fen, float(b), run), feed=feed)
            if o is not None:
                o.param = ("up", float(b), run)
                out.append(o)
        if fft >= T.DOWN_MIN_FEED_FT:
            dmin = math.sqrt(max(C.WIRE_M ** 2 - (fft * FT - T.L_BOTTOM_FT * FT) ** 2, 0))
            for i in range(8):
                run = dmin + i * (C.WIRE_M - 0.02 - dmin) / 7
                o = T.make_down_sloper(offset(fen, float(b), run), feed=feed)
                if o is not None:
                    o.param = ("down", float(b), run)
                    out.append(o)
    return out


def sloper_neighbours(feed):
    fen, fft = feed

    def nb(o):
        d, b, run = o.param
        out = []
        for db in (-5, -2.5, 0, 2.5, 5):
            for dr in ((-0.5, -0.25, 0, 0.25, 0.5) if d == "up"
                       else (-0.1, -0.05, 0, 0.05, 0.1)):
                r = run + dr
                if not 10.0 <= r < C.WIRE_M:
                    continue
                en = offset(fen, b + db, r)
                if d == "up":
                    if fft + math.sqrt(C.WIRE_M ** 2 - r ** 2) / FT > C.TREE_MAX_FT:
                        continue
                    x = T.make_sloper(en, feed=feed)
                else:
                    x = T.make_down_sloper(en, feed=feed)
                if x is not None:
                    x.param = (d, b + db, r)
                    out.append(x)
        return out
    return nb


def vee_cands(feed):
    fen, _ = feed
    apexes = [C.APEX_EN] + [offset(fen, float(b), float(d))
                            for d in range(4, 25, 2) for b in range(0, 360, 10)]
    out = []
    for ap in apexes:
        if not C.inside_parcel(ap, 0.0):
            continue
        b1 = T.rel(ap, feed)[1]
        for delta in range(-70, 71, 10):
            o = T.make_vee(ap, b1 + delta, feed=feed)
            if o is None or not C.inside_parcel(o.supports[2][2], 0.0):
                continue
            o.param = (ap, (b1 + delta) % 360)
            out.append(o)
    return out


def vee_neighbours(feed):
    def nb(o):
        ap0, b20 = o.param
        out = []
        for de in (-1, 0, 1):
            for dn in (-1, 0, 1):
                ap = (ap0[0] + de, ap0[1] + dn)
                if not C.inside_parcel(ap, 0.0):
                    continue
                for db in (-5, -2.5, 0, 2.5, 5):
                    x = T.make_vee(ap, b20 + db, feed=feed)
                    if x is None or x.bend > 70 or \
                            not C.inside_parcel(x.supports[2][2], 0.0):
                        continue
                    x.param = (ap, (b20 + db) % 360)
                    out.append(x)
        return out
    return nb


def ell_cands(feed):
    fen, _ = feed
    out = []
    for b in range(0, 360, 10):
        for d in range(6, 39, 2):
            en = offset(fen, float(b), float(d))
            if not C.inside_parcel(en, 0.0):
                continue
            for h2 in range(10, 93, 2):
                o = T.make_ell(en, h2 / 2 / FT, feed=feed)
                if o is not None:
                    o.param = (en, h2 / 2 / FT)
                    out.append(o)
    return out


def ell_neighbours(feed):
    def nb(o):
        en0, top0 = o.param
        out = []
        for de in (-1, 0, 1):
            for dn in (-1, 0, 1):
                en = (en0[0] + de, en0[1] + dn)
                if not C.inside_parcel(en, 0.0):
                    continue
                for dh in (-4, -2, 0, 2, 4):
                    x = T.make_ell(en, top0 + dh, feed=feed)
                    if x is not None:
                        x.param = (en, top0 + dh)
                        out.append(x)
        return out
    return nb


def far_sloper(a, b):
    return math.dist(a.supports[-1][2], b.supports[-1][2]) >= 8.0


def far_vee(a, b):
    fa, fb = a.supports[1][2], b.supports[1][2]
    return (math.dist(fa, fb) >= 10.0 or
            T.bend_deg(T.rel(fa, a.feed)[1], T.rel(fb, b.feed)[1]) >= 20)


def far_ell(a, b):
    return math.dist(a.supports[1][2], b.supports[1][2]) >= 6.0


def redbox_cands():
    F = T.FEED10[1] * FT
    apex_h, post_h = 50 * FT, 20 * FT
    leg1 = math.hypot(C.APEX_DIST, apex_h - F)
    rest = C.WIRE_M - leg1
    out = []
    for pe, pn in C.red_box_points(0.5):
        run = math.hypot(pe - C.APEX_EN[0], pn - C.APEX_EN[1])
        if abs(math.hypot(run, apex_h - post_h) - rest) > 0.45:
            continue
        brg = polar(pe - C.APEX_EN[0], pn - C.APEX_EN[1])[1]
        o = C.Option("x", "x", [(leg1, (F + apex_h) / 2, C.APEX_BRG),
                                (rest, (apex_h + post_h) / 2, brg)],
                     [("feed", 10, (0.0, 0.0)), ("apex tree", 50, C.APEX_EN),
                      ("post", 20, (pe, pn))])
        d, b = polar(pe, pn)
        o.label = f"RB-POST20, post re-placed on NEC: {d/FT:.0f} ft at {mag(b):.0f}°M"
        o.family, o.model, o.feed = "garden post", "bent wire (§3/§4)", T.FEED10
        o.bend = T.bend_deg(C.APEX_BRG, brg)
        out.append(o)
    return out


def f10a_cands():
    f, a, fs, e = T.FEED10[1] * FT, 50 * FT, 50 * FT, 30 * FT
    leg1 = math.hypot(C.APEX_DIST, a - f)
    into = 29.7 - leg1
    tail = (C.WIRE_M - leg1) - into
    run_tail = math.sqrt(max(tail ** 2 - (fs - e) ** 2, 0))
    out = []
    for b2 in range(0, 360, 5):
        if T.bend_deg(C.APEX_BRG, b2) > 70:
            continue
        far_en = offset(C.APEX_EN, float(b2), into)
        end_en = offset(far_en, float(b2), run_tail)
        if not (C.inside_parcel(far_en, 0.0) and C.inside_parcel(end_en, 0.0)):
            continue
        o = C.Option("x", f"F10-A, leg 2 re-aimed on NEC to {mag(b2):.0f}°M",
                     [(leg1, (f + a) / 2, C.APEX_BRG), (into, (a + fs) / 2, float(b2)),
                      (tail, (fs + e) / 2, float(b2))],
                     [("feed", 10, (0.0, 0.0)), ("apex tree", 50, C.APEX_EN),
                      ("far support", 50, far_en), ("end", 30, end_en)])
        o.family, o.model, o.feed = "bent flat-top", "bent wire (§3/§4)", T.FEED10
        o.bend = T.bend_deg(C.APEX_BRG, b2)
        out.append(o)
    return out


# --------------------------------------------------------------------------

def run_nec_searches():
    picks = {}
    t0 = time.time()
    for fname, feed, pre in (("transformer", T.FEED10, "N"), ("roof", T.ROOF_FEED, "NR")):
        print(f"[{time.time()-t0:5.0f}s] NEC candidates from the {fname} ...")
        sc, vc, lc = sloper_cands(feed), vee_cands(feed), ell_cands(feed)
        print(f"         {len(sc)} slopers, {len(vc)} Vs, {len(lc)} Ls")
        # The roof adds are 6 slopers, 3 Vs, 6 Ls (operator 2026-09-12).
        counts = ({"SL": 3, "V": 3, "L": 3} if fname == "transformer"
                  else {"SL": 6, "V": 3, "L": 6})
        for metric, key, tag in (("3band", k3, ""), ("40+20", k2, "2")):
            for fam, cands, nbf, far in (
                    ("SL", sc, sloper_neighbours(feed), far_sloper),
                    ("V", vc, vee_neighbours(feed), far_vee),
                    ("L", lc, ell_neighbours(feed), far_ell)):
                n = counts[fam] if metric == "3band" else 3
                got = nec_search(cands, key, n, far, nbf)
                for i, o in enumerate(got, 1):
                    o.key = f"{pre}{tag}-{fam}{i}"
                    o.label = o.label + (" · NEC search" if metric == "3band"
                                         else " · NEC search, 40+20 m")
                picks[f"{fname}:{metric}:{fam}"] = got
                print(f"[{time.time()-t0:5.0f}s]   {fname} {metric} {fam}: " +
                      ", ".join(f"{k3(o)[0]}/75 {k2(o)[0]}/50" for o in got))
            if fname == "roof" and metric == "3band":
                down = [c for c in sc if getattr(c, "direction", "") == "down"]
                if down:
                    got = nec_search(down, key, 1, far_sloper, sloper_neighbours(feed))
                    for o in got:
                        o.key, o.label = "NR-DN1", o.label + " · NEC search"
                    picks["roof:3band:DN"] = got
    rb, fa = nec_batch(redbox_cands()), nec_batch(f10a_cands())
    for metric, key, tag in (("3band", k3, ""), ("40+20", k2, "2")):
        b1 = max(rb, key=key)
        b2 = max(fa, key=key)
        x1 = C.Option(f"N{tag}-RB20", b1.label, b1.segments, b1.supports)
        x2 = C.Option(f"N{tag}-F10A", b2.label, b2.segments, b2.supports)
        for x, src in ((x1, b1), (x2, b2)):
            x.family, x.model, x.feed, x.bend = src.family, src.model, src.feed, src.bend
            if metric == "40+20":
                x.label += ", 40+20 m"
        picks[f"transformer:{metric}:RB"] = [x1]
        picks[f"transformer:{metric}:F10A"] = [x2]
    return picks


def main():
    t0 = time.time()
    print("analytic lineup (topology_search.run + roof) ...")
    res = T.run(verbose=False)
    roof = T.run_feed(T.ROOF_FEED, prefix="R")
    existing = list(res["existing"].values())
    groups = {
        "existing": existing,
        "analytic:lineup": T.lineup(res),
        "analytic:transformer": (res["3band:sloper"] + res["3band:vee"]
                                 + res["3band:ell"]),
        "analytic:40+20": (res["40+20:sloper"] + res["40+20:vee"] + res["40+20:ell"]
                           + [res["40+20:rb"], res["40+20:f10a"]]),
        "analytic:roof": roof["sloper"] + roof["vee"] + roof["ell"] + roof["down"],
    }
    nec_picks = run_nec_searches()
    for k, v in nec_picks.items():
        groups["nec:" + k] = v

    # Deduplicate every wire by its NEC polyline; keep the first key.
    wires, alias, member = {}, {}, {}
    for gname, group in groups.items():
        for o in group:
            if not o.supports:
                continue
            p = N.polyline(o)
            k = wires.get(p)
            if k is None:
                wires[p] = o
                member[o.key] = [gname]
            else:
                alias.setdefault(k.key, [])
                if o.key != k.key and o.key not in alias[k.key]:
                    alias[k.key].append(o.key)
                if gname not in member[k.key]:
                    member[k.key].append(gname)
    allw = list(wires.values())
    print(f"[{time.time()-t0:5.0f}s] NEC on all five bands for {len(allw)} distinct wires ...")
    nec_batch(allw, ALLB)

    def mk(o, bands):
        return N.aggregate(o.nec, bands)

    r3 = sorted(allw, key=lambda o: N.rank_key(o.nec, B3), reverse=True)
    r2 = sorted(allw, key=lambda o: N.rank_key(o.nec, B2), reverse=True)
    a3 = sorted(allw, key=lambda o: T.rank_key(o, B3), reverse=True)
    a2 = sorted(allw, key=lambda o: T.rank_key(o, B2), reverse=True)

    # Model-vs-NEC agreement, per model, over every wire and cell (3 bands).
    agree = {}
    for o in allw:
        model = getattr(o, "model", "?")
        grp = ("bent wire" if model.startswith("bent") else
               "slant (§9)" if model.startswith("slant") else
               "hybrid L" if model.startswith("hybrid") else "horizontal")
        d = agree.setdefault(grp, {"ana": [], "nec": [], "wires": 0})
        d["wires"] += 1
        for b in B3:
            nets = C.band_nets(o, b)
            d["ana"] += [v + C.BAND[b]["peak_dBi"] for v in nets]
            d["nec"] += [v - 6.02 for v in o.nec[b]]
    import nec_validate as V
    agreement = []
    for grp, d in list(agree.items()) + [("all", {
            "ana": [x for v in agree.values() for x in v["ana"]],
            "nec": [x for v in agree.values() for x in v["nec"]],
            "wires": sum(v["wires"] for v in agree.values())})]:
        ana = [max(x, -40.0) for x in d["ana"]]
        nec = [max(x, -40.0) for x in d["nec"]]
        agreement.append({
            "model": grp, "wires": d["wires"], "cells": len(ana),
            "corr": round(V._corr(ana, nec), 3),
            "mean_nec_minus_analytic_dB": round(sum(n - a for a, n in zip(ana, nec)) / len(ana), 2),
            "mean_abs_diff_dB": round(sum(abs(n - a) for a, n in zip(ana, nec)) / len(ana), 2),
            "workable_agreement": round(sum((a >= C.WORKABLE_dBi) == (n >= C.WORKABLE_dBi)
                                            for a, n in zip(ana, nec)) / len(ana), 3)})
    rank_corr = {
        "3band": round(V.spearman([T.rank_key(o, B3)[0] * 1000 + T.rank_key(o, B3)[2] for o in allw],
                                  [N.rank_key(o.nec, B3)[0] * 1000 + N.rank_key(o.nec, B3)[2] for o in allw]), 3),
        "40+20": round(V.spearman([T.rank_key(o, B2)[0] * 1000 + T.rank_key(o, B2)[2] for o in allw],
                                  [N.rank_key(o.nec, B2)[0] * 1000 + N.rank_key(o.nec, B2)[2] for o in allw]), 3)}
    print("agreement:", json.dumps(agreement, indent=1))
    print("rank correlation analytic vs NEC:", rank_corr)

    out = []
    for o in r3:
        feed = getattr(o, "feed", T.FEED10)
        out.append({
            "key": o.key, "label": o.label, "family": getattr(o, "family", "?"),
            "model": getattr(o, "model", "?"), "bend": getattr(o, "bend", 0.0),
            "feed": [list(feed[0]), feed[1]],
            "supports": [[nm, h, en[0], en[1]] for nm, h, en in o.supports],
            "poly": [list(p) for p in o.poly], "aliases": alias.get(o.key, []),
            "groups": member[o.key], "parcel": T.parcel_status(o),
            "max_anchor_ft": o.max_anchor_ft,
            "nec": o.nec,
            "nec_rank3": r3.index(o) + 1, "nec_rank2": r2.index(o) + 1,
            "ana_rank3": a3.index(o) + 1, "ana_rank2": a2.index(o) + 1,
            "nec3": mk(o, B3), "nec2": mk(o, B2),
            "nec_band": {b: N.aggregate(o.nec, [b]) for b in ALLB},
            "ana3": C.aggregate_multiband(o, B3), "ana2": C.aggregate_multiband(o, B2),
            "ana_band": {b: {"mean_power_dBi": C.aggregate(o, b)["mean_power_dBi"],
                             "n_workable": C.aggregate(o, b)["n_workable"]}
                         for b in ALLB},
        })
    with open(os.path.join(DATA, "nec-scores.json"), "w", encoding="utf-8") as fh:
        json.dump({"generated_by": "tools/nec_search.py", "freqs_MHz": FREQS,
                   "workable_nec_dBi": N.WORKABLE_NEC_dBi,
                   "targets": [t[0] for t in N.TARGETS],
                   "roof_feed": [list(T.ROOF_FEED[0]), T.ROOF_FEED[1]],
                   "agreement": agreement, "rank_corr": rank_corr,
                   "wires": out}, fh, indent=0)

    with open(os.path.join(DATA, "nec-ranking.csv"), "w", encoding="utf-8",
              newline="") as fh:
        fh.write("# Every wire in the study, scored by NEC-2 (tools/nec_search.py).\n")
        fh.write(f"# Workable = NEC gain >= {N.WORKABLE_NEC_dBi:.2f} dBi (study -5 dBi "
                 "+ 6.02 dB ground reflection). Bands modelled at the wire's own "
                 "resonances; see data/nec-resonances.json.\n")
        fh.write("# ana_* = the analytic scores the study used before, for comparison.\n")
        fh.write("nec_rank3,key,family,model,feed_ft,nec3_cells,nec3_regions,nec3_dBi,"
                 "nec3_worst,nec_rank2,nec2_cells,nec2_dBi,ana_rank3,ana3_cells,"
                 "ana3_dBi,ana_rank2,ana2_cells,max_anchor_ft,parcel,aliases,label\n")
        for w in out:
            fh.write(f"{w['nec_rank3']},{w['key']},{w['family']},\"{w['model']}\","
                     f"{w['feed'][1]:.0f},{w['nec3']['n_workable']},"
                     f"{w['nec3']['n_regions_covered']},{w['nec3']['mean_power_dBi']:.2f},"
                     f"{w['nec3']['worst_dBi']:.1f},{w['nec_rank2']},"
                     f"{w['nec2']['n_workable']},{w['nec2']['mean_power_dBi']:.2f},"
                     f"{w['ana_rank3']},{w['ana3']['n_workable']},"
                     f"{w['ana3']['mean_power_dBi']:.2f},{w['ana_rank2']},"
                     f"{w['ana2']['n_workable']},{w['max_anchor_ft']},"
                     f"\"{w['parcel']}\",\"{' '.join(w['aliases'])}\",\"{w['label']}\"\n")

    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
         '<name>JYR8010 EFHW - every wire, ranked by NEC-2</name>',
         '<Style id="w"><LineStyle><color>ff00d7ff</color><width>4</width></LineStyle></Style>']
    for w in out:
        coords = " ".join(f"{to_latlon(p[0], p[1])[1]:.8f},{to_latlon(p[0], p[1])[0]:.8f},{p[2]:.2f}"
                          for p in w["poly"])
        desc = (f"#{w['nec_rank3']} on NEC 40+20+15 m: {w['nec3']['n_workable']}/75 cells, "
                f"{w['nec3']['mean_power_dBi']:+.2f} dBi, worst {w['nec3']['worst_dBi']:+.1f}<br/>"
                f"NEC 40+20 m: #{w['nec_rank2']}, {w['nec2']['n_workable']}/50<br/>"
                f"Analytic (old): #{w['ana_rank3']}, {w['ana3']['n_workable']}/75<br/>"
                f"{w['label']}<br/>{w['parcel']}")
        L.append(f'<Folder><name>#{w["nec_rank3"]} {w["key"]}</name><Placemark>'
                 f'<name>{w["key"]}</name><styleUrl>#w</styleUrl>'
                 f'<description><![CDATA[{desc}]]></description><LineString>'
                 f'<altitudeMode>relativeToGround</altitudeMode><coordinates>{coords}'
                 f'</coordinates></LineString></Placemark></Folder>')
    L.append('</Document></kml>')
    with open(os.path.join(DATA, "nec-ranking.kml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))

    print(f"\n[{time.time()-t0:5.0f}s] TOP 25 ON NEC 40+20+15 m")
    for w in out[:25]:
        print(f"  #{w['nec_rank3']:3d} {w['key']:12s} {w['family']:15s} NEC "
              f"{w['nec3']['n_workable']:2d}/75 {w['nec3']['mean_power_dBi']:+6.2f} "
              f"worst {w['nec3']['worst_dBi']:+6.1f} | 40+20 #{w['nec_rank2']:3d} "
              f"{w['nec2']['n_workable']:2d}/50 | analytic #{w['ana_rank3']:3d} "
              f"{w['ana3']['n_workable']:2d}/75 | hi {w['max_anchor_ft']:3d} | "
              f"{w['parcel']}")
    for key in ("CURRENT", "BASE", "RB-POST20", "F10-A", "A"):
        w = next((x for x in out if x["key"] == key), None)
        if w:
            print(f"  #{w['nec_rank3']:3d} {key:12s} NEC {w['nec3']['n_workable']:2d}/75 "
                  f"{w['nec3']['mean_power_dBi']:+6.2f} | 40+20 #{w['nec_rank2']} "
                  f"{w['nec2']['n_workable']}/50 | analytic #{w['ana_rank3']} "
                  f"{w['ana3']['n_workable']}/75")
    print(f"\nwrote data/nec-scores.json, nec-ranking.csv, nec-ranking.kml "
          f"({len(out)} wires)")


if __name__ == "__main__":
    main()
