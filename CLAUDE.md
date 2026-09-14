# Working in this repository

Read [docs/agent-runbook.md](docs/agent-runbook.md) first. Its invariants apply
to every change.

- Every `wasds150` command needs `--home .wasds150-home`.
- Radio files live in `radio-data/<radio>/` (see `radio-data/README.md`). Never
  write to or delete anything on the Z: drive.
- COM3 is an unrelated device: never use it for a radio.
- The operator's identity (WA7DAM, General; GMRS WRWH962; DMR 3227807; NXDN
  16240) lives only in `src/wasds150/station.py`.

## Audit every change that can reach a radio

Anything that touches the catalog, a source adapter or recipe, a plan, the
fleet template or an exporter can change what a radio transmits on or what a
memory is called. After such a change, before exporting or committing:

1. Run the tests: `.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_webui.py`.
   `tests/test_transmit_audit.py` fails if a fleet plan blocks transmit on a
   licensed channel, transmits where the operator holds no licence, or if the
   WWARA checks stop catching a wrong call, input or access tone.
2. Run `.venv\Scripts\wasds150.exe --home .wasds150-home fleet audit`. It runs
   the same checks against the working catalog and every exported file, and
   checks each analog amateur repeater's call, input and access tone against
   WWARA's current, pending, about-to-expire and expired lists. It exits
   non-zero on any error.
3. Fix an error where the data comes from (the catalog module, recipe or
   source adapter), never by editing an exported file. Re-export with
   `fleet export --all` and audit again.

## Rules the audit enforces

- **Transmit follows the service, not the block.** Amateur channels (inside
  General privileges), GMRS/FRS and MURS transmit on every radio whose hardware
  covers them, whichever block or zone holds them. A repeater with no usable
  input transmits simplex. Everything else - public safety, business, marine,
  air, rail, weather - is receive only. Never add a receive-only exception for
  a licensed channel: the TH-D75 enforces receive-only with an out-of-band split
  that makes the radio beep and refuse PTT.
- **A repeater is named by the call WWARA coordinates its pair to**, with the
  club or net in the channel note. Its access tone is WWARA's `CTCSS_IN`.
- **D-STAR memory names are routing calls** (`N7IH   C`); do not rename them to
  the licensee.
- Two machines can share a pair on different tones: a memory's name must match
  the record whose input and tone it carries.
