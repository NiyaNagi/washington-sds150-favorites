# Icom ID-52A: step by step

The export is a set of CS-52 CSV files: one per memory group, plus the
D-STAR repeater list for DR. The last group is **Near Me**, a second copy of
the nearest stations from every amateur service, so SCAN > Group on it is one
pass over the same list the Anytone scans.

**You need:** Icom CS-52 and the radio's USB cable. The CSV layout has not yet
been confirmed against a file CS-52 wrote itself, so check one group before
writing.

## Files

| Path | What it is |
|---|---|
| `radio-data\id-52a\backups\id-52a-before-YYYY-MM-DD.icf` | Your read of the radio (step 3) |
| `radio-data\id-52a\exports\id-52a-fleet\Csv\MemoryCh\` | One CSV per memory group, numbered in import order |
| `radio-data\id-52a\exports\id-52a-fleet\Csv\RptList\DSTAR_Near_Home.csv` | D-STAR repeaters for DR |
| `radio-data\id-52a\exports\id-52a-fleet-report.md` | Groups and counts to check |
| `radio-data\id-52a\backups\id-52a-fleet-YYYY-MM-DD.icf` | The file you write (step 6) |

## Steps

1. **Export.**

   ```powershell
   .venv\Scripts\wasds150.exe --home .wasds150-home fleet export --radios id-52a
   ```

   Close the CSVs in any spreadsheet before importing.
2. **Start CS-52** and connect the radio.
3. **Read the radio first**, and save it as
   `radio-data\id-52a\backups\id-52a-before-YYYY-MM-DD.icf`. The memories then
   land on top of your call sign, GPS and APRS settings instead of a blank
   file.
4. **Import every memory group at once.** Select Memory CH in the tree, then
   File > Import > **All**, and choose `CS-52_All_Memory.csv` from the export
   folder. CS-52 sorts its rows into groups by their Group No, so all 22
   groups, Near Me last, fill in one import. Do not use Import > Group for
   this: it fills whichever group you selected, whatever group the file
   names, so a second group file overwrites the first. The per-group files
   in `Csv\MemoryCh\` are still there for replacing a single group.
5. **Import the D-STAR list the same way.** Select Digital > Repeater List,
   then File > Import > **All**, and choose `Csv\RptList\DSTAR_Near_Home.csv`.
   It fills group 01 (Near Home) by its Group No. Answer **No** when CS-52 asks
   about USE(FROM).
6. **Save** As `radio-data\id-52a\backups\id-52a-fleet-YYYY-MM-DD.icf`, then
   **write** it to the radio.

**No PC?** Copy the `Csv` folder into `ID-52\` on the radio's microSD card, then
MENU > SD Card > Import/Export > Import.

## Check on the radio

- Open a group near home and check a few memories against the report.
- Press DR and confirm a local D-STAR repeater is listed.
- On the Near Me group, SCAN > Group scans the whole list.

## Undo

Open `id-52a-before-YYYY-MM-DD.icf` in CS-52 and write it.

More detail: [scan-groups.md](../scan-groups.md). Open questions about the
CSV layout are in [open-items.md](../open-items.md).
