from __future__ import annotations

import base64
import csv
import html
import math
import re
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
BANDS = [
    ("6 m", 50.0, 54.0),
    ("FM Broadcast", 88.0, 108.0),
    ("VHF Air", 118.0, 137.0),
    ("2 m", 144.0, 148.0),
    ("VHF Public Safety / LMR", 150.0, 174.0),
    ("Marine VHF", 156.0, 162.0),
    ("Railroad", 159.81, 161.565),
    ("NOAA Weather", 162.4, 162.55),
    ("1.25 m", 222.0, 225.0),
    ("Military Air", 225.0, 400.0),
    ("Federal UHF", 406.1, 420.0),
    ("70 cm", 420.0, 450.0),
    ("UHF Public Safety / LMR", 450.0, 470.0),
    ("T-Band", 470.0, 512.0),
    ("700 MHz Public Safety DL", 769.0, 775.0),
    ("800 MHz Public Safety DL", 851.0, 869.0),
    ("33 cm", 902.0, 928.0),
    ("900 MHz Trunking DL", 935.0, 941.0),
    ("UAT", 978.0, 978.0),
    ("ADS-B", 1090.0, 1090.0),
]


def natural_key(value: str) -> list[object]:
    return [float(part) if re.fullmatch(r"\d+(?:\.\d+)?", part) else part.lower()
            for part in re.split(r"(\d+(?:\.\d+)?)", value)]


def read_touchstone(path: Path) -> tuple[np.ndarray, np.ndarray]:
    unit_factor = 1.0
    data_format = "MA"
    rows: list[tuple[float, float, float]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        if line.startswith("#"):
            fields = line[1:].upper().split()
            unit_factor = {"HZ": 1.0, "KHZ": 1e3, "MHZ": 1e6, "GHZ": 1e9}[fields[0]]
            data_format = fields[2]
            continue
        values = line.split()
        if len(values) >= 3:
            rows.append((float(values[0]) * unit_factor, float(values[1]), float(values[2])))
    values = np.asarray(rows, dtype=float)
    if data_format == "RI":
        gamma = values[:, 1] + 1j * values[:, 2]
    elif data_format == "MA":
        gamma = values[:, 1] * np.exp(1j * np.deg2rad(values[:, 2]))
    elif data_format == "DB":
        gamma = 10 ** (values[:, 1] / 20) * np.exp(1j * np.deg2rad(values[:, 2]))
    else:
        raise ValueError(f"Unsupported Touchstone format {data_format} in {path}")
    return values[:, 0] / 1e6, gamma


def swr(gamma: np.ndarray | complex) -> np.ndarray:
    magnitude = np.abs(gamma)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = (1 + magnitude) / (1 - magnitude)
    return np.where(magnitude >= 1, np.inf, result)


def interpolated_swr(freq: np.ndarray, gamma: np.ndarray, target_mhz: float) -> float:
    real = np.interp(target_mhz, freq, gamma.real)
    imag = np.interp(target_mhz, freq, gamma.imag)
    return float(swr(complex(real, imag)))


def format_swr(value: float) -> str:
    return "∞" if not math.isfinite(value) else f"{value:.2f}"


def chart_label(item: dict[str, object]) -> str:
    family = str(item["family"])
    stem = Path(item["path"]).stem
    if family == "Anteena Extendable":
        match = re.search(r"Extendable-(\d+(?:\.\d+)?)-", stem, re.IGNORECASE)
        return f"Generic extendable — {match.group(1) if match else stem}"
    if family == "RH789":
        match = re.search(r"RH789-(\d+(?:\.\d+)?)-", stem, re.IGNORECASE)
        return f"RH789 — {match.group(1) if match else stem}"
    return {
        "Diamond SRH77CA + BNC Adapter": "Diamond SRH77CA",
        "Remtronix 920": "Remtronix 920",
        "TID TD771 + SMA + BNC Adapter": "TID TD771",
    }.get(family, family)


files = sorted(ROOT.rglob("*.s1p"), key=lambda p: natural_key(str(p.relative_to(ROOT))))
if not files:
    raise SystemExit(f"No .s1p files found beneath {ROOT}")

measurements: list[dict[str, object]] = []
for path in files:
    freq, gamma = read_touchstone(path)
    label = f"{path.parent.name} / {path.stem}"
    centers = {name: interpolated_swr(freq, gamma, (low + high) / 2) for name, low, high in BANDS}
    measurements.append({"path": path, "label": label, "family": path.parent.name, "freq": freq,
                         "gamma": gamma, "centers": centers})

csv_path = ROOT / "swr-comparison-common-ham-bands.csv"
with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
    writer = csv.writer(stream)
    writer.writerow(["Measurement", *[f"{name} center ({(low + high) / 2:g} MHz) estimated SWR"
                                       for name, low, high in BANDS]])
    for item in measurements:
        centers = item["centers"]
        writer.writerow([item["label"], *[("inf" if not math.isfinite(centers[name]) else f"{centers[name]:.4f}")
                                          for name, _, _ in BANDS]])

fig_height = max(9.0, len(measurements) * 0.34)
band_groups = [("VHF and lower frequencies", BANDS[:9]), ("UHF and microwave frequencies", BANDS[9:])]
fig, axes = plt.subplots(2, 1, figsize=(18, fig_height * 2.15), constrained_layout=True)
images = []
short_labels = [chart_label(item) for item in measurements]
family_breaks = [index - 0.5 for index in range(1, len(measurements))
                 if measurements[index]["family"] != measurements[index - 1]["family"]]
for ax, (group_title, group_bands) in zip(axes, band_groups):
    matrix = np.array([[min(float(item["centers"][name]), 10.0) for name, _, _ in group_bands]
                       for item in measurements])
    image = ax.imshow(matrix, aspect="auto", cmap="RdYlGn_r", vmin=1, vmax=5)
    images.append(image)
    tick_labels = [f"{textwrap.fill(name, 16)}\n{(low + high) / 2:g} MHz" for name, low, high in group_bands]
    ax.set_xticks(range(len(group_bands)), tick_labels, fontsize=8, rotation=30, ha="right", rotation_mode="anchor")
    ax.set_yticks(range(len(measurements)), short_labels, fontsize=8)
    ax.set_title(group_title, fontsize=13, fontweight="bold", pad=12)
    for boundary in family_breaks:
        ax.axhline(boundary, color="white", linewidth=2.2)
    for row, item in enumerate(measurements):
        for col, (name, _, _) in enumerate(group_bands):
            value = float(item["centers"][name])
            text = "∞" if not math.isfinite(value) else (">10" if value > 10 else f"{value:.1f}")
            ax.text(col, row, text, ha="center", va="center", fontsize=7,
                    color="white" if matrix[row, col] >= 4.2 else "black")
fig.suptitle("Estimated SWR at common U.S. amateur and scanner-band centers\n"
             "Complex interpolation of 11.5 MHz-spaced samples", fontsize=16, fontweight="bold")
fig.colorbar(images[0], ax=axes, location="right", shrink=0.72, pad=0.02, label="SWR (color capped at 5)")
heatmap_path = ROOT / "swr-comparison-common-ham-bands.png"
fig.savefig(heatmap_path, dpi=180, bbox_inches="tight")
plt.close(fig)

families = sorted({str(item["family"]) for item in measurements}, key=natural_key)
family_plot_paths: list[Path] = []
for family in families:
    members = [item for item in measurements if item["family"] == family]
    fig, ax = plt.subplots(figsize=(13, 6), constrained_layout=True)
    for item in members:
        freq = item["freq"]
        trace = np.clip(swr(item["gamma"]), 1, 10)
        ax.plot(freq, trace, linewidth=1.1, label=Path(item["path"]).stem)
    for name, low, high in BANDS:
        ax.axvspan(low, high, color="#4c78a8", alpha=0.10)
    ax.axhline(2, color="green", linestyle="--", linewidth=1, label="SWR 2:1")
    ax.axhline(3, color="orange", linestyle="--", linewidth=1, label="SWR 3:1")
    ax.set(xlabel="Frequency (MHz)", ylabel="SWR (display capped at 10)", ylim=(1, 10), xlim=(50, 1200),
           title=f"{family}: measured broadband SWR")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncol=3, loc="upper right")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", family).strip("-")
    plot_path = ROOT / f"swr-{safe}.png"
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)
    family_plot_paths.append(plot_path)

best_rows: list[str] = []
for name, low, high in BANDS:
    ranked = sorted(measurements, key=lambda item: float(item["centers"][name]))
    for rank, item in enumerate(ranked[:5], 1):
        value = float(item["centers"][name])
        best_rows.append(f"<tr><td>{html.escape(name)}</td><td>{rank}</td><td>{html.escape(str(item['label']))}</td>"
                         f"<td>{format_swr(value)}</td></tr>")

family_rows: list[str] = []
for family in families:
    members = [item for item in measurements if item["family"] == family]
    cells = [f"<td>{html.escape(family)}</td>"]
    for name, _, _ in BANDS:
        best = min(members, key=lambda item: float(item["centers"][name]))
        cells.append(f"<td>{format_swr(float(best['centers'][name]))}<br><small>{html.escape(Path(best['path']).stem)}</small></td>")
    family_rows.append("<tr>" + "".join(cells) + "</tr>")

all_rows: list[str] = []
for item in measurements:
    cells = [f"<td>{html.escape(str(item['label']))}</td>"]
    cells.extend(f"<td>{format_swr(float(item['centers'][name]))}</td>" for name, _, _ in BANDS)
    all_rows.append("<tr>" + "".join(cells) + "</tr>")


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")

band_headers = "".join(f"<th>{html.escape(name)}<br><small>{low:g}–{high:g} MHz</small></th>" for name, low, high in BANDS)
plot_sections = "".join(f"<h2>{html.escape(family)}</h2><img src='{data_uri(path)}' alt='{html.escape(family)} SWR plot'>"
                        for family, path in zip(families, family_plot_paths))
report = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Antenna SWR comparison</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;max-width:1500px;margin:2rem auto;padding:0 1rem;color:#202124}}
h1,h2{{color:#17365d}} .warning{{background:#fff4ce;border-left:5px solid #d99b00;padding:1rem}}
table{{border-collapse:collapse;width:100%;margin:1rem 0 2rem}} th,td{{border:1px solid #ccc;padding:.45rem;text-align:left}}
th{{background:#e9f2fb;position:sticky;top:0}} tr:nth-child(even){{background:#f8f8f8}} small{{color:#555}}
img{{display:block;max-width:100%;height:auto;margin:1rem auto 2.5rem;border:1px solid #ddd}}
.table-scroll{{overflow-x:auto;max-width:100%;margin-bottom:2rem}}
.wide{{min-width:2800px;margin-bottom:0}} .wide th:first-child,.wide td:first-child{{position:sticky;left:0;z-index:1;background:#fff;min-width:260px}}
.wide th:first-child{{z-index:3;background:#e9f2fb}}
</style></head><body>
<h1>Antenna SWR comparison</h1>
<p>Analyzed {len(measurements)} Touchstone sweeps, each covering 50–1200 MHz with 101 points. The comparison includes amateur, aviation, broadcast FM, NOAA weather, marine, railroad, land-mobile/public-safety, trunking, UAT, and ADS-B targets.</p>
<div class='warning'><strong>Resolution limitation:</strong> samples are 11.5 MHz apart. Every listed amateur band is narrower than, or comparable to, that spacing. Band-center values below are estimates produced by interpolating complex S11 (not SWR). They are useful for coarse comparison, but they do not prove the true minimum, maximum, or full-band SWR. Re-sweep each band at finer resolution before transmitting or making tuning decisions.</div>
<h2>Best configuration in each antenna family</h2>
<div class='table-scroll'><table class='wide'><thead><tr><th>Family</th>{band_headers}</tr></thead><tbody>{''.join(family_rows)}</tbody></table></div>
<h2>Top five measurements by estimated band-center SWR</h2>
<table><thead><tr><th>Band</th><th>Rank</th><th>Measurement</th><th>Estimated SWR</th></tr></thead><tbody>{''.join(best_rows)}</tbody></table>
<h2>All measurements heatmap</h2><img src='{data_uri(heatmap_path)}' alt='SWR comparison heatmap'>
<h2>All estimated band-center values</h2>
<div class='table-scroll'><table class='wide'><thead><tr><th>Measurement</th>{band_headers}</tr></thead><tbody>{''.join(all_rows)}</tbody></table></div>
<h1>Broadband family plots</h1>{plot_sections}
<p><small>Generated from files beneath {html.escape(str(ROOT))}. Values use a 50 Ω reference impedance. Scanner-band matching is shown as a relative receive-antenna comparison; receive performance does not require a transmitter-grade 2:1 SWR.</small></p>
</body></html>"""
report_path = ROOT / "swr-comparison-report.html"
report_path.write_text(report, encoding="utf-8")

print(f"Analyzed {len(measurements)} files")
print(f"Report: {report_path}")
print(f"CSV: {csv_path}")
print(f"Heatmap: {heatmap_path}")
for name, low, high in BANDS:
    best = min(measurements, key=lambda item: float(item["centers"][name]))
    print(f"{name} ({low:g}-{high:g} MHz): {best['label']} = {format_swr(float(best['centers'][name]))}")
