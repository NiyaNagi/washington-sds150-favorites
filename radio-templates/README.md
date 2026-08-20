# Radio templates

Baseline files used by the export targets. **These contain no curated channel
data.**

## `ftx1-factory-default.FTX1`

A Yaesu `.FTX1` read straight off a factory-reset FTX-1. This is the
reproducible baseline: it holds the radio's default settings and a single
default memory (7.000 MHz), and nothing personal.

Keeping it in the repository means the blank template can be regenerated from
a known starting point rather than from whatever happened to be on someone's
radio that day.

## `ftx1-blank.FTX1`

The factory default with its 999 user memories zeroed and three base records
kept at the front, one per duplex shape. Everything else is byte-identical to
the factory file.

### Why a template exists at all

An FTX-1 memory record is 295 bytes and this project has decoded roughly a
dozen of them. The rest carry per-channel settings the programmer wrote and
the radio expects. Synthesising those bytes would produce a file that loads
and then behaves oddly in ways that are very hard to trace back to here. So
`wasds150.export.ftx1_target` starts from this template and patches only the
fields it understands; everything else keeps whatever the vendor programmer
put there.

### What must NOT be cleared

A `.FTX1` is much more than a channel list. Past the memory array it holds the
radio's configuration - CW messages, GPS setup, display data - and the five
HOME channels. **None of that may be blanked.**

This is not hypothetical. The first version of the format model divided the
whole file by the record size, which minted roughly 800 phantom "records" out
of the configuration area. The template builder then dutifully cleared *every
record*, wiping about 100 KB of radio settings. The resulting file loaded
fine and its memories were correct, so nothing looked wrong.

Two things now prevent a repeat:

* `Ftx1File.load()` bounds the record array at `RECORD_COUNT` and carries
  everything past it as an opaque trailer.
* `tests/test_ftx1_target.py::TestSettingsAreaPreserved` asserts that an
  export leaves the trailer, the header and the HOME channels byte-identical
  to the template.

### Why clearing the memories was not trivial either

Blanking the fields this project models is not enough. A record has an
undecoded tail beyond the 32-character comment at `0x85`, and in a file saved
by the RT Systems programmer that tail holds further descriptive text from the
vendor's bundled marine and service databases. An early attempt blanked only
the modelled fields and still leaked strings like `"Intership only."` and
`"Safety Information Broadcasts."`.

The generator therefore zeroes each memory record outright, then restores only
base records whose *full* 295 bytes contain no readable text, and refuses to
write if any text survives in the memory area.

### Regenerating

```bash
python scripts/radios/make_ftx1_template.py \
    --source radio-templates/ftx1-factory-default.FTX1 \
    --out radio-templates/ftx1-blank.FTX1
```

Any file saved by the RT Systems programmer works as a source, but the factory
default is preferred: it carries no personal configuration. Whatever you use,
only the memory area is cleared - its settings are inherited by every file the
export target produces, so use a radio configured the way you want.

## Decoded record fields

A memory record is 295 bytes. These offsets are confirmed against files the
RT Systems programmer wrote from a real radio, plus two probe files where
every memory was identical except one column (see
`scripts/radios/make_ftx1_probe.py`).

| Offset | Size | Field | How it was confirmed |
|---|---|---|---|
| `0x00` | u8 | In use (bit 1 = M-Grp) | 967/967 vendor records |
| `0x01` | u32 LE | Receive frequency, Hz | round-trips on every record |
| `0x05` | u32 LE | Transmit frequency, Hz | round-trips on every record |
| `0x09` | u32 LE | Offset/shift magnitude, Hz | equals \|tx-rx\| on 963/967 |
| `0x0D` | u8 | Offset direction: 0 simplex, 1 minus, 2 plus | agrees on 967/967 |
| `0x0E` | u8 | **Operating mode** | probe file, 18 modes |
| `0x0F` | utf-16 | Name, 12 characters | round-trips |
| `0x2D` | u8 | Tone mode: 0 off, 1 enc+dec, 2 enc | vendor records |
| `0x2E`/`0x2F` | u8 | Tx/Rx CTCSS index | 50-tone table |
| `0x34` | u8 | Skip on scan | probe file |
| `0x47`, `0x50` | u8 | Tx DGID (stored twice) | probe file |
| `0x4A`, `0x51` | u8 | Rx DGID (stored twice) | probe file |
| `0x4C` | bits | `0x40` HF Antenna = Ant 2 | probe file |
| `0x4D` | bits | `0x80` Packet Narrow, `0x40` Digital Narrow, `0x01` SuperDx, low bits DNR algorithm | probe file |
| `0x4E` | bits | `0x04` SSB Narrow, `0x02` CW Narrow, `0x01` RTTY Narrow | probe file |
| `0x4F` | u8 | Noise Blanker level | probe file |
| `0x85` | utf-16 | Comment, 79 characters | vendor records up to 79 chars |

### Operating mode codes

| Code | Programmer label | Code | Programmer label |
|---:|---|---:|---|
| `0x00` | FM | `0x0F` | RTTY-R |
| `0x01` | AM | `0x12` | PKT-FM |
| `0x03` | FM Narrow | `0x13` | PKT-LSB |
| `0x04` | AM Narrow | `0x14` | PKT-USB |
| `0x05` | LSB | `0x17` | CWL |
| `0x06` | USB | `0x18` | CWU |
| `0x0B` | Packet | `0x19` | PSK |
| `0x0E` | RTTY | `0x1C` | DN (System Fusion) |
| | | `0x1D` | VW |
| | | `0x20` | Auto |

Cross-checked against a file saved from a real radio, which contains exactly
three of these: `0x00` on general FM channels, `0x03` on the FRS and MURS
channels that are genuinely narrowband, and `0x1C` on the System Fusion
repeaters.

### Fields the radio derives rather than stores

Width, Contour, IF Shift, Attenuator, IPO, AGC, Bk-In, DNF and Notch produced
**no byte change** when set in the programmer on an FM memory. They are HF
receiver controls that the programmer greys out for FM, and Width in
particular is displayed per mode - 300 Hz for SSB, 50 Hz for CW, 16 kHz for
FM. They are not per-memory settings on a VHF/UHF channel, so there is
nothing for this project to write.
