# Yaesu FTX-1: step by step

The export is a native RT Systems file, patched onto a factory-reset baseline.
The Near Me memories have the **M-Grp** column ticked. The FTX-1 has no banks,
and Set Menu 55: MEM Group turns those ticked memories into its one memory
subset.

**You need:** RT Systems FTX-1 Programmer (V5) and its USB cable.

## Files

| Path | What it is |
|---|---|
| `radio-data\ftx1\backups\ftx1-before-YYYY-MM-DD.FTX1` | Your read of the radio (step 2) |
| `radio-data\ftx1\exports\ftx1-fleet.FTX1` | The export |
| `radio-data\ftx1\exports\ftx1-fleet-report.md` | Memory map, the memory count and the M-Grp count to check |
| `radio-data\ftx1\templates\` | The factory-default and blank baselines the export is built on |
| `radio-data\ftx1\source-files\` | The original hand-built RT Systems files (`ftx1-wa-radio-read-2026-08-19.FTX1` and others) |

## Steps

1. **Export.**

   ```powershell
   .venv\Scripts\wasds150.exe --home .wasds150-home fleet export --radios ftx1
   ```

2. **Read the radio first.** Connect the FTX-1, start RT Systems, then
   Communications > **Get Data From Radio**. Save it as
   `radio-data\ftx1\backups\ftx1-before-YYYY-MM-DD.FTX1`. The programmer will
   not send a file until it has read the radio once, and this read is your way
   back.
3. **Open the export.** File > Open `radio-data\ftx1\exports\ftx1-fleet.FTX1`,
   then spot-check:
   - memory 1 is `NOAAWXWX2`, 162.400, receive only;
   - a 2 m repeater has the right offset and CTCSS;
   - a 70 cm repeater has a 5.000 MHz offset;
   - M-Grp is ticked on the Near Me rows (the count is in the report).
4. **Send.** Communications > **Send Data To Radio**.

## Check on the radio

- The last used memory matches the report's count.
- A repeater near home opens with its tone. Every toned channel is written
  as Tone, never Tone Sql, so the receiver stays open.
- **Set Menu 55: MEM Group.** Note whether it *scans* only the ticked memories
  or only shows them apart. The answer is still an open item
  ([open-items.md](../open-items.md)).

## Undo

Open `radio-data\ftx1\backups\ftx1-before-YYYY-MM-DD.FTX1` and send it to the radio.

More detail: how each field was decoded is in
[radio-data/ftx1/templates/README.md](../../radio-data/ftx1/templates/README.md);
scan behaviour is in [scan-groups.md](../scan-groups.md).
