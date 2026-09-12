#!/usr/bin/env python3
"""Validate the study's models against NEC-2 (PyNEC), and NEC against itself.

Four parts, in the order a skeptic should read them:

  1. ENGINE BENCHMARKS - does PyNEC reproduce textbook results? Half-wave
     dipole impedance and gain, the angle convention, and the take-off angle
     of a horizontal dipole over perfect ground (METHOD.md section 4).
  2. RESONANCES - where the modelled 39.6 m wire is actually resonant, bare
     and with the 1 m counterpoise feed nec_engine.py uses. Written to
     data/nec-resonances.json, which nec_engine.py reads.
  3. THE PATTERN FORMULA - METHOD.md section 3's long-wire pattern against
     NEC, band by band: lobe angle, peak directivity, shape correlation. Also
     scored: the end-fed standing-wave form, |sin(n pi/2 cos t)/sin t| for even
     n, which section 3 does not use.
  4. SENSITIVITY - how far the NEC ranking of the 35 compare_options.py wires
     moves under each modelling choice: frequency policy, ground model,
     segmentation, counterpoise length, workable threshold.

Model-versus-NEC agreement over every wire on the list is computed by
nec_search.py, which has all of them.

Run from the repository root:

    python .../tools/nec_validate.py

Writes ../data/nec-validation.json and ../data/nec-resonances.json.
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compare_options as C          # noqa: E402
import nec_engine as N               # noqa: E402
from site_geometry import longwire_field   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
C0, R = N.C0, N.WIRE_R
B3 = ["40m", "20m", "15m"]


def _ctx(wires, freq, ground=None, src=(1, 1)):
    import PyNEC as P
    c = P.nec_context()
    g = c.get_geometry()
    for tag, (a, b, n) in enumerate(wires, 1):
        g.wire(tag, n, *a, *b, R, 1.0, 1.0)
    c.geometry_complete(0)
    if ground is None:
        c.gn_card(-1, 0, 0, 0, 0, 0, 0, 0)
    elif ground == "perfect":
        c.gn_card(1, 0, 0, 0, 0, 0, 0, 0)
    c.ex_card(0, src[0], src[1], 0, 1.0, 0, 0, 0, 0, 0)
    c.fr_card(0, 1, freq, 0)
    return c


def _z(c):
    # PyNEC solves lazily; a radiation-pattern request triggers it.
    c.rp_card(0, 1, 1, 0, 5, 0, 0, 90, 0, 0, 0, 0, 0)
    return c.get_input_parameters(0).get_impedance()[0]


# --------------------------------------------------------------------------
# 1. Engine benchmarks
# --------------------------------------------------------------------------

def benchmarks():
    out = {}
    lam = C0 / 14.0
    prev, res = None, None
    for k in range(460, 506, 1):
        L = lam * k / 1000
        z = _z(_ctx([((0, 0, -L / 2), (0, 0, L / 2), 41)], 14.0, src=(1, 21)))
        if prev and prev[1].imag < 0 <= z.imag:
            res = {"length_lambda": round(k / 1000, 3), "R_ohm": round(z.real, 1)}
        prev = (k / 1000, z)
    c = _ctx([((0, 0, -lam / 4), (0, 0, lam / 4), 41)], 14.0, src=(1, 21))
    z = _z(c)
    c.rp_card(0, 181, 1, 0, 5, 0, 0, 0, 0, 1, 0, 0, 0)
    out["dipole"] = {
        "resonance": res, "textbook_resonance": "0.47-0.49 lambda, ~70 ohm",
        "half_wave_Z": [round(z.real, 1), round(z.imag, 1)],
        "textbook_Z": [73, 42],
        "gain_dBi": round(float(c.get_radiation_pattern(1).get_gain().max()), 2),
        "textbook_gain_dBi": 2.15}

    c = _ctx([((-lam / 4, 0, 0), (lam / 4, 0, 0), 41)], 14.0, src=(1, 21))
    c.rp_card(0, 1, 5, 0, 5, 0, 0, 90, 0, 0, 22.5, 0, 0)
    gg = [round(float(v), 1) for v in c.get_radiation_pattern(0).get_gain().flatten()]
    out["convention"] = {"x_dipole_gain_phi_0_22_45_67_90": gg,
                         "null_at_phi_0": gg[0] < -50,
                         "mapping": "phi = 90 - bearing_T, theta = 90 - elevation"}

    lam = C0 / 14.15
    rows = []
    for hl in (0.3, 0.45, 0.6, 1.0):
        c = _ctx([((-0.24 * lam, 0, hl * lam), (0.24 * lam, 0, hl * lam), 41)],
                 14.15, ground="perfect", src=(1, 21))
        c.rp_card(0, 181, 1, 0, 5, 0, 0, 0, 90, 0.5, 0, 0, 0)
        gg = c.get_radiation_pattern(0).get_gain().flatten()
        rows.append({"h_lambda": hl, "nec_elev": round(90 - gg.argmax() * 0.5, 1),
                     "section4_elev": round(math.degrees(math.asin(1 / (4 * hl))), 1)})
    out["takeoff_perfect_ground"] = rows
    return out


# --------------------------------------------------------------------------
# 2. Resonances
# --------------------------------------------------------------------------

def _wire_ctx(f, counterpoise, segs):
    wires = []
    if counterpoise:
        wires.append(((counterpoise, 0, 0), (0, 0, 0), 1))
    wires.append(((0, 0, 0), (0, 0, C.WIRE_M), segs))
    return _ctx(wires, f, src=(1, 1))


def resonance(band, counterpoise, f1=None):
    """Peak of R near the band's harmonic.

    First run searched 0.80-1.10 of each band frequency and on 20/15/10 m
    landed on the ODD harmonic below (n=3, 5, 7), which has the higher R. Now
    the fundamental is found first and harmonic n is searched near n x f1.
    """
    f0, n = C.BAND[band]["f"], C.BAND[band]["n"]
    segs = max(61, int(C.WIRE_M / (C0 / f0 / 30)) | 1)
    lo, hi = (f0 * 0.80, f0 * 1.10) if f1 is None else (n * f1 * 0.95, n * f1 * 1.08)
    best = None
    for i in range(0, 101):
        f = lo + (hi - lo) * i / 100
        rr = _z(_wire_ctx(f, counterpoise, segs)).real
        if best is None or rr > best[0]:
            best = (rr, f)
    edge = best[1] <= lo * 1.001 or best[1] >= hi * 0.999
    for j in range(-12, 13):                      # refine to 0.025%
        f = best[1] * (1 + j / 4000)
        rr = _z(_wire_ctx(f, counterpoise, segs)).real
        if rr > best[0]:
            best = (rr, f)
    return round(best[1], 4), round(best[0]), edge


def resonances():
    out = {"bare": {}, "with_counterpoise": {}, "R_peak_ohm": {}, "edge_hit": {},
           "ratio_to_fundamental": {},
           "measured_80m_MHz": 3.6056,
           "measured_note": "parent report's best 80 m match, Z = 49.8 + 4.3j"}
    for variant, cp in (("bare", 0.0), ("with_counterpoise", N.COUNTERPOISE_M)):
        f1 = resonance("80m", cp)[0]
        for b in C.BAND_KEYS:
            f, r, e = resonance(b, cp, None if b == "80m" else f1)
            out[variant][b] = f
            out["R_peak_ohm"].setdefault(b, []).append(r)
            out["edge_hit"][b] = out["edge_hit"].get(b, False) or e
            out["ratio_to_fundamental"].setdefault(b, []).append(round(f / f1, 3))
    return out


# --------------------------------------------------------------------------
# 3. The pattern formula
# --------------------------------------------------------------------------

def end_fed_form(t_deg, n):
    t = math.radians(t_deg)
    if abs(math.sin(t)) < 1e-9:
        return 0.0
    k = n * math.pi / 2
    v = math.sin(k * math.cos(t)) if n % 2 == 0 else math.cos(k * math.cos(t))
    return abs(v / math.sin(t))


def _corr(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def pattern_check(freqs):
    rows = []
    th = [i * 0.5 for i in range(361)]
    for key, f_band, lam, n, pk, _, _ in C.BANDS:
        f = freqs[key]
        segs = max(61, int(C.WIRE_M / (C0 / f / 30)) | 1)
        c = _wire_ctx(f, 0.0, segs)
        c.rp_card(0, 361, 1, 0, 5, 0, 0, 0, 0, 0.5, 0, 0, 0)
        gg = c.get_radiation_pattern(0).get_gain().flatten()
        i = int(gg.argmax())
        nec_lobe = min(th[i], 180 - th[i])
        nec_db = [max(-25.0, gg[k] - gg.max()) for k in range(4, 357)]
        pc = max(longwire_field(t, n) for t in th[4:357])
        pe = max(end_fed_form(t, n) for t in th[4:357])
        cos_db = [max(-25.0, 20 * math.log10(max(longwire_field(t, n), 1e-9) / pc))
                  for t in th[4:357]]
        end_db = [max(-25.0, 20 * math.log10(max(end_fed_form(t, n), 1e-9) / pe))
                  for t in th[4:357]]
        rows.append({
            "band": key, "n": n, "model_MHz": f,
            "nec_lobe_deg": nec_lobe,
            "section3_lobe_deg": (max(range(1, 90), key=lambda t: longwire_field(t, n))
                                  if n > 1 else 90),
            "end_fed_lobe_deg": (max(range(1, 90), key=lambda t: end_fed_form(t, n))
                                 if n > 1 else 90),
            "arrl_lobe_deg": {1: 90, 2: 54, 4: 36, 6: 29, 8: 25}.get(n),
            "nec_peak_dBi": round(float(gg.max()), 2),
            "study_peak_dBi": pk,
            "shape_corr_section3": round(_corr(nec_db, cos_db), 3),
            "shape_corr_end_fed": round(_corr(nec_db, end_db), 3)})
    return rows


# --------------------------------------------------------------------------
# 4. Sensitivity of the NEC ranking to NEC's own modelling choices
# --------------------------------------------------------------------------

def spearman(a, b):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    return _corr(ranks(a), ranks(b))


def sensitivity(freqs):
    opts = [o for o in C.build_options() if o.supports]
    polys = [N.polyline(o) for o in opts]
    base = N.gains_many(polys, freqs, B3)

    def score(gs, thr=None):
        return [N.rank_key(g, B3, thr)[0] * 1000 + N.rank_key(g, B3, thr)[2]
                for g in gs]

    base_score = score(base)
    base_cells = [v for g in base for b in B3 for v in g[b]]
    variants = [
        ("band frequencies instead of resonance", dict(freqs=N.model_freqs("band"))),
        ("Sommerfeld ground (GN 2)", dict(kw={"gtype": 2})),
        ("lambda/40 segments", dict(kw={"seg_per_lambda": 40})),
        ("0.5 m counterpoise", dict(kw={"counterpoise": 0.5})),
        ("2.0 m counterpoise", dict(kw={"counterpoise": 2.0})),
    ]
    rows = []
    for name, v in variants:
        gs = N.gains_many(polys, v.get("freqs", freqs), B3, **v.get("kw", {}))
        cells = [x for g in gs for b in B3 for x in g[b]]
        rows.append({
            "variant": name,
            "rank_spearman": round(spearman(base_score, score(gs)), 3),
            "cell_mean_abs_dB": round(sum(abs(a - b) for a, b in
                                          zip(base_cells, cells)) / len(cells), 2),
            "workable_agreement": round(sum(
                (a >= N.WORKABLE_NEC_dBi) == (b >= N.WORKABLE_NEC_dBi)
                for a, b in zip(base_cells, cells)) / len(cells), 3)})
    for d in (-2.0, 2.0):
        rows.append({
            "variant": f"workable threshold {d:+.0f} dB",
            "rank_spearman": round(spearman(base_score,
                                            score(base, N.WORKABLE_NEC_dBi + d)), 3),
            "cell_mean_abs_dB": 0.0, "workable_agreement": None})
    return {"n_wires": len(opts), "rows": rows}


def main():
    print("1. engine benchmarks ...")
    bench = benchmarks()
    print(json.dumps(bench, indent=1))
    print("\n2. resonances (peak R) ...")
    res = resonances()
    print(json.dumps(res, indent=1))
    with open(os.path.join(DATA, "nec-resonances.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    freqs = N.model_freqs()
    print("\n3. pattern formula at the resonant frequencies ...")
    pat = pattern_check(res["bare"])
    for r in pat:
        print(" ", r)
    print("\n4. sensitivity of the NEC ranking ...")
    sens = sensitivity(freqs)
    for r in sens["rows"]:
        print(" ", r)
    with open(os.path.join(DATA, "nec-validation.json"), "w", encoding="utf-8") as fh:
        json.dump({"benchmarks": bench, "resonances": res, "pattern": pat,
                   "sensitivity": sens, "workable_nec_dBi": N.WORKABLE_NEC_dBi,
                   "model": {"wire_radius_m": N.WIRE_R, "eps_r": N.EPS_R,
                             "sigma": N.SIGMA, "seg_per_lambda": N.SEG_PER_LAMBDA,
                             "counterpoise_m": N.COUNTERPOISE_M,
                             "ground_type": N.GROUND_TYPE}}, fh, indent=1)
    print("\nwrote data/nec-validation.json and data/nec-resonances.json")


if __name__ == "__main__":
    main()
