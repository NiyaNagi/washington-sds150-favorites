#!/usr/bin/env python3
"""Generate the JYR8010 two-choke installed-system report and comparison."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path
from types import ModuleType

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


COLORS = {
    "historical": "#315c8c",
    "current": "#b11f4b",
    "repeat": "#23856d",
    "muted": "#77716d",
    "grid": "#d8d3cd",
}


def load_base() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "generate_report.py"
    spec = importlib.util.spec_from_file_location("jyr8010_base_report", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load base report generator from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def interpolate_complex(
    target: np.ndarray, source: np.ndarray, values: np.ndarray
) -> np.ndarray:
    if target[0] < source[0] or target[-1] > source[-1]:
        raise ValueError("interpolation target extends outside source range")
    return np.interp(target, source, values.real) + 1j * np.interp(
        target, source, values.imag
    )


def plot_comparison_zooms(
    base: ModuleType,
    output: Path,
    historical_f: np.ndarray,
    historical_metrics: dict[str, np.ndarray],
    current_f: np.ndarray,
    current_metrics: dict[str, np.ndarray],
    historical_summary: list[dict[str, object]],
    current_summary: list[dict[str, object]],
) -> None:
    fig, axes = plt.subplots(4, 2, figsize=(15, 18), constrained_layout=True)
    for axis, band, old, new in zip(
        axes.flat, base.BANDS, historical_summary, current_summary
    ):
        name, lower, upper = band
        old_selected = (historical_f >= lower) & (historical_f <= upper)
        new_selected = (current_f >= lower) & (current_f <= upper)
        axis.plot(
            historical_f[old_selected] / 1e6,
            historical_metrics["swr"][old_selected],
            color=COLORS["historical"],
            linewidth=1.7,
            label="August 16 historical",
        )
        axis.plot(
            current_f[new_selected] / 1e6,
            current_metrics["swr"][new_selected],
            color=COLORS["current"],
            linewidth=1.7,
            label="August 28 chokes + counterpoise",
        )
        axis.axhline(2, color=COLORS["muted"], linestyle="--", linewidth=0.8)
        axis.scatter(
            float(old["minimum_swr_frequency_mhz"]),
            float(old["minimum_swr"]),
            color=COLORS["historical"],
            s=24,
        )
        axis.scatter(
            float(new["minimum_swr_frequency_mhz"]),
            float(new["minimum_swr"]),
            color=COLORS["current"],
            s=24,
        )
        maximum = max(
            np.nanmax(historical_metrics["swr"][old_selected]),
            np.nanmax(current_metrics["swr"][new_selected]),
        )
        axis.set(
            title=(
                f"{name}: {float(old['minimum_swr']):.2f} -> "
                f"{float(new['minimum_swr']):.2f}"
            ),
            xlabel="Frequency (MHz)",
            ylabel="SWR",
            xlim=(lower / 1e6, upper / 1e6),
            ylim=(1, max(2.2, min(8, maximum * 1.08))),
        )
        axis.grid(True, alpha=0.7)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2)
    fig.suptitle(
        "JYR8010 supported-band comparison\n"
        "Historical configuration versus current two-choke + counterpoise system",
        fontsize=17,
    )
    fig.savefig(output / "historical_comparison_swr_zooms.png", dpi=200)
    plt.close(fig)


def plot_change_scorecard(
    output: Path,
    historical: list[dict[str, object]],
    current: list[dict[str, object]],
) -> None:
    names = [str(item["band"]) for item in current]
    old_minimum = [float(item["minimum_swr"]) for item in historical]
    new_minimum = [float(item["minimum_swr"]) for item in current]
    old_coverage = [
        float(item["coverage_percent"]["2.0"])  # type: ignore[index]
        for item in historical
    ]
    new_coverage = [
        float(item["coverage_percent"]["2.0"])  # type: ignore[index]
        for item in current
    ]
    y = np.arange(len(names))
    fig, (left, right) = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=True)
    left.barh(
        y + 0.18,
        old_minimum,
        height=0.35,
        color=COLORS["historical"],
        label="Historical",
    )
    left.barh(
        y - 0.18,
        new_minimum,
        height=0.35,
        color=COLORS["current"],
        label="Choked + counterpoise",
    )
    left.axvline(2, color=COLORS["muted"], linestyle="--")
    left.set_yticks(y, names)
    left.invert_yaxis()
    left.set_xlabel("Minimum SWR")
    left.set_title("Best match in each advertised band")
    left.grid(True, axis="x", alpha=0.7)
    left.legend()

    x = np.arange(len(names))
    width = 0.36
    right.bar(
        x - width / 2,
        old_coverage,
        width,
        color=COLORS["historical"],
        label="Historical",
    )
    right.bar(
        x + width / 2,
        new_coverage,
        width,
        color=COLORS["current"],
        label="Choked + counterpoise",
    )
    right.set_xticks(x, names, rotation=45)
    right.set_ylim(0, 100)
    right.set_ylabel("Percent of band at SWR <= 2:1")
    right.set_title("No-tuner 2:1 coverage")
    right.grid(True, axis="y", alpha=0.7)
    right.legend()
    fig.suptitle("Observed supported-band changes", fontsize=17)
    fig.savefig(output / "historical_change_scorecard.png", dpi=200)
    plt.close(fig)


def plot_repeatability(
    base: ModuleType,
    output: Path,
    frequencies: np.ndarray,
    first: np.ndarray,
    repeat: np.ndarray,
) -> dict[str, float]:
    first_metrics = base.calculate_metrics(first)
    repeat_metrics = base.calculate_metrics(repeat)
    complex_delta = np.abs(first - repeat)
    swr_delta = np.abs(first_metrics["swr"] - repeat_metrics["swr"])
    result = {
        "median_complex_s11_delta": float(np.nanmedian(complex_delta)),
        "p95_complex_s11_delta": float(np.nanpercentile(complex_delta, 95)),
        "maximum_complex_s11_delta": float(np.nanmax(complex_delta)),
        "median_swr_delta": float(np.nanmedian(swr_delta)),
        "p95_swr_delta": float(np.nanpercentile(swr_delta, 95)),
        "maximum_swr_delta": float(np.nanmax(swr_delta)),
    }
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), constrained_layout=True)
    axes[0].semilogx(
        frequencies / 1e6,
        complex_delta,
        color=COLORS["repeat"],
        linewidth=0.8,
    )
    axes[0].set(xlabel="Frequency (MHz)", ylabel="Absolute complex S11 delta")
    axes[0].grid(True, which="both", alpha=0.7)
    axes[1].semilogx(
        frequencies / 1e6,
        np.minimum(swr_delta, 0.3),
        color=COLORS["current"],
        linewidth=0.8,
    )
    axes[1].set(
        xlabel="Frequency (MHz)",
        ylabel="Absolute SWR delta (clipped at 0.3)",
    )
    axes[1].grid(True, which="both", alpha=0.7)
    fig.suptitle(
        "Unchanged choked-system repeatability\n"
        f"Median complex delta {result['median_complex_s11_delta']:.5f}; "
        f"median SWR delta {result['median_swr_delta']:.5f}",
        fontsize=16,
    )
    fig.savefig(output / "repeatability.png", dpi=200)
    plt.close(fig)
    return result


def plot_open_path_comparison(
    output: Path,
    unchoked_f: np.ndarray,
    unchoked_gamma: np.ndarray,
    choked_f: np.ndarray,
    choked_gamma: np.ndarray,
) -> dict[str, object]:
    frequencies = choked_f
    unchoked = interpolate_complex(frequencies, unchoked_f, unchoked_gamma)
    unchoked_magnitude = np.abs(unchoked)
    choked_magnitude = np.abs(choked_gamma)
    with np.errstate(divide="ignore"):
        unchoked_apparent = -20.0 * np.log10(unchoked_magnitude) / 2.0
        choked_apparent = -20.0 * np.log10(choked_magnitude) / 2.0
    samples: dict[str, dict[str, float]] = {}
    for frequency in (3_500_000, 7_000_000, 14_000_000, 21_000_000, 28_000_000, 54_000_000):
        index = int(np.argmin(np.abs(frequencies - frequency)))
        samples[f"{frequency / 1e6:g}_mhz"] = {
            "unchoked_apparent_one_way_attenuation_db": float(
                unchoked_apparent[index]
            ),
            "choked_apparent_one_way_attenuation_db": float(
                choked_apparent[index]
            ),
            "observed_delta_db": float(
                choked_apparent[index] - unchoked_apparent[index]
            ),
        }
    result: dict[str, object] = {
        "unchoked_baseline": {
            "captured_at": "2026-08-23T20:41:49.618104-07:00",
            "calibration_created_at": "2026-08-23T20:32:58.778082-07:00",
        },
        "two_choke_path": {
            "captured_at": "2026-08-28T22:16:20.231084-07:00",
            "calibration_created_at": "2026-08-28T22:06:04.362381-07:00",
        },
        "method": (
            "Far-end-open one-port comparison. Apparent one-way attenuation is "
            "-20*log10(|Gamma|)/2 and is valid as line loss only for an ideal "
            "open on a uniform, well-matched line."
        ),
        "interpretation_limit": (
            "This is a cross-day, cross-calibration comparison. The window "
            "transition, connectors, and chokes introduce discontinuities and "
            "multiple reflections. This is a plausibility comparison, not "
            "measured insertion loss, common-mode impedance, or a controlled "
            "estimate of the components' added loss."
        ),
        "samples": samples,
    }
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), constrained_layout=True)
    axes[0].semilogx(
        frequencies / 1e6,
        unchoked_magnitude,
        color=COLORS["historical"],
        linewidth=1,
        label="Unchoked feed path",
    )
    axes[0].semilogx(
        frequencies / 1e6,
        choked_magnitude,
        color=COLORS["current"],
        linewidth=1,
        label="Two-choke feed path",
    )
    axes[0].set(xlabel="Frequency (MHz)", ylabel="Far-end-open |Gamma|", ylim=(0, 1.05))
    axes[0].grid(True, which="both", alpha=0.7)
    axes[0].legend()
    axes[1].semilogx(
        frequencies / 1e6,
        unchoked_apparent,
        color=COLORS["historical"],
        linewidth=1,
        label="Unchoked apparent attenuation",
    )
    axes[1].semilogx(
        frequencies / 1e6,
        choked_apparent,
        color=COLORS["current"],
        linewidth=1,
        label="Two-choke apparent attenuation",
    )
    axes[1].set(xlabel="Frequency (MHz)", ylabel="Apparent one-way attenuation (dB)")
    axes[1].grid(True, which="both", alpha=0.7)
    axes[1].legend()
    fig.suptitle(
        "Far-end-open feed-path diagnostic (cross-day, cross-calibration)\n"
        "Does not measure insertion loss or common-mode choking impedance",
        fontsize=16,
    )
    fig.savefig(output / "open_path_choke_comparison.png", dpi=200)
    plt.close(fig)
    return result


def plot_installation(output: Path) -> None:
    fig, axis = plt.subplots(figsize=(17, 7), constrained_layout=True)
    x = [0, 2.0, 4.0, 5.5, 8.0, 10.0, 12.0, 14.5]
    labels = [
        "Radio / NanoVNA\nCH0 reference",
        "25 ft LS400\ninside office",
        "Choke 1 at window\n3 ft RG8X\n11 turns, Mix 31",
        "Window flat-ribbon\ntransition",
        "75 ft LS400\noutdoors",
        "Choke 2 at feedpoint\n3 ft RG8X\n11 turns, Mix 31",
        "JYR8010 transformer",
        "40 m radiator",
    ]
    axis.plot(x, [0] * len(x), color=COLORS["muted"], linewidth=3)
    for index, (position, label) in enumerate(zip(x, labels)):
        axis.scatter(position, 0, color=COLORS["current"], s=130, zorder=4)
        axis.text(
            position,
            0.52 if index % 2 else -0.72,
            label,
            ha="center",
            va="center",
            fontsize=10,
            bbox={"facecolor": "white", "edgecolor": COLORS["grid"], "alpha": 0.95},
        )
    axis.annotate(
        "16 ft counterpoise on dedicated terminal\nalong ground, opposite radiator",
        xy=(12, 0),
        xytext=(12, -1.55),
        ha="center",
        arrowprops={"arrowstyle": "->", "color": COLORS["muted"]},
    )
    axis.set_xlim(-1, 15.5)
    axis.set_ylim(-2.1, 1.55)
    axis.axis("off")
    axis.set_title(
        "August 28 JYR8010 installed-system measurement path\n"
        "106 ft of coax plus the window transition; two 11-turn Mix 31 chokes",
        fontsize=16,
    )
    fig.savefig(output / "installed_system_layout.png", dpi=200)
    plt.close(fig)


def comparison_table(
    historical: list[dict[str, object]],
    current: list[dict[str, object]],
) -> str:
    rows = [
        "| Band | Historical best | Current best | Best-SWR change | "
        "Frequency shift | <=2:1 coverage change |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for old, new in zip(historical, current):
        old_coverage = float(old["coverage_percent"]["2.0"])  # type: ignore[index]
        new_coverage = float(new["coverage_percent"]["2.0"])  # type: ignore[index]
        rows.append(
            f"| {new['band']} | {float(old['minimum_swr']):.2f} at "
            f"{float(old['minimum_swr_frequency_mhz']):.6f} MHz | "
            f"{float(new['minimum_swr']):.2f} at "
            f"{float(new['minimum_swr_frequency_mhz']):.6f} MHz | "
            f"{float(new['minimum_swr']) - float(old['minimum_swr']):+.2f} | "
            f"{(int(new['minimum_swr_frequency_hz']) - int(old['minimum_swr_frequency_hz'])) / 1e3:+.1f} kHz | "
            f"{old_coverage:.0f}% -> {new_coverage:.0f}% |"
        )
    return "\n".join(rows)


def write_readme(
    base: ModuleType,
    output: Path,
    summaries: list[dict[str, object]],
    historical: list[dict[str, object]],
    repeatability: dict[str, float],
    open_comparison: dict[str, object],
) -> None:
    best = min(summaries, key=lambda item: float(item["minimum_swr"]))
    full_two_to_one = [
        str(item["band"])
        for item in summaries
        if float(item["maximum_swr"]) <= 2.0
    ]
    samples = open_comparison["samples"]
    assert isinstance(samples, dict)
    sample_7 = samples["7_mhz"]
    sample_28 = samples["28_mhz"]
    sample_54 = samples["54_mhz"]
    assert isinstance(sample_7, dict)
    assert isinstance(sample_28, dict)
    assert isinstance(sample_54, dict)
    content = f"""# JYR8010 EFHW: two-choke office-feed installation

This package applies the same supported-band analysis as the original JYR8010
report to a new installed-system measurement from 0.5 through 54 MHz.

## Current configuration

- JYR8010-150W, 40 m radiating element, nominal 1:49/1:64 transformer.
- 75 ft LS400 outdoors, window flat-ribbon transition, and 25 ft LS400 inside
  the office.
- Two common-mode chokes, each **3 ft RG8X wound 11 turns through one Mix 31
  FT240-size toroid**.
- Window choke: immediately before the 25 ft indoor feed line.
- Feedpoint choke: immediately before the JYR8010 transformer.
- 16 ft counterpoise on the transformer's dedicated terminal, along the ground
  opposite the radiator.
- VNA reference plane: office-side PL-259/SO-239 adapter on CH0/Port 1.
- Total coax in the measured path: approximately 106 ft plus the flat-ribbon
  transition.

![Installed system layout](charts/installed_system_layout.png)

## Current results

- Best advertised-band match: **{best['band']} at
  {float(best['minimum_swr_frequency_mhz']):.6f} MHz, SWR
  {float(best['minimum_swr']):.2f}**.
- Full advertised bands at or below 2:1: **{", ".join(full_two_to_one)}**.
- Two unchanged sweeps repeated with median complex-S11 delta
  **{repeatability['median_complex_s11_delta']:.5f}** and median SWR delta
  **{repeatability['median_swr_delta']:.5f}**.

{base.markdown_table(summaries)}

## Standard JYR8010 visuals

### Supported-band SWR zooms

![Supported-band SWR zooms](charts/supported_band_swr_zooms.png)

### Performance scorecard

![Band performance scorecard](charts/band_performance_scorecard.png)

### Usable bandwidth

![Usable bandwidth](charts/usable_bandwidth_by_threshold.png)

### Feed-point impedance at the office-side reference plane

![Supported-band impedance](charts/supported_band_impedance.png)

### Return loss

![Supported-band return loss](charts/supported_band_return_loss.png)

### Smith chart

![Supported-band Smith chart](charts/supported_bands_smith_chart.png)

### Supported-band overview

![Supported-band overview](charts/supported_bands_log_overview.png)

### Repeatability

![Repeatability](charts/repeatability.png)

## Calibration and diagnostics

- Fresh ideal one-port software OSL: 0.5-54 MHz, 40,001 points, nominal
  1.3375 kHz spacing, and 1 kHz measurement bandwidth.
- OPEN-to-SHORT raw median separation: 1.538.
- Reconnected-load verification: median SWR 1.00075, p95 1.00087, maximum
  1.00106, and median impedance 50.0357 + j0.0112 ohms.
- The first antenna capture timed out after segment 150 because the NanoVNA
  firmware stopped answering. No partial result was accepted. The VNA was
  physically power-cycled without disturbing the RF path, and the full capture
  was restarted from segment 1.

### Far-end-open feed-path comparison

![Open-path comparison](charts/open_path_choke_comparison.png)

Under the simplifying ideal-open/uniform-line assumption, apparent one-way
attenuation changed by **{float(sample_7['observed_delta_db']):+.2f} dB at
7 MHz**, **{float(sample_28['observed_delta_db']):+.2f} dB at 28 MHz**, and
**{float(sample_54['observed_delta_db']):+.2f} dB at 54 MHz**. The unchoked
trace was captured August 23 and the choked trace August 28 under separate OSL
calibrations. The observed delta includes day-to-day/calibration repeatability,
the added 6 ft of RG8X/connectors, and discontinuities from the chokes and
window transition. It cannot be attributed to any one component. A one-port
far-end-open measurement does **not** measure insertion loss or common-mode
choking impedance.

## Data and reproduction

- `data/band_summary.csv` and `.json`: the same per-band metrics as the original
  JYR8010 report.
- `data/supported_band_points.csv`: calibrated points inside all eight
  advertised bands.
- `data/antenna_full_sweep.s1p`: complex average of the two current sweeps.
- `data/historical_comparison.csv` and `.json`: old-versus-current deltas.
- `measurements/`: full calibration, verification, open-path diagnostic, and
  both current source sweeps, plus the complete August 23 unchoked open-path
  baseline and its separate calibration.
- `interactive-report.html`: self-contained supported-band explorer.

From the repository root, recreate the complete report with:

```bash
python3 antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/generate_report.py \\
  --historical-source antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/data/historical_2026-08-16.s1p \\
  --current-source antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/data/current_sweep_1.s1p \\
  --repeat-source antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/data/current_sweep_2.s1p \\
  --calibration-dir antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/calibration \\
  --open-path-dir antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/choked-far-end-open \\
  --unchoked-open-dir antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/unchoked-baseline/far-end-open \\
  --unchoked-calibration-dir antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/unchoked-baseline/calibration \\
  --current-dir antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/current-sweep-1 \\
  --repeat-dir antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/current-sweep-2
```

## Historical comparison and observed changes

The August 16 historical run and August 28 current run differ in more than the
toroids. The old metadata records **no dedicated counterpoise** and does not
record feed-line length, antenna support geometry, or an office/window path.
The current run adds **two chokes, six feet of RG8X, their connectors, a 16 ft
counterpoise, the documented 75 ft + ribbon + 25 ft office path, and a different
date/calibration/reference environment**. Therefore, the table below precisely
describes the observed system-level differences but cannot assign them to the
toroids alone.

{comparison_table(historical, summaries)}

![Historical comparison](charts/historical_comparison_swr_zooms.png)

![Observed change scorecard](charts/historical_change_scorecard.png)

Observed pattern:

- **40m remained essentially unchanged** in minimum SWR while retaining broad
  <=2:1 coverage.
- **20m, 17m, 15m, 12m, and 10m improved** in minimum SWR; 17m became fully
  <=2:1 and 10m gained substantially more <=2:1 coverage.
- **80m became slightly worse** but retained a strong low-SWR subrange.
- **30m became substantially worse**, losing its former full-band <=2:1 match.
- These changes are stable across the two current sweeps, but they are the
  combined result of the complete current installation - not a controlled
  measurement of choke effectiveness.

SWR measures input impedance match, not gain, radiation efficiency, pattern,
receive sensitivity, noise-floor reduction, or common-mode suppression.
"""
    (output / "README.md").write_text(content, encoding="ascii")


def normalize_csv(root: Path) -> None:
    for path in root.rglob("*.csv"):
        path.write_text(path.read_text(encoding="ascii"), encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-source", required=True, type=Path)
    parser.add_argument("--current-source", required=True, type=Path)
    parser.add_argument("--repeat-source", required=True, type=Path)
    parser.add_argument("--calibration-dir", required=True, type=Path)
    parser.add_argument("--open-path-dir", required=True, type=Path)
    parser.add_argument("--unchoked-open-dir", required=True, type=Path)
    parser.add_argument("--unchoked-calibration-dir", required=True, type=Path)
    parser.add_argument("--current-dir", required=True, type=Path)
    parser.add_argument("--repeat-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()

    base = load_base()
    final_output = args.output.resolve()
    backup_output = final_output.with_name(f".{final_output.name}.backup")
    if backup_output.exists():
        if final_output.exists():
            shutil.rmtree(backup_output)
        else:
            os.replace(backup_output, final_output)
    final_output.mkdir(parents=True, exist_ok=True)
    staging_handle = tempfile.TemporaryDirectory(
        prefix=".jyr8010-two-choke-", dir=final_output.parent
    )
    staging = Path(staging_handle.name)
    inputs = staging / "inputs"
    inputs.mkdir()
    file_inputs = (
        "historical_source",
        "current_source",
        "repeat_source",
    )
    for name in file_inputs:
        source = getattr(args, name)
        destination = inputs / f"{name}{source.suffix}"
        shutil.copy2(source, destination)
        setattr(args, name, destination)
    directory_inputs = (
        "calibration_dir",
        "open_path_dir",
        "unchoked_open_dir",
        "unchoked_calibration_dir",
        "current_dir",
        "repeat_dir",
    )
    for name in directory_inputs:
        source = getattr(args, name)
        destination = inputs / name
        shutil.copytree(source, destination)
        setattr(args, name, destination)

    output = staging / "generated"
    shutil.copytree(
        final_output,
        output,
        ignore=shutil.ignore_patterns(
            "charts",
            "data",
            "measurements",
            "README.md",
            "interactive-report.html",
            "__pycache__",
        ),
    )
    charts = output / "charts"
    data = output / "data"
    measurements = output / "measurements"
    charts.mkdir()
    data.mkdir()
    measurements.mkdir()

    historical_f, historical_gamma = base.load_touchstone(args.historical_source)
    current_f, current_gamma = base.load_touchstone(args.current_source)
    repeat_f, repeat_gamma = base.load_touchstone(args.repeat_source)
    choked_open_f, choked_open_gamma = base.load_touchstone(
        args.open_path_dir / "antenna.s1p"
    )
    unchoked_open_f, unchoked_open_gamma = base.load_touchstone(
        args.unchoked_open_dir / "antenna.s1p"
    )
    if not np.array_equal(current_f, repeat_f):
        raise ValueError("current sweep frequencies do not match repeat")
    if not np.array_equal(current_f, choked_open_f):
        raise ValueError("current sweep frequencies do not match open-path sweep")
    average_gamma = (current_gamma + repeat_gamma) / 2.0
    current_metrics = base.calculate_metrics(average_gamma)
    historical_metrics = base.calculate_metrics(historical_gamma)
    summaries, interactive = base.analyze_bands(
        current_f, average_gamma, current_metrics
    )
    historical_summary, _ = base.analyze_bands(
        historical_f, historical_gamma, historical_metrics
    )

    base.set_plot_style()
    base.plot_swr_zooms(
        charts,
        current_f,
        current_metrics,
        summaries,
        subtitle=(
            "Calibrated at the office-side adapter; complete feed path included"
        ),
    )
    base.plot_impedance(
        charts,
        current_f,
        current_metrics,
        title="Input impedance at the office-side adapter by supported band",
    )
    base.plot_return_loss(charts, current_f, current_metrics)
    base.plot_performance(charts, summaries)
    base.plot_threshold_ranges(charts, summaries)
    base.plot_smith(charts, current_f, average_gamma)
    base.plot_log_overview(charts, current_f, current_metrics)
    plot_comparison_zooms(
        base,
        charts,
        historical_f,
        historical_metrics,
        current_f,
        current_metrics,
        historical_summary,
        summaries,
    )
    plot_change_scorecard(charts, historical_summary, summaries)
    repeatability = plot_repeatability(
        base, charts, current_f, current_gamma, repeat_gamma
    )
    open_comparison = plot_open_path_comparison(
        charts,
        unchoked_open_f,
        unchoked_open_gamma,
        choked_open_f,
        choked_open_gamma,
    )
    plot_installation(charts)

    base.write_supported_points(data, current_f, average_gamma, current_metrics)
    base.write_summary_csv(data, summaries)
    (data / "band_summary.json").write_text(
        json.dumps(summaries, indent=2) + "\n", encoding="ascii"
    )
    comparison = {
        "comparison_is_controlled_choke_ab": False,
        "historical": historical_summary,
        "current_two_chokes_and_counterpoise": summaries,
    }
    (data / "historical_comparison.json").write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="ascii"
    )
    with (data / "historical_comparison.csv").open(
        "w", newline="", encoding="ascii"
    ) as destination:
        writer = csv.writer(destination)
        writer.writerow(
            (
                "band",
                "historical_minimum_swr",
                "historical_minimum_frequency_mhz",
                "historical_coverage_le_2_percent",
                "current_minimum_swr",
                "current_minimum_frequency_mhz",
                "current_coverage_le_2_percent",
                "minimum_swr_change",
                "minimum_frequency_shift_khz",
            )
        )
        for old, new in zip(historical_summary, summaries):
            writer.writerow(
                (
                    new["band"],
                    old["minimum_swr"],
                    old["minimum_swr_frequency_mhz"],
                    old["coverage_percent"]["2.0"],  # type: ignore[index]
                    new["minimum_swr"],
                    new["minimum_swr_frequency_mhz"],
                    new["coverage_percent"]["2.0"],  # type: ignore[index]
                    float(new["minimum_swr"]) - float(old["minimum_swr"]),
                    (
                        int(new["minimum_swr_frequency_hz"])
                        - int(old["minimum_swr_frequency_hz"])
                    )
                    / 1e3,
                )
            )
    (data / "repeatability.json").write_text(
        json.dumps(repeatability, indent=2) + "\n", encoding="ascii"
    )
    (data / "open_path_comparison.json").write_text(
        json.dumps(open_comparison, indent=2) + "\n", encoding="ascii"
    )
    with (data / "antenna_full_sweep.s1p").open("w", encoding="ascii") as destination:
        destination.write("! Two-sweep complex average, JYR8010 choked installation\n")
        destination.write("# Hz S RI R 50\n")
        for frequency, sample in zip(current_f, average_gamma):
            destination.write(
                f"{int(frequency)} {sample.real:.12g} {sample.imag:.12g}\n"
            )
    shutil.copy2(args.historical_source, data / "historical_2026-08-16.s1p")
    shutil.copy2(args.current_source, data / "current_sweep_1.s1p")
    shutil.copy2(args.repeat_source, data / "current_sweep_2.s1p")
    shutil.copy2(
        args.unchoked_open_dir / "antenna.s1p",
        data / "unchoked_open_path.s1p",
    )

    metadata = {
        "report_generated_at": "2026-08-28T22:29:40.311458-07:00",
        "antenna": {
            "model": "JYR8010-150W",
            "type": "end-fed half-wave",
            "radiating_element_length_m": 40,
            "nominal_transformer_ratio": "1:49 / 1:64",
            "advertised_supported_bands": [item[0] for item in base.BANDS],
            "asin": "B0DBDCNVZD",
        },
        "installation": {
            "feed_path": [
                "25 ft LS400 inside office",
                "3 ft RG8X window-entry choke",
                "window flat-ribbon transition",
                "75 ft LS400 outdoors",
                "3 ft RG8X feedpoint choke",
            ],
            "total_coax_length_ft_excluding_window_transition": 106,
            "chokes": [
                {
                    "location": "window entry before 25 ft indoor LS400",
                    "coax": "RG8X",
                    "coax_length_ft": 3,
                    "turns": 11,
                    "core": "Mix 31 FT240-size toroid",
                },
                {
                    "location": "antenna feedpoint before transformer",
                    "coax": "RG8X",
                    "coax_length_ft": 3,
                    "turns": 11,
                    "core": "Mix 31 FT240-size toroid",
                },
            ],
            "counterpoise": {
                "length_ft": 16,
                "connection": "dedicated JYR8010 transformer terminal",
                "layout": "on ground, opposite antenna direction",
            },
            "office_environment": "substantial computer equipment",
            "physical_antenna_geometry": (
                "User reported everything else unchanged; exact support "
                "dimensions were not recorded in the historical JYR8010 report."
            ),
        },
        "instrument": {
            "model": "NanoVNA-H",
            "firmware": "1.2.50",
            "measurement_bandwidth_hz": 1000,
            "reference_impedance_ohm": 50,
        },
        "calibration": {
            "type": "software one-port ideal OSL",
            "reference_plane": "office-side PL-259/SO-239 adapter on CH0",
            "created_at": "2026-08-28T22:06:04.362381-07:00",
            "open_short_median_raw_separation": 1.5382252686454203,
            "load_verification": {
                "median_swr": 1.0007535021898002,
                "p95_swr": 1.0008701941153695,
                "maximum_swr": 1.0010623169934088,
                "median_resistance_ohm": 50.035745085839366,
                "median_reactance_ohm": 0.011240891766802232,
            },
        },
        "sweep": {
            "capture_1_at": "2026-08-28T22:26:16.148844-07:00",
            "capture_2_at": "2026-08-28T22:29:40.311458-07:00",
            "range_hz": [500_000, 54_000_000],
            "points": 40_001,
            "nominal_step_hz": 1_337.5,
        },
        "capture_recovery": {
            "issue": (
                "First attempt timed out after segment 150 while restoring "
                "calibration state; no partial result was saved."
            ),
            "action": (
                "Physically power-cycled NanoVNA without disturbing RF setup "
                "and restarted the complete sweep."
            ),
        },
        "comparison_limit": (
            "Historical and current configurations differ in chokes, added "
            "RG8X/connectors, counterpoise, documented office feed path, date, "
            "calibration, and potentially undocumented geometry. Differences "
            "cannot be attributed to toroids alone."
        ),
        "open_path_comparison_limit": (
            "The unchoked far-end-open baseline was captured August 23 under "
            "a separate OSL calibration; the choked path was captured August "
            "28. The observed differences are cross-day and cross-calibration."
        ),
    }
    (data / "measurement_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="ascii"
    )

    shutil.copytree(args.calibration_dir, measurements / "calibration")
    shutil.copytree(args.open_path_dir, measurements / "choked-far-end-open")
    shutil.copytree(
        args.unchoked_open_dir,
        measurements / "unchoked-baseline" / "far-end-open",
    )
    shutil.copytree(
        args.unchoked_calibration_dir,
        measurements / "unchoked-baseline" / "calibration",
    )
    shutil.copytree(args.current_dir, measurements / "current-sweep-1")
    shutil.copytree(args.repeat_dir, measurements / "current-sweep-2")
    base.write_html(
        output,
        summaries,
        interactive,
        metadata,
        page_title="JYR8010 EFHW two-choke office-feed results",
        heading="JYR8010 EFHW: two chokes + counterpoise",
        subtitle=(
            "Interactive supported-band analysis for the 106 ft office feed "
            "path with two 11-turn Mix 31 chokes and a 16 ft counterpoise."
        ),
        installation_note=(
            "Two 3 ft RG8X, 11-turn Mix 31 chokes are installed at the window "
            "entry and feedpoint. A 16 ft counterpoise is connected directly "
            "to the transformer terminal. Results are input impedance at the "
            "office-side adapter, not de-embedded antenna feed-point impedance."
        ),
        footer=(
            "Captured 2026-08-28 22:23-22:29 PDT | NanoVNA-H firmware 1.2.50 | "
            "0.5-54 MHz | 40,001 points | 50-ohm reference"
        ),
        resolution_value="1.3375 kHz",
        resolution_caption="nominal point spacing",
        context_note_label="Interpretation note",
        context_note=(
            "Better radio-end SWR can result from transmission-line phase and "
            "loss. This report does not establish antenna gain, efficiency, "
            "noise reduction, or common-mode choke impedance."
        ),
    )
    write_readme(
        base,
        output,
        summaries,
        historical_summary,
        repeatability,
        open_comparison,
    )
    normalize_csv(output)

    os.replace(final_output, backup_output)
    try:
        os.replace(output, final_output)
    except BaseException:
        os.replace(backup_output, final_output)
        raise
    else:
        shutil.rmtree(backup_output)
    staging_handle.cleanup()
    print(f"generated {final_output}")


if __name__ == "__main__":
    main()
