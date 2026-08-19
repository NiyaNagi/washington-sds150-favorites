"""Generate ``wasds150/catalog/ftx1_import.py`` from an RT Systems file.

The operator's own FTX-1 file is a curated data set - statewide amateur
repeaters, the full marine channel list, business itinerant channels - that
took real effort to assemble and that the project's automated sources do not
fully cover.  This folds the parts the catalog is missing into the catalog,
so every radio benefits rather than just the one the file was written for.

Matching is on frequency **and** name, not frequency alone: two repeaters on
the same output in different towns are different channels, and collapsing
them would silently lose one.

Run this after refreshing the source file; the generated module is committed
so the catalog does not depend on a path outside the repository.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys
import unicodedata

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.export.ftx1_file import Ftx1File
from wasds150.generate.pipeline import apply_profile
from wasds150.models.catalog import Catalog
from wasds150.plan.resolve import iter_catalog_channels

DEFAULT_SOURCE = r"Z:\Texts\HAM\Radio Programming\FTX1 WA.FTX1"
DEFAULT_OUT = "src/wasds150/catalog/ftx1_import.py"

CTCSS_TONES = [
    67.0, 69.3, 71.9, 74.4, 77.0, 79.7, 82.5, 85.4, 88.5, 91.5,
    94.8, 97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3,
    131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2, 165.5, 167.9,
    171.3, 173.8, 177.3, 179.9, 183.5, 186.2, 189.9, 192.8, 196.6, 199.5,
    203.5, 206.5, 210.7, 218.1, 225.7, 229.1, 233.6, 241.8, 250.3, 254.1,
]
OFF_TONE_MODE = 0x2C
OFF_TX_TONE = 0x2D

_CALLSIGN = re.compile(r"^[A-Z]{1,2}[0-9][A-Z]{1,3}$")


def ascii_only(text: str) -> str:
    """Fold to plain ASCII; the catalog requires it and so does every radio."""
    normalized = unicodedata.normalize("NFKD", text)
    cleaned = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(cleaned.split())


def classify(record) -> str:
    mhz = record.rx_mhz
    name = record.name.upper()
    if 144 <= mhz <= 148:
        return "Amateur 2 Meter Repeaters"
    if 420 <= mhz <= 450:
        return "Amateur 70 Centimeter Repeaters"
    if 50 <= mhz <= 54:
        return "Amateur 6 Meter"
    if 156 <= mhz <= 163:
        return "Marine VHF"
    if name.startswith(("FRS", "GMRS", "MURS")):
        return "Personal Radio Services"
    if 450 <= mhz <= 470:
        return "Business and Itinerant UHF"
    if 162.4 <= mhz <= 162.55:
        return "NOAA Weather"
    return "Other"


def tone_of(record) -> str:
    if record.raw[OFF_TONE_MODE] == 0:
        return ""
    index = record.raw[OFF_TX_TONE]
    if index >= len(CTCSS_TONES):
        return ""
    return f"TONE=C{CTCSS_TONES[index]:g}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--home", default=".wasds150-home")
    args = parser.parse_args(argv)

    ftx1 = Ftx1File.load(pathlib.Path(args.source))
    memories = [r for r in ftx1.records[:999] if not r.empty]

    ctx = build_context(AppConfig(home=pathlib.Path(args.home)))
    catalog = Catalog(
        favorites=apply_profile(ctx.catalog, ctx.load_profile()).enabled_favorites
    )
    known = set()
    for favorite_list, _sys, _dept, channel in iter_catalog_channels(catalog):
        # The generated list is itself in the catalog once this has run, so it
        # has to be excluded or a regeneration would match its own output and
        # produce an empty file.
        if favorite_list.favorite_key == "FTX01":
            continue
        if channel.freq_mhz:
            known.add((round(channel.freq_mhz, 4), ascii_only(channel.label).upper()))
    known_freqs = {freq for freq, _name in known}

    new = []
    for record in memories:
        freq = round(record.rx_mhz, 4)
        name = ascii_only(record.name).upper()
        if (freq, name) in known:
            continue
        # A bare callsign on an amateur frequency identifies a distinct
        # repeater even when the catalog already knows that frequency.
        is_repeater = _CALLSIGN.match(name) and record.tx_hz != record.rx_hz
        if freq in known_freqs and not is_repeater:
            continue
        new.append(record)

    grouped = collections.defaultdict(list)
    for record in new:
        grouped[classify(record)].append(record)

    # A linked system uses one callsign on one output from several sites, so
    # callsign plus frequency is not unique. The site is in the comment, which
    # is exactly what tells the two apart on the air.
    labels = {}
    for group, records in grouped.items():
        seen = collections.Counter()
        for record in records:
            base = ascii_only(record.name)
            key = (group, base, round(record.rx_mhz, 4))
            seen[key] += 1
            if seen[key] == 1:
                labels[id(record)] = base
                continue
            site = ascii_only(record.comment).split(",")[0].strip()
            candidate = f"{base} {site}" if site else f"{base} {seen[key]}"
            labels[id(record)] = candidate

    print(f"source memories: {len(memories)}")
    print(f"new to the catalog: {len(new)}")
    for group, records in sorted(grouped.items()):
        print(f"  {group:<34} {len(records)}")

    lines = [
        '"""Channels imported from the operator\'s RT Systems FTX-1 file.',
        "",
        "GENERATED FILE - do not edit by hand.",
        "Regenerate with scripts/radios/import_ftx1_to_catalog.py",
        "",
        "These are channels the project's own sources did not supply: amateur",
        "repeaters across eastern Washington that the WWARA extract does not",
        "cover, the full marine VHF channel list, and business itinerant",
        "channels. Frequencies, repeater inputs and CTCSS tones are as recorded",
        "in the operator's file; nothing here has been inferred.",
        '"""',
        "from __future__ import annotations",
        "",
        "from typing import List",
        "",
        "from wasds150.models.catalog import Channel, Department, FavoritesList, System",
        "from wasds150.util.hashing import stable_id",
        "",
        "SOURCE = \"operator-supplied RT Systems FTX-1 file\"",
        "",
        "#: (label, rx_mhz, tx_mhz, tone, mode, note)",
        "CHANNELS = {",
    ]
    for group, records in sorted(grouped.items()):
        lines.append(f"    {group!r}: (")
        for record in sorted(records, key=lambda r: r.rx_mhz):
            tx = record.tx_mhz if record.tx_hz != record.rx_hz else None
            note = ascii_only(record.comment)
            mode = "FM" if record.rx_mhz > 30 else "USB"
            lines.append(
                f"        ({labels[id(record)]!r}, {record.rx_mhz!r}, "
                f"{tx!r}, {tone_of(record)!r}, {mode!r}, {note!r}),"
            )
        lines.append("    ),")
    lines.extend(
        [
            "}",
            "",
            "",
            "def system() -> System:",
            "    departments = []",
            "    for group, rows in CHANNELS.items():",
            "        channels = [",
            "            Channel(",
            "                id=stable_id(f'ftx1-import:{group}:{label}:{rx}', kind='channel'),",
            "                label=label,",
            "                freq_mhz=rx,",
            "                tx_freq_mhz=tx,",
            "                mode=mode,",
            "                tone=tone,",
            "                tx_tone=tone,",
            "                service_type=13 if 'Amateur' in group else 21,",
            "                notes=f'{note} ({SOURCE})' if note else SOURCE,",
            "            )",
            "            for label, rx, tx, tone, mode, note in rows",
            "        ]",
            "        departments.append(",
            "            Department(",
            "                id=stable_id(f'ftx1-import:dept:{group}', kind='department'),",
            "                label=group,",
            "                channels=channels,",
            "            )",
            "        )",
            "    return System(",
            "        id=stable_id('ftx1-import:system', kind='system'),",
            "        label='Imported from the operator FTX-1 file',",
            "        departments=departments,",
            "    )",
            "",
            "",
            "def favorite() -> FavoritesList:",
            "    return FavoritesList(",
            "        id=stable_id('ftx1-import:FTX01', kind='favorites-list'),",
            "        slug='ftx01',",
            "        favorite_key='FTX01',",
            "        favorite_name='Operator FTX-1 Import',",
            "        region='Washington statewide',",
            "        counties='All 39 counties',",
            "        scenario='Statewide amateur repeaters, marine VHF and business itinerant channels',",
            "        source_type='conventional, operator supplied',",
            "        system_or_category='Channels imported from the operator RT Systems FTX-1 file',",
            "        sites_or_coverage='Statewide',",
            "        departments_or_channels='Amateur 2m and 70cm repeaters, marine VHF, business itinerant',",
            "        mode='FM/NFM',",
            "        monitorability='Analog conventional',",
            "        upgrade_required='None',",
            "        source_url='',",
            "        notes=(",
            "            'Imported from the operator RT Systems FTX-1 file. Only channels the '",
            "            'catalog did not already carry are included; amateur repeaters are '",
            "            'matched on callsign as well as frequency so two machines sharing an '",
            "            'output are both kept.'",
            "        ),",
            "        systems=[system()],",
            "    )",
            "",
            "",
            "def favorites() -> List[FavoritesList]:",
            "    return [favorite()]",
            "",
        ]
    )

    out = pathlib.Path(args.out)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
