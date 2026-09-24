"""VHF/UHF external noise (Fa) per band for every surveyed antenna, vs ITU-R P.372.

    .venv\\Scripts\\python.exe rf-environment\\tools\\vhfnoise.py [survey_data_dir]

Method (same as hfnoise.py): the floor is the 20th percentile of the per-point
minimum across passes, so carriers, birdies and bursts are excluded. The
analyzer's own floor (empty-port baseline, same RBW, same input) is
subtracted in linear power. Fa = N[dBm/Hz] + 174 with the RBW as the noise
bandwidth. Feedline and window-joint loss are then corrected to the antenna
terminals (lineloss.py). Within 1 dB of the analyzer floor a band is "below
detection" and only the detection limit (also referred to the antenna) is
reported as an upper bound.

ITU-R P.372 man-made-noise medians (Fa = c - d log f MHz) are defined from
0.3 to 250 MHz; no reference is given above that.
"""
import json, math, re, sys
from pathlib import Path
from lineloss import correct_fa, loss_db, FEEDS

DEFAULT = Path(__file__).resolve().parents[1] / "2026-09-23-survey" / "data"
ITU = [("city", 76.8, 27.7), ("residential", 72.5, 27.7), ("rural", 67.2, 27.7), ("galactic", 52.0, 23.0)]

BANDS = [
    ("6 m", 50, 54), ("60–86 MHz", 60, 86), ("Airband", 118, 137), ("2 m", 144, 148), ("VHF-high", 150, 174),
    ("1.25 m", 222, 225), ("240–340 MHz", 240, 340), ("70 cm", 420, 450), ("UHF 450–470", 450, 470),
    ("700 PS", 769, 775), ("800 PS", 851, 869), ("902–928", 902, 928),
]
LOW_WIDE_BASE = "p1__Lopen_wide.json"
ANTENNAS = {
    "desk": dict(label="Smiley on the desk", bands={
        "6 m": ("p2__L_6m.json", "p1__Lopen_6m.json"), "60–86 MHz": ("p2__L_wide.json", LOW_WIDE_BASE),
        "Airband": ("p2__L_air.json", "p1__Lopen_air.json"), "2 m": ("p2__L_2m.json", "p1__Lopen_2m.json"),
        "VHF-high": ("p2__L_vhf.json", "p1__Lopen_vhf.json"), "1.25 m": ("p2__L_220.json", "p1__Lopen_220.json"),
        "240–340 MHz": ("p2__L_wide.json", LOW_WIDE_BASE),
        "70 cm": ("p1__H_70cm.json", "p2__Hopen_70cm.json"), "UHF 450–470": ("p1__H_uhf.json", "p2__Hopen_70cm.json")}),
    "efhw": dict(label="EFHW (HF wire, roof feed)", bands={
        "6 m": ("p3__E_lo.json", "p1__Lopen_6m.json"), **{b: ("p3__E_wide.json", LOW_WIDE_BASE) for b in (
            "60–86 MHz", "Airband", "2 m", "VHF-high", "1.25 m", "240–340 MHz")}}),
    "sg7900": dict(label="SG7900 under the porch", bands={
        "6 m": ("p4__S_6m.json", "p1__Lopen_6m.json"), "60–86 MHz": ("p4__S_wide.json", LOW_WIDE_BASE),
        "Airband": ("p4__S_air.json", "p1__Lopen_air.json"), "2 m": ("p4__S_2m.json", "p1__Lopen_2m.json"),
        "VHF-high": ("p4__S_vhf.json", "p1__Lopen_vhf.json"), "1.25 m": ("p4__S_220.json", "p1__Lopen_220.json"),
        "240–340 MHz": ("p4__S_wide.json", LOW_WIDE_BASE),
        "70 cm": ("p5__SH_70cm.json", "p2__Hopen_70cm.json"), "UHF 450–470": ("p5__SH_uhf.json", "p2__Hopen_70cm.json")}),
    "discone": dict(label="D3000N discone on the roof", bands={
        "6 m": ("p6__D_6m.json", "p1__Lopen_6m.json"), "60–86 MHz": ("p6__D_wide.json", LOW_WIDE_BASE),
        "Airband": ("p6__D_air.json", "p1__Lopen_air.json"), "2 m": ("p6__D_2m.json", "p1__Lopen_2m.json"),
        "VHF-high": ("p6__D_vhf.json", "p1__Lopen_vhf.json"), "1.25 m": ("p6__D_220.json", "p1__Lopen_220.json"),
        "240–340 MHz": ("p6__D_wide.json", LOW_WIDE_BASE),
        "70 cm": ("p7__DH_70cm.json", "p2__Hopen_70cm.json"), "UHF 450–470": ("p7__DH_uhf.json", "p2__Hopen_70cm.json"),
        "700 PS": ("p7__DH_700.json", "p4__Hopen_700.json"), "800 PS": ("p7__DH_800.json", "p4__Hopen_800.json"),
        "902–928": ("p7__DH_900.json", "p4__Hopen_900.json")}),
}
HIGH_INPUT = {"70 cm", "UHF 450–470", "700 PS", "800 PS", "902–928"}
# The roof discone feeds FM broadcast at up to -26 dBm into the unfiltered HIGH input, which then makes FM
# harmonics x3..x9 (humps centred on n x ~98 MHz, n x 20 MHz wide) across 264-960 MHz. Those bands measure the
# analyzer, not the roof: report them only as upper bounds until an FM band-stop filter is fitted.
MASKED = {("discone", b): "FM harmonics made in the unfiltered HIGH input" for b in HIGH_INPUT}


def rbw_hz(rec):
    return float(re.match(r"([\d.]+)", rec["rbw_actual"]).group(1)) * 1e3


def floor_p20(rec, lo, hi):
    idx = [i for i, f in enumerate(rec["freqs"]) if lo * 1e6 <= f <= hi * 1e6]
    mins = sorted(min(p[i] for p in rec["passes"]) for i in idx)
    return mins[int(len(mins) * 0.2)]


_cache = {}


def _load(path):
    if path not in _cache:
        _cache[path] = json.load(open(path))
    return _cache[path]


def fa_of(data, pair, lo, hi, antenna):
    a_path, b_path = data / pair[0], data / pair[1]
    if not (a_path.exists() and b_path.exists()):
        return None
    ant, base = _load(a_path), _load(b_path)
    rbw = rbw_hz(ant)
    a, b = floor_p20(ant, lo, hi), floor_p20(base, lo, hi)
    fc = math.sqrt(lo * hi)
    inst_meas = b - 10 * math.log10(rbw) + 174
    out = dict(ant_dbm=a, inst_dbm=b, rbw=rbw, loss_db=loss_db(antenna, fc),
               limit=correct_fa(inst_meas, antenna, fc), fa_meas=None, fa=None)
    if a - b >= 1.0:
        ext = 10 * math.log10(10 ** (a / 10) - 10 ** (b / 10))
        out["fa_meas"] = ext - 10 * math.log10(rbw) + 174
        out["fa"] = correct_fa(out["fa_meas"], antenna, fc)
    return out


def itu(lo, hi):
    fc = math.sqrt(lo * hi)
    return None if fc > 250 else {n: c - d * math.log10(fc) for n, c, d in ITU}


def compute(data=DEFAULT):
    rows = []
    for name, lo, hi in BANDS:
        row = dict(band=name, lo=lo, hi=hi, itu=itu(lo, hi), high_input=name in HIGH_INPUT, ant={})
        for key, spec in ANTENNAS.items():
            pair = spec["bands"].get(name)
            v = fa_of(data, pair, lo, hi, key) if pair else None
            if v and (key, name) in MASKED:
                # keep the value only as an upper bound
                v["limit"] = v["fa"] if v["fa"] is not None else v["limit"]
                v["fa"] = None
                v["masked"] = MASKED[(key, name)]
            row["ant"][key] = v
        rows.append(row)
    return rows


def fmt(v):
    if v is None:
        return "      —"
    if v["fa"] is None:
        return f"<{v['limit']:5.1f}{'m' if v.get('masked') else ' '}"
    return f"{v['fa']:7.1f}"


def main():
    data = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    keys = list(ANTENNAS)
    print("Fa at the antenna terminals (dB above kT0B); '<' = upper bound: below detection, or 'm' = masked by "
          "FM harmonics made in the analyzer")
    print(f"{'band':13s}" + "".join(f"{k:>9s}" for k in keys) + "    city   rural")
    for r in compute(data):
        i = r["itu"]
        tail = f"  {i['city']:6.1f}  {i['rural']:6.1f}" if i else "   (no ITU curve)"
        print(f"{r['band']:13s}" + "".join(f"  {fmt(r['ant'][k])}" for k in keys) + tail)
    print("feeds: " + "; ".join(f"{k}: {FEEDS[k]['desc']}" for k in keys))


if __name__ == "__main__":
    main()
