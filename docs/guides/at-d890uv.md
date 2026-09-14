# Anytone AT-D890UV: step by step

The export is a CPS import bundle. In the D890UV CPS it builds the channels,
zones, scan lists, talkgroups, receive groups, the AM air band and the FM
list. **Every zone is also a scan list with the same name.** Press PF1 in a zone
to scan it. **Near Me** is the first zone, and stations beyond the radius are in
the Far zones.

**You need:** Anytone D890UV CPS 1.05 (`C:\D890UV\D890UV.exe`), firmware 1.05 with the
NXDN overlay, band mode 00014, and the programming cable. The radio is on
**COM6**. Never use COM3.

First time on a new radio: firmware, band mode and the options utility are
covered in [at-d890uv-programming.md](../at-d890uv-programming.md). The files are in
`radio-data\at-d890uv\firmware\`.

## Files

| Path | What it is |
|---|---|
| `radio-data\at-d890uv\exports\at-d890uv-fleet\at-d890uv-fleet.LST` | The import manifest |
| `radio-data\at-d890uv\exports\at-d890uv-fleet\scanlists.json` | Full scan lists, for the patch in step 8 |
| `radio-data\at-d890uv\exports\at-d890uv-fleet-report.md` | Zones, scan lists and counts to check |
| `radio-data\at-d890uv\backups\at-d890uv-factory-mode14-2026-09-11.rdt` | The base codeplug: band mode 00014, before any import |
| `radio-data\at-d890uv\backups\at-d890uv-fleet-YYYY-MM-DD.rdt` | Your saved import (step 7) |
| `radio-data\at-d890uv\backups\at-d890uv-fleet-YYYY-MM-DD-full.rdt` | The patched codeplug you write (step 8) |
| `radio-data\at-d890uv\exports\at-d890uv-fleet\*ContactList.CSV` | radioid.net DMR and NXDN contact lists, listed in the `.LST` (a standing copy is kept in `radio-data\shared\contacts\`) |
| `radio-data\at-d890uv\readbacks\YYYY-MM-DD-readback\` | Export All after writing (step 11) |

## Steps

1. **Export.**

   ```powershell
   .venv\Scripts\wasds150.exe --home .wasds150-home fleet export --radios at-d890uv
   ```

2. **Open the base codeplug.** In the CPS, File > Open
   `radio-data\at-d890uv\backups\at-d890uv-factory-mode14-2026-09-11.rdt`, or your
   last saved codeplug if it has your settings. Model Information must read
   `UHF{400-520} MHF{220-225} VHF{136-174}`.
3. **Import.** Tool > Import > Import From File List, choose
   `at-d890uv-fleet.LST`, then **Import All**. The file list includes the DMR and
   NXDN contact lists, so the import takes several minutes. Scan lists show at most 50 members
   for now. That is expected, and step 8 fixes it. If the CPS cannot resolve a
   name, the export is stale: export again instead of editing.
4. **Identity.**
   - NX Setting: Unit ID(Own) and Base ID = **16240**, Air Alias Name =
     **WA7DAM**. Check these even on a saved codeplug, because a read-back once
     showed them at factory values.
   - Radio ID List: row 1 = **3227807 / WA7DAM**.
5. **Optional Settings.**
   - Digital Function: **Digital Monitor = Double Slot, CC = Any, ID = Any**.
     Without it, DMR stays silent unless the talkgroup is in that channel's
     receive list.
   - Work Mode: VFO/MEM A = MEM, **MEM Zone A = Near Me**, Sub-Channel Mode On.
   - Other: **Priority Zone A = Near Me**, Scan Mode CO, TOT 180 s.
   - Display: **Display mode = Channel Name**.
   - AM/FM: AM(B), AM Work Zone `Air Local 01`.
   - Keys: PF1 Scan / Nuisance Delete, PF2 Digital Monitor / Monitor, PF3 AM/FM /
     Alarm, P1 Sub CH Switch / Main Channel Switch, P2 Priority Zone / V/M.
6. **Contacts.** Import All loaded the DMR and NXDN contact lists. Check that
   Digital > DMR Digital Contact List and NX Digital Contact List are filled, and
   open one NXDN entry: its Attr, TxForbid and Ring columns are written empty.
7. **Save** As `radio-data\at-d890uv\backups\at-d890uv-fleet-YYYY-MM-DD.rdt`.
8. **Restore the long scan lists.** The CPS importer stops at 50 members, so
   this puts the rest back:

   ```powershell
   .venv\Scripts\python.exe scripts\radios\patch_atd890_scanlists.py `
       --rdt radio-data\at-d890uv\backups\at-d890uv-fleet-YYYY-MM-DD.rdt `
       --sidecar radio-data\at-d890uv\exports\at-d890uv-fleet\scanlists.json `
       --output radio-data\at-d890uv\backups\at-d890uv-fleet-YYYY-MM-DD-full.rdt
   ```

9. **Write.** Open the `-full.rdt`. Check that Near Me has 100 members and
   that the other lists match the report. Then Write to radio: Other Data and
   Digital Contact List.
10. **On the radio:** Menu > Settings > Radio Set > Display > **Ch. Name = CH
    name**. On Frequency the radio runs in VFO mode, where a channel's offset
    and tone do not apply.
11. **Read back (optional).** Read from radio, then Tool > Export > Export All
    into a new `radio-data\at-d890uv\readbacks\YYYY-MM-DD-readback\` folder, and
    compare:

    ```powershell
    .venv\Scripts\python.exe scripts\radios\diff_atd890_export.py `
        --bundle radio-data\at-d890uv\exports\at-d890uv-fleet `
        --readback radio-data\at-d890uv\readbacks\YYYY-MM-DD-readback
    ```

## Check on the radio

- The radio starts in zone Near Me, and PF1 scans it.
- A DMR repeater near home, on its main talkgroup, opens when the group is
  active. Digital Monitor on means you also hear groups not in the list.
- The AM air band watches `Air Local 01` on the B side.
- `Ham NXDN` holds KC7BAE on 443.050 (RAN 5), receive only. Check in the CPS
  that the channel shows RAN 5 after import, then set Menu > Settings > Radio
  Set > Other Func > Protocol = NXDN to hear it; DMR is silent until you set it
  back to DMR.
- No DMR memory is programmed without a talkgroup: those could not be keyed,
  and the machines worth keying are in the DMR zones with their talkgroups.

## Undo

Open the previous `.rdt` from `radio-data\at-d890uv\backups\` and write it.

More detail: [at-d890uv-programming.md](../at-d890uv-programming.md),
[scan-groups.md](../scan-groups.md), [puget-sound-nets.md](../puget-sound-nets.md).
