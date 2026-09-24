"""Render the 2026-09-23 survey charts (light + dark SVG) from the committed data.

    .venv-nanovna\\Scripts\\python.exe rf-environment\\tools\\make_charts.py

Needs matplotlib (present in .venv-nanovna; never add it to .venv).
"""
import json, math, statistics, textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from lineloss import correct_fa
import matplotlib.pyplot as plt

SURVEY = Path(__file__).resolve().parents[1] / "2026-09-23-survey"
DATA, CHARTS = SURVEY / "data", SURVEY / "charts"
CHARTS.mkdir(exist_ok=True)

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  axis="#c3c2b7", band="#f0efec", s1="#2a78d6", s2="#eb6834", s3="#1baf7a", s4="#eda100"),
    "dark": dict(surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 axis="#383835", band="#262624", s1="#3987e5", s2="#d95926", s3="#199e70", s4="#c98500"),
}
# one colour per antenna in every chart (validated: 4 adjacent on lines; desk/sg7900/discone all-pairs on dots)
ANT_COLOR = {"desk": "s1", "efhw": "s2", "sg7900": "s3", "discone": "s4"}
ANT_LABEL = {"desk": "Smiley on the desk", "efhw": "EFHW (roof feed)", "sg7900": "SG7900 under the porch",
             "discone": "D3000N discone, roof"}
HAM = [(1.8, 2.0, "160"), (3.5, 4.0, "80"), (5.33, 5.41, "60"), (7.0, 7.3, "40"), (10.1, 10.15, "30"),
       (14.0, 14.35, "20"), (18.068, 18.168, "17"), (21.0, 21.45, "15"), (24.89, 24.99, "12"), (28.0, 29.7, "10")]
VHF_BANDS = [(50, 54, "6m"), (144, 148, "2m"), (222, 225, "1.25m")]
F_SMPS_6M = 68.691e3
F_AUDIO = 12.288e6


def load(name):
    return json.load(open(DATA / name))


def style(ax, th, xlabel, ylabel):
    ax.set_facecolor(th["surface"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(th["axis"])
        ax.spines[s].set_linewidth(1)
    ax.tick_params(colors=th["muted"], labelsize=9, length=0, pad=6)
    ax.grid(True, axis="y", color=th["grid"], linewidth=1)
    ax.set_axisbelow(True)
    ax.set_xlabel(xlabel, color=th["ink2"], fontsize=10)
    ax.set_ylabel(ylabel, color=th["ink2"], fontsize=10)


def figure(th, w=9.6, h=4.2, ncols=1):
    fig, axes = plt.subplots(1, ncols, figsize=(w, h), facecolor=th["surface"])
    return fig, axes


def title(fig, th, t, sub):
    fig.text(0.012, 0.965, t, color=th["ink"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.012, 0.905, "\n".join(textwrap.wrap(sub, 150)), color=th["ink2"], fontsize=9.5, va="top",
             linespacing=1.4)


def legend(ax, th, loc="upper right"):
    lg = ax.legend(loc=loc, frameon=False, fontsize=9, labelcolor=th["ink2"], handlelength=1.6)
    return lg


def save(fig, name, theme):
    path = CHARTS / f"{name}-{theme}.svg"
    fig.savefig(path, facecolor=fig.get_facecolor(), metadata={"Date": None})
    plt.close(fig)
    # matplotlib leaves trailing spaces in path data; strip them so git diff --check stays clean
    text = path.read_text(encoding="utf-8")
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")


def maxhold(rec):
    return [max(p[i] for p in rec["passes"]) for i in range(len(rec["freqs"]))]


def minhold(rec):
    return [min(p[i] for p in rec["passes"]) for i in range(len(rec["freqs"]))]


def block_median(rec, lo, hi):
    F = rec["freqs"]
    vals = [statistics.median(p[i] for p in rec["passes"]) for i, f in enumerate(F) if lo <= f < hi]
    return statistics.median(vals) if vals else None


# 1 ------------------------------------------------------------------------
WIDE = {"desk": "p2__L_wide.json", "efhw": "p3__E_wide.json", "sg7900": "p4__S_wide.json", "discone": "p6__D_wide.json"}


def chart_floor_excess(th, theme):
    base = load("p1__Lopen_wide.json")
    recs = {k: load(v) for k, v in WIDE.items() if (DATA / v).exists()}
    step = 2e6
    xs, ys = [], {k: [] for k in recs}
    f = 0.0
    while f < 350e6:
        b = block_median(base, f, f + step)
        if b is not None:
            xs.append((f + step / 2) / 1e6)
            for k, r in recs.items():
                ys[k].append(max(0.0, block_median(r, f, f + step) - b))
        f += step
    fig, ax = figure(th)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.13)
    for lo, hi, lab in VHF_BANDS + [(1.8, 29.7, "HF")]:
        ax.axvspan(lo, hi, color=th["band"], lw=0, zorder=0)
        ax.text((lo + hi) / 2, 38, lab, color=th["muted"], fontsize=8.5, ha="center")
    ax.axvspan(88, 108, color=th["band"], lw=0, zorder=0, alpha=0.5)
    ax.text(98, 38, "FM bcst", color=th["muted"], fontsize=8.5, ha="center")
    for k in recs:
        ax.plot(xs, ys[k], color=th[ANT_COLOR[k]], lw=2, solid_joinstyle="round", label=ANT_LABEL[k])
    ax.set_xlim(0, 350)
    ax.set_ylim(0, 41)
    style(ax, th, "MHz", "dB above the tinySA's own floor")
    legend(ax, th, "upper right")
    title(fig, th, "VHF hash is worst at the desk, lower on the porch, absent on the roof",
          "Median noise floor above the empty-port baseline, 2 MHz blocks, 32 kHz RBW, as measured at the tinySA (no feedline "
          "correction). The FM band (clipped) and the discone's 186–216 MHz spikes (VHF TV 9, 11, 13) are real stations.")
    save(fig, "floor-excess", theme)


# 2 ------------------------------------------------------------------------
def chart_6m_comb(th, theme):
    r, b = load("p2__L_6m.json"), load("p1__Lopen_6m.json")
    F = [f / 1e6 for f in r["freqs"]]
    p = r["passes"][1]
    fig, ax = figure(th)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.13)
    ax.plot([f / 1e6 for f in b["freqs"]], b["passes"][0], color=th["muted"], lw=1.2, label="empty port (tinySA floor)")
    ax.plot(F, p, color=th["s1"], lw=1.4, solid_joinstyle="round", label="Smiley on the desk, one 11 kHz sweep")
    n0, n1 = math.ceil(50e6 / F_SMPS_6M), math.floor(51e6 / F_SMPS_6M)
    for n in range(n0, n1 + 1):
        ax.plot([n * F_SMPS_6M / 1e6] * 2, [-74.5, -73], color=th["s2"], lw=1.5)
    ax.text(50.005, -71.5, f"orange ticks: harmonics n × 68.69 kHz (n = {n0}–{n1})", color=th["ink2"], fontsize=8.5)
    ax.set_xlim(50.0, 51.0)
    ax.set_ylim(-118, -69)
    style(ax, th, "MHz", "dBm")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.86), frameon=False, fontsize=9, labelcolor=th["ink2"],
              handlelength=1.6, ncols=2)
    title(fig, th, "6 m is a switch-mode supply comb: a line every 68.69 kHz",
          "50.0–51.0 MHz shown; the same comb fills all of 50–54 MHz at −87 to −90 dBm (≈S9 on a VHF S-meter). "
          "Lines wander between sweeps, so the supply's frequency moves with its load.")
    save(fig, "six-metre-comb", theme)


# 3 ------------------------------------------------------------------------
def chart_birdies(th, theme):
    r2, r70 = load("p2__L_2m.json"), load("p1__H_70cm.json")
    fig, axes = figure(th, 9.6, 4.2, 2)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.76, bottom=0.14, wspace=0.22)
    panels = [
        (axes[0], r2, 147.40, 147.52, [(147.450, "147.450"), (147.4625, "147.4625 DMR")], 147.456, "147.456 = 12 × 12.288",
         "2 m (Smiley, 5 kHz steps)"),
        (axes[1], r70, 442.30, 442.45, [(442.375, "442.375"), (442.400, "442.400")], 442.368, "442.368 = 36 × 12.288",
         "70 cm (desk whip, 6.25 kHz steps)"),
    ]
    for ax, rec, lo, hi, chans, bird, blab, sub in panels:
        F = [f / 1e6 for f in rec["freqs"]]
        idx = [i for i, f in enumerate(F) if lo <= f <= hi]
        mh = maxhold(rec)
        md = [statistics.median(p[i] for p in rec["passes"]) for i in range(len(F))]
        for c, lab in chans:
            ax.axvspan(c - 0.00625, c + 0.00625, color=th["band"], lw=0, zorder=0)
        ax.plot([F[i] for i in idx], [md[i] for i in idx], color=th["s1"], lw=2, solid_joinstyle="round",
                label="median of sweeps")
        ax.axvline(bird, color=th["s2"], lw=1.5, zorder=1)
        ymin = min(md[i] for i in idx) - 6
        ymax = max(mh[i] for i in idx) + 12
        ax.set_ylim(ymin, ymax)
        for k, (c, lab) in enumerate(chans):
            ax.text(c, ymax - 3 - 4 * k, lab, color=th["muted"], fontsize=8, ha="center")
        ax.text(bird, ymin + 1.5, " " + blab, color=th["ink2"], fontsize=8.5, ha="left")
        ax.set_xlim(lo, hi)
        style(ax, th, "MHz", "dBm")
        ax.set_title(sub, color=th["ink2"], fontsize=9.5, loc="left")
    title(fig, th, "Harmonics of a 12.288 MHz audio clock sit on programmed channels",
          "Grey bands are 12.5 kHz channels programmed in your radios; the orange line is the clock harmonic. "
          "Both carriers were present in every sweep.")
    save(fig, "birdies", theme)


# 4 ------------------------------------------------------------------------
def harmonic_levels(rec, nmin, nmax, fund, tol=15e3):
    F = rec["freqs"]
    mh = maxhold(rec)
    out = []
    for n in range(nmin, nmax + 1):
        f0 = n * fund
        if not (F[0] <= f0 <= F[-1]) or 87.5e6 <= f0 <= 108.5e6:  # FM broadcast would masquerade
            continue
        idx = [i for i, f in enumerate(F) if abs(f - f0) <= tol]
        if not idx:
            continue
        win = [i for i, f in enumerate(F) if abs(f - f0) <= 1.5e6]
        floor = sorted(mh[i] for i in win)[len(win) // 4]
        pk = max(mh[i] for i in idx)
        out.append((n, pk, pk - floor))
    return out


def chart_clock_ladder(th, theme):
    low = harmonic_levels(load("p2__L_wide.json"), 2, 28, F_AUDIO)
    high = harmonic_levels(load("p1__H_wide.json"), 20, 40, F_AUDIO)
    fig, ax = figure(th)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.13)
    for series, col, lab in ((low, th["s1"], "Smiley on LOW input"), (high, th["s2"], "desk whip on HIGH input")):
        det = [(n, v) for n, v, snr in series if snr >= 6]
        ax.scatter([n for n, _ in det], [v for _, v in det], s=52, color=col, edgecolors=th["surface"], linewidths=2,
                   zorder=3, label=lab)
    for n, lab, dx, dy in ((4, "49.152 (6m edge)", 0.6, 4), (12, "147.456 → 2m channels", -6, 7),
                           (13, "159.744", 1.2, 6), (36, "442.368 → 442.375", 0.6, 4)):
        v = next((v for m, v, s in low + high if m == n and s >= 6), None)
        if v is not None:
            ax.annotate(lab, xy=(n, v), xytext=(n + dx, v + dy), color=th["ink2"], fontsize=8.5,
                        arrowprops=dict(arrowstyle="-", color=th["muted"], lw=1))
    ax.set_xlim(0, 41)
    ax.set_ylim(-110, -70)
    style(ax, th, "harmonic number n  (frequency = n × 12.288 MHz)", "peak dBm")
    legend(ax, th, "lower left")
    title(fig, th, "One 12.288 MHz clock, heard from 49 MHz to 442 MHz",
          "Each dot is a harmonic ≥ 6 dB above the local floor (max of all sweeps). 12.288 MHz = 256 × 48 kHz: "
          "a digital-audio master clock (PC audio codec, USB audio/DAC, monitor speakers).")
    save(fig, "clock-ladder", theme)


# 5 ------------------------------------------------------------------------
ITU = [("city", 76.8, 27.7), ("residential", 72.5, 27.7), ("rural", 67.2, 27.7), ("quiet rural", 53.6, 28.6)]
BANDS = [("160m", 1.8, 2.0), ("80m", 3.5, 4.0), ("60m", 5.33, 5.41), ("40m", 7.0, 7.3), ("30m", 10.1, 10.15),
         ("20m", 14.0, 14.35), ("17m", 18.068, 18.168), ("15m", 21.0, 21.45), ("12m", 24.89, 24.99), ("10m", 28.0, 29.7)]


def hf_fa():
    ant, base = load("p3__E_hf.json"), load("p1__Lopen_hf.json")
    rbw = 11e3
    rows = []
    for name, lo, hi in BANDS:
        def fl(rec):
            idx = [i for i, f in enumerate(rec["freqs"]) if lo * 1e6 <= f <= hi * 1e6]
            mins = sorted(min(p[i] for p in rec["passes"]) for i in idx)
            return mins[int(len(mins) * 0.2)]
        a, b = fl(ant), fl(base)
        ext = 10 * math.log10(10 ** (a / 10) - 10 ** (b / 10))
        fc = math.sqrt(lo * hi)
        fa = correct_fa(ext - 10 * math.log10(rbw) + 174, "efhw", fc)  # refer to the antenna: feedline loss
        rows.append((name, fa, [c - d * math.log10(fc) for _, c, d in ITU]))
    return rows


def chart_hf_noise(th, theme):
    rows = hf_fa()
    x = list(range(len(rows)))
    fig, ax = figure(th)
    fig.subplots_adjust(left=0.07, right=0.87, top=0.78, bottom=0.12)
    greys = [th["ink2"], th["muted"], th["muted"], th["axis"]]
    for k, (cat, _, _) in enumerate(ITU):
        ys = [r[2][k] for r in rows]
        ax.plot(x, ys, color=greys[k], lw=1.2, zorder=1)
        ax.text(x[-1] + 0.15, ys[-1], cat, color=th["ink2"], fontsize=8.5, va="center")
    ax.scatter(x, [r[1] for r in rows], s=60, color=th["s1"], edgecolors=th["surface"], linewidths=2, zorder=3,
               label="measured on the EFHW (lower bound)")
    for xi, r in zip(x, rows):
        ax.text(xi, r[1] + 2.2, f"{r[1]:.0f}", color=th["ink"], fontsize=8.5, ha="center")
    for xi in (2, 4, 6):
        ax.axvspan(xi - 0.35, xi + 0.35, color=th["band"], lw=0, zorder=0)
    ax.set_xticks(x, [r[0] for r in rows])
    ax.set_ylim(5, 75)
    style(ax, th, "", "Fa, dB above thermal noise (kT₀B)")
    legend(ax, th, "upper right")
    title(fig, th, "HF noise: rural on the main bands, residential-to-city on 60, 30 and 17 m",
          "External noise per band vs ITU-R P.372 man-made-noise medians. Shaded bands are ones the 80 m EFHW is mismatched on, "
          "so their true noise is even higher.")
    save(fig, "hf-noise-itu", theme)


# 6 ------------------------------------------------------------------------
def smooth(xs, w):
    out = []
    for i in range(len(xs)):
        seg = xs[max(0, i - w):i + w + 1]
        out.append(sum(seg) / len(seg))
    return out


def chart_hf_floor(th, theme):
    r, b = load("p3__E_hf.json"), load("p1__Lopen_hf.json")
    F = [f / 1e6 for f in r["freqs"]]
    mn = smooth(minhold(r), 5)
    bb = smooth(b["passes"][0], 5)
    fig, ax = figure(th)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.13)
    for lo, hi, lab in HAM:
        ax.axvspan(lo, hi, color=th["band"], lw=0, zorder=0)
        ax.text((lo + hi) / 2, -58, lab, color=th["muted"], fontsize=8, ha="center")
    sel = [i for i, f in enumerate(F) if f >= 1.6]
    ax.plot([F[i] for i in sel], [bb[i] for i in sel], color=th["muted"], lw=1.2, label="empty port (tinySA floor)")
    ax.plot([F[i] for i in sel], [mn[i] for i in sel], color=th["s1"], lw=1.6, solid_joinstyle="round",
            label="EFHW, minimum of 4 sweeps (carriers removed)")
    for x, y, lab in ((5.1, -73, "5 MHz hump:\n120 Hz bursts"), (10.7, -80, "10.7 MHz hump"), (16.6, -80, "16–17 MHz\nsteady hump")):
        ax.annotate(lab, xy=(x, y - 3), xytext=(x + 1.2, y + 6), color=th["ink2"], fontsize=8.5,
                    arrowprops=dict(arrowstyle="-", color=th["muted"], lw=1))
    ax.set_xlim(1.6, 30)
    ax.set_ylim(-116, -55)
    style(ax, th, "MHz", "dBm (11 kHz RBW)")
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.9), frameon=False, fontsize=9, labelcolor=th["ink2"],
              handlelength=1.6)
    title(fig, th, "Three noise humps ride on the HF floor",
          "Grey bands are amateur allocations (numbers are metres). The humps sit between the main bands and "
          "swamp 60, 30 and 17 m.")
    save(fig, "hf-floor", theme)


# 7 ------------------------------------------------------------------------
def chart_zero_span(th, theme):
    z = load("zs__hf_fast.json")
    by = {round(d["f"], 2): d for d in z["data"]}
    ms = 219.0
    fig, ax = figure(th)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.13)
    for f, col, lab in ((5.15, th["s2"], "5.15 MHz hump"), (16.7, th["s1"], "16.7 MHz hump")):
        rec = by[f]["records"][3]
        t = [i * ms / len(rec) for i in range(len(rec))]
        ax.plot(t, rec, color=col, lw=1.4, solid_joinstyle="round", label=lab)
    for k in range(0, 27):
        tk = k * 1000 / 120
        if tk <= ms:
            ax.axvline(tk, color=th["axis"], lw=1, zorder=1)
    ax.text(2, -52.5, "vertical hairlines every 8.33 ms = 120 Hz (twice per mains cycle)", color=th["ink2"], fontsize=8.5)
    ax.set_xlim(0, ms)
    ax.set_ylim(-92, -50)
    style(ax, th, "milliseconds (zero span, 30 kHz RBW)", "dBm")
    ax.grid(False, axis="x")
    legend(ax, th, "upper right")
    title(fig, th, "Two different HF sources: one pulses with the mains, one never stops",
          "At 5.15 MHz the noise bursts 120 times a second (a rectifier-fed switch-mode device). "
          "At 16.7 MHz it is steady: a continuous electronic emitter.")
    save(fig, "zero-span", theme)


# 8 ------------------------------------------------------------------------
def chart_vhf_noise(th, theme):
    import vhfnoise
    rows = [r for r in vhfnoise.compute(DATA) if any(r["ant"][k] for k in ("desk", "sg7900", "discone"))]
    x = list(range(len(rows)))
    n_itu = sum(1 for r in rows if r["itu"])
    fig, ax = figure(th, 9.6, 4.8)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.76, bottom=0.17)
    for xi, r in zip(x, rows):
        if r["high_input"]:
            ax.axvspan(xi - 0.42, xi + 0.42, color=th["band"], lw=0, zorder=0)
    greys = {"city": th["ink2"], "residential": th["muted"], "rural": th["muted"], "galactic": th["axis"]}
    for cat in ("city", "residential", "rural", "galactic"):
        ys = [r["itu"][cat] for r in rows[:n_itu]]
        ax.plot(x[:n_itu], ys, color=greys[cat], lw=1.2, zorder=1)
        ax.text(n_itu - 1 + 0.3, ys[-1], cat, color=th["ink2"], fontsize=8, va="center")
    offs = {"desk": -0.24, "sg7900": 0.0, "discone": 0.24}
    for k, dx in offs.items():
        col = th[ANT_COLOR[k]]
        det = [(xi + dx, r["ant"][k]["fa"]) for xi, r in zip(x, rows) if r["ant"][k] and r["ant"][k]["fa"] is not None]
        und = [(xi + dx, r["ant"][k]["limit"]) for xi, r in zip(x, rows) if r["ant"][k] and r["ant"][k]["fa"] is None]
        ax.scatter([a for a, _ in det], [b for _, b in det], s=46, color=col, edgecolors=th["surface"], linewidths=2,
                   zorder=4, label=ANT_LABEL[k])
        ax.scatter([a for a, _ in und], [b for _, b in und], s=46, facecolors=th["surface"], edgecolors=col,
                   linewidths=1.8, zorder=4)
        if k == "desk":
            for a, b in det:
                ax.text(a, b + 1.8, f"{b:.0f}", color=th["ink"], fontsize=8, ha="center", zorder=5)
    ax.scatter([], [], s=46, facecolors=th["surface"], edgecolors=th["muted"], linewidths=1.8,
               label="hollow: upper bound")
    labels = [r["band"].replace(" MHz", "\nMHz").replace("UHF ", "UHF\n").replace(" PS", "\nPS") for r in rows]
    ax.set_xticks(x, labels, fontsize=8.5)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.set_ylim(-5, 58)
    style(ax, th, "", "Fa at the antenna, dB above kT₀B")
    ax.text(n_itu + 0.1, 46, "shaded = HIGH input; no ITU curve above 250 MHz.\ndiscone HIGH values are masked by the analyzer's "
            "own FM harmonics", color=th["muted"], fontsize=8, va="center")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=th["ink2"], handlelength=1.2, ncols=4,
              columnspacing=1.2)
    title(fig, th, "External noise per band on every antenna, vs ITU-R P.372",
          "Carriers excluded (20th percentile of the minimum over sweeps), the tinySA's own floor subtracted, feedline loss "
          "added back so every value is at the antenna. Hollow markers are upper bounds: below the tinySA's detection limit, "
          "or (discone above 240 MHz) masked by FM harmonics the analyzer makes itself.")
    save(fig, "vhf-noise-itu", theme)


# 9 ------------------------------------------------------------------------
def chart_birdie_by_antenna(th, theme):
    files = {"desk": "p2__L_2m.json", "sg7900": "p4__S_2m.json", "discone": "p6__D_2m.json"}
    lo, hi = 147.40, 147.52
    fig, ax = figure(th)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.13)
    for c, lab in ((147.450, "147.450"), (147.4625, "147.4625 DMR")):
        ax.axvspan(c - 0.00625, c + 0.00625, color=th["band"], lw=0, zorder=0)
    ax.axvline(147.456, color=th["muted"], lw=1, zorder=1)
    ax.text(147.4565, -64, " 147.456 = 12 × 12.288 MHz", color=th["ink2"], fontsize=8.5)
    for k, fn in files.items():
        if not (DATA / fn).exists():
            continue
        rec = load(fn)
        F = [f / 1e6 for f in rec["freqs"]]
        idx = [i for i, f in enumerate(F) if lo <= f <= hi]
        md = [statistics.median(p[i] for p in rec["passes"]) for i in idx]
        ax.plot([F[i] for i in idx], md, color=th[ANT_COLOR[k]], lw=2, solid_joinstyle="round", label=ANT_LABEL[k])
    ax.text(147.450, -118.5, "147.450", color=th["muted"], fontsize=8, ha="center")
    ax.text(147.4625, -115.5, "147.4625 DMR", color=th["muted"], fontsize=8, ha="center")
    ax.set_xlim(lo, hi)
    ax.set_ylim(-120, -62)
    style(ax, th, "MHz", "dBm, median of 5 sweeps")
    legend(ax, th, "upper right")
    title(fig, th, "The 147.456 MHz birdie on each antenna",
          "Grey bands are the programmed 147.450 and 147.4625 channels. Levels are as measured at the tinySA; "
          "the SG7900 and discone sit behind 1.2 and 1.7 dB of feedline.")
    save(fig, "birdie-by-antenna", theme)


# 10 -----------------------------------------------------------------------
HIGH_SERVICES = [(420, 450, "70cm"), (450, 470, "UHF"), (470, 608, "UHF TV"), (617, 652, "LTE 600\ndown"),
                 (729, 768, "LTE 700\ndown"), (769, 775, "700\nPS"), (851, 869, "800\nPS"), (869, 894, "cell\n850"),
                 (902, 928, "ISM /\n33cm"), (929, 932, "pag.")]


def chart_discone_high(th, theme):
    if not (DATA / "p7__DH_wide.json").exists():
        return
    rec = load("p7__DH_wide.json")
    b1, b2 = load("p2__Hopen_wide.json"), load("p4__Hopen_hi.json")
    F = [f / 1e6 for f in rec["freqs"]]
    mh = maxhold(rec)
    md = [statistics.median(p[i] for p in rec["passes"]) for i in range(len(F))]
    bf = [f / 1e6 for f in b1["freqs"]] + [f / 1e6 for f in b2["freqs"] if f > b1["freqs"][-1]]
    bv = [statistics.median(p[i] for p in b1["passes"]) for i in range(len(b1["freqs"]))] + \
         [statistics.median(p[i] for p in b2["passes"]) for i, f in enumerate(b2["freqs"]) if f > b1["freqs"][-1]]
    fig, ax = figure(th, 9.6, 4.4)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.76, bottom=0.12)
    for lo, hi, lab in HIGH_SERVICES:
        ax.axvspan(lo, hi, color=th["band"], lw=0, zorder=0)
        ax.text((lo + hi) / 2, -42, lab, color=th["muted"], fontsize=7.5, ha="center", va="top")
    # FM harmonics made inside the unfiltered HIGH input: x3 proven by the attenuator (falls up to 20 dB);
    # x4..x9 are the smooth humps centred on n x ~98 MHz and n x 20 MHz wide
    ax.axvspan(264, 324, facecolor="none", edgecolor=th["muted"], hatch="////", lw=0, zorder=0)
    ax.text(294, -42, "FM × 3\nanalyzer-made", color=th["ink2"], fontsize=7.5, ha="center", va="top")
    for n in range(4, 10):
        fc = n * 98.0
        if fc < 955:
            ax.text(fc, -123.5, f"FM×{n}", color=th["ink2"], fontsize=7.5, ha="center", va="bottom")
    ax.plot(bf, smooth(bv, 3), color=th["muted"], lw=1.1, label="empty port (tinySA floor)")
    ax.plot(F, smooth(md, 2), color=th[ANT_COLOR["discone"]], lw=1.2, label="discone, median of 3 sweeps")
    ax.set_xlim(240, 960)
    ax.set_ylim(-126, -36)
    style(ax, th, "MHz", "dBm at the tinySA (32 kHz RBW)")
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.8), frameon=False, fontsize=8.5, labelcolor=th["ink2"],
              handlelength=1.4)
    title(fig, th, "Roof discone above 240 MHz: real stations on top of the analyzer's own FM harmonics",
          "HIGH input, median of three sweeps. FM broadcast at up to −26 dBm overdrives the unfiltered input, which then makes "
          "FM ×3…×9 humps (labelled at the bottom). Carriers above the humps are real; the floor between them is not the roof's.")
    save(fig, "discone-high", theme)


CHARTS_FN = [chart_floor_excess, chart_6m_comb, chart_birdies, chart_clock_ladder, chart_hf_noise, chart_hf_floor,
             chart_zero_span, chart_vhf_noise, chart_birdie_by_antenna, chart_discone_high]

if __name__ == "__main__":
    # a fixed hashsalt keeps clip-path ids stable, so re-running only changes charts whose data changed
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "svg.fonttype": "none",
                         "svg.hashsalt": "rf-environment"})
    for theme, th in THEMES.items():
        for fn in CHARTS_FN:
            fn(th, theme)
    print("wrote", len(list(CHARTS.glob("*.svg"))), "charts to", CHARTS)
