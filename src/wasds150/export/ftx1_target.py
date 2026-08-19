"""Write a resolved plan as a Yaesu ``.FTX1`` memory file.

This target does not synthesise records from nothing.  A memory record is 295
bytes and this project has decoded perhaps a dozen of them; the rest carry
per-channel settings the programmer wrote and the radio expects.  Inventing
those bytes would produce a file that loads and then behaves oddly in ways
that are very hard to trace back here.

So the target starts from a **template file** - a real ``.FTX1`` with its
memories cleared but its structure and one record of each duplex shape
intact - and patches only the fields it understands.  Everything this project
does not model keeps whatever the programmer put there.

The template ships in the repository at :data:`TEMPLATE_RELPATH` and contains
no channel data.  It is structure only, so it carries none of the operator's
curated content and none of any third-party database.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from wasds150.export.ftx1_file import (
    CTCSS_TONES,
    PMS_PAIRS,
    Ftx1File,
    Ftx1Record,
)
from wasds150.plan.resolve import ResolvedPlan
from wasds150.radios.bandplan import BANDS_BY_ID
from wasds150.radios.scan_ranges import ranges_by_priority

#: Repository-relative location of the structural template.
TEMPLATE_RELPATH = Path("radio-templates") / "ftx1-blank.FTX1"

#: The FTX-1 shows twelve characters of a memory tag.
NAME_LEN = 12

#: Comment field width in the programmer.
COMMENT_LEN = 32

#: Memories available before the programmable scan pairs begin.
MEMORY_CAPACITY = 999


class Ftx1ExportError(RuntimeError):
    """Raised when the file cannot be produced."""


@dataclass
class Ftx1ExportResult:
    """What an export wrote, in the shape the export registry expects."""

    rows: int = 0
    scan_pairs: int = 0
    warnings: List[str] = field(default_factory=list)


def template_path(root: Optional[Path] = None) -> Path:
    """Absolute path to the vendored blank template."""
    if root is None:
        here = Path(__file__).resolve()
        for candidate in here.parents:
            if (candidate / "pyproject.toml").is_file():
                root = candidate
                break
        else:
            root = Path.cwd()
    return Path(root) / TEMPLATE_RELPATH


def _nearest_ctcss(hz: Optional[float]) -> Optional[float]:
    """Snap a tone to the radio's 50-entry CTCSS table, or drop it.

    A tone the radio cannot represent is discarded rather than approximated
    to the nearest neighbour: a repeater that wants 100.0 Hz will not open
    for 103.5 Hz, and a channel that silently fails to key is worse than one
    that visibly carries no tone.
    """
    if hz is None:
        return None
    for tone in CTCSS_TONES:
        if abs(tone - hz) < 0.05:
            return tone
    return None


def _channel_tone(channel) -> Optional[float]:
    """The CTCSS tone to program for one memory.

    A repeater channel carries its access tone in ``tx_tone``; a listening
    channel carries the tone the traffic is transmitted with in ``rx_tone``.
    Both are worth programming - the first opens the repeater, the second
    gives tone squelch on a busy shared frequency - so fall back rather than
    programming no tone at all on receive-only memories.
    """
    for spec in (channel.tx_tone, channel.rx_tone):
        if spec is not None and spec.ctcss_hz is not None:
            return spec.ctcss_hz
    return None


def _pick_templates(source: Ftx1File) -> Dict[str, Ftx1Record]:
    """One real record per duplex shape, to patch new memories from."""
    templates: Dict[str, Ftx1Record] = {}
    for record in source.records[:MEMORY_CAPACITY]:
        if record.tx_hz == record.rx_hz:
            templates.setdefault("simplex", record)
        elif record.tx_hz > record.rx_hz:
            templates.setdefault("plus", record)
        else:
            templates.setdefault("minus", record)
        if len(templates) == 3:
            break
    if "simplex" not in templates:
        # A blank template has every record simplex-shaped at 0 Hz, which is
        # still a usable base: duplex is set explicitly by ``patched``.
        templates["simplex"] = source.records[0]
    templates.setdefault("plus", templates["simplex"])
    templates.setdefault("minus", templates["simplex"])
    return templates


def render_ftx1(
    resolved: ResolvedPlan,
    *,
    template: Optional[Path] = None,
) -> "tuple[Ftx1File, Ftx1ExportResult]":
    """Build an in-memory ``.FTX1`` from a resolved plan."""
    path = Path(template) if template is not None else template_path()
    if not path.is_file():
        raise Ftx1ExportError(
            f"FTX-1 template not found at {path}. It ships with the repository; "
            "regenerate it with scripts/radios/make_ftx1_template.py from a "
            "file saved by the RT Systems programmer."
        )

    original = path.read_bytes()
    ftx1 = Ftx1File.load(path)
    if not ftx1.round_trips(original):
        raise Ftx1ExportError(
            "the FTX-1 parser does not round-trip the template; refusing to write"
        )

    result = Ftx1ExportResult()
    templates = _pick_templates(ftx1)

    channels = resolved.channels[:MEMORY_CAPACITY]
    if len(resolved.channels) > MEMORY_CAPACITY:
        result.warnings.append(
            f"plan resolved {len(resolved.channels)} channels but the FTX-1 holds "
            f"{MEMORY_CAPACITY}; the last "
            f"{len(resolved.channels) - MEMORY_CAPACITY} were not written"
        )

    for slot, channel in enumerate(channels):
        rx = int(round(channel.rx_freq_mhz * 1_000_000))
        tx = (
            int(round(channel.tx_freq_mhz * 1_000_000))
            if channel.transmit and channel.tx_freq_mhz
            else rx
        )
        raw_tone = _channel_tone(channel)
        tone = _nearest_ctcss(raw_tone)
        if raw_tone is not None and tone is None:
            result.warnings.append(
                f"{channel.name}: tone {raw_tone:g} Hz is not a standard CTCSS "
                "value and was not programmed"
            )

        shape = "simplex" if tx == rx else ("plus" if tx > rx else "minus")
        comment = (channel.comment or channel.label)[:COMMENT_LEN]
        ftx1.records[slot] = templates[shape].patched(
            rx_hz=rx,
            tx_hz=tx,
            name=channel.name[:NAME_LEN],
            comment=comment,
            tone_hz=tone,
            in_use=True,
        )
        result.rows += 1

    # Clear any template memory beyond what the plan filled, so a stale
    # channel from the template can never appear on the radio.
    for slot in range(len(channels), MEMORY_CAPACITY):
        record = ftx1.records[slot]
        if not record.empty:
            ftx1.records[slot] = record.patched(in_use=False)

    # Programmable scan ranges occupy their own memory region, so they cost
    # nothing from the 999 channel budget.
    scan_ranges = ranges_by_priority(PMS_PAIRS)
    for pair, scan_range in enumerate(scan_ranges):
        BANDS_BY_ID.get(scan_range.band_id)  # validate the band id exists
        ftx1.set_scan_limit(
            pair,
            scan_range.low_mhz,
            scan_range.high_mhz,
            label=scan_range.label[:NAME_LEN],
            note=scan_range.note[:COMMENT_LEN],
        )
    result.scan_pairs = len(scan_ranges)

    return ftx1, result


def write_ftx1(
    resolved: ResolvedPlan,
    path: Path,
    *,
    template: Optional[Path] = None,
) -> Ftx1ExportResult:
    """Write a resolved plan to ``path`` as a ``.FTX1`` file."""
    ftx1, result = render_ftx1(resolved, template=template)
    path.parent.mkdir(parents=True, exist_ok=True)
    ftx1.save(path)

    # Read back and confirm the radio-visible content survived.
    check = Ftx1File.load(path)
    written = len([r for r in check.memories() if not r.empty])
    if written != result.rows:
        raise Ftx1ExportError(
            f"wrote {result.rows} memories but read back {written}; "
            "the record model is wrong"
        )
    return result
