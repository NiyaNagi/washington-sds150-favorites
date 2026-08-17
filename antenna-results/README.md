# Antenna measurement results

Reproducible reports built from calibrated complex S11 measurements. The scanner survey compares six valid antenna families and 20 configurations across 20 receive-service windows; the earlier JYR8010 EFHW HF report remains intact.

> **SWR is impedance match only.** It cannot establish receive gain, scanner sensitivity, radiation pattern, or decode performance.

## Headline recommendations

- **Best one for typical SDS150 modern public safety:** Remtronix 920.
- **Best when manual VHF/UHF retuning matters more:** RH789, while accepting poor 700/800/900 MHz.
- **Best two:** Remtronix 920 + RH789.
- Add/substitute TD771 for 222-225 MHz; choose Diamond SRH77CA for broad 420-450 MHz.
- No good measured winner for civil air or 2m in this no-radio-chassis fixture.

See the [full comparison and circumstance table](comparison/README.md) or open the [offline interactive report](comparison/interactive-report.html).

## Inventory

| Family | Status | Scope |
|---|---|---|
| [Remtronix 920](antennas/remtronix-920/README.md) | valid | fixed; modern 700/800/900 MHz |
| [RH789](antennas/rh789/README.md) | valid | settings 1-6; manually retuned VHF/UHF |
| [TID TD771](antennas/tid-td771/README.md) | valid | fixed; exceptional 222-225 MHz |
| [Diamond SRH77CA](antennas/diamond-srh77ca/README.md) | valid | fixed; broad 420-450 MHz |
| [Generic extendable](antennas/generic-extendable/README.md) | valid / experimental | settings 1-10; geometry-sensitive |
| [Uniden SDS150 stock](antennas/uniden-sds150-stock/README.md) | valid | reference antenna |
| [TIDRADIO H9 stock](antennas/tidradio-h9-stock/README.md) | invalid / inconclusive | preserved, excluded |
| [JYR8010 EFHW](antennas/jyr8010-efhw/README.md) | preserved HF report | separate prior report |

## Method

- NanoVNA-H firmware 1.2.50, 50 Ω reference.
- Software ideal OSL calibration at the SMA-to-BNC output reference plane.
- Broadband: 50-1200 MHz, 40,001 points, nominal ~28.75 kHz spacing.
- Service zooms: three complex-S11 passes averaged point by point. An exact configuration/service zoom is authoritative over broadband.
- Every valid configuration × service records minimum SWR and frequency, median, maximum, coverage ≤2:1 and ≤3:1, source, R, X, and return loss derived from RI Touchstone data.
- Ranking: authoritative median SWR, then maximum, then minimum.
- Nonfinite values become JSON `null` and display as “very poor / outside calibrated dynamic range.”

## Calibration and fixture

Load reconnect verification: median 1.00135, p95 1.01044, maximum 1.19335 across the full sweep; VHF maximum 1.00127. See the [preserved calibration baseline](calibration-baselines/sma-to-bnc/2026-08-16-nanovna-h/README.md).

The saved calibration is reusable only with the same unchanged adapter chain and a load verification each session. Calibration accuracy does not remove antenna-fixture uncertainty.

Measurements used fixed upright geometry, no added counterpoise, with the USB cable remaining part of the RF environment. Handheld antennas depend on the radio chassis, operator, adapter, nearby objects, and cable geometry.

## Layout and reproduction

- `antennas/*/measurements/`: preserved S1P, raw NPZ, JSON, and authoritative zoom artifacts.
- `antennas/*/charts/` and family READMEs: generated analysis.
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
