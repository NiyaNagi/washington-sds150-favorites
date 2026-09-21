#!/usr/bin/env python3
"""Hardened capture of averaged, calibrated scanner-service zooms.

The service table, segment counts, complex-average math, calibration-term
interpolation, summary schema, CSV columns, and Touchstone formatting are
byte-equivalent to the archived August 2026 helper
(``session-helpers/capture_scanner_zooms.py``), so zooms captured here are
directly comparable to the preserved survey data.

What this entry point adds, matching ``nanovna_swr.py``:

- it imports the hardened acquisition wrapper, so every segment scan is
  validated for point count, shape, finiteness, and integer-Hz frequencies;
- it rejects nonfinite raw or calibrated values, and passive results with
  ``|Gamma| >= 1``, before anything is written;
- it stages the whole run in a temporary directory and publishes it with one
  atomic directory swap plus a recoverable rollback backup, so a failure
  leaves any prior zoom set intact;
- a run that fails a gate is preserved only under an explicit
  ``.rejected-TIMESTAMP`` sibling.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
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

ZOOM_BY_NAME = {item[0]: item for item in ZOOMS}


def interpolate_complex(
    target: np.ndarray, source: np.ndarray, values: np.ndarray
) -> np.ndarray:
    return np.interp(target, source, values.real) + 1j * np.interp(
        target, source, values.imag
    )


def capture_once(
    vna: "n.NanoVNA", start: int, stop: int, segments: int
) -> tuple[np.ndarray, np.ndarray]:
    frequencies: list[np.ndarray] = []
    samples: list[np.ndarray] = []
    for index in range(segments):
        segment_start = round(start + (stop - start) * index / segments)
        segment_stop = round(start + (stop - start) * (index + 1) / segments)
        segment_frequencies, segment_samples = vna.scan(segment_start, segment_stop)
        if index:
            segment_frequencies = segment_frequencies[1:]
            segment_samples = segment_samples[1:]
        frequencies.append(segment_frequencies)
        samples.append(segment_samples)
    return np.concatenate(frequencies), np.concatenate(samples)


def require_within_calibration(
    name: str, frequencies: np.ndarray, calibration_frequencies: np.ndarray
) -> None:
    if frequencies[0] < calibration_frequencies[0] or (
        frequencies[-1] > calibration_frequencies[-1]
    ):
        raise ValueError(
            f"{name}: {frequencies[0]}-{frequencies[-1]} Hz falls outside the "
            f"calibrated span {calibration_frequencies[0]}-"
            f"{calibration_frequencies[-1]} Hz"
        )


def write_zoom(
    output: Path,
    name: str,
    frequencies: np.ndarray,
    gamma: np.ndarray,
    metrics: dict[str, np.ndarray],
) -> None:
    with (output / f"{name}.csv").open("w", newline="", encoding="ascii") as destination:
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
    with (output / f"{name}.s1p").open("w", encoding="ascii") as destination:
        destination.write("! Calibrated averaged scanner-service zoom\n")
        destination.write("# Hz S RI R 50\n")
        for frequency, sample in zip(frequencies, gamma):
            destination.write(f"{frequency:d} {sample.real:.12g} {sample.imag:.12g}\n")


def capture_zooms(
    vna: "n.NanoVNA",
    staging: Path,
    selected: list[tuple[str, int, int, int]],
    averages: int,
    calibration_frequencies: np.ndarray,
    directivity: np.ndarray,
    source_match: np.ndarray,
    tracking: np.ndarray,
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    with vna.raw_measurements():
        for name, start, stop, segments in selected:
            passes = []
            frequencies = None
            for average in range(averages):
                pass_frequencies, samples = capture_once(vna, start, stop, segments)
                if frequencies is None:
                    frequencies = pass_frequencies
                elif not np.array_equal(frequencies, pass_frequencies):
                    raise IOError(f"{name}: frequencies changed between averages")
                n.require_finite(f"{name} raw S11 pass {average + 1}", samples)
                passes.append(samples)
                print(f"{name}: average {average + 1}/{averages}", flush=True)

            assert frequencies is not None
            require_within_calibration(name, frequencies, calibration_frequencies)
            measured = np.mean(np.stack(passes), axis=0)
            gamma = n.apply_calibration(
                measured,
                interpolate_complex(frequencies, calibration_frequencies, directivity),
                interpolate_complex(frequencies, calibration_frequencies, source_match),
                interpolate_complex(frequencies, calibration_frequencies, tracking),
            )
            n.require_finite(f"{name} calibrated S11", gamma)
            maximum_gamma = float(np.max(np.abs(gamma)))
            if maximum_gamma >= 1.0:
                raise ValueError(
                    f"{name}: calibrated passive zoom has nonphysical "
                    f"|Gamma| {maximum_gamma}"
                )

            metrics = n.calculate_metrics(gamma)
            finite = np.flatnonzero(np.isfinite(metrics["swr"]))
            if not finite.size:
                raise ValueError(f"{name}: no finite SWR samples")
            best = finite[np.argmin(metrics["swr"][finite])]
            summaries.append(
                {
                    "service": name,
                    "start_hz": start,
                    "stop_hz": stop,
                    "points": int(len(frequencies)),
                    "frequency_step_hz": float(np.median(np.diff(frequencies))),
                    "averages": averages,
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
                    "resistance_at_minimum_ohm": float(metrics["resistance_ohm"][best]),
                    "reactance_at_minimum_ohm": float(metrics["reactance_ohm"][best]),
                }
            )
            write_zoom(staging, name, frequencies, gamma, metrics)
    return summaries


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
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.averages < 1:
        parser.error("--averages must be at least 1")

    output_dir = args.output
    if output_dir.is_symlink():
        raise ValueError(f"refusing symlinked zoom output directory {output_dir}")
    if output_dir.exists() and any(output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(f"{output_dir} is not empty; use --overwrite to replace it")

    (
        calibration_frequencies,
        directivity,
        source_match,
        tracking,
        calibration_metadata,
    ) = n.load_calibration(args.calibration)

    selected = (
        [ZOOM_BY_NAME[name] for name in args.services] if args.services else list(ZOOMS)
    )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}.", dir=output_dir.parent
    )
    staging = Path(temporary.name) / "zooms"
    staging.mkdir()
    try:
        vna = n.NanoVNA(args.port)
        try:
            device = vna.info()
            summaries = capture_zooms(
                vna,
                staging,
                selected,
                args.averages,
                calibration_frequencies,
                directivity,
                source_match,
                tracking,
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
        (staging / "summary.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="ascii"
        )
        n.publish_run(staging, output_dir)
    except BaseException:
        if staging.exists() and any(staging.iterdir()):
            import shutil

            shutil.move(str(staging), str(n.rejected_path(output_dir)))
        raise
    finally:
        temporary.cleanup()

    print(json.dumps(summaries, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
