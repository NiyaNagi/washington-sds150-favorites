# Legacy radio plans

Programming files from the single-radio plans that came before the fleet
plans (`td-h9-fleet`, `ftx1-fleet`, and so on). They are kept because the
older guides refer to them. The files you load today are in each radio's
`radio-data/<radio>/exports/` folder, and the step-by-step guides are in
[`docs/guides/`](../../../docs/guides/README.md).

| File | Radio | Contents |
|---|---|---|
| `h9-ozette.csv` | TIDRADIO TD-H9 | 185 memories, CHIRP Generic CSV |
| `h9-ozette-report.md` | | Human-readable memory map |
| `ftx1-wa.FTX1` | Yaesu FTX-1 | 979 memories + 47 scan pairs, native format |
| `ftx1-wa-report.md` | | Human-readable memory map |
| `ftx1-local.FTX1` | Yaesu FTX-1 | 355 memories, native format |
| `ftx1-local-report.md` | | Human-readable memory map |
| `ftx1-scan.FTX1` | Yaesu FTX-1 | One frequency-ordered list of 379 memories, everything tunable within 75 mi; data/beacons scan-skipped |
| `ftx1-scan-report.md` | | Human-readable memory map |
| `thd75-ames-lake-report.md` | Kenwood TH-D75A | 692 ordinary memories in 21 groups |
| `thd75-scan-report.md` | Kenwood TH-D75A | One frequency-ordered list, everything tunable within 75 mi; broadcast/data/CB scan-skipped |
| `atd890-scan/` | Anytone AT-D890UV | CPS 1.05 import bundle: `Channel.CSV`, zones, scan lists, talkgroups, receive groups, AM air and FM lists, `.LST` manifest - built **without** RadioReference rows |
| `atd890-scan-report.md` | | Human-readable zone map, drops and warnings for that public copy |

The FTX-1 files are alternatives, not additions - loading one replaces the
radio's memories with the next. `ftx1-wa` is the statewide inventory;
`ftx1-local` keeps only repeaters within 60 miles of home and fills the rest
with HF nets, beacons and utility stations, split into eighteen service
blocks. `ftx1-scan` is the same content at a 75-mile radius flattened into a
single frequency-ordered list. `thd75-scan` does the same for the TH-D75A.

Native `.d75` files (`thd75-ames-lake.d75`, `thd75-scan.d75`) are written here
but git-ignored, because they carry settings read from a specific radio. The
TH-D75A's tracked reference image, `thd75-current.d75`, is in
[`radio-data/th-d75/reference/current/`](../../th-d75/reference/current/).

Everything here is **generated**. The catalog is the source of truth, so these
files go stale the moment the catalog changes. Regenerate with:

```bash
wasds150 --home .wasds150-home plan export h9-ozette --out radio-data/shared/legacy-plans --exclude-licensed
wasds150 --home .wasds150-home plan export ftx1-wa --target ftx1-file --out radio-data/shared/legacy-plans --exclude-licensed
wasds150 --home .wasds150-home plan export ftx1-local --target ftx1-file --out radio-data/shared/legacy-plans --exclude-licensed
wasds150 --home .wasds150-home plan export ftx1-scan --target ftx1-file --out radio-data/shared/legacy-plans --exclude-licensed
wasds150 --home .wasds150-home plan export thd75-ames-lake --target thd75-file --out radio-data/shared/legacy-plans --exclude-licensed
wasds150 --home .wasds150-home plan export thd75-scan --target thd75-file --out radio-data/shared/legacy-plans --exclude-licensed
wasds150 --home .wasds150-home plan export atd890-scan --target atd890-cps --out radio-data/shared/legacy-plans --exclude-licensed
```

Without `--out`, a plan export goes to its radio's own folder,
`radio-data/<radio>/exports/`, and includes your RadioReference rows.
Load from there: a copy kept anywhere else does not update, and a stale file
looks completely normal in the programmer.

## Provenance

These are built only from data already committed to this repository - the
catalog modules under `src/wasds150/catalog/`, each channel carrying its source
URL. No vendor database, no licensed Sentinel or RadioReference content, and no
per-channel text from the RT Systems programmer is present. See
[`NOTICE.md`](../../../NOTICE.md) for the redistribution posture per source.

## What is set per FTX-1 channel, and how it was established

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
