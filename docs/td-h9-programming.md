# Programming the TIDRADIO TD-H9

This is the complete, reproducible procedure for programming a TD-H9 from this
project's unified catalog — including every hardware fault we hit and how to
tell them apart. It was written while programming two radios for a Lake Ozette
trip; both ended up with 185 identical, verified channels.

Everything here is verified against real hardware unless explicitly marked
otherwise.

---

## What you need

| Item | Notes |
|---|---|
| TIDRADIO TD-H9 | Any variant; the radio reports its own GMRS/HAM mode during the handshake |
| Programming cable | Two-pin Kenwood/Baofeng style. Most are counterfeit Prolific — see [Cable troubleshooting](#cable-troubleshooting) |
| Python 3.10+ | For CHIRP only. The `wasds150` package itself runs on 3.9+ |
| This repository | Installed per the main [README](../README.md) |

CHIRP is **GPL-3** and this project is MIT with zero runtime dependencies, so
CHIRP is never vendored or imported. It lives in its own interpreter and is
driven as a subprocess. `.venv-chirp/` and `.chirp-modules/` are git-ignored.

---

## One-time setup

```bash
# 1. A separate interpreter for CHIRP (needs Python 3.10+; this project supports 3.9)
python -m venv .venv-chirp
.venv-chirp/Scripts/pip install git+https://github.com/kk7ds/chirp.git   # Windows
# .venv-chirp/bin/pip install git+https://github.com/kk7ds/chirp.git     # macOS/Linux

# 2. Fetch the TD-H9 driver module (not in mainline CHIRP yet)
python scripts/radios/fetch_chirp_tdh9_module.py
```

The driver comes from the CHIRP issue tracker (issue #12216) and lands in
`.chirp-modules/`. It is not committed.

---

## The short version

```bash
# Generate the programming file from the catalog
wasds150 --home .wasds150-home plan export h9-ozette --out wasds150-output/radios

# Back up the radio and dry-run (writes nothing)
.venv-chirp/Scripts/python.exe scripts/radios/program_tdh9.py \
    --port COM7 --label radio-a --csv wasds150-output/radios/h9-ozette.csv

# Program it for real
.venv-chirp/Scripts/python.exe scripts/radios/program_tdh9.py \
    --port COM7 --label radio-a --csv wasds150-output/radios/h9-ozette.csv --execute
```

Or do all of it from the browser: `wasds150 ui` → **Radios** tab.

Every run reads the radio and saves a timestamped image to `radio-backups/`
*before* anything is written. `--execute` is required to modify the radio; the
default is always a dry run.

---

## Verified radio facts

Measured against real hardware, not copied from a spec sheet:

| Property | Value |
|---|---|
| Memory channels | 199 |
| Channel name length | 8 characters |
| Banks | None |
| Serial baud | **38400** (not 115200 — see below) |
| Modes | FM, NFM, AM, NAM (analog only) |
| Power levels | Low **1 W** / Mid **5 W** / High **10 W** |
| RX coverage | 76–108, 108–136, 136–174, 220–230, 350–390, 400–520 MHz |
| Handshake magic | `PVOJH\x5c\x14` |

### The Mid power level is 5 W, not 4 W

`get_features()` advertises power in dBm (30/36/40), and 36 dBm rounds to
"4 W". The driver's own class literal says `watts=5.00`. Use **5.0 W** for the
GMRS interstitial channels — that is exactly the 47 CFR 95.1767 limit rather
than a watt under it.

---

## Cable troubleshooting

We hit three independent faults stacked on top of each other. They present
almost identically, so work through them in this order.

### Fault 1 — counterfeit Prolific chip

Nearly every cheap programming cable uses a cloned **PL2303HXA**. Prolific's
current driver (3.8.43.0) deliberately refuses to serve clones, and it fails
in the most confusing way possible: it reports no error, it *creates* the COM
port, and then every attempt to open that port fails.

The fix is to fall back to the legacy 3.2.0.0 driver. In an **administrator**
PowerShell:

```powershell
pnputil /enum-drivers | Select-String -Context 2,6 "Prolific"   # find the oemNN.inf
pnputil /delete-driver oemNN.inf /uninstall /force
pnputil /scan-devices
```

Then **unplug and replug the cable into the same USB socket** — the driver
binds per socket, and a different socket reloads the broken version.

`scripts/radios/swap_prolific_driver.ps1` automates this and writes a log.

### Fault 2 — wrong baud rate

The TD-H9 talks at **38400**, not the 115200 that several online guides list.
At the wrong baud the radio is completely silent, which looks exactly like a
dead cable.

### Fault 3 — handshake ordering

`sync_in()` alone fails. The driver must call
`radio_cls.detect_from_serial(pipe)` first. **Upload is the opposite** — it
idents itself, so do not pre-ident before a write.

### Telling faults apart

```bash
python scripts/radios/probe_tdh9.py --port COM7
```

| Symptom | Cause |
|---|---|
| Port will not open at all | Fault 1 (driver) |
| Port opens, radio silent at every baud | Fault 2, or radio off / plug not seated |
| Radio ACKs `0x06` but clone fails | Fault 3 (handshake order) |
| First attempt fails, second succeeds | **Normal.** The retry logic handles it |

> **Do not diagnose with a guessed handshake string.** We wasted a debugging
> round sending `PROGRAM` — a string we invented — got silence at three baud
> rates, and nearly concluded the radio was faulty. The real magic is
> `cls._idents[0]`. Silence in response to a made-up handshake proves nothing.

---

## Two traps that produce a *silently* wrong radio

Both of these produced a radio that looked perfectly programmed. Neither was
visible in the CSV or the dry run. **Only reading the radio back exposed them.**

### Trap 1 — power silently downgraded to Low

The driver maps power like this:

```python
_mem.lowpower = self._tx_power.index(mem.power)
```

`list.index()` compares by object identity here. A `PowerLevel` parsed from a
CSV is a *different object* from the radio's own, so `.index()` raises, the
handler swallows it, and the channel falls back to index 0 — **Low**. The CSV
said 4.0 W and every channel on the radio was 1 W.

The fix, in `apply_csv()`, is to substitute the driver's own level object
before calling `set_memory`:

```python
levels = radio.get_features().valid_power_levels
memory.power = min(levels, key=lambda lv: abs(float(lv) - float(memory.power)))
```

**General rule:** when vendor code maps a value by object identity, hand it
*its own* object.

### Trap 2 — a write that silently does nothing

An earlier patch replaced CHIRP's `_write_block` to add settling delay for the
slow cable, and in doing so dropped the per-block ACK check. The upload printed
"write complete" while the radio ignored every byte.

**Never reimplement a write path you have not fully decoded.** Reads are safe
to adjust — a bad read fails loudly. Writes are not. If a device acknowledges
writes, *check the acknowledgement*. If you only need to change timing, change
it on the read side. `patch_slow_cable()` now patches `_read_block` only.

### The lesson behind both

Verify on the device, not on the artifact. A clean dry run and a correct CSV
prove nothing about what is actually in the radio. `--execute` always reads
back and compares channel by channel; trust that, not the export.

---

## Channel ordering

Ordering is set per block in the plan, via `sort=` on each `PlanBlock`:

| Sort | Behaviour | When to use |
|---|---|---|
| `SORT_CATALOG` | Catalog order | Curated lists |
| `SORT_FREQ` | Ascending frequency | Band scans |
| `SORT_LABEL` | Alphabetical | Rarely correct for numbered channels |
| `SORT_NATURAL` | Digit-aware | Anything numbered: GMRS, marine |

**`SORT_FREQ` interleaves GMRS.** The main channels (462.550, .575 …) and the
interstitials (462.5625, .5875 …) alternate within the band, so a frequency
sweep yields 15, 1, 16, 2, 17, 3 … `SORT_LABEL` is no better — alphabetically,
"15" sorts before "2".

`SORT_NATURAL` splits on digit runs so `GMRS 2` precedes `GMRS 15`. The shipped
plan also separates GMRS 1–7, FRS 8–14, and GMRS 15–22 into their own blocks so
the radio's channel numbers match the printed FRS/GMRS chart.

---

## Transmit power and the law

Power is set per block and the plan encodes the legal limits directly:

| Block | Power | Limit |
|---|---|---|
| GMRS 1–7 (interstitial) | 5 W | 47 CFR 95.1767 caps these at 5 W |
| GMRS 15–22 + repeaters | 10 W | Full power permitted |
| FRS 8–14 | receive only | FRS-only channels; a GMRS licensee must not transmit here on a Part 90 radio |
| MURS | 1 W | 47 CFR 95.2767 caps MURS at 2 W |
| Amateur | 10 W | Within licence privileges |

`tests/test_plan.py::TestOzettePlanCompliance` resolves the **real shipped
plan** and asserts these limits hold, so a future edit cannot quietly raise
MURS to 10 W.

Transmit is opt-in per block via `tx_policy`. `TX_NONE` programs a channel for
listening only and is the default for every public-safety, marine, aviation and
NOAA block. Transmitting on those is illegal without the appropriate licence
and authorisation.

---

## Refreshing a list later

The catalog is the source of truth, so refreshing is just re-exporting:

```bash
# Optional: pull live source data into the catalog first
wasds150 --home .wasds150-home sources update --apply

# Re-resolve the plan and rewrite the CSV
wasds150 --home .wasds150-home plan export h9-ozette --out wasds150-output/radios

# Re-flash
.venv-chirp/Scripts/python.exe scripts/radios/program_tdh9.py \
    --port COM7 --label radio-a --csv wasds150-output/radios/h9-ozette.csv --execute
```

In the browser, that is **Refresh from catalog** → **Export** → **Write to
radio** on the Radios tab.

Disabling a Favorites List on the **Profile** tab also removes its channels
from every plan, because plans resolve against the profile-filtered catalog.

---

## Operational notes

- The radio stays in programming mode after a write. **Power-cycle it** before
  reading again, or the next handshake fails.
- Keep the cable in the **same USB socket**; the Prolific driver binds per
  socket.
- Attempt 1 of both read and write routinely fails. Retries are built in.
- The radio must be **powered on** with the plug fully seated. The two-pin
  connector seats about a millimetre *after* it looks seated.
- Backups accumulate in `radio-backups/` (git-ignored) as
  `<label>-<timestamp>.img`, plus a `-verify-` image after each write.

---

## Restoring a radio

Backups are full CHIRP images and can be written straight back:

```bash
# Dry run first — reads the radio, saves its current contents, changes nothing
.venv-chirp/Scripts/python.exe scripts/radios/program_tdh9.py \
    --port COM7 --restore radio-backups/radio-a-20260819-101713.img

# Restore for real
.venv-chirp/Scripts/python.exe scripts/radios/program_tdh9.py \
    --port COM7 --restore radio-backups/radio-a-20260819-101713.img --execute
```

The radio's current contents are backed up as `<label>-pre-restore-<stamp>.img`
before the restore runs, so a restore is itself reversible. The factory image
saved before your first write is the one worth keeping.

---

## Adding another radio

The architecture is additive — nothing existing changes:

1. **Capability profile** in `src/wasds150/radios/registry.py` — bands, modes,
   channel count, name length. Set `verified=False` until you have tested
   against hardware; the UI displays that flag.
2. **Channel plan** in `src/wasds150/plans/` — blocks, selectors, sort, power,
   transmit policy.
3. **Export target** in `src/wasds150/export/registry.py` — declare which radio
   it serves, so a plan can never reach the wrong writer.

Both the CLI and the Radios tab pick up all three automatically through
`src/wasds150/plan/service.py`.

---

## Related

- [Agent runbook](agent-runbook.md) — copy-paste procedures for automation
- [Lake Ozette profile](ozette-lake.md) — what this plan covers and why
- [Data sources](data-sources.md) — where the catalog's facts come from
