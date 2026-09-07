# Calibrated NanoVNA antenna-deployment methodology

This is the complete, normative method used to create the calibrated antenna
evidence packages in this repository. It covers acquisition, software OSL
calibration, quality gates, installed-feed diagnostics, repeatability,
analysis, visualization, interpretation, preservation, review, and publication.

The corresponding record of what happened during the August 2026 sessions is
[`2026-08-EFHW-SESSION-RECORD.md`](2026-08-EFHW-SESSION-RECORD.md). The
copy-paste prompt for another LLM is
[`../prompts/REPEAT-ANTENNA-DEPLOYMENT.md`](../prompts/REPEAT-ANTENNA-DEPLOYMENT.md).
Exact runtime versions and SHA-256 file identities are in
[`TOOLCHAIN-MANIFEST.json`](TOOLCHAIN-MANIFEST.json).

## 1. Scope and measurement claim

The method measures calibrated one-port complex S11 at a declared reference
plane. It derives:

- reflection coefficient magnitude and phase;
- SWR;
- return loss;
- complex input impedance;
- minimum, median, and maximum SWR inside defined frequency windows;
- impedance and return loss at the minimum-SWR point;
- percentage of a window at or below SWR 1.5, 2.0, and 3.0;
- longest contiguous range meeting each threshold;
- point-level and band-level repeatability.

It does **not** directly measure:

- radiated power, gain, radiation efficiency, pattern, polarization, or field
  strength;
- receiver sensitivity, decode rate, or received noise floor;
- common-mode current or a choke's common-mode impedance;
- two-port cable/transition insertion loss;
- traceable absolute impedance accuracy.

A low radio-end SWR can be caused by a good antenna match, transmission-line
phase transformation, or loss that attenuates the reflected wave. State the
reference plane and every intervening component before interpreting a result.

The core protocol characterizes an already deployed antenna. When a new build
must first be tuned, use the optional controlled tuning loop in section 10.1,
then perform a fresh final characterization without substituting the tuning
traces for final evidence.

## 2. Terminology

**Reference plane** is the physical connector where OPEN, SHORT, and LOAD are
attached. The calibration removes systematic one-port error only up to this
plane.

**Antenna-feedpoint result** applies only when the VNA calibration plane is
directly at the antenna input and no unmodeled line remains between them.

**Installed-system result** is measured at the radio/VNA end of a complete
feed path. It includes all coax, adapters, transitions, chokes, connectors,
counterpoise interaction, and the antenna.

**Historical comparison** compares runs whose uncontrolled variables differ.
It can report observed deltas but cannot establish causation.

**Controlled A/B comparison** changes exactly one declared variable while
holding the antenna, support geometry, counterpoise, feed line, connector
torque, cable routing, reference plane, calibration, environment, and timing
constant. Run A and B consecutively under one verified calibration.

## 3. Hardware and software used

The August 2026 sessions used:

- NanoVNA-H;
- firmware 1.2.50, with the device status response reporting a May 16, 2026
  build;
- CH0/Port 1 for S11;
- 115200-baud USB serial;
- NanoVNA command protocol with 101 points per scan segment;
- device-reported 1 kHz measurement bandwidth;
- ideal OPEN, SHORT, and 50-ohm LOAD standards;
- Python 3.9.6;
- NumPy 2.0.2;
- Matplotlib 3.9.4;
- pySerial 3.5;
- macOS serial device `/dev/cu.usbmodem4001`.

Install the exact Python dependencies:

```bash
python3 -m venv .venv-nanovna
.venv-nanovna/bin/pip install \
  -r antenna-results/tools/requirements-nanovna.txt
```

Run the calibration solver self-test before hardware work:

```bash
.venv-nanovna/bin/python \
  antenna-results/tools/nanovna_swr.py self-test
```

Check the connected VNA:

```bash
.venv-nanovna/bin/python \
  antenna-results/tools/nanovna_swr.py status
```

Pass `--port /path/to/serial-device` when the default port is not correct.
Before every calibration, confirm the status response reports
`bandwidth 3 (1000Hz)`. The acquisition tool records but does not change this
device state. If the VNA reports a different bandwidth, stop and set 1 kHz on
the device before capturing any standard.

## 4. Safety and physical controls

1. Disconnect all transmitters before attaching the VNA.
2. Never transmit into a VNA, calibration standard, disconnected/open feed
   line, or a person working on the antenna.
3. Turn the radio off before changing RF connections.
4. Keep antenna wire, ropes, and supports farther from power lines than their
   full possible falling length.
5. Treat EFHW radiator ends and transformer terminals as high-voltage points
   during transmission.
6. Keep people and animals away from the radiator and counterpoise during
   transmission; perform the required RF-exposure evaluation separately.
7. The counterpoise is not lightning protection. Disconnect during storms and
   use a properly bonded entrance arrestor for permanent installations.
8. Preserve strain relief, weather sealing, and trip-hazard marking.
9. Record the lowest-rated component. The 10 W GOWENIC transformer was treated
   as a 10 W maximum component, with about 5 W preferred for continuous-duty
   digital operation.

## 5. Metadata to capture before measurement

Do not begin until these facts are recorded:

- antenna manufacturer, model, type, product link, and rated power;
- radiator physical length, material, and any loops/folds;
- support geometry: endpoint heights, horizontal arrangement, slope, and
  nearby conductive objects;
- ground/counterpoise length, connection point, orientation, and height;
- every feed-line section in order from VNA/radio to antenna:
  cable type, length, adapters, transitions, switches, arrestors, and chokes;
- choke location, coax type/length, turn count, core material, and core size;
- indoor/outdoor routing and nearby powered equipment;
- weather and ground state when relevant;
- exact calibration reference plane;
- comparison goal and whether it is controlled A/B or historical;
- sweep start, stop, segment count, point count, and bandwidth;
- timezone and local timestamps.

Never fill an unknown with an inference. Write `unknown` and explain the
comparison limitation.

## 6. Sweep design

The NanoVNA returns 101 points per scan command. The capture engine uses
contiguous overlapping segments and drops the first point of every segment
after the first. For `S` segments:

```text
unique_points = S * (101 - 1) + 1
nominal_step_hz = (stop_hz - start_hz) / (S * 100)
```

Standard profiles:

| Profile | Start | Stop | Segments | Unique points | Nominal step |
|---|---:|---:|---:|---:|---:|
| HF through 6m | 0.5 MHz | 54 MHz | 400 | 40,001 | 1,337.5 Hz |
| 160m through 2m | 1.8 MHz | 148 MHz | 400 | 40,001 | 3,655 Hz |

The tool rejects:

- a segment returning other than 101 rows;
- a row other than frequency, S11 real, S11 imaginary;
- a final point count different from the formula;
- non-increasing frequencies;
- a measurement frequency grid different from its calibration grid.

## 7. Raw capture behavior

`antenna-results/tools/nanovna_swr.py` sends:

```text
scan START STOP 101 0b011
```

Every raw standard or DUT capture is wrapped by:

```text
cal off
... raw scans ...
cal on
```

This preserves the VNA's saved calibration but prevents it from being applied
inside the raw data used by the software OSL solver. The saved device
calibration is therefore not the evidence calibration.

The capture is written only after all segments finish. A timeout mid-sweep does
not produce a valid partial NPZ/CSV or Touchstone result.

The byte-exact historical engine is preserved as
`nanovna_swr_session_2026_08.py`. New runs use the hardened `nanovna_swr.py`
entry point, which validates floating-point scan fields before frequency
conversion, rejects nonfinite calibration/corrected values, stages the complete
run, writes `run-status.json`, and atomically publishes the run directory with
rollback. Failed derived output is placed only in an explicitly named rejected
directory.

## 8. Software one-port OSL calibration

At each frequency, the measurement model is:

```text
m = Ed + Er * Gamma / (1 - Es * Gamma)
```

where:

- `m` is measured raw S11;
- `Gamma` is the actual reflection coefficient;
- `Ed` is directivity error;
- `Es` is source-match error;
- `Er` is reflection-tracking error.

The ideal standards are:

```text
OPEN  Gamma = +1
SHORT Gamma = -1
LOAD  Gamma =  0
```

The implemented solution is:

```text
Ed = load
open_delta = open - Ed
short_delta = short - Ed
denominator = open_delta - short_delta
Es = (open_delta + short_delta) / denominator
Er = open_delta * (1 - Es)
```

Correction is:

```text
delta = measured - Ed
Gamma = delta / (Er + Es * delta)
```

The solver rejects singular standard combinations and near-zero reflection
tracking.

### Calibration command sequence

Set a unique directory name before starting:

```bash
CAL=nanovna_measurements/YYYY-MM-DD_HHMM_antenna_calibration
PY=.venv-nanovna/bin/python
TOOL=antenna-results/tools/nanovna_swr.py
```

Connect OPEN at the final reference plane:

```bash
$PY $TOOL capture open \
  --start 500000 --stop 54000000 --segments 400 \
  --output-dir "$CAL"
```

Connect the verified SHORT at exactly the same plane:

```bash
$PY $TOOL capture short \
  --start 500000 --stop 54000000 --segments 400 \
  --output-dir "$CAL"
```

Connect the 50-ohm LOAD:

```bash
$PY $TOOL capture load \
  --start 500000 --stop 54000000 --segments 400 \
  --output-dir "$CAL"

$PY $TOOL calibrate --calibration-dir "$CAL"
```

For 1.8-148 MHz, change start/stop to `1800000` and `148000000`.

## 9. Calibration-standard quality gate

Validate raw standards **before** trusting the solved calibration.

All three captures must have:

- identical frequencies;
- the expected start, stop, and point count;
- strictly increasing frequency;
- meaningful pairwise complex separation.

The reusable validator defaults to a minimum median pairwise raw separation of
0.2. In the verified August 23 and August 28 HF-through-6m calibrations,
OPEN-to-SHORT separation was about 1.538.

The August 23 first SHORT was accidentally open-like:

The value below is a contemporaneous session-log observation; the invalid raw
SHORT was overwritten during correction and is not reproducible from the
preserved package:

```text
OPEN-to-SHORT median raw separation: 0.046
```

That bad calibration made both an attached antenna and a far-end-open 100 ft
feed line look nearly 50 ohms across the whole span. The impossible physical
result triggered investigation. After recapturing only SHORT:

```text
OPEN-to-SHORT median raw separation: 1.538
```

The calibration was recomputed and every dependent verification/diagnostic/DUT
sweep was repeated. Never retain a result derived from a failed standard.

The standards can be checked immediately:

```bash
python3 - <<'PY'
import numpy as np
from pathlib import Path

base = Path("REPLACE_WITH_CALIBRATION_DIR")
data = {
    name: np.load(base / f"{name}.npz")["s11_raw"]
    for name in ("open", "short", "load")
}
for first, second in (
    ("open", "short"),
    ("open", "load"),
    ("short", "load"),
):
    delta = np.abs(data[first] - data[second])
    print(first, second, "median", np.median(delta))
PY
```

## 10. Independent reconnected-load verification

The LOAD used to solve OSL must be physically removed and reconnected before
verification. This exercises connector repeatability and short-term drift.

```bash
$PY $TOOL measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir "$CAL/load-verification"
```

Default acceptance thresholds in `validate_nanovna_run.py`:

| Metric | Maximum |
|---|---:|
| Median SWR | 1.01 |
| 95th-percentile SWR | 1.02 |
| Maximum SWR | 1.10 |

These gates are intentionally generous compared with the verified runs:

| Session | Median | p95 | Maximum |
|---|---:|---:|---:|
| GOWENIC office path, Aug 23 | 1.00009 | 1.00030 | 1.00047 |
| JYR8010 two-choke, Aug 28 | 1.00075 | 1.00087 | 1.00106 |

Because the same LOAD is used for calibration and verification, this proves
stability and reconnect repeatability - not independent traceable accuracy.

### 10.1 Optional tune-to-target loop

Use this only when the deployment itself still needs adjustment:

1. Choose the target band and a focused scan spanning below and above the
   observed resonance.
2. Record the complete starting geometry and physical conductor length.
3. Change exactly one reversible variable at a time: fold/loop length, support
   height, slope, counterpoise, or feed-line route.
4. Capture complex S11 after each change on an unchanged frequency grid.
5. Record amount changed, cumulative amount, resonance frequency, minimum SWR,
   impedance at minimum, and band-edge SWR.
6. Use small increments as resonance approaches the target. Do not infer a
   final cut from a single large trim.
7. Prefer reversible folds/loops before permanently removing wire.
8. If changing wire length, preserve every removed length and cumulative total
   in the run history.
9. Confirm the apparent final state with an unchanged repeat.
10. Once the build is final, capture fresh full-span OSL/load verification and
    the two final DUT sweeps required by this methodology.

The August 17 GOWENIC sequence is the worked example: 22 in, then 30 in, then
8 in were removed; redeploying from an 8 ft inverted V to a 25-to-3 ft sloper
caused a larger final resonance shift than the small mechanical loop change.
This demonstrated why length and deployment geometry must remain separate
variables in the tuning log.

## 11. Far-end-open installed-feed diagnostic

For a long installed path:

1. connect the complete feed path to CH0;
2. disconnect the antenna/transformer at the far end;
3. leave the far end of the final cable or feedpoint choke open;
4. capture a calibrated full-span sweep.

```bash
$PY $TOOL measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir "$OPEN_PATH"
```

A real open low-loss line should produce a large reflection. The validator
defaults to median `|Gamma| >= 0.5`.

This diagnostic caught the invalid August 23 calibration: the supposed open
100 ft line initially looked approximately 50 ohms. Under the corrected
calibration, median `|Gamma|` was 0.834.

For an ideal open on a uniform, well-matched line:

```text
round_trip_attenuation_db = -20 * log10(|Gamma|)
apparent_one_way_attenuation_db = round_trip_attenuation_db / 2
```

Do not call this measured insertion loss when the path includes adapters,
window ribbon, connectors, switches, or chokes. Those discontinuities create
multiple reflections. A two-port calibrated measurement is required for
insertion loss. A one-port open-path test also does not measure choke
common-mode impedance.

## 12. DUT and repeatability captures

Reconnect the antenna without moving:

- radiator or supports;
- transformer;
- counterpoise;
- chokes;
- feed line or window transition;
- VNA reference-plane adapter;
- nearby powered equipment.

Capture the first full sweep:

```bash
$PY $TOOL measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir "$RUN1"
```

Capture a second unchanged sweep:

```bash
$PY $TOOL measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir "$RUN2"
```

Average complex S11:

```text
Gamma_average = (Gamma_run1 + Gamma_run2) / 2
```

Never average SWR, impedance magnitude, or dB values when complex S11 is
available.

Default repeatability gates:

| Metric | Maximum median |
|---|---:|
| `abs(Gamma_run1 - Gamma_run2)` | 0.005 |
| `abs(SWR_run1 - SWR_run2)` | 0.05 |

The August 28 JYR8010 pair achieved median complex delta 0.00036 and median SWR
delta 0.00085.

## 13. Derived metrics

For calibrated complex reflection coefficient `Gamma` and `Z0 = 50 ohms`:

```text
rho = abs(Gamma)
SWR = (1 + rho) / (1 - rho), for rho < 1
return_loss_db = -20 * log10(rho)
Z = Z0 * (1 + Gamma) / (1 - Gamma)
R = real(Z)
X = imag(Z)
phase_degrees = angle(Gamma)
```

Report per band/window:

- lower and upper frequency;
- sample count and step;
- minimum, median, and maximum SWR;
- minimum-SWR frequency;
- return loss, resistance, and reactance at that point;
- percent of sampled points at SWR <= 1.5, <= 2.0, and <= 3.0;
- every contiguous passing interval;
- longest contiguous interval at each threshold;
- rating derived from full-window maximum and coverage.

Use actual US license allocations for regulatory claims. The continuous
5.3305-5.4064 MHz 60m span is an analysis envelope; US 60m operation is
channelized and not authorized continuously throughout that envelope.

## 14. Visualization contract

An EFHW deployment package should include:

- full-span SWR and return-loss comparison;
- supported-band SWR zooms with band edges and minima;
- impedance plots with the true reference plane in the title;
- return-loss plots;
- Smith chart;
- minimum/maximum SWR and <=2:1 coverage scorecard;
- usable contiguous bandwidth by threshold;
- physical feed/antenna layout;
- repeatability chart;
- far-end-open diagnostic;
- historical or A/B change chart;
- self-contained interactive HTML with no network dependency.

Every chart must label:

- antenna/configuration;
- reference plane;
- whether values are clipped;
- comparison provenance;
- series legend;
- frequency units.

The HTML must identify the correct point spacing and must not inherit unrelated
scanner-specific notes from another report.

## 15. Comparison discipline

Before writing "the choke changed X," verify that the comparison held constant:

- antenna and radiator;
- antenna geometry;
- ground/counterpoise;
- coax type and electrical length;
- transitions/connectors;
- reference plane;
- OSL calibration;
- frequency span, frequency grid, and point spacing;
- cable routing;
- nearby equipment;
- weather/ground conditions;
- elapsed time.

If any differ, use:

> The current installed system differs by ... . The table precisely reports
> observed input-impedance changes, but those changes cannot be attributed to
> one component.

The August 28 JYR8010 comparison was explicitly not a controlled choke A/B. It
also added 6 ft of RG8X, connectors, a 16 ft counterpoise, a documented office
feed path, a different date, a different calibration, and a 1.3375 kHz grid
instead of the historical 3.655 kHz grid. Its open-path baseline was cross-day
and cross-calibration.

## 16. RFI interpretation

Office computer equipment can raise receiver noise or inject signals into the
system. A stable passive S11 transformation does not prove that ambient RFI
caused the change. To evaluate RFI:

- record receiver noise floor by band with equipment on/off;
- use fixed receiver settings and bandwidth;
- measure common-mode current with an RF current probe if available;
- perform controlled choke A/B tests under one calibration;
- use a spectrum analyzer or receiver capture for noise signatures.

Do not infer RFI improvement from SWR alone.

## 17. Failure handling

### Invalid standard

Symptoms:

- OPEN and SHORT raw traces are insufficiently separated;
- an antenna and a far-end-open line both look nearly 50 ohms;
- implausibly flat near-1:1 SWR across unrelated bands.

Action:

1. reject all dependent results;
2. verify standard identity visually/electrically;
3. recapture only the bad standard on the same frequency grid;
4. recompute OSL;
5. physically reconnect LOAD and reverify;
6. repeat open-path and every DUT sweep.

### NanoVNA serial/firmware timeout

In the August 28 session the VNA stopped answering after segment 150 and then
timed out while restoring `cal on`.

Action:

1. do not accept partial data;
2. test `status`;
3. if USB reconnection does not recover it, use the physical power switch
   because the internal battery can keep the firmware hung;
4. leave the RF adapter and entire DUT path untouched;
5. verify `status` again;
6. restart the sweep from segment 1;
7. capture an unchanged repeat afterward.

The saved software OSL remains valid after a VNA power cycle only if the VNA,
port, adapter chain, reference plane, frequency grid, and physical connection
remain unchanged. If uncertain, recalibrate.

### Impossible result

Do not rationalize a physically impossible result. Add a discriminating
diagnostic:

- reconnect LOAD;
- far-end open;
- far-end short;
- direct known load;
- controlled cable section;
- repeat sweep.

Preserve rejected raw captures when possible. If they were overwritten, say so
and do not quote unverifiable exact values in the final package.

## 18. Evidence preservation

Store:

- `open.npz/csv`, `short.npz/csv`, `load.npz/csv`;
- solved `calibration.npz`;
- full reconnect-verification NPZ/CSV/S1P/summary/charts;
- far-end-open NPZ/CSV/S1P/summary/charts;
- at least two DUT NPZ/CSV/S1P/summary/charts;
- complex-averaged S1P;
- per-point supported-band CSV;
- band summary CSV/JSON;
- repeatability JSON;
- comparison CSV/JSON;
- metadata JSON;
- static charts;
- self-contained interactive HTML;
- deterministic generator and requirements;
- README with caveats and exact regeneration command.

Use immutable timestamped source directories. Generate reports into staging and
atomically replace the package only after success. Preserve a recoverable
sibling backup during the final swap.

## 19. Validation command

Example for the August 28 JYR8010 run:

```bash
python3 antenna-results/tools/validate_nanovna_run.py \
  --calibration-dir \
    antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/calibration \
  --load-verification-dir \
    antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/calibration/load-verification \
  --open-path-dir \
    antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/choked-far-end-open \
  --measurement-dir \
    antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/current-sweep-1 \
  --repeat-dir \
    antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/measurements/current-sweep-2 \
  --start-hz 500000 \
  --stop-hz 54000000 \
  --points 40001
```

Always point final validation at the **packaged copies** of calibration,
verification, diagnostics, and DUT runs. Validating only the disposable source
directories does not prove that publication copied the evidence correctly.

Also run:

1. `nanovna_swr.py self-test`;
2. validator corruption tests proving NaN, stale solved-calibration terms, and
   interior frequency-grid drift are rejected, and proving raw NPZ, calibrated
   CSV, canonical RI Touchstone, and every derived CSV column remain bound;
3. Python compilation for every changed generator;
4. `git diff --check`;
5. deterministic packaged-input regeneration with pre/post SHA-256 comparison;
6. intentional failed generation to confirm packaged evidence survives;
7. stale-file injection to confirm generated directories are replaced;
8. data assertions for band count, point count, metadata, S1P row count, and
   comparison provenance;
9. browser load, console-error check, selector interaction, desktop screenshot,
   and mobile-width layout check;
10. focused read-only code review;
11. the repository's configured test suite.

If an unrelated repository defect blocks the full suite, report the exact
error and still complete all targeted antenna-package validations. Do not claim
the full suite passed.

## 20. Publication procedure

1. Fetch `origin/main`.
2. Confirm the working tree contains only intended changes.
3. Update `antenna-results/README.md` and `CHANGELOG.md`.
4. Stage all raw evidence, generated reports, tooling, and documentation.
5. Run `git diff --cached --check`.
6. Commit with the required co-author trailer.
7. If `origin/main` advanced, rebase the single measurement commit and merge
   both changelog histories.
8. Re-run integrated assertions.
9. Push directly to `main` only when explicitly requested.
10. Fetch again and confirm local `HEAD == origin/main`.

Never force-push over unrelated work.

## 21. Script inventory

### Acquisition and validation

- `antenna-results/tools/nanovna_swr_session_2026_08.py`: byte-exact
  capture/calibration engine used during the sessions.
- `antenna-results/tools/nanovna_swr.py`: hardened operational wrapper around
  the session-exact engine for future captures.
- `antenna-results/tools/validate_nanovna_run.py`: codified form of the inline
  validation checks used throughout the sessions.
- `antenna-results/tools/test_nanovna_tools.py`: standalone targeted corruption
  and evidence-binding tests for the acquisition/validation toolchain.
- `antenna-results/tools/requirements-nanovna.txt`: exact runtime versions.

### Report generation used

- `antenna-results/antennas/gowenic-efhw/generate_report.py`
- `antenna-results/antennas/gowenic-efhw/installed-office-feed/generate_report.py`
- `antenna-results/antennas/jyr8010-efhw/generate_report.py`
- `antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/generate_report.py`

### Other repository antenna tooling

- `antenna-results/tools/generate_scanner_antenna_report.py`

### Archived session-specific helpers

- `antenna-results/tools/session-helpers/capture_scanner_zooms.py`
- `antenna-results/tools/session-helpers/retest_bands.py`
- `antenna-results/tools/session-helpers/verify_load.py`

These are byte-exact archives of the surviving local helpers. They were not
used for the final August 23 or August 28 EFHW installed-system evidence and
retain hard-coded assumptions/paths, so they are audit artifacts rather than
recommended entry points. Their useful quality checks are incorporated into
the validator and packaged report generators.
