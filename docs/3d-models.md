# 3D models: moved

The printable mounts, the enclosure and the parametric modelling method have moved to their own repository:

**https://github.com/NiyaNagi/alturas-labs-models** (private)

They were developed here in August and September 2026 and split out, with the full history of every
file, on 2026-09-10. The work covered:
- the SDS150 visor mounts and Peak Design bracket;
- the EFHW antenna enclosure;
- the Peak Design radio standoff;
- the ProClip plates;
- a hex antenna insulator.

The OpenSCAD sources, the `scripts/cad/` verification pipeline and the radio hardware measurement
registry all went with them.

## Why they moved

They use a different toolchain: OpenSCAD and a trimesh/manifold3d environment, versus the
zero-dependency `wasds150` package. They serve a different audience: mechanical design and
3D printing, versus radio programming. They now sit alongside the rest of the Alturas Labs model
library, including the GarageBuddy product line. Nothing in `src/`, `tests/` or `pyproject.toml`
ever depended on them.

## What this repository still owes it

Nothing. The radio dimensions the mounts need (lug, pedestal, envelopes) now live in that
repository's `objects/` library. If this repository ever learns a new physical fact about a radio,
record it there.

## What stayed here

- `rfh-2-remote/`: the GPL-3.0 RFH-2 keypad PCB and its generated cover plates. It uses a different
  toolchain (gerbonara) and license, and is not part of this move.
- A local `.venv-cad/` directory, if you have one, is no longer used by anything here and can be deleted.

Moved: `models/`, `scripts/cad/`, `docs/modelling-method.md`, `docs/efhw-enclosure.md`,
`docs/pd-capture-bracket.md`, `docs/peak-design-radio-standoff.md`,
`docs/peak-design-radio-standoff-plan.md`, `docs/proclip-radio-mounts.md` and
`docs/radio-hardware-measurements.md`.
