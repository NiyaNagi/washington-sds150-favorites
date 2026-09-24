# RF environment

Measurements of the local interference environment: what the radios have to hear through at the operator's
QTH (Ames Lake / Redmond). Each survey is a dated folder with its report, charts and raw data.

| Survey | Instrument and antennas | Headline |
|---|---|---|
| [2026-09-23](2026-09-23-survey/README.md) | tinySA (basic); desk Smiley, JYR8010 EFHW, SG7900 on the porch, D3000N discone on the roof | At the desk, VHF noise runs ~20 dB above ITU "city" and a 12.288 MHz clock drops birdies on 147.450/147.4625/442.375; the porch and roof antennas are 15–19 dB quieter and birdie-free. A 68.69 kHz supply (6 m comb), a 120.000 MHz carrier and a 16–17 MHz emitter are house-wide. HF is rural on the main bands but residential-to-city on 60/30/17 m. The roof discone feeds FM at −26 dBm: fit an FM band-stop filter for the SDS150 |

- **[RFI-HUNT.md](RFI-HUNT.md):** the switch-off procedure that pins each finding to a device, with the live
  monitor, the cable-only test and the list of candidate devices.
- **[tools/](tools/README.md):** the tinySA driver, survey runner, analysis scripts, hunt monitor and chart
  generator.

Only measured frequencies and levels are committed here. Anything matched against the licensed local catalog
(RadioReference rows) is built into the gitignored `.wasds150-home/rf-environment/` and is never copied into this
folder.
