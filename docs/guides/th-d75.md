# Kenwood TH-D75A: step by step

The export is patched onto an exact read of your radio, so APRS, GPS,
Bluetooth, the menus and the power-on image all survive. Only ordinary
memories, group names and the D-STAR repeater list change. The hardware
transfer is Kenwood MCP-D75 only, because CHIRP's TH-D75 clone path fails on
this radio.

**You need:** MCP-D75, the Kenwood VCP driver, and a USB cable. The radio is on
**COM14**. Never use COM3: it is an unrelated device.

## Files

| Path | What it is |
|---|---|
| `radio-data\th-d75\backups\th-d75-before-YYYY-MM-DD-HHMM.d75` | Your read of the radio (step 1); the export is built on the newest file here |
| `radio-data\th-d75\exports\th-d75-fleet.d75` | The export |
| `radio-data\th-d75\exports\th-d75-fleet-report.md` | Memory map, groups, the memory count to check |
| `radio-data\th-d75\reference\dstar\dstar-within-50mi.tsv` | D-STAR repeaters within 50 miles, for MCP-D75's import |
| `radio-data\th-d75\exports\th-d75-fleet-mcp.d75` | What MCP-D75 saves after the import (step 5) |
| `radio-data\th-d75\exports\th-d75-fleet-final.d75` | The file you write to the radio (step 6) |

## Steps

1. **Read the radio.** In MCP-D75, read the radio on COM14 and save it as
   `radio-data\th-d75\backups\th-d75-before-YYYY-MM-DD-HHMM.d75` (today's date
   and time).
2. **Export.** The export uses the newest `.d75` in `backups\`, which is the file you just saved.

   ```powershell
   .venv\Scripts\wasds150.exe --home .wasds150-home fleet export --radios th-d75
   ```

   To build on a different read, set it first with
   `fleet settings --set th-d75.backup_d75=<path>`. An empty value goes back to
   the newest file.
3. **Open the export.** In MCP-D75, File > Open
   `radio-data\th-d75\exports\th-d75-fleet.d75`.
4. **Import the D-STAR list.** Under Repeater List for TH-D75A (K-type /
   U.S.A. and Canada), import
   `radio-data\th-d75\reference\dstar\dstar-within-50mi.tsv`.
5. **Save.** File > Save As
   `radio-data\th-d75\exports\th-d75-fleet-mcp.d75`.
6. **Finalize.** MCP-D75 rewrites empty special-memory pages when it saves. This
   step restores every byte outside the memories, group names and D-STAR
   region from your step 1 read:

   ```powershell
   .venv\Scripts\python.exe scripts\radios\finalize_thd75_image.py `
       --backup radio-data\th-d75\backups\th-d75-before-YYYY-MM-DD-HHMM.d75 `
       --mcp-saved radio-data\th-d75\exports\th-d75-fleet-mcp.d75 `
       --output radio-data\th-d75\exports\th-d75-fleet-final.d75
   ```

7. **Audit and check the call sign.** Run `fleet audit --radios th-d75` and
   confirm **0 error(s)**. Then open `th-d75-fleet-final.d75` in MCP-D75 and
   check that My Callsign (D-STAR) and the APRS My Callsign are **WA7DAM**. The
   file keeps your radio's own settings, and reads from before the call change
   still hold KM7HKM.
8. **Write.** Check the memory count: the report's "Channels programmed" plus
   the Near Me copies (the report's **Near Me** section gives the number - 850
   and 84, 934 memories, as of 2026-09-13). Check the DR repeater list is
   filled, then write it to the radio on COM14.
9. **Read back (optional).** Read the radio again and save it as
   `radio-data\th-d75\backups\th-d75-readback-YYYY-MM-DD-HHMM.d75`, so the
   written image can be compared byte for byte.

## Check on the radio

- A few memories from the report have the right frequency, offset and tone.
- PTT on any amateur memory keys up, for example 443.050 KC7BAE E Tiger (+5,
  103.5). A memory that beeps and refuses to transmit is an image from before
  2026-09-13, when catch-all groups were programmed receive only: write the
  current export.
- Your call sign, APRS and GPS settings are unchanged.
- **Menu > Scan > Group Link Scan** sweeps the **Near Me** memory group, the last
  group: KC7BAE E Tiger, WW7PSR, then the nearest reachable repeaters, in
  frequency order. Memory Group Link is already set to that group alone.
- DR shows a local D-STAR repeater.

## Undo

Open your step 1 file from `radio-data\th-d75\backups\` in MCP-D75 and write it.

More detail: [th-d75-ames-lake.md](../th-d75-ames-lake.md),
[th-d75-current-configuration.md](../th-d75-current-configuration.md), and the
manuals in `radio-data\th-d75\reference\manuals\`.
