from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import json, sys

p = json.load(open(PROGRAMMED))
for arg in sys.argv[1:]:
    fq, tol = (float(x) for x in arg.split(":"))
    hits = sorted({(f, r) for r, fs in p.items() for f in fs if abs(f - fq) <= tol})
    print(f"{fq} +/-{tol*1e3:g}k:", ", ".join(f"{r} {f}" for f, r in hits) or "-")
