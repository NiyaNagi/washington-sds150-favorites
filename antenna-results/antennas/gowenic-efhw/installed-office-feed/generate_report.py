#!/usr/bin/env python3
"""Generate the GOWENIC EFHW outdoor-vs-office-feed comparison package."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import tempfile
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


REFERENCE_OHMS = 50.0
THRESHOLDS = (1.5, 2.0, 3.0)
BANDS = (
    ("160m", 1_800_000, 2_000_000),
    ("80m", 3_500_000, 4_000_000),
    ("60m envelope", 5_330_500, 5_406_400),
    ("40m", 7_000_000, 7_300_000),
    ("30m", 10_100_000, 10_150_000),
    ("20m", 14_000_000, 14_350_000),
    ("17m", 18_068_000, 18_168_000),
    ("15m", 21_000_000, 21_450_000),
    ("12m", 24_890_000, 24_990_000),
    ("10m", 28_000_000, 29_700_000),
    ("6m", 50_000_000, 54_000_000),
)
COLORS = {
    "outdoor": "#315c8c",
    "office": "#b11f4b",
    "repeat": "#23856d",
    "grid": "#d8d3cd",
    "text": "#242424",
    "muted": "#77716d",
}


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
    result_frequencies = np.asarray(frequencies, dtype=np.int64)
    result_samples = np.asarray(samples, dtype=np.complex128)
    if np.any(np.diff(result_frequencies) <= 0):
        raise ValueError(f"non-increasing frequencies in {path}")
    return result_frequencies, result_samples


def calculate_metrics(gamma: np.ndarray) -> dict[str, np.ndarray]:
    magnitude = np.abs(gamma)
    with np.errstate(divide="ignore", invalid="ignore"):
        swr = np.where(magnitude < 1.0, (1.0 + magnitude) / (1.0 - magnitude), np.inf)
        return_loss = -20.0 * np.log10(magnitude)
        impedance = REFERENCE_OHMS * (1.0 + gamma) / (1.0 - gamma)
    return {
        "magnitude": magnitude,
        "phase_deg": np.angle(gamma, deg=True),
        "swr": swr,
        "return_loss_db": return_loss,
        "resistance_ohm": impedance.real,
        "reactance_ohm": impedance.imag,
    }


def interpolate_complex(
    target: np.ndarray, source: np.ndarray, values: np.ndarray
) -> np.ndarray:
    if target[0] < source[0] or target[-1] > source[-1]:
        raise ValueError("interpolation target extends outside source frequency range")
    return np.interp(target, source, values.real) + 1j * np.interp(
        target, source, values.imag
    )


def contiguous_ranges(
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


def longest_range(ranges: list[tuple[int, int]]) -> str:
    if not ranges:
        return "none"
    start, stop = max(ranges, key=lambda item: item[1] - item[0])
    if start == stop:
        return f"{start / 1e6:.4f} MHz"
    return f"{start / 1e6:.4f}-{stop / 1e6:.4f} MHz"


def summarize_band(
    name: str,
    lower: int,
    upper: int,
    frequencies: np.ndarray,
    gamma: np.ndarray,
) -> dict[str, object]:
    metrics = calculate_metrics(gamma)
    indexes = np.flatnonzero((frequencies >= lower) & (frequencies <= upper))
    if not indexes.size:
        raise ValueError(f"no samples found for {name}")
    swr = metrics["swr"][indexes]
    finite = np.flatnonzero(np.isfinite(swr))
    best_local = finite[np.argmin(swr[finite])]
    best = indexes[best_local]
    coverage = {
        f"{threshold:.1f}": float(100.0 * np.mean(swr <= threshold))
        for threshold in THRESHOLDS
    }
    ranges = {
        f"{threshold:.1f}": longest_range(
            contiguous_ranges(frequencies[indexes], swr, threshold)
        )
        for threshold in THRESHOLDS
    }
    return {
        "band": name,
        "lower_hz": lower,
        "upper_hz": upper,
        "points": int(indexes.size),
        "minimum_swr": float(metrics["swr"][best]),
        "minimum_swr_frequency_hz": int(frequencies[best]),
        "maximum_swr": float(np.nanmax(swr)),
        "median_swr": float(np.nanmedian(swr)),
        "return_loss_at_minimum_db": float(metrics["return_loss_db"][best]),
        "resistance_at_minimum_ohm": float(metrics["resistance_ohm"][best]),
        "reactance_at_minimum_ohm": float(metrics["reactance_ohm"][best]),
        "coverage_percent": coverage,
        "longest_contiguous_range": ranges,
    }


def analyze_bands(
    frequencies: np.ndarray, gamma: np.ndarray
) -> list[dict[str, object]]:
    return [
        summarize_band(name, lower, upper, frequencies, gamma)
        for name, lower, upper in BANDS
    ]


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#f7f4ef",
            "axes.facecolor": "#ffffff",
            "axes.edgecolor": "#8a8580",
            "axes.labelcolor": COLORS["text"],
            "axes.titlecolor": COLORS["text"],
            "xtick.color": "#4d4a47",
            "ytick.color": "#4d4a47",
            "grid.color": COLORS["grid"],
            "font.family": "DejaVu Sans",
            "font.size": 10,
        }
    )


def plot_overview(
    output: Path,
    outdoor_f: np.ndarray,
    outdoor_metrics: dict[str, np.ndarray],
    office_f: np.ndarray,
    office_metrics: dict[str, np.ndarray],
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), constrained_layout=True)
    axes[0].semilogx(
        outdoor_f / 1e6,
        np.minimum(outdoor_metrics["swr"], 20),
        color=COLORS["outdoor"],
        linewidth=1,
        label="August 18: 75 ft LS400 outdoors",
    )
    axes[0].semilogx(
        office_f / 1e6,
        np.minimum(office_metrics["swr"], 20),
        color=COLORS["office"],
        linewidth=1,
        label="August 23: 75 ft + ribbon + 25 ft to office",
    )
    axes[0].axhline(2, color=COLORS["muted"], linestyle="--", linewidth=1)
    axes[0].set(xlabel="Frequency (MHz)", ylabel="SWR (clipped at 20)", ylim=(1, 20))
    axes[0].grid(True, which="both", alpha=0.7)
    axes[0].legend()

    axes[1].semilogx(
        outdoor_f / 1e6,
        outdoor_metrics["return_loss_db"],
        color=COLORS["outdoor"],
        linewidth=1,
        label="75 ft outdoor baseline",
    )
    axes[1].semilogx(
        office_f / 1e6,
        office_metrics["return_loss_db"],
        color=COLORS["office"],
        linewidth=1,
        label="100 ft + window transition",
    )
    axes[1].axhline(9.54, color=COLORS["muted"], linestyle="--", linewidth=1)
    axes[1].set(xlabel="Frequency (MHz)", ylabel="Return loss (dB)")
    axes[1].grid(True, which="both", alpha=0.7)
    axes[1].legend()
    fig.suptitle(
        "GOWENIC EFHW feed-system comparison\n"
        "Input impedance at the VNA-side adapter; cable and transition are included",
        fontsize=16,
    )
    fig.savefig(output / "full_span_comparison.png", dpi=200)
    plt.close(fig)


def plot_band_comparison(
    output: Path,
    outdoor_f: np.ndarray,
    outdoor_metrics: dict[str, np.ndarray],
    office_f: np.ndarray,
    office_metrics: dict[str, np.ndarray],
    outdoor_summary: list[dict[str, object]],
    office_summary: list[dict[str, object]],
) -> None:
    fig, axes = plt.subplots(4, 3, figsize=(18, 18), constrained_layout=True)
    for axis, band, old, new in zip(
        axes.flat, BANDS, outdoor_summary, office_summary
    ):
        name, lower, upper = band
        old_selected = (outdoor_f >= lower) & (outdoor_f <= upper)
        new_selected = (office_f >= lower) & (office_f <= upper)
        axis.plot(
            outdoor_f[old_selected] / 1e6,
            outdoor_metrics["swr"][old_selected],
            color=COLORS["outdoor"],
            linewidth=1.7,
            label="75 ft outdoor",
        )
        axis.plot(
            office_f[new_selected] / 1e6,
            office_metrics["swr"][new_selected],
            color=COLORS["office"],
            linewidth=1.7,
            label="100 ft + ribbon",
        )
        axis.axhline(2, color=COLORS["muted"], linestyle="--", linewidth=0.8)
        axis.scatter(
            float(old["minimum_swr_frequency_hz"]) / 1e6,
            float(old["minimum_swr"]),
            color=COLORS["outdoor"],
            s=24,
        )
        axis.scatter(
            float(new["minimum_swr_frequency_hz"]) / 1e6,
            float(new["minimum_swr"]),
            color=COLORS["office"],
            s=24,
        )
        maximum = max(
            np.nanmax(outdoor_metrics["swr"][old_selected]),
            np.nanmax(office_metrics["swr"][new_selected]),
        )
        axis.set(
            title=(
                f"{name}: {float(old['minimum_swr']):.2f} -> "
                f"{float(new['minimum_swr']):.2f}"
            ),
            xlabel="Frequency (MHz)",
            ylabel="SWR",
            xlim=(lower / 1e6, upper / 1e6),
            ylim=(1, max(2.2, min(20, maximum * 1.08))),
        )
        axis.grid(True, alpha=0.7)
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2)
    fig.suptitle(
        "US amateur-band SWR: outdoor baseline vs installed office feed",
        fontsize=17,
    )
    fig.savefig(output / "amateur_band_swr_comparison.png", dpi=200)
    plt.close(fig)


def plot_scorecard(
    output: Path,
    outdoor_summary: list[dict[str, object]],
    office_summary: list[dict[str, object]],
) -> None:
    names = [str(item["band"]) for item in office_summary]
    old_min = [float(item["minimum_swr"]) for item in outdoor_summary]
    new_min = [float(item["minimum_swr"]) for item in office_summary]
    old_coverage = [
        float(item["coverage_percent"]["2.0"])  # type: ignore[index]
        for item in outdoor_summary
    ]
    new_coverage = [
        float(item["coverage_percent"]["2.0"])  # type: ignore[index]
        for item in office_summary
    ]
    y = np.arange(len(names))
    fig, (left, right) = plt.subplots(1, 2, figsize=(16, 8), constrained_layout=True)
    left.barh(y + 0.18, np.minimum(old_min, 20), height=0.35, color=COLORS["outdoor"])
    left.barh(y - 0.18, np.minimum(new_min, 20), height=0.35, color=COLORS["office"])
    left.axvline(2, color=COLORS["muted"], linestyle="--")
    left.set_yticks(y, names)
    left.invert_yaxis()
    left.set_xlabel("Minimum SWR (values above 20 clipped)")
    left.set_title("Best match in each band")
    left.grid(True, axis="x", alpha=0.7)

    width = 0.36
    x = np.arange(len(names))
    right.bar(x - width / 2, old_coverage, width, color=COLORS["outdoor"], label="75 ft")
    right.bar(x + width / 2, new_coverage, width, color=COLORS["office"], label="100 ft + ribbon")
    right.set_xticks(x, names, rotation=45)
    right.set_ylim(0, 100)
    right.set_ylabel("Percent of band at SWR <= 2:1")
    right.set_title("Usable no-tuner coverage")
    right.grid(True, axis="y", alpha=0.7)
    right.legend()
    fig.suptitle("Feed-system band scorecard", fontsize=17)
    fig.savefig(output / "band_scorecard.png", dpi=200)
    plt.close(fig)


def plot_repeatability(
    output: Path,
    frequencies: np.ndarray,
    first_gamma: np.ndarray,
    repeat_gamma: np.ndarray,
) -> dict[str, float]:
    first_metrics = calculate_metrics(first_gamma)
    repeat_metrics = calculate_metrics(repeat_gamma)
    complex_delta = np.abs(first_gamma - repeat_gamma)
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
        np.minimum(swr_delta, 1.5),
        color=COLORS["office"],
        linewidth=0.8,
    )
    axes[1].set(
        xlabel="Frequency (MHz)",
        ylabel="Absolute SWR delta (clipped at 1.5)",
    )
    axes[1].grid(True, which="both", alpha=0.7)
    fig.suptitle(
        "Unchanged installed-system repeatability\n"
        f"Median complex delta {result['median_complex_s11_delta']:.5f}; "
        f"median SWR delta {result['median_swr_delta']:.4f}",
        fontsize=16,
    )
    fig.savefig(output / "repeatability.png", dpi=200)
    plt.close(fig)
    return result


def plot_open_path_loss(
    output: Path, frequencies: np.ndarray, gamma: np.ndarray
) -> dict[str, float]:
    magnitude = np.abs(gamma)
    with np.errstate(divide="ignore"):
        round_trip_loss = -20.0 * np.log10(magnitude)
    estimated_one_way_loss = round_trip_loss / 2.0
    result = {
        "median_open_magnitude": float(np.median(magnitude)),
        "p05_open_magnitude": float(np.percentile(magnitude, 5)),
        "p95_open_magnitude": float(np.percentile(magnitude, 95)),
        "median_apparent_one_way_attenuation_db": float(
            np.median(estimated_one_way_loss)
        ),
        "apparent_one_way_attenuation_at_7_mhz_db": float(
            estimated_one_way_loss[np.argmin(np.abs(frequencies - 7_000_000))]
        ),
        "apparent_one_way_attenuation_at_54_mhz_db": float(
            estimated_one_way_loss[np.argmin(np.abs(frequencies - 54_000_000))]
        ),
    }
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), constrained_layout=True)
    axes[0].semilogx(
        frequencies / 1e6, magnitude, color=COLORS["outdoor"], linewidth=1
    )
    axes[0].set(xlabel="Frequency (MHz)", ylabel="Open-path |Gamma|", ylim=(0, 1.05))
    axes[0].grid(True, which="both", alpha=0.7)
    axes[1].semilogx(
        frequencies / 1e6,
        estimated_one_way_loss,
        color=COLORS["office"],
        linewidth=1,
    )
    axes[1].set(
        xlabel="Frequency (MHz)",
        ylabel="Apparent one-way attenuation (dB)",
    )
    axes[1].grid(True, which="both", alpha=0.7)
    fig.suptitle(
        "Far-end-open feed-path diagnostic\n"
        "Valid as loss only for an ideal open on a uniform, well-matched line",
        fontsize=16,
    )
    fig.savefig(output / "far_end_open_diagnostic.png", dpi=200)
    plt.close(fig)
    return result


def plot_feed_layout(output: Path) -> None:
    fig, axis = plt.subplots(figsize=(16, 6), constrained_layout=True)
    x = [0, 2.5, 5.0, 7.0, 9.5, 12.5]
    labels = [
        "NanoVNA / radio\nCH0",
        "25 ft LS400\ninside office",
        "Window flat-ribbon\ntransition",
        "75 ft LS400\noutdoors",
        "EFHW transformer\n+ 96 in counterpoise",
        "62.5 ft radiator\n25 ft to 3 ft sloper",
    ]
    axis.plot(x, [0] * len(x), color=COLORS["muted"], linewidth=3)
    for position, label in zip(x, labels):
        axis.scatter(position, 0, color=COLORS["office"], s=130, zorder=4)
        axis.text(
            position,
            0.4 if position % 5 else -0.65,
            label,
            ha="center",
            va="center",
            fontsize=11,
            bbox={"facecolor": "white", "edgecolor": COLORS["grid"], "alpha": 0.95},
        )
    axis.annotate(
        "Office equipment and local RF environment",
        xy=(1.5, 0),
        xytext=(1.5, 1.15),
        ha="center",
        arrowprops={"arrowstyle": "->", "color": COLORS["muted"]},
    )
    axis.set_xlim(-1, 13.5)
    axis.set_ylim(-1.3, 1.6)
    axis.axis("off")
    axis.set_title(
        "August 23 installed-system measurement plane\n"
        "The VNA sees the complete 100 ft feed path, window transition, and antenna",
        fontsize=16,
    )
    fig.savefig(output / "installed_feed_layout.png", dpi=200)
    plt.close(fig)


def write_average_touchstone(
    output: Path, frequencies: np.ndarray, gamma: np.ndarray
) -> None:
    with output.open("w", encoding="ascii") as destination:
        destination.write("! Two-sweep complex average, installed office-feed system\n")
        destination.write("# Hz S RI R 50\n")
        for frequency, sample in zip(frequencies, gamma):
            destination.write(
                f"{int(frequency)} {sample.real:.12g} {sample.imag:.12g}\n"
            )


def normalize_csv_line_endings(root: Path) -> None:
    for path in root.rglob("*.csv"):
        content = path.read_text(encoding="ascii")
        path.write_text(content, encoding="ascii")


def write_comparison_points(
    output: Path,
    frequencies: np.ndarray,
    office_gamma: np.ndarray,
    repeat_gamma: np.ndarray,
    outdoor_gamma: np.ndarray,
) -> None:
    average_gamma = (office_gamma + repeat_gamma) / 2.0
    office_metrics = calculate_metrics(average_gamma)
    outdoor_metrics = calculate_metrics(outdoor_gamma)
    with output.open("w", newline="", encoding="ascii") as destination:
        writer = csv.writer(destination)
        writer.writerow(
            (
                "frequency_hz",
                "frequency_mhz",
                "office_s11_real",
                "office_s11_imag",
                "office_swr",
                "office_resistance_ohm",
                "office_reactance_ohm",
                "outdoor_s11_real_interpolated",
                "outdoor_s11_imag_interpolated",
                "outdoor_swr_interpolated",
            )
        )
        writer.writerows(
            zip(
                frequencies,
                frequencies / 1e6,
                average_gamma.real,
                average_gamma.imag,
                office_metrics["swr"],
                office_metrics["resistance_ohm"],
                office_metrics["reactance_ohm"],
                outdoor_gamma.real,
                outdoor_gamma.imag,
                outdoor_metrics["swr"],
            )
        )


def write_band_csv(
    output: Path,
    outdoor: list[dict[str, object]],
    office: list[dict[str, object]],
) -> None:
    fields = (
        "band",
        "lower_mhz",
        "upper_mhz",
        "outdoor_minimum_swr",
        "outdoor_minimum_frequency_mhz",
        "outdoor_coverage_at_or_below_2_percent",
        "office_minimum_swr",
        "office_minimum_frequency_mhz",
        "office_maximum_swr",
        "office_median_swr",
        "office_resistance_at_minimum_ohm",
        "office_reactance_at_minimum_ohm",
        "office_coverage_at_or_below_1_5_percent",
        "office_coverage_at_or_below_2_percent",
        "office_coverage_at_or_below_3_percent",
        "office_longest_range_at_or_below_2",
    )
    with output.open("w", newline="", encoding="ascii") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        for band, old, new in zip(BANDS, outdoor, office):
            name, lower, upper = band
            writer.writerow(
                {
                    "band": name,
                    "lower_mhz": lower / 1e6,
                    "upper_mhz": upper / 1e6,
                    "outdoor_minimum_swr": old["minimum_swr"],
                    "outdoor_minimum_frequency_mhz": (
                        float(old["minimum_swr_frequency_hz"]) / 1e6
                    ),
                    "outdoor_coverage_at_or_below_2_percent": old[
                        "coverage_percent"
                    ]["2.0"],  # type: ignore[index]
                    "office_minimum_swr": new["minimum_swr"],
                    "office_minimum_frequency_mhz": (
                        float(new["minimum_swr_frequency_hz"]) / 1e6
                    ),
                    "office_maximum_swr": new["maximum_swr"],
                    "office_median_swr": new["median_swr"],
                    "office_resistance_at_minimum_ohm": new[
                        "resistance_at_minimum_ohm"
                    ],
                    "office_reactance_at_minimum_ohm": new[
                        "reactance_at_minimum_ohm"
                    ],
                    "office_coverage_at_or_below_1_5_percent": new[
                        "coverage_percent"
                    ]["1.5"],  # type: ignore[index]
                    "office_coverage_at_or_below_2_percent": new[
                        "coverage_percent"
                    ]["2.0"],  # type: ignore[index]
                    "office_coverage_at_or_below_3_percent": new[
                        "coverage_percent"
                    ]["3.0"],  # type: ignore[index]
                    "office_longest_range_at_or_below_2": new[
                        "longest_contiguous_range"
                    ]["2.0"],  # type: ignore[index]
                }
            )


def markdown_table(
    outdoor: list[dict[str, object]], office: list[dict[str, object]]
) -> str:
    rows = [
        "| Band | Outdoor best | Office-feed best | Frequency shift | "
        "Office <=2:1 | Office Z at best |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for old, new in zip(outdoor, office):
        shift = (
            int(new["minimum_swr_frequency_hz"])
            - int(old["minimum_swr_frequency_hz"])
        ) / 1e3
        rows.append(
            f"| {new['band']} | {float(old['minimum_swr']):.2f} at "
            f"{int(old['minimum_swr_frequency_hz']) / 1e6:.6f} MHz | "
            f"{float(new['minimum_swr']):.2f} at "
            f"{int(new['minimum_swr_frequency_hz']) / 1e6:.6f} MHz | "
            f"{shift:+.1f} kHz | "
            f"{float(new['coverage_percent']['2.0']):.0f}% | "  # type: ignore[index]
            f"{float(new['resistance_at_minimum_ohm']):.1f} "
            f"{float(new['reactance_at_minimum_ohm']):+.1f}j ohms |"
        )
    return "\n".join(rows)


def write_readme(
    output: Path,
    outdoor: list[dict[str, object]],
    office: list[dict[str, object]],
    repeatability: dict[str, float],
    open_path: dict[str, float],
) -> None:
    content = f"""# GOWENIC EFHW installed office-feed comparison

This report measures the same 62.5 ft GOWENIC-module EFHW in two feed-system
configurations:

1. **August 18 outdoor baseline:** 75 ft LS400 outdoors.
2. **August 23 installed office path:** 75 ft LS400 outdoors, a window
   flat-ribbon transition, then another 25 ft LS400 into an office containing
   substantial computer equipment.

The August 18 parent report previously said 12 ft; that final configuration has
been corrected to **75 ft LS400 outdoors**. Earlier tuning-history runs that
actually used 12 ft remain labeled 12 ft.

## Headline results

- The installed system retains a good full-band 40m match: **SWR
  {float(office[3]['minimum_swr']):.2f} at
  {int(office[3]['minimum_swr_frequency_hz']) / 1e6:.6f} MHz**, with
  {float(office[3]['coverage_percent']['2.0']):.0f}% of sampled 40m points at
  or below 2:1.
- 40m moved **{(int(office[3]['minimum_swr_frequency_hz']) - int(outdoor[3]['minimum_swr_frequency_hz'])) / 1e3:+.1f} kHz**
  relative to the 75 ft outdoor baseline.
- 80m and 20m present much better impedance matches at the office end, but this
  does **not** prove increased radiation efficiency. Added line length,
  transition loss, and transmission-line phase can transform or mask the
  antenna feed-point mismatch.
- 160m and 6m remain poor matches. The sweep starts at 0.5 MHz for diagnostic
  context, but the band table covers US amateur allocations through 6m.
- The two unchanged installed sweeps were repeatable: median complex-S11 delta
  **{repeatability['median_complex_s11_delta']:.5f}** and median SWR delta
  **{repeatability['median_swr_delta']:.4f}**.

## Band comparison

{markdown_table(outdoor, office)}

## Measurement chain

![Installed feed layout](charts/installed_feed_layout.png)

The reference plane is the VNA-side adapter in the office. Therefore this is
an **installed-system input-impedance test**, not a de-embedded transformer or
antenna feed-point measurement.

## Visual results

### Full span

![Full-span comparison](charts/full_span_comparison.png)

### Amateur-band zooms

![Amateur-band SWR comparison](charts/amateur_band_swr_comparison.png)

### Band scorecard

![Band scorecard](charts/band_scorecard.png)

### Repeatability

![Repeatability](charts/repeatability.png)

### Far-end-open feed-path diagnostic

![Far-end-open diagnostic](charts/far_end_open_diagnostic.png)

The open-path test measured median |Gamma|
**{open_path['median_open_magnitude']:.3f}**. Under the simplifying assumption
of an ideal open on a uniform, well-matched line, that corresponds to apparent
one-way attenuation of
**{open_path['apparent_one_way_attenuation_at_7_mhz_db']:.2f} dB at 7 MHz** and
**{open_path['apparent_one_way_attenuation_at_54_mhz_db']:.2f} dB at 54 MHz**.
The window transition and connectors introduce discontinuities and multiple
reflections, so these are plausibility diagnostics, **not measured insertion
loss**. A calibrated two-port measurement is required for actual path loss.

## Calibration and fault detection

- NanoVNA-H firmware 1.2.50; software ideal one-port OSL at CH0/Port 1.
- Sweep: 0.5-54 MHz, 40,001 points, nominal 1.3375 kHz spacing, 1 kHz
  measurement bandwidth.
- The first SHORT capture was accidentally open-like. OPEN-to-SHORT raw
  separation was far below the known-good standard behavior.
- The impossible initial near-1:1 antenna/open-path results were rejected.
- Those rejected captures were overwritten during correction and are not
  presented as source evidence; only the corrected raw standards and sweeps are
  included.
- After replacing only SHORT and recalculating OSL, reconnect verification was
  median SWR 1.00009, p95 1.00030, and maximum 1.00047.
- A valid far-end-open test then showed the expected large reflection before
  the antenna was reconnected.

## Interpretation limits

- SWR and S11 measure the impedance presented to the radio. They do not measure
  gain, radiation efficiency, pattern, receive sensitivity, or transmitted
  field strength.
- A longer lossy line can make SWR look better at the radio while wasting power.
- The window transition and added 25 ft change both attenuation and electrical
  length, so differences cannot be attributed uniquely to office RFI.
- `60m envelope` is the continuous 5.3305-5.4064 MHz analysis envelope, not a
  claim that every frequency inside it is authorized for US transmission; US
  60m operation is channelized.
- Ambient office RFI primarily affects receiver noise and may contaminate a VNA
  trace if strong enough; it does not normally explain stable broadband
  impedance transformation by itself.
- Do not compare the two configurations as controlled antenna-performance or
  gain measurements.

## Data

- `data/band_comparison.csv` and `.json`: per-band results.
- `data/comparison_points.csv`: point-by-point complex and SWR comparison.
- `data/office_average.s1p`: complex average of the two valid installed sweeps.
- `measurements/`: complete calibration, verification, open-path diagnostic,
  and both installed-system source runs.
- `interactive-report.html`: self-contained offline band explorer.

## Regenerate from packaged inputs

From the repository root in an environment with the versions in
`requirements.txt`:

```bash
python3 antenna-results/antennas/gowenic-efhw/installed-office-feed/generate_report.py \\
  --outdoor-source antenna-results/antennas/gowenic-efhw/installed-office-feed/data/outdoor_75ft_baseline.s1p \\
  --office-source antenna-results/antennas/gowenic-efhw/installed-office-feed/data/office_sweep_1.s1p \\
  --office-repeat-source antenna-results/antennas/gowenic-efhw/installed-office-feed/data/office_sweep_2.s1p \\
  --calibration-dir antenna-results/antennas/gowenic-efhw/installed-office-feed/measurements/calibration \\
  --open-path-dir antenna-results/antennas/gowenic-efhw/installed-office-feed/measurements/far-end-open \\
  --office-dir antenna-results/antennas/gowenic-efhw/installed-office-feed/measurements/installed-sweep-1 \\
  --office-repeat-dir antenna-results/antennas/gowenic-efhw/installed-office-feed/measurements/installed-sweep-2
```
"""
    (output / "README.md").write_text(content, encoding="ascii")


def write_html(
    output: Path,
    outdoor_summary: list[dict[str, object]],
    office_summary: list[dict[str, object]],
    interactive: dict[str, dict[str, list[float]]],
) -> None:
    report = json.dumps(
        {
            "outdoor": outdoor_summary,
            "office": office_summary,
            "bands": interactive,
        },
        separators=(",", ":"),
    )
    rows = "\n".join(
        f"<tr><td><strong>{new['band']}</strong></td>"
        f"<td>{float(old['minimum_swr']):.2f}</td>"
        f"<td>{float(new['minimum_swr']):.2f}</td>"
        f"<td>{int(new['minimum_swr_frequency_hz']) / 1e6:.6f}</td>"
        f"<td>{float(new['coverage_percent']['2.0']):.0f}%</td></tr>"  # type: ignore[index]
        for old, new in zip(outdoor_summary, office_summary)
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GOWENIC EFHW office-feed comparison</title>
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
.shell {{ max-width: 1400px; margin: 0 auto; padding: 32px 24px 64px; }}
h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 3.4rem); letter-spacing: -0.04em; }}
h2 {{ margin: 0 0 16px; }}
p {{ color: var(--cp-text-muted); line-height: 1.55; }}
.eyebrow {{ color: var(--cp-accent); font-weight: 700; text-transform: uppercase; letter-spacing: .12em; }}
.cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 28px 0; }}
.card, .panel {{
  background: var(--cp-surface);
  border: 1px solid var(--cp-border);
  border-radius: 16px;
  box-shadow: 0 0 2px var(--cp-border), 0 1px 2px var(--cp-border);
}}
.card {{ padding: 20px; }}
.card strong {{ display: block; font-size: 1.7rem; margin-top: 6px; }}
.label {{ color: var(--cp-text-muted); font-size: .8rem; text-transform: uppercase; letter-spacing: .08em; }}
.panel {{ padding: 20px; margin-top: 16px; }}
.controls {{ display: flex; gap: 12px; margin-bottom: 16px; }}
select {{
  background: var(--cp-surface);
  color: var(--cp-text);
  border: 1px solid var(--cp-border-strong);
  border-radius: 0.625rem;
  padding: 10px 12px;
  font: inherit;
}}
.charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
canvas {{ width: 100%; height: 360px; display: block; }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 11px; border-bottom: 1px solid var(--cp-border); text-align: left; }}
th {{ color: var(--cp-text-muted); }}
.note {{ border-left: 4px solid var(--cp-warning); padding-left: 16px; }}
@media (max-width: 800px) {{
  .cards, .charts {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<main class="shell">
  <div class="eyebrow">Calibrated installed-system measurement</div>
  <h1>GOWENIC EFHW office-feed comparison</h1>
  <p>75 ft LS400 outdoors versus 75 ft LS400 + window ribbon + 25 ft LS400 into the office.</p>
  <section class="cards">
    <div class="card"><span class="label">40m installed best</span><strong>{float(office_summary[3]['minimum_swr']):.2f} SWR</strong><span>{int(office_summary[3]['minimum_swr_frequency_hz']) / 1e6:.6f} MHz</span></div>
    <div class="card"><span class="label">Resolution</span><strong>1.3375 kHz</strong><span>40,001 points, 0.5-54 MHz</span></div>
    <div class="card"><span class="label">Installed path</span><strong>100 ft + ribbon</strong><span>measured at office-side adapter</span></div>
  </section>
  <section class="panel">
    <h2>Explore a band</h2>
    <div class="controls"><label>Band <select id="band"></select></label></div>
    <div class="charts">
      <div><h2>SWR comparison</h2><canvas id="swr"></canvas></div>
      <div><h2>Installed impedance</h2><canvas id="impedance"></canvas></div>
    </div>
  </section>
  <section class="panel">
    <h2>Band scorecard</h2>
    <div class="table-wrap"><table>
      <thead><tr><th>Band</th><th>Outdoor best</th><th>Office best</th><th>Office MHz</th><th>Office <=2:1</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
  </section>
  <section class="panel note">
    <p><strong>Interpret carefully:</strong> better SWR at the radio does not prove better radiation efficiency. The extra cable and window transition transform impedance and add loss. Office RFI is more relevant to receiver noise than to this stable passive S11 result.</p>
  </section>
</main>
<script>
const REPORT = {report};
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const select = document.getElementById("band");
Object.keys(REPORT.bands).forEach(name => {{
  const option = document.createElement("option");
  option.value = name;
  option.textContent = name;
  select.appendChild(option);
}});
function draw(canvas, x, series, yLabel, include) {{
  const ratio = devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.floor(rect.width * ratio);
  canvas.height = Math.floor(rect.height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const width = rect.width, height = rect.height;
  const margin = {{left: 58, right: 18, top: 44, bottom: 42}};
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const all = series.flatMap(item => item.values.filter(Number.isFinite));
  let low = Math.min(...all, include), high = Math.max(...all, include);
  const pad = Math.max((high - low) * .08, .01);
  low -= pad; high += pad;
  const mapX = value => margin.left + (value - x[0]) / (x[x.length - 1] - x[0]) * plotW;
  const mapY = value => margin.top + (high - value) / (high - low) * plotH;
  ctx.fillStyle = css("--cp-surface"); ctx.fillRect(0, 0, width, height);
  ctx.font = '12px "Segoe UI", sans-serif';
  for (let tick = 0; tick <= 5; tick++) {{
    const px = margin.left + plotW * tick / 5;
    const py = margin.top + plotH * tick / 5;
    ctx.strokeStyle = css("--cp-border");
    ctx.beginPath(); ctx.moveTo(px, margin.top); ctx.lineTo(px, margin.top + plotH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(margin.left, py); ctx.lineTo(margin.left + plotW, py); ctx.stroke();
    ctx.fillStyle = css("--cp-text-muted");
    ctx.textAlign = "center";
    ctx.fillText((x[0] + (x[x.length - 1] - x[0]) * tick / 5).toFixed(3), px, height - 18);
    ctx.textAlign = "right";
    ctx.fillText((high - (high - low) * tick / 5).toFixed(1), margin.left - 8, py + 4);
  }}
  series.forEach(item => {{
    ctx.strokeStyle = item.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    item.values.forEach((value, index) => {{
      const px = mapX(x[index]), py = mapY(value);
      if (index) ctx.lineTo(px, py); else ctx.moveTo(px, py);
    }});
    ctx.stroke();
  }});
  let legendX = margin.left;
  let legendY = 16;
  series.forEach(item => {{
    const entryWidth = 30 + ctx.measureText(item.label).width + 24;
    if (legendX + entryWidth > width - margin.right) {{
      legendX = margin.left;
      legendY += 16;
    }}
    ctx.strokeStyle = item.color;
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(legendX, legendY); ctx.lineTo(legendX + 24, legendY); ctx.stroke();
    ctx.fillStyle = css("--cp-text");
    ctx.textAlign = "left";
    ctx.fillText(item.label, legendX + 30, legendY + 4);
    legendX += entryWidth;
  }});
  ctx.fillStyle = css("--cp-text"); ctx.textAlign = "center";
  ctx.fillText("Frequency (MHz)", margin.left + plotW / 2, height - 2);
  ctx.save(); ctx.translate(13, margin.top + plotH / 2); ctx.rotate(-Math.PI / 2);
  ctx.fillText(yLabel, 0, 0); ctx.restore();
}}
function render() {{
  const band = REPORT.bands[select.value];
  draw(document.getElementById("swr"), band.frequency_mhz, [
    {{label: "75 ft outdoor", values: band.outdoor_swr, color: css("--cp-link")}},
    {{label: "100 ft + ribbon", values: band.office_swr, color: css("--cp-accent")}}
  ], "SWR", 1);
  draw(document.getElementById("impedance"), band.frequency_mhz, [
    {{label: "Resistance R", values: band.office_resistance, color: css("--cp-success")}},
    {{label: "Reactance X", values: band.office_reactance, color: css("--cp-accent")}}
  ], "Ohms", 0);
}}
select.addEventListener("change", render);
window.addEventListener("resize", render);
render();
</script>
</body>
</html>
"""
    (output / "interactive-report.html").write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdoor-source", type=Path, required=True)
    parser.add_argument("--office-source", type=Path, required=True)
    parser.add_argument("--office-repeat-source", type=Path, required=True)
    parser.add_argument("--calibration-dir", type=Path, required=True)
    parser.add_argument("--open-path-dir", type=Path, required=True)
    parser.add_argument("--office-dir", type=Path, required=True)
    parser.add_argument("--office-repeat-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()

    final_output = args.output.resolve()
    backup_output = final_output.with_name(f".{final_output.name}.backup")
    if backup_output.exists():
        if final_output.exists():
            shutil.rmtree(backup_output)
        else:
            os.replace(backup_output, final_output)
    final_output.mkdir(parents=True, exist_ok=True)
    staging_handle = tempfile.TemporaryDirectory(
        prefix=".gowenic-office-feed-", dir=final_output.parent
    )
    staging = Path(staging_handle.name)
    inputs = staging / "inputs"
    inputs.mkdir()
    staged_files = {
        "outdoor_source": args.outdoor_source,
        "office_source": args.office_source,
        "office_repeat_source": args.office_repeat_source,
    }
    for name, source in staged_files.items():
        destination = inputs / f"{name}{source.suffix}"
        shutil.copy2(source, destination)
        setattr(args, name, destination)
    staged_directories = {
        "calibration_dir": args.calibration_dir,
        "open_path_dir": args.open_path_dir,
        "office_dir": args.office_dir,
        "office_repeat_dir": args.office_repeat_dir,
    }
    for name, source in staged_directories.items():
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
    charts.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    measurements.mkdir(parents=True, exist_ok=True)

    outdoor_f, outdoor_gamma = load_touchstone(args.outdoor_source)
    office_f, office_gamma = load_touchstone(args.office_source)
    repeat_f, repeat_gamma = load_touchstone(args.office_repeat_source)
    open_f, open_gamma = load_touchstone(args.open_path_dir / "antenna.s1p")
    if not np.array_equal(office_f, repeat_f):
        raise ValueError("office sweep frequencies do not match repeat")
    if not np.array_equal(office_f, open_f):
        raise ValueError("open-path frequencies do not match office sweep")
    average_gamma = (office_gamma + repeat_gamma) / 2.0

    outdoor_summary = analyze_bands(outdoor_f, outdoor_gamma)
    office_summary = analyze_bands(office_f, average_gamma)
    office_metrics = calculate_metrics(average_gamma)
    outdoor_metrics = calculate_metrics(outdoor_gamma)
    set_plot_style()
    plot_overview(charts, outdoor_f, outdoor_metrics, office_f, office_metrics)
    plot_band_comparison(
        charts,
        outdoor_f,
        outdoor_metrics,
        office_f,
        office_metrics,
        outdoor_summary,
        office_summary,
    )
    plot_scorecard(charts, outdoor_summary, office_summary)
    repeatability = plot_repeatability(
        charts, office_f, office_gamma, repeat_gamma
    )
    open_path = plot_open_path_loss(charts, open_f, open_gamma)
    plot_feed_layout(charts)

    write_average_touchstone(data / "office_average.s1p", office_f, average_gamma)
    overlap = (office_f >= outdoor_f[0]) & (office_f <= outdoor_f[-1])
    outdoor_interpolated = interpolate_complex(
        office_f[overlap], outdoor_f, outdoor_gamma
    )
    write_comparison_points(
        data / "comparison_points.csv",
        office_f[overlap],
        office_gamma[overlap],
        repeat_gamma[overlap],
        outdoor_interpolated,
    )
    write_band_csv(
        data / "band_comparison.csv", outdoor_summary, office_summary
    )
    comparison = {
        "outdoor_baseline": outdoor_summary,
        "installed_office_feed": office_summary,
    }
    (data / "band_comparison.json").write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="ascii"
    )
    (data / "repeatability.json").write_text(
        json.dumps(repeatability, indent=2) + "\n", encoding="ascii"
    )
    (data / "far_end_open_diagnostic.json").write_text(
        json.dumps(open_path, indent=2) + "\n", encoding="ascii"
    )
    metadata = {
        "report_generated_at": "2026-08-23T20:49:49.907359-07:00",
        "antenna": {
            "module": "GOWENIC No Tune End Fed Half Antenna, 10 W",
            "physical_radiator_length_ft": 62.5,
            "feed_end_loop_in": 8,
            "far_end_loop_in": 14,
            "counterpoise_in": 96,
            "geometry": "25 ft to 3 ft sloper",
            "common_mode_choke": False,
        },
        "outdoor_baseline": {
            "captured_at": "2026-08-18T00:27:25.447889-07:00",
            "feed_path": "75 ft LS400 outdoors",
            "correction": (
                "Parent report previously recorded 12 ft; user clarified the "
                "final August 18 test used 75 ft LS400 outdoors."
            ),
            "range_hz": [1_800_000, 148_000_000],
            "points": 40_001,
        },
        "installed_office_feed": {
            "captured_at": "2026-08-23T20:46:24.893558-07:00",
            "repeat_captured_at": "2026-08-23T20:49:49.907359-07:00",
            "feed_path": [
                "75 ft LS400 outdoors",
                "window flat-ribbon transition",
                "25 ft LS400 into office",
            ],
            "environment": "office with substantial computer equipment",
            "range_hz": [500_000, 54_000_000],
            "points": 40_001,
            "nominal_step_hz": 1_337.5,
            "measurement_bandwidth_hz": 1_000,
        },
        "calibration": {
            "type": "software one-port ideal OSL",
            "reference_plane": "VNA-side CH0 adapter in office",
            "corrected_at": "2026-08-23T20:32:58.778082-07:00",
            "load_verification": {
                "median_swr": 1.0000858186593053,
                "p95_swr": 1.0003037887481392,
                "maximum_swr": 1.000473539972914,
                "median_resistance_ohm": 50.001752192414045,
                "median_reactance_ohm": -0.002485303753368028,
            },
        },
        "invalid_run_handling": {
            "issue": "Initial SHORT capture was electrically open-like.",
            "action": (
                "Rejected impossible near-1:1 connected and open-path traces, "
                "recaptured SHORT, recalculated OSL, repeated verification, "
                "repeated open-path diagnostic, and captured two final sweeps."
            ),
            "rejected_source_captures_preserved": False,
            "note": (
                "The rejected captures were overwritten during correction, so "
                "the package makes no exact numerical claim from those sources."
            ),
        },
        "interpretation": (
            "Results are installed-system input impedance. Cable loss and "
            "electrical length can improve radio-end SWR without improving "
            "antenna radiation efficiency."
        ),
    }
    (data / "measurement_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="ascii"
    )

    shutil.copy2(args.outdoor_source, data / "outdoor_75ft_baseline.s1p")
    shutil.copy2(args.office_source, data / "office_sweep_1.s1p")
    shutil.copy2(args.office_repeat_source, data / "office_sweep_2.s1p")
    shutil.copytree(
        args.calibration_dir,
        measurements / "calibration",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        args.open_path_dir,
        measurements / "far-end-open",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        args.office_dir,
        measurements / "installed-sweep-1",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        args.office_repeat_dir,
        measurements / "installed-sweep-2",
        dirs_exist_ok=True,
    )

    interactive: dict[str, dict[str, list[float]]] = {}
    for name, lower, upper in BANDS:
        selected = (office_f >= lower) & (office_f <= upper)
        band_f = office_f[selected]
        band_office_gamma = average_gamma[selected]
        band_outdoor_gamma = interpolate_complex(
            band_f, outdoor_f, outdoor_gamma
        )
        office_band_metrics = calculate_metrics(band_office_gamma)
        outdoor_band_metrics = calculate_metrics(band_outdoor_gamma)
        interactive[name] = {
            "frequency_mhz": (band_f / 1e6).round(6).tolist(),
            "outdoor_swr": outdoor_band_metrics["swr"].round(5).tolist(),
            "office_swr": office_band_metrics["swr"].round(5).tolist(),
            "office_resistance": office_band_metrics["resistance_ohm"]
            .round(4)
            .tolist(),
            "office_reactance": office_band_metrics["reactance_ohm"]
            .round(4)
            .tolist(),
        }
    write_readme(output, outdoor_summary, office_summary, repeatability, open_path)
    write_html(output, outdoor_summary, office_summary, interactive)
    normalize_csv_line_endings(output)
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
