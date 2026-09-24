"""Feedline loss between each antenna and the tinySA, and the correction to antenna-referred noise.

Cable loss per 100 ft, f in MHz, as k1*sqrt(f) + k2*f:
  KMR400 (LMR-400 class)  0.12229, 0.00026   Times Microwave LMR-400 datasheet curve
  RG-8X                   0.31,    0.0015    fit to Belden 9258 typical values (+/-20%)
A window feed-through is not specified by the operator; it is modelled as
0.3 dB at 146 MHz scaling with sqrt(f). SMA/PL-259 adapters are ignored.
Transformer (EFHW 49:1) loss and antenna mismatch are NOT corrected, so an
Fa corrected here is still a lower bound for the EFHW.

The line attenuates antenna noise and adds its own thermal noise:
    fa_meas = fa_ant / l + (1 - 1/l)      (linear factors, l = loss ratio)
so  fa_ant  = l * fa_meas - (l - 1).
"""
import math

CABLES = {"KMR400": (0.12229, 0.00026), "RG-8X": (0.31, 0.0015)}

# antenna -> list of (cable, feet) plus a window feed-through
FEEDS = {
    "desk":    dict(runs=[], window=False, desc="Smiley on the tinySA's SMA: no feedline"),
    "efhw":    dict(runs=[("KMR400", 150), ("KMR400", 20)], window=True,
                    desc="150 ft KMR400 + window feed-through + 20 ft KMR400"),
    "sg7900":  dict(runs=[("RG-8X", 16), ("KMR400", 20)], window=True,
                    desc="16 ft RG-8X (NMO base) + window feed-through + 20 ft KMR400"),
    "discone": dict(runs=[("KMR400", 75), ("KMR400", 20)], window=True,
                    desc="75 ft KMR400 + window feed-through + 20 ft KMR400"),
}


def cable_db(cable, feet, f_mhz):
    k1, k2 = CABLES[cable]
    return (k1 * math.sqrt(f_mhz) + k2 * f_mhz) * feet / 100.0


def window_db(f_mhz):
    return 0.3 * math.sqrt(f_mhz / 146.0)


def loss_db(antenna, f_mhz):
    feed = FEEDS[antenna]
    total = sum(cable_db(c, ft, f_mhz) for c, ft in feed["runs"])
    if feed["window"]:
        total += window_db(f_mhz)
    return total


def correct_fa(fa_meas_db, antenna, f_mhz):
    """Antenna-referred Fa from Fa measured at the tinySA input."""
    l = 10 ** (loss_db(antenna, f_mhz) / 10)
    fa = 10 ** (fa_meas_db / 10)
    val = l * fa - (l - 1)
    return 10 * math.log10(val) if val > 0 else float("-inf")


if __name__ == "__main__":
    fs = [3.6, 7.1, 14.2, 28.5, 52, 73, 127, 146, 162, 223, 290, 435, 460, 770, 860, 915]
    print("MHz    " + "  ".join(f"{a:>8s}" for a in FEEDS))
    for f in fs:
        print(f"{f:6.1f} " + "  ".join(f"{loss_db(a, f):8.2f}" for a in FEEDS))
