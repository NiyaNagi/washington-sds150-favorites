# Prompt: repeat a calibrated antenna deployment with another LLM

Copy everything below into a new LLM session. Replace bracketed placeholders
only when you already know the value. Leave unknowns as `UNKNOWN`; the LLM must
ask rather than guess.

---

You are performing a rigorous, reproducible one-port NanoVNA characterization
of an antenna deployment and must persist the complete evidence package in the
`washington-sds150-favorites` repository.

## Objective

Measure `[ANTENNA_MODEL]` in `[DEPLOYMENT_DESCRIPTION]` from `[START_HZ]` through
`[STOP_HZ]` at high resolution. Produce the same evidence quality, calculations,
visuals, diagnostics, repeatability, deterministic generation, documentation,
review, and repository publication used by:

- `antenna-results/antennas/gowenic-efhw/installed-office-feed/`
- `antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/`
- `antenna-results/docs/NANOVNA-DEPLOYMENT-METHODOLOGY.md`

Do not merely explain how to do this. Operate the connected NanoVNA, capture the
data, validate it, generate the package, test it, and commit/push only when the
user explicitly authorizes publication.

By default, characterize an already deployed antenna. If the user also wants
to tune a new build, run the optional tune-to-target phase below before the
fresh final characterization.

## Non-negotiable interaction rules

1. Read the repository and methodology before asking questions.
2. Ask only unresolved physical/configuration questions.
3. Present discrete connection confirmations as clickable choices when the
   interface supports them, always retaining an `Other` path.
4. Stop after each physical-action question and wait for the user.
5. Never assume OPEN, SHORT, LOAD, CH0, counterpoise placement, choke placement,
   cable length, or antenna geometry.
6. Do not redo a valid completed capture unless a later quality gate invalidates
   it.
7. Keep the user informed only at major phase changes.

## Safety

- Confirm every transmitter is disconnected before VNA attachment.
- Never ask the user to transmit into the VNA, a calibration standard, or an
  open feed line.
- Keep RF hardware untouched during calibration and repeated DUT sweeps.
- Warn about power-line, lightning, RF-exposure, high-voltage EFHW end,
  weatherproofing, strain-relief, and trip hazards when applicable.
- Record the lowest-rated RF component and do not recommend exceeding it.

## Inputs to resolve

Ask for and record:

- antenna make/model/type/product link/rated power;
- radiator material and exact physical length;
- folds, loops, loading coils, traps, or transformer ratio;
- support geometry and endpoint heights;
- counterpoise/ground length, route, height, and exact connection;
- every feed-path section in VNA-to-antenna order:
  cable type/length, adapters, arrestors, switches, ribbon transitions;
- each choke's exact location, coax type, coax length, turns, core mix, and core
  size;
- indoor/outdoor routing, nearby conductive objects, and powered equipment;
- weather/ground conditions if comparisons span time;
- exact VNA adapter/reference plane;
- whether the requested comparison is controlled A/B or historical;
- repository output slug;
- whether direct commit/push to main is authorized.

If the user asks what one component changed but other variables also changed,
state before measurement that only combined system-level change can be reported.
Offer a fresh controlled A/B as the recommended option.

## Repository and tool discovery

Work from the repository root. Read:

```text
antenna-results/README.md
antenna-results/docs/NANOVNA-DEPLOYMENT-METHODOLOGY.md
antenna-results/tools/README.md
antenna-results/tools/nanovna_swr.py
antenna-results/tools/validate_nanovna_run.py
```

Read the closest existing antenna package and reuse its:

- band definitions;
- summary schema;
- chart style;
- interactive-report structure;
- metadata conventions;
- atomic staged-publication pattern.

Do not modify unrelated code or generated packages.

## Environment

Use:

```bash
python3 -m venv .venv-nanovna
.venv-nanovna/bin/pip install \
  -r antenna-results/tools/requirements-nanovna.txt
```

Then:

```bash
PY=.venv-nanovna/bin/python
TOOL=antenna-results/tools/nanovna_swr.py
$PY $TOOL self-test
$PY $TOOL status [--port PORT]
```

Expected reference environment:

- Python 3.9.6 or compatible;
- NumPy 2.0.2;
- Matplotlib 3.9.4;
- pySerial 3.5;
- NanoVNA-H firmware 1.2.50;
- 1 kHz device bandwidth.

Record actual versions rather than silently claiming these if they differ.
Require the `status` response to report `bandwidth 3 (1000Hz)` before
calibration. The capture tool reads but does not set bandwidth; if it differs,
stop and have the operator set 1 kHz on the NanoVNA before continuing.

## Sweep profile

Default HF-through-6m profile:

```text
START_HZ=500000
STOP_HZ=54000000
SEGMENTS=400
POINTS=40001
NOMINAL_STEP_HZ=1337.5
```

Default 160m-through-2m profile:

```text
START_HZ=1800000
STOP_HZ=148000000
SEGMENTS=400
POINTS=40001
NOMINAL_STEP_HZ=3655
```

Use 400 overlapping 101-point segments. The capture script removes duplicated
segment endpoints. Do not substitute a coarse 101-point whole-span sweep.

## Phase 1: fresh OSL calibration

Choose immutable timestamped paths:

```bash
CAL=nanovna_measurements/YYYY-MM-DD_HHMM_[SLUG]_calibration
RUN1=nanovna_measurements/YYYY-MM-DD_HHMM_[SLUG]_sweep_1
RUN2=nanovna_measurements/YYYY-MM-DD_HHMM_[SLUG]_sweep_2
OPEN_PATH=nanovna_measurements/YYYY-MM-DD_HHMM_[SLUG]_far_end_open
```

The standards attach directly to CH0/Port 1 at the unchanged final VNA adapter
reference plane, not at the antenna end of the feed line.

Ask the user to connect OPEN, wait, then run:

```bash
$PY $TOOL capture open \
  --start $START_HZ --stop $STOP_HZ --segments 400 \
  --output-dir "$CAL"
```

Ask for verified SHORT. Explicitly say that its center pin must be bonded to the
shell. Wait, then run:

```bash
$PY $TOOL capture short \
  --start $START_HZ --stop $STOP_HZ --segments 400 \
  --output-dir "$CAL"
```

Immediately validate OPEN/SHORT frequency-grid equality and raw complex
separation. They should be clearly distinct; known good HF sessions were about
1.538. Do not continue if the two standards are insufficiently separated.

Ask for LOAD, wait, then run:

```bash
$PY $TOOL capture load \
  --start $START_HZ --stop $STOP_HZ --segments 400 \
  --output-dir "$CAL"

$PY - <<'PY'
import numpy as np
from pathlib import Path

base = Path("REPLACE_WITH_CALIBRATION_DIR")
captures = {
    name: np.load(base / f"{name}.npz")
    for name in ("open", "short", "load")
}
reference = captures["open"]["frequencies_hz"]
for name, capture in captures.items():
    if not np.array_equal(reference, capture["frequencies_hz"]):
        raise SystemExit(f"{name} frequency grid differs from OPEN")
for first, second in (("open", "short"), ("open", "load"), ("short", "load")):
    separation = np.median(
        np.abs(captures[first]["s11_raw"] - captures[second]["s11_raw"])
    )
    print(first, second, separation)
    if not np.isfinite(separation) or separation < 0.2:
        raise SystemExit(f"{first}/{second} standards insufficiently separated")
PY

$PY $TOOL calibrate --calibration-dir "$CAL"
```

Run this complete three-standard grid/separation gate after LOAD and before
solving calibration. Do not rely only on the earlier OPEN/SHORT check.

## Phase 2: independent LOAD reconnect verification

Ask the user to physically remove and firmly reconnect LOAD at the same plane.
Wait, then:

```bash
$PY $TOOL measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir "$CAL/load-verification"
```

Fail closed if:

- median SWR > 1.01;
- p95 SWR > 1.02;
- maximum SWR > 1.10;
- frequency grid or point count differs.

State that reuse of the same LOAD proves reconnect stability/drift, not
independent traceability.

## Optional phase 2.5: tune a new deployment

Use only when the antenna is not yet in its final physical state:

1. Select a focused range around the target-band resonance.
2. Record exact physical wire length and deployment geometry.
3. Change one reversible variable at a time.
4. After each change, capture complex S11 on the same frequency grid and record
   the change amount, cumulative amount, resonance, minimum SWR, impedance, and
   band-edge values.
5. Use progressively smaller adjustments near target.
6. Prefer folds or loops before permanent cuts.
7. Run an unchanged focused repeat at the apparent final state.
8. Then discard the focused calibration as final evidence and return to Phase
   1 for a fresh full-span OSL, verification, diagnostics, and two final sweeps.

Use `antenna-results/docs/2026-08-EFHW-SESSION-RECORD.md` section 3 as the
worked trim/redeployment example.

## Phase 3: far-end-open path diagnostic

For an installed feed system, ask the user to connect the complete feed path to
CH0 but disconnect the antenna/transformer at the far end. Chokes and
transitions that are part of the tested path must remain present.

Run:

```bash
$PY $TOOL measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir "$OPEN_PATH"
```

Require physically plausible reflection; default median `|Gamma| >= 0.5`.

If an open long line looks near 50 ohms across the span:

1. reject the calibration and every dependent result;
2. inspect standard identity and CH0 connection;
3. compare raw OPEN/SHORT/LOAD separation;
4. recapture the bad standard on the identical frequency grid;
5. re-solve OSL;
6. redo LOAD verification, open-path, and DUT sweeps.

For an ideal open/uniform line only:

```text
apparent_one_way_attenuation_db = -20*log10(|Gamma|)/2
```

Call this a plausibility diagnostic - not insertion loss - when discontinuities are
present. Do not claim it measures choke common-mode impedance.

## Phase 4: two unchanged DUT sweeps

Ask the user to reconnect the complete antenna deployment and keep everything
undisturbed.

Run:

```bash
$PY $TOOL measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir "$RUN1"

$PY $TOOL measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir "$RUN2"
```

If the VNA hangs:

- reject partial output;
- probe `status`;
- remember USB removal may not reboot a battery-powered NanoVNA;
- physically power-cycle it while leaving the RF path untouched;
- verify status;
- restart from segment 1;
- recalibrate if the reference plane might have moved.

Compute:

```text
Gamma_average = (Gamma_run1 + Gamma_run2) / 2
```

Do not average SWR.

Default repeatability gates:

- median complex-S11 delta <= 0.005;
- median SWR delta <= 0.05;
- exact frequency-grid equality.

## Phase 5: complete analysis

At every point compute:

```text
rho = abs(Gamma)
SWR = (1 + rho) / (1 - rho)
return_loss_db = -20*log10(rho)
Z = 50*(1 + Gamma)/(1 - Gamma)
```

For every relevant US amateur band/service window report:

- minimum, median, maximum SWR;
- minimum-SWR frequency;
- return loss and R+jX at the minimum;
- percent coverage <=1.5, <=2.0, <=3.0;
- all contiguous intervals and longest interval at each threshold;
- edge values where relevant;
- points and frequency step.

Treat 60m as channelized. If analyzing 5.3305-5.4064 MHz continuously, label it
an envelope and do not imply continuous transmit authorization.

## Phase 6: comparison

For controlled A/B:

- use one verified calibration;
- preserve geometry and routing;
- preserve frequency span, exact grid, and point spacing;
- change one variable;
- capture two sweeps per state if practical;
- report point/band deltas and repeatability.

For historical/multi-variable comparison:

- inventory every known difference;
- preserve each run's raw data and calibration;
- disclose differences in frequency span, grid, and point spacing;
- label cross-day and cross-calibration comparisons;
- report observed differences;
- explicitly say causation cannot be assigned to one component.

Never use SWR to claim gain, efficiency, receive sensitivity, noise reduction,
or common-mode suppression.

## Phase 7: report package

Create:

```text
antenna-results/antennas/[SLUG]/[DEPLOYMENT-SLUG]/
  README.md
  requirements.txt
  generate_report.py
  interactive-report.html
  charts/
  data/
  measurements/
```

Persist:

- all OSL raw NPZ/CSV and solved calibration;
- reconnect verification;
- far-end-open diagnostic;
- both DUT raw NPZ/CSV/S1P/summary/charts;
- complex average S1P;
- per-point CSV;
- band summaries CSV/JSON;
- repeatability and comparison JSON/CSV;
- metadata with all physical details and limitations;
- full static visual set;
- self-contained interactive HTML;
- exact packaged-input regeneration command.

Visuals must include:

- full span;
- band zooms;
- impedance;
- return loss;
- Smith chart;
- scorecard;
- threshold bandwidth;
- physical layout;
- repeatability;
- open-path diagnostic;
- comparison/delta chart.

The true reference plane must appear in titles. Avoid inherited labels,
resolution values, or notes from another report.

Generate entirely in staging. Load/copy inputs before touching outputs. Publish
the complete package with one atomic directory swap and a recoverable sibling
backup. A failure must leave the prior package intact.

## Phase 8: validation

Validate the copies inside the finished package, not the disposable
`nanovna_measurements/` source directories. Define the actual packaged paths
created by the deployment generator:

```bash
PACKAGE=antenna-results/antennas/[SLUG]/[DEPLOYMENT-SLUG]
PKG_CAL="$PACKAGE/measurements/calibration"
PKG_OPEN="$PACKAGE/measurements/far-end-open"
PKG_RUN1="$PACKAGE/measurements/sweep-1"
PKG_RUN2="$PACKAGE/measurements/sweep-2"

$PY antenna-results/tools/validate_nanovna_run.py \
  --calibration-dir "$PKG_CAL" \
  --load-verification-dir "$PKG_CAL/load-verification" \
  --open-path-dir "$PKG_OPEN" \
  --measurement-dir "$PKG_RUN1" \
  --repeat-dir "$PKG_RUN2" \
  --start-hz $START_HZ \
  --stop-hz $STOP_HZ \
  --points 40001 \
  --output "$PACKAGE/validation.json"
```

If the generator uses more descriptive measurement directory names, set
`PKG_CAL`, `PKG_OPEN`, `PKG_RUN1`, and `PKG_RUN2` to those exact packaged
locations. Keep `validation.json` unique to this deployment package.

Also validate:

- generator compilation;
- `git diff --check`;
- expected band and file counts;
- S1P sample count;
- metadata values;
- no nonfinite calibrated values;
- `|Gamma| < 1`;
- deterministic packaged-input regeneration by SHA-256 before/after;
- failed-generation evidence preservation;
- stale-output removal;
- atomic interruption recovery;
- browser title/content, controls, desktop/mobile layout, and zero console
  errors;
- no external resources/network calls in HTML;
- focused read-only code review;
- repository test suite.

If the full repository suite is blocked by an unrelated pre-existing issue,
give the exact file/error and do not claim it passed.

## Phase 9: documentation and publication

Update:

- antenna parent README;
- `antenna-results/README.md`;
- `CHANGELOG.md`;
- this methodology only if the process learned something new.

Show the user the results and visuals before publication when requested.

When publication is explicitly authorized:

1. fetch `origin/main`;
2. confirm only intended changes;
3. stage all raw evidence and generated outputs;
4. run staged diff checks;
5. commit with:

   ```text
   Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
   ```

6. rebase if remote main advanced; merge both changelog histories;
7. rerun integrated assertions;
8. push without force;
9. fetch and prove local HEAD equals `origin/main`.

## Final response

Lead with completion state and commit link if published. Include:

- exact measured configuration and reference plane;
- calibration verification;
- repeatability;
- concise per-band table;
- key visual links;
- comparison conclusions and causal limitations;
- exact location of full raw/package evidence;
- any blocked repository-wide test with exact error.

Do not claim that low SWR proves radiation efficiency or that a choke worked
unless a controlled common-mode measurement supports it.

---
