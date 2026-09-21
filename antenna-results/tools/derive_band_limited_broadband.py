#!/usr/bin/env python3
"""Derive a band-limited broadband Touchstone from a rejected capture.

``nanovna_swr.py measure`` fails closed when any calibrated sample of a
passive DUT reaches ``|Gamma| >= 1``, and preserves the raw capture under a
``.rejected-TIMESTAMP`` directory. That is the correct behaviour: a nonphysical
sample means the corrected result is outside the fixture's calibrated dynamic
range, and it must never be published as a measurement.

A badly matched antenna can still be perfectly measurable over most of the
span while exhausting the dynamic range at one end. This tool recovers only
the physically valid part of such a capture:

- it recomputes ``Gamma`` from the preserved ``antenna_raw.npz`` and the same
  solved calibration, exactly as ``measure`` would;
Two different failures need two different treatments, so the tool picks a mode
from the shape of the damage and records which one it used:

``isolated`` - every unbroken stretch of nonphysical samples is at most
``--max-isolated-run`` points (default 5). That is an outlier, typically a
local transmitter keying up during the sweep, not a property of the antenna.
Those individual samples are dropped and the rest of the span is kept.

``truncated`` - the nonphysical samples form a wide region, which is what
exhausting the fixture's calibrated dynamic range looks like. The tool keeps
the longest unbroken physical run and truncates there. Stitching across such a
region would fabricate a continuous curve out of noise and hide the very
condition that made the capture fail, so any physical sample beyond the
truncation point is discarded with the rest.

In both modes it writes ``antenna.s1p`` over the retained samples and
``broadband-excluded.json`` recording the mode, the retained range and every
excluded interval, so what was dropped is explicit and checkable rather than
silently missing. It refuses to write anything if the retained samples cover
less than ``--minimum-retained`` of the sweep (default 0.5).

The output is a derived artifact, not a raw one. It is deterministic and
re-runnable from the preserved raw capture plus the calibration, which is the
same evidence binding ``validate_nanovna_run.py`` enforces elsewhere.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nanovna_swr as n  # noqa: E402


def contiguous_intervals(indexes: np.ndarray) -> list[tuple[int, int]]:
    if not indexes.size:
        return []
    intervals = []
    start = previous = int(indexes[0])
    for index in indexes[1:]:
        index = int(index)
        if index != previous + 1:
            intervals.append((start, previous))
            start = index
        previous = index
    intervals.append((start, previous))
    return intervals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rejected-dir", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--minimum-retained", type=float, default=0.5)
    parser.add_argument("--max-isolated-run", type=int, default=5)
    args = parser.parse_args()

    raw = np.load(args.rejected_dir / "antenna_raw.npz")
    frequencies = raw["frequencies_hz"]
    measured = raw["s11_raw"]
    n.require_finite("preserved raw S11", measured)

    (
        calibration_frequencies,
        directivity,
        source_match,
        tracking,
        calibration_metadata,
    ) = n.load_calibration(args.calibration)
    n.engine.ensure_matching_frequencies(calibration_frequencies, frequencies, "antenna")

    gamma = n.apply_calibration(measured, directivity, source_match, tracking)
    magnitude = np.abs(gamma)
    physical = np.isfinite(magnitude) & (magnitude < 1.0)
    if not physical.any():
        raise SystemExit("no physical samples in this capture")

    defects = contiguous_intervals(np.flatnonzero(~physical))
    widest_defect = max((b - a + 1 for a, b in defects), default=0)
    if widest_defect <= args.max_isolated_run:
        mode = "isolated"
        keep = np.flatnonzero(physical)
    else:
        mode = "truncated"
        runs = contiguous_intervals(np.flatnonzero(physical))
        start, stop = max(runs, key=lambda run: run[1] - run[0])
        keep = np.arange(start, stop + 1)

    retained = keep.size / frequencies.size
    if retained < args.minimum_retained:
        raise SystemExit(
            f"retained samples cover only {retained:.1%} of the sweep; refusing to "
            f"derive a band-limited broadband below the "
            f"{args.minimum_retained:.0%} threshold"
        )
    start, stop = int(keep[0]), int(keep[-1])
    kept = np.zeros(frequencies.size, dtype=bool)
    kept[keep] = True
    excluded = np.flatnonzero(~kept)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "antenna.s1p").open("w", encoding="ascii") as destination:
        destination.write(
            "! Calibrated NanoVNA antenna measurement, band-limited to the "
            "calibrated dynamic range\n"
        )
        destination.write(
            "! Samples with nonfinite or |Gamma| >= 1 were excluded; see "
            "broadband-excluded.json\n"
        )
        destination.write("# Hz S RI R 50\n")
        for index in keep:
            destination.write(
                f"{int(frequencies[index]):d} {gamma[index].real:.12g} "
                f"{gamma[index].imag:.12g}\n"
            )

    report = {
        "derived_from": str(args.rejected_dir),
        "calibration_file": str(args.calibration),
        "calibration": calibration_metadata,
        "mode": mode,
        "total_points": int(frequencies.size),
        "retained_points": int(keep.size),
        "retained_fraction": float(retained),
        "retained_range_hz": [int(frequencies[start]), int(frequencies[stop])],
        "excluded_points": int(excluded.size),
        "excluded_intervals_hz": [
            [int(frequencies[a]), int(frequencies[b])]
            for a, b in contiguous_intervals(excluded)
        ],
        "maximum_excluded_gamma_magnitude": (
            float(magnitude[excluded].max()) if excluded.size else None
        ),
        "physical_samples_discarded_by_truncation": int(
            physical.sum() - physical[keep].sum()
        ),
        "reason": (
            "calibrated |Gamma| reached or exceeded 1, which is nonphysical for a "
            "passive antenna and indicates the fixture's calibrated dynamic range "
            "was exhausted; these frequencies are reported as very poor / outside "
            "calibrated dynamic range, never as a measured value"
        ),
    }
    (args.output_dir / "broadband-excluded.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="ascii"
    )
    print(
        f"{mode}: retained {keep.size}/{frequencies.size} points "
        f"({frequencies[start]/1e6:.3f}-{frequencies[stop]/1e6:.3f} MHz), "
        f"excluded {excluded.size}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
