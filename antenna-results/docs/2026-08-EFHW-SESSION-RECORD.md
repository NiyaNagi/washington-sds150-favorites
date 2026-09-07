# August 2026 EFHW measurement session record

This is the chronological audit trail for the GOWENIC and JYR8010 EFHW work
performed from August 17 through August 28, 2026. It records configurations,
commands, failures, corrections, validation, results, and publication history.

The normative procedure is
[`NANOVNA-DEPLOYMENT-METHODOLOGY.md`](NANOVNA-DEPLOYMENT-METHODOLOGY.md).

## 1. Instruments and common settings

- NanoVNA-H, firmware 1.2.50.
- CH0/Port 1 S11.
- 50-ohm reference.
- Device bandwidth report: 1 kHz.
- Raw scan command: `scan START STOP 101 0b011`.
- Software ideal one-port OSL with VNA internal calibration disabled during raw
  scans.
- 400 overlapping 101-point segments, duplicate endpoints removed.
- Python 3.9.6, NumPy 2.0.2, Matplotlib 3.9.4, pySerial 3.5.
- Primary local acquisition script:
  `antenna-results/tools/nanovna_swr_session_2026_08.py` (preserved
  byte-exact). Future runs use the hardened `nanovna_swr.py` wrapper.

## 2. Original JYR8010 baseline - August 16

Artifact:
[`../antennas/jyr8010-efhw/`](../antennas/jyr8010-efhw/)

Recorded configuration:

- JYR8010-150W;
- 40 m radiator;
- nominal 1:49/1:64 transformer;
- no dedicated ground;
- no dedicated counterpoise;
- feed-line length and antenna support geometry were not recorded.

Measurement:

- 1.8-148 MHz;
- 40,001 points;
- nominal 3.655 kHz spacing;
- calibration at antenna-side adapter plane;
- capture at 2026-08-16 12:50 PDT.

Baseline supported-band minima:

| Band | SWR | Frequency | <=2:1 coverage |
|---|---:|---:|---:|
| 80m | 1.09 | 3.605570 MHz | 60% |
| 40m | 1.44 | 7.198435 MHz | 94% |
| 30m | 1.60 | 10.100505 MHz | 100% |
| 20m | 1.19 | 14.245275 MHz | 100% |
| 17m | 1.83 | 18.068405 MHz | 71% |
| 15m | 1.52 | 21.007025 MHz | 100% |
| 12m | 1.63 | 24.892290 MHz | 100% |
| 10m | 1.78 | 28.466880 MHz | 28% |

This became historical context, not a controlled baseline for later choke
changes, because critical physical variables were undocumented.

## 3. GOWENIC tuning progression - August 17

Artifact:
[`../antennas/gowenic-efhw/`](../antennas/gowenic-efhw/)

The home-built 40m EFHW used a generic GOWENIC "No Tune End Fed Half Antenna"
10 W module, not a genuine QRPGuys-branded board.

Incremental measurements:

| Time PDT | Configuration change | Resonance/minimum |
|---|---|---:|
| 22:30 | Initial approximate inverted V, apex about 8 ft | 6.304000 MHz, 1.52 |
| 22:31 | Focused repeat | 6.304375 MHz, 1.52 |
| 22:35 | Middle of 12 ft coax rerouted | 6.301750 MHz, 1.51 |
| 22:41 | Removed 22 in radiator | 6.459555 MHz, 1.59 |
| 22:45 | 52 in total removed | 6.713611 MHz, 1.51 |
| 22:50 | 60 in total removed | 6.812375 MHz, 1.48 |
| 23:01 | Raised to 25-to-3 ft sloper, changed coax route | 7.025000 MHz, 1.38 |
| 23:02 | Focused sloper repeat | 7.025375 MHz, 1.38 |
| 23:14 | Permanent 14 in far tie-off loop | 7.020750 MHz, 1.40 |
| 23:21 | 40/20/15/10m harmonic characterization | 7.020500 MHz, 1.40 |

Learnings:

- removing wire moved the fundamental upward as expected;
- raising/redeploying the wire shifted resonance more than the final small
  mechanical loop change;
- coax rerouting had a small measurable effect, showing feed-line/common-mode
  sensitivity before a dedicated counterpoise;
- physical deployment is part of the antenna system and must be recorded.

## 4. Final GOWENIC build and full sweep - August 18

Final build:

- 62.5 ft physical radiator wire;
- 8 in feed-end strain loop;
- 14 in far-end tie-off loop;
- about 60 ft 8 in straight supported span after mechanical loop consumption;
- 25 ft far end and 3 ft feed end;
- 96 in counterpoise on transformer ground/shield;
- counterpoise straight on ground, angled away from radiator;
- no common-mode choke;
- 75 ft LS400 outdoors.

The report originally carried an incorrect 12 ft final-feed-line value. On
August 23 the user clarified that the final August 18 run used 75 ft LS400
outdoors. The final metadata, README, generator, and reproduction instructions
were corrected; earlier tuning runs that really used 12 ft remained unchanged.

Full OSL:

```bash
python .nanovna-tools/nanovna_swr.py capture open \
  --start 1800000 --stop 148000000 --segments 400 \
  --output-dir nanovna_measurements/2026-08-18_0007_gowenic_efhw_full_calibration

python .nanovna-tools/nanovna_swr.py capture short \
  --start 1800000 --stop 148000000 --segments 400 \
  --output-dir nanovna_measurements/2026-08-18_0007_gowenic_efhw_full_calibration

python .nanovna-tools/nanovna_swr.py capture load \
  --start 1800000 --stop 148000000 --segments 400 \
  --output-dir nanovna_measurements/2026-08-18_0007_gowenic_efhw_full_calibration

python .nanovna-tools/nanovna_swr.py calibrate \
  --calibration-dir nanovna_measurements/2026-08-18_0007_gowenic_efhw_full_calibration
```

After physical LOAD reconnect:

```bash
python .nanovna-tools/nanovna_swr.py measure \
  --calibration nanovna_measurements/2026-08-18_0007_gowenic_efhw_full_calibration/calibration.npz \
  --output-dir nanovna_measurements/2026-08-18_0007_gowenic_efhw_full_calibration/load-verification
```

Verification:

- median SWR 1.00052;
- p95 1.00088;
- maximum 1.01115;
- median impedance 50.008 + j0.024 ohms.

Final antenna:

```bash
python .nanovna-tools/nanovna_swr.py measure \
  --calibration nanovna_measurements/2026-08-18_0007_gowenic_efhw_full_calibration/calibration.npz \
  --output-dir nanovna_measurements/2026-08-18_0024_gowenic_efhw_final
```

Selected result:

- 40m minimum 1.41 at 7.022995 MHz;
- 40m 100% <=2:1;
- 20m minimum 2.58;
- 15m minimum 1.89, 24% <=2:1;
- 10m minimum 1.68, 76% <=2:1.

Published:

- commit `aaed1201370ae3d4c208631b7295a1d7fe87d9b8`;
- package contains tuning history, source sweeps, all OSL artifacts, static and
  interactive reports, build geometry, reproduction guide, and LLM prompt.

## 5. GOWENIC installed office feed - August 23

Artifact:
[`../antennas/gowenic-efhw/installed-office-feed/`](../antennas/gowenic-efhw/installed-office-feed/)

Configuration:

```text
VNA/radio
  -> 25 ft LS400 inside office
  -> window flat-ribbon transition
  -> 75 ft LS400 outdoors
  -> GOWENIC transformer and EFHW
```

The office contained substantial computer equipment. The result was explicitly
treated as installed-system input impedance, not de-embedded antenna feed-point
impedance.

### Fresh 0.5-54 MHz calibration

```bash
CAL=nanovna_measurements/2026-08-23_1959_home_efhw_office_feed_calibration

python .nanovna-tools/nanovna_swr.py capture open \
  --start 500000 --stop 54000000 --segments 400 --output-dir "$CAL"
python .nanovna-tools/nanovna_swr.py capture short \
  --start 500000 --stop 54000000 --segments 400 --output-dir "$CAL"
python .nanovna-tools/nanovna_swr.py capture load \
  --start 500000 --stop 54000000 --segments 400 --output-dir "$CAL"
python .nanovna-tools/nanovna_swr.py calibrate --calibration-dir "$CAL"
```

### Invalid SHORT incident

The first SHORT was electrically open-like:

The following exact values were recorded contemporaneously in the session
before the bad SHORT and dependent outputs were overwritten. They are useful
for explaining detection but are **not independently reproducible from the
preserved package**:

```text
OPEN/SHORT median separation: 0.046
OPEN/LOAD median separation: 0.655
SHORT/LOAD median separation: 0.656
```

The bad calibration produced an impossible result:

- attached antenna median SWR about 1.039 across 0.5-54 MHz;
- every amateur band looked <=2:1;
- far-end-open 100 ft feed path also looked approximately 50 ohms.

The result was not rationalized or published. The actual SHORT was verified as
center-to-shell bonded and recaptured on the identical grid:

```bash
python .nanovna-tools/nanovna_swr.py capture short \
  --start 500000 --stop 54000000 --segments 400 \
  --output-dir "$CAL" --overwrite
python .nanovna-tools/nanovna_swr.py calibrate --calibration-dir "$CAL"
```

Corrected standard separation:

```text
OPEN/SHORT median: 1.538
OPEN/LOAD median: 0.655
SHORT/LOAD median: 0.885
```

Every dependent measurement was repeated.

### Corrected verification and diagnostics

Corrected reconnect verification:

- median SWR 1.00009;
- p95 1.00030;
- maximum 1.00047;
- median impedance 50.0018 - j0.0025 ohms.

Corrected far-end-open path:

- median `|Gamma|` 0.834;
- `|Gamma|` 0.884 at 7 MHz;
- `|Gamma|` 0.794 at 54 MHz;
- apparent ideal-open/uniform-line one-way attenuation 0.54 dB at 7 MHz and
  1.00 dB at 54 MHz.

Those attenuation values were documented as plausibility estimates, not
insertion-loss measurements.

### Corrected DUT and repeat

```bash
python .nanovna-tools/nanovna_swr.py measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir nanovna_measurements/2026-08-23_2017_home_efhw_office_feed \
  --overwrite

python .nanovna-tools/nanovna_swr.py measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir nanovna_measurements/2026-08-23_2047_home_efhw_office_feed_repeat
```

Repeatability:

- median complex-S11 delta 0.00066;
- p95 0.00464;
- median SWR delta 0.0049;
- p95 SWR delta 0.0493.

Selected installed-system results:

| Band | Minimum | <=2:1 coverage |
|---|---:|---:|
| 80m | 1.16 at 3.617713 MHz | 96% |
| 40m | 1.40 at 7.214250 MHz | 93% |
| 20m | 1.22 at 14.226763 MHz | 100% |
| 17m | 1.83 at 18.068063 MHz | 71% |
| 15m | 1.50 at 21.056038 MHz | 100% |
| 12m | 1.62 at 24.890650 MHz | 100% |
| 10m | 1.69 at 28.554063 MHz | 40% |
| 6m | 5.47 at 50.927763 MHz | 0% |

Interpretation:

- the longer path and window transition changed phase and attenuation;
- better radio-end SWR did not prove better radiation efficiency;
- office RFI was a receiver-noise concern, not a sufficient explanation for a
  stable broadband impedance transformation.

Published:

- commit `186b5a7fa9bc4edd3ee6ad60088a76d7f67fb2d5`.

## 6. JYR8010 two-choke office feed - August 28

Artifact:
[`../antennas/jyr8010-efhw/two-choke-office-feed/`](../antennas/jyr8010-efhw/two-choke-office-feed/)

The user chose comparison with the August 16 historical JYR8010 run rather than
a fresh no-choke/choke A/B. The report therefore labels all differences as
observational.

Current path:

```text
VNA/radio at office-side PL-259/SO-239 adapter
  -> 25 ft LS400
  -> window-entry choke
       3 ft RG8X, 11 turns, Mix 31 FT240-size toroid
  -> window flat-ribbon transition
  -> 75 ft LS400 outdoors
  -> feedpoint choke
       3 ft RG8X, 11 turns, Mix 31 FT240-size toroid
  -> JYR8010 transformer
       16 ft counterpoise on dedicated terminal,
       on ground opposite radiator
  -> 40 m radiator
```

Total coax: about 106 ft plus the window transition.

### Calibration

```bash
CAL=nanovna_measurements/2026-08-28_2151_jyr8010_choked_calibration

python .nanovna-tools/nanovna_swr.py capture open \
  --start 500000 --stop 54000000 --segments 400 --output-dir "$CAL"
python .nanovna-tools/nanovna_swr.py capture short \
  --start 500000 --stop 54000000 --segments 400 --output-dir "$CAL"
python .nanovna-tools/nanovna_swr.py capture load \
  --start 500000 --stop 54000000 --segments 400 --output-dir "$CAL"
python .nanovna-tools/nanovna_swr.py calibrate --calibration-dir "$CAL"
```

OPEN/SHORT median separation: 1.538.

Reconnect verification:

- median SWR 1.00075;
- p95 1.00087;
- maximum 1.00106;
- median impedance 50.0357 + j0.0112 ohms.

### Open-path diagnostic

```bash
python .nanovna-tools/nanovna_swr.py measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir nanovna_measurements/2026-08-28_2213_jyr8010_choked_feedpath_open
```

The choked feed path behaved as an open line. A comparison with the August 23
unchoked open-path trace showed apparent one-way deltas of:

- +0.07 dB at 7 MHz;
- +0.22 dB at 28 MHz;
- +0.27 dB at 54 MHz.

This comparison is cross-day and cross-calibration. It does not measure choke
common-mode impedance and cannot assign the delta to RG8X, connectors, toroids,
calibration variation, or day-to-day change individually. Both complete raw
source/calibration sets are preserved.
In the packaged JYR8010 report these live under
`measurements/unchoked-baseline/calibration/` and
`measurements/unchoked-baseline/far-end-open/`.

### VNA timeout and recovery

The first antenna attempt reached segment 150, then the VNA stopped answering
and timed out while the script attempted `cal on`.

USB disconnect/reconnect did not recover it because the internal battery kept
the VNA powered. The physical power switch was cycled for five seconds while
the RF adapter and installed system remained untouched. `status` then returned
normally.

No partial antenna file had been written. The sweep restarted from segment 1:

```bash
python .nanovna-tools/nanovna_swr.py measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir nanovna_measurements/2026-08-28_2218_jyr8010_two_chokes_counterpoise
```

Repeat:

```bash
python .nanovna-tools/nanovna_swr.py measure \
  --calibration "$CAL/calibration.npz" \
  --output-dir nanovna_measurements/2026-08-28_2226_jyr8010_two_chokes_counterpoise_repeat
```

Repeatability:

- median complex-S11 delta 0.00036;
- p95 0.00075;
- median SWR delta 0.00085;
- p95 SWR delta 0.00576;
- every supported-band minimum repeated within 1.337 kHz and 0.0014 SWR.

Current results:

| Band | Minimum | Median / max | Z at minimum | <=2:1 |
|---|---:|---:|---:|---:|
| 80m | 1.16 at 3.564213 | 2.13 / 4.12 | 55.9 + j5.1 | 46% |
| 40m | 1.44 at 7.192850 | 1.55 / 2.04 | 37.9 - j10.3 | 97% |
| 30m | 2.86 at 10.148725 | 2.95 / 3.04 | 33.7 - j42.2 | 0% |
| 20m | 1.09 at 14.265550 | 1.20 / 1.57 | 50.1 - j4.3 | 100% |
| 17m | 1.45 at 18.068063 | 1.50 / 1.55 | 72.3 + j3.1 | 100% |
| 15m | 1.37 at 21.001200 | 1.51 / 1.71 | 59.0 + j14.8 | 100% |
| 12m | 1.53 at 24.890650 | 1.58 / 1.64 | 70.6 + j14.9 | 100% |
| 10m | 1.60 at 28.505913 | 2.01 / 3.02 | 77.0 - j11.2 | 49% |

Observed historical deltas:

- 40m essentially unchanged;
- 20m, 17m, 15m, 12m, and 10m improved in minimum SWR;
- 80m slightly worse;
- 30m substantially worse.

Those are combined installed-system changes, not isolated toroid effects.
The historical baseline also used a different 1.8-148 MHz, 3.655 kHz grid;
the current run used 0.5-54 MHz at 1.3375 kHz. The coarser historical grid can
under-resolve a sharp minimum, adding another comparison limitation.

Published:

- commit `e049c324153e21d5e9ac00b184e4b0fcc6e0eaf0`.

## 7. Report-generation commands

Each package README contains its exact packaged-input command. The generators
used were:

```text
antenna-results/antennas/gowenic-efhw/generate_report.py
antenna-results/antennas/gowenic-efhw/installed-office-feed/generate_report.py
antenna-results/antennas/jyr8010-efhw/generate_report.py
antenna-results/antennas/jyr8010-efhw/two-choke-office-feed/generate_report.py
```

The deployment generators:

- copy inputs into staging before touching outputs;
- build generated directories in staging;
- preserve generator source and requirements;
- atomically swap the complete package;
- keep a sibling backup during publication;
- recover a prior backup at the start of the next run;
- normalize generated CSV line endings;
- support deterministic self-regeneration from packaged inputs.

## 8. Validation actually performed

Across the packages, validation included:

- acquisition solver self-test;
- device status checks;
- standard frequency-grid equality;
- raw standard separation;
- reconnected-load median/p95/maximum SWR;
- finite calibrated arrays and `|Gamma| < 1`;
- exact 40,001-point count and monotonic frequency;
- Touchstone row count;
- far-end-open plausibility;
- point-level repeatability;
- per-band repeatability;
- expected band count and ordering;
- metadata/configuration assertions;
- static chart generation;
- interactive HTML load, selector interaction, console-error check, desktop
  and mobile screenshots;
- no external HTML resources or network calls;
- generated-output stale-file removal;
- intentional failed regeneration preserving packaged evidence;
- atomic interruption recovery;
- byte-identical packaged-input regeneration using SHA-256 manifests;
- `git diff --check`;
- multiple focused code-review passes.

The repository-wide pytest suite was repeatedly attempted during these sessions
but could not collect under the Python 3.9 environment because
`src/wasds150/recipes/systems.py:249` contained an f-string expression with a
backslash. This was unrelated to the antenna packages. No claim was made that
the full suite passed.

## 9. Review findings that improved the method

Focused reviews caught and corrected:

- calling apparent open-path attenuation "measured loss";
- failing to preserve/disclose a cross-day calibration baseline;
- generated directories retaining stale files;
- describing the US 60m analysis envelope as continuous authorization;
- unlabeled interactive plot series;
- mobile legend clipping;
- self-regeneration deleting packaged inputs before loading them;
- failed publication risking loss of packaged sources;
- interruption windows between multiple output-directory moves;
- inherited wrong reference-plane chart titles;
- inherited wrong resolution and scanner-specific HTML notes.

These findings are now encoded in the methodology and generators.

## 10. Core learnings

1. Calibration plausibility must be judged physically, not just numerically.
2. Raw standard separation should be checked before solving OSL.
3. Physically reconnect the LOAD after calibration.
4. A far-end-open line is a powerful discriminating diagnostic.
5. Never average SWR when complex S11 is available.
6. Two unchanged DUT sweeps are the minimum evidence for stability.
7. Reference-plane wording must follow the actual connector, not the antenna
   model.
8. A good radio-end SWR may include beneficial transformation or harmful loss.
9. SWR alone says nothing about receive noise or choke effectiveness.
10. Do not attribute a multi-variable historical difference to one component.
11. USB reconnection may not reboot a battery-powered NanoVNA.
12. Failed captures and generators must not produce success-shaped artifacts.
13. Raw evidence, metadata, scripts, and deterministic regeneration are all
    part of the result - not optional extras.

## 11. Methodology archival - September 6

The user requested a complete transfer package so another LLM could reproduce
the process without relying on conversation history or this machine's hidden
files.

The repository audit found:

- all raw GOWENIC/JYR8010 evidence and deployment-specific report generators
  were already committed;
- the core acquisition script and three local helpers still existed only under
  `.nanovna-tools`;
- validation logic was spread across inline Python commands and report
  assertions;
- no single document connected calibration math, physical interaction,
  diagnostics, failure handling, analysis, review, and Git publication.

Archival actions:

1. preserved the exact acquisition engine as
   `tools/nanovna_swr_session_2026_08.py`;
2. verified its SHA-256 matched the local script exactly;
3. added `tools/nanovna_swr.py` as a hardened operational wrapper without
   altering the historical archive;
4. archived the three surviving local helpers byte-for-byte under
   `tools/session-helpers/`;
5. added pinned acquisition dependencies;
6. converted all inline quality gates into `validate_nanovna_run.py`;
7. added `test_nanovna_tools.py`;
8. created the normative methodology, this session record, exact toolchain
   manifest, and reusable LLM prompt;
9. linked everything from `antenna-results/README.md` and the changelog.

Independent reviews then found and drove fixes for:

- NaN/infinity passing validation;
- stale solved calibration terms not matching recaptured standards;
- measurement/verification/open-path grids sharing only endpoints rather than
  the exact calibration grid;
- CSV and Touchstone not being bound back to raw NPZ evidence;
- unchecked `frequency_mhz` and phase columns;
- unchecked Touchstone units/representation/reference impedance;
- NaN CLI thresholds disabling gates;
- stale passed validation reports surviving a later failed validation;
- non-transactional operational capture output;
- raw floating-point frequency NaN being converted to an integer before
  validation;
- the prompt requesting a three-standard gate before LOAD existed;
- missing disclosure that the historical JYR8010 comparison also used a
  different frequency span and resolution;
- bandwidth being read but not set by the acquisition script.

The final operational toolchain:

- rejects nonfinite scan, raw, calibration, corrected, and derived values;
- validates frequencies before integer conversion;
- recomputes solved OSL terms from packaged standards;
- recomputes calibrated S11 from each raw DUT NPZ;
- checks every derived CSV field and canonical `# Hz S RI R 50` Touchstone;
- binds validation output to evidence SHA-256 hashes;
- removes stale validation success before a new run;
- uses transactional DUT publication with rollback and rejected-output naming;
- marks incomplete/rejected standard captures;
- requires explicit confirmation that the VNA reports 1 kHz bandwidth.

Targeted tests:

```text
17 tests passed:
- calibration solver recovery
- nonfinite scan rejection
- nonfinite threshold rejection
- stale calibration rejection
- shifted interior-grid rejection
- raw/CSV/Touchstone binding
- Touchstone option-line binding
- atomic run-directory publication
- raw S11/frequency shape mismatch rejection
- invalid/reversed/unbounded sweep rejection before hardware access
- validation-output collision rejection without deleting evidence
- malformed Touchstone extra-field rejection
- mathematically valid infinite return loss at exactly zero reflection
- measurement output/calibration directory overlap rejection
- unowned rollback backup preservation
- symlinked rollback-marker refusal without following the link
- symlinked output/backup directory refusal before publication
```

Both packaged installed-system evidence sets passed the hardened validator. The
full repository pytest suite remained blocked during archival by the unrelated
Python 3.9 syntax error in `src/wasds150/recipes/systems.py:249`.
