# Kenwood TH-D75A stock antenna — PROVISIONAL

> **This is not a survey entry.** It is deliberately excluded from the scanner
> antenna comparison, its scorecard, and every ranking, because it was captured
> at a reference plane that does not match the calibration used to correct it.
> Recapture it against its own calibration before quoting any number here.

Captured 2026-09-20. The antenna was screwed **directly onto CH0**, with the
SMA-to-BNC adapter **removed**, while the correction applied was the
2026-09-19 calibration solved at the **BNC face of that adapter**. The
calibration therefore de-embeds an adapter that was not in the path.

## What that does to the numbers

The error is a function of the adapter's electrical length, so it scales with
frequency:

- **VHF is essentially unaffected.** A few centimetres of adapter is negligible
  against a 2 m wavelength, so the VHF results below are trustworthy in
  magnitude even though the plane is wrong.
- **UHF is mildly affected**, mostly in phase, which shifts `R+jX` and the exact
  resonant frequency more than it shifts SWR.
- **700 MHz and above is the least trustworthy.** Treat the 700/800 MHz figures
  as unusable.

Separately, the sweep exceeded the fixture's calibrated dynamic range above
714.930 MHz, so the broadband Touchstone is truncated there
(`broadband-excluded.json`), and the 33cm, 900 MHz trunking, UAT 978 and
ADS-B 1090 zooms all failed the passive-physics gate and have no valid data at
all. 15 of 19 services were captured.

## Why this capture is worth keeping

It is the control experiment for the whole September 2026 handheld session. The
TH-D75A stock whip is a known-good dual-band antenna that demonstrably works on
both bands on its radio.

| Service | Minimum | Median | Coverage <=2:1 |
|---|---:|---:|---:|
| 2m | 20.467 | 24.942 | 0.0% |
| VHF LMR | 37.743 | 63.682 | 0.0% |
| NOAA weather | 66.826 | 72.771 | 0.0% |
| 1.25m | 4.503 | 7.658 | 0.0% |
| Federal UHF | 1.535 | 1.857 | 69.0% |
| **70cm** | **1.230** | **1.435** | **86.1%** |
| UHF LMR | 2.372 | 3.556 | 0.0% |
| T-band | 2.759 | 3.906 | 0.0% |

Strongest matches sit at 218.3 MHz (1.91), 412.5 MHz (1.85), **427.5 MHz
(1.25)** and 442.7 MHz (1.82).

The instrument finds this antenna's 70cm resonance at 427.5 MHz, exactly where
it belongs, and returns the best 70cm result of any antenna measured in this
fixture. The same sweep, on the same antenna, reads roughly 25:1 on 2m.

That is not a measurement failure. It is the fixture: with no radio chassis and
no counterpoise, a compact VHF helical has nothing to work against, and the
instrument body and its cable become the other half of the antenna. This whip
depends on the chassis more than any other antenna in the session, which is why
it is simultaneously the worst at VHF and the best at UHF.

**Consequence for the rest of the survey:** the VHF figures for every
counterpoise-less handheld here describe the antenna *plus this fixture*, not
the antenna on a radio. The Diamond RH77CA's poor 2m result, which prompted a
full remount and repeat, is confirmed by this control as a property of the
fixture rather than of that antenna. See the
[session uncertainty note](../../docs/2026-09-HANDHELD-SESSION-UNCERTAINTY.md).

## To promote this to a real entry

1. Cut a fresh OSL calibration at the bare CH0 SMA plane, with the antenna's own
   connector type, and verify it with a load reconnect.
2. Recapture broadband and all 19 zooms against that calibration.
3. Only then add it to the generator's family registry.

Results taken at the bare SMA plane are a different measurement context from the
SMA-to-BNC bench fixture used by the rest of the survey, so they should not be
ranked against those entries even once recalibrated, unless the plane is made
to match.
