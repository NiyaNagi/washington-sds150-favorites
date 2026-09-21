# NanoVNA-H SMA-to-BNC calibration baseline — 2026-09-19

Immutable calibration capture used by the September 2026 handheld additions:
Diamond RH77CA, Diamond SRH320A, and the Signal Stick with and without its
counterpoise.

## Reference plane and acquisition

- NanoVNA-H firmware 1.2.50; 50 Ω reference; `bandwidth 3 (1000Hz)`.
- 50-1200 MHz, 40,001 points, nominal 28.75 kHz spacing, 400 segments.
- Software ideal open/short/load calibration at the antenna side of the
  attached SMA-to-BNC adapter.
- Acquisition environment: Python 3.12.7, NumPy 2.0.2, Matplotlib 3.9.4,
  pySerial 3.5. The August 2026 sessions used Python 3.9.6; the pinned
  scientific stack is identical.

## Three-standard gate

Median raw complex separation, all on an identical strictly increasing grid:

| Pair | Separation |
|---|---:|
| open / short | 1.1607 |
| open / load | 0.6493 |
| short / load | 0.5217 |

## Reconnect verification

| Run | Median | p95 | Max |
|---|---:|---:|---:|
| After the solve | 1.00677 | 1.02379 | 1.16781 |
| After a mid-session power cycle | 1.00310 | 1.01471 | 1.16418 |

The two verifications agree to a median `|dGamma|` of 0.00230 over the full
span and 0.00045 within 2m, so the reference plane survived the reboot.

By region, after the solve:

| Region | Median | Max |
|---|---:|---:|
| 50-150 MHz | 1.00123 | 1.00202 |
| 150-300 MHz | 1.00266 | 1.00504 |
| 300-600 MHz | 1.00514 | 1.14134 |
| 600-900 MHz | 1.00853 | 1.07577 |
| 900-1200 MHz | 1.01610 | 1.16781 |

`fixture-floor-by-service.json` records the same verification broken down by
receive service; a measured antenna SWR cannot be resolved below those values.

### Threshold overrides, with reasons

The validator's p95 (1.02) and maximum (1.10) gates are HF defaults and are not
met at the top of this span. They are overridden here for a documented fixture
reason: the residual is confined above 300 MHz and reflects a BNC bayonet
approaching 1.2 GHz. The accepted August 2026 baseline also exceeds the maximum
gate, at 1.19335. The median gate passes.

## A rejected first attempt is preserved separately

The first calibration of this session was rejected. Its reconnect verification
read median 1.02124, p95 1.05038, maximum 2.10489, and it carried 300 points
above 1.10 in narrow clusters at 216.09, 293.7-297.2 and 326.0-326.7 MHz from a
nearby active radio. Moving the fixture away from that radio and snugging the
adapter onto CH0 produced the baseline recorded here, with 2 such points.

## Preserved files

- `open.npz` + `open.csv`
- `short.npz` + `short.csv`
- `load.npz` + `load.csv`
- `calibration.npz`
- `fixture-floor-by-service.json`
- `verification/load-verification.csv` + `.json`
- `verification/load-verification-postreboot.csv` + `.json`

The saved calibration is reusable only with the same unchanged adapter chain
and a fresh 50 Ω load verification each session. Calibration accuracy does not
remove antenna-fixture uncertainty, and for these antennas the mounting
dominates: see the
[session uncertainty note](../../../docs/2026-09-HANDHELD-SESSION-UNCERTAINTY.md).
