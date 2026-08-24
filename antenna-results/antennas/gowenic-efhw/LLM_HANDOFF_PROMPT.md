# LLM handoff prompt

You are continuing a calibrated NanoVNA antenna-characterization workflow.
Reproduce the complete process rather than only summarizing an existing plot.

Build under test:
- Generic GOWENIC "No Tune End Fed Half Antenna" 10 W module, Amazon ASIN
  B0C3JVM9SR. It resembles a compensated QRPGuys-style design but is not a
  QRPGuys-branded board.
- 62.5 ft total physical radiator wire.
- 8 in feed-end strain loop and 14 in far-end tie-off loop.
- Sloper: feed end 3 ft, far end 25 ft.
- 96 in counterpoise connected to coax shield / transformer ground, laid
  straight on the ground and angled away from the antenna direction.
- 75 ft LS400 outdoors and no common-mode choke.

Measurement requirements:
1. Preserve every run and record each physical configuration change.
2. At the antenna-side adapter reference plane, capture fresh OPEN, SHORT, and
   50-ohm LOAD data from 1.8 through 148 MHz using 400 overlapping 101-point
   segments (40,001 unique points, nominal 3.655 kHz spacing) with the VNA's
   internal correction disabled during raw captures.
3. Solve and apply a software one-port ideal OSL calibration.
4. Physically reconnect the load and run an independent full-span verification.
   Treat this as connector-repeatability and drift evidence, not traceable
   accuracy, because the same load is used as the calibration standard.
5. Connect the final antenna without disturbing its geometry and capture a new
   full-span calibrated complex-S11 sweep. Do not reuse pre-counterpoise sweeps
   as final data.
6. Export raw NPZ/CSV captures, calibrated RI Touchstone, point CSV, JSON/CSV
   band summaries, SWR/return-loss/impedance/Smith plots, a build schematic,
   tuning-progression visualization, metadata, reproduction steps, and a
   self-contained interactive HTML report.
7. Analyze all US amateur bands from 160m through 2m, with special emphasis on
   the intended 40m/20m/15m/10m harmonic set. Report minimum, maximum, median,
   impedance and return loss at minimum, percent coverage at SWR <=1.5/2/3, and
   the longest contiguous <=2:1 range.
8. State clearly that SWR measures impedance match, not gain, efficiency,
   radiation pattern, or receive sensitivity.
9. Distinguish the generic GOWENIC board from a genuine QRPGuys product.
10. Make generation deterministic and retain old runs as historical only when
    their configuration differs from the final counterpoise build.
