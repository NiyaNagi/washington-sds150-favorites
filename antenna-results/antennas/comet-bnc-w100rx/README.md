# Comet BNC-W100RX telescopic

A 25-1300 MHz wideband receive antenna, BNC, eight sections including the base, measured at all eight lengths. Its resonance walks cleanly up the spectrum as it is retracted - 62.9, 67.2, 105.8, 108.5, 117.6, 124.1, 255.0 and 315.0 MHz - but its best match at any length is only 1.56:1, and most service windows sit between 4:1 and 25:1. That is what a wideband receive antenna is: a deliberate broadband compromise rather than a resonant design.

> **SWR is impedance match only.** It does not measure receive gain, sensitivity, radiation pattern, or on-air decoding.

## Measurement inventory

- Connection: BNC antenna, direct to the measurement plane.
- Measurement context: Handheld bench fixture.
- Calibrated 50-1200 MHz broadband sweep: 40,001 points (~28.75 kHz spacing).
- Three-pass complex-averaged service zooms override broadband data for the same configuration and service.
- [setting 1 (collapsed, 21 cm)](measurements/setting-1-collapsed/antenna.s1p): Fully collapsed, 21 cm.
- [setting 2 (33 cm)](measurements/setting-2/antenna.s1p): Six sections retracted, 33 cm.
- [setting 3 (44 cm)](measurements/setting-3/antenna.s1p): Five sections retracted, 44 cm.
- [setting 4 (56 cm)](measurements/setting-4/antenna.s1p): Four sections retracted, 56 cm.
- [setting 5 (67 cm)](measurements/setting-5/antenna.s1p): Three sections retracted, 67 cm.
- [setting 6 (78 cm)](measurements/setting-6/antenna.s1p): Two sections retracted, 78 cm.
- [setting 7 (89 cm)](measurements/setting-7/antenna.s1p): One section retracted, 89 cm.
- [setting 8 (fully extended, 99.5 cm)](measurements/setting-8-fully-extended/antenna.s1p): Fully extended, 99.5 cm.

## Conclusions

- Useful around 406-470 MHz, strongest at the 420 MHz edge.
- Broadest measured handheld-fixture match across both UAT 978 and ADS-B 1090, though match alone does not establish tracking sensitivity.
- Poor at VHF and 700/800 MHz in this no-radio-chassis fixture.

## Analysis charts

### Broadband overview

![Comet W100RX Broadband overview](charts/broadband-overview.png)

### Scanner scorecard

![Comet W100RX Scanner scorecard](charts/scanner-scorecard.png)

### Authoritative averaged zoom panels

![Comet W100RX Authoritative averaged zoom panels](charts/authoritative-zoom-panels.png)

### Impedance and return loss

![Comet W100RX Impedance and return loss](charts/impedance-return-loss.png)

### Setting × service heatmap

![Comet W100RX Setting × service heatmap](charts/setting-service-heatmap.png)

## Best measured setting by service

[Download CSV](best-setting-table.csv). Rankings use authoritative median SWR, then maximum, then minimum.

| Service | Setting | Source | Min | Median | Max |
|---|---|---|---:|---:|---:|
| 6m amateur | setting 8 (fully extended, 99.5 cm) | broadband | 8.95 | 10.38 | 11.30 |
| FM broadcast | setting 7 (89 cm) | averaged_zoom | 2.49 | 5.12 | 12.42 |
| Civil air | setting 3 (44 cm) | averaged_zoom | 2.14 | 3.05 | 6.14 |
| 2m amateur | setting 3 (44 cm) | averaged_zoom | 5.26 | 5.54 | 6.07 |
| VHF LMR | setting 3 (44 cm) | averaged_zoom | 5.21 | 8.43 | 11.02 |
| Marine VHF | setting 4 (56 cm) | averaged_zoom | 6.26 | 7.12 | 9.43 |
| Railroad | setting 4 (56 cm) | averaged_zoom | 6.83 | 7.12 | 7.51 |
| NOAA weather | setting 4 (56 cm) | averaged_zoom | 6.61 | 6.66 | 7.26 |
| 1.25m amateur | setting 8 (fully extended, 99.5 cm) | averaged_zoom | 3.93 | 4.01 | 4.11 |
| Military air | setting 1 (collapsed, 21 cm) | averaged_zoom | 1.56 | 2.79 | 11.84 |
| Federal UHF | setting 6 (78 cm) | averaged_zoom | 3.31 | 4.12 | 7.77 |
| 70cm amateur | setting 6 (78 cm) | averaged_zoom | 2.82 | 2.99 | 3.76 |
| UHF LMR | setting 8 (fully extended, 99.5 cm) | averaged_zoom | 2.99 | 3.12 | 3.51 |
| T-band | setting 5 (67 cm) | averaged_zoom | 3.15 | 3.55 | 4.41 |
| 700 MHz public safety | setting 3 (44 cm) | averaged_zoom | 5.13 | 5.36 | 5.53 |
| 800 MHz public safety | setting 1 (collapsed, 21 cm) | averaged_zoom | 7.00 | 7.23 | 7.52 |
| 33cm amateur | setting 4 (56 cm) | averaged_zoom | 6.04 | 7.33 | 8.84 |
| 900 MHz trunking | setting 4 (56 cm) | averaged_zoom | 7.28 | 7.58 | 8.21 |
| UAT 978 | setting 6 (78 cm) | averaged_zoom | 6.54 | 7.75 | 8.83 |
| ADS-B 1090 | setting 1 (collapsed, 21 cm) | averaged_zoom | 5.28 | 5.97 | 6.37 |

## Caveats

- SWR understates this antenna more than any other here. It is receive-only, and on receive a few dB of mismatch loss is usually swamped by external noise, so a poor match does not mean poor listening. Nothing in this survey measures receive sensitivity.
- Unlike the Smiley, it carries no matching coil, so at lengths near a half-wave it presents a very high impedance and reads badly - 20:1 on 2m at full extension.
- Captured against the 2026-09-20 BNC calibration without a fresh load reconnect verification, at the operator's direction; the adapter was assumed undisturbed since the Smiley run.
- Federal UHF has no valid measurement at settings 2, 5 and 8: a persistent local transmitter at 411.675 MHz pushed the calibrated reflection past unity. The same frequency is the worst point in the 2026-09-19 load verification and broke the Smiley's federal-UHF zooms.
- Fixed upright bench geometry on a secured fixture, no counterpoise; the USB cable remained part of the RF environment. Changing setting means handling the antenna, so every setting change is also a remount.
- Handheld antennas normally interact with the scanner chassis and operator. Treat these as fixture-specific comparisons.
- [Package method and calibration notes](../../README.md) · [immutable historical manual testing](../../manual-testing/)
