# TH-D75A current operator configuration

This snapshot is based on the operator-supplied MCP-D75 file dated 2026-08-27.
Only ordinary repeater memories and the previously verified native D-STAR
repeater region were changed. Every other byte and all 400 typed settings come
from the supplied file.

## Exact artifacts

| Artifact | Purpose | SHA-256 |
|---|---|---|
| `radio-configs/thd75-current.d75` | Complete 500,736-byte MCP-D75 image, including every menu setting and memory region | `03BC9BA3ED4F94F9A3BE68D14ED9245CC1F5EB0C17C61637304F6EFBF4193F07` |
| `radio-configs/thd75-current-settings.json` | All 400 settings decoded by the pinned firmware-1.03 schema | Source hash embedded in the file |
| `radio-configs/thd75-power-on-KM7HKM.bmp` | 240x180, 16-bit RGB565 power-on image | `D299694C49260914F8BCE8D6A9E6836D07991A0975158DC8B66F3FA05375C785` |

The native image is intentionally tracked because the operator explicitly
requested a complete repository backup. It contains personal radio settings,
location information, callsigns, and the embedded power-on image. Do not copy
it to a public repository without reviewing that information.

The file passes the pinned `swiftraccoon/kenwood` typed parser, contains 545
ordinary memories, and round-trips byte-for-byte.

The exact supplied predecessor is backed up beside the working file on the Z
drive as `TH-D75 Configuration-before-sort-20260827.d75` (SHA-256
`00BB14C49220BA9C2E32AE875567F14E7B4A4DA2C721AE9EC04C23A8A8E5D377`).

## Operator memories placed in the 70 cm group

These three records were added manually after the original read-back. They are
now represented in the radio-specific catalog as `THD75USER` and reproduced by
the `thd75-ames-lake` plan in the existing `70cm Repeaters` physical group.

| Radio memory | Name | Receive | Transmit behavior | Mode | TX tone |
|---:|---|---:|---:|---|---:|
| 96 | N7QTREDMOND | 442.325 MHz | +5.000 MHz | FM | 103.5 Hz |
| 102 | W7AUX | 442.825 MHz | +5.000 MHz | FM | 103.5 Hz |
| 108 | VAERPT | 443.050 MHz | +5.000 MHz | FM | 103.5 Hz |

These values are operator-derived, not independently verified. In particular:

- Current WWARA-derived data agree with the +5 MHz inputs for N7QT and W7AUX,
  but describe N7QT as DMR and W7AUX as P25 rather than analog FM.

The repository preserves the radio's values exactly and keeps the conflicts
visible rather than presenting them as verified coordination facts.

## Newly added coordinated repeaters

A fresh WWARA extract found four WW7MST repeaters absent from the supplied
image. A fifth WW7MST channel, 444.825 MHz, was already present.

| Memory | Name | Receive | Input | Group | Tone |
|---:|---|---:|---:|---:|---:|
| 15 | WW7MSTSEATTLE | 146.900 MHz | 146.300 MHz | 0 | 103.5 Hz |
| 55 | WW7MSTSEATTLE | 224.680 MHz | 223.080 MHz | 1 | 103.5 Hz |
| 120 | WW7MSTSEATTLE | 443.550 MHz | 448.550 MHz | 2 | 103.5 Hz |
| 122 | WW7MSTTACOMA | 443.675 MHz | 448.675 MHz | 2 | 103.5 Hz |

The complete 172-memory repeater section is sorted by physical group, receive
frequency, then channel name. Group totals are 38 two-meter, 19 1.25-meter,
94 70-centimeter, and 21 D-STAR memories. Non-repeater memories retain their
original relative order after the repeater section.

The current WWARA source ZIP has SHA-256
`CE204B5E0DCB63FBCF65C3CCA110D4880E4CBED12852AC723E157E454820C6FE`.
No additional confirmed D-STAR repeaters were found in the internet
cross-check. The verified 21-entry local D-STAR list was restored because the
operator-supplied file's native repeater list was blank.

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

The supplied image also scan-locks AA7MI Nordland, K7NP University Place, and
K7LWH C Bellevue. These individual preferences are represented in the plan.

## Notable supplied settings

- Power-on bitmap replaced with the KM7HKM contact/reward graphic.
- Bluetooth enabled.
- Time-zone raw value changed from 36 to 28.
- Meter display set to Type 1.
- GPS position source changed to stored position 0.
- Stored position 0 named `Home`, with altitude and coordinates populated.
- APRS callsign changed from `NOCALL` to `KM7HKM`.
- APRS QSY-in-status enabled.
- APRS icon symbol changed from raw value 91 to 62.
- D-STAR GPS data-in-frame transmission enabled.
- Auto Power Off disabled and the power-on text message cleared.
- Group links 0 through 3 configured.
- Analog and digital scan resume set to Carrier Operate, with scan backlight enabled.
- QSO logging enabled and single-band display set to GPS altitude.
- APRS receive and transmit beeps disabled, one-line three-second interrupt
  display selected, and Voice Alert set to RX Only.

The six D-STAR `My Callsign` slots under Menu 610 remain empty in this image.
`KM7HKM` is currently configured for APRS only; normal D-STAR DV/DR
transmission remains unavailable until the callsign is also entered in Menu
610.

Exact raw values for all settings—not only the changed values—are retained in
the JSON snapshot and complete native image.
