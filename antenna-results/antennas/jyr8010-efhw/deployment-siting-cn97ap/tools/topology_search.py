#!/usr/bin/env python3
"""Search three wire families with the feed held at 10 ft, and re-rank on 40+20 m.

Asked 2026-09-12: overlay the as-built sloper, BASE, RB-POST20, F10-A, the top
three slopers and the top three inverted-V or inverted-L deployments on the
property, and separately find the best options if only 40 m and 20 m mattered.
The operator set the limits:

  SL  STRAIGHT SLOPER. Feed 10 ft, support anywhere up to the 150 ft tree cap.
      Parcel NOT enforced ("doesn't need to be on the lot") - status reported.
      Slant model, METHOD.md section 9. LOW confidence.
  V   INVERTED-V. Feed 10 ft -> apex at 50 ft -> end tied off at 10 ft.
      Apex and end on the lot. Horizontal bent-wire model (sections 3/4),
      exactly as V1/V2 are scored.
  L   INVERTED-L WITH THE VERTICAL AT THE FAR END. Feed 10 ft -> top of a
      support, rising no more than 30 deg -> the rest of the wire hangs
      straight down, bottom at least 8 ft up. Support on the lot. The vertical
      is NOT at the feed: that end is a voltage maximum and radiates poorly
      there (AGENT_GUIDE.md).

The L needs a model the study did not have. Both legs are scored on the
section 9 slant model - the rising leg at its own slope, the hanging leg at
90 deg - and combined as a union exactly as section 3 combines two horizontal
legs. At least 10 m must hang vertically, or it is just a sloper. That combination is NEW and UNVALIDATED
and the two legs are orthogonal - a 90 deg bend, which endpoint_study.py
classes as OVERSTATED. L figures are the least trustworthy numbers in the study.

Bend filter: V candidates are ranked only with a bend of 70 deg or less, the
limit endpoint_study.py gives for what section 3 is entitled to score.

Two metrics, both ranked the way METHOD.md section 7 requires (workable cells,
then regions reachable, then mean power):
  3-band  40 + 20 + 15 m, 75 cells - the study's standing ranking
  40+20   40 + 20 m only,  50 cells - the operator's 2026-09-12 question

Standard library only. Run from the repository root:

    python3 antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap/tools/topology_search.py

Writes ../data/topology-search.csv and ../data/topology-search.kml.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compare_options as C          # noqa: E402
from site_geometry import (          # noqa: E402
    WIRE_M, polar, offset, mag, longwire_field, longwire_peak,
)

FT = 0.3048
FEED_FT = 10.0
F = FEED_FT * FT
APEX_FT = 50.0
END_FT = 10.0
L_BOTTOM_FT = 8.0
L_MAX_RISE_DEG = 30.0
# An "L" with a token vertical is just a sloper. The first search run returned
# one with 1 ft hanging down; require a real vertical section.
L_MIN_VERTICAL_M = 10.0
# The horizontal bent-wire model is only used for Vs whose legs stay in the
# regime V1/V2 already occupy (26-34 deg). The first run returned an apex 13 ft
# from the feed - a near-vertical first leg at the high-voltage end, scored as
# if it were horizontal.
V_MAX_LEG_SLOPE_DEG = 40.0
METRICS = {"3band": list(C.MULTIBAND), "40+20": ["40m", "20m"]}

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def rank_key(o, bands):
    m = C.aggregate_multiband(o, bands)
    return (m["n_workable"], m["n_regions_covered"], m["mean_power_dBi"])


def bend_deg(b1, b2):
    """Deviation from a straight wire in plan, degrees. 0 = straight."""
    return abs((b2 - b1 + 180) % 360 - 180)


def trust(bend):
    return "OK" if bend <= 70 else "OVERSTATED" if bend <= 110 else "NOT VALID"


def parcel_status(o):
    """Worst parcel status over all supports, in words."""
    worst = "on the lot"
    for nm, h, en in o.supports[1:]:
        if not C.inside_parcel(en, 0.0):
            e, n = en
            t = (e - 46.9) / -116.8
            gap = n - (-32.0 + t * 25.2)
            if gap < 0:
                return f"{nm} {-gap/FT:.0f} ft past the south line"
            return f"{nm} past the east line"
        if not C.inside_parcel(en):
            worst = "on the lot, inside the 5 m setback"
    return worst


# --------------------------------------------------------------------------
# Family constructors
# --------------------------------------------------------------------------

def make_sloper(top_en, key="x"):
    run, brg = polar(*top_en)
    top_ft = FEED_FT + math.sqrt(WIRE_M ** 2 - run ** 2) / FT
    o = C._sloper(key, f"Sloper, feed 10 ft to a {top_ft:.0f} ft support "
                       f"{run/FT:.0f} ft out at {mag(brg):.0f}°M",
                  (0.0, 0.0), FEED_FT, top_en, "Topology search.")
    o.family, o.bend, o.model = "sloper", 0.0, "slant (§9, LOW)"
    return o


def make_vee(apex_en, b2, key="x"):
    d1, b1 = polar(*apex_en)
    a, e = APEX_FT * FT, END_FT * FT
    leg1 = math.hypot(d1, a - F)
    leg2 = WIRE_M - leg1
    if leg2 <= (a - e) + 0.5:
        return None
    run2 = math.sqrt(leg2 ** 2 - (a - e) ** 2)
    if (math.degrees(math.atan2(a - F, d1)) > V_MAX_LEG_SLOPE_DEG
            or math.degrees(math.atan2(a - e, run2)) > V_MAX_LEG_SLOPE_DEG):
        return None
    end_en = offset(apex_en, b2, run2)
    bend = bend_deg(b1, b2)
    o = C.Option(
        key, f"Inverted-V, apex 50 ft {d1/FT:.0f} ft out at {mag(b1):.0f}°M, "
             f"second leg to {mag(b2):.0f}°M",
        [(leg1, (F + a) / 2, b1), (leg2, (a + e) / 2, b2)],
        [("feed", int(FEED_FT), (0.0, 0.0)), ("apex", int(APEX_FT), apex_en),
         ("end", int(END_FT), end_en)],
        f"Bend {bend:.0f} deg ({trust(bend)}). Horizontal bent-wire model.")
    o.family, o.bend, o.model = "inverted-V", bend, "bent wire (§3/§4)"
    return o


class InvertedL(C.Option):
    """Feed -> top of a support -> wire hangs straight down.

    Scored as the union of a horizontal-model leg and a slant-model vertical
    leg. See the module docstring: new, unvalidated, lowest confidence.
    """

    def __init__(self, key, top_en, top_ft):
        d1, b1 = polar(*top_en)
        H = top_ft * FT
        self.leg1 = math.hypot(d1, H - F)
        self.leg2 = WIRE_M - self.leg1
        self.H = H
        bottom = H - self.leg2
        super().__init__(
            key, f"Inverted-L, rising to {top_ft:.0f} ft {d1/FT:.0f} ft out at "
                 f"{mag(b1):.0f}°M, then {self.leg2/FT:.0f} ft hanging down",
            [(self.leg1, (F + H) / 2, b1), (self.leg2, (H + bottom) / 2, b1)],
            [("feed", int(FEED_FT), (0.0, 0.0)),
             ("support top", int(round(top_ft)), top_en),
             ("hanging end", int(round(bottom / FT)), top_en)],
            "Vertical section at the FAR end. Union of horizontal and slant "
            "models - NEW, UNVALIDATED, lowest confidence in the study.")
        self.rise_deg = math.degrees(math.atan2(H - F, d1))
        self.family, self.bend = "inverted-L", 90.0
        self.model = "hybrid §3+§9 (UNVALIDATED)"

    def height_at_wire(self, s):
        if s <= self.leg1:
            return F + s * (self.H - F) / self.leg1
        return self.H - (s - self.leg1)

    def score(self, bearing, arrival_deg, band="20m", raw_elev=False):
        bd = C.BAND[band]
        lam, n = bd["lam"], bd["n"]
        if raw_elev:
            eff = arrival_deg
        else:
            horizon, slope = C.terrain_at(bearing)
            eff = max(C.arrival_for_band(arrival_deg, band), horizon) + slope
        h_eff = max(self.mean_imax_height(band), 0.5)
        ph = 2 * math.pi * (h_eff / lam) * math.sin(math.radians(eff))
        gh = math.sin(ph) ** 2
        gv = math.cos(ph) ** 2 * 10 ** (C.vert_ground_loss_dB(eff) / 10)

        def slant(leg_bearing, slope):
            # The section 9 formula, identical to Option.score's slant branch.
            th = math.radians(slope)
            psi = C.slant_axis_angle(bearing, eff, leg_bearing, slope)
            pat = (longwire_field(psi, n) / longwire_peak(n)) ** 2
            lin = math.sin(th) ** 2 * pat * gv + math.cos(th) ** 2 * pat * gh
            return 10 * math.log10(max(lin, 1e-12))

        # Leg 1 on the slant model at its own rise - the same model the
        # sloper family uses, so an L cannot win on a model choice. The first
        # run scored this leg as horizontal and an "L" with 1 ft of vertical
        # took first place on that alone.
        net_1 = slant(self.segments[0][2], self.rise_deg)
        # Leg 2 hangs straight down: slant model at 90 deg (bearing moot).
        net_2 = slant(0.0, 90.0)
        return net_1, net_2, max(net_1, net_2)


def make_ell(top_en, top_ft, key="x"):
    if not (0 < top_ft <= C.TREE_MAX_FT):
        return None
    o = InvertedL(key, top_en, top_ft)
    if o.leg2 < L_MIN_VERTICAL_M or o.rise_deg > L_MAX_RISE_DEG or \
            o.H - o.leg2 < L_BOTTOM_FT * FT:
        return None
    return o


# --------------------------------------------------------------------------
# Searches. Coarse grid, then diversity-filtered picks refined locally.
# --------------------------------------------------------------------------

def _pick(cands, n, far_enough, refine):
    cands.sort(key=lambda c: c[0], reverse=True)
    picks = []
    for c in cands:
        if any(not far_enough(c, p) for p in picks):
            continue
        r = refine(c)
        if any(not far_enough(r, p) for p in picks):
            r = c
        picks.append(r)
        if len(picks) == n:
            break
    return picks


def search_slopers(bands, n=3):
    cands = []
    for b in range(0, 360, 5):
        for r2 in range(20, 80):                      # run 10.0 .. 39.5 m
            run = r2 / 2
            if FEED_FT + math.sqrt(WIRE_M ** 2 - run ** 2) / FT > C.TREE_MAX_FT:
                continue
            en = offset((0.0, 0.0), float(b), run)
            cands.append((rank_key(make_sloper(en), bands), en))

    def refine(c):
        best = c
        run0, b0 = polar(*c[1])
        for db in range(-4, 5):
            for dr in range(-5, 6):
                run = run0 + dr / 10
                if not 10.0 <= run < WIRE_M or FEED_FT + math.sqrt(
                        WIRE_M ** 2 - run ** 2) / FT > C.TREE_MAX_FT:
                    continue
                en = offset((0.0, 0.0), b0 + db, run)
                k = rank_key(make_sloper(en), bands)
                if k > best[0]:
                    best = (k, en)
        return best

    def far(a, b):
        return math.dist(a[1], b[1]) >= 8.0
    return [make_sloper(p[1]) for p in _pick(cands, n, far, refine)]


def search_vees(bands, n=3):
    apexes = [C.APEX_EN] + [offset((0.0, 0.0), float(b), float(d))
                            for d in range(4, 25, 2) for b in range(0, 360, 10)]
    cands = []
    for ap in apexes:
        if not C.inside_parcel(ap, 0.0):
            continue
        b1 = polar(*ap)[1]
        for delta in range(-70, 71, 5):
            o = make_vee(ap, b1 + delta)
            if o is None or not C.inside_parcel(o.supports[2][2], 0.0):
                continue
            cands.append((rank_key(o, bands), ap, (b1 + delta) % 360))

    def refine(c):
        best = c
        for de in (-1, -0.5, 0, 0.5, 1):
            for dn in (-1, -0.5, 0, 0.5, 1):
                ap = (c[1][0] + de, c[1][1] + dn)
                if not C.inside_parcel(ap, 0.0):
                    continue
                b1 = polar(*ap)[1]
                for db in range(-3, 4):
                    b2 = c[2] + db
                    o = make_vee(ap, b2)
                    if o is None or o.bend > 70 or \
                            not C.inside_parcel(o.supports[2][2], 0.0):
                        continue
                    k = rank_key(o, bands)
                    if k > best[0]:
                        best = (k, ap, b2 % 360)
        return best

    def far(a, b):
        # Distinct designs, not one V slid along its own leg: the apexes must
        # be 10 m apart or the first legs must point 20 deg apart.
        return (math.dist(a[1], b[1]) >= 10.0
                or bend_deg(polar(*a[1])[1], polar(*b[1])[1]) >= 20)
    return [make_vee(p[1], p[2]) for p in _pick(cands, n, far, refine)]


def search_ells(bands, n=3):
    cands = []
    for b in range(0, 360, 10):
        for d in range(6, 39):
            en = offset((0.0, 0.0), float(b), float(d))
            if not C.inside_parcel(en, 0.0):
                continue
            for h2 in range(10, 93):                   # 5.0 .. 46.0 m
                o = make_ell(en, h2 / 2 / FT)
                if o is not None:
                    cands.append((rank_key(o, bands), en, h2 / 2 / FT))

    def refine(c):
        best = c
        for de in (-1, -0.5, 0, 0.5, 1):
            for dn in (-1, -0.5, 0, 0.5, 1):
                en = (c[1][0] + de, c[1][1] + dn)
                if not C.inside_parcel(en, 0.0):
                    continue
                for dh in (-3, -1.5, 0, 1.5, 3):
                    o = make_ell(en, c[2] + dh)
                    if o is None:
                        continue
                    k = rank_key(o, bands)
                    if k > best[0]:
                        best = (k, en, c[2] + dh)
        return best

    def far(a, b):
        return math.dist(a[1], b[1]) >= 6.0
    return [make_ell(p[1], p[2]) for p in _pick(cands, n, far, refine)]


def search_redbox_post20(bands):
    """RB-POST20's post re-placed in the staked strip for a different metric."""
    apex_h, post_h = APEX_FT * FT, 20.0 * FT
    leg1 = math.hypot(C.APEX_DIST, apex_h - F)
    rest = WIRE_M - leg1
    best = None
    for pe, pn in C.red_box_points(0.5):
        run = math.hypot(pe - C.APEX_EN[0], pn - C.APEX_EN[1])
        if abs(math.hypot(run, apex_h - post_h) - rest) > 0.45:
            continue
        brg = polar(pe - C.APEX_EN[0], pn - C.APEX_EN[1])[1]
        o = C.Option("x", "x", [(leg1, (F + apex_h) / 2, C.APEX_BRG),
                                (rest, (apex_h + post_h) / 2, brg)],
                     [("feed", 10, (0.0, 0.0)), ("apex tree", 50, C.APEX_EN),
                      ("post", 20, (pe, pn))])
        k = rank_key(o, bands)
        if best is None or k > best[0]:
            best = (k, o, (pe, pn))
    o = best[1]
    d, b = polar(*best[2])
    o.label = (f"RB-POST20 re-placed for 40+20 m: post {d/FT:.0f} ft at "
               f"{mag(b):.0f}°M")
    o.family, o.bend, o.model = "garden post", bend_deg(
        C.APEX_BRG, o.segments[1][2]), "bent wire (§3/§4)"
    return o


def search_f10a_leg2(bands):
    """F10-A with leg 2 swung, as endpoint_study.py does, bend <= 70 deg."""
    f, a, fs, e = F, 50 * FT, 50 * FT, 30 * FT
    leg1 = math.hypot(C.APEX_DIST, a - f)
    into = 29.7 - leg1
    tail = (WIRE_M - leg1) - into
    run_tail = math.sqrt(max(tail ** 2 - (fs - e) ** 2, 0))
    best = None
    for b2 in range(0, 360, 5):
        if bend_deg(C.APEX_BRG, b2) > 70:
            continue
        far_en = offset(C.APEX_EN, float(b2), into)
        end_en = offset(far_en, float(b2), run_tail)
        if not (C.inside_parcel(far_en, 0.0) and C.inside_parcel(end_en, 0.0)):
            continue
        o = C.Option("x", "x", [(leg1, (f + a) / 2, C.APEX_BRG),
                                (into, (a + fs) / 2, float(b2)),
                                (tail, (fs + e) / 2, float(b2))],
                     [("feed", 10, (0.0, 0.0)), ("apex tree", 50, C.APEX_EN),
                      ("far support", 50, far_en), ("end", 30, end_en)])
        k = rank_key(o, bands)
        if best is None or k > best[0]:
            best = (k, o, b2)
    o = best[1]
    o.label = f"F10-A with leg 2 re-aimed to {mag(best[2]):.0f}°M for 40+20 m"
    o.family, o.bend, o.model = "bent flat-top", bend_deg(
        C.APEX_BRG, best[2]), "bent wire (§3/§4)"
    return o


# --------------------------------------------------------------------------

def tag_existing(o):
    """Family and model labels for the options compare_options.py builds."""
    if o.is_slant:
        o.family, o.model = "sloper", "slant (§9, LOW)"
    elif o.key.startswith(("V", "F10-V")):
        o.family, o.model = "inverted-V", "bent wire (§3/§4)"
    elif o.key.startswith("RB-"):
        o.family, o.model = "garden post", "bent wire (§3/§4)"
    else:
        o.family, o.model = "bent / flat-top", "bent wire (§3/§4)"
    if not hasattr(o, "bend"):
        bs = [s[2] for s in o.segments]
        o.bend = max((bend_deg(bs[i], bs[i + 1]) for i in range(len(bs) - 1)),
                     default=0.0)
    return o


def run(verbose=True):
    """Every search, both metrics. Returns a dict of named groups of Options."""
    say = print if verbose else (lambda *a, **k: None)
    existing = [tag_existing(o) for o in C.build_options()]
    E = {o.key: o for o in existing}
    out = {"existing": E}
    for metric, bands in METRICS.items():
        say(f"searching slopers on {metric} ...")
        sl = search_slopers(bands)
        say(f"searching inverted-Vs on {metric} ...")
        vv = search_vees(bands)
        say(f"searching inverted-Ls on {metric} ...")
        ll = search_ells(bands)
        pre = "SRCH" if metric == "3band" else "W"
        for fam, group in (("SL", sl), ("V", vv), ("L", ll)):
            for i, o in enumerate(group, 1):
                o.key = f"{pre}-{fam}{i}"
        out[f"{metric}:sloper"] = sl
        out[f"{metric}:vee"] = vv
        out[f"{metric}:ell"] = ll
        # Top three of V and L together, as the operator asked.
        vl = sorted(vv + ll, key=lambda o: rank_key(o, bands), reverse=True)
        out[f"{metric}:vee_or_ell"] = vl[:3]

    bands = METRICS["40+20"]
    rb, fa = search_redbox_post20(bands), search_f10a_leg2(bands)
    rb.key, fa.key = "W-RB20", "W-F10A"
    pool = (existing + out["40+20:sloper"] + out["40+20:vee"]
            + out["40+20:ell"] + [rb, fa])
    out["40+20:pool"] = sorted(pool, key=lambda o: rank_key(o, bands),
                               reverse=True)
    out["40+20:rb"], out["40+20:f10a"] = rb, fa
    return out


def lineup(res):
    """The operator's selection, in display order."""
    E = res["existing"]
    return ([E["CURRENT"], E["BASE"], E["RB-POST20"], E["F10-A"]]
            + res["3band:sloper"] + res["3band:vee_or_ell"])


def describe(o):
    m3 = C.aggregate_multiband(o, METRICS["3band"])
    m2 = C.aggregate_multiband(o, METRICS["40+20"])
    return (f"{o.key:10s} {o.family:15s} 3b {m3['mean_power_dBi']:+6.2f} "
            f"{m3['n_workable']:2d}/75 {m3['n_regions_covered']:2d}/25 w "
            f"{m3['worst_dBi']:+6.1f} | 40+20 {m2['mean_power_dBi']:+6.2f} "
            f"{m2['n_workable']:2d}/50 {m2['n_regions_covered']:2d}/25 w "
            f"{m2['worst_dBi']:+6.1f} | hi {o.max_anchor_ft:3d} ft "
            f"bend {o.bend:3.0f} {trust(o.bend):10s} | {parcel_status(o)} | "
            f"{o.label}")


def main():
    res = run()
    all3 = sorted(list(res["existing"].values()) + res["3band:sloper"]
                  + res["3band:vee"] + res["3band:ell"],
                  key=lambda o: rank_key(o, METRICS["3band"]), reverse=True)

    print("\n" + "=" * 110)
    print("THE LINEUP (3-band, 40+20+15 m)")
    print("=" * 110)
    for o in lineup(res):
        print(f"  #{all3.index(o)+1:2d}/{len(all3)}  {describe(o)}")
    for grp in ("3band:sloper", "3band:vee", "3band:ell"):
        print(f"\n  best of family {grp}:")
        for o in res[grp]:
            print(f"     {describe(o)}")

    print("\n" + "=" * 110)
    print("40 + 20 m RANKING - existing options plus every family re-searched")
    print("=" * 110)
    pool = res["40+20:pool"]
    for i, o in enumerate(pool[:15], 1):
        print(f"  #{i:2d}  {describe(o)}")
    print("  ...")
    for o in lineup(res):
        if o in pool:
            print(f"  #{pool.index(o)+1:2d}  {describe(o)}")
        else:
            m2 = C.aggregate_multiband(o, METRICS["40+20"])
            rank = 1 + sum(1 for p in pool if rank_key(p, METRICS["40+20"])
                           > rank_key(o, METRICS["40+20"]))
            print(f"  ~#{rank:2d} {describe(o)}")

    # Outputs -------------------------------------------------------------
    seen, rows = set(), []
    for grp, metric in (("lineup", "3band"), ("3band:sloper", "3band"),
                        ("3band:vee", "3band"), ("3band:ell", "3band"),
                        ("40+20:pool", "40+20")):
        group = lineup(res) if grp == "lineup" else res[grp]
        if grp == "40+20:pool":
            group = group[:10]
        for o in group:
            if o.key in seen:
                continue
            seen.add(o.key)
            rows.append((grp, o))

    with open(os.path.join(DATA, "topology-search.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write("# Topology search, feed 10 ft. Generated by "
                 "tools/topology_search.py.\n")
        fh.write("# Slopers: parcel NOT enforced (operator's choice). V and L: "
                 "supports on the lot.\n")
        fh.write("# 3b_* = 40+20+15 m over 75 cells; w_* = 40+20 m over 50 cells."
                 " Ranked cells, regions, dBi.\n")
        fh.write("# model: slant = METHOD.md s9 (LOW); hybrid = inverted-L, "
                 "NEW and UNVALIDATED.\n")
        fh.write("# No model includes tree absorption.\n")
        fh.write("group,key,family,model,bend_deg,trust,max_anchor_ft,parcel,"
                 "3b_dBi,3b_cells,3b_regions,3b_worst,w_dBi,w_cells,w_regions,"
                 "w_worst," + ",".join(f"{b}_dBi,{b}_n" for b in C.BAND_KEYS)
                 + ",supports,label\n")
        for grp, o in rows:
            m3 = C.aggregate_multiband(o, METRICS["3band"])
            m2 = C.aggregate_multiband(o, METRICS["40+20"])
            sup = "; ".join(f"{nm} {h}ft {polar(*en)[0]/FT:.0f}ft@"
                            f"{mag(polar(*en)[1]):.0f}M" if polar(*en)[0] > 0.01
                            else f"{nm} {h}ft" for nm, h, en in o.supports)
            per = ",".join(f"{C.aggregate(o, b)['mean_power_dBi']:.2f},"
                           f"{C.aggregate(o, b)['n_workable']}"
                           for b in C.BAND_KEYS)
            fh.write(f"{grp},{o.key},{o.family},\"{o.model}\",{o.bend:.0f},"
                     f"{trust(o.bend)},{o.max_anchor_ft},\"{parcel_status(o)}\","
                     f"{m3['mean_power_dBi']:.2f},{m3['n_workable']},"
                     f"{m3['n_regions_covered']},{m3['worst_dBi']:.1f},"
                     f"{m2['mean_power_dBi']:.2f},{m2['n_workable']},"
                     f"{m2['n_regions_covered']},{m2['worst_dBi']:.1f},{per},"
                     f"\"{sup}\",\"{o.label}\"\n")

    kml_opts = [o for _, o in rows]
    ranked = sorted(kml_opts, key=lambda o: rank_key(o, METRICS["3band"]),
                    reverse=True)
    path = C.write_kml(kml_opts, os.path.join(DATA, "topology-search.kml"),
                       ranked)
    print("\nwrote data/topology-search.csv and", os.path.normpath(path))


if __name__ == "__main__":
    main()
