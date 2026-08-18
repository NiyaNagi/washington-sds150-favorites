# Reproduce this EFHW build and measurement

## Build

1. Cut exactly 62.5 ft (750 in) of radiator wire.
2. Attach the feed end to the GOWENIC 10 W generic EFHW module.
3. Form an 8 in feed-end strain loop and a 14 in far-end tie-off loop. Do not
   remove another 22 in; those allowances are already part of the 62.5 ft
   physical conductor.
4. Install as a sloper with the transformer/feed end 3 ft above ground and the
   far end 25 ft above ground.
5. Connect a 96 in counterpoise to the coax shield / transformer ground.
6. Lay the counterpoise straight on the ground, angled away from the radiator.
7. Use the 12 ft coax route recorded for this test and do not install a choke.

## Measure

1. Keep the NanoVNA-H, adapter chain, and reference plane unchanged.
2. Set 1.8-148 MHz, 400 overlapping 101-point segments, yielding 40,001 unique
   points at nominal 3.655 kHz spacing and 1 kHz measurement bandwidth.
3. Capture raw OPEN, SHORT, and 50-ohm LOAD standards at the antenna-side
   adapter plane with device calibration disabled during each scan.
4. Solve the software one-port ideal OSL error terms.
5. Physically disconnect and reconnect the LOAD, repeat the full-span sweep,
   and reject the calibration if reconnect behavior is materially worse than
   the baseline in `data/measurement_metadata.json`.
6. Replace the LOAD with the undisturbed final antenna and repeat the full span.
7. Run:

```bash
python3 antenna-results/antennas/gowenic-efhw/generate_report.py \
  --source /path/to/final/antenna.s1p \
  --raw-capture /path/to/final/antenna_raw.npz \
  --measurement-summary /path/to/final/summary.json \
  --final-measurement-dir /path/to/final \
  --calibration-dir /path/to/final/full_calibration \
  --history-root /path/to/nanovna_measurements
```

The generator uses only NumPy and Matplotlib and recreates every chart, table,
metadata file, and offline interactive report.
