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
4. **Import each memory group.** Memory CH > right-click the group > Import >
   Group, and choose the matching file from `Csv\MemoryCh\`. Go in file-name
   order, because each file names the group it fills. Answer **No** when CS-52
   asks about USE(FROM). The last file is Near Me.
5. **Import the D-STAR list.** Digital > Repeater List > right-click a group >
   Import > Group, and choose `Csv\RptList\DSTAR_Near_Home.csv`.
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
