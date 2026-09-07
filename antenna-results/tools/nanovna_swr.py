#!/usr/bin/env python3
"""Hardened entry point for the August 2026 NanoVNA capture engine."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

import nanovna_swr_session_2026_08 as engine
from nanovna_swr_session_2026_08 import *  # noqa: F401,F403

MAX_SEGMENTS = 10_000
BACKUP_MARKER = ".nanovna-run-backup.json"


def require_finite(label: str, values: np.ndarray) -> None:
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{label} contains nonfinite values")


def validate_sweep(start: int, stop: int, segments: int) -> None:
    if start < 0:
        raise ValueError("sweep start must be nonnegative")
    if stop <= start:
        raise ValueError("sweep stop must be greater than start")
    if segments < 1 or segments > MAX_SEGMENTS:
        raise ValueError(f"segments must be between 1 and {MAX_SEGMENTS}")
    intervals = segments * (engine.POINTS_PER_SEGMENT - 1)
    if stop - start < intervals:
        raise ValueError(
            "sweep span is too small for a strictly increasing integer-Hz grid"
        )


def hardened_scan(
    self: engine.NanoVNA, start: int, stop: int
) -> tuple[np.ndarray, np.ndarray]:
    validate_sweep(start, stop, 1)
    lines = self.command(
        f"scan {start} {stop} {engine.POINTS_PER_SEGMENT} 0b011",
        timeout=45.0,
    )
    if len(lines) != engine.POINTS_PER_SEGMENT:
        raise IOError(
            f"expected {engine.POINTS_PER_SEGMENT} points, received {len(lines)}"
        )
    values = np.asarray(
        [[float(item) for item in line.split()] for line in lines],
        dtype=np.float64,
    )
    if values.shape != (engine.POINTS_PER_SEGMENT, 3):
        raise IOError(f"unexpected scan response shape: {values.shape}")
    require_finite("NanoVNA scan response", values)
    frequencies = values[:, 0]
    rounded_frequencies = np.rint(frequencies)
    if not np.array_equal(frequencies, rounded_frequencies):
        raise ValueError("NanoVNA returned a non-integer frequency")
    return (
        rounded_frequencies.astype(np.int64),
        values[:, 1] + 1j * values[:, 2],
    )


engine.NanoVNA.scan = hardened_scan
NanoVNA = engine.NanoVNA

original_capture = engine.capture


def capture(
    vna: engine.NanoVNA,
    start: int,
    stop: int,
    segments: int,
) -> tuple[np.ndarray, np.ndarray]:
    validate_sweep(start, stop, segments)
    return original_capture(vna, start, stop, segments)


engine.capture = capture

original_load_capture = engine.load_capture


def load_capture(
    path: engine.Path,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    frequencies, samples, metadata = original_load_capture(path)
    require_finite(f"{path} frequencies", frequencies)
    require_finite(f"{path} raw S11", samples)
    return frequencies, samples, metadata


engine.load_capture = load_capture

original_calculate_error_terms = engine.calculate_error_terms


def calculate_error_terms(
    open_sample: np.ndarray,
    short_sample: np.ndarray,
    load_sample: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    for label, values in (
        ("OPEN", open_sample),
        ("SHORT", short_sample),
        ("LOAD", load_sample),
    ):
        require_finite(f"{label} raw S11", values)
    solved = original_calculate_error_terms(open_sample, short_sample, load_sample)
    for label, values in zip(
        ("directivity", "source match", "reflection tracking"), solved
    ):
        require_finite(f"solved {label}", values)
    return solved


engine.calculate_error_terms = calculate_error_terms

original_apply_calibration = engine.apply_calibration


def apply_calibration(
    measured: np.ndarray,
    directivity: np.ndarray,
    source_match: np.ndarray,
    reflection_tracking: np.ndarray,
) -> np.ndarray:
    for label, values in (
        ("measured raw S11", measured),
        ("directivity", directivity),
        ("source match", source_match),
        ("reflection tracking", reflection_tracking),
    ):
        require_finite(label, values)
    corrected = original_apply_calibration(
        measured, directivity, source_match, reflection_tracking
    )
    require_finite("corrected S11", corrected)
    return corrected


engine.apply_calibration = apply_calibration

original_save_capture = engine.save_capture


def save_capture(
    path: engine.Path,
    label: str,
    frequencies: np.ndarray,
    samples: np.ndarray,
    metadata: dict[str, object],
) -> None:
    require_finite(f"{label} frequencies", frequencies)
    require_finite(f"{label} raw S11", samples)
    original_save_capture(path, label, frequencies, samples, metadata)


engine.save_capture = save_capture

original_save_calibration = engine.save_calibration


def save_calibration(
    output: engine.Path,
    frequencies: np.ndarray,
    directivity: np.ndarray,
    source_match: np.ndarray,
    reflection_tracking: np.ndarray,
    metadata: dict[str, object],
) -> None:
    for label, values in (
        ("calibration frequencies", frequencies),
        ("directivity", directivity),
        ("source match", source_match),
        ("reflection tracking", reflection_tracking),
    ):
        require_finite(label, values)
    original_save_calibration(
        output,
        frequencies,
        directivity,
        source_match,
        reflection_tracking,
        metadata,
    )


engine.save_calibration = save_calibration

original_load_calibration = engine.load_calibration


def load_calibration(
    path: engine.Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    loaded = original_load_calibration(path)
    for label, values in zip(
        (
            "calibration frequencies",
            "directivity",
            "source match",
            "reflection tracking",
        ),
        loaded[:4],
    ):
        require_finite(f"{path} {label}", values)
    return loaded


engine.load_calibration = load_calibration

original_save_measurement = engine.save_measurement


def save_measurement(
    output_dir: engine.Path,
    frequencies: np.ndarray,
    gamma: np.ndarray,
    metadata: dict[str, object],
) -> None:
    require_finite("measurement frequencies", frequencies)
    require_finite("calibrated S11", gamma)
    maximum_gamma = float(np.max(np.abs(gamma)))
    if maximum_gamma >= 1.0:
        raise ValueError(
            f"calibrated passive measurement has nonphysical |Gamma| {maximum_gamma}"
        )
    original_save_measurement(output_dir, frequencies, gamma, metadata)


engine.save_measurement = save_measurement


def capture_command(args: engine.argparse.Namespace) -> None:
    validate_sweep(args.start, args.stop, args.segments)
    output_dir = Path(args.output_dir)
    if output_dir.is_symlink():
        raise ValueError(f"refusing symlinked capture output directory {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{args.label}.npz"
    csv_output = output.with_suffix(".csv")
    marker = output_dir / f".{args.label}.capture-status.json"
    if marker.is_symlink():
        raise ValueError(f"refusing symlinked capture-status marker {marker}")
    if (output.exists() or csv_output.exists()) and not args.overwrite:
        raise FileExistsError(
            f"{output} or {csv_output} already exists; use --overwrite"
        )
    marker.write_text(
        json.dumps({"status": "in-progress", "label": args.label}, indent=2) + "\n",
        encoding="ascii",
    )
    try:
        vna = NanoVNA(args.port)
        try:
            device = vna.info()
            frequencies, samples = engine.capture(
                vna, args.start, args.stop, args.segments
            )
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
            "nominal_frequency_step_hz": engine.frequency_step(
                args.start, args.stop, args.segments
            ),
            "device": device,
        }
        with tempfile.TemporaryDirectory(
            prefix=f".{args.label}.", dir=output_dir
        ) as temporary:
            staged_output = Path(temporary) / f"{args.label}.npz"
            save_capture(
                staged_output, args.label, frequencies, samples, metadata
            )
            os.replace(staged_output.with_suffix(".csv"), csv_output)
            os.replace(staged_output, output)
    except BaseException:
        marker.write_text(
            json.dumps({"status": "rejected", "label": args.label}, indent=2)
            + "\n",
            encoding="ascii",
        )
        raise
    else:
        marker.unlink()
    print(output)


engine.capture_command = capture_command


def calibrate_command(args: engine.argparse.Namespace) -> None:
    calibration_dir = Path(args.calibration_dir)
    status_markers = list(calibration_dir.glob(".*.capture-status.json"))
    if status_markers:
        raise ValueError(
            "calibration directory contains incomplete/rejected capture markers: "
            + ", ".join(path.name for path in status_markers)
        )
    open_frequencies, open_sample, open_metadata = load_capture(
        calibration_dir / "open.npz"
    )
    short_frequencies, short_sample, _ = load_capture(
        calibration_dir / "short.npz"
    )
    load_frequencies, load_sample, _ = load_capture(calibration_dir / "load.npz")
    engine.ensure_matching_frequencies(
        open_frequencies, short_frequencies, "short"
    )
    engine.ensure_matching_frequencies(open_frequencies, load_frequencies, "load")
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
    with tempfile.TemporaryDirectory(
        prefix=".calibration.", dir=calibration_dir
    ) as temporary:
        staged_output = Path(temporary) / "calibration.npz"
        save_calibration(
            staged_output,
            open_frequencies,
            directivity,
            source_match,
            reflection_tracking,
            metadata,
        )
        os.replace(staged_output, output)
    print(output)


engine.calibrate_command = calibrate_command


def rejected_path(output_dir: Path) -> Path:
    timestamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    candidate = output_dir.with_name(f"{output_dir.name}.rejected-{timestamp}")
    counter = 1
    while candidate.exists():
        candidate = output_dir.with_name(
            f"{output_dir.name}.rejected-{timestamp}-{counter}"
        )
        counter += 1
    return candidate


def publish_run(staging: Path, output_dir: Path) -> None:
    backup = output_dir.with_name(f".{output_dir.name}.backup")
    if output_dir.is_symlink():
        raise ValueError(f"refusing symlinked measurement output {output_dir}")
    if backup.is_symlink():
        raise ValueError(f"refusing symlinked rollback backup {backup}")
    if backup.exists():
        marker = backup / BACKUP_MARKER
        if marker.is_symlink() or not marker.is_file():
            raise ValueError(f"refusing to remove unowned backup directory {backup}")
        ownership = json.loads(marker.read_text(encoding="ascii"))
        if ownership.get("output_dir") != str(output_dir.resolve()):
            raise ValueError(f"backup ownership does not match {output_dir}")
        if output_dir.exists():
            shutil.rmtree(backup)
        else:
            os.replace(backup, output_dir)
            (output_dir / BACKUP_MARKER).unlink()
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError(f"measurement output is not a directory: {output_dir}")
        marker = output_dir / BACKUP_MARKER
        if marker.exists() or marker.is_symlink():
            raise ValueError(f"refusing existing backup marker path {marker}")
        marker.write_text(
            json.dumps({"output_dir": str(output_dir.resolve())}, indent=2) + "\n",
            encoding="ascii",
        )
        try:
            os.replace(output_dir, backup)
        except BaseException:
            marker.unlink(missing_ok=True)
            raise
    try:
        os.replace(staging, output_dir)
    except BaseException:
        if backup.exists():
            os.replace(backup, output_dir)
            (output_dir / BACKUP_MARKER).unlink(missing_ok=True)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def validate_measurement_paths(calibration_path: Path, output_dir: Path) -> None:
    backup = output_dir.with_name(f".{output_dir.name}.backup")
    if output_dir.is_symlink():
        raise ValueError("measurement output directory must not be a symlink")
    if backup.is_symlink():
        raise ValueError("measurement rollback backup must not be a symlink")
    resolved_calibration = calibration_path.resolve()
    resolved_output = output_dir.resolve()
    resolved_backup = backup.resolve()
    for label, candidate in (
        ("output directory", resolved_output),
        ("rollback backup directory", resolved_backup),
    ):
        if candidate == resolved_calibration or candidate in resolved_calibration.parents:
            raise ValueError(f"measurement {label} must not equal or contain calibration")


def measure_command(args: engine.argparse.Namespace) -> None:
    calibration_path = Path(args.calibration)
    output_dir = Path(args.output_dir)
    validate_measurement_paths(calibration_path, output_dir)
    (
        calibration_frequencies,
        directivity,
        source_match,
        reflection_tracking,
        calibration_metadata,
    ) = load_calibration(calibration_path)
    source = calibration_metadata["source_capture"]
    if not isinstance(source, dict):
        raise ValueError("calibration source metadata is not an object")
    try:
        start = int(source["start_hz"])
        stop = int(source["stop_hz"])
        segments = int(source["segments"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("calibration source sweep metadata is invalid") from error
    validate_sweep(start, stop, segments)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists() and any(output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(
            f"{output_dir} is not empty; use --overwrite to replace it"
        )

    temporary = tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}.", dir=output_dir.parent
    )
    staging = Path(temporary.name) / "run"
    staging.mkdir()
    try:
        vna = NanoVNA(args.port)
        try:
            device = vna.info()
            frequencies, measured = engine.capture(
                vna,
                start,
                stop,
                segments,
            )
        finally:
            vna.close()

        engine.ensure_matching_frequencies(
            calibration_frequencies, frequencies, "antenna"
        )
        raw_metadata = {
            "captured_at": datetime.now().astimezone().isoformat(),
            "label": "antenna_raw",
            "port": args.port,
            "start_hz": start,
            "stop_hz": stop,
            "segments": segments,
            "points": int(len(frequencies)),
            "device": device,
        }
        save_capture(
            staging / "antenna_raw.npz",
            "antenna_raw",
            frequencies,
            measured,
            raw_metadata,
        )
        gamma = apply_calibration(
            measured, directivity, source_match, reflection_tracking
        )
        save_measurement(
            staging,
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
        (staging / "run-status.json").write_text(
            json.dumps(
                {
                    "status": "complete",
                    "captured_at": raw_metadata["captured_at"],
                    "points": int(len(frequencies)),
                    "calibration_file": str(calibration_path.resolve()),
                },
                indent=2,
            )
            + "\n",
            encoding="ascii",
        )
        publish_run(staging, output_dir)
    except BaseException:
        if staging.exists() and any(staging.iterdir()):
            shutil.move(str(staging), rejected_path(output_dir))
        raise
    finally:
        temporary.cleanup()
    print(output_dir)


engine.measure_command = measure_command


def main() -> int:
    return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
