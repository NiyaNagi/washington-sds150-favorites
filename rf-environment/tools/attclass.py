"""Classify features as real or analyzer-made from an unattenuated and an attenuated sweep.

    .venv\\Scripts\\python.exe rf-environment\\tools\\attclass.py <att0.json> <att10.json> [block_mhz]

The tinySA corrects its display for attenuation, so a real signal reads the
same with and without it, while a product generated inside the analyzer
(harmonics, intermodulation of strong inputs) falls. Only points at least
6 dB above the attenuated sweep's own floor can be judged. Each block
reports how many judgeable points held (within 3 dB) and how many fell by
more than 6 dB.
"""
import json, statistics, sys


def main():
    a = json.load(open(sys.argv[1]))
    b = json.load(open(sys.argv[2]))
    blk = float(sys.argv[3]) * 1e6 if len(sys.argv) > 3 else 10e6
    F = a["freqs"]
    A = [statistics.median(p[i] for p in a["passes"]) for i in range(len(F))]
    Bf = b["freqs"]
    B = b["passes"][0]
    bi = {round(f): i for i, f in enumerate(Bf)}
    floor_b = sorted(B)[len(B) // 5]
    print(f"attenuated floor (p20) {floor_b:.1f} dBm; blocks of {blk/1e6:g} MHz")
    print("block MHz        judged  held  fell>6  max fall   verdict")
    f0 = F[0]
    while f0 < F[-1]:
        idx = [i for i, f in enumerate(F) if f0 <= f < f0 + blk and round(f) in bi]
        judged = [(A[i], B[bi[round(F[i])]]) for i in idx if A[i] > floor_b + 6]
        held = sum(1 for x, y in judged if abs(x - y) <= 3)
        fell = sum(1 for x, y in judged if x - y > 6)
        mx = max((x - y for x, y in judged), default=0)
        verdict = "" if not judged else ("ANALYZER-MADE" if fell > held else ("real" if held >= fell else "mixed"))
        if judged:
            print(f"{f0/1e6:6.0f}-{(f0+blk)/1e6:<6.0f}  {len(judged):6d} {held:5d} {fell:7d} {mx:9.1f}   {verdict}")
        f0 += blk


if __name__ == "__main__":
    main()
