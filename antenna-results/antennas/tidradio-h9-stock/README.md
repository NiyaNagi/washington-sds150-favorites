# TIDRADIO H9 stock antenna — invalid / inconclusive

> **Excluded from every scorecard, chart, ranking, and recommendation.**

One broadband capture was taken and immediately looked electrically open across the bands this antenna is designed for. Testing was stopped before any zoom or reseat verification.

## Why this capture is invalid

The capture shows a near-total reflection across the antenna's own design bands: 2m, VHF land mobile, marine, railroad, NOAA weather, 1.25m, UHF land mobile, and the T-band all read as an effectively infinite standing-wave ratio, which is the signature of an open or unseated connection rather than a working dual-band whip. The capture was never repeated after a reseat, so nothing here can be attributed to the antenna itself.

The raw capture is preserved for traceability:

- [antenna.s1p](measurements/2026-08-16/antenna.s1p)
- [antenna_raw.npz](measurements/2026-08-16/antenna_raw.npz)
- [summary.json](measurements/2026-08-16/summary.json)

No repeat verification was performed because the user skipped it. These files must not be interpreted as antenna performance. A new, reseated capture plus verification would be required before including this model.

SWR is impedance match only—not receive gain, sensitivity, pattern, or decoding performance.
