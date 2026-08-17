#!/usr/bin/env python3
"""Generate the JYR8010 supported-band NanoVNA report and charts."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from datetime import datetime
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


BANDS = (
    ("80m", 3_500_000, 4_000_000),
    ("40m", 7_000_000, 7_300_000),
    ("30m", 10_100_000, 10_150_000),
    ("20m", 14_000_000, 14_350_000),
    ("17m", 18_068_000, 18_168_000),
    ("15m", 21_000_000, 21_450_000),
    ("12m", 24_890_000, 24_990_000),
    ("10m", 28_000_000, 29_700_000),
)
THRESHOLDS = (1.5, 2.0, 3.0)
REFERENCE_OHMS = 50.0
PLOT_COLORS = (
    "#8e244d",
    "#315c8c",
    "#23856d",
    "#b26a22",
    "#6d4c91",
    "#22758c",
    "#9a5433",
    "#4f6d3a",
)


def load_touchstone(path: Path) -> tuple[np.ndarray, np.ndarray]:
    frequencies: list[int] = []
    samples: list[complex] = []
    with path.open(encoding="ascii") as source:
        for line in source:
            stripped = line.strip()
            if not stripped or stripped.startswith(("!", "#")):
                continue
            frequency, real, imaginary = stripped.split()[:3]
            frequencies.append(int(frequency))
            samples.append(complex(float(real), float(imaginary)))
    if not frequencies:
        raise ValueError(f"no samples found in {path}")
    return np.asarray(frequencies), np.asarray(samples)


def calculate_metrics(gamma: np.ndarray) -> dict[str, np.ndarray]:
    magnitude = np.abs(gamma)
    with np.errstate(divide="ignore", invalid="ignore"):
        swr = np.where(magnitude < 1.0, (1.0 + magnitude) / (1.0 - magnitude), np.inf)
        return_loss = -20.0 * np.log10(magnitude)
        impedance = REFERENCE_OHMS * (1.0 + gamma) / (1.0 - gamma)
    return {
        "swr": swr,
        "return_loss_db": return_loss,
        "resistance_ohm": impedance.real,
        "reactance_ohm": impedance.imag,
        "phase_deg": np.angle(gamma, deg=True),
    }


def contiguous_intervals(
    frequencies: np.ndarray, values: np.ndarray, threshold: float
) -> list[tuple[int, int]]:
    passing = np.isfinite(values) & (values <= threshold)
    transitions = np.diff(np.concatenate(([False], passing, [False])).astype(int))
    starts = np.flatnonzero(transitions == 1)
    stops = np.flatnonzero(transitions == -1) - 1
    return [
        (int(frequencies[start]), int(frequencies[stop]))
        for start, stop in zip(starts, stops)
    ]


def format_interval(interval: tuple[int, int] | None) -> str:
    if interval is None:
        return "none"
    start, stop = interval
    if start == stop:
        return f"{start / 1e6:.4f} MHz"
    return f"{start / 1e6:.4f}-{stop / 1e6:.4f} MHz"


def rating(maximum_swr: float, coverage_2: float, minimum_swr: float) -> str:
    if maximum_swr <= 1.5:
        return "excellent full-band"
    if maximum_swr <= 2.0:
        return "very good full-band"
    if maximum_swr <= 3.0:
        return "usable full-band"
    if coverage_2 >= 75.0:
        return "very good over most"
    if coverage_2 > 0.0:
        return "best in a subrange"
    if minimum_swr <= 3.0:
        return "tuner recommended"
    return "poor match"


def analyze_bands(
    frequencies: np.ndarray,
    gamma: np.ndarray,
    metrics: dict[str, np.ndarray],
) -> tuple[list[dict[str, object]], dict[str, dict[str, list[float]]]]:
    summaries: list[dict[str, object]] = []
    interactive: dict[str, dict[str, list[float]]] = {}
    for name, lower, upper in BANDS:
        selected = (frequencies >= lower) & (frequencies <= upper)
        indexes = np.flatnonzero(selected)
        if indexes.size == 0:
            raise ValueError(f"no points found for {name}")
        band_frequencies = frequencies[indexes]
        band_gamma = gamma[indexes]
        band_metrics = {key: values[indexes] for key, values in metrics.items()}
        finite = np.isfinite(band_metrics["swr"])
        best_local = np.flatnonzero(finite)[np.argmin(band_metrics["swr"][finite])]
        best_global = indexes[best_local]
        intervals: dict[str, list[dict[str, object]]] = {}
        longest: dict[str, str] = {}
        coverage: dict[str, float] = {}
        for threshold in THRESHOLDS:
            found = contiguous_intervals(
                band_frequencies, band_metrics["swr"], threshold
            )
            intervals[f"{threshold:.1f}"] = [
                {
                    "start_hz": start,
                    "stop_hz": stop,
                    "width_khz": (stop - start) / 1e3,
                }
                for start, stop in found
            ]
            best_interval = max(found, key=lambda item: item[1] - item[0], default=None)
            longest[f"{threshold:.1f}"] = format_interval(best_interval)
            coverage[f"{threshold:.1f}"] = float(
                100.0 * np.mean(band_metrics["swr"] <= threshold)
            )

        minimum_swr = float(metrics["swr"][best_global])
        maximum_swr = float(np.nanmax(band_metrics["swr"]))
        summary: dict[str, object] = {
            "band": name,
            "wavelength_m": int(name.removesuffix("m")),
            "lower_hz": lower,
            "upper_hz": upper,
            "lower_mhz": lower / 1e6,
            "upper_mhz": upper / 1e6,
            "bandwidth_khz": (upper - lower) / 1e3,
            "points": int(indexes.size),
            "minimum_swr": minimum_swr,
            "minimum_swr_frequency_hz": int(frequencies[best_global]),
            "minimum_swr_frequency_mhz": frequencies[best_global] / 1e6,
            "maximum_swr": maximum_swr,
            "median_swr": float(np.nanmedian(band_metrics["swr"])),
            "return_loss_at_minimum_db": float(
                metrics["return_loss_db"][best_global]
            ),
            "resistance_at_minimum_ohm": float(
                metrics["resistance_ohm"][best_global]
            ),
            "reactance_at_minimum_ohm": float(
                metrics["reactance_ohm"][best_global]
            ),
            "coverage_percent": coverage,
            "longest_contiguous_range": longest,
            "threshold_intervals": intervals,
            "rating": rating(maximum_swr, coverage["2.0"], minimum_swr),
        }
        summaries.append(summary)
        interactive[name] = {
            "frequency_mhz": (band_frequencies / 1e6).round(6).tolist(),
            "swr": band_metrics["swr"].round(5).tolist(),
            "return_loss_db": band_metrics["return_loss_db"].round(4).tolist(),
            "resistance_ohm": band_metrics["resistance_ohm"].round(4).tolist(),
            "reactance_ohm": band_metrics["reactance_ohm"].round(4).tolist(),
            "gamma_real": band_gamma.real.round(7).tolist(),
            "gamma_imag": band_gamma.imag.round(7).tolist(),
        }
    return summaries, interactive


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#f7f4ef",
            "axes.facecolor": "#ffffff",
            "axes.edgecolor": "#8a8580",
            "axes.labelcolor": "#242424",
            "axes.titlecolor": "#242424",
            "xtick.color": "#4d4a47",
            "ytick.color": "#4d4a47",
            "grid.color": "#d8d3cd",
            "font.family": "DejaVu Sans",
            "font.size": 10,
        }
    )


def plot_swr_zooms(
    output: Path,
    frequencies: np.ndarray,
    metrics: dict[str, np.ndarray],
    summaries: list[dict[str, object]],
) -> None:
    fig, axes = plt.subplots(4, 2, figsize=(15, 18), constrained_layout=True)
    for axis, band, summary, color in zip(
        axes.flat, BANDS, summaries, PLOT_COLORS
    ):
        name, lower, upper = band
        selected = (frequencies >= lower) & (frequencies <= upper)
        band_frequencies = frequencies[selected] / 1e6
        band_swr = metrics["swr"][selected]
        axis.plot(band_frequencies, band_swr, color=color, linewidth=1.8)
        for threshold, linestyle in ((1.5, ":"), (2.0, "--"), (3.0, "-.")):
            axis.axhline(
                threshold,
                color="#77716d",
                linestyle=linestyle,
                linewidth=0.8,
                alpha=0.65,
            )
        best_frequency = float(summary["minimum_swr_frequency_mhz"])
        best_swr = float(summary["minimum_swr"])
        axis.scatter(best_frequency, best_swr, color="#b11f4b", zorder=4)
        axis.annotate(
            f"{best_frequency:.6f} MHz\nSWR {best_swr:.2f}",
            xy=(best_frequency, best_swr),
            xytext=(8, 16),
            textcoords="offset points",
            arrowprops={"arrowstyle": "->", "color": "#b11f4b"},
            fontsize=9,
        )
        axis.set_title(
            f"{name} | {lower / 1e6:g}-{upper / 1e6:g} MHz | "
            f"{summary['rating']}"
        )
        axis.set_xlabel("Frequency (MHz)")
        axis.set_ylabel("SWR")
        axis.set_xlim(lower / 1e6, upper / 1e6)
        axis.set_ylim(
            1.0,
            max(2.1, min(5.0, float(np.nanmax(band_swr)) * 1.12)),
        )
        axis.grid(True, alpha=0.7)
    fig.suptitle(
        "JYR8010 supported-band SWR zooms\n"
        "Calibrated at the antenna-side adapter reference plane",
        fontsize=17,
    )
    fig.savefig(output / "supported_band_swr_zooms.png", dpi=200)
    plt.close(fig)


def plot_impedance(
    output: Path,
    frequencies: np.ndarray,
    metrics: dict[str, np.ndarray],
) -> None:
    fig, axes = plt.subplots(4, 2, figsize=(15, 18), constrained_layout=True)
    for axis, (name, lower, upper), color in zip(
        axes.flat, BANDS, PLOT_COLORS
    ):
        selected = (frequencies >= lower) & (frequencies <= upper)
        x = frequencies[selected] / 1e6
        axis.plot(
            x,
            metrics["resistance_ohm"][selected],
            color=color,
            linewidth=1.6,
            label="Resistance R",
        )
        axis.plot(
            x,
            metrics["reactance_ohm"][selected],
            color="#b11f4b",
            linewidth=1.4,
            label="Reactance X",
        )
        axis.axhline(50, color="#77716d", linestyle="--", linewidth=0.8)
        axis.axhline(0, color="#77716d", linewidth=0.8)
        axis.set_title(name)
        axis.set_xlabel("Frequency (MHz)")
        axis.set_ylabel("Impedance (ohms)")
        axis.set_xlim(lower / 1e6, upper / 1e6)
        axis.grid(True, alpha=0.7)
        axis.legend(loc="best", fontsize=8)
    fig.suptitle("Feed-point impedance by supported band", fontsize=17)
    fig.savefig(output / "supported_band_impedance.png", dpi=200)
    plt.close(fig)


def plot_return_loss(
    output: Path,
    frequencies: np.ndarray,
    metrics: dict[str, np.ndarray],
) -> None:
    fig, axes = plt.subplots(4, 2, figsize=(15, 18), constrained_layout=True)
    for axis, (name, lower, upper), color in zip(
        axes.flat, BANDS, PLOT_COLORS
    ):
        selected = (frequencies >= lower) & (frequencies <= upper)
        axis.plot(
            frequencies[selected] / 1e6,
            metrics["return_loss_db"][selected],
            color=color,
            linewidth=1.7,
        )
        axis.axhline(
            9.54,
            color="#77716d",
            linestyle="--",
            linewidth=0.8,
            label="SWR 2:1",
        )
        axis.set_title(name)
        axis.set_xlabel("Frequency (MHz)")
        axis.set_ylabel("Return loss (dB)")
        axis.set_xlim(lower / 1e6, upper / 1e6)
        axis.grid(True, alpha=0.7)
        axis.legend(loc="best", fontsize=8)
    fig.suptitle("Return loss by supported band", fontsize=17)
    fig.savefig(output / "supported_band_return_loss.png", dpi=200)
    plt.close(fig)


def plot_performance(
    output: Path, summaries: list[dict[str, object]]
) -> None:
    names = [str(item["band"]) for item in summaries]
    minima = [float(item["minimum_swr"]) for item in summaries]
    maxima = [float(item["maximum_swr"]) for item in summaries]
    coverage = [
        float(item["coverage_percent"]["2.0"])  # type: ignore[index]
        for item in summaries
    ]
    y = np.arange(len(names))
    fig, (left, right) = plt.subplots(1, 2, figsize=(15, 7), constrained_layout=True)
    left.hlines(y, minima, maxima, color="#b9b2ac", linewidth=5)
    left.scatter(minima, y, color="#23856d", s=75, label="Minimum")
    left.scatter(maxima, y, color="#b11f4b", s=75, label="Maximum")
    left.axvline(2.0, color="#77716d", linestyle="--", linewidth=1)
    left.set_yticks(y, names)
    left.invert_yaxis()
    left.set_xlabel("SWR")
    left.set_title("Best-to-worst SWR across each band")
    left.grid(True, axis="x", alpha=0.7)
    left.legend()
    bars = right.barh(y, coverage, color=PLOT_COLORS)
    right.set_yticks(y, names)
    right.invert_yaxis()
    right.set_xlim(0, 100)
    right.set_xlabel("Percent of US band at SWR <= 2.0")
    right.set_title("No-tuner 2:1 coverage")
    right.grid(True, axis="x", alpha=0.7)
    right.bar_label(bars, fmt="%.0f%%", padding=3)
    fig.suptitle("Supported-band performance scorecard", fontsize=17)
    fig.savefig(output / "band_performance_scorecard.png", dpi=200)
    plt.close(fig)


def plot_threshold_ranges(
    output: Path, summaries: list[dict[str, object]]
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), constrained_layout=True)
    for axis, threshold in zip(axes, THRESHOLDS):
        for row, summary in enumerate(summaries):
            lower = float(summary["lower_mhz"])
            upper = float(summary["upper_mhz"])
            span = upper - lower
            axis.hlines(row, 0, 100, color="#cfc9c3", linewidth=8)
            intervals = summary["threshold_intervals"][f"{threshold:.1f}"]  # type: ignore[index]
            for interval in intervals:
                start = (float(interval["start_hz"]) / 1e6 - lower) / span * 100
                stop = (float(interval["stop_hz"]) / 1e6 - lower) / span * 100
                axis.hlines(
                    row,
                    start,
                    stop,
                    color=PLOT_COLORS[row],
                    linewidth=8,
                )
            axis.text(
                102,
                row,
                summary["longest_contiguous_range"][f"{threshold:.1f}"],  # type: ignore[index]
                va="center",
                fontsize=8,
            )
        axis.set_yticks(range(len(summaries)), [item["band"] for item in summaries])
        axis.invert_yaxis()
        axis.set_xlim(0, 145)
        axis.set_xlabel("Position within the US amateur band (%)")
        axis.set_title(f"Contiguous ranges at SWR <= {threshold:.1f}")
        axis.grid(True, axis="x", alpha=0.6)
    fig.suptitle(
        "Usable bandwidth by SWR threshold\n"
        "Text at right gives the longest contiguous range",
        fontsize=17,
    )
    fig.savefig(output / "usable_bandwidth_by_threshold.png", dpi=200)
    plt.close(fig)


def draw_smith_grid(axis: plt.Axes) -> None:
    theta = np.linspace(0, 2 * np.pi, 800)
    axis.plot(np.cos(theta), np.sin(theta), color="#4d4a47", linewidth=1.2)
    for resistance in (0.2, 0.5, 1, 2, 5):
        center = resistance / (resistance + 1)
        radius = 1 / (resistance + 1)
        axis.plot(
            center + radius * np.cos(theta),
            radius * np.sin(theta),
            color="#d0cac4",
            linewidth=0.55,
        )
    resistance_values = np.linspace(0, 15, 1000)
    for reactance in (0.2, 0.5, 1, 2, 5):
        for sign in (-1, 1):
            z = resistance_values + 1j * sign * reactance
            gamma = (z - 1) / (z + 1)
            axis.plot(
                gamma.real,
                gamma.imag,
                color="#d0cac4",
                linewidth=0.55,
            )
    axis.axhline(0, color="#a8a19b", linewidth=0.6)
    axis.scatter(0, 0, color="#242424", s=15, zorder=5)
    axis.text(0.03, 0.03, "50 ohms", fontsize=8)
    axis.set_aspect("equal")
    axis.set_xlim(-1.05, 1.05)
    axis.set_ylim(-1.05, 1.05)
    axis.set_xlabel("Reflection coefficient, real")
    axis.set_ylabel("Reflection coefficient, imaginary")
    axis.grid(False)


def plot_smith(
    output: Path,
    frequencies: np.ndarray,
    gamma: np.ndarray,
) -> None:
    fig, axis = plt.subplots(figsize=(10, 10), constrained_layout=True)
    draw_smith_grid(axis)
    for (name, lower, upper), color in zip(BANDS, PLOT_COLORS):
        selected = (frequencies >= lower) & (frequencies <= upper)
        axis.plot(
            gamma[selected].real,
            gamma[selected].imag,
            color=color,
            linewidth=2,
            label=name,
        )
        first = np.flatnonzero(selected)[0]
        axis.scatter(gamma[first].real, gamma[first].imag, color=color, s=18)
    axis.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.11))
    axis.set_title("Supported-band Smith chart\nDots mark each band's lower edge")
    fig.savefig(output / "supported_bands_smith_chart.png", dpi=220)
    plt.close(fig)


def plot_log_overview(
    output: Path,
    frequencies: np.ndarray,
    metrics: dict[str, np.ndarray],
) -> None:
    fig, axis = plt.subplots(figsize=(15, 7), constrained_layout=True)
    for (name, lower, upper), color in zip(BANDS, PLOT_COLORS):
        selected = (frequencies >= lower) & (frequencies <= upper)
        axis.semilogx(
            frequencies[selected] / 1e6,
            np.minimum(metrics["swr"][selected], 5),
            color=color,
            linewidth=2,
            label=name,
        )
    axis.axhline(2, color="#77716d", linestyle="--", linewidth=1)
    axis.set_xlabel("Frequency (MHz, logarithmic scale)")
    axis.set_ylabel("SWR (clipped at 5)")
    axis.set_ylim(1, 5)
    axis.set_title("Supported bands from 80m through 10m")
    axis.grid(True, which="both", alpha=0.7)
    axis.legend(ncol=8, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.savefig(output / "supported_bands_log_overview.png", dpi=200)
    plt.close(fig)


def write_supported_points(
    output: Path,
    frequencies: np.ndarray,
    gamma: np.ndarray,
    metrics: dict[str, np.ndarray],
) -> None:
    with (output / "supported_band_points.csv").open(
        "w", newline="", encoding="ascii"
    ) as destination:
        writer = csv.writer(destination)
        writer.writerow(
            (
                "band",
                "frequency_hz",
                "frequency_mhz",
                "swr",
                "return_loss_db",
                "resistance_ohm",
                "reactance_ohm",
                "s11_real",
                "s11_imag",
                "phase_deg",
            )
        )
        for name, lower, upper in BANDS:
            selected = np.flatnonzero(
                (frequencies >= lower) & (frequencies <= upper)
            )
            for index in selected:
                writer.writerow(
                    (
                        name,
                        int(frequencies[index]),
                        f"{frequencies[index] / 1e6:.6f}",
                        f"{metrics['swr'][index]:.8f}",
                        f"{metrics['return_loss_db'][index]:.8f}",
                        f"{metrics['resistance_ohm'][index]:.8f}",
                        f"{metrics['reactance_ohm'][index]:.8f}",
                        f"{gamma[index].real:.10f}",
                        f"{gamma[index].imag:.10f}",
                        f"{metrics['phase_deg'][index]:.8f}",
                    )
                )


def write_summary_csv(output: Path, summaries: list[dict[str, object]]) -> None:
    with (output / "band_summary.csv").open(
        "w", newline="", encoding="ascii"
    ) as destination:
        fields = (
            "band",
            "lower_mhz",
            "upper_mhz",
            "minimum_swr",
            "minimum_swr_frequency_mhz",
            "maximum_swr",
            "median_swr",
            "return_loss_at_minimum_db",
            "resistance_at_minimum_ohm",
            "reactance_at_minimum_ohm",
            "coverage_at_or_below_1_5_percent",
            "coverage_at_or_below_2_0_percent",
            "coverage_at_or_below_3_0_percent",
            "longest_range_at_or_below_2_0",
            "rating",
        )
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        for item in summaries:
            writer.writerow(
                {
                    "band": item["band"],
                    "lower_mhz": item["lower_mhz"],
                    "upper_mhz": item["upper_mhz"],
                    "minimum_swr": item["minimum_swr"],
                    "minimum_swr_frequency_mhz": item[
                        "minimum_swr_frequency_mhz"
                    ],
                    "maximum_swr": item["maximum_swr"],
                    "median_swr": item["median_swr"],
                    "return_loss_at_minimum_db": item[
                        "return_loss_at_minimum_db"
                    ],
                    "resistance_at_minimum_ohm": item[
                        "resistance_at_minimum_ohm"
                    ],
                    "reactance_at_minimum_ohm": item[
                        "reactance_at_minimum_ohm"
                    ],
                    "coverage_at_or_below_1_5_percent": item[
                        "coverage_percent"
                    ]["1.5"],  # type: ignore[index]
                    "coverage_at_or_below_2_0_percent": item[
                        "coverage_percent"
                    ]["2.0"],  # type: ignore[index]
                    "coverage_at_or_below_3_0_percent": item[
                        "coverage_percent"
                    ]["3.0"],  # type: ignore[index]
                    "longest_range_at_or_below_2_0": item[
                        "longest_contiguous_range"
                    ]["2.0"],  # type: ignore[index]
                    "rating": item["rating"],
                }
            )


def markdown_table(summaries: list[dict[str, object]]) -> str:
    rows = [
        "| Band | US range | Best SWR | Best frequency | Z at best | "
        "Band <=2:1 | Longest <=2:1 range | Assessment |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in summaries:
        coverage = item["coverage_percent"]["2.0"]  # type: ignore[index]
        rows.append(
            f"| {item['band']} | {item['lower_mhz']:g}-{item['upper_mhz']:g} MHz "
            f"| {item['minimum_swr']:.2f} | "
            f"{item['minimum_swr_frequency_mhz']:.6f} MHz | "
            f"{item['resistance_at_minimum_ohm']:.1f} "
            f"{item['reactance_at_minimum_ohm']:+.1f}j ohms | "
            f"{coverage:.0f}% | "
            f"{item['longest_contiguous_range']['2.0']} | "  # type: ignore[index]
            f"{item['rating']} |"
        )
    return "\n".join(rows)


def write_readme(output: Path, summaries: list[dict[str, object]]) -> None:
    best = min(summaries, key=lambda item: float(item["minimum_swr"]))
    full_two_to_one = [
        str(item["band"])
        for item in summaries
        if float(item["maximum_swr"]) <= 2.0
    ]
    content = f"""# JYR8010 EFHW antenna results

This folder contains a calibrated NanoVNA-H characterization of the antenna's
advertised US amateur bands: **80m, 40m, 30m, 20m, 17m, 15m, 12m, and 10m**.
The antenna is a 40-meter end-fed half-wave design sold as the
JYR8010-150W with a nominal 1:49/1:64 impedance transformer
([Amazon ASIN B0DBDCNVZD](https://www.amazon.com/dp/B0DBDCNVZD)).

## Quick findings

- Best measured match: **{best['band']} at
  {best['minimum_swr_frequency_mhz']:.6f} MHz, SWR {best['minimum_swr']:.2f}**.
- Full-band SWR at or below 2:1: **{", ".join(full_two_to_one)}**.
- Every supported band has at least part of its range below 2:1.
- 10m is the most frequency-sensitive band and is best around
  **{summaries[-1]['minimum_swr_frequency_mhz']:.6f} MHz**.
- The SDS150 itself starts at 25 MHz, so **10m is the only advertised antenna
  band in this report that the scanner can tune directly**. The lower HF bands
  remain useful for connected HF receivers and amateur transceivers.
- These results are installation-specific. With no dedicated ground or
  counterpoise, the feed line can become part of the antenna's return path.

## Band scorecard

{markdown_table(summaries)}

`Band <=2:1` is the percentage of sampled points inside the listed US amateur
band at SWR 2.0 or lower. `Z at best` is the calibrated complex impedance at the
minimum-SWR point.

## Charts

### Supported-band SWR zooms

![Supported-band SWR zooms](charts/supported_band_swr_zooms.png)

### Performance scorecard

![Band performance scorecard](charts/band_performance_scorecard.png)

### Usable bandwidth

![Usable bandwidth by threshold](charts/usable_bandwidth_by_threshold.png)

### Feed-point impedance

![Supported-band impedance](charts/supported_band_impedance.png)

### Return loss

![Supported-band return loss](charts/supported_band_return_loss.png)

### Smith chart

![Supported-band Smith chart](charts/supported_bands_smith_chart.png)

### 80m-through-10m overview

![Supported bands overview](charts/supported_bands_log_overview.png)

## Interactive report

Open [`interactive-report.html`](interactive-report.html) locally to select a
band and inspect SWR, resistance/reactance, return loss, and reflection
coefficient. It is self-contained and makes no network requests.

## Data files

- [`band_summary.csv`](data/band_summary.csv) - one-row-per-band scorecard.
- [`band_summary.json`](data/band_summary.json) - full threshold intervals and
  machine-readable analysis.
- [`supported_band_points.csv`](data/supported_band_points.csv) - calibrated
  points inside the eight supported US bands.
- [`antenna_full_sweep.s1p`](data/antenna_full_sweep.s1p) - calibrated
  40,001-point Touchstone source from 1.8 through 148 MHz.
- [`measurement_metadata.json`](data/measurement_metadata.json) - instrument,
  calibration, antenna, installation, and analysis metadata.

## Measurement method

- Instrument: NanoVNA-H, firmware 1.2.50.
- Calibration: software one-port ideal OSL at the antenna side of the attached
  adapter; the NanoVNA's saved calibration was preserved.
- Sweep: 1.8-148 MHz, 40,001 points, nominal 3.655 kHz spacing, 1 kHz
  measurement bandwidth.
- Capture time: 2026-08-16 at 12:50 PDT.
- Reference impedance: 50 ohms.
- Installation reported during measurement: no dedicated ground or
  counterpoise.
- Sanity check: reconnecting the calibration load produced median SWR 1.00003
  and median impedance 50.000 ohms on focused 160m and 60m checks.

The supplied load was also the load calibration standard, so the sanity check
establishes calibration stability and connector repeatability rather than
independent traceable accuracy. Antenna surroundings, height, routing,
feed-line length, weather, and common-mode current can shift these results.
"""
    (output / "README.md").write_text(content, encoding="ascii")


def write_html(
    output: Path,
    summaries: list[dict[str, object]],
    interactive: dict[str, dict[str, list[float]]],
    metadata: dict[str, object],
) -> None:
    data = json.dumps(
        {"summaries": summaries, "bands": interactive, "metadata": metadata},
        separators=(",", ":"),
    )
    rows = "\n".join(
        f"""<tr>
<td><strong>{item['band']}</strong></td>
<td>{item['lower_mhz']:g}-{item['upper_mhz']:g}</td>
<td>{item['minimum_swr']:.2f}</td>
<td>{item['minimum_swr_frequency_mhz']:.6f}</td>
<td>{item['resistance_at_minimum_ohm']:.1f} {item['reactance_at_minimum_ohm']:+.1f}j</td>
<td>{item['coverage_percent']['2.0']:.0f}%</td>
<td>{item['longest_contiguous_range']['2.0']}</td>
<td>{item['rating']}</td>
</tr>"""
        for item in summaries
    )
    best = min(summaries, key=lambda item: float(item["minimum_swr"]))
    complete = sum(float(item["maximum_swr"]) <= 2.0 for item in summaries)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JYR8010 EFHW antenna results</title>
<link rel="icon" href="data:,">
<script>
  (() => {{
    const param = new URLSearchParams(window.location.search).get("scoutTheme");
    const theme =
      param || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  }})();
</script>
<style>
:root {{
  color-scheme: light;
  --cp-bg: #f7f4ef;
  --cp-bg-elevated: #fcfbf8;
  --cp-surface: #ffffff;
  --cp-surface-soft: #f5f5f5;
  --cp-border: #dedede;
  --cp-border-strong: #919191;
  --cp-text: #242424;
  --cp-text-muted: #5c5c5c;
  --cp-text-soft: #6f6f6f;
  --cp-accent: #b11f4b;
  --cp-accent-hover: #9a1a41;
  --cp-accent-soft: rgba(177, 31, 75, 0.08);
  --cp-accent-fg: #ffffff;
  --cp-success: #16a34a;
  --cp-danger: #dc2626;
  --cp-warning: #f59e0b;
  --cp-link: #0078d4;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
  --cp-overlay: rgba(255, 255, 255, 0.8);
  --cp-panel: rgba(255, 255, 255, 0.86);
  --cp-panel-strong: rgba(255, 255, 255, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.55);
  --cp-highlight: rgba(177, 31, 75, 0.12);
}}
html[data-theme="dark"] {{
  color-scheme: dark;
  --cp-bg: #3d3b3a;
  --cp-bg-elevated: #343231;
  --cp-surface: #292929;
  --cp-surface-soft: #2e2e2e;
  --cp-border: #474747;
  --cp-border-strong: #5f5f5f;
  --cp-text: #dedede;
  --cp-text-muted: #919191;
  --cp-text-soft: #b0b0b0;
  --cp-accent: #fd8ea1;
  --cp-accent-hover: #fb7b91;
  --cp-accent-soft: rgba(253, 142, 161, 0.14);
  --cp-accent-fg: #1a1a1a;
  --cp-success: #4ade80;
  --cp-danger: #f87171;
  --cp-warning: #fbbf24;
  --cp-link: #4da6ff;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  --cp-overlay: rgba(41, 41, 41, 0.88);
  --cp-panel: rgba(41, 41, 41, 0.72);
  --cp-panel-strong: rgba(41, 41, 41, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.04);
  --cp-highlight: rgba(253, 142, 161, 0.12);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--cp-bg);
  color: var(--cp-text);
  font-family: "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif;
}}
.shell {{ max-width: 1440px; margin: 0 auto; padding: 32px 24px 64px; }}
header {{ display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; }}
h1 {{ margin: 0 0 8px; font-size: clamp(2rem, 5vw, 3.5rem); letter-spacing: -0.04em; }}
h2 {{ margin: 0 0 16px; font-size: 1.35rem; }}
p {{ color: var(--cp-text-muted); line-height: 1.55; }}
.eyebrow {{ color: var(--cp-accent); font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }}
button, select {{
  border: 1px solid var(--cp-border-strong);
  background: var(--cp-surface);
  color: var(--cp-text);
  border-radius: 0.625rem;
  padding: 10px 12px;
  font: inherit;
}}
button {{ cursor: pointer; }}
button:hover {{ border-color: var(--cp-accent); }}
.cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 28px 0; }}
.card, .panel {{
  background: var(--cp-surface);
  border: 1px solid var(--cp-border);
  border-radius: 16px;
  box-shadow: var(--cp-shadow);
}}
.card {{ padding: 20px; }}
.card strong {{ display: block; font-size: 1.75rem; margin-top: 6px; }}
.label {{ color: var(--cp-text-muted); font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; }}
.controls {{ display: flex; gap: 12px; align-items: end; flex-wrap: wrap; margin: 22px 0 16px; }}
.control {{ display: grid; gap: 6px; }}
.charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.panel {{ padding: 18px; min-width: 0; }}
canvas {{ width: 100%; height: 330px; display: block; }}
.wide {{ grid-column: 1 / -1; }}
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: .9rem; }}
th, td {{ padding: 12px 10px; border-bottom: 1px solid var(--cp-border); text-align: left; white-space: nowrap; }}
th {{ color: var(--cp-text-muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; }}
tbody tr:hover {{ background: var(--cp-accent-soft); }}
.note {{ border-left: 4px solid var(--cp-warning); padding: 2px 16px; margin-top: 24px; }}
.tooltip {{
  position: fixed;
  display: none;
  pointer-events: none;
  background: var(--cp-panel-strong);
  color: var(--cp-text);
  border: 1px solid var(--cp-border);
  border-radius: 0.625rem;
  padding: 8px 10px;
  box-shadow: var(--cp-shadow);
  font-family: Consolas, "Courier New", Courier, monospace;
  font-size: .8rem;
  z-index: 10;
}}
footer {{ margin-top: 28px; color: var(--cp-text-muted); font-size: .85rem; }}
a {{ color: var(--cp-link); }}
@media (max-width: 900px) {{
  .cards {{ grid-template-columns: 1fr 1fr; }}
  .charts {{ grid-template-columns: 1fr; }}
  .wide {{ grid-column: auto; }}
  header {{ display: block; }}
  header button {{ margin-top: 12px; }}
}}
@media (max-width: 520px) {{
  .shell {{ padding: 20px 12px 40px; }}
  .cards {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="shell">
  <header>
    <div>
      <div class="eyebrow">Calibrated NanoVNA-H measurement</div>
      <h1>JYR8010 EFHW antenna</h1>
      <p>Interactive supported-band analysis for 80m through 10m. US amateur-band edges; 40,001-point source sweep.</p>
    </div>
    <button id="theme-toggle" type="button">Toggle theme</button>
  </header>
  <section class="cards" aria-label="Measurement highlights">
    <div class="card"><span class="label">Best match</span><strong>{best['minimum_swr']:.2f} SWR</strong><span>{best['band']} at {best['minimum_swr_frequency_mhz']:.6f} MHz</span></div>
    <div class="card"><span class="label">Full-band <=2:1</span><strong>{complete} / 8</strong><span>supported bands</span></div>
    <div class="card"><span class="label">Resolution</span><strong>3.655 kHz</strong><span>nominal point spacing</span></div>
    <div class="card"><span class="label">Reference plane</span><strong>Adapter output</strong><span>software ideal OSL</span></div>
  </section>
  <section class="panel">
    <h2>Explore a supported band</h2>
    <div class="controls">
      <label class="control"><span class="label">Band</span><select id="band-select"></select></label>
      <label class="control"><span class="label">SWR guide</span><select id="threshold-select"><option value="1.5">1.5:1</option><option value="2" selected>2.0:1</option><option value="3">3.0:1</option></select></label>
    </div>
    <div class="charts">
      <div class="panel"><h2>SWR</h2><canvas id="swr-chart"></canvas></div>
      <div class="panel"><h2>Resistance and reactance</h2><p>R is green; X is rose.</p><canvas id="impedance-chart"></canvas></div>
      <div class="panel"><h2>Return loss</h2><canvas id="return-chart"></canvas></div>
      <div class="panel"><h2>Reflection coefficient plane</h2><canvas id="smith-chart"></canvas></div>
    </div>
  </section>
  <section class="panel wide" style="margin-top:16px">
    <h2>Band scorecard</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Band</th><th>US range MHz</th><th>Best SWR</th><th>Best MHz</th><th>Z at best ohms</th><th>Band <=2:1</th><th>Longest <=2:1</th><th>Assessment</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </section>
  <div class="note"><p><strong>SDS150 note:</strong> the scanner starts at 25 MHz, so 10m is the only advertised antenna band here that it can tune directly. Lower HF results apply to connected HF receivers and amateur transceivers.</p></div>
  <div class="note"><p><strong>Installation note:</strong> no dedicated ground or counterpoise was present. The feed line can therefore become part of the EFHW return path, so routing, feed-line length, nearby objects, and a future common-mode choke can change these results.</p></div>
  <footer>Captured 2026-08-16 12:50 PDT | NanoVNA-H firmware 1.2.50 | 1.8-148 MHz | 50-ohm reference | report generated offline</footer>
</div>
<div id="tooltip" class="tooltip"></div>
<script>
const REPORT = {data};
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const colors = () => ({{
  bg: css("--cp-surface"),
  grid: css("--cp-border"),
  text: css("--cp-text"),
  muted: css("--cp-text-muted"),
  accent: css("--cp-accent"),
  success: css("--cp-success"),
  warning: css("--cp-warning"),
  danger: css("--cp-danger")
}});
const select = document.getElementById("band-select");
Object.keys(REPORT.bands).forEach(name => {{
  const option = document.createElement("option");
  option.value = name;
  option.textContent = name;
  select.appendChild(option);
}});
const tooltip = document.getElementById("tooltip");
const canvases = ["swr-chart", "impedance-chart", "return-chart", "smith-chart"].map(id => document.getElementById(id));

function setup(canvas) {{
  const ratio = window.devicePixelRatio || 1;
  const box = canvas.getBoundingClientRect();
  canvas.width = Math.max(320, Math.floor(box.width * ratio));
  canvas.height = Math.max(220, Math.floor(box.height * ratio));
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return {{context, width: canvas.width / ratio, height: canvas.height / ratio}};
}}

function extent(values, include) {{
  let low = Math.min(...values);
  let high = Math.max(...values);
  if (include !== undefined) {{
    low = Math.min(low, include);
    high = Math.max(high, include);
  }}
  const pad = Math.max((high - low) * .1, .01);
  return [low - pad, high + pad];
}}

function lineChart(canvas, x, series, options) {{
  const {{context: ctx, width, height}} = setup(canvas);
  const c = colors();
  const margin = {{left: 58, right: 18, top: 14, bottom: 42}};
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const xRange = [Math.min(...x), Math.max(...x)];
  const allY = series.flatMap(item => item.values.filter(Number.isFinite));
  const yRange = options.yRange || extent(allY, options.includeY);
  const mapX = value => margin.left + (value - xRange[0]) / (xRange[1] - xRange[0]) * plotW;
  const mapY = value => margin.top + (yRange[1] - value) / (yRange[1] - yRange[0]) * plotH;
  ctx.fillStyle = c.bg;
  ctx.fillRect(0, 0, width, height);
  ctx.font = '12px "Segoe UI", sans-serif';
  ctx.lineWidth = 1;
  for (let tick = 0; tick <= 5; tick++) {{
    const px = margin.left + plotW * tick / 5;
    const py = margin.top + plotH * tick / 5;
    ctx.strokeStyle = c.grid;
    ctx.beginPath(); ctx.moveTo(px, margin.top); ctx.lineTo(px, margin.top + plotH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(margin.left, py); ctx.lineTo(margin.left + plotW, py); ctx.stroke();
    ctx.fillStyle = c.muted;
    ctx.textAlign = "center";
    ctx.fillText((xRange[0] + (xRange[1] - xRange[0]) * tick / 5).toFixed(3), px, height - 18);
    ctx.textAlign = "right";
    ctx.fillText((yRange[1] - (yRange[1] - yRange[0]) * tick / 5).toFixed(1), margin.left - 8, py + 4);
  }}
  if (options.guide !== undefined) {{
    const py = mapY(options.guide);
    ctx.strokeStyle = c.warning;
    ctx.setLineDash([6, 5]);
    ctx.beginPath(); ctx.moveTo(margin.left, py); ctx.lineTo(margin.left + plotW, py); ctx.stroke();
    ctx.setLineDash([]);
  }}
  series.forEach((item, index) => {{
    ctx.strokeStyle = item.color || (index ? c.accent : c.success);
    ctx.lineWidth = 2;
    ctx.beginPath();
    item.values.forEach((value, point) => {{
      const px = mapX(x[point]);
      const py = mapY(value);
      if (point) ctx.lineTo(px, py); else ctx.moveTo(px, py);
    }});
    ctx.stroke();
  }});
  ctx.fillStyle = c.text;
  ctx.textAlign = "center";
  ctx.fillText("Frequency (MHz)", margin.left + plotW / 2, height - 2);
  ctx.save();
  ctx.translate(13, margin.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(options.yLabel, 0, 0);
  ctx.restore();
  canvas._plot = {{x, series, margin, plotW, mapX}};
}}

function smithChart(canvas, real, imaginary) {{
  const {{context: ctx, width, height}} = setup(canvas);
  const c = colors();
  const size = Math.min(width, height) - 46;
  const radius = size / 2;
  const cx = width / 2;
  const cy = height / 2;
  ctx.fillStyle = c.bg;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = c.grid;
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx - radius, cy); ctx.lineTo(cx + radius, cy); ctx.stroke();
  [0.2, 0.5, 1, 2, 5].forEach(r => {{
    const center = r / (r + 1);
    const rr = 1 / (r + 1);
    ctx.beginPath(); ctx.arc(cx + center * radius, cy, rr * radius, 0, Math.PI * 2); ctx.stroke();
  }});
  ctx.strokeStyle = c.accent;
  ctx.lineWidth = 2;
  ctx.beginPath();
  real.forEach((value, index) => {{
    const px = cx + value * radius;
    const py = cy - imaginary[index] * radius;
    if (index) ctx.lineTo(px, py); else ctx.moveTo(px, py);
  }});
  ctx.stroke();
  ctx.fillStyle = c.success;
  ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = c.text;
  ctx.textAlign = "center";
  ctx.fillText("50 ohms", cx, cy - 10);
}}

function render() {{
  const name = select.value;
  const band = REPORT.bands[name];
  const guide = Number(document.getElementById("threshold-select").value);
  lineChart(document.getElementById("swr-chart"), band.frequency_mhz, [{{name: "SWR", values: band.swr}}], {{yLabel: "SWR", includeY: 1, guide}});
  lineChart(document.getElementById("impedance-chart"), band.frequency_mhz, [
    {{name: "R", values: band.resistance_ohm, color: colors().success}},
    {{name: "X", values: band.reactance_ohm, color: colors().accent}}
  ], {{yLabel: "Ohms", includeY: 0}});
  lineChart(document.getElementById("return-chart"), band.frequency_mhz, [{{name: "RL", values: band.return_loss_db}}], {{yLabel: "Return loss (dB)", includeY: 9.54}});
  smithChart(document.getElementById("smith-chart"), band.gamma_real, band.gamma_imag);
}}

canvases.slice(0, 3).forEach(canvas => canvas.addEventListener("mousemove", event => {{
  const plot = canvas._plot;
  if (!plot) return;
  const box = canvas.getBoundingClientRect();
  const localX = event.clientX - box.left;
  const fraction = Math.max(0, Math.min(1, (localX - plot.margin.left) / plot.plotW));
  const index = Math.round(fraction * (plot.x.length - 1));
  const values = plot.series.map(item => `${{item.name}} ${{item.values[index].toFixed(3)}}`).join(" | ");
  tooltip.textContent = `${{plot.x[index].toFixed(6)}} MHz | ${{values}}`;
  tooltip.style.display = "block";
  tooltip.style.left = `${{event.clientX + 12}}px`;
  tooltip.style.top = `${{event.clientY + 12}}px`;
}}));
canvases.slice(0, 3).forEach(canvas => canvas.addEventListener("mouseleave", () => tooltip.style.display = "none"));
select.addEventListener("change", render);
document.getElementById("threshold-select").addEventListener("change", render);
document.getElementById("theme-toggle").addEventListener("click", () => {{
  const current = document.documentElement.getAttribute("data-theme");
  document.documentElement.setAttribute("data-theme", current === "dark" ? "light" : "dark");
  render();
}});
window.addEventListener("resize", render);
render();
</script>
</body>
</html>
"""
    (output / "interactive-report.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()

    output = args.output.resolve()
    charts = output / "charts"
    data_dir = output / "data"
    charts.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    frequencies, gamma = load_touchstone(args.source)
    metrics = calculate_metrics(gamma)
    summaries, interactive = analyze_bands(frequencies, gamma, metrics)
    set_plot_style()
    plot_swr_zooms(charts, frequencies, metrics, summaries)
    plot_impedance(charts, frequencies, metrics)
    plot_return_loss(charts, frequencies, metrics)
    plot_performance(charts, summaries)
    plot_threshold_ranges(charts, summaries)
    plot_smith(charts, frequencies, gamma)
    plot_log_overview(charts, frequencies, metrics)
    write_supported_points(data_dir, frequencies, gamma, metrics)
    write_summary_csv(data_dir, summaries)
    (data_dir / "band_summary.json").write_text(
        json.dumps(summaries, indent=2) + "\n", encoding="ascii"
    )
    shutil.copy2(args.source, data_dir / "antenna_full_sweep.s1p")

    metadata: dict[str, object] = {
        "report_generated_at": datetime.now().astimezone().isoformat(),
        "antenna": {
            "model": "JYR8010-150W",
            "type": "end-fed half-wave",
            "radiating_element_length_m": 40,
            "nominal_transformer_ratio": "1:49 / 1:64",
            "advertised_supported_bands": [item[0] for item in BANDS],
            "product_url": "https://www.amazon.com/dp/B0DBDCNVZD",
            "asin": "B0DBDCNVZD",
        },
        "installation": {
            "dedicated_ground": False,
            "dedicated_counterpoise": False,
            "note": (
                "Feed line may be part of the RF return path; installation-specific "
                "common-mode effects are possible."
            ),
        },
        "instrument": {
            "model": "NanoVNA-H",
            "firmware": "1.2.50",
            "measurement_bandwidth_hz": 1000,
            "reference_impedance_ohm": REFERENCE_OHMS,
        },
        "calibration": {
            "type": "software one-port ideal OSL",
            "reference_plane": "antenna side of attached adapter",
            "standards": ["open", "short", "50-ohm load"],
            "device_saved_calibration_preserved": True,
            "created_at": "2026-08-16T12:46:31-07:00",
        },
        "sweep": {
            "captured_at": "2026-08-16T12:50:57-07:00",
            "start_hz": int(frequencies[0]),
            "stop_hz": int(frequencies[-1]),
            "points": int(len(frequencies)),
            "nominal_frequency_step_hz": float(np.median(np.diff(frequencies))),
            "segments": 400,
        },
        "analysis": {
            "band_plan": "United States amateur allocations",
            "supported_bands_only": True,
            "swr_thresholds": list(THRESHOLDS),
            "reference_impedance_ohm": REFERENCE_OHMS,
        },
        "load_reconnection_check": {
            "note": (
                "The calibration load was reconnected, so this establishes drift "
                "and connector repeatability rather than independent traceability."
            ),
            "160m_median_swr": 1.0000310168,
            "60m_median_swr": 1.0000341673,
            "median_resistance_ohm": 50.0,
            "maximum_abs_reactance_ohm": 0.0037,
        },
    }
    (data_dir / "measurement_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="ascii"
    )
    write_readme(output, summaries)
    write_html(output, summaries, interactive, metadata)
    print(f"generated {output}")


if __name__ == "__main__":
    main()
