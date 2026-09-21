# AnyTone AT-D890UV OEM long whip

The long AnyTone whip holds the entire NOAA weather window and the whole federal-UHF block at or below 2:1, the only antenna in the survey to do both. It is poor on its own nominal 2m and 70cm bands in this fixture.

> **SWR is impedance match only.** It does not measure receive gain, sensitivity, radiation pattern, or on-air decoding.

## Measurement inventory

- Connection: SMA-female antenna via an SMA male-to-male adapter.
- Measurement context: Handheld bench fixture, SMA plane.
- Calibrated 50-1200 MHz broadband sweep: 40,001 points (~28.75 kHz spacing).
- Three-pass complex-averaged service zooms override broadband data for the same configuration and service.
- [SMA adapter plane](measurements/2026-09-20-sma-adapter/antenna.s1p): AnyTone's long OEM dual-band antenna, approximately 38 cm, measured at the adapter's outer face.

## Conclusions

- Useful around 406-470 MHz, strongest at the 420 MHz edge.
- Broadest measured handheld-fixture match across both UAT 978 and ADS-B 1090, though match alone does not establish tracking sensitivity.
- Poor at VHF and 700/800 MHz in this no-radio-chassis fixture.

## Analysis charts

### Broadband overview

![AT-D890UV 38cm Broadband overview](charts/broadband-overview.png)

### Scanner scorecard

![AT-D890UV 38cm Scanner scorecard](charts/scanner-scorecard.png)

### Authoritative averaged zoom panels

![AT-D890UV 38cm Authoritative averaged zoom panels](charts/authoritative-zoom-panels.png)

### Impedance and return loss

![AT-D890UV 38cm Impedance and return loss](charts/impedance-return-loss.png)


## Caveats

- Above 877.454 MHz it exhausts the fixture's calibrated dynamic range: the broadband Touchstone is truncated there and 33cm, 900 MHz trunking, UAT 978 and ADS-B 1090 have no valid measurement at all.
- VHF figures describe the antenna plus a fixture with no radio chassis.
- Fixed upright bench geometry on a secured fixture, no counterpoise; the USB cable remained part of the RF environment.
- Vehicle body, mounting location, feed line, and antenna-side adapter are part of this installed result.
- [Package method and calibration notes](../../README.md) · [immutable historical manual testing](../../manual-testing/)
