# NanoVNA-H vehicle-adapter calibration baseline - 2026-08-16

Immutable calibration capture used for the installed Taurus triband vehicle antenna.

## Reference plane and acquisition

- NanoVNA-H firmware 1.2.50; 50 ohm reference.
- 50-1200 MHz, 40,001 points, nominal 28.75 kHz spacing.
- Reference plane: NanoVNA port 0 -> SMA-to-BNC-female adapter -> BNC plane.
- The antenna-side BNC-to-PL-239 adapter, vehicle feed line, mount, and vehicle body remain part of the DUT.
- This calibration is independent of the handheld SMA-to-BNC fixture baseline.

## Preserved files

- `open.npz` + `open.csv`
- `short.npz` + `short.csv`
- `load.npz` + `load.csv`
- `calibration.npz`
- `verification/load-reconnect-verification.csv`
- `verification/load-reconnect-verification.json`

## Reconnect verification

| Region | Median SWR | p95 SWR | Maximum SWR |
|---|---:|---:|---:|
| Full 50-1200 MHz | 1.02638 | 1.11973 | 1.23518 |
| VHF 50-225 MHz | 1.00438 | 1.00766 | 1.00813 |
| UHF 225-512 MHz | 1.01454 | 1.02150 | 1.04843 |
| 700-941 MHz | 1.03053 | 1.17585 | 1.20647 |
| L-band 976-1092 MHz | 1.06803 | 1.11860 | 1.23518 |

Repeatability is strong through VHF/UHF and acceptable through the scanner range, with visibly higher residual uncertainty above 1 GHz. Recalibrate whenever the NanoVNA-side adapter chain changes. Do not reuse the handheld fixture baseline for this vehicle chain.
