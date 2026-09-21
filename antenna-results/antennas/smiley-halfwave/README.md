# Smiley 2m half-wave telescopic

Smiley Antenna Co. 2m half-wave telescopic flex, 144-148 MHz, BNC, collapsing to 8 in and extending to 36 in. Measured at all seven lengths, it is the only antenna in this survey with a broad 2m match, and it achieves it with no counterpoise at all. A half-wave is fed at high impedance and barely depends on a ground plane, which is exactly why it succeeds on a fixture where every quarter-wave whip fails.

> **SWR is impedance match only.** It does not measure receive gain, sensitivity, radiation pattern, or on-air decoding.

## Measurement inventory

- Connection: BNC antenna, direct to the measurement plane.
- Measurement context: Handheld bench fixture.
- Calibrated 50-1200 MHz broadband sweep: 40,001 points (~28.75 kHz spacing).
- Three-pass complex-averaged service zooms override broadband data for the same configuration and service.
- [setting 1 (collapsed, 22 cm)](measurements/setting-1-collapsed/antenna.s1p): Fully collapsed, 22 cm.
- [setting 2 (34.5 cm)](measurements/setting-2/antenna.s1p): Five sections retracted, 34.5 cm.
- [setting 3 (46 cm)](measurements/setting-3/antenna.s1p): Four sections retracted, 46 cm.
- [setting 4 (57.5 cm)](measurements/setting-4/antenna.s1p): Three sections retracted, 57.5 cm.
- [setting 5 (69 cm)](measurements/setting-5/antenna.s1p): Two sections retracted, 69 cm.
- [setting 6 (80 cm)](measurements/setting-6/antenna.s1p): One section retracted, 80 cm. The best 2m match in the survey.
- [setting 7 (fully extended)](measurements/setting-7-fully-extended/antenna.s1p): Fully extended; length not measured, catalogue figure is 36 in.

## Conclusions

- Useful around 406-470 MHz, strongest at the 420 MHz edge.
- Broadest measured handheld-fixture match across both UAT 978 and ADS-B 1090, though match alone does not establish tracking sensitivity.
- Poor at VHF and 700/800 MHz in this no-radio-chassis fixture.

## Analysis charts

### Broadband overview

![Smiley 1/2 wave Broadband overview](charts/broadband-overview.png)

### Scanner scorecard

![Smiley 1/2 wave Scanner scorecard](charts/scanner-scorecard.png)

### Authoritative averaged zoom panels

![Smiley 1/2 wave Authoritative averaged zoom panels](charts/authoritative-zoom-panels.png)

### Impedance and return loss

![Smiley 1/2 wave Impedance and return loss](charts/impedance-return-loss.png)

### Setting × service heatmap

![Smiley 1/2 wave Setting × service heatmap](charts/setting-service-heatmap.png)

## Best measured setting by service

[Download CSV](best-setting-table.csv). Rankings use authoritative median SWR, then maximum, then minimum.

| Service | Setting | Source | Min | Median | Max |
|---|---|---|---:|---:|---:|
| 6m amateur | setting 7 (fully extended) | broadband | 40.31 | 55.85 | 67.05 |
| FM broadcast | setting 2 (34.5 cm) | averaged_zoom | 1.33 | 3.16 | 11.17 |
| Civil air | setting 5 (69 cm) | averaged_zoom | 1.39 | 2.26 | 4.40 |
| 2m amateur | setting 6 (80 cm) | averaged_zoom | 1.22 | 1.39 | 1.63 |
| VHF LMR | setting 5 (69 cm) | averaged_zoom | 1.10 | 1.83 | 3.37 |
| Marine VHF | setting 5 (69 cm) | averaged_zoom | 1.22 | 1.52 | 1.77 |
| Railroad | setting 5 (69 cm) | averaged_zoom | 1.16 | 1.22 | 1.32 |
| NOAA weather | setting 5 (69 cm) | averaged_zoom | 1.12 | 1.13 | 1.14 |
| 1.25m amateur | setting 3 (46 cm) | averaged_zoom | 2.02 | 2.05 | 2.14 |
| Military air | setting 1 (collapsed, 22 cm) | averaged_zoom | 1.70 | 2.96 | 12.36 |
| Federal UHF | setting 6 (80 cm) | averaged_zoom | 2.33 | 2.81 | 4.09 |
| 70cm amateur | setting 3 (46 cm) | averaged_zoom | 2.36 | 2.56 | 3.29 |
| UHF LMR | setting 3 (46 cm) | averaged_zoom | 2.43 | 2.69 | 3.17 |
| T-band | setting 5 (69 cm) | averaged_zoom | 2.75 | 3.45 | 4.43 |
| 700 MHz public safety | setting 3 (46 cm) | averaged_zoom | 3.89 | 3.97 | 4.01 |
| 800 MHz public safety | setting 5 (69 cm) | averaged_zoom | 3.43 | 3.72 | 4.05 |
| 33cm amateur | setting 5 (69 cm) | averaged_zoom | 1.17 | 1.54 | 2.39 |
| 900 MHz trunking | setting 5 (69 cm) | averaged_zoom | 3.09 | 3.40 | 3.68 |
| UAT 978 | setting 7 (fully extended) | averaged_zoom | 4.46 | 4.80 | 5.25 |
| ADS-B 1090 | setting 5 (69 cm) | averaged_zoom | 3.31 | 3.46 | 3.73 |

## Caveats

- Setting 6 at 80 cm is a sharp optimum: 100 percent of 2m at or below 2:1, against 0 percent at both 69 cm and fully extended. Length matters more than any other variable measured in this survey.
- Resonant frequency and best match do not track together. Setting 5 is the only setting whose minimum falls inside the band rather than at the 144 MHz edge, yet it matches worse than setting 6, so the coil's matching network rather than length alone sets the match.
- Its baseline is the weakest of the September session, failing the p95 gate at 1.03800 above 300 MHz. The 2m floor of 1.00148 is excellent, so VHF results are solid and UHF results carry more uncertainty.
- Federal UHF has no valid measurement at settings 2 and 5.
- The manufacturer's 7 dBd gain claim is not measurable from SWR and is recorded here only as a claim.
- Fixed upright bench geometry on a secured fixture, no counterpoise; the USB cable remained part of the RF environment. Changing setting means handling the antenna, so every setting change is also a remount.
- Handheld antennas normally interact with the scanner chassis and operator. Treat these as fixture-specific comparisons.
- [Package method and calibration notes](../../README.md) · [immutable historical manual testing](../../manual-testing/)
