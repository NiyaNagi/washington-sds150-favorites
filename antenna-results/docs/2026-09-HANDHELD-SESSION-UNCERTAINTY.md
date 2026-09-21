# September 2026 handheld session: measured uncertainty

This note records what was actually measured about the fixture during the
2026-09-19/20 session that added the Diamond RH77CA, Diamond SRH320A, and the
Signal Stick with and without its counterpoise. It exists because the session
measured its own repeatability instead of assuming it, and the answer changes
how the per-band numbers should be read.

> **SWR is impedance match only.** Nothing here establishes gain, sensitivity,
> pattern, or decode performance.

## The instrument and calibration are not the limiting factor

A fresh 50-1200 MHz OSL calibration was solved at the BNC face of the
SMA-to-BNC adapter, after a first attempt was rejected. Reconnect verification
against that solve:

| Run | Median | p95 | Max |
|---|---:|---:|---:|
| After the solve | 1.00677 | 1.02379 | 1.16781 |
| After a mid-session power cycle | 1.00310 | 1.01471 | 1.16418 |
| August 2026 baseline, for comparison | 1.00135 | 1.01044 | 1.19335 |

The two verifications differ by a median `|dGamma|` of 0.00230 across the full
span and 0.00045 within 2m. Sweep-to-sweep repeatability on a terminated load
was a median `|dGamma|` of 0.00064.

The p95 and maximum gates are the validator's HF defaults. They are not
achievable on a BNC bayonet approaching 1.2 GHz, and the accepted August
baseline also exceeds the 1.10 maximum. The residual is confined to the top of
the span; below 300 MHz the floor is a median of 1.001-1.003.

### Per-service floor

From the reconnect verification. A measured antenna SWR cannot be resolved
below these values, and they are preserved as
`calibration-baselines/sma-to-bnc/2026-09-19-nanovna-h/fixture-floor-by-service.json`.

| Service | Floor median | Floor max |
|---|---:|---:|
| 6m | 1.00067 | 1.00076 |
| FM broadcast | 1.00120 | 1.00136 |
| Civil air | 1.00154 | 1.00175 |
| 2m | 1.00175 | 1.00186 |
| VHF LMR | 1.00194 | 1.00280 |
| NOAA weather | 1.00196 | 1.00199 |
| 1.25m | 1.00264 | 1.00275 |
| Military air | 1.00351 | 1.01931 |
| Federal UHF | 1.00476 | 1.14134 |
| 70cm | 1.00498 | 1.01050 |
| UHF LMR | 1.00527 | 1.01421 |
| T-band | 1.00565 | 1.00892 |
| 700 MHz public safety | 1.00893 | 1.01135 |
| 800 MHz public safety | 1.00993 | 1.01387 |
| 33cm | 1.01248 | 1.06212 |
| 900 MHz trunking | 1.01255 | 1.02376 |
| UAT 978 | 1.01317 | 1.03730 |
| ADS-B 1090 | 1.01819 | 1.06268 |

## The antenna mounting is the limiting factor

These antennas have no counterpoise and no radio chassis. The instrument body
and its USB cable are the other half of the antenna, so how the assembly is
mounted is part of what is being measured.

**Free-standing on the instrument.** Two identical sweeps, nothing touched
between them, on the SRH320A:

| Band | Median `\|dGamma\|` | Gate |
|---|---:|---:|
| 2m | 0.14863 | 0.005 |
| 1.25m | 0.08349 | 0.005 |
| 70cm | 0.17912 | 0.005 |
| Federal UHF | 0.09767 | 0.005 |

**Secured.** Instrument taped down, cable fixed along a set route, whip
supported so it cannot sway, operator clear:

| Band | Consecutive | Cumulative over ~2 min |
|---|---:|---:|
| 2m | 0.0093-0.0117 | 0.0202 |
| 70cm | 0.0010-0.0022 | 0.0025 |

Securing the fixture improved 2m repeatability by roughly 13x and 70cm by
roughly 100x. The residual drifts monotonically rather than scattering, which
is consistent with slow thermal or mechanical settling: about 0.03 SWR at the
2m minimum over two minutes.

**Across a remount, the result moves much further.** The same antenna, same
calibration, before and after the fixture was disturbed and re-secured:

| | Before | After |
|---|---|---|
| 2m minimum SWR | 1.075-1.103 @ 146.3 MHz | 1.387 @ 148.0 MHz |
| 2m median SWR | ~1.17 | 1.600 |
| 70cm minimum SWR | 1.788 @ 420.0 MHz | 1.195 @ 422.1 MHz |

Both states were internally stable and they disagree by far more than the
drift within either one.

### A deliberate remount, measured end to end

The RH77CA was later recaptured at a second mounting against the same
calibration, as a direct test of the first result. Both runs are published, as
`first mounting` and `second mounting`.

| Service | Median `\|dGamma\|` | Median `\|dSWR\|` |
|---|---:|---:|
| 2m | 0.16351 | 0.88490 |
| 1.25m | 0.11706 | 1.33013 |
| Federal UHF | 0.14119 | 0.39225 |
| VHF LMR | 0.07621 | 0.66686 |
| 70cm | 0.07156 | 0.69921 |
| UHF LMR | 0.05146 | 0.78878 |

That is the remount uncertainty, measured rather than estimated: at 2m it is
roughly 16x the drift within a single mounting.

**What survives a remount and what does not.** The minimum-SWR frequencies at
UHF repeat across mountings to 0.1 MHz:

| Run | Strongest dips below 600 MHz |
|---|---|
| First mounting | 124.6 (1.54), 392.8 (1.48), 400.8 (1.12), 408.9 (1.50) |
| Second mounting | 392.7 (1.58), 400.8 (1.39), 412.8 (1.30), 420.8 (1.81) |
| Free-standing, discarded | 168.5 (1.98), 176.6 (1.30), 184.7 (1.78), 204.6 (1.55) |

The VHF behaviour moves with every remount while the UHF resonances stay put.
That is the expected split: at UHF the radiator is electrically large and
largely indifferent to what is behind it, while at VHF the instrument body and
its cable are half the antenna.

The qualitative result is robust even where the numbers are not. Three
independent RH77CA mountings put the 2m minimum at 4.263, 5.430 and 4.816, and
none of them has a single point at or below 2:1.

### The control experiment

The Kenwood TH-D75A stock whip was captured on 2026-09-20 screwed directly to
CH0. It is a **provisional** capture at a mismatched reference plane and is
excluded from the survey, but it settles what the fixture can and cannot
measure. See
[`antennas/kenwood-thd75a-stock/PROVISIONAL.md`](../antennas/kenwood-thd75a-stock/PROVISIONAL.md).

| Service | Minimum SWR | Median | Coverage <=2:1 |
|---|---:|---:|---:|
| 2m | 20.467 | 24.942 | 0.0% |
| VHF LMR | 37.743 | 63.682 | 0.0% |
| **70cm** | **1.230** | **1.435** | **86.1%** |
| Federal UHF | 1.535 | 1.857 | 69.0% |

This is a known-good dual-band antenna that works on both bands on its radio.
The instrument places its 70cm resonance at 427.5 MHz, exactly where it
belongs, and returns the best 70cm figures of any antenna measured in this
fixture. The same sweep reads about 25:1 on 2m.

The plane mismatch does not explain it: an adapter is a few centimetres, which
is negligible against a 2 m wavelength, so that error is smallest at VHF and
largest at UHF. The VHF result is real.

**This fixture cannot measure VHF match for a counterpoise-less handheld
antenna.** With no chassis, a compact VHF helical has nothing to work against
and the instrument body and cable become the other half of the antenna. Every
VHF figure in this session describes the antenna *plus this fixture*. It
follows that the Diamond RH77CA's poor 2m result is a property of the fixture,
not of that antenna - which is what the RH77CA remount and repeat had already
suggested and this control confirms.

### The half-wave that proves the rule

The Smiley 2m half-wave telescopic, measured 2026-09-20 at seven lengths, is
the counter-example that completes the argument. A half-wave is fed at high
impedance and barely depends on a ground plane, so if the fixture is the reason
every quarter-wave whip fails at VHF, a half-wave should succeed on the same
fixture. It does:

| Setting | Length | 2m minimum | at MHz | 2m median | Coverage <=2:1 |
|---|---|---:|---:|---:|---:|
| 7 | fully extended | 2.652 | 144.000 | 3.069 | 0% |
| **6** | **80 cm** | **1.223** | 144.008 | **1.391** | **100%** |
| 5 | 69 cm | 2.029 | 147.188 | 2.190 | 0% |
| 4 | 57.5 cm | 2.188 | 144.004 | 2.297 | 0% |
| 3 | 46 cm | 2.593 | 144.008 | 2.821 | 0% |
| 2 | 34.5 cm | 3.222 | 144.000 | 3.591 | 0% |
| 1 | 22 cm collapsed | 4.102 | 144.000 | 4.642 | 0% |

A single sharp optimum at 80 cm, falling away monotonically in both directions,
measured against a 2m floor of 1.00148. This is the only broad 2m match in the
survey and it needs no counterpoise.

Two details are worth keeping. Fully extended is *worse* than 80 cm, and
setting 5 is the only setting whose minimum falls inside the band rather than
pinned at the 144 MHz edge, yet it matches worse than setting 6. Resonant
frequency and best match therefore do not track together here, which points at
the coil matching network rather than electrical length alone.

## How to read the published numbers

- Every antenna in this session except the RH77CA was captured at **one
  mounting**, by choice. Those per-band figures are exact for their mounting
  and carry a remount uncertainty of the size the RH77CA pair measured
  directly: about 0.16 in `|Gamma|` and up to ~1 SWR at VHF.
- The RH77CA is published at two mountings so that spread is visible in the
  scorecard rather than only in this note.
- Differences between antennas that are smaller than a few tenths of SWR at
  VHF are not established by this data.
- Minimum-SWR **frequencies** at UHF are far more trustworthy than the SWR
  values themselves; they repeated to 0.1 MHz across mountings.
- The Signal Stick counterpoise result is safe despite this: the 2m minimum
  moves 6.405 to 1.386 and coverage at or below 2:1 moves 0 to 84.2 percent,
  roughly two orders of magnitude beyond the remount effect. The smaller
  shifts it shows on other services are **not** separable from remount effects.
- The same limitation applies to the August 2026 entries in this survey, which
  were captured one mounting per antenna with no remount check and no measured
  repeatability. This note quantifies a limitation those entries share; it does
  not make them wrong.

To resolve differences at the level of the drift floor, a future session should
capture each configuration across several independent remounts and publish the
spread, and interleave any A/B comparison rather than running it as two blocks.

## Dynamic range

Two broadband sweeps reached a nonphysical `|Gamma| >= 1` and were refused by
`nanovna_swr.py measure`, which preserved the raw capture. Both were recovered
with `derive_band_limited_broadband.py`:

- **SRH320A**: truncated at 909.798 MHz, retaining 74.8 percent of the sweep.
  Its 33cm zoom, UAT 978 and ADS-B 1090 also failed the gate. UAT 978 and
  ADS-B 1090 have no valid data at all and are reported as very poor / outside
  calibrated dynamic range rather than as a measurement.
- **Signal Stick, no counterpoise**: one isolated sample at 465.811 MHz
  (`|Gamma|` 1.0844), consistent with a local transmitter keying up during the
  sweep. That sample alone was dropped and the full span retained.

## Interference

The first calibration attempt showed 300 points above 1.10 SWR in narrow
clusters at 216.09, 293.7-297.2 and 326.0-326.7 MHz. Moving the fixture away
from an active radio reduced that to 2 points. Measurements in this note and
in the September packages were taken after that move.

## Instrument hangs

The NanoVNA's serial session hung twice during long capture runs and required
a physical power cycle each time. The second hang occurred with no process
interference at all, so it is a property of the instrument under sustained
segment scanning, not of the host tooling. The software calibration survives a
reboot; the mounting does not, because the power button is on the assembly that
carries the antenna.
