"""Collect receive frequencies programmed into each radio from the fleet reports."""
from paths import RF, FREQ_INDEX, CATALOG, RADIO_DATA, PROGRAMMED, HOME_QTH  # noqa: F401
import json, os, re

ROOT = str(RADIO_DATA)
FILES = {
    "TD-H9": "td-h9/exports/td-h9-fleet-report.md",
    "FTX-1": "ftx1/exports/ftx1-fleet-report.md",
    "AT-D890UV": "at-d890uv/exports/at-d890uv-fleet-report.md",
    "ID-52A": "id-52a/exports/id-52a-fleet-report.md",
    "TH-D75": "th-d75/exports/th-d75-fleet-report.md",
}
pat = re.compile(r"(?<![\d.])(\d{1,3}\.\d{3,5})(?![\d.])")
out = {}
for radio, rel in FILES.items():
    txt = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    fs = set()
    for line in txt.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        for c in cells[:6]:
            m = pat.fullmatch(c)
            if m:
                f = float(m.group(1))
                if 0.1 <= f <= 1300:
                    fs.add(round(f, 5))
    out[radio] = sorted(fs)
    print(radio, len(fs), out[radio][:5])
json.dump(out, open(PROGRAMMED, "w"))
