# RF environment

Measurements of the local interference environment: what the radios have to hear through at the operator's
QTH (Ames Lake / Redmond). Each survey is a dated folder with its report, charts and raw data.

| Survey | Instrument | Headline |
|---|---|---|
| [2026-09-23](2026-09-23-survey/README.md) | tinySA (basic), desk whip + Smiley + JYR8010 EFHW | VHF at the desk sits 18–29 dB above the analyzer floor from local equipment; a 12.288 MHz clock drops birdies on 147.450/147.4625/442.375; a 68.69 kHz switcher combs 6 m; HF is rural on the main bands but residential-to-city on 60/30/17 m from a mains-synchronous switcher and a steady 16–17 MHz emitter |

- **[RFI-HUNT.md](RFI-HUNT.md):** the switch-off procedure that pins each finding to a device, with the live
  monitor.
- **[tools/](tools/README.md):** the tinySA driver, survey runner, analysis scripts, hunt monitor and chart
  generator.

Only measured frequencies and levels are committed here. Anything matched against the licensed local catalog
(RadioReference rows) is built into the gitignored `.wasds150-home/rf-environment/` and is never copied into this
folder.
