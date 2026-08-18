#!/usr/bin/env python3
"""Generate the final GOWENIC-module EFHW NanoVNA report and charts."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


BANDS = (
    ("160m", 1_800_000, 2_000_000),
    ("80m", 3_500_000, 4_000_000),
    ("60m", 5_330_500, 5_406_400),
    ("40m", 7_000_000, 7_300_000),
    ("30m", 10_100_000, 10_150_000),
    ("20m", 14_000_000, 14_350_000),
    ("17m", 18_068_000, 18_168_000),
    ("15m", 21_000_000, 21_450_000),
    ("12m", 24_890_000, 24_990_000),
    ("10m", 28_000_000, 29_700_000),
    ("6m", 50_000_000, 54_000_000),
    ("2m", 144_000_000, 148_000_000),
)
INTENDED_HARMONIC_BANDS = ("40m", "20m", "15m", "10m")
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
    "#a43d3d",
    "#3a6d8c",
    "#7d5a35",
    "#536878",
)

HISTORY = (
    {
        "captured_at": "2026-08-17T22:30:48.289996-07:00",
        "run": "2026-08-17_2230_efhw_8ft_initial/broad",
        "configuration": "Initial approximate inverted V; apex about 8 ft; far end low.",
        "change": "Baseline after initial assembly.",
        "effect": "Established the initial 6.304 MHz resonance at SWR 1.52, below 40m.",
        "minimum_swr": 1.5239712029340644,
        "minimum_swr_frequency_hz": 6_304_000,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T22:31:29.670766-07:00",
        "run": "2026-08-17_2230_efhw_8ft_initial/focused",
        "configuration": "Same 8 ft inverted V; three-pass focused repeat.",
        "change": "Higher-resolution confirmation.",
        "effect": "Confirmed the baseline within 0.4 kHz and 0.001 SWR.",
        "minimum_swr": 1.523729884942572,
        "minimum_swr_frequency_hz": 6_304_375,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T22:35:41.379315-07:00",
        "run": "2026-08-17_2230_efhw_8ft_initial/coax-rerouted",
        "configuration": "Same 8 ft inverted V; middle of 12 ft coax rerouted.",
        "change": "Common-mode sensitivity check.",
        "effect": "Shifted resonance down 2.6 kHz and SWR down 0.009; small but measurable feed-line sensitivity.",
        "minimum_swr": 1.5147400995322609,
        "minimum_swr_frequency_hz": 6_301_750,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T22:41:06.381644-07:00",
        "run": "2026-08-17_2240_efhw_8ft_after_22in",
        "configuration": "8 ft inverted V; 22 in total removed.",
        "change": "Removed 22 in of radiator.",
        "effect": "Moved resonance up 158 kHz to 6.460 MHz; minimum SWR rose to 1.59.",
        "minimum_swr": 1.5851758587667555,
        "minimum_swr_frequency_hz": 6_459_555,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T22:45:31.910991-07:00",
        "run": "2026-08-17_2245_efhw_8ft_after_52in",
        "configuration": "8 ft inverted V; 52 in total removed.",
        "change": "Removed another 30 in, 52 in cumulative.",
        "effect": "Moved resonance up another 254 kHz to 6.714 MHz; minimum SWR improved to 1.51.",
        "minimum_swr": 1.5142921901968944,
        "minimum_swr_frequency_hz": 6_713_611,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T22:50:16.432404-07:00",
        "run": "2026-08-17_2250_efhw_8ft_after_60in",
        "configuration": "8 ft inverted V; 60 in total removed.",
        "change": "Removed another 8 in, 60 in cumulative.",
        "effect": "Moved resonance up another 99 kHz to 6.812 MHz; minimum SWR improved to 1.48.",
        "minimum_swr": 1.4807809740542661,
        "minimum_swr_frequency_hz": 6_812_375,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T23:01:44.110914-07:00",
        "run": "2026-08-17_2301_efhw_25ft_sloper_60in_trim",
        "configuration": "25 ft to 3 ft sloper; 8 in feed loop; 12 ft coax; no choke or counterpoise.",
        "change": "Raised far end to about 25 ft and changed coax route.",
        "effect": "Moved resonance into 40m at 7.025 MHz and improved minimum SWR to 1.38.",
        "minimum_swr": 1.3795765581268085,
        "minimum_swr_frequency_hz": 7_025_000,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T23:02:29.510590-07:00",
        "run": "2026-08-17_2301_efhw_25ft_sloper_60in_trim/focused",
        "configuration": "25 ft to 3 ft sloper; 8 in feed loop; 12 ft coax; no choke or counterpoise.",
        "change": "Three-pass focused repeat of the raised sloper.",
        "effect": "Confirmed the raised-sloper result within 0.4 kHz and 0.001 SWR.",
        "minimum_swr": 1.3796619215065329,
        "minimum_swr_frequency_hz": 7_025_375,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T23:14:15.242185-07:00",
        "run": "2026-08-17_2314_efhw_25ft_sloper_14in_loop",
        "configuration": "25 ft to 3 ft sloper; 8 in feed loop; 14 in far loop; no choke or counterpoise.",
        "change": "Set permanent 14 in far-end tie-off loop.",
        "effect": "Shifted resonance down 4.6 kHz and raised minimum SWR by 0.019.",
        "minimum_swr": 1.3988505757124228,
        "minimum_swr_frequency_hz": 7_020_750,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-17T23:21:37.243919-07:00",
        "run": "2026-08-17_2319_efhw_harmonics_25ft_sloper",
        "configuration": "Same sloper and loops; no choke or counterpoise.",
        "change": "Three-pass 40m/20m/15m/10m harmonic characterization.",
        "effect": "Measured minima of 1.40 on 40m, 2.23 on 20m, 4.59 on 15m, and 1.81 on 10m.",
        "minimum_swr": 1.4041192844920765,
        "minimum_swr_frequency_hz": 7_020_500,
        "valid_for_final_configuration": False,
    },
    {
        "captured_at": "2026-08-18T00:27:25.447889-07:00",
        "run": "2026-08-18_0024_gowenic_efhw_final",
        "configuration": "Final 62.5 ft wire, 8 in feed loop, 14 in far loop, 25 ft to 3 ft sloper, 96 in grounded counterpoise, no choke.",
        "change": "Added the final 96 in counterpoise and repeated full OSL-calibrated span.",
        "effect": "Kept 40m essentially unchanged at 1.41, improved 15m from 4.59 to 1.89 and 10m from 1.81 to 1.68, while 20m changed from 2.23 to 2.58.",
        "minimum_swr": 1.406056041265677,
        "minimum_swr_frequency_hz": 7_022_995,
        "valid_for_final_configuration": True,
    },
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
    fig, axes = plt.subplots(4, 3, figsize=(18, 18), constrained_layout=True)
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
        "Final GOWENIC-module EFHW amateur-band SWR zooms\n"
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
    fig, axes = plt.subplots(4, 3, figsize=(18, 18), constrained_layout=True)
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
    fig.suptitle("Feed-point impedance by US amateur band", fontsize=17)
    fig.savefig(output / "supported_band_impedance.png", dpi=200)
    plt.close(fig)


def plot_return_loss(
    output: Path,
    frequencies: np.ndarray,
    metrics: dict[str, np.ndarray],
) -> None:
    fig, axes = plt.subplots(4, 3, figsize=(18, 18), constrained_layout=True)
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
    fig.suptitle("Return loss by US amateur band", fontsize=17)
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
    fig.suptitle("US amateur-band performance scorecard", fontsize=17)
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
    axis.set_title("US amateur-band Smith chart\nDots mark each band's lower edge")
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
    axis.set_title("Measured US amateur bands from 160m through 2m")
    axis.grid(True, which="both", alpha=0.7)
    axis.legend(ncol=8, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.savefig(output / "supported_bands_log_overview.png", dpi=200)
    plt.close(fig)


def plot_tuning_progression(output: Path) -> None:
    labels = [
        "Initial",
        "Focused",
        "Coax route",
        "-22 in",
        "-52 in",
        "-60 in",
        "25 ft broad",
        "25 ft focused",
        "14 in loop",
        "Harmonics",
        "+ counterpoise",
    ]
    frequency_mhz = [
        float(item["minimum_swr_frequency_hz"]) / 1e6 for item in HISTORY
    ]
    swr = [float(item["minimum_swr"]) for item in HISTORY]
    x = np.arange(len(HISTORY))
    fig, left = plt.subplots(figsize=(16, 8), constrained_layout=True)
    right = left.twinx()
    left.plot(
        x,
        frequency_mhz,
        color="#315c8c",
        linewidth=2,
        marker="o",
        label="Minimum-SWR frequency",
    )
    right.plot(
        x,
        swr,
        color="#b11f4b",
        linewidth=2,
        marker="s",
        label="Minimum SWR",
    )
    left.axhspan(7.0, 7.3, color="#23856d", alpha=0.1, label="US 40m band")
    left.set_xticks(x, labels, rotation=35, ha="right")
    left.set_ylabel("Minimum-SWR frequency (MHz)")
    right.set_ylabel("Minimum SWR")
    left.set_title(
        "Tuning progression\n"
        "Earlier runs document configuration effects but do not represent the final counterpoise build"
    )
    left.grid(True, axis="y", alpha=0.7)
    handles_left, labels_left = left.get_legend_handles_labels()
    handles_right, labels_right = right.get_legend_handles_labels()
    left.legend(handles_left + handles_right, labels_left + labels_right, loc="best")
    fig.savefig(output / "tuning_progression.png", dpi=200)
    plt.close(fig)


def plot_build_geometry(output: Path) -> None:
    conductor_feet = 62.5
    loop_consumption_feet = (8 + 14) / 12
    span_feet = conductor_feet - loop_consumption_feet
    vertical_rise_feet = 25 - 3
    horizontal_run_feet = math.sqrt(span_feet**2 - vertical_rise_feet**2)
    angle_degrees = math.degrees(math.atan2(vertical_rise_feet, horizontal_run_feet))

    fig, axis = plt.subplots(figsize=(15, 8), constrained_layout=True)
    axis.plot(
        [0, horizontal_run_feet],
        [3, 25],
        color="#b11f4b",
        linewidth=6,
        solid_capstyle="round",
    )
    axis.scatter([0, horizontal_run_feet], [3, 25], color="#242424", s=75, zorder=5)
    axis.plot([0, -8], [0, 0], color="#315c8c", linewidth=5)
    axis.plot([0, 0], [0, 3], color="#77716d", linestyle="--", linewidth=1.5)
    axis.axhline(0, color="#4f6d3a", linewidth=2)
    axis.text(0.5, 3.6, "Feed end / transformer: 3 ft", fontsize=11)
    axis.text(
        horizontal_run_feet - 16,
        26,
        "Far end: 25 ft",
        fontsize=11,
    )
    axis.text(-8, -1.6, "96 in counterpoise on ground", fontsize=11)
    axis.text(
        horizontal_run_feet * 0.42,
        16.5,
        f"62.5 ft physical conductor\n"
        f"8 in feed loop + 14 in far loop\n"
        f"approx. supported span {span_feet:.2f} ft",
        ha="center",
        bbox={"facecolor": "white", "edgecolor": "#dedede", "alpha": 0.92},
    )
    axis.text(
        horizontal_run_feet * 0.54,
        8,
        f"approx. horizontal run {horizontal_run_feet:.1f} ft\n"
        f"approx. slope {angle_degrees:.1f} degrees",
        ha="center",
    )
    axis.text(
        -7,
        6,
        "Counterpoise connected to\ncoax shield / transformer ground\nNo choke",
        fontsize=11,
    )
    axis.set_xlim(-11, horizontal_run_feet + 4)
    axis.set_ylim(-3, 30)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("Approximate horizontal distance (ft)")
    axis.set_ylabel("Height above ground (ft)")
    axis.set_title("Final EFHW installation geometry (schematic, not to scale at loops)")
    axis.grid(True, alpha=0.5)
    fig.savefig(output / "final_build_geometry.png", dpi=200)
    plt.close(fig)


def write_history(output: Path) -> None:
    history = {
        "note": (
            "All runs before the final 2026-08-18 capture lack the final 96-inch "
            "counterpoise and are retained only as configuration history."
        ),
        "calibration_runs": [
            {
                "run": "2026-08-17_2221_efhw_calibration",
                "range_hz": [5_500_000, 8_500_000],
                "purpose": "Initial 40m tuning calibration.",
            },
            {
                "run": "2026-08-17_2316_efhw_harmonic_calibration",
                "range_hz": [6_500_000, 31_000_000],
                "purpose": "Pre-counterpoise harmonic-band calibration.",
            },
            {
                "run": "2026-08-18_0007_gowenic_efhw_full_calibration",
                "range_hz": [1_800_000, 148_000_000],
                "points": 40_001,
                "purpose": "Final full-span OSL calibration and reconnect verification.",
            },
        ],
        "antenna_runs": list(HISTORY),
    }
    (output / "measurement_history.json").write_text(
        json.dumps(history, indent=2) + "\n", encoding="ascii"
    )
    with (output / "measurement_history.csv").open(
        "w", newline="", encoding="ascii"
    ) as destination:
        writer = csv.DictWriter(destination, fieldnames=HISTORY[0].keys())
        writer.writeheader()
        writer.writerows(HISTORY)


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


def markdown_history_table() -> str:
    rows = [
        "| Time (PDT) | Change | Minimum | Measured effect |",
        "|---|---|---:|---|",
    ]
    for item in HISTORY:
        captured = str(item["captured_at"])[11:19]
        rows.append(
            f"| {captured} | {item['change']} | "
            f"{float(item['minimum_swr_frequency_hz']) / 1e6:.6f} MHz, "
            f"SWR {float(item['minimum_swr']):.2f} | {item['effect']} |"
        )
    return "\n".join(rows)


def write_readme(output: Path, summaries: list[dict[str, object]]) -> None:
    best = min(summaries, key=lambda item: float(item["minimum_swr"]))
    full_two_to_one = [
        str(item["band"])
        for item in summaries
        if float(item["maximum_swr"]) <= 2.0
    ]
    intended = [
        item for item in summaries if str(item["band"]) in INTENDED_HARMONIC_BANDS
    ]
    content = f"""# GOWENIC-module 40m EFHW antenna results

This package characterizes a home-built 40m end-fed half-wave made with the
GOWENIC **"No Tune End Fed Half Antenna" 10 W module**
([Amazon ASIN B0C3JVM9SR](https://www.amazon.com/dp/B0C3JVM9SR)).
It is a generic compensated EFHW board in the QRPGuys style, **not a
QRPGuys-branded product**. The listing specifies 50 ohms and 10 W but does not
publish a band list or transformer ratio.

## Quick findings

- Best measured match: **{best['band']} at
  {best['minimum_swr_frequency_mhz']:.6f} MHz, SWR {best['minimum_swr']:.2f}**.
- Full-band SWR at or below 2:1: **{", ".join(full_two_to_one) or "none"}**.
- Intended harmonic-band result: **40m is <=2:1 across the full US band**;
  15m and 10m have useful subranges; 20m needs a tuner.
- The final 96-inch counterpoise produced a 40m minimum of
  **{intended[0]['minimum_swr']:.2f} at
  {intended[0]['minimum_swr_frequency_mhz']:.6f} MHz**.
- Match quality is installation-specific; height, nearby objects, wet ground,
  counterpoise routing, coax routing, and any future common-mode choke can move
  these results.

## Final build

| Item | Final value |
|---|---|
| Physical radiator wire | 62.5 ft (750 in) |
| Feed-end strain loop | 8 in of wire |
| Far-end tie-off loop | 14 in of wire |
| Approximate supported span after loop consumption | 60 ft 8 in |
| Feed-end height | 3 ft |
| Far-end height | 25 ft |
| Counterpoise | 96 in (8 ft), straight on ground |
| Counterpoise connection | Coax shield / transformer ground |
| Counterpoise direction | Angled away from the antenna direction |
| Feed line | 12 ft coax |
| Common-mode choke | None |

The final reproducible conductor length is **62.5 ft total physical wire**.
Subtracting the two mechanical loop allowances gives an approximate straight
supported span of **60 ft 8 in**. The full conductor remains physically present;
the span figure is for layout, not an instruction to cut off another 22 inches.

## Incremental testing and measured effects

{markdown_history_table()}

The first ten rows are historical configurations. Only the final row includes
the 96-inch counterpoise and represents the finished antenna. The counterpoise
did not materially move the already-good 40m match, but it substantially
improved 15m and modestly improved 10m; 20m became somewhat worse.

## Band scorecard

{markdown_table(summaries)}

`Band <=2:1` is the percentage of sampled points inside the listed US amateur
band at SWR 2.0 or lower. `Z at best` is the calibrated complex impedance at the
minimum-SWR point.

## Charts

### Amateur-band SWR zooms

![Amateur-band SWR zooms](charts/supported_band_swr_zooms.png)

### Performance scorecard

![Band performance scorecard](charts/band_performance_scorecard.png)

### Usable bandwidth

![Usable bandwidth by threshold](charts/usable_bandwidth_by_threshold.png)

### Feed-point impedance

![Supported-band impedance](charts/supported_band_impedance.png)

### Return loss

![Supported-band return loss](charts/supported_band_return_loss.png)

### Smith chart

![Amateur-band Smith chart](charts/supported_bands_smith_chart.png)

### Full amateur-band overview

![Amateur bands overview](charts/supported_bands_log_overview.png)

### Tuning progression

![Tuning progression](charts/tuning_progression.png)

### Final installation geometry

![Final installation geometry](charts/final_build_geometry.png)

## Interactive report

Open [`interactive-report.html`](interactive-report.html) locally to select a
band and inspect SWR, resistance/reactance, return loss, and reflection
coefficient. It is self-contained and makes no network requests.

## Data files

- [`band_summary.csv`](data/band_summary.csv) - one-row-per-band scorecard.
- [`band_summary.json`](data/band_summary.json) - full threshold intervals and
  machine-readable analysis.
- [`supported_band_points.csv`](data/supported_band_points.csv) - calibrated
  points inside the twelve measured US amateur bands.
- [`antenna_full_sweep.s1p`](data/antenna_full_sweep.s1p) - calibrated
  40,001-point Touchstone source from 1.8 through 148 MHz.
- [`measurement_metadata.json`](data/measurement_metadata.json) - instrument,
  calibration, antenna, installation, and analysis metadata.
- [`measurement_history.json`](data/measurement_history.json) and
  [`measurement_history.csv`](data/measurement_history.csv) - every tuning run,
  configuration change, and validity status.
- [`measurements/history/`](measurements/history/) - preserved source artifacts
  from every pre-counterpoise antenna run.
- [`measurements/2026-08-18-final/`](measurements/2026-08-18-final/) - complete
  final counterpoise-installed measurement output.
- [`measurements/calibration-history/`](measurements/calibration-history/) -
  preserved initial 40m and pre-counterpoise harmonic OSL calibrations.
- [`REPRODUCE.md`](REPRODUCE.md) - build and measurement reproduction steps.
- [`LLM_HANDOFF_PROMPT.md`](LLM_HANDOFF_PROMPT.md) - a reusable prompt for
  another LLM to repeat the complete process.

## Measurement method

- Instrument: NanoVNA-H, firmware 1.2.50.
- Calibration: software one-port ideal OSL at the antenna side of the attached
  adapter; the NanoVNA's saved calibration was preserved.
- Sweep: 1.8-148 MHz, 40,001 points, nominal 3.655 kHz spacing, 1 kHz
  measurement bandwidth.
- Calibration time: 2026-08-18 at 00:10-00:18 PDT.
- Final antenna capture time: 2026-08-18 at 00:24-00:27 PDT.
- Reference impedance: 50 ohms.
- Reconnected-load verification across the full span: median SWR **1.00052**,
  95th percentile **1.00088**, maximum **1.01115**, and median impedance
  **50.008 + j0.024 ohms**.

The reconnected load was also the load calibration standard, so the sanity check
establishes calibration stability and connector repeatability rather than
independent traceable accuracy. Antenna surroundings, height, routing,
feed-line length, weather, and common-mode current can shift these results.
"""
    (output / "README.md").write_text(content, encoding="ascii")


def write_reproduction_files(output: Path) -> None:
    reproduce = """# Reproduce this EFHW build and measurement

## Build

1. Cut exactly 62.5 ft (750 in) of radiator wire.
2. Attach the feed end to the GOWENIC 10 W generic EFHW module.
3. Form an 8 in feed-end strain loop and a 14 in far-end tie-off loop. Do not
   remove another 22 in; those allowances are already part of the 62.5 ft
   physical conductor.
4. Install as a sloper with the transformer/feed end 3 ft above ground and the
   far end 25 ft above ground.
5. Connect a 96 in counterpoise to the coax shield / transformer ground.
6. Lay the counterpoise straight on the ground, angled away from the radiator.
7. Use the 12 ft coax route recorded for this test and do not install a choke.

## Measure

1. Keep the NanoVNA-H, adapter chain, and reference plane unchanged.
2. Set 1.8-148 MHz, 400 overlapping 101-point segments, yielding 40,001 unique
   points at nominal 3.655 kHz spacing and 1 kHz measurement bandwidth.
3. Capture raw OPEN, SHORT, and 50-ohm LOAD standards at the antenna-side
   adapter plane with device calibration disabled during each scan.
4. Solve the software one-port ideal OSL error terms.
5. Physically disconnect and reconnect the LOAD, repeat the full-span sweep,
   and reject the calibration if reconnect behavior is materially worse than
   the baseline in `data/measurement_metadata.json`.
6. Replace the LOAD with the undisturbed final antenna and repeat the full span.
7. Run:

```bash
python3 antenna-results/antennas/gowenic-efhw/generate_report.py \\
  --source /path/to/final/antenna.s1p \\
  --raw-capture /path/to/final/antenna_raw.npz \\
  --measurement-summary /path/to/final/summary.json \\
  --final-measurement-dir /path/to/final \\
  --calibration-dir /path/to/final/full_calibration \\
  --history-root /path/to/nanovna_measurements
```

The generator uses only NumPy and Matplotlib and recreates every chart, table,
metadata file, and offline interactive report.
"""
    (output / "REPRODUCE.md").write_text(reproduce, encoding="ascii")

    prompt = """# LLM handoff prompt

You are continuing a calibrated NanoVNA antenna-characterization workflow.
Reproduce the complete process rather than only summarizing an existing plot.

Build under test:
- Generic GOWENIC "No Tune End Fed Half Antenna" 10 W module, Amazon ASIN
  B0C3JVM9SR. It resembles a compensated QRPGuys-style design but is not a
  QRPGuys-branded board.
- 62.5 ft total physical radiator wire.
- 8 in feed-end strain loop and 14 in far-end tie-off loop.
- Sloper: feed end 3 ft, far end 25 ft.
- 96 in counterpoise connected to coax shield / transformer ground, laid
  straight on the ground and angled away from the antenna direction.
- 12 ft coax and no common-mode choke.

Measurement requirements:
1. Preserve every run and record each physical configuration change.
2. At the antenna-side adapter reference plane, capture fresh OPEN, SHORT, and
   50-ohm LOAD data from 1.8 through 148 MHz using 400 overlapping 101-point
   segments (40,001 unique points, nominal 3.655 kHz spacing) with the VNA's
   internal correction disabled during raw captures.
3. Solve and apply a software one-port ideal OSL calibration.
4. Physically reconnect the load and run an independent full-span verification.
   Treat this as connector-repeatability and drift evidence, not traceable
   accuracy, because the same load is used as the calibration standard.
5. Connect the final antenna without disturbing its geometry and capture a new
   full-span calibrated complex-S11 sweep. Do not reuse pre-counterpoise sweeps
   as final data.
6. Export raw NPZ/CSV captures, calibrated RI Touchstone, point CSV, JSON/CSV
   band summaries, SWR/return-loss/impedance/Smith plots, a build schematic,
   tuning-progression visualization, metadata, reproduction steps, and a
   self-contained interactive HTML report.
7. Analyze all US amateur bands from 160m through 2m, with special emphasis on
   the intended 40m/20m/15m/10m harmonic set. Report minimum, maximum, median,
   impedance and return loss at minimum, percent coverage at SWR <=1.5/2/3, and
   the longest contiguous <=2:1 range.
8. State clearly that SWR measures impedance match, not gain, efficiency,
   radiation pattern, or receive sensitivity.
9. Distinguish the generic GOWENIC board from a genuine QRPGuys product.
10. Make generation deterministic and retain old runs as historical only when
    their configuration differs from the final counterpoise build.
"""
    (output / "LLM_HANDOFF_PROMPT.md").write_text(prompt, encoding="ascii")


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
<title>GOWENIC-module EFHW antenna results</title>
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
      <h1>GOWENIC-module 40m EFHW</h1>
      <p>Interactive US amateur-band analysis from 160m through 2m. Final 62.5 ft sloper with 96 in counterpoise; 40,001-point source sweep.</p>
    </div>
    <button id="theme-toggle" type="button">Toggle theme</button>
  </header>
  <section class="cards" aria-label="Measurement highlights">
    <div class="card"><span class="label">Best match</span><strong>{best['minimum_swr']:.2f} SWR</strong><span>{best['band']} at {best['minimum_swr_frequency_mhz']:.6f} MHz</span></div>
    <div class="card"><span class="label">Full-band <=2:1</span><strong>{complete} / 12</strong><span>measured amateur bands</span></div>
    <div class="card"><span class="label">Resolution</span><strong>3.655 kHz</strong><span>nominal point spacing</span></div>
    <div class="card"><span class="label">Reference plane</span><strong>Adapter output</strong><span>software ideal OSL</span></div>
  </section>
  <section class="panel">
    <h2>Explore an amateur band</h2>
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
  <div class="note"><p><strong>Hardware identity:</strong> this is the generic GOWENIC 10 W module sold under ASIN B0C3JVM9SR. It is QRPGuys-style, not a genuine QRPGuys-branded board.</p></div>
  <div class="note"><p><strong>Installation note:</strong> the final build uses a 96 in counterpoise connected to transformer ground, straight on the ground and angled away from the radiator. There is no common-mode choke. Geometry, ground conditions, feed-line routing, and nearby objects can change these results.</p></div>
  <div class="note"><p><strong>Interpretation:</strong> SWR measures impedance match. It does not establish antenna gain, efficiency, radiation pattern, or receive sensitivity.</p></div>
  <footer>Captured 2026-08-18 00:24-00:27 PDT | NanoVNA-H firmware 1.2.50 | 1.8-148 MHz | 50-ohm reference | report generated offline</footer>
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
    parser.add_argument("--raw-capture", type=Path)
    parser.add_argument("--measurement-summary", type=Path)
    parser.add_argument("--final-measurement-dir", type=Path)
    parser.add_argument("--calibration-dir", type=Path)
    parser.add_argument("--history-root", type=Path)
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
    plot_tuning_progression(charts)
    plot_build_geometry(charts)
    write_supported_points(data_dir, frequencies, gamma, metrics)
    write_summary_csv(data_dir, summaries)
    write_history(data_dir)
    (data_dir / "band_summary.json").write_text(
        json.dumps(summaries, indent=2) + "\n", encoding="ascii"
    )
    shutil.copy2(args.source, data_dir / "antenna_full_sweep.s1p")
    if args.raw_capture:
        shutil.copy2(args.raw_capture, data_dir / "antenna_raw.npz")
    if args.measurement_summary:
        shutil.copy2(args.measurement_summary, data_dir / "source_summary.json")
    if args.final_measurement_dir:
        shutil.copytree(
            args.final_measurement_dir,
            output / "measurements" / "2026-08-18-final",
            dirs_exist_ok=True,
        )
    if args.calibration_dir:
        calibration_output = data_dir / "calibration"
        calibration_output.mkdir(parents=True, exist_ok=True)
        for source_file in args.calibration_dir.glob("*"):
            if source_file.is_file():
                shutil.copy2(source_file, calibration_output / source_file.name)
        verification = args.calibration_dir / "load-verification"
        if verification.is_dir():
            shutil.copytree(
                verification,
                calibration_output / "load-verification",
                dirs_exist_ok=True,
            )
    if args.history_root:
        history_output = output / "measurements" / "history"
        history_output.mkdir(parents=True, exist_ok=True)
        run_directories = {
            str(item["run"]).split("/", 1)[0]
            for item in HISTORY
            if not bool(item["valid_for_final_configuration"])
        }
        for run_directory in sorted(run_directories):
            shutil.copytree(
                args.history_root / run_directory,
                history_output / run_directory,
                dirs_exist_ok=True,
            )
        calibration_history = output / "measurements" / "calibration-history"
        for run_directory in (
            "2026-08-17_2221_efhw_calibration",
            "2026-08-17_2316_efhw_harmonic_calibration",
        ):
            shutil.copytree(
                args.history_root / run_directory,
                calibration_history / run_directory,
                dirs_exist_ok=True,
            )

    metadata: dict[str, object] = {
        "report_generated_at": "2026-08-18T00:27:25.447889-07:00",
        "antenna": {
            "module_brand": "GOWENIC",
            "listing_name": "No Tune End Fed Half Antenna",
            "type": "generic compensated end-fed half-wave module",
            "identity_note": (
                "QRPGuys-style generic board; not a QRPGuys-branded product."
            ),
            "rated_power_w": 10,
            "listing_impedance_ohm": 50,
            "published_transformer_ratio": None,
            "advertised_supported_bands": None,
            "intended_harmonic_bands": list(INTENDED_HARMONIC_BANDS),
            "physical_radiator_length_ft": 62.5,
            "product_url": "https://www.amazon.com/dp/B0C3JVM9SR",
            "asin": "B0C3JVM9SR",
        },
        "installation": {
            "configuration": "sloper",
            "feed_end_height_ft": 3,
            "far_end_height_ft": 25,
            "feed_end_strain_loop_wire_in": 8,
            "far_end_tie_off_loop_wire_in": 14,
            "approximate_supported_span_ft": 60 + 8 / 12,
            "counterpoise_length_in": 96,
            "counterpoise_connection": "coax shield / transformer ground",
            "counterpoise_layout": (
                "straight on ground, angled away from antenna direction"
            ),
            "feed_line_length_ft": 12,
            "common_mode_choke": False,
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
            "created_at": "2026-08-18T00:18:10.227204-07:00",
        },
        "sweep": {
            "captured_at": "2026-08-18T00:27:25.447889-07:00",
            "start_hz": int(frequencies[0]),
            "stop_hz": int(frequencies[-1]),
            "points": int(len(frequencies)),
            "nominal_frequency_step_hz": float(np.median(np.diff(frequencies))),
            "segments": 400,
        },
        "analysis": {
            "band_plan": "United States amateur allocations",
            "all_measured_amateur_bands": [item[0] for item in BANDS],
            "intended_harmonic_bands": list(INTENDED_HARMONIC_BANDS),
            "swr_thresholds": list(THRESHOLDS),
            "reference_impedance_ohm": REFERENCE_OHMS,
        },
        "load_reconnection_check": {
            "note": (
                "The calibration load was reconnected, so this establishes drift "
                "and connector repeatability rather than independent traceability."
            ),
            "range_hz": [1_800_000, 148_000_000],
            "points": 40_001,
            "median_swr": 1.000518743210567,
            "p95_swr": 1.0008795993501658,
            "maximum_swr": 1.0111497728192607,
            "median_resistance_ohm": 50.008349285302536,
            "median_reactance_ohm": 0.02413502519939014,
        },
    }
    (data_dir / "measurement_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="ascii"
    )
    write_readme(output, summaries)
    write_reproduction_files(output)
    write_html(output, summaries, interactive, metadata)
    print(f"generated {output}")


if __name__ == "__main__":
    main()
