# Kenwood TH-D75A — Ames Lake 50-mile loadout

## Result

The connected North American TH-D75A was identified on COM11 and read with
Kenwood MCP-D75 1.00 before any write. Its firmware is 1.03. The exact
pre-change file is private under `radio-backups/th-d75/`; its SHA-256 is:

`B9AEFA8D9F5C153149059D98464E5EA05A64BB95A938B4D9FE8E55C35BFE0886`

The initial final file was `radio-configs/thd75-ames-lake.d75`. It contains 538 ordinary
memories in 21 named groups and 21 nearby entries in the radio's separate
native D-STAR repeater list. Final SHA-256:

`C6171D3F7D9DE6A4192327ADB41BEAA95546F53E9893FE649118C56CDFDF726F`

The final file was accepted by MCP-D75 without a frequency-rounding warning,
reported 462 free memories, and round-tripped through the independent
hardware-tested `swiftraccoon/kenwood` TH-D75 parser with all 538 records valid.
MCP-D75 then wrote the connected radio to 100% with “Writing completed.” A
full read-back reached 100% with “Reading completed.” and reproduced all 538
ordinary-memory fields with zero semantic differences. The private read-back
SHA-256 is:

`A3F7AA7DF0C0FAE5D44766D8AFB1561BAC9A05798B2EB60650D3D9A148F8351E`

The operator subsequently added three memories and updated personal settings.
The current 545-memory image, complete typed settings snapshot and exact
changes are documented in [the current configuration](th-d75-current-configuration.md).

## What is loaded

| Group | Memories |
|---|---:|
| 2 m analog repeaters within 50 miles | 37 |
| 1.25 m analog repeaters within 50 miles | 18 |
| 70 cm analog repeaters within 50 miles | 89 |
| D-STAR repeaters within 50 miles | 21 |
| Amateur calling/simplex | 4 |
| 6 m and 10 m amateur receive | 18 |
| Satellites and ISS | 5 |
| NOAA Weather Radio | 6 |
| SAR and interoperability | 24 |
| Wildland fire | 57 |
| Marine, VTS, ferry and USCG | 23 |
| Civil aviation AM | 30 |
| Military aviation AM | 23 |
| Rail and transit | 7 |
| GMRS/FRS receive | 22 |
| MURS and business receive | 18 |
| CB AM receive | 40 |
| FM broadcast WFM | 32 |
| AM broadcast | 29 |
| HF time standards | 8 |
| HF emergency and utility | 27 |
| Operator additions in the 70 cm group | 3 |

The broadcast groups are new catalog coverage derived from the FCC's current
AM/FM radius queries. The D-STAR entries are from Kenwood's
`KWD_20260823_E.tsv`, filtered to the TH-D75A model, 0.1–524 MHz receive
coverage, Washington, and 50 miles from 47.633966, -121.960584.

## Capability decisions

The TH-D75A profile reflects the physical radio and Kenwood documentation:

- 1,000 ordinary memories and 30 named groups.
- A separate 1,500-entry D-STAR repeater list.
- Transmit on 144–148, 222–225 and 430–450 MHz.
- Band B receive from 0.1–524 MHz.
- FM, NFM, D-STAR DV/DR, AM, USB, LSB, CW and WFM.
- No P25, DMR, NXDN, System Fusion voice, or trunk tracking.

P25/DMR/NXDN channels and trunked talkgroups are dropped rather than relabeled
as analog. Non-amateur services are outside the hardware transmit bands and
are receive-only. Receive-only amateur satellite downlinks use an odd split to
410.000 MHz, which MCP-D75 preserves but the North American radio cannot
transmit on; this prevents an accidental PTT on a satellite downlink.

No APRS or D-STAR operator callsign was invented. Existing APRS, MYCALL,
Bluetooth, GPS, display, audio and menu settings were preserved from the exact
radio read. APRS transmit remains unavailable until the operator enters a
licensed callsign on the radio.

## Data and software provenance

- Kenwood MCP-D75 1.00: official hardware read, import, save and write path.
- Kenwood USB CDC driver 1.00: binds the radio as `TH-D75 (COM11)`.
- Kenwood TH-D75 in-depth manual: receive/transmit/mode and memory capacities.
- Kenwood worldwide D-STAR list dated 2026-08-23.
- WWARA nightly coordination extract: local analog repeater sites, offsets and
  access tones.
- FCC AM/FM Query: licensed broadcast transmitters within 50 miles.
- NOAA/NWS and USCG/NAVCEN: weather and marine channel allocations.
- FAA/NASR and the project's existing public-source catalog: aviation and
  other conventional receive services.
- `swiftraccoon/kenwood` commit
  `2eb932db81ac82b53e8a2c99ab8bca99d5b22d4a`: independent typed validation of
  the firmware-1.03 MCP image and 40-byte memory records.

## Regeneration workflow

1. Read the radio with MCP-D75 and place the private backup in
   `radio-backups/th-d75/`.
2. Export the plan with target `thd75-file`.
3. In MCP-D75, open the generated file and import the filtered official TSV
   under **Repeater List** for **TH-D75A (K-type/U.S.A. and Canada)**.
4. Save from MCP-D75.
5. Run `scripts/radios/finalize_thd75_image.py` with the exact pre-change
   backup and MCP-saved file. MCP normalizes otherwise-empty special-memory
   pages on save; finalization restores every byte outside ordinary memories,
   group names and the full D-STAR region.
6. Open the final file in MCP-D75, verify 538 memories and the local DR list,
   then write it to the radio.
7. Read the radio back and compare counts, representative channels, group
   names and preserved settings.

Never use COM3 for this workflow; it is an unrelated device. CHIRP's current
TH-D75 full-clone path failed at the first block on this radio, so hardware
transfer uses MCP-D75 only.
