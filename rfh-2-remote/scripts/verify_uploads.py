#!/usr/bin/env python3
"""Fab-side acceptance checks for the three RFH-2 upload archives.

Deliberately dependency-free: this re-reads the archives with a parser that
shares no code with whatever produced them, so a bug in the generator cannot
hide behind the same bug in the checker. `scripts/accept_zips.py` does the
same job via gerbonara if you want a third opinion.

Checks per archive: required layer set, flat structure, drill hole count and
diameters against JLCPCB's 0.3-6.3 mm plated window, and board outline extent.
Then checks the four 5.0 mm mounting holes agree across all three boards.
"""
from __future__ import annotations

import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
UPLOAD = os.path.join(PROJ, "jlcpcb-upload")

ARCHIVES = [
    ("cover", "JLCPCB-1-RFH-2-cover.zip", 4),
    ("mainboard", "JLCPCB-2-RFH-2-mainboard.zip", 122),
    ("bottom", "JLCPCB-3-RFH-2-bottom.zip", 4),
]

# JLCPCB plated-hole window.
MIN_DRILL_MM = 0.30
MAX_DRILL_MM = 6.30

# Suffixes that identify each required layer, lowercased.
LAYER_PATTERNS = {
    "top copper": (".gtl", "copper_top.gbr"),
    "bottom copper": (".gbl", "copper_bottom.gbr"),
    "top mask": (".gts", "soldermask_top.gbr"),
    "bottom mask": (".gbs", "soldermask_bottom.gbr"),
    "outline": (".gko", "profile.gbr"),
}
SILK_PATTERNS = (".gto", ".gbo", "silkscreen_top.gbr", "silkscreen_bottom.gbr")
DRILL_PATTERNS = (".drl", ".xln", ".txt")

failures: list[str] = []


def check(tag: str, name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   ({detail})" if detail else ""))
    if not ok:
        failures.append(f"{tag}: {name}")


def parse_excellon(text: str) -> list[tuple[float, float, float]]:
    """Return [(x_mm, y_mm, diameter_mm)] from an Excellon drill program."""
    metric = "METRIC" in text
    decimals = 3
    fmt = re.search(r"METRIC\s*,\s*[LT]Z\s*,\s*(\d+)\.(\d+)", text)
    if fmt:
        decimals = int(len(fmt.group(2)))

    tools: dict[str, float] = {}
    for match in re.finditer(r"^T(\d+)C([\d.]+)", text, re.MULTILINE):
        tools[str(int(match.group(1)))] = float(match.group(2))

    def scale(raw: str) -> float:
        if "." in raw:
            return float(raw)
        negative = raw.startswith("-")
        digits = raw.lstrip("+-")
        return (-1 if negative else 1) * int(digits) / (10**decimals)

    holes: list[tuple[float, float, float]] = []
    current: float | None = None
    for line in text.splitlines():
        line = line.strip()
        select = re.fullmatch(r"T(\d+)", line)
        if select:
            current = tools.get(str(int(select.group(1))))
            continue
        coord = re.fullmatch(r"X(-?[\d.]+)Y(-?[\d.]+)", line)
        if coord and current:
            holes.append((scale(coord.group(1)), scale(coord.group(2)), current))
    if not metric:
        holes = [(x * 25.4, y * 25.4, d * 25.4) for x, y, d in holes]
    return holes


def parse_gerber_extent(text: str) -> tuple[float, float, float, float] | None:
    """Return (min_x, min_y, max_x, max_y) in mm from a gerber's coordinates."""
    fs = re.search(r"%FSLA?X(\d)(\d)Y(\d)(\d)\*%", text)
    if not fs:
        return None
    frac = int(fs.group(2))
    unit_mm = "%MOMM*%" in text
    xs: list[float] = []
    ys: list[float] = []
    last_x = last_y = 0.0

    def scale(raw: str) -> float:
        negative = raw.startswith("-")
        digits = raw.lstrip("+-")
        return (-1 if negative else 1) * int(digits) / (10**frac)

    for match in re.finditer(r"(?:X(-?\d+))?(?:Y(-?\d+))?D0[123]\*", text):
        if match.group(1) is None and match.group(2) is None:
            continue
        if match.group(1) is not None:
            last_x = scale(match.group(1))
        if match.group(2) is not None:
            last_y = scale(match.group(2))
        xs.append(last_x)
        ys.append(last_y)
    if not xs:
        return None
    extent = (min(xs), min(ys), max(xs), max(ys))
    if not unit_mm:
        extent = tuple(value * 25.4 for value in extent)  # type: ignore[assignment]
    return extent  # type: ignore[return-value]


def main() -> int:
    mount_sets: dict[str, list[tuple[float, float]]] = {}

    for tag, filename, expected_holes in ARCHIVES:
        path = os.path.join(UPLOAD, filename)
        print(f"\n=== {tag}  ({filename}, {os.path.getsize(path) / 1024:.0f} kB) ===")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            contents = {name: archive.read(name) for name in names}

        check(tag, "flat archive, no directories", not any(n.endswith("/") for n in names))
        lower = {name.lower(): name for name in names}

        for label, patterns in LAYER_PATTERNS.items():
            present = any(n.endswith(patterns) for n in lower)
            check(tag, f"layer present: {label}", present)
        check(tag, "silkscreen present", any(n.endswith(SILK_PATTERNS) for n in lower))

        drills = [orig for low, orig in lower.items() if low.endswith(DRILL_PATTERNS)]
        check(tag, "exactly one drill file", len(drills) == 1, ", ".join(drills))
        if len(drills) != 1:
            continue

        holes = parse_excellon(contents[drills[0]].decode("utf-8", "replace"))
        check(tag, f"drill hole count == {expected_holes}", len(holes) == expected_holes,
              f"{len(holes)} holes")

        diameters = sorted({round(d, 3) for _, _, d in holes})
        in_window = all(MIN_DRILL_MM <= d <= MAX_DRILL_MM for d in diameters)
        check(tag, "all drills within JLCPCB 0.3-6.3 mm", in_window,
              f"{diameters[0]:.3f}-{diameters[-1]:.3f} mm, {len(diameters)} sizes")

        mount_sets[tag] = sorted(
            (round(x, 3), round(y, 3)) for x, y, d in holes if abs(d - 5.0) < 1e-6
        )
        check(tag, "four 5.00 mm mounting holes", len(mount_sets[tag]) == 4,
              f"{len(mount_sets[tag])}")

        outline_name = next(
            (orig for low, orig in lower.items()
             if low.endswith(LAYER_PATTERNS["outline"])), None)
        if outline_name:
            extent = parse_gerber_extent(contents[outline_name].decode("utf-8", "replace"))
            if extent:
                width = extent[2] - extent[0]
                height = extent[3] - extent[1]
                check(tag, "outline within 76.0-76.5 x 90.0-90.5 mm",
                      76.0 <= width <= 76.5 and 90.0 <= height <= 90.5,
                      f"{width:.3f} x {height:.3f} mm")

    print("\n=== cross-board ===")
    if len(mount_sets) == len(ARCHIVES):
        reference = mount_sets["mainboard"]
        for tag, coords in mount_sets.items():
            check("stack", f"{tag} mounting holes match mainboard",
                  coords == reference, f"{coords}")
    else:
        check("stack", "mounting holes recovered for all three boards", False)

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
