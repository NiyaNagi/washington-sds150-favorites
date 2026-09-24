import json, sys

z = json.load(open(sys.argv[1]))
print("rbw", z["rbw"], "mode", z["mode"])
for tr in z["targets"]:
    F, P = tr["freqs"], tr["passes"]
    n = len(F)
    mx = [max(p[i] for p in P) for i in range(n)]
    mn = [min(p[i] for p in P) for i in range(n)]
    fl = sorted(mx)[n // 4]
    peaks = [i for i in range(1, n - 1) if mx[i] >= mx[i - 1] and mx[i] >= mx[i + 1] and mx[i] - fl > 6]
    sel = []
    for i in sorted(peaks, key=lambda i: -mx[i]):
        if all(abs(i - j) > 4 for j in sel):
            sel.append(i)
    sel.sort()
    # -6 dB width of strongest
    desc = ", ".join(f"{F[i]/1e6:.4f}({mx[i]:.0f}/min{mn[i]:.0f})" for i in sel[:16])
    print(f"{tr['center']} MHz span {tr['span_khz']}k floor {fl:.1f} passes {len(P)}: {desc}")
