#!/usr/bin/env python3
"""Repeat selected NanoVNA bands with complex averaging and marked minima."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import nanovna_swr as n  # noqa: E402


CALIBRATION = Path(
    "nanovna_measurements/2026-08-16_1232_calibration/calibration.npz"
)
OUTPUT = Path("nanovna_measurements/2026-08-16_1256_band_retest")
AVERAGES = 10
BANDS = (
    ("160m", 1_750_000, 2_050_000, 1_800_000, 2_000_000),
    ("60m", 5_250_000, 5_500_000, 5_330_500, 5_406_400),
)


def interpolate_complex(
    target: np.ndarray, source: np.ndarray, values: np.ndarray
) -> np.ndarray:
    return np.interp(target, source, values.real) + 1j * np.interp(
        target, source, values.imag
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cal_f, directivity, source_match, tracking, cal_metadata = n.load_calibration(
        CALIBRATION
    )
    device = n.NanoVNA(n.DEFAULT_PORT)
    results: list[dict[str, object]] = []
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), constrained_layout=True)

    try:
        with device.raw_measurements():
            for axis, (name, scan_start, scan_stop, band_start, band_stop) in zip(
                axes, BANDS
            ):
                captures = []
                frequencies = None
                for run in range(AVERAGES):
                    run_frequencies, samples = device.scan(scan_start, scan_stop)
                    if frequencies is None:
                        frequencies = run_frequencies
                    elif not np.array_equal(frequencies, run_frequencies):
                        raise IOError(f"{name} frequencies changed between captures")
                    captures.append(samples)
                    print(f"{name}: completed average {run + 1}/{AVERAGES}")

                assert frequencies is not None
                measured = np.mean(np.stack(captures), axis=0)
                corrected = n.apply_calibration(
                    measured,
                    interpolate_complex(frequencies, cal_f, directivity),
                    interpolate_complex(frequencies, cal_f, source_match),
                    interpolate_complex(frequencies, cal_f, tracking),
                )
                swr = n.calculate_metrics(corrected)["swr"]
                in_band = (
                    (frequencies >= band_start)
                    & (frequencies <= band_stop)
                    & np.isfinite(swr)
                )
                indexes = np.flatnonzero(in_band)
                best = indexes[np.argmin(swr[indexes])]
                record = {
                    "band": name,
                    "scan_start_hz": scan_start,
                    "scan_stop_hz": scan_stop,
                    "amateur_band_start_hz": band_start,
                    "amateur_band_stop_hz": band_stop,
                    "averages": AVERAGES,
                    "points": int(len(frequencies)),
                    "frequency_step_hz": float(np.median(np.diff(frequencies))),
                    "minimum_swr": float(swr[best]),
                    "minimum_swr_frequency_hz": int(frequencies[best]),
                    "band_edge_swr": {
                        "lower": float(swr[indexes[0]]),
                        "upper": float(swr[indexes[-1]]),
                    },
                }
                results.append(record)

                with (OUTPUT / f"{name}_retest.csv").open(
                    "w", newline="", encoding="ascii"
                ) as output:
                    writer = csv.writer(output)
                    writer.writerow(("frequency_hz", "frequency_mhz", "swr"))
                    writer.writerows(zip(frequencies, frequencies / 1e6, swr))

                axis.plot(frequencies / 1e6, swr, linewidth=1.25)
                axis.axvspan(
                    band_start / 1e6,
                    band_stop / 1e6,
                    color="#2ca02c",
                    alpha=0.08,
                    label=f"{name} amateur band",
                )
                axis.scatter(
                    frequencies[best] / 1e6,
                    swr[best],
                    color="#d62728",
                    zorder=3,
                )
                axis.annotate(
                    f"minimum in band\n{frequencies[best] / 1e6:.6f} MHz\n"
                    f"SWR {swr[best]:.2f}",
                    xy=(frequencies[best] / 1e6, swr[best]),
                    xytext=(12, -12),
                    textcoords="offset points",
                    va="top",
                    arrowprops={"arrowstyle": "->"},
                )
                axis.set_title(f"{name} retest - {AVERAGES}-sweep complex average")
                axis.set_xlabel("Frequency (MHz)")
                axis.set_ylabel("SWR")
                axis.grid(True, alpha=0.3)
                axis.legend()
    finally:
        device.close()

    metadata = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "calibration_file": str(CALIBRATION.resolve()),
        "calibration": cal_metadata,
        "results": results,
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="ascii"
    )
    fig.suptitle("Focused NanoVNA antenna retest")
    fig.savefig(OUTPUT / "160m_60m_retest.png", dpi=200)
    print(OUTPUT)


if __name__ == "__main__":
    main()
