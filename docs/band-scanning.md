# Band-oriented scanning and listening packs

The generated catalog includes `BAND01` through `BAND12`. These are ordinary
Favorites Lists assembled from the project's existing cited channels, so they
can be enabled, avoided, location-controlled, exported, and installed like any
other list.

A Favorites List cannot contain a continuous frequency range: it scans discrete
programmed channels. For exploratory sweeps, use the SDS150 **Service Search**
or **Custom Search** feature alongside the band pack. Store confirmed voice
channels in a local Favorites List; permanently avoid constant data carriers.

Band packs intentionally reuse existing lists. Enable a pack **or** its source
components for a listening session, not both, or the same transmission may be
scanned repeatedly. Do not install/enable all 136 catalog entries at once: use
the Profile and guarded bulk installer to select a practical subset, and keep
only one or two scenario packs active for a responsive scan cycle.

## Listening packs

| Key | Pack | Reused content | Suggested exploratory search |
|---|---|---|---|
| BAND01 | Civil Air | WA airports, Seattle Center/FSS, guard, SAR, medevac, airshows | 118.000–136.975 MHz, AM |
| BAND02 | Military Air | 243 guard, JBLM/Whidbey/Fairchild/CAP, USCG air, airshows | 225.000–399.975 MHz, AM |
| BAND03 | Amateur VHF/UHF | Repeaters, linked systems, ARES/RACES, simplex, ISS/satellites | 29.500–29.700; 50–54; 144–148; 222–225; 420–450; 902–928 MHz |
| BAND04 | Marine VHF | USCG, VTS, distress/safety, ferries, ports, rescue | 156.050–157.425 and 160.600–162.025 MHz, FM |
| BAND05 | Railroad | Western/eastern AAR road, yard, dispatch and maintenance | 159.810–161.565 MHz, NFM |
| BAND06 | Personal & Itinerant | FRS/GMRS, MURS, CB, color-dot/itinerant | 26.965–27.405 AM; 151–155 and 462–468 MHz FM/NFM |
| BAND07 | Public Safety Interop | SAR, CEMNET, NIFOG V/U/7/8, STATEOPS, DNR/NIFC | Scan programmed channels first; broad searches create heavy noise |
| BAND08 | Weather, SAR & Emergency | NOAA Weather, SAR, guard, medevac, HEAR/MED | Use Weather Scan/Weather Alert Priority plus programmed channels |
| BAND09 | Federal Wildland & Parks | NPS, USFS, NIFC, DNR and mountain/wilderness profiles | 162–174 MHz NFM; incident assignments change |
| BAND10 | Medical & Medevac | HEAR/MED, Airlift/Life Flight, AMR | 150–174 and 450–470 MHz; NXDN requires upgrade |
| BAND11 | Roads, Rail & Utilities | WSDOT conventional, tow, ferry, rail, utility voice | 150–174, 450–470 and 851–869 MHz; avoid SCADA/data |
| BAND12 | Business, Events & Media | Itinerant, transit DMR/NXDN, event UHF, air boss, ENG | 150–174 and 450–470 MHz; use Close Call at venues |

Use **Auto** step/modulation unless the table specifies AM or NFM. Start with a
2-second delay. Attenuation can help at airports, summits, or dense RF sites.
Avoid these common non-voice signals after identification: NOAA/AIS data,
SCADA/telemetry, paging, control channels, packet/APRS, trunk control channels,
and continuous digital carriers unsupported by the installed upgrades.

## Amateur-specific notes

The SDS150 receives FM/NFM and supported digital voice but does not demodulate
SSB or CW. The pack therefore emphasizes FM calling, repeaters and satellites:

- 10 m FM simplex: 29.600 MHz
- 6 m FM simplex: 52.525 MHz
- 2 m FM calling: 146.520 MHz
- 1.25 m FM calling: 223.500 MHz
- 70 cm FM calling: 446.000 MHz
- Mason County ARC: 146.720 MHz output, PL 103.5 (receive does not require tone)

Local coordinator plans take precedence over national recommendations. Use the
WWARA/ERAC or club directory before adding a repeater, and program the repeater
**output**, not its input.

## Other worthwhile scenarios

The statewide catalog already covers most useful SDS150 voice scenarios:
public safety, fire/EMS, wildfire, federal parks/forests, aviation, military,
marine, rail, amateur, satellites, personal radio, business, events, medical,
roads, utilities and weather. Remaining useful workflows are generally
location/time dependent rather than fixed statewide lists:

- Close Call at fairs, stadiums, trailheads, construction sites and ski areas
- Airshow/Seafair seasonal profiles
- Incident-specific wildfire ICS-205 channels
- Local school, campus, mall and hospital operations
- Wireless microphones and production intercom at events
- Racing pit/official channels

Do not create permanent entries from an unidentified hit. Confirm frequency,
mode, purpose, location and whether the audio is legal/appropriate to monitor.

## Sources

- FAA Aeronautical Information Manual, emergency 121.5/243.0 MHz and aviation procedures: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap6_section_3.html
- FAA chart and publication portal: https://www.faa.gov/air_traffic/publications/
- ARRL national amateur band plan: https://www.arrl.org/band-plan
- USCG/NAVCEN U.S. marine VHF channels: https://www.navcen.uscg.gov/us-vhf-channel-information
- CISA National Interoperability Field Operations Guide 2.02: https://www.cisa.gov/sites/default/files/2024-12/NIFOG%202.02_508%20FINAL%20VERSION%2012%2003%202024.pdf
- Washington Field Operations Guide 1.10: https://mil.wa.gov/asset/6a1eeab054e7c/Washington-Field-Operations-Guide_FOG_1.10.pdf
- NOAA Weather Radio Washington stations: https://www.weather.gov/nwr/stations?State=WA
- FCC Personal Radio Services rules: https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-95
- FCC Industrial/Business licensing overview: https://www.fcc.gov/wireless/bureau-divisions/mobility-division/industrial-business
