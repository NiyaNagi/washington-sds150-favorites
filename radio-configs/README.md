# Generated radio configurations

Programming files built from this repository's own catalog, committed so they
can be picked up and loaded without running the toolchain first.

| File | Radio | Contents |
|---|---|---|
| `h9-ozette.csv` | TIDRADIO TD-H9 | 185 memories, CHIRP Generic CSV |
| `h9-ozette-report.md` | | Human-readable memory map |
| `ftx1-wa.FTX1` | Yaesu FTX-1 | 960 memories + 47 scan pairs, native format |
| `ftx1-wa-report.md` | | Human-readable memory map |
| `ftx1-local.FTX1` | Yaesu FTX-1 | 351 memories, native format |
| `ftx1-local-report.md` | | Human-readable memory map |
| `ftx1-scan.FTX1` | Yaesu FTX-1 | One frequency-ordered list, everything tunable within 75 mi; data/beacons scan-skipped |
| `ftx1-scan-report.md` | | Human-readable memory map |
| `thd75-ames-lake-report.md` | Kenwood TH-D75A | 545 ordinary memories in 21 groups |
| `thd75-scan-report.md` | Kenwood TH-D75A | One frequency-ordered list, everything tunable within 75 mi; broadcast/data/CB scan-skipped |
| `thd75-current.d75` | Kenwood TH-D75A | Exact operator-requested 545-memory image with all settings |
| `thd75-current-settings.json` | | All 400 typed MCP settings decoded for review |
| `thd75-power-on-KM7HKM.bmp` | | 240x180 16-bit RGB565 power-on identification image (earlier callsign; the operator is now WA7DAM) |
| `atd890-scan/` | Anytone AT-D890UV | CPS 1.05 import bundle: `Channel.CSV`, zones, scan lists, talkgroups, receive groups, AM air and FM lists, `.LST` manifest - built **without** RadioReference rows |
| `atd890-scan-report.md` | | Human-readable zone map, drops and warnings for that public copy |

The FTX-1 files are alternatives, not additions - loading one replaces the
radio's memories with the next. `ftx1-wa` is the statewide inventory;
`ftx1-local` keeps only repeaters within 60 miles of home and fills the rest
with HF nets, beacons and utility stations, split into eighteen service
blocks. `ftx1-scan` is the same content at a 75-mile radius flattened into a
single frequency-ordered list: every repeater band, calling channel and
receive service runs 52 MHz to 470 MHz in one contiguous sweep, with the
continuous-carrier channels (HF data, beacons, WWV, utility) programmed but
locked out of scan. `thd75-scan` does the same for the TH-D75A.

`thd75-scan.d75` is written by the export but git-ignored like every other
native `.d75`; regenerate it locally with the command below.

Everything here is **generated**. The catalog is the source of truth, so these
files go stale the moment the catalog changes. Regenerate with:

```bash
wasds150 --home .wasds150-home plan export h9-ozette --out radio-configs
wasds150 --home .wasds150-home plan export ftx1-wa --target ftx1-file --out radio-configs
wasds150 --home .wasds150-home plan export ftx1-local --target ftx1-file --out radio-configs
wasds150 --home .wasds150-home plan export ftx1-scan --target ftx1-file --out radio-configs
wasds150 --home .wasds150-home plan export thd75-ames-lake --target thd75-file --out radio-configs
wasds150 --home .wasds150-home plan export thd75-scan --target thd75-file --out radio-configs
wasds150 --home .wasds150-home plan export atd890-scan --target atd890-cps --out radio-configs --exclude-licensed
```

The Anytone bundle you actually load should include your own RadioReference
export, so build that one into the git-ignored output directory instead:

```bash
wasds150 --home .wasds150-home plan export atd890-scan --target atd890-cps --out wasds150-output/radios
```

> **Copy the file to wherever you actually load it from.** Exporting writes
> here, inside the repository. If you keep a working copy in your programming
> folder, that copy does not update, and a stale one looks completely normal in
> the programmer - right channel count, right frequencies, wrong everything
> that was fixed since. Check the timestamp before loading.

Use `--copy-to` to update both in one step:

```bash
wasds150 --home .wasds150-home plan export ftx1-wa --target ftx1-file \
    --out radio-configs --copy-to "Z:/Texts/HAM/Radio Programming"
```

## Provenance

These are built only from data already committed to this repository - the
catalog modules under `src/wasds150/catalog/`, each channel carrying its source
URL. No vendor database, no licensed Sentinel or RadioReference content, and no
per-channel text from the RT Systems programmer is present. See
[`NOTICE.md`](../NOTICE.md) for the redistribution posture per source.

## Loading them

- **TD-H9** - import the CSV in CHIRP and upload, or use
  `scripts/radios/program_tdh9.py`. See
  [the programming guide](../docs/td-h9-programming.md).
- **FTX-1** - open the `.FTX1` directly in the RT Systems programmer.
- **AT-D890UV** - in the Anytone CPS: File > New, Tool > Import > select
  `atd890-scan/atd890-scan.LST` > Import All, fix the Radio ID, set the
  Optional Settings listed in [the AT-D890UV guide](../docs/at-d890uv-programming.md),
  write.
- **TH-D75A** - open the private `.d75` in Kenwood MCP-D75, import the filtered
  native D-STAR list, finalize settings preservation, write, and read back as
  documented in [the TH-D75 guide](../docs/th-d75-ames-lake.md). Native `.d75`
  files are ignored because they contain settings read from a specific radio.
  The sole exception is `thd75-current.d75`, which is tracked at the operator's
  explicit request; review its personal data before changing repository
  visibility or redistributing it.

The FTX-1 profile is **unverified against hardware**: it was built from
documentation, and the generated file has been checked against a hand-merged
reference file but never written to a radio. Review it in the programmer
before trusting it.

## What is set per channel, and how it was established

Every field below was decoded by writing a probe file with one memory per
setting, changing that one column in the RT Systems programmer, and diffing
the saved result. Nothing here is inferred from a manual or guessed from a
band plan. See `scripts/radios/make_ftx1_probe.py`.

| Column | Set from | Notes |
|---|---|---|
| Receive/Transmit Frequency | catalog | |
| Offset Frequency + Direction | catalog | shift has its own field, `0x09` |
| Operating Mode | catalog | AM airband, FM Narrow for FRS/MURS, LSB/USB per band |
| Tone Mode | catalog | **Tone**, never Tone Sql - see below |
| CTCSS | catalog | 50-tone table index |
| Skip | plan | data channels are programmed but skipped on scan |
| Name, Comment | catalog | 12 and 79 characters |

Everything else in the grid - Width, AGC, IPO, Attenuator, Contour, IF Shift,
the Narrow flags - is inherited from the vendor's own per-band HOME channel
rather than invented. Setting those columns on an FM memory in the programmer
changes no bytes at all: they are HF receiver controls, and Width is derived
from the mode.

### Tone, not Tone Squelch

Tone Mode stores `0 None, 1 Tone, 2 Tone Sql, 3 DCS`. This project writes
**1 (Tone)** on every toned channel: the access tone is transmitted so the
repeater keys up, and the receiver stays open.

Writing 2 instead is a quiet failure. Transmit still works perfectly, but the
receiver mutes unless the far end sends a matching tone back - and plenty of
repeaters do not. The channel then appears dead while looking entirely correct
in the memory list. A test asserts no shipped channel is tone squelched.

Tone Sql is a legitimate operator choice for a noisy channel; it is just wrong
as a default.
