# Blank radio templates

Structural templates used by the export targets. **These contain no channel
data.**

## `ftx1-blank.FTX1`

A Yaesu `.FTX1` container with every memory record zeroed and three
verified-clean base records kept at the front, one per duplex shape
(simplex / plus / minus).

### Why a template exists at all

An FTX-1 memory record is 295 bytes and this project has decoded roughly a
dozen of them. The rest carry per-channel settings the programmer wrote and
the radio expects. Synthesising those bytes would produce a file that loads
and then behaves oddly in ways that are very hard to trace back to here. So
`wasds150.export.ftx1_target` starts from this template and patches only the
fields it understands; everything else keeps whatever the vendor programmer
put there.

### Why clearing was not trivial

Blanking the fields this project models is not enough. A record has an
undecoded tail beyond the 32-character comment at `0x85`, and in a file saved
by the RT Systems programmer that tail holds further descriptive text from the
vendor's bundled marine and service databases. The first attempt at this
template blanked only the modelled fields and still leaked strings like
`"Intership only."` and `"Safety Information Broadcasts."`.

The generator therefore zeroes every record outright, then restores only base
records whose *full* 295 bytes contain no readable text, and refuses to write
if any text survives outside the container header.

### Regenerating

```bash
python scripts/radios/make_ftx1_template.py \
    --source "path/to/YourFile.FTX1" \
    --out radio-templates/ftx1-blank.FTX1
```

The source is any file saved by the RT Systems programmer. It is read only for
its container structure; nothing from its channel list reaches the output, and
the script verifies that before writing.

`tests/test_ftx1_target.py::test_template_carries_no_channel_data` asserts the
committed template stays clean.
