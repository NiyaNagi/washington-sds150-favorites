#!/usr/bin/env python3
"""Targeted tests for the archived/hardened NanoVNA toolchain."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import nanovna_swr as capture  # noqa: E402


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_nanovna_run", TOOLS / "validate_nanovna_run.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError("cannot load validate_nanovna_run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


class NanoVnaToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="nanovna-tool-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_calibration(self) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        frequencies = np.array([1, 2, 3], dtype=np.int64)
        standards = {
            "open": np.ones(3, dtype=np.complex128),
            "short": -np.ones(3, dtype=np.complex128),
            "load": np.zeros(3, dtype=np.complex128),
        }
        for name, samples in standards.items():
            np.savez_compressed(
                self.root / f"{name}.npz",
                label=name,
                frequencies_hz=frequencies,
                s11_raw=samples,
                metadata=json.dumps({}),
            )
        terms = {
            "directivity": standards["load"],
            "source_match": np.zeros(3, dtype=np.complex128),
            "reflection_tracking": np.ones(3, dtype=np.complex128),
        }
        np.savez_compressed(
            self.root / "calibration.npz",
            frequencies_hz=frequencies,
            metadata=json.dumps({}),
            **terms,
        )
        return frequencies, terms

    def write_measurement(
        self, directory: Path, frequencies: np.ndarray, gamma: np.ndarray
    ) -> None:
        directory.mkdir()
        np.savez_compressed(
            directory / "antenna_raw.npz",
            label="antenna_raw",
            frequencies_hz=frequencies,
            s11_raw=gamma,
            metadata=json.dumps({}),
        )
        magnitude = np.abs(gamma)
        with np.errstate(divide="ignore", invalid="ignore"):
            swr = (1 + magnitude) / (1 - magnitude)
            return_loss = -20 * np.log10(magnitude)
            impedance = 50 * (1 + gamma) / (1 - gamma)
        with (directory / "antenna_swr.csv").open(
            "w", newline="", encoding="ascii"
        ) as destination:
            writer = csv.writer(destination)
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
                    magnitude,
                    np.angle(gamma, deg=True),
                    swr,
                    return_loss,
                    impedance.real,
                    impedance.imag,
                )
            )
        with (directory / "antenna.s1p").open(
            "w", encoding="ascii"
        ) as destination:
            destination.write("# Hz S RI R 50\n")
            for frequency, sample in zip(frequencies, gamma):
                destination.write(
                    f"{frequency} {sample.real:.12g} {sample.imag:.12g}\n"
                )

    def test_calibration_solver_self_test(self) -> None:
        rng = np.random.default_rng(42)
        count = 1000
        directivity = 0.03 + 0.02j + rng.normal(0, 0.001, count)
        source_match = -0.08 + 0.04j + rng.normal(0, 0.001, count)
        tracking = 0.75 - 0.12j + rng.normal(0, 0.001, count)

        def measure(gamma: np.ndarray) -> np.ndarray:
            return directivity + tracking * gamma / (1 - source_match * gamma)

        expected = 0.2 * np.exp(1j * np.linspace(-np.pi, np.pi, count))
        solved = capture.calculate_error_terms(
            measure(np.ones(count)),
            measure(-np.ones(count)),
            measure(np.zeros(count)),
        )
        corrected = capture.apply_calibration(measure(expected), *solved)
        self.assertLess(float(np.max(np.abs(corrected - expected))), 1e-12)

    def test_nonfinite_scan_is_rejected(self) -> None:
        class FakeVna:
            def command(self, command: str, timeout: float) -> list[str]:
                del command, timeout
                return ["nan 0 0"] + [
                    f"{frequency} 0 0" for frequency in range(101, 201)
                ]

        with self.assertRaisesRegex(ValueError, "nonfinite"):
            capture.hardened_scan(FakeVna(), 100, 200)

    def test_stale_calibration_is_rejected(self) -> None:
        frequencies, terms = self.write_calibration()
        terms["directivity"] = np.full(3, 0.1 + 0j)
        np.savez_compressed(
            self.root / "calibration.npz",
            frequencies_hz=frequencies,
            metadata=json.dumps({}),
            **terms,
        )
        with self.assertRaisesRegex(ValueError, "does not match raw standards"):
            validator.validate_standards(
                self.root,
                expected_start=1,
                expected_stop=3,
                expected_points=3,
                minimum_standard_separation=0.2,
            )

    def test_shifted_grid_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly match"):
            validator.assert_exact_grid(
                np.array([1, 2.5, 3]), np.array([1, 2, 3]), label="shifted"
            )

    def test_raw_shape_mismatch_is_rejected(self) -> None:
        self.write_calibration()
        raw = self.root / "open.npz"
        np.savez_compressed(
            raw,
            frequencies_hz=np.array([1, 2, 3]),
            s11_raw=np.array([1 + 0j]),
            metadata=json.dumps({}),
        )
        with self.assertRaisesRegex(ValueError, "shape does not match"):
            validator.load_raw(raw)

    def test_invalid_sweep_ranges_are_rejected(self) -> None:
        for start, stop, segments in (
            (20, 10, 1),
            (-1, 100, 1),
            (1, 100, 0),
            (1, 100, 10_001),
            (1, 50, 1),
        ):
            with self.subTest(start=start, stop=stop, segments=segments):
                with self.assertRaises(ValueError):
                    capture.validate_sweep(start, stop, segments)
        capture.validate_sweep(500_000, 54_000_000, 400)

    def test_nonfinite_threshold_is_rejected(self) -> None:
        with self.assertRaisesRegex(Exception, "finite and nonnegative"):
            validator.finite_nonnegative("nan")

    def test_raw_csv_and_touchstone_are_bound(self) -> None:
        frequencies, terms = self.write_calibration()
        measurement = self.root / "measurement"
        gamma = np.array([0.1 + 0j, 0 + 0.2j, -0.1 + 0j])
        self.write_measurement(measurement, frequencies, gamma)
        validator.validate_measurement(
            measurement,
            reference_frequencies=frequencies,
            calibration_terms=terms,
            expected_start=1,
            expected_stop=3,
            expected_points=3,
        )
        raw = measurement / "antenna_raw.npz"
        with np.load(raw, allow_pickle=False) as data:
            payload = {name: data[name] for name in data.files}
        payload["s11_raw"] = payload["s11_raw"].copy()
        payload["s11_raw"][1] += 0.01
        np.savez_compressed(raw, **payload)
        with self.assertRaisesRegex(ValueError, "does not match raw capture"):
            validator.validate_measurement(
                measurement,
                reference_frequencies=frequencies,
                calibration_terms=terms,
                expected_start=1,
                expected_stop=3,
                expected_points=3,
            )

    def test_touchstone_options_are_bound(self) -> None:
        frequencies, terms = self.write_calibration()
        measurement = self.root / "measurement"
        gamma = np.array([0.1 + 0j, 0 + 0.2j, -0.1 + 0j])
        self.write_measurement(measurement, frequencies, gamma)
        touchstone = measurement / "antenna.s1p"
        touchstone.write_text(
            touchstone.read_text(encoding="ascii").replace(
                "# Hz S RI R 50", "# MHz S MA R 75"
            ),
            encoding="ascii",
        )
        with self.assertRaisesRegex(ValueError, "canonical Touchstone option"):
            validator.validate_measurement(
                measurement,
                reference_frequencies=frequencies,
                calibration_terms=terms,
                expected_start=1,
                expected_stop=3,
                expected_points=3,
            )

    def test_touchstone_extra_fields_are_rejected(self) -> None:
        path = self.root / "bad.s1p"
        path.write_text(
            "# Hz S RI R 50\n1 0.1 0.2 99\n",
            encoding="ascii",
        )
        with self.assertRaisesRegex(ValueError, "exactly 3 fields"):
            validator.load_touchstone(path)

    def test_output_cannot_overlap_evidence(self) -> None:
        evidence = self.root / "antenna.s1p"
        evidence.write_text("# Hz S RI R 50\n1 0 0\n", encoding="ascii")
        with self.assertRaisesRegex(ValueError, "must not overlap evidence"):
            validator.prepare_output(evidence, [evidence], [self.root])
        self.assertTrue(evidence.exists())
        new_file = self.root / "validation.json"
        with self.assertRaisesRegex(ValueError, "must not overlap evidence"):
            validator.prepare_output(new_file, [evidence], [self.root])
        self.assertFalse(new_file.exists())

    def test_perfect_match_return_loss_is_valid(self) -> None:
        frequencies, terms = self.write_calibration()
        measurement = self.root / "perfect"
        gamma = np.zeros(3, dtype=np.complex128)
        self.write_measurement(measurement, frequencies, gamma)
        validator.validate_measurement(
            measurement,
            reference_frequencies=frequencies,
            calibration_terms=terms,
            expected_start=1,
            expected_stop=3,
            expected_points=3,
        )

    def test_atomic_publish_replaces_complete_directory(self) -> None:
        output = self.root / "published"
        output.mkdir()
        (output / "old.txt").write_text("old", encoding="ascii")
        staging = self.root / "staging"
        staging.mkdir()
        (staging / "run-status.json").write_text("complete", encoding="ascii")
        capture.publish_run(staging, output)
        self.assertFalse((output / "old.txt").exists())
        self.assertEqual(
            (output / "run-status.json").read_text(encoding="ascii"), "complete"
        )
        self.assertFalse(output.with_name(".published.backup").exists())

    def test_measurement_output_cannot_contain_calibration(self) -> None:
        calibration_dir = self.root / "calibration"
        calibration_dir.mkdir()
        calibration = calibration_dir / "calibration.npz"
        calibration.write_bytes(b"calibration")
        with self.assertRaisesRegex(ValueError, "must not equal or contain"):
            capture.validate_measurement_paths(calibration, calibration_dir)
        with self.assertRaisesRegex(ValueError, "must not equal or contain"):
            capture.validate_measurement_paths(calibration, self.root)
        capture.validate_measurement_paths(
            calibration, calibration_dir / "load-verification"
        )
        backup_calibration = self.root / ".dut.backup" / "calibration.npz"
        backup_calibration.parent.mkdir()
        backup_calibration.write_bytes(b"calibration")
        with self.assertRaisesRegex(
            ValueError, "rollback backup directory must not equal or contain"
        ):
            capture.validate_measurement_paths(
                backup_calibration, self.root / "dut"
            )

    def test_unowned_backup_is_never_deleted(self) -> None:
        output = self.root / "run"
        backup = self.root / ".run.backup"
        backup.mkdir()
        evidence = backup / "calibration.npz"
        evidence.write_bytes(b"do not delete")
        staging = self.root / "staging"
        staging.mkdir()
        with self.assertRaisesRegex(ValueError, "unowned backup"):
            capture.publish_run(staging, output)
        self.assertEqual(evidence.read_bytes(), b"do not delete")

    def test_symlinked_backup_marker_is_never_followed(self) -> None:
        output = self.root / "run"
        output.mkdir()
        external = self.root / "external-calibration.npz"
        external.write_bytes(b"calibration")
        (output / capture.BACKUP_MARKER).symlink_to(external)
        staging = self.root / "staging"
        staging.mkdir()
        with self.assertRaisesRegex(ValueError, "backup marker"):
            capture.publish_run(staging, output)
        self.assertEqual(external.read_bytes(), b"calibration")

    def test_symlinked_output_and_backup_directories_are_rejected(self) -> None:
        external = self.root / "external"
        external.mkdir()
        calibration = self.root / "calibration.npz"
        calibration.write_bytes(b"calibration")
        output = self.root / "run"
        output.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            capture.validate_measurement_paths(calibration, output)
        output.unlink()
        backup = self.root / ".run.backup"
        backup.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "backup must not be a symlink"):
            capture.validate_measurement_paths(calibration, output)
        staging = self.root / "staging"
        staging.mkdir()
        with self.assertRaisesRegex(ValueError, "symlinked rollback backup"):
            capture.publish_run(staging, output)


if __name__ == "__main__":
    unittest.main()
