# TIDRADIO TD-H9: step by step

The TD-H9 is the one handheld written without a vendor program. A script
drives CHIRP to read the radio, save a backup, write the CSV and read every
channel back to compare. It has no memory groups, so there is no Near Me list.
The memories are in scan order.

**You need:** the two-pin programming cable, and the one-time CHIRP setup in
[td-h9-programming.md](../td-h9-programming.md#one-time-setup) (`.venv-chirp`
plus the TD-H9 driver module). **Never use COM3.** It is an unrelated device.

## Files

| Path | What it is |
|---|---|
| `radio-data\td-h9\exports\td-h9-fleet.csv` | The export (CHIRP Generic CSV) |
| `radio-data\td-h9\exports\td-h9-fleet-report.md` | Memory map, drops and warnings |
| `radio-data\td-h9\backups\td-h9-YYYYMMDD-HHMMSS.img` | The read taken before every run |
| `radio-data\td-h9\backups\td-h9-verify-YYYYMMDD-HHMMSS.img` | The read-back after a write |

## Steps

1. **Find the port.** Plug the cable into the same USB socket as last time. The
   Prolific driver binds per socket. Open Device Manager > Ports and note the
   Prolific USB-to-Serial port, for example COM7. Save it once:

   ```powershell
   .venv\Scripts\wasds150.exe --home .wasds150-home fleet settings --set td-h9.com_port=COM7
   ```

2. **Connect.** Seat the two-pin plug fully: it seats about a millimetre after
   it looks seated. Then turn the radio on.
3. **Back up and dry-run.** In `Update Radios.cmd`, tick only the TD-H9 and
   leave **Write to the radios** unticked. Or from a terminal:

   ```powershell
   .venv\Scripts\wasds150.exe --home .wasds150-home fleet update --radios td-h9
   ```

   It reads the radio into `radio-data\td-h9\backups\` and stages the CSV.
   Nothing is written to the radio.
4. **Write.** Run it again with **Write to the radios** ticked, or add
   `--execute`. It writes the radio, reads it back and compares every channel
   with the file.
5. **Power-cycle the radio.** It stays in programming mode after a write, and
   the next connection fails until it is turned off and on.

The same without the wizard, from the repository folder:

```powershell
.venv\Scripts\wasds150.exe --home .wasds150-home fleet export --radios td-h9
.venv-chirp\Scripts\python.exe scripts\radios\program_tdh9.py --port COM7 --csv radio-data\td-h9\exports\td-h9-fleet.csv
.venv-chirp\Scripts\python.exe scripts\radios\program_tdh9.py --port COM7 --csv radio-data\td-h9\exports\td-h9-fleet.csv --execute
```

## Check on the radio

- The last memory matches the report's count.
- A repeater near home opens with its tone.
- GMRS/FRS/MURS channels transmit at full power. That is the documented choice
  for this radio.

## Undo

Write a backup image back:

```powershell
.venv-chirp\Scripts\python.exe scripts\radios\program_tdh9.py --port COM7 --restore radio-data\td-h9\backups\<image>.img --execute
```

If the handshake fails, see
[td-h9-programming.md: Cable troubleshooting](../td-h9-programming.md#cable-troubleshooting).
It covers the failure modes that leave a radio silently wrong.
