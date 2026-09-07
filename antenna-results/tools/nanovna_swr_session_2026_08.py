#!/usr/bin/env python3
"""High-resolution one-port NanoVNA calibration and SWR capture."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

import matplotlib
import numpy as np
import serial

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


DEFAULT_PORT = "/dev/cu.usbmodem4001"
DEFAULT_START = 1_800_000
DEFAULT_STOP = 148_000_000
DEFAULT_SEGMENTS = 400
POINTS_PER_SEGMENT = 101
REFERENCE_OHMS = 50.0

AMATEUR_BANDS = (
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


class NanoVNA:
    def __init__(self, port: str) -> None:
        self.serial = serial.Serial(port, 115200, timeout=0.25)
        time.sleep(0.25)
        self.serial.reset_input_buffer()

    def close(self) -> None:
        self.serial.close()

    def command(self, command: str, timeout: float = 30.0) -> list[str]:
        self.serial.reset_input_buffer()
        self.serial.write(f"{command}\r".encode("ascii"))
        deadline = time.monotonic() + timeout
        lines: list[str] = []
        while time.monotonic() < deadline:
            line = self.serial.readline().decode("ascii", "replace").strip()
            if not line:
                continue
            if line == command:
                continue
            if line.startswith("ch>"):
                return lines
            lines.append(line)
        raise TimeoutError(f"NanoVNA command timed out: {command}")

    def info(self) -> dict[str, str]:
        return {
            "version": " ".join(self.command("version")),
            "info": "\n".join(self.command("info")),
            "calibration": " ".join(self.command("cal")),
            "bandwidth": " ".join(self.command("bandwidth")),
        }

    @contextmanager
    def raw_measurements(self) -> Iterator[None]:
        self.command("cal off")
        try:
            yield
        finally:
            self.command("cal on")

    def scan(self, start: int, stop: int) -> tuple[np.ndarray, np.ndarray]:
        lines = self.command(
            f"scan {start} {stop} {POINTS_PER_SEGMENT} 0b011",
            timeout=45.0,
        )
        if len(lines) != POINTS_PER_SEGMENT:
            raise IOError(
                f"expected {POINTS_PER_SEGMENT} points, received {len(lines)}"
            )
        values = np.asarray(
            [[float(item) for item in line.split()] for line in lines],
            dtype=np.float64,
        )
        if values.shape != (POINTS_PER_SEGMENT, 3):
            raise IOError(f"unexpected scan response shape: {values.shape}")
        return values[:, 0].astype(np.int64), values[:, 1] + 1j * values[:, 2]


def frequency_step(start: int, stop: int, segments: int) -> float:
    return (stop - start) / (segments * (POINTS_PER_SEGMENT - 1))


def capture(
    vna: NanoVNA,
    start: int,
    stop: int,
    segments: int,
) -> tuple[np.ndarray, np.ndarray]:
    frequencies: list[np.ndarray] = []
    samples: list[np.ndarray] = []
    started = time.monotonic()

    with vna.raw_measurements():
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

            completed = index + 1
            if completed == 1 or completed % 10 == 0 or completed == segments:
                elapsed = time.monotonic() - started
                remaining = elapsed / completed * (segments - completed)
                print(
                    f"{completed}/{segments} segments "
                    f"({remaining / 60:.1f} min remaining)",
                    file=sys.stderr,
                    flush=True,
                )

    all_frequencies = np.concatenate(frequencies)
    all_samples = np.concatenate(samples)
    expected_points = segments * (POINTS_PER_SEGMENT - 1) + 1
    if len(all_frequencies) != expected_points:
        raise IOError(f"expected {expected_points} points, got {len(all_frequencies)}")
    if np.any(np.diff(all_frequencies) <= 0):
        raise IOError("NanoVNA returned non-increasing frequencies")
    return all_frequencies, all_samples


def save_capture(
    path: Path,
    label: str,
    frequencies: np.ndarray,
    samples: np.ndarray,
    metadata: dict[str, object],
) -> None:
    np.savez_compressed(
        path,
        label=label,
        frequencies_hz=frequencies,
        s11_raw=samples,
        metadata=json.dumps(metadata),
    )
    csv_path = path.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="ascii") as output:
        writer = csv.writer(output)
        writer.writerow(("frequency_hz", "s11_raw_real", "s11_raw_imag"))
        writer.writerows(zip(frequencies, samples.real, samples.imag))


def load_capture(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    with np.load(path, allow_pickle=False) as data:
        frequencies = data["frequencies_hz"]
        samples = data["s11_raw"]
        metadata = json.loads(str(data["metadata"]))
    return frequencies, samples, metadata


def calculate_error_terms(
    open_sample: np.ndarray,
    short_sample: np.ndarray,
    load_sample: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    directivity = load_sample
    open_delta = open_sample - directivity
    short_delta = short_sample - directivity
    denominator = open_delta - short_delta
    if np.any(np.abs(denominator) < 1e-12):
        raise ValueError("calibration standards produced a singular solution")
    source_match = (open_delta + short_delta) / denominator
    reflection_tracking = open_delta * (1.0 - source_match)
    if np.any(np.abs(reflection_tracking) < 1e-12):
        raise ValueError("calibration reflection tracking is too small")
    return directivity, source_match, reflection_tracking


def apply_calibration(
    measured: np.ndarray,
    directivity: np.ndarray,
    source_match: np.ndarray,
    reflection_tracking: np.ndarray,
) -> np.ndarray:
    delta = measured - directivity
    denominator = reflection_tracking + source_match * delta
    result = np.full(measured.shape, np.nan + 1j * np.nan, dtype=np.complex128)
    np.divide(delta, denominator, out=result, where=np.abs(denominator) > 1e-15)
    return result


def ensure_matching_frequencies(
    reference: np.ndarray,
    candidate: np.ndarray,
    label: str,
) -> None:
    if not np.array_equal(reference, candidate):
        raise ValueError(f"{label} frequencies do not match the open capture")


def save_calibration(
    output: Path,
    frequencies: np.ndarray,
    directivity: np.ndarray,
    source_match: np.ndarray,
    reflection_tracking: np.ndarray,
    metadata: dict[str, object],
) -> None:
    np.savez_compressed(
        output,
        frequencies_hz=frequencies,
        directivity=directivity,
        source_match=source_match,
        reflection_tracking=reflection_tracking,
        metadata=json.dumps(metadata),
    )


def load_calibration(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    with np.load(path, allow_pickle=False) as data:
        return (
            data["frequencies_hz"],
            data["directivity"],
            data["source_match"],
            data["reflection_tracking"],
            json.loads(str(data["metadata"])),
        )


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


def band_summary(
    frequencies: np.ndarray, metrics: dict[str, np.ndarray]
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    swr = metrics["swr"]
    for name, start, stop in AMATEUR_BANDS:
        indexes = np.flatnonzero(
            (frequencies >= start) & (frequencies <= stop) & np.isfinite(swr)
        )
        if indexes.size == 0:
            continue
        best_index = indexes[np.argmin(swr[indexes])]
        result.append(
            {
                "band": name,
                "start_hz": start,
                "stop_hz": stop,
                "minimum_swr": float(swr[best_index]),
                "minimum_swr_frequency_hz": int(frequencies[best_index]),
            }
        )
    return result


def save_measurement(
    output_dir: Path,
    frequencies: np.ndarray,
    gamma: np.ndarray,
    metadata: dict[str, object],
) -> None:
    metrics = calculate_metrics(gamma)

    with (output_dir / "antenna_swr.csv").open(
        "w", newline="", encoding="ascii"
    ) as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "frequency_hz",
                "frequency_mhz",
                "s11_real",
                "s11_imag",
                "s11_magnitude",
                "phase_deg",
                "swr",
                "return_loss_db",
                "resistance_ohm",
                "reactance_ohm",
            )
        )
        writer.writerows(
            zip(
                frequencies,
                frequencies / 1e6,
                gamma.real,
                gamma.imag,
                metrics["magnitude"],
                metrics["phase_deg"],
                metrics["swr"],
                metrics["return_loss_db"],
                metrics["resistance_ohm"],
                metrics["reactance_ohm"],
            )
        )

    with (output_dir / "antenna.s1p").open("w", encoding="ascii") as output:
        output.write("! Calibrated high-resolution NanoVNA antenna measurement\n")
        output.write("# Hz S RI R 50\n")
        for frequency, sample in zip(frequencies, gamma):
            output.write(f"{frequency:d} {sample.real:.12g} {sample.imag:.12g}\n")

    finite_indexes = np.flatnonzero(np.isfinite(metrics["swr"]))
    if finite_indexes.size:
        best_index = finite_indexes[np.argmin(metrics["swr"][finite_indexes])]
        minimum_swr = float(metrics["swr"][best_index])
        minimum_frequency = int(frequencies[best_index])
    else:
        minimum_swr = None
        minimum_frequency = None
    summary = {
        **metadata,
        "points": int(len(frequencies)),
        "frequency_step_hz": float(np.median(np.diff(frequencies))),
        "minimum_swr": minimum_swr,
        "minimum_swr_frequency_hz": minimum_frequency,
        "bands": band_summary(frequencies, metrics),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="ascii"
    )
    plot_results(output_dir, frequencies, metrics["swr"])


def plot_results(output_dir: Path, frequencies: np.ndarray, swr: np.ndarray) -> None:
    plot_swr = np.minimum(swr, 10.0)
    fig, axis = plt.subplots(figsize=(14, 6))
    axis.plot(frequencies / 1e6, plot_swr, linewidth=0.65)
    axis.set(
        title="Antenna SWR, 160 m through 2 m",
        xlabel="Frequency (MHz)",
        ylabel="SWR (values above 10 clipped)",
        ylim=(1, 10),
    )
    axis.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "swr_full_span.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(4, 3, figsize=(15, 13), constrained_layout=True)
    for axis, (name, start, stop) in zip(axes.flat, AMATEUR_BANDS):
        selected = (frequencies >= start) & (frequencies <= stop)
        axis.plot(frequencies[selected] / 1e6, plot_swr[selected], linewidth=0.8)
        axis.set_title(name)
        axis.set_ylim(1, 10)
        axis.grid(True, alpha=0.3)
        axis.set_xlabel("MHz")
        axis.set_ylabel("SWR")
    fig.suptitle("Antenna SWR by US amateur band (values above 10 clipped)")
    fig.savefig(output_dir / "swr_amateur_bands.png", dpi=180)
    plt.close(fig)


def capture_command(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{args.label}.npz"
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"{output} already exists; use --overwrite to replace it")

    vna = NanoVNA(args.port)
    try:
        device = vna.info()
        frequencies, samples = capture(vna, args.start, args.stop, args.segments)
    finally:
        vna.close()

    metadata: dict[str, object] = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "label": args.label,
        "port": args.port,
        "start_hz": args.start,
        "stop_hz": args.stop,
        "segments": args.segments,
        "points": int(len(frequencies)),
        "nominal_frequency_step_hz": frequency_step(
            args.start, args.stop, args.segments
        ),
        "device": device,
    }
    save_capture(output, args.label, frequencies, samples, metadata)
    print(output)


def calibrate_command(args: argparse.Namespace) -> None:
    calibration_dir = Path(args.calibration_dir)
    open_frequencies, open_sample, open_metadata = load_capture(
        calibration_dir / "open.npz"
    )
    short_frequencies, short_sample, _ = load_capture(calibration_dir / "short.npz")
    load_frequencies, load_sample, _ = load_capture(calibration_dir / "load.npz")
    ensure_matching_frequencies(open_frequencies, short_frequencies, "short")
    ensure_matching_frequencies(open_frequencies, load_frequencies, "load")
    directivity, source_match, reflection_tracking = calculate_error_terms(
        open_sample, short_sample, load_sample
    )
    output = calibration_dir / "calibration.npz"
    metadata = {
        "created_at": datetime.now().astimezone().isoformat(),
        "reference_plane": "antenna side of attached adapter",
        "standards": "ideal open, short, and 50-ohm load",
        "source_capture": open_metadata,
    }
    save_calibration(
        output,
        open_frequencies,
        directivity,
        source_match,
        reflection_tracking,
        metadata,
    )
    print(output)


def measure_command(args: argparse.Namespace) -> None:
    calibration_path = Path(args.calibration)
    (
        calibration_frequencies,
        directivity,
        source_match,
        reflection_tracking,
        calibration_metadata,
    ) = load_calibration(calibration_path)
    source = calibration_metadata["source_capture"]
    assert isinstance(source, dict)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_output = output_dir / "antenna_raw.npz"
    if raw_output.exists() and not args.overwrite:
        raise FileExistsError(
            f"{raw_output} already exists; use --overwrite to replace it"
        )

    vna = NanoVNA(args.port)
    try:
        device = vna.info()
        frequencies, measured = capture(
            vna,
            int(source["start_hz"]),
            int(source["stop_hz"]),
            int(source["segments"]),
        )
    finally:
        vna.close()

    ensure_matching_frequencies(calibration_frequencies, frequencies, "antenna")
    raw_metadata = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "label": "antenna_raw",
        "port": args.port,
        "start_hz": int(source["start_hz"]),
        "stop_hz": int(source["stop_hz"]),
        "segments": int(source["segments"]),
        "points": int(len(frequencies)),
        "device": device,
    }
    save_capture(raw_output, "antenna_raw", frequencies, measured, raw_metadata)
    gamma = apply_calibration(
        measured, directivity, source_match, reflection_tracking
    )
    save_measurement(
        output_dir,
        frequencies,
        gamma,
        {
            "captured_at": raw_metadata["captured_at"],
            "range_hz": [int(frequencies[0]), int(frequencies[-1])],
            "calibration_file": str(calibration_path.resolve()),
            "calibration": calibration_metadata,
            "device": device,
        },
    )
    print(output_dir)


def status_command(args: argparse.Namespace) -> None:
    vna = NanoVNA(args.port)
    try:
        print(json.dumps(vna.info(), indent=2))
    finally:
        vna.close()


def self_test_command(_: argparse.Namespace) -> None:
    rng = np.random.default_rng(42)
    count = 1000
    directivity = 0.03 + 0.02j + rng.normal(0, 0.001, count)
    source_match = -0.08 + 0.04j + rng.normal(0, 0.001, count)
    tracking = 0.75 - 0.12j + rng.normal(0, 0.001, count)

    def measure(gamma: np.ndarray) -> np.ndarray:
        return directivity + tracking * gamma / (1.0 - source_match * gamma)

    open_sample = measure(np.ones(count, dtype=np.complex128))
    short_sample = measure(-np.ones(count, dtype=np.complex128))
    load_sample = measure(np.zeros(count, dtype=np.complex128))
    expected = 0.2 * np.exp(1j * np.linspace(-math.pi, math.pi, count))
    measured = measure(expected)
    solved = calculate_error_terms(open_sample, short_sample, load_sample)
    corrected = apply_calibration(measured, *solved)
    error = float(np.max(np.abs(corrected - expected)))
    if error > 1e-12:
        raise AssertionError(f"calibration self-test failed: maximum error {error}")
    print(f"calibration self-test passed; maximum complex error {error:.3g}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--port", default=DEFAULT_PORT)
    status_parser.set_defaults(function=status_command)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("label", choices=("open", "short", "load"))
    capture_parser.add_argument("--port", default=DEFAULT_PORT)
    capture_parser.add_argument("--start", type=int, default=DEFAULT_START)
    capture_parser.add_argument("--stop", type=int, default=DEFAULT_STOP)
    capture_parser.add_argument("--segments", type=int, default=DEFAULT_SEGMENTS)
    capture_parser.add_argument("--output-dir", required=True)
    capture_parser.add_argument("--overwrite", action="store_true")
    capture_parser.set_defaults(function=capture_command)

    calibrate_parser = subparsers.add_parser("calibrate")
    calibrate_parser.add_argument("--calibration-dir", required=True)
    calibrate_parser.set_defaults(function=calibrate_command)

    measure_parser = subparsers.add_parser("measure")
    measure_parser.add_argument("--port", default=DEFAULT_PORT)
    measure_parser.add_argument("--calibration", required=True)
    measure_parser.add_argument("--output-dir", required=True)
    measure_parser.add_argument("--overwrite", action="store_true")
    measure_parser.set_defaults(function=measure_command)

    self_test_parser = subparsers.add_parser("self-test")
    self_test_parser.set_defaults(function=self_test_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.function(args)
    except (OSError, TimeoutError, ValueError, serial.SerialException) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
