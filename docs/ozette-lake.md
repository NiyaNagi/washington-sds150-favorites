# Lake Ozette and the north-west Olympic coast

Programming notes for the `OZ01` Favorites List and the `h9-ozette` channel
plan, covering Lake Ozette, Cape Alava, Neah Bay, Sekiu, Clallam Bay, Forks
and La Push.

Location anchors come from the USGS GNIS Domestic Names dataset:

| Feature | GNIS id | Latitude | Longitude |
| --- | ---: | ---: | ---: |
| Ozette Lake | 1531490 | 48.0947448 | -124.6372175 |
| Cape Alava | 1503792 | 48.1658959 | -124.7324598 |
| Ozette (populated place) | 1511209 | 48.1547881 | -124.6671768 |

There is no GNIS record for "Ozette Ranger Station" or "Ozette Campground";
USGS removed man-made and administrative features from GNIS, and the National
Park Service does not publish coordinates for either. Ozette Lake is used as
the location-control centre with a 60-mile radius.

## What the TD-H9 cannot do here

The TD-H9 receives 76-108, 108-136 (AM), 136-174, 220-230, 350-390 and
400-520 MHz, and demodulates only AM, FM and NFM. A large part of the
statewide catalog is therefore unreachable from this radio, and the plan drops
it with a stated reason rather than pretending otherwise. Run
`wasds150 plan show h9-ozette` to see the current exclusion list.

Deliberately excluded:

| Excluded | Reason |
| --- | --- |
| All P25 trunked systems (PSERN, WSP, WSDOT, SREC, JIWN) | 700/800 MHz and digital |
| STATEOPS 1-5 (852 MHz) | Outside receive coverage |
| CEMNET (45/46 MHz) | Below the receive floor |
| CB (27 MHz) | Below the receive floor |
| 7CALL/7TAC (769-775 MHz), 8CALL/8TAC (851 MHz) | Outside receive coverage |
| USCG land mobile "NET" channels | P25, frequently encrypted |
| Federal LE2-LE5, LE11-LE15 | P25 |
| Clallam County's four trunked systems | Trunked, assumed P25 |
| Amateur DMR, D-STAR and Fusion repeaters | Not demodulated |
| Marine channel 70, AIS 1/2 | Data only, no voice |
| Most military UHF air (225-350 MHz) | Outside receive coverage |

The SDS150 covers nearly all of the above, which is the reason the catalog
keeps them: one database, different radios, different subsets.

## Sourcing

Every channel in `OZ01` carries its own source URL in the channel note.

| Category | Source |
| --- | --- |
| Olympic NP, Olympic NF, USFS, DOI | RadioReference US Government (Washington), aid/2373 |
| WA DNR Olympic Region | RadioReference WA Natural Resources, aid/2372 |
| Clallam County | RadioReference Clallam County, ctid/2962 |
| Makah, Quileute, City of Forks | FCC ULS bulk Private Land Mobile database |
| SAR, LERN, OSCCR, REDNET | Washington Field Operations Guide 1.10 and RadioReference WA Mutual Aid |
| Marine channels and vessel traffic sectors | USCG NAVCEN and 33 CFR 161.12 |
| NOAA Weather Radio | National Weather Service station dataset |
| Aviation | FAA airport records via AirNav; Seattle ARTCC sectors from RadioReference aid/2235 |
| Amateur repeaters | RepeaterBook and the WAFOG Clallam County AUXCOMM tables |
| FRS, GMRS, MURS | 47 CFR Part 95 |

Repeater inputs come from a licence record or published coordination data.
None are derived from a band-plan convention, so a repeater whose input is not
published is programmed receive-only rather than guessed at.

Tones absent from a source are left empty. FCC ULS never publishes CTCSS, so
the Makah, Quileute and City of Forks repeaters have inputs but no tone; they
will open on carrier squelch for listening.

## Local highlights

- **DNR Ozette 159.255 (192.8 PL)** is the Washington DNR Olympic Region
  repeater named for this location, and the single most locally relevant
  channel in the list.
- **Seattle Center sector 03 on 125.100** is fed by the Neah Bay RCAG - the
  air traffic sector directly overhead.
- **Prince Rupert Traffic channel 74 (156.725)** is the vessel traffic sector
  covering the water off Cape Alava. Seattle Traffic 5A (156.250) takes over
  east of 124 degrees 40 minutes west.
- **NOAA KIH36 on 162.550** transmits from Bohokus Peak above Neah Bay and is
  the primary weather station at the lake. KXI27 on 162.425 from Clearwater
  near Forks is the backup. Clallam County SAME code is 053009.
- **Clallam County West Dispatch 453.375 (103.5 PL)** carries the Sheriff,
  Forks PD and La Push PD.
- **Ellis Mountain 147.060 (100.0 PL)** at Clallam Bay is the nearest 2 m
  amateur repeater; Gunderson Mountain 145.210 and Mount Octopus 147.280 near
  Forks cover the west end.

## Transmit policy

The plan programs transmit only where a licence covers it:

- GMRS main channels 1-7 and 15-22, and the eight repeater pairs, transmit.
- **FRS channels 8-14 are receive only.** They are FRS-only interstitials; a
  GMRS licence does not authorize transmitting there, and the radio's lowest
  power setting exceeds the FRS limit for those channels.
- MURS and the amateur bands transmit.
- Everything else is written with CHIRP `Duplex=off`, which inhibits transmit
  in the radio rather than relying on the operator to remember.

No GMRS repeater is publicly published anywhere in Clallam County - RepeaterBook
returns no results for the county and every nearby town, and the one myGMRS
listing for Port Angeles paywalls its tones. The eight repeater channels are
therefore programmed with standard pairs and no access tone, ready to have a
tone added on site.

## Programming the radio

```
wasds150 --home .wasds150-home sources update --only wwara --apply
wasds150 --home .wasds150-home plan show h9-ozette
wasds150 --home .wasds150-home plan export h9-ozette --out wasds150-output/radios
```

Then, in the CHIRP virtual environment:

```
python scripts/radios/fetch_chirp_tdh9_module.py
python scripts/radios/probe_tdh9.py --port COM3
python scripts/radios/program_tdh9.py --port COM3 --label radio-a --backup-only
python scripts/radios/program_tdh9.py --port COM3 --csv wasds150-output/radios/h9-ozette.csv --execute
```

The TD-H9 is not supported by any released CHIRP build; support exists only as
a test module attached to CHIRP issue 12216. The radio must be powered on for
its USB-C serial port to enumerate, and the Kenwood K1 two-pin CH340 cable is
more reliable than the native USB-C connection.
