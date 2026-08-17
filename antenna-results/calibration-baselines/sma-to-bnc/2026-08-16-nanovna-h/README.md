# NanoVNA-H SMA-to-BNC calibration baseline — 2026-08-16

Immutable calibration capture used by the scanner-antenna measurements.

## Reference plane and acquisition

- NanoVNA-H firmware 1.2.50; 50 Ω reference.
- 50-1200 MHz, 40,001 points, nominal 28.75 kHz spacing.
- Software ideal open/short/load calibration at the antenna side of the attached SMA-to-BNC adapter.
- The adapter chain must remain physically unchanged.

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
| Full 50-1200 MHz | 1.00135 | 1.01044 | 1.19335 |
| VHF high 137-225 MHz | 1.00032 | 1.00041 | 1.00127 |

The saved calibration is reusable only with the same unchanged adapter chain and a fresh 50 Ω load verification each session. Recalibrate after reconnecting or moving the chain if verification is not consistent. Fixture geometry still affects handheld antennas even when the reference-plane calibration is accurate.
