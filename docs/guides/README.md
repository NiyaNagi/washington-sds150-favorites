# Step-by-step radio guides

One page per radio. Each page says what to open, what to click and where every
file is saved. The **Fleet** tab (`Update Radios.cmd`) walks through the same
steps and does the automatic ones for you. The checklist text it shows is in
[Updating every radio](../fleet-updates.md).

| Radio | Loaded with | Guide |
|---|---|---|
| Uniden SDS150 | Sentinel (installed automatically) | [sds150.md](sds150.md) |
| TIDRADIO TD-H9 | CHIRP, driven by a script (automatic) | [td-h9.md](td-h9.md) |
| Kenwood TH-D75A | Kenwood MCP-D75 | [th-d75.md](th-d75.md) |
| Yaesu FTX-1 | RT Systems FTX-1 Programmer | [ftx1.md](ftx1.md) |
| Anytone AT-D890UV | Anytone D890UV CPS 1.05 | [at-d890uv.md](at-d890uv.md) |
| Icom ID-52A | Icom CS-52 | [id-52a.md](id-52a.md) |

## Before any radio

1. **Build fresh files.** Double-click `Update Radios.cmd` and run an update
   with **Write to the radios** unticked, or from the repository folder:

   ```powershell
   .venv\Scripts\wasds150.exe --home .wasds150-home fleet export --all
   ```

   Every command needs `--home .wasds150-home`. Without it wasds150 starts
   from an empty home and builds tiny files.
2. **Load from `radio-data\`.** Each radio's files are written to
   `radio-data\<radio>\exports\`. Nothing is copied anywhere else, so an older
   copy in another folder is stale even if it looks right.
3. **Read before you write.** Every guide starts by saving what is on the radio
   into `radio-data\<radio>\backups\`, named with the radio and today's date.
   That file is how you undo a write.
4. **Never use COM3.** It is an unrelated device. Current ports: AT-D890UV
   COM6, TH-D75A COM14. The TD-H9's Prolific cable port is shown in Device
   Manager.
5. **Check the report.** Next to each export is a `-report.md` with the memory
   map, what was dropped and why, and the counts to check on the radio.
6. **Audit before you write.**

   ```powershell
   .venv\Scripts\wasds150.exe --home .wasds150-home fleet audit
   ```

   Every transmitting radio must show **0 error(s)**. The audit checks that
   every amateur, GMRS/FRS and MURS memory can transmit, that nothing else can,
   and that each repeater's call, input and access tone match WWARA. Add
   `--warnings` to see the items that need a look rather than a fix.
7. **Your call sign is WA7DAM.** The radios keep their own identity settings
   (TH-D75 My Callsign and APRS call, ID-52A MY call, FTX-1 call), and older
   reads of the TH-D75 still hold the previous call, KM7HKM. Check it in the
   vendor program before writing.

The folder layout is described in [radio-data/README.md](../../radio-data/README.md).
