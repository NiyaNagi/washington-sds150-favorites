# RF-environment tools

Scripts that drive a **basic tinySA** (hardware v0.3, firmware 1.4) over its USB shell and analyse the results.
The tinySA enumerates as `USB Serial Device (COM17)`, VID 0483 / PID 5740. `tsa.py` refuses COM3, which is
an unrelated device.

| Environment | Used for |
|---|---|
| `.venv-chirp` | anything that talks to the tinySA (needs pyserial) |
| `.venv` | analysis scripts (stdlib only) |
| `.venv-nanovna` | `make_charts.py` (matplotlib) |

Never add a dependency to `.venv`. The analysis scripts are stdlib-only on purpose.

New runs write to `.wasds150-home/rf-environment/rf/`, which is gitignored; set `RF_OUT` to change it. Copy a
finished survey into a dated folder beside `2026-09-23-survey/` when it's worth keeping.

## Measure

| Script | What it does |
|---|---|
| `tsa.py` | Minimal shell driver. `python tsa.py version "rbw 10"` sends raw commands |
| `survey.py` | Multi-pass survey. `python survey.py p2` runs a phase; see `PHASES` for which antenna goes on which port (p1–p3: desk whips and EFHW; p4/p5: SG7900 LOW/HIGH; p6/p7: discone LOW/HIGH, with attenuated repeats). Every pass is kept so continuous and intermittent signals can be told apart. Fills the few points the firmware omits (e.g. 344.65 MHz in LOW mode) from neighbours and logs them; a lost prompt times out after 60 s and resyncs |
| `zoom.py` | 290-point high-resolution looks at listed frequencies |
| `zerospan.py` | Zero-span time captures with an envelope DFT: burst fraction and repetition rates (120 Hz = mains-synchronous) |
| `atten_test.py` | 0/10/20 dB attenuator test. External signals keep their level; analyzer-made products drop |
| `hunt.py` | Live fingerprint monitor for [RFI-HUNT.md](../RFI-HUNT.md) |

## Analyse

| Script | What it does |
|---|---|
| `analyze.py` | Emissions above a rolling floor, with persistence, width, band, empty-port comparison (`--baseline`) and catalog matches |
| `harmfit.py` | Fits a harmonic series n·F to each pass (switching/clock frequency, 1 Hz grid) |
| `comb.py` | Evenly spaced combs among persistent peaks |
| `acorr.py` | Autocorrelation of a sweep segment (periodic fine structure, e.g. a 32.7 kHz switcher inside a noise hump) |
| `hfnoise.py` | Per-band HF external noise Fa vs ITU-R P.372 categories, feedline-corrected |
| `vhfnoise.py` | Per-band VHF/UHF Fa for every antenna, feedline-corrected, with detection limits and bands masked by analyzer-made FM harmonics |
| `lineloss.py` | Feedline and window feed-through loss per antenna, and the correction of measured noise back to the antenna |
| `fingerprints.py` | Is each known emission present on each antenna? Levels relative to a distant FM/NOAA reference on the same antenna, so antennas of different gain can be compared and a source localised |
| `attclass.py` | Classifies features as real or analyzer-made from an unattenuated and an attenuated sweep |
| `hambirdies.py` | Persistent carriers inside ham bands, flagged against programmed channels |
| `attcmp2.py` | Fair att0-vs-att10 comparison per MHz block |
| `fine.py` | Text view of a segment: min/median/max per block, optional baseline |
| `impact.py` | Counts each radio's programmed channels on the measured problem zones |
| `make_charts.py` | Renders the survey charts (light and dark SVG) |

## Local indexes (never committed)

| Script | Writes |
|---|---|
| `build_index.py` | `freq_index.json`: every catalog frequency with its label and distance. Contains licensed rows |
| `programmed.py` | `programmed.json`: each radio's programmed frequencies, parsed from its fleet report |

Run both before `analyze.py`, `hambirdies.py` or `impact.py`:

```
.venv\Scripts\python.exe rf-environment\tools\build_index.py
.venv\Scripts\python.exe rf-environment\tools\programmed.py
```

## Instrument notes learned the hard way

- **Sweep time depends on the step, not just the RBW.** With a step smaller than the RBW, 11 kHz RBW runs at about
  4 ms per point. With a step much larger than the RBW, the firmware sub-samples each bin, and 3 kHz RBW took
  590 ms per point.
- **RBW 10 is the practical sensitivity setting.** Its floor is within ~2.5 dB of 3 kHz at a tenth of the time.
  LOW floor: −113 dBm at 11 kHz; HIGH: −117 to −121 dBm.
- **HIGH-input spurs sit at 30 MHz multiples** (270, 300, 330 … 480 MHz). The LOW input with `spur on` shows only
  the 0 Hz leakage and 30.000 MHz.
- **Below 1 MHz the LOW input's own leakage** sets the floor: −65 dBm at 25–150 kHz, −89 dBm at 1 MHz.
- **The HIGH-input attenuator is a single ~20 dB step.** Use the LOW input for attenuator tests.
- Killing a script mid-scan leaves the tinySA paused. Run `python tsa.py resume` to restore it.
- **The tinySA can freeze.** It stays enumerated on USB but stops answering, and even opening the port blocks.
  Only a power cycle clears it: switch off, unplug USB, reconnect, switch on. `tsa.py` sets a 5 s write timeout so
  a frozen unit raises instead of hanging, and `survey.py` retries a chunk whose prompt was lost.
- **The HIGH input has no filter.** A strong antenna (the roof discone delivers FM at −26 dBm) makes FM
  harmonics ×3…×9 across 264–960 MHz inside the analyzer. Use an FM band-stop filter on such antennas, or treat
  HIGH-input noise figures as upper bounds and check features with `attclass.py`.
- **Max-hold lets on-air traffic pose as interference** (APRS bursts on 144.390 looked like a desk cluster on
  the roof). Localise with the median across sweeps, as `fingerprints.py` does.
