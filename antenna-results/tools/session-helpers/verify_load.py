#!/usr/bin/env python3
"""Verify the NanoVNA calibration using a reconnected 50-ohm load."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import nanovna_swr as n  # noqa: E402


CALIBRATION = Path(
    "nanovna_measurements/2026-08-16_1232_calibration/calibration.npz"
)
OUTPUT = Path("nanovna_measurements/2026-08-16_1300_load_verification.json")
AVERAGES = 10
BANDS = (
    ("160m", 1_750_000, 2_050_000),
    ("60m", 5_250_000, 5_500_000),
)


def interpolate_complex(
    target: np.ndarray, source: np.ndarray, values: np.ndarray
) -> np.ndarray:
    return np.interp(target, source, values.real) + 1j * np.interp(
        target, source, values.imag
    )


def main() -> None:
    cal_f, directivity, source_match, tracking, metadata = n.load_calibration(
        CALIBRATION
    )
    device = n.NanoVNA(n.DEFAULT_PORT)
    results: list[dict[str, object]] = []
    try:
        with device.raw_measurements():
            for name, start, stop in BANDS:
                captures = []
                frequencies = None
                for run in range(AVERAGES):
                    run_frequencies, samples = device.scan(start, stop)
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
                metrics = n.calculate_metrics(corrected)
                results.append(
                    {
                        "band": name,
                        "start_hz": start,
                        "stop_hz": stop,
                        "median_swr": float(np.nanmedian(metrics["swr"])),
                        "maximum_swr": float(np.nanmax(metrics["swr"])),
                        "median_resistance_ohm": float(
                            np.nanmedian(metrics["resistance_ohm"])
                        ),
                        "maximum_abs_reactance_ohm": float(
                            np.nanmax(np.abs(metrics["reactance_ohm"]))
                        ),
                    }
                )
    finally:
        device.close()

    report = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "standard": "reconnected 50-ohm load",
        "averages": AVERAGES,
        "calibration_file": str(CALIBRATION.resolve()),
        "calibration": metadata,
        "results": results,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
