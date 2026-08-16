# Manual handheld antenna testing

This folder preserves the manually captured NanoVNA-H antenna sweeps and their
generated comparison artifacts from August 15, 2026.

## Contents

- `Anteena Extendable/` — 19 sweeps of the generic telescoping antenna at
  half-step extension settings from 1 through 10.
- `RH789/` — 11 sweeps of the RH789 telescoping antenna at half-step extension
  settings from 1 through 6.
- `Diamond SRH77CA + BNC Adapter/` — Diamond SRH77CA with its BNC adapter.
- `Remtronix 920/` — Remtronix 920 BNC antenna.
- `TID TD771 + SMA + BNC Adapter/` — TID TD771 with the measured adapter chain.
- `swr-comparison-report.html` — self-contained comparison report.
- `swr-comparison-common-ham-bands.csv` — estimated band-center SWR matrix.
- `swr-comparison-common-ham-bands.png` — two-panel comparison heatmap.
- `swr-*.png` — broadband plots by antenna family.
- `compare_swr.py` — parser and report generator used to produce the comparison.

Original spellings in source directory and file names are retained for measurement
provenance.

## Measurement limitations

Each Touchstone file contains 101 S11 samples from 50 through 1200 MHz, giving a
nominal spacing of 11.5 MHz. The generated band-center comparisons interpolate
complex S11 rather than SWR, but the source spacing is still too coarse to
establish true in-band minima, maxima, usable bandwidth, or transmitter safety
for narrow amateur allocations.

Use these captures as a broadband reconnaissance set and relative comparison.
Before transmitting, repeat the relevant band with a calibrated, high-density
sweep at the exact fixture reference plane and evaluate the radio's transmit
frequency, including repeater offset.

The `nanovna-saver.exe` application found beside the source results was not copied:
it is a third-party executable/tool, not measurement output or repository source.
