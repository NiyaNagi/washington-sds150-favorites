#!/usr/bin/env python3
"""Capture averaged, calibrated scanner-service zooms with a NanoVNA."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import nanovna_swr as n  # noqa: E402


ZOOMS = (
    ("fm-broadcast", 88_000_000, 108_000_000, 20),
    ("civil-air", 118_000_000, 137_000_000, 20),
    ("2m", 144_000_000, 148_000_000, 10),
    ("vhf-lmr", 150_000_000, 174_000_000, 20),
    ("marine-vhf", 156_000_000, 162_000_000, 10),
    ("railroad", 159_810_000, 161_565_000, 10),
    ("noaa-weather", 162_400_000, 162_550_000, 1),
    ("1.25m", 222_000_000, 225_000_000, 10),
    ("military-air", 225_000_000, 400_000_000, 100),
    ("federal-uhf", 406_100_000, 420_000_000, 20),
    ("70cm", 420_000_000, 450_000_000, 30),
    ("uhf-lmr", 450_000_000, 470_000_000, 20),
    ("t-band", 470_000_000, 512_000_000, 40),
    ("700-public-safety-downlink", 769_000_000, 775_000_000, 10),
    ("800-public-safety-downlink", 851_000_000, 869_000_000, 20),
    ("33cm", 902_000_000, 928_000_000, 20),
    ("900-trunking-downlink", 935_000_000, 941_000_000, 10),
    ("uat-978", 976_000_000, 980_000_000, 10),
    ("ads-b-1090", 1_088_000_000, 1_092_000_000, 10),
)


def interpolate_complex(
    target: np.ndarray, source: np.ndarray, values: np.ndarray
) -> np.ndarray:
    return np.interp(target, source, values.real) + 1j * np.interp(
        target, source, values.imag
    )


def capture_once(
    vna: n.NanoVNA, start: int, stop: int, segments: int
) -> tuple[np.ndarray, np.ndarray]:
    frequencies: list[np.ndarray] = []
    samples: list[np.ndarray] = []
    for index in range(segments):
        segment_start = round(start + (stop - start) * index / segments)
        segment_stop = round(start + (stop - start) * (index + 1) / segments)
        segment_frequencies, segment_samples = vna.scan(
            segment_start, segment_stop
        )
        if index:
            segment_frequencies = segment_frequencies[1:]
            segment_samples = segment_samples[1:]
        frequencies.append(segment_frequencies)
        samples.append(segment_samples)
    return np.concatenate(frequencies), np.concatenate(samples)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--averages", type=int, default=3)
    parser.add_argument("--port", default=n.DEFAULT_PORT)
    parser.add_argument(
        "--services",
        nargs="+",
        choices=[item[0] for item in ZOOMS],
        help="Capture only these services; defaults to all.",
    )
    args = parser.parse_args()
    if args.averages < 1:
        parser.error("--averages must be at least 1")

    (
        calibration_frequencies,
        directivity,
        source_match,
        tracking,
        calibration_metadata,
    ) = n.load_calibration(args.calibration)
    args.output.mkdir(parents=True, exist_ok=True)
    vna = n.NanoVNA(args.port)
    summaries: list[dict[str, object]] = []

    try:
        device = vna.info()
        with vna.raw_measurements():
            selected_zooms = (
                [item for item in ZOOMS if item[0] in args.services]
                if args.services
                else list(ZOOMS)
            )
            for name, start, stop, segments in selected_zooms:
                passes = []
                frequencies = None
                for average in range(args.averages):
                    pass_frequencies, samples = capture_once(
                        vna, start, stop, segments
                    )
                    if frequencies is None:
                        frequencies = pass_frequencies
                    elif not np.array_equal(frequencies, pass_frequencies):
                        raise IOError(
                            f"{name}: frequencies changed between averages"
                        )
                    passes.append(samples)
                    print(
                        f"{name}: average {average + 1}/{args.averages}",
                        flush=True,
                    )

                assert frequencies is not None
                measured = np.mean(np.stack(passes), axis=0)
                gamma = n.apply_calibration(
                    measured,
                    interpolate_complex(
                        frequencies, calibration_frequencies, directivity
                    ),
                    interpolate_complex(
                        frequencies, calibration_frequencies, source_match
                    ),
                    interpolate_complex(
                        frequencies, calibration_frequencies, tracking
                    ),
                )
                metrics = n.calculate_metrics(gamma)
                finite = np.flatnonzero(np.isfinite(metrics["swr"]))
                best = finite[np.argmin(metrics["swr"][finite])]
                summary = {
                    "service": name,
                    "start_hz": start,
                    "stop_hz": stop,
                    "points": int(len(frequencies)),
                    "frequency_step_hz": float(
                        np.median(np.diff(frequencies))
                    ),
                    "averages": args.averages,
                    "minimum_swr": float(metrics["swr"][best]),
                    "minimum_swr_frequency_hz": int(frequencies[best]),
                    "median_swr": float(np.nanmedian(metrics["swr"])),
                    "maximum_swr": float(np.nanmax(metrics["swr"])),
                    "coverage_at_or_below_2_percent": float(
                        100 * np.mean(metrics["swr"] <= 2)
                    ),
                    "coverage_at_or_below_3_percent": float(
                        100 * np.mean(metrics["swr"] <= 3)
                    ),
                    "resistance_at_minimum_ohm": float(
                        metrics["resistance_ohm"][best]
                    ),
                    "reactance_at_minimum_ohm": float(
                        metrics["reactance_ohm"][best]
                    ),
                }
                summaries.append(summary)

                with (args.output / f"{name}.csv").open(
                    "w", newline="", encoding="ascii"
                ) as destination:
                    writer = csv.writer(destination)
                    writer.writerow(
                        (
                            "frequency_hz",
                            "s11_real",
                            "s11_imag",
                            "swr",
                            "return_loss_db",
                            "resistance_ohm",
                            "reactance_ohm",
                        )
                    )
                    writer.writerows(
                        zip(
                            frequencies,
                            gamma.real,
                            gamma.imag,
                            metrics["swr"],
                            metrics["return_loss_db"],
                            metrics["resistance_ohm"],
                            metrics["reactance_ohm"],
                        )
                    )
                with (args.output / f"{name}.s1p").open(
                    "w", encoding="ascii"
                ) as destination:
                    destination.write(
                        "! Calibrated averaged scanner-service zoom\n"
                    )
                    destination.write("# Hz S RI R 50\n")
                    for frequency, sample in zip(frequencies, gamma):
                        destination.write(
                            f"{frequency:d} {sample.real:.12g} "
                            f"{sample.imag:.12g}\n"
                        )
    finally:
        vna.close()

    report = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "calibration_file": str(args.calibration),
        "calibration": calibration_metadata,
        "device": device,
        "results": summaries,
    }
    (args.output / "summary.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="ascii"
    )
    print(json.dumps(summaries, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
