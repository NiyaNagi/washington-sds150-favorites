# NanoVNA measurement tools

This directory contains the acquisition and validation tools used for the
calibrated antenna evidence packages in this repository.

## Environment

The August 2026 sessions ran with:

- Python 3.9.6
- NumPy 2.0.2
- Matplotlib 3.9.4
- pySerial 3.5
- NanoVNA-H firmware 1.2.50

Create an isolated environment from the repository root:

```bash
python3 -m venv .venv-nanovna
.venv-nanovna/bin/pip install -r antenna-results/tools/requirements-nanovna.txt
```

## Acquisition

`nanovna_swr_session_2026_08.py` is the byte-exact high-resolution one-port
acquisition engine used for the August 2026 OSL calibrations and sweeps.
`nanovna_swr.py` is the operational entry point: it delegates to that exact
engine while rejecting nonfinite raw/calibration/corrected values and passive
measurements with `|Gamma| >= 1` before artifacts are written.

```bash
.venv-nanovna/bin/python antenna-results/tools/nanovna_swr.py self-test
.venv-nanovna/bin/python antenna-results/tools/nanovna_swr.py status
```

The `status` output must report `bandwidth 3 (1000Hz)` for the documented
profile. The tool reads and records bandwidth but deliberately does not change
the VNA's persistent device setting.

The tool:

- talks to `/dev/cu.usbmodem4001` at 115200 baud by default;
- requests raw S11 with `scan ... 101 0b011`;
- disables NanoVNA internal correction during each raw capture;
- stitches overlapping 101-point segments while removing duplicate endpoints;
- solves a software ideal one-port OPEN/SHORT/LOAD calibration;
- writes raw NPZ/CSV, calibrated RI Touchstone, point CSV, summary JSON, and
  basic SWR charts.

The hardened entry point stages a complete DUT run and publishes it with a
directory swap plus rollback backup. A successful future run contains
`run-status.json`; a derived-data failure is preserved only under an explicit
`.rejected-TIMESTAMP` directory. Standard captures use an in-progress/rejected
marker and atomic NPZ/CSV replacement, and calibration solve refuses any such
marker. Rollback directories carry a tool-ownership marker; an unknown
preexisting backup is refused and never recursively deleted.

Use `--port` on `status`, `capture`, or `measure` when the serial device differs.

## Validation

`validate_nanovna_run.py` formalizes the checks that were originally run as
inline Python during the sessions:

```bash
.venv-nanovna/bin/python antenna-results/tools/validate_nanovna_run.py \
  --calibration-dir path/to/calibration \
  --load-verification-dir path/to/calibration/load-verification \
  --open-path-dir path/to/far-end-open \
  --measurement-dir path/to/sweep-1 \
  --repeat-dir path/to/sweep-2 \
  --start-hz 500000 \
  --stop-hz 54000000 \
  --points 40001 \
  --output path/to/validation.json
```

Defaults intentionally fail closed:

- all standards, calibration terms, measurements, and repeats must share an
  exact, strictly increasing frequency grid;
- each pair of calibration standards must have median raw complex separation
  of at least 0.2;
- solved directivity, source-match, and reflection-tracking terms must
  numerically match terms recomputed from the packaged raw standards;
- every field used by a quality gate must be finite; NaN and infinity fail;
- calibrated CSV and RI Touchstone values must match S11 recomputed from each
  packaged `antenna_raw.npz` and the validated calibration terms;
- Touchstone options must be exactly `# Hz S RI R 50`, and every CSV column
  including MHz frequency and phase must match recomputed values;
- reconnected-load median/p95/maximum SWR must be at most 1.01/1.02/1.10;
- calibrated antenna samples must be finite with `|Gamma| < 1`;
- far-end-open median `|Gamma|` must be at least 0.5 when that diagnostic is
  requested;
- repeat median complex-S11 and SWR deltas must be at most 0.005 and 0.05.

These are session-quality gates, not metrology traceability claims. Override a
threshold only with a documented instrument/fixture reason.
Successful validation reports include SHA-256 identities for every bound
evidence file. The validator removes any prior success report before checking
and atomically publishes the replacement, so a failed rerun cannot leave stale
`"status": "passed"` evidence.

Run the standalone targeted tests:

```bash
.venv-nanovna/bin/python antenna-results/tools/test_nanovna_tools.py -v
```

They cover calibration-solver recovery, nonfinite scan rejection, stale solved
calibration, interior grid drift, nonfinite CLI thresholds, and
raw-NPZ-to-CSV/Touchstone evidence binding.

## Analysis generators

The report generators remain next to their data because they encode the exact
antenna model, bands, configuration, comparison provenance, and visual contract:

- `antennas/gowenic-efhw/generate_report.py`
- `antennas/gowenic-efhw/installed-office-feed/generate_report.py`
- `antennas/jyr8010-efhw/generate_report.py`
- `antennas/jyr8010-efhw/two-choke-office-feed/generate_report.py`
- `tools/generate_scanner_antenna_report.py`

Each EFHW deployment generator supports deterministic regeneration from its
packaged inputs and publishes through a staged directory swap so a failed run
does not destroy its evidence.

## Archived session helpers

[`session-helpers/`](session-helpers/) contains byte-exact copies of the
surviving local August 2026 helper scripts. They are retained to satisfy the
session audit trail, not as recommended interfaces.
