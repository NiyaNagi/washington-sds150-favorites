#!/usr/bin/env python3
"""Validate a calibrated NanoVNA antenna-measurement evidence set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np


def load_raw(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        frequencies = data["frequencies_hz"]
        samples = data["s11_raw"]
    if frequencies.ndim != 1:
        raise ValueError(f"{path}: frequencies must be one-dimensional")
    if samples.ndim != 1:
        raise ValueError(f"{path}: raw S11 must be one-dimensional")
    if frequencies.shape != samples.shape:
        raise ValueError(f"{path}: raw S11 shape does not match frequency grid")
    return frequencies, samples


def load_points(path: Path) -> np.ndarray:
    points = np.genfromtxt(path, delimiter=",", names=True)
    if points.size == 0:
        raise ValueError(f"no points in {path}")
    return points


def load_touchstone(path: Path) -> tuple[np.ndarray, np.ndarray]:
    frequencies: list[int] = []
    samples: list[complex] = []
    option_line: list[str] | None = None
    with path.open(encoding="ascii") as source:
        for line in source:
            stripped = line.split("!", 1)[0].strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                if option_line is not None:
                    raise ValueError(f"multiple Touchstone option lines in {path}")
                option_line = stripped.split()
                continue
            fields = stripped.split()
            if len(fields) != 3:
                raise ValueError(
                    f"{path}: expected exactly 3 fields per one-port RI row"
                )
            frequency, real, imaginary = fields
            frequencies.append(int(frequency))
            samples.append(complex(float(real), float(imaginary)))
    if option_line != ["#", "Hz", "S", "RI", "R", "50"]:
        raise ValueError(
            f"{path}: expected canonical Touchstone option '# Hz S RI R 50'"
        )
    if not frequencies:
        raise ValueError(f"no Touchstone samples in {path}")
    return (
        np.asarray(frequencies, dtype=np.int64),
        np.asarray(samples, dtype=np.complex128),
    )


def finite_nonnegative(value: str) -> float:
    parsed = float(value)
    if not np.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("value must be finite and nonnegative")
    return parsed


def swr_limit(value: str) -> float:
    parsed = finite_nonnegative(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("SWR limit must be at least 1")
    return parsed


def gamma_threshold(value: str) -> float:
    parsed = finite_nonnegative(value)
    if parsed > 1:
        raise argparse.ArgumentTypeError("|Gamma| threshold must not exceed 1")
    return parsed


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_frequency_shape(
    frequencies: np.ndarray,
    *,
    expected_start: int,
    expected_stop: int,
    expected_points: int,
    label: str,
) -> None:
    if len(frequencies) != expected_points:
        raise ValueError(
            f"{label}: expected {expected_points} points, got {len(frequencies)}"
        )
    if int(frequencies[0]) != expected_start:
        raise ValueError(
            f"{label}: expected start {expected_start}, got {frequencies[0]}"
        )
    if int(frequencies[-1]) != expected_stop:
        raise ValueError(
            f"{label}: expected stop {expected_stop}, got {frequencies[-1]}"
        )
    if np.any(np.diff(frequencies) <= 0):
        raise ValueError(f"{label}: frequencies are not strictly increasing")


def assert_exact_grid(
    frequencies: np.ndarray,
    reference_frequencies: np.ndarray,
    *,
    label: str,
) -> None:
    if not np.array_equal(frequencies, reference_frequencies):
        raise ValueError(f"{label}: frequency grid does not exactly match calibration")


def assert_finite(points: np.ndarray, fields: tuple[str, ...], *, label: str) -> None:
    for field in fields:
        if not np.all(np.isfinite(points[field])):
            raise ValueError(f"{label}: {field} contains nonfinite data")


def assert_return_loss(
    return_loss: np.ndarray, magnitude: np.ndarray, *, label: str
) -> None:
    valid = np.isfinite(return_loss) | (
        np.isposinf(return_loss) & (magnitude == 0)
    )
    if not np.all(valid):
        raise ValueError(
            f"{label}: return_loss_db is invalid unless +inf corresponds to |Gamma|=0"
        )


def validate_standards(
    calibration_dir: Path,
    *,
    expected_start: int,
    expected_stop: int,
    expected_points: int,
    minimum_standard_separation: float,
) -> tuple[dict[str, float], np.ndarray, dict[str, np.ndarray]]:
    status_markers = list(calibration_dir.glob(".*.capture-status.json"))
    if status_markers:
        raise ValueError(
            "calibration directory contains incomplete/rejected capture markers: "
            + ", ".join(path.name for path in status_markers)
        )
    captures = {
        label: load_raw(calibration_dir / f"{label}.npz")
        for label in ("open", "short", "load")
    }
    reference_frequencies = captures["open"][0]
    assert_frequency_shape(
        reference_frequencies,
        expected_start=expected_start,
        expected_stop=expected_stop,
        expected_points=expected_points,
        label="OPEN",
    )
    for label, (frequencies, _) in captures.items():
        if not np.array_equal(reference_frequencies, frequencies):
            raise ValueError(f"{label}: frequencies do not match OPEN")
        if not np.all(np.isfinite(captures[label][1])):
            raise ValueError(f"{label}: raw S11 contains nonfinite values")
    separations = {}
    for first, second in (("open", "short"), ("open", "load"), ("short", "load")):
        median = float(
            np.median(np.abs(captures[first][1] - captures[second][1]))
        )
        separations[f"{first}_{second}_median_separation"] = median
        if median < minimum_standard_separation:
            raise ValueError(
                f"{first}/{second}: median raw separation {median:.6f} is below "
                f"{minimum_standard_separation:.6f}"
            )
    calibration_path = calibration_dir / "calibration.npz"
    if not calibration_path.exists():
        raise ValueError(f"missing solved calibration: {calibration_path}")
    with np.load(calibration_path, allow_pickle=False) as calibration:
        if not np.array_equal(
            reference_frequencies, calibration["frequencies_hz"]
        ):
            raise ValueError("solved calibration frequencies do not match standards")
        open_sample = captures["open"][1]
        short_sample = captures["short"][1]
        load_sample = captures["load"][1]
        expected_directivity = load_sample
        open_delta = open_sample - expected_directivity
        short_delta = short_sample - expected_directivity
        denominator = open_delta - short_delta
        if np.any(np.abs(denominator) < 1e-12):
            raise ValueError("raw standards produce a singular calibration")
        expected_source_match = (open_delta + short_delta) / denominator
        expected_tracking = open_delta * (1.0 - expected_source_match)
        expected_terms = {
            "directivity": expected_directivity,
            "source_match": expected_source_match,
            "reflection_tracking": expected_tracking,
        }
        for term, expected in expected_terms.items():
            if calibration[term].shape != reference_frequencies.shape:
                raise ValueError(f"calibration term {term} has wrong shape")
            if not np.all(np.isfinite(calibration[term])):
                raise ValueError(f"calibration term {term} contains nonfinite values")
            if not np.allclose(
                calibration[term], expected, rtol=1e-12, atol=1e-12
            ):
                raise ValueError(
                    f"calibration term {term} does not match raw standards"
                )
    return separations, reference_frequencies, expected_terms


def apply_calibration(
    measured: np.ndarray, calibration_terms: dict[str, np.ndarray]
) -> np.ndarray:
    if measured.ndim != 1:
        raise ValueError("measured raw S11 must be one-dimensional")
    for label, values in calibration_terms.items():
        if values.ndim != 1 or values.shape != measured.shape:
            raise ValueError(
                f"calibration term {label} shape does not match measured raw S11"
            )
    delta = measured - calibration_terms["directivity"]
    denominator = (
        calibration_terms["reflection_tracking"]
        + calibration_terms["source_match"] * delta
    )
    if np.any(np.abs(denominator) <= 1e-15):
        raise ValueError("calibration correction denominator is too small")
    gamma = delta / denominator
    if not np.all(np.isfinite(gamma)):
        raise ValueError("recomputed calibrated S11 contains nonfinite data")
    return gamma


def validate_measurement(
    measurement_dir: Path,
    *,
    reference_frequencies: np.ndarray,
    calibration_terms: dict[str, np.ndarray],
    expected_start: int,
    expected_stop: int,
    expected_points: int,
) -> dict[str, float]:
    points = load_points(measurement_dir / "antenna_swr.csv")
    assert_frequency_shape(
        points["frequency_hz"],
        expected_start=expected_start,
        expected_stop=expected_stop,
        expected_points=expected_points,
        label=measurement_dir.name,
    )
    assert_exact_grid(
        points["frequency_hz"],
        reference_frequencies,
        label=measurement_dir.name,
    )
    assert_finite(
        points,
        (
            "frequency_mhz",
            "s11_real",
            "s11_imag",
            "s11_magnitude",
            "phase_deg",
            "swr",
            "resistance_ohm",
            "reactance_ohm",
        ),
        label=measurement_dir.name,
    )
    assert_return_loss(
        points["return_loss_db"],
        points["s11_magnitude"],
        label=measurement_dir.name,
    )
    if not np.allclose(
        points["frequency_mhz"],
        points["frequency_hz"] / 1e6,
        rtol=0,
        atol=5e-13,
    ):
        raise ValueError(
            f"{measurement_dir.name}: frequency_mhz does not match frequency_hz"
        )
    raw_frequencies, measured = load_raw(measurement_dir / "antenna_raw.npz")
    assert_exact_grid(
        raw_frequencies,
        reference_frequencies,
        label=f"{measurement_dir.name} raw capture",
    )
    if not np.all(np.isfinite(measured)):
        raise ValueError(f"{measurement_dir.name}: raw S11 contains nonfinite data")
    recomputed_gamma = apply_calibration(measured, calibration_terms)
    csv_gamma = points["s11_real"] + 1j * points["s11_imag"]
    if not np.allclose(csv_gamma, recomputed_gamma, rtol=1e-11, atol=1e-11):
        raise ValueError(
            f"{measurement_dir.name}: calibrated CSV does not match raw capture"
        )
    recomputed_magnitude = np.abs(recomputed_gamma)
    if not np.allclose(
        points["s11_magnitude"], recomputed_magnitude, rtol=1e-11, atol=1e-11
    ):
        raise ValueError(
            f"{measurement_dir.name}: CSV |Gamma| does not match calibrated S11"
        )
    with np.errstate(divide="ignore", invalid="ignore"):
        recomputed_swr = (1.0 + recomputed_magnitude) / (
            1.0 - recomputed_magnitude
        )
        recomputed_return_loss = -20.0 * np.log10(recomputed_magnitude)
        recomputed_impedance = 50.0 * (1.0 + recomputed_gamma) / (
            1.0 - recomputed_gamma
        )
    derived_fields = {
        "phase_deg": np.angle(recomputed_gamma, deg=True),
        "swr": recomputed_swr,
        "return_loss_db": recomputed_return_loss,
        "resistance_ohm": recomputed_impedance.real,
        "reactance_ohm": recomputed_impedance.imag,
    }
    for field, expected in derived_fields.items():
        if not np.allclose(points[field], expected, rtol=1e-10, atol=1e-10):
            raise ValueError(
                f"{measurement_dir.name}: CSV {field} does not match calibrated S11"
            )
    maximum_gamma = float(np.max(recomputed_magnitude))
    if maximum_gamma >= 1.0:
        raise ValueError(
            f"{measurement_dir.name}: nonphysical |Gamma| maximum {maximum_gamma}"
        )
    touchstone = measurement_dir / "antenna.s1p"
    if not touchstone.exists():
        raise ValueError(f"missing Touchstone output: {touchstone}")
    touchstone_frequencies, touchstone_gamma = load_touchstone(touchstone)
    assert_exact_grid(
        touchstone_frequencies,
        reference_frequencies,
        label=f"{measurement_dir.name} Touchstone",
    )
    if not np.all(np.isfinite(touchstone_gamma)):
        raise ValueError(f"{measurement_dir.name}: Touchstone contains nonfinite data")
    if not np.allclose(
        touchstone_gamma, recomputed_gamma, rtol=1e-9, atol=1e-9
    ):
        raise ValueError(
            f"{measurement_dir.name}: Touchstone does not match raw capture"
        )
    return {
        "minimum_swr": float(np.min(points["swr"])),
        "median_swr": float(np.median(points["swr"])),
        "maximum_swr": float(np.max(points["swr"])),
        "maximum_gamma": maximum_gamma,
    }


def validate_load(
    verification_dir: Path,
    *,
    reference_frequencies: np.ndarray,
    calibration_terms: dict[str, np.ndarray],
    expected_start: int,
    expected_stop: int,
    expected_points: int,
    maximum_median_swr: float,
    maximum_p95_swr: float,
    maximum_swr: float,
) -> dict[str, float]:
    validate_measurement(
        verification_dir,
        reference_frequencies=reference_frequencies,
        calibration_terms=calibration_terms,
        expected_start=expected_start,
        expected_stop=expected_stop,
        expected_points=expected_points,
    )
    points = load_points(verification_dir / "antenna_swr.csv")
    assert_frequency_shape(
        points["frequency_hz"],
        expected_start=expected_start,
        expected_stop=expected_stop,
        expected_points=expected_points,
        label="load verification",
    )
    assert_exact_grid(
        points["frequency_hz"],
        reference_frequencies,
        label="load verification",
    )
    assert_finite(
        points,
        (
            "s11_real",
            "s11_imag",
            "s11_magnitude",
            "swr",
            "resistance_ohm",
            "reactance_ohm",
        ),
        label="load verification",
    )
    swr = points["swr"]
    result = {
        "median_swr": float(np.median(swr)),
        "p95_swr": float(np.percentile(swr, 95)),
        "maximum_swr": float(np.max(swr)),
        "median_resistance_ohm": float(np.median(points["resistance_ohm"])),
        "median_reactance_ohm": float(np.median(points["reactance_ohm"])),
        "maximum_abs_reactance_ohm": float(
            np.max(np.abs(points["reactance_ohm"]))
        ),
    }
    limits = {
        "median_swr": maximum_median_swr,
        "p95_swr": maximum_p95_swr,
        "maximum_swr": maximum_swr,
    }
    for field, limit in limits.items():
        if result[field] > limit:
            raise ValueError(
                f"load verification {field} {result[field]:.6f} exceeds {limit:.6f}"
            )
    return result


def validate_open_path(
    open_path_dir: Path,
    *,
    reference_frequencies: np.ndarray,
    calibration_terms: dict[str, np.ndarray],
    expected_start: int,
    expected_stop: int,
    expected_points: int,
    minimum_median_gamma: float,
) -> dict[str, float]:
    validate_measurement(
        open_path_dir,
        reference_frequencies=reference_frequencies,
        calibration_terms=calibration_terms,
        expected_start=expected_start,
        expected_stop=expected_stop,
        expected_points=expected_points,
    )
    points = load_points(open_path_dir / "antenna_swr.csv")
    assert_frequency_shape(
        points["frequency_hz"],
        expected_start=expected_start,
        expected_stop=expected_stop,
        expected_points=expected_points,
        label="far-end-open path",
    )
    assert_exact_grid(
        points["frequency_hz"],
        reference_frequencies,
        label="far-end-open path",
    )
    assert_finite(
        points,
        ("s11_real", "s11_imag", "s11_magnitude", "swr"),
        label="far-end-open path",
    )
    magnitude = points["s11_magnitude"]
    result = {
        "median_gamma": float(np.median(magnitude)),
        "p05_gamma": float(np.percentile(magnitude, 5)),
        "p95_gamma": float(np.percentile(magnitude, 95)),
    }
    if result["median_gamma"] < minimum_median_gamma:
        raise ValueError(
            "far-end-open path median |Gamma| "
            f"{result['median_gamma']:.6f} is below {minimum_median_gamma:.6f}"
        )
    return result


def validate_repeatability(
    first_dir: Path,
    repeat_dir: Path,
    *,
    reference_frequencies: np.ndarray,
    calibration_terms: dict[str, np.ndarray],
    expected_start: int,
    expected_stop: int,
    expected_points: int,
    maximum_median_complex_delta: float,
    maximum_median_swr_delta: float,
) -> dict[str, float]:
    validate_measurement(
        first_dir,
        reference_frequencies=reference_frequencies,
        calibration_terms=calibration_terms,
        expected_start=expected_start,
        expected_stop=expected_stop,
        expected_points=expected_points,
    )
    validate_measurement(
        repeat_dir,
        reference_frequencies=reference_frequencies,
        calibration_terms=calibration_terms,
        expected_start=expected_start,
        expected_stop=expected_stop,
        expected_points=expected_points,
    )
    first = load_points(first_dir / "antenna_swr.csv")
    repeat = load_points(repeat_dir / "antenna_swr.csv")
    for label, points in (("first", first), ("repeat", repeat)):
        assert_frequency_shape(
            points["frequency_hz"],
            expected_start=expected_start,
            expected_stop=expected_stop,
            expected_points=expected_points,
            label=label,
        )
        assert_exact_grid(
            points["frequency_hz"],
            reference_frequencies,
            label=label,
        )
        assert_finite(
            points,
            ("s11_real", "s11_imag", "s11_magnitude", "swr"),
            label=label,
        )
    if not np.array_equal(first["frequency_hz"], repeat["frequency_hz"]):
        raise ValueError("repeat frequencies do not exactly match the first sweep")
    complex_delta = np.hypot(
        first["s11_real"] - repeat["s11_real"],
        first["s11_imag"] - repeat["s11_imag"],
    )
    swr_delta = np.abs(first["swr"] - repeat["swr"])
    result = {
        "median_complex_s11_delta": float(np.median(complex_delta)),
        "p95_complex_s11_delta": float(np.percentile(complex_delta, 95)),
        "maximum_complex_s11_delta": float(np.max(complex_delta)),
        "median_swr_delta": float(np.median(swr_delta)),
        "p95_swr_delta": float(np.percentile(swr_delta, 95)),
        "maximum_swr_delta": float(np.max(swr_delta)),
    }
    if result["median_complex_s11_delta"] > maximum_median_complex_delta:
        raise ValueError(
            "median complex-S11 delta "
            f"{result['median_complex_s11_delta']:.6f} exceeds "
            f"{maximum_median_complex_delta:.6f}"
        )
    if result["median_swr_delta"] > maximum_median_swr_delta:
        raise ValueError(
            f"median SWR delta {result['median_swr_delta']:.6f} exceeds "
            f"{maximum_median_swr_delta:.6f}"
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-dir", required=True, type=Path)
    parser.add_argument("--load-verification-dir", required=True, type=Path)
    parser.add_argument("--measurement-dir", required=True, type=Path)
    parser.add_argument("--repeat-dir", required=True, type=Path)
    parser.add_argument("--open-path-dir", type=Path)
    parser.add_argument("--start-hz", required=True, type=int)
    parser.add_argument("--stop-hz", required=True, type=int)
    parser.add_argument("--points", type=int, default=40_001)
    parser.add_argument(
        "--minimum-standard-separation", type=finite_nonnegative, default=0.2
    )
    parser.add_argument("--maximum-load-median-swr", type=swr_limit, default=1.01)
    parser.add_argument("--maximum-load-p95-swr", type=swr_limit, default=1.02)
    parser.add_argument("--maximum-load-swr", type=swr_limit, default=1.10)
    parser.add_argument(
        "--minimum-open-path-median-gamma", type=gamma_threshold, default=0.5
    )
    parser.add_argument(
        "--maximum-repeat-median-complex-delta",
        type=finite_nonnegative,
        default=0.005,
    )
    parser.add_argument(
        "--maximum-repeat-median-swr-delta",
        type=finite_nonnegative,
        default=0.05,
    )
    parser.add_argument("--output", type=Path)
    return parser


def evidence_files(args: argparse.Namespace) -> list[Path]:
    roots = evidence_roots(args)
    result: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root.is_symlink():
            raise ValueError(f"evidence root must not be a symlink: {root}")
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"evidence tree contains a symlink: {path}")
            resolved = path.resolve()
            if path.is_file() and resolved not in seen:
                result.append(path)
                seen.add(resolved)
    return result


def evidence_roots(args: argparse.Namespace) -> list[Path]:
    result = [
        args.calibration_dir,
        args.load_verification_dir,
        args.measurement_dir,
        args.repeat_dir,
    ]
    if args.open_path_dir:
        result.append(args.open_path_dir)
    return result


def prepare_output(output: Path | None, inputs: list[Path], roots: list[Path]) -> None:
    if output is None:
        return
    resolved_output = output.resolve()
    temporary_output = output.with_name(f".{output.name}.tmp").resolve()
    resolved_inputs = {path.resolve() for path in inputs}
    resolved_roots = [root.resolve() for root in roots]
    inside_evidence = any(
        root == candidate or root in candidate.parents
        for root in resolved_roots
        for candidate in (resolved_output, temporary_output)
    )
    if (
        resolved_output in resolved_inputs
        or temporary_output in resolved_inputs
        or inside_evidence
    ):
        raise ValueError("--output and its temporary path must not overlap evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    output.with_name(f".{output.name}.tmp").unlink(missing_ok=True)


def main() -> int:
    args = build_parser().parse_args()
    bound_roots = evidence_roots(args)
    bound_evidence = evidence_files(args)
    prepare_output(args.output, bound_evidence, bound_roots)
    if args.start_hz < 0 or args.stop_hz <= args.start_hz:
        raise ValueError("frequency range must be nonnegative and increasing")
    if args.points < 2:
        raise ValueError("--points must be at least 2")
    standards, reference_frequencies, calibration_terms = validate_standards(
        args.calibration_dir,
        expected_start=args.start_hz,
        expected_stop=args.stop_hz,
        expected_points=args.points,
        minimum_standard_separation=args.minimum_standard_separation,
    )
    report: dict[str, object] = {
        "range_hz": [args.start_hz, args.stop_hz],
        "expected_points": args.points,
        "standards": standards,
        "load_verification": validate_load(
            args.load_verification_dir,
            reference_frequencies=reference_frequencies,
            calibration_terms=calibration_terms,
            expected_start=args.start_hz,
            expected_stop=args.stop_hz,
            expected_points=args.points,
            maximum_median_swr=args.maximum_load_median_swr,
            maximum_p95_swr=args.maximum_load_p95_swr,
            maximum_swr=args.maximum_load_swr,
        ),
        "measurement": validate_measurement(
            args.measurement_dir,
            reference_frequencies=reference_frequencies,
            calibration_terms=calibration_terms,
            expected_start=args.start_hz,
            expected_stop=args.stop_hz,
            expected_points=args.points,
        ),
        "repeatability": validate_repeatability(
            args.measurement_dir,
            args.repeat_dir,
            reference_frequencies=reference_frequencies,
            calibration_terms=calibration_terms,
            expected_start=args.start_hz,
            expected_stop=args.stop_hz,
            expected_points=args.points,
            maximum_median_complex_delta=args.maximum_repeat_median_complex_delta,
            maximum_median_swr_delta=args.maximum_repeat_median_swr_delta,
        ),
    }
    if args.open_path_dir:
        report["far_end_open"] = validate_open_path(
            args.open_path_dir,
            reference_frequencies=reference_frequencies,
            calibration_terms=calibration_terms,
            expected_start=args.start_hz,
            expected_stop=args.stop_hz,
            expected_points=args.points,
            minimum_median_gamma=args.minimum_open_path_median_gamma,
        )
    report["status"] = "passed"
    report["evidence_sha256"] = {
        str(path): sha256(path) for path in bound_evidence
    }
    rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        temporary_output = args.output.with_name(f".{args.output.name}.tmp")
        temporary_output.write_text(rendered, encoding="ascii")
        os.replace(temporary_output, args.output)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
