# Antenna measurement results

Reproducible reports built from calibrated complex S11 measurements. The scanner survey compares 18 valid antenna families and 47 configurations across 20 receive-service windows; the JYR8010 and final GOWENIC-module EFHW HF reports are preserved separately.

> **SWR is impedance match only.** It cannot establish receive gain, scanner sensitivity, radiation pattern, or decode performance.

## Reproduce an antenna deployment

- [Complete calibrated NanoVNA methodology](docs/NANOVNA-DEPLOYMENT-METHODOLOGY.md)
  defines hardware setup, reference planes, 40,001-point segmented capture,
  software OSL math, standard/load/open-path quality gates, repeatability,
  analysis, visualization, interpretation limits, evidence preservation, and
  publication.
- [August 2026 EFHW session record](docs/2026-08-EFHW-SESSION-RECORD.md)
  preserves the chronological GOWENIC and JYR8010 configurations, commands,
  results, failures, corrections, reviews, and commits.
- [September 2026 handheld session uncertainty](docs/2026-09-HANDHELD-SESSION-UNCERTAINTY.md)
  records the measured fixture floor, mounting repeatability, and dynamic-range
  limits behind the RH77CA, SRH320A and Signal Stick entries.
- [Reusable LLM deployment prompt](prompts/REPEAT-ANTENNA-DEPLOYMENT.md) is a
  copy-paste contract for repeating the same process on another antenna.
- [NanoVNA acquisition and validation tools](tools/README.md) include the exact
  capture engine, pinned dependencies, and fail-closed evidence validator.
- [Toolchain manifest](docs/TOOLCHAIN-MANIFEST.json) records exact runtime
  versions and SHA-256 identities for the acquisition and report scripts.

## Headline recommendations

- **Best all-rounder:** the Smiley 2m half-wave telescopic. At 69 cm it covers more services broadly than anything else measured; at 80 cm it is the only antenna with a broad 2m match.
- **Best one for typical SDS150 modern public safety:** Remtronix 920, which holds all of 700 and 800 MHz at or below 2:1.
- **Best when manual VHF/UHF retuning matters more:** RH789, while accepting poor 700/800/900 MHz.
- **Best two:** Remtronix 920 + Smiley half-wave.
- **2m:** Smiley at 80 cm (100% at or below 2:1). **1.25m:** TID TD771. **70cm:** Kenwood TH-D75A OEM. **UHF land mobile:** RH789 setting 6. **Federal UHF:** Diamond SRH320A.
- **VHF high (marine, railroad, NOAA):** Smiley at 69 cm covers all three at or below 2:1; the AnyTone long whip covers the whole NOAA window.
- **Installed vehicle option:** Taurus triband for useful VHF-high and partial 800/900 MHz coverage.
- The generated inventory gap table identifies services with only partial or poor full-window match.

> **Read the VHF numbers with care.** Every quarter-wave handheld here is measured with no radio chassis and no counterpoise, so the instrument body and its cable become the other half of the antenna. A known-good Kenwood TH-D75A OEM whip reads about 24:1 on 2m in this fixture while returning the survey's best 70cm result. These VHF figures rank antennas against each other on this bench; they do not predict on-radio VHF performance. The Smiley wins 2m because a half-wave genuinely does not need a counterpoise, which is a real advantage rather than a fixture artefact. See the [September 2026 session uncertainty note](docs/2026-09-HANDHELD-SESSION-UNCERTAINTY.md).

See the [full comparison, coverage matrix, and gap table](comparison/README.md) or open the [offline interactive report](comparison/interactive-report.html).

## Inventory

| Family | Status | Scope |
|---|---|---|
| [Remtronix 920](antennas/remtronix-920/README.md) | valid | fixed; modern 700/800/900 MHz |
| [RH789](antennas/rh789/README.md) | valid | settings 1-6; manually retuned VHF/UHF |
| [TID TD771](antennas/tid-td771/README.md) | valid | fixed; exceptional 222-225 MHz |
| [Diamond SRH77CA](antennas/diamond-srh77ca/README.md) | valid | fixed; broad 420-450 MHz |
| [Diamond RH77CA](antennas/diamond-rh77ca/README.md) | valid | fixed; broad 406-420 MHz |
| [Diamond SRH320A](antennas/diamond-srh320a/README.md) | valid | fixed; best 222-225 MHz and 406-420 MHz; no valid data above 909.798 MHz |
| [Signal Stick](antennas/signal-stick/README.md) | valid / control | fixed; measured without its counterpoise |
| [Signal Stick with counterpoise](antennas/signal-stick-counterpoise/README.md) | valid | fixed; 84% of 2m at or below 2:1 with the wire fitted |
| [Smiley 2m half-wave telescopic](antennas/smiley-halfwave/README.md) | valid | settings 1-7, 22-91 cm; **the only broad 2m match in the survey** and the best all-rounder |
| [Comet BNC-W100RX telescopic](antennas/comet-bnc-w100rx/README.md) | valid | settings 1-8, 21-99.5 cm; 25-1300 MHz wideband receive design, no good match at any length |
| [Kenwood TH-D75A OEM](antennas/kenwood-thd75a-stock/README.md) | valid | fixed, bare SMA plane; best measured 70cm; the fixture control experiment |
| [Icom ID-52A OEM](antennas/icom-id52a-stock/README.md) | valid | fixed, bare SMA plane; best window is UHF land mobile |
| [AnyTone AT-D890UV rubber duck](antennas/anytone-atd890uv-16cm/README.md) | valid | fixed ~16 cm, SMA adapter plane; 88% of federal UHF |
| [AnyTone AT-D890UV long whip](antennas/anytone-atd890uv-38cm/README.md) | valid | fixed ~38 cm, SMA adapter plane; full NOAA and full federal UHF |
| [Generic extendable](antennas/generic-extendable/README.md) | valid / experimental | settings 1-10; geometry-sensitive |
| [Uniden SDS150 stock](antennas/uniden-sds150-stock/README.md) | valid | reference antenna |
| [Taurus triband vehicle](antennas/taurus-triband-vehicle/README.md) | valid / installed vehicle | fixed installation; VHF-high and partial 800/900 MHz |
| [TIDRADIO TD-H9 stock](antennas/tidradio-h9-stock/README.md) | valid | fixed, SMA adapter plane; full federal UHF, strong 70cm. The rejected August capture is preserved separately |
| [JYR8010 EFHW](antennas/jyr8010-efhw/README.md) | valid HF reports and siting study | 39.6 m / 130 ft **80m-band** EFHW; historical baseline, [two-choke office-feed installation](antennas/jyr8010-efhw/two-choke-office-feed/README.md), and [CN97ap deployment siting study](antennas/jyr8010-efhw/deployment-siting-cn97ap/README.md) |
| [GOWENIC-module 40m EFHW](antennas/gowenic-efhw/README.md) | valid HF reports | 62.5 ft sloper; 75 ft outdoor baseline plus [100 ft/window office-feed comparison](antennas/gowenic-efhw/installed-office-feed/README.md) |

## Method

- NanoVNA-H firmware 1.2.50, 50 Ω reference.
- Independent software ideal OSL calibrations for the handheld SMA-to-BNC bench fixture and the vehicle BNC reference plane.
- Broadband: 50-1200 MHz, 40,001 points, nominal ~28.75 kHz spacing.
- Service zooms: three complex-S11 passes averaged point by point. An exact configuration/service zoom is authoritative over broadband.
- Every valid configuration × service records minimum SWR and frequency, median, maximum, coverage ≤2:1 and ≤3:1, source, R, X, and return loss derived from RI Touchstone data.
- Ranking: authoritative median SWR, then maximum, then minimum; context-specific ranks avoid treating the vehicle and handheld fixtures as controlled gain comparisons.
- Coverage classes use full-window percentages: broad <=2:1, broad <=3:1, partial only, or gap.
- Nonfinite values become JSON `null` and display as “very poor / outside calibrated dynamic range.”

## Calibration and fixture

Load reconnect verification: median 1.00135, p95 1.01044, maximum 1.19335 across the full sweep; VHF maximum 1.00127. See the [preserved calibration baseline](calibration-baselines/sma-to-bnc/2026-08-16-nanovna-h/README.md).

The September 2026 handheld additions use their own [2026-09-19 baseline](calibration-baselines/sma-to-bnc/2026-09-19-nanovna-h/README.md): median 1.00677, p95 1.02379, maximum 1.16781, with a per-service floor table. That session also measured its mounting repeatability, which is much coarser than the calibration floor and is the dominant uncertainty for counterpoise-less handheld whips; see the [session uncertainty note](docs/2026-09-HANDHELD-SESSION-UNCERTAINTY.md).

The separate [vehicle-adapter baseline](calibration-baselines/vehicle-adapter/2026-08-16-nanovna-h/README.md) verifies the BNC reference plane used for the installed Taurus antenna. Full-span reconnect verification was median 1.02638, p95 1.11973, and maximum 1.23518; uncertainty is highest above 1 GHz.

The saved calibration is reusable only with the same unchanged adapter chain and a load verification each session. Calibration accuracy does not remove antenna-fixture uncertainty.

Handheld measurements used fixed upright geometry with no added counterpoise; the installed Taurus measurement includes the vehicle body, mount, feed line, and antenna-side adapter. Compare impedance coverage within context, not as direct receive-gain measurements between contexts.

## Layout and reproduction

- `antennas/*/measurements/`: preserved S1P, raw NPZ, JSON, and authoritative zoom artifacts.
- `antennas/*/charts/` and family READMEs: generated analysis.
- `antennas/jyr8010-efhw/deployment-siting-cn97ap/`: site-specific deployment design - GIS parcel data, USGS 3DEP terrain horizon, great-circle bearings, and predicted DX coverage. **Analysis and prediction, not measurement**; see its `METHOD.md` for per-model confidence.
- `comparison/`: CSV/JSON scorecards, charts, recommendations, and offline report.
- `calibration-baselines/`: immutable OSL and verification captures.
- [`manual-testing/`](manual-testing/): immutable historical coarse reconnaissance; not used for current rankings.
- `tools/generate_scanner_antenna_report.py`: deterministic generator.

```bash
python3 antenna-results/tools/generate_scanner_antenna_report.py
```

Run this from the repository root in any Python environment with the versions in [`tools/requirements.txt`](tools/requirements.txt).

## Invalid capture policy

The TIDRADIO H9 stock trace appeared electrically open and repeat verification was skipped. Raw files are preserved, clearly labeled invalid/inconclusive, and excluded from all calculations and recommendations.
