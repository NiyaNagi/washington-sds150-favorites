#!/usr/bin/env python3
"""Does moving the END of the wire buy anything? Three separate questions.

The operator asked whether re-siting the far end - for example onto the house
roof as a sloper - would help significantly. That is really three questions
with three different answers, so they are scored separately here:

  1. END HEIGHT   - hold both bearings, raise the far tie-off. This is the
                    current-null question, and the answer is nearly
                    model-independent.
  2. END BEARING  - hold heights, swing leg 2 through every azimuth. This is
                    the pattern question, and it has to be filtered by bend
                    angle (see below).
  3. ROOF SUPPORT - use the house ridge as the high point instead of the tree.

**The bend-angle filter matters.** METHOD.md section 3 scores a bent wire as
the UNION of two lobe sets: it ignores relative phase between the legs and so
overstates how cleanly they add. That approximation degrades as the bend
sharpens - two nearly antiparallel legs partially cancel and nothing here knows
it. Any azimuth recommendation must therefore be filtered on bend angle, not
taken from the score alone. Bends past ~110 deg are reported but marked NOT
VALID rather than silently ranked first, which is exactly what happened on the
first run of this script.

Standard library only. Run from the repository root:

    python3 antenna-results/antennas/jyr8010-efhw/deployment-siting-cn97ap/tools/endpoint_study.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compare_options as C          # noqa: E402
from site_geometry import (          # noqa: E402
    WIRE_M, offset, polar, to_latlon, dms, mag,
)

FT = 0.3048
RUN1, BRG1 = C.APEX_DIST, C.APEX_BRG

# House footprint, from the operator's own corner marks (data/site-points.json).
# feed = NE corner at the origin; backyard corner 12.28 m at 154.9T is the SE
# corner; front yard corner 7.08 m at 325.9T. Long axis therefore runs about
# 155/335T. The ridge is taken as the midpoint of the feed->backyard edge
# shifted 4 m onto the roof centreline.
#
# ASSUMED, NOT MEASURED: the 4 m half-width and the ridge heights below. The
# conclusion is insensitive to both - see the printed table.
RIDGE_EN = offset(offset((0, 0), 154.9, 6.1), 244.9, 4.0)


def build(end_ft=30.0, leg2=130.0, apex_ft=50.0, far_ft=50.0, feed_ft=24.0):
    """Option A with the far end's height and bearing as free parameters."""
    f, a, fs, e = feed_ft * FT, apex_ft * FT, far_ft * FT, end_ft * FT
    leg1 = math.hypot(RUN1, a - f)
    into = 29.7 - leg1                     # far support at the current maximum
    tail = (WIRE_M - leg1) - into
    run_far = math.sqrt(max(into ** 2 - (a - fs) ** 2, 0))
    run_tail = math.sqrt(max(tail ** 2 - (fs - e) ** 2, 0))
    far_en = offset(C.APEX_EN, leg2, run_far)
    o = C.Option("X", f"leg2 {leg2:.0f}T, end {end_ft:.0f} ft",
                 [(leg1, (f + a) / 2, BRG1), (into, (a + fs) / 2, leg2),
                  (tail, (fs + e) / 2, leg2)], [])
    return o, far_en, offset(far_en, leg2, run_tail)


def bend(leg2):
    """Deviation from a straight wire, degrees. 0 = straight."""
    return abs((leg2 - BRG1 + 180) % 360 - 180)


def trust(leg2):
    b = bend(leg2)
    return "OK" if b <= 70 else "OVERSTATED" if b <= 110 else "NOT VALID"


def line(o, label):
    m = C.aggregate_multiband(o)
    per = "  ".join(f"{b}:{C.aggregate(o, b)['mean_power_dBi']:+6.2f}"
                    for b in C.BAND_KEYS)
    print(f"{label:42s} {m['mean_power_dBi']:+6.2f} dBi  {m['n_workable']:2d}/75"
          f"  {m['n_regions_covered']:2d}/25  worst {m['worst_dBi']:7.1f}   {per}")


def region_3band(o):
    out = {}
    for name, lat, lon, arr in C.TARGETS:
        b = C.TARGET_BEARINGS[name]
        lin = [10 ** ((o.score(b, arr, bd)[2] + C.BAND[bd]["peak_dBi"]) / 10)
               for bd in C.MULTIBAND]
        out[name] = 10 * math.log10(sum(lin) / len(lin))
    return out


def q1_end_height():
    print("=" * 124)
    print("1. END HEIGHT - bearings unchanged (leg1 82T, leg2 130T), apex and "
          "far support stay at 50 ft")
    print("=" * 124)
    for h in (10, 20, 30, 40, 50, 60):
        line(build(end_ft=h)[0], f"   end tie-off at {h:2d} ft")

    print("\n   WHY SO LITTLE: both ends of an EFHW are voltage maxima, i.e.")
    print("   current NULLS. Only the current maxima radiate, and the tail")
    print("   segment (29.7-39.6 m of wire) contains almost none of them:")
    for b in C.BAND_KEYS:
        n = C.BAND[b]["n"]
        pos = C.imax_positions(n)
        tail = [p for p in pos if p > 29.7]
        print(f"      {b:4s} n={n}  {len(tail)} of {n} current maxima in the "
              f"tail" + (f" (at {', '.join(f'{p:.1f}' for p in tail)} m)"
                         if tail else ""))
    print("   The far support already sits at 29.7 m - the 40 m and 15 m")
    print("   current maximum - precisely so the end does not have to matter.")


def q2_end_bearing():
    print("\n" + "=" * 124)
    print("2. END BEARING - end at 30 ft, leg 2 swung through every azimuth")
    print("=" * 124)
    rows = []
    for b2 in range(0, 360, 5):
        o, far_en, end_en = build(leg2=float(b2))
        m = C.aggregate_multiband(o)
        rows.append((m["n_workable"], m["mean_power_dBi"], b2, m, far_en, end_en))
    rows.sort(reverse=True)

    print(f"{'leg2 T':>7s} {'leg2 M':>7s} {'bend':>6s} {'3-band':>8s} "
          f"{'cells':>7s} {'regs':>6s} {'worst':>8s}  {'end from feed':>17s}"
          f"  parcel  model")
    for i, (nw, agg, b2, m, far_en, end_en) in enumerate(rows):
        if i >= 8 and b2 != 130:
            continue
        d, br = polar(*end_en)
        ok = C.inside_parcel(end_en) and C.inside_parcel(far_en)
        mark = "  <-- CURRENT DESIGN" if b2 == 130 else ""
        print(f"{b2:7d} {mag(b2):7.0f} {bend(b2):5.0f}d {agg:8.2f} {nw:4d}/75 "
              f"{m['n_regions_covered']:4d}/25 {m['worst_dBi']:8.1f}  "
              f"{d:6.1f} m at {br:5.0f}T  {'in ' if ok else 'OUT':>6s}  "
              f"{trust(b2):10s}{mark}")

    good = [r for r in rows if bend(r[2]) <= 70]
    best = good[0]
    print(f"\n   Best azimuth the model is entitled to score: leg2 "
          f"{best[2]}T / {mag(best[2]):.0f}M, bend {bend(best[2]):.0f} deg, "
          f"{best[1]:+.2f} dBi, {best[0]}/75 cells")
    la, lo = to_latlon(*best[5])
    d, br = polar(*best[5])
    print(f"   Its end would land {d:.1f} m ({d/FT:.0f} ft) from the feed at "
          f"{br:.0f}T / {mag(br):.0f}M - {dms(la, lo)[0]} {dms(la, lo)[1]}")

    print("\n   What that swap would actually cost and buy (3-band mean dBi "
          "per region):")
    a, b = region_3band(build(leg2=130.0)[0]), region_3band(build(leg2=float(best[2]))[0])
    deltas = sorted(((b[k] - a[k], k) for k in a), reverse=True)
    print(f"      {'region':18s} {'brg':>5s} {'130T':>8s} "
          f"{str(best[2]) + 'T':>8s} {'delta':>8s}")
    for dv, k in deltas:
        if abs(dv) < 0.8:
            continue
        print(f"      {k:18s} {C.TARGET_BEARINGS[k]:5.0f} {a[k]:8.1f} "
              f"{b[k]:8.1f} {dv:+8.1f}")
    print("\n   Read the losers against the terrain table: Hawaii 240T, VK2")
    print("   244T and South Africa 058T. The 210-270T sector is the only one")
    print("   with a -7.9 deg foreground downslope, and it is the reason this")
    print("   site can work VK at all. The winners - Florida, Caribbean,")
    print("   Denver, Dallas - already come back on 15 m and 10 m without")
    print("   moving anything. That is a bad trade at any price, and it is")
    print("   only worth +0.5 dB.")


def q3_roof():
    print("\n" + "=" * 124)
    print("3. ROOF AS THE HIGH SUPPORT - ridge assumed on the house long axis")
    print("=" * 124)
    d, b = polar(*RIDGE_EN)
    la, lo = to_latlon(*RIDGE_EN)
    print(f"   assumed ridge point: {d:.1f} m ({d/FT:.0f} ft) from the feed at "
          f"{b:.0f}T / {mag(b):.0f}M   {dms(la, lo)[0]} {dms(la, lo)[1]}")
    print(f"   compare: the apex TREE is {C.APEX_DIST:.1f} m "
          f"({C.APEX_DIST/FT:.0f} ft) away at 50 ft.\n")
    for rf in (20, 25, 30, 40):
        top, f = rf * FT, 24 * FT
        leg_a = math.hypot(d, abs(top - f))
        rest = WIRE_M - leg_a
        best = None
        for b2 in range(0, 360):
            run = math.sqrt(max(rest ** 2 - (top - 10 * FT) ** 2, 0))
            if not C.inside_parcel(offset(RIDGE_EN, float(b2), run)):
                continue
            o = C.Option("R", "roof", [(leg_a, (f + top) / 2, b),
                                       (rest, (top + 10 * FT) / 2, float(b2))], [])
            m = C.aggregate_multiband(o)
            if best is None or (m["n_workable"], m["mean_power_dBi"]) > best[0]:
                best = ((m["n_workable"], m["mean_power_dBi"]), b2, o)
        o = best[2]
        line(o, f"   ridge {rf} ft, best run {best[1]:03d}T, avg ht "
                f"{o.avg_h/FT:.0f} ft")
    print()
    line(build()[0], "   A - apex tree 50 ft, end 30 ft, leg2 130T")
    print(f"\n   The ridge is only {d/FT:.0f} ft from the feed, so barely 19% of")
    print("   the wire is in the first leg and the remaining 81% slopes away")
    print("   from a low point. Average height collapses from 41.6 ft to")
    print("   16-27 ft. Height in wavelengths is what sets low-angle gain, and")
    print("   the roof cannot supply it - it is both too close and too low.")
    print("\n   NOT SCORED, and deliberately: anchoring the END on the roof.")
    print("   Feed to apex is 17.9 m, leaving 21.7 m of wire that would have")
    print("   to fold back to a point ~7 m from the feed - a hairpin whose")
    print("   legs are near antiparallel. METHOD.md section 3 cannot model")
    print("   the cancellation, so no number here would be honest. It is also")
    print("   the wrong idea on its own terms: the end is the VOLTAGE maximum,")
    print("   about 1 kV RMS at 150 W (see INSULATORS.md), and that does not")
    print("   belong on a roof next to gutters, flashing and house wiring.")


def main():
    q1_end_height()
    q2_end_bearing()
    q3_roof()
    print("\n" + "=" * 124)
    print("VERDICT: keep the end where it is.")
    print("  - Raising it 10 -> 60 ft is worth 0.35 dB. It is a current null.")
    print("  - Re-aiming it is worth at most +0.5 dB and costs the southwest")
    print("    terrain window, which is the site's one real advantage.")
    print("  - The roof is 2.6-4.1 dB WORSE than the tree, and the wire's end")
    print("    is the last thing that should be attached to a house.")
    print("=" * 124)


if __name__ == "__main__":
    main()
