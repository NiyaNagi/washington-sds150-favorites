"""Generate starter .FTX1 files for decoding unknown record fields.

Reverse engineering a field needs records that are identical except for that
one field. Rather than ask someone to hand-build a dozen memories in the
programmer, this writes the memories already in place - same frequency, same
everything, named for the value they should be given - so the only work left
is changing one column per row and saving.

Usage::

    python scripts/radios/make_ftx1_probe.py --out "Z:/path/to/folder"

Then, in the RT Systems programmer:

1. Open the generated file.
2. For each row, set the single column its name asks for.
3. Save it under the same name.

Bring the saved file back and ``compare_ftx1_files.py`` will show exactly
which byte changed for each value.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from wasds150.export.ftx1_file import Ftx1File  # noqa: E402
from wasds150.export.ftx1_target import _band_bases, _base_for, template_path  # noqa: E402

#: Every probe memory sits on the 2 m calling frequency. One frequency for
#: the whole file means any byte that differs between two records is caused
#: by the field being probed and nothing else.
PROBE_HZ = 146_520_000

#: Operating Mode values, in the order the vendor's own string table lists
#: them (FTX1_V5.dll at 0x533C8). The name records what to select so the
#: mapping is unambiguous when the file comes back.
MODE_ROWS = [
    "MODE-LSB",
    "MODE-USB",
    "MODE-CWL",
    "MODE-CWU",
    "MODE-AM",
    "MODE-AMN",
    "MODE-FM",
    "MODE-FMN",
    "MODE-DATAL",
    "MODE-DATAU",
    "MODE-DATAFM",
    "MODE-DFMN",
    "MODE-RTTYL",
    "MODE-RTTYU",
    "MODE-PSK",
    "MODE-C4FM",
    "MODE-VW",
    "MODE-AMS",
]

#: One row per field, each changing a single column away from the default.
#: BASE is deliberately first and left untouched: every other row is diffed
#: against it, so a byte that moves in BASE too is not the field we want.
FIELD_ROWS = [
    ("BASE", "leave every column at its default"),
    ("SKIP-ON", "tick Skip"),
    ("ATT-ON", "tick Attenuator"),
    ("IPO-AMP1", "set IPO to AMP1"),
    ("IPO-AMP2", "set IPO to AMP2"),
    ("AGC-FAST", "set AGC to Fast"),
    ("AGC-MID", "set AGC to Mid"),
    ("AGC-SLOW", "set AGC to Slow"),
    ("NB-ON", "turn Noise Blanker on"),
    ("MGRP-1", "set M-Grp to 1"),
    ("MGRP-5", "set M-Grp to 5"),
    ("DGID-TX7", "set Tx DGID to 07"),
    ("DGID-RX7", "set Rx DGID to 07"),
    ("SSB-NARROW", "tick SSB Narrow"),
    ("CW-NARROW", "tick CW Narrow"),
    ("RTTY-NARROW", "tick RTTY Narrow"),
    ("PKT-NARROW", "tick Packet Narrow"),
    ("DIG-NARROW", "tick Digital Narrow"),
    ("ANT-2", "set HF Antenna to Ant 2"),
    ("SUPERDX", "tick SuperDx"),
    ("BKIN-ON", "turn Bk-In on"),
    ("DNF-ON", "tick DNF"),
    ("NOTCH-ON", "tick Notch Filter"),
    ("WIDTH-ALT", "change Width to any other value"),
    ("CONTOUR-ALT", "change Contour/APF to any other value"),
    ("DNR-ALT", "change DNR Algorithm to any other value"),
    ("IFSHIFT-ALT", "change IF Shift Frequency to any other value"),
]

#: Tone Mode is the field that decides whether a repeater keys up, and whether
#: the receiver stays muted. The record stores 0, 1, 2 and 3; only 0 is known
#: for certain to mean "none". These rows pin the rest down.
TONE_ROWS = [
    ("TONE-NONE", "leave Tone Mode as None"),
    ("TONE-TONE", "set Tone Mode to Tone (encode only)"),
    ("TONE-TSQL", "set Tone Mode to Tone Sql / T Sql (encode and decode)"),
    ("TONE-DCS", "set Tone Mode to DCS"),
    ("TONE-REV", "set Tone Mode to Reverse Tone, if the list offers one"),
    ("TONE-OTHER1", "set Tone Mode to any remaining option in the list"),
    ("TONE-OTHER2", "set Tone Mode to another remaining option, if any"),
]


def build(rows, comments, template: pathlib.Path) -> Ftx1File:
    """A file whose memories differ only in name."""
    ftx1 = Ftx1File.load(template)
    bases = _band_bases(ftx1)
    base = _base_for(bases, PROBE_HZ / 1_000_000)

    for slot, (name, note) in enumerate(zip(rows, comments)):
        ftx1.records[slot] = base.patched(
            rx_hz=PROBE_HZ,
            tx_hz=PROBE_HZ,
            name=name[:12],
            comment=note[:79],
            in_use=True,
        )
    # Clear the rest so the file holds nothing but the probe rows.
    for slot in range(len(rows), 999):
        record = ftx1.records[slot]
        if not record.empty:
            ftx1.records[slot] = record.patched(in_use=False)
    return ftx1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="radio-configs/probes",
        help="Directory to write the probe files into",
    )
    parser.add_argument("--template", help="Override the .FTX1 template")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite probe files that already exist",
    )
    args = parser.parse_args(argv)

    template = pathlib.Path(args.template) if args.template else template_path()
    if not template.is_file():
        raise SystemExit(f"template not found at {template}")

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # A probe file is only useful once somebody has spent time editing it in
    # the programmer. Regenerating over the top destroys that work, and the
    # file looks superficially fine afterwards, so refuse by default.
    planned = ["ftx1-modes.FTX1", "ftx1-fields.FTX1", "ftx1-tones.FTX1"]
    existing = [name for name in planned if (out / name).is_file()]
    if existing and not args.force:
        raise SystemExit(
            "refusing to overwrite existing probe files:\n"
            + "\n".join(f"  {out / name}" for name in existing)
            + "\n\nThose may already hold edits made in the programmer. Move "
            "them aside,\nchoose a different --out, or pass --force if you "
            "are sure."
        )

    modes = build(
        MODE_ROWS,
        [f"set Operating Mode to {n.split('-', 1)[1]}" for n in MODE_ROWS],
        template,
    )
    modes_path = out / "ftx1-modes.FTX1"
    modes.save(modes_path)

    fields = build(
        [name for name, _ in FIELD_ROWS],
        [note for _, note in FIELD_ROWS],
        template,
    )
    fields_path = out / "ftx1-fields.FTX1"
    fields.save(fields_path)

    tones = build(
        [name for name, _ in TONE_ROWS],
        [note for _, note in TONE_ROWS],
        template,
    )
    tones_path = out / "ftx1-tones.FTX1"
    tones.save(tones_path)

    print(f"wrote {modes_path}  ({len(MODE_ROWS)} memories)")
    print(f"wrote {fields_path} ({len(FIELD_ROWS)} memories)")
    print(f"wrote {tones_path}  ({len(TONE_ROWS)} memories)")
    print()
    print("Open each in the RT Systems programmer. Every memory is already on")
    print(f"{PROBE_HZ / 1e6:.3f} MHz and its Comment column says what to change.")
    print("Change only that one column per row, save, and hand the files back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
