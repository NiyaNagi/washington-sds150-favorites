#!/usr/bin/env python3
"""Render the cover and back plate to the PNGs used in the documentation.

Parses the shipped gerbers rather than any in-memory model, so the images
cannot drift from the files a fab would receive. The back plate silkscreen
lives on the bottom layer and is mirrored in the gerber, so it is un-mirrored
here to show what you actually read when the unit is turned over.
"""
from __future__ import annotations

import os
import re
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
GERBERS = os.path.join(PROJ, "gerbers")
IMAGES = os.path.join(PROJ, "images")

BW, BH = 76.0, 90.0
SCALE = 14
MASK = (12, 78, 45)
SILK = (255, 255, 255)
HOLE = (22, 22, 22)
RING = (208, 180, 40)

MOUNT = [(3.572, 3.826), (72.360, 3.937), (3.572, 85.826), (72.360, 85.937)]


def parse(path: str) -> tuple[list, list, list]:
    """Return (polylines, filled regions, arcs) in mm."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()

    polylines: list = []
    regions: list = []
    arcs: list = []
    current: list = []
    region_pts: list = []
    x = y = 0.0
    in_region = False

    def num(raw: str) -> float:
        return int(raw) / 10000.0

    for line in text.splitlines():
        line = line.strip()
        if line == "G36*":
            in_region, region_pts = True, []
            continue
        if line == "G37*":
            if len(region_pts) > 2:
                regions.append(region_pts)
            in_region = False
            continue
        arc = re.match(r"G03X(-?\d+)Y(-?\d+)I(-?\d+)J(-?\d+)D01\*", line)
        if arc:
            i = num(arc.group(3))
            arcs.append((x + i, y, abs(i)))
            continue
        move = re.match(r"(?:X(-?\d+))?(?:Y(-?\d+))?D0([123])\*", line)
        if not move:
            continue
        if move.group(1) is not None:
            x = num(move.group(1))
        if move.group(2) is not None:
            y = num(move.group(2))
        op = move.group(3)
        if in_region:
            region_pts.append((x, y))
        elif op == "2":
            if len(current) > 1:
                polylines.append(current)
            current = [(x, y)]
        elif op == "1":
            current.append((x, y))
    if len(current) > 1:
        polylines.append(current)
    return polylines, regions, arcs


def render(folder: str, silk_ext: str, mirror: bool) -> Image.Image:
    base = os.path.join(GERBERS, folder)
    stem = next(f[: -len(silk_ext)] for f in os.listdir(base) if f.endswith(silk_ext))
    lines, regions, _ = parse(os.path.join(base, stem + silk_ext))
    _, _, cutouts = parse(os.path.join(base, stem + ".GKO"))

    img = Image.new("RGB", (int(BW * SCALE), int(BH * SCALE)), MASK)
    draw = ImageDraw.Draw(img)

    def px(x: float, y: float) -> tuple[float, float]:
        if mirror:
            x = BW - x
        return x * SCALE, (BH - y) * SCALE

    for poly in lines:
        draw.line([px(*p) for p in poly], fill=SILK, width=2)
    for reg in regions:
        draw.polygon([px(*p) for p in reg], fill=SILK)
    for cx, cy, r in cutouts:
        cxp, cyp = px(cx, cy)
        rr = r * SCALE
        draw.ellipse([cxp - rr, cyp - rr, cxp + rr, cyp + rr],
                     fill=HOLE, outline=RING, width=2)
    for hx, hy in MOUNT:
        cxp, cyp = px(hx, hy)
        rr = 2.5 * SCALE
        draw.ellipse([cxp - rr, cyp - rr, cxp + rr, cyp + rr],
                     fill=HOLE, outline=RING, width=2)
    return img


def main() -> int:
    os.makedirs(IMAGES, exist_ok=True)

    cover = render("cover", ".GTO", mirror=False)
    back = render("bottom", ".GBO", mirror=True)

    cover_path = os.path.join(IMAGES, "cover-render.png")
    cover.save(cover_path)
    print(f"wrote {cover_path}  {cover.size[0]}x{cover.size[1]}")

    pad = 30
    combo = Image.new("RGB", (cover.width * 2 + pad * 3, cover.height + pad * 2),
                      (20, 20, 20))
    combo.paste(cover, (pad, pad))
    combo.paste(back, (pad * 2 + cover.width, pad))
    combo_path = os.path.join(IMAGES, "front-and-back.png")
    combo.save(combo_path)
    print(f"wrote {combo_path}  {combo.size[0]}x{combo.size[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
