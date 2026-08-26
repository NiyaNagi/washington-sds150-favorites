# TH-D75A current operator configuration

This snapshot captures the operator's MCP-D75 file after manual edits on
2026-08-26. It supersedes the initial 538-memory hardware write documented in
the Ames Lake loadout guide.

## Exact artifacts

| Artifact | Purpose | SHA-256 |
|---|---|---|
| `radio-configs/thd75-current.d75` | Complete 500,736-byte MCP-D75 image, including every menu setting and memory region | `25E7330FA52E7AE50E4CE5C0406E41955C06FC0C3A7639C29968B6AF1B85116A` |
| `radio-configs/thd75-current-settings.json` | All 400 settings decoded by the pinned firmware-1.03 schema | Source hash embedded in the file |
| `radio-configs/thd75-power-on-KM7HKM.bmp` | 240x180, 16-bit RGB565 power-on image | `D299694C49260914F8BCE8D6A9E6836D07991A0975158DC8B66F3FA05375C785` |

The native image is intentionally tracked because the operator explicitly
requested a complete repository backup. It contains personal radio settings,
location information, callsigns, and the embedded power-on image. Do not copy
it to a public repository without reviewing that information.

The file passes the pinned `swiftraccoon/kenwood` typed parser, contains 541
ordinary memories, and round-trips byte-for-byte.

## Newly recovered memories

These three records were added manually after the original read-back. They are
now represented in the radio-specific catalog as `THD75USER` and reproduced by
the `thd75-ames-lake` plan in the existing `70cm Repeaters` physical group.

| Radio memory | Name | Receive | Transmit behavior | Mode | TX tone |
|---:|---|---:|---:|---|---:|
| 538 | VAERPT | 443.050 MHz | +0.600 MHz | FM | 103.5 Hz |
| 539 | N7QTREDMOND | 442.325 MHz | +0.600 MHz | FM | 103.5 Hz |
| 540 | W7AUX | 442.825 MHz | Simplex | FM | 103.5 Hz |

These values are operator-derived, not independently verified. In particular:

- Current WWARA-derived data describe N7QT at 442.325 MHz as DMR with a +5 MHz
  input, not analog FM with a 600 kHz offset.
- Current public data describe W7AUX at 442.825 MHz as P25. The operator image
  stores it as FM simplex.

The repository preserves the radio's values exactly and keeps the conflicts
visible rather than presenting them as verified coordination facts.

## Recovered channel preferences

All six NOAA weather memories are now scan-locked. The channels remain
available for manual recall but normal memory/group scans skip them. This is
represented by `skip_scan=True` in the plan.

The current file stores the two VHF satellite receive memories `SSTV` and
`AO91` with their odd-split transmit value normalized back to the receive
frequency. The generated plan deliberately retains its safer 410.000 MHz
out-of-amateur-band transmit-inhibit split. The exact native image remains the
authoritative record of the operator's current setting; regeneration chooses
the safer behavior rather than enabling accidental satellite-downlink
transmission.

## Typed settings changed since the first read-back

The typed schema found 17 changed settings:

- Power-on bitmap replaced with the KM7HKM contact/reward graphic.
- Bluetooth enabled.
- Time-zone raw value changed from 36 to 28.
- Meter display changed from Type 1 to Type 2.
- GPS position source changed to stored position 0.
- Stored position 0 named `Home`, with altitude and coordinates populated.
- APRS callsign changed from `NOCALL` to `KM7HKM`.
- APRS QSY-in-status enabled.
- APRS icon symbol changed from raw value 91 to 62.
- D-STAR GPS data-in-frame transmission enabled.

The six D-STAR `My Callsign` slots under Menu 610 remain empty in this image.
`KM7HKM` is currently configured for APRS only; normal D-STAR DV/DR
transmission remains unavailable until the callsign is also entered in Menu
610.

Exact raw values for all settings—not only the changed values—are retained in
the JSON snapshot and complete native image.
