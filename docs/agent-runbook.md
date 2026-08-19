# Agent runbook

Copy-paste procedures for automating this repository. Written for an AI coding
agent or anyone driving the project non-interactively. Every command here has
been run against real hardware or a real catalog.

Paths use Windows separators; swap `.venv/Scripts/` for `.venv/bin/` on
macOS/Linux.

---

## Environments

Three virtual environments, deliberately separate:

| Environment | Purpose | Why separate |
|---|---|---|
| `.venv` | The `wasds150` package, CLI, web UI, tests | Zero runtime deps, Python 3.9+ |
| `.venv-chirp` | CHIRP, hardware programming only | CHIRP is GPL-3 and needs Python 3.10+ |
| `.venv-cad` | OpenSCAD/trimesh model checks | Heavy scientific deps, unrelated |

**Never** add a dependency to `.venv` or import CHIRP from inside
`src/wasds150/`. The zero-dependency guarantee and the MIT/GPL boundary both
depend on that separation.

---

## Verify the checkout is healthy

```powershell
cd "c:\Users\Adam Steenwyk\Documents\Code\washington-sds150-favorites"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\wasds150.exe --home .wasds150-home doctor
```

Expect the full suite green. `doctor` checks the Python version, that the
catalog loads, that the home directory is writable, and that the web UI assets
are present.

---

## Regenerate a radio programming file

```powershell
.venv\Scripts\wasds150.exe --home .wasds150-home plan export h9-ozette --out wasds150-output/radios
```

Writes `h9-ozette.csv` (the programming file) and `h9-ozette-report.md` (a
human-readable memory map). Add `--json` for machine-readable output.

Inspect without writing:

```powershell
.venv\Scripts\wasds150.exe --home .wasds150-home plan show h9-ozette
.venv\Scripts\wasds150.exe --home .wasds150-home plan list
.venv\Scripts\wasds150.exe --home .wasds150-home radios list
```

---

## Program a TD-H9

Full detail and troubleshooting: [TD-H9 programming](td-h9-programming.md).

```powershell
# 1. Back up only — always safe, never writes
.venv-chirp\Scripts\python.exe scripts\radios\program_tdh9.py `
    --port COM7 --label radio-a --backup-only

# 2. Dry run — stages the CSV, writes nothing
.venv-chirp\Scripts\python.exe scripts\radios\program_tdh9.py `
    --port COM7 --label radio-a --csv wasds150-output\radios\h9-ozette.csv

# 3. Program for real
.venv-chirp\Scripts\python.exe scripts\radios\program_tdh9.py `
    --port COM7 --label radio-a --csv wasds150-output\radios\h9-ozette.csv --execute
```

**Preconditions:** radio powered **on**, two-pin plug fully seated, cable in
the same USB socket as last time.

**Expected output on success:** `saved backup:` → `staged N channels` →
`write complete` → `verified N channels read back correctly`.

Attempt 1 failing with "Radio did not respond" is normal; retries are built in.

### Confirm what is actually on the radio

Do not trust the CSV or the dry run. Read the verify image back:

```powershell
.venv-chirp\Scripts\python.exe -c "
import sys, collections
sys.path.insert(0, 'scripts/radios')
from program_tdh9 import load_tdh9_module
load_tdh9_module()
from chirp import directory
cls = directory.DRV_TO_RADIO['TIDRADIO_TD-H9']
r = cls('radio-backups/radio-a-verify-TIMESTAMP.img')
mem = {}
for i in range(1, 200):
    m = r.get_memory(i)
    if not m.empty:
        mem[i] = m
print(len(mem), 'channels')
print('power:', dict(collections.Counter(str(m.power) for m in mem.values())))
print('gaps:', [i for i in range(1, max(mem) + 1) if i not in mem])
"
```

Two historic bugs were invisible everywhere except here: power silently
downgraded to Low, and a write that acknowledged nothing. See
[TD-H9 programming](td-h9-programming.md#two-traps-that-produce-a-silently-wrong-radio).

---

## Refresh a list

```powershell
# Optional: pull live public-source facts into the catalog
.venv\Scripts\wasds150.exe --home .wasds150-home sources update            # preview
.venv\Scripts\wasds150.exe --home .wasds150-home sources update --apply    # commit

# Re-resolve and rewrite the programming file
.venv\Scripts\wasds150.exe --home .wasds150-home plan export h9-ozette --out wasds150-output/radios
```

Then re-flash. Plans resolve against the *profile-filtered* catalog, so
disabling a Favorites List also removes its channels from every plan.

---

## Run the portal UI headlessly

```powershell
.venv\Scripts\wasds150.exe --home .wasds150-home ui --port 8731 --no-browser
```

The session token is printed at startup and embedded in the served page. To
drive the API directly, scrape it from the page rather than parsing stdout:

```powershell
$base = "http://127.0.0.1:8731"
$page = (Invoke-WebRequest -UseBasicParsing "$base/").Content
$page -match 'WASDS150_TOKEN\s*=\s*"([^"]+)"' | Out-Null
$headers = @{ "X-Wasds150-Token" = $Matches[1] }

Invoke-RestMethod "$base/api/v1/plans" -Headers $headers
Invoke-RestMethod "$base/api/v1/plans/h9-ozette" -Headers $headers
Invoke-RestMethod "$base/api/v1/programmer/status" -Headers $headers
```

The server binds `127.0.0.1` only and rejects unauthenticated requests with
401.

### Radio endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/radios` | Capability profiles |
| GET | `/api/v1/plans` | Plans with their export targets |
| GET | `/api/v1/plans/{id}` | Resolved memory map |
| POST | `/api/v1/plans/{id}/export` | Write the programming file |
| GET | `/api/v1/programmer/status` | Toolchain state + serial ports |
| POST | `/api/v1/programmer/run` | Back up / dry run / flash |

`POST /api/v1/programmer/run` body:

```json
{ "port": "COM7", "label": "radio-a",
  "csv": "wasds150-output/radios/h9-ozette.csv",
  "execute": false, "backup_only": false }
```

`execute` defaults to `false`, so the default action is always the safe one.
Port and label are validated against strict patterns before any subprocess
starts; anything containing a shell metacharacter or a path separator is
rejected with 400.

---

## PowerShell gotchas in this repo

These wasted real time:

- **Multi-line commands get mangled** when sent to the integrated terminal.
  Write a `.ps1` file and run it with
  `powershell -ExecutionPolicy Bypass -File script.ps1`.
- **Here-strings (`@"..."@`) with embedded quotes** corrupt and produce
  misleading exit code 1 even when the Python inside succeeded. Prefer
  `python -c "..."` with single-quoted internals, or a temp file.
- **Strings starting with `-`** (like auth tokens) are parsed as parameters.
  Assign them to a variable first, or scrape them from the page.
- Set `$env:PYTHONIOENCODING='utf-8'` before Python that prints non-ASCII.

---

## Adding a radio

1. **Capability profile** → `src/wasds150/radios/registry.py`. Bands, modes,
   channel count, name length. Set `verified=False` until tested on hardware —
   the UI surfaces that flag.
2. **Channel plan** → `src/wasds150/plans/`, then register it in
   `src/wasds150/plans/__init__.py`.
3. **Export target** → `src/wasds150/export/registry.py`, declaring
   `radio_id` so a plan can never reach the wrong writer.
4. **Tests** → extend `tests/test_radios.py` and `tests/test_plan.py`.

The CLI and the Radios tab both pick all three up automatically via
`src/wasds150/plan/service.py`. No front-end change is needed.

---

## Invariants — do not break these

| Invariant | Why |
|---|---|
| `wasds150` has **zero runtime dependencies** | `pip install wasds150` must work anywhere with stdlib only |
| CHIRP is **never imported** inside `src/wasds150/` | GPL-3 vs MIT licence boundary |
| Licensed data is **never committed** | Sentinel HPDB, RadioReference exports; see `.gitignore` and `NOTICE.md` |
| Every catalog channel carries a **source URL** in `notes` | Claims must be checkable |
| Dropped channels are **reported, never coerced** | Silently rewriting a P25 talkgroup as analog FM makes dead channels that look programmed |
| Writing to hardware **requires an explicit flag** | Dry run is always the default |

---

## Related

- [TD-H9 programming](td-h9-programming.md) — full hardware procedure
- [Data sources](data-sources.md) — source precedence and refresh policy
- [Sentinel refresh runbook](sentinel-refresh-runbook.md) — the scanner path
