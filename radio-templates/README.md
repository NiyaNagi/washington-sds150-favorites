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
