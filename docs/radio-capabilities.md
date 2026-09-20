# Radio capabilities

Generated from the radio profiles in `src/wasds150/radios/registry.py` by `wasds150 fleet docs`; do not edit by hand. Every plan picks stations by these capabilities, and `wasds150 fleet audit` fails a memory the radio cannot hold (`capability-violation`), a D-STAR machine on a radio without D-STAR (`dstar-unsupported`) and a D-STAR machine programmed as FM (`dstar-as-analog`).

| Radio | D-STAR | C4FM | DMR | NXDN | P25 | AM | Transmit | Verified |
|---|---|---|---|---|---|---|---|---|
| Anytone AT-D890UV | - | - | yes | yes | - | 108-137 MHz | 136-174, 220-225, 400-520 MHz | yes (2026-09-19) |
| Yaesu FTX-1 | - | yes | - | - | - | all receive bands | 1.8-2, 3.5-4, 5.3-5.4, 7-7.3, 10.1-10.15, 14-14.35, 18.068-18.168, 21-21.45, 24.89-24.99, 28-29.7, 50-54, 144-148, 430-450 MHz | no (2026-09-19) |
| Icom ID-52A | yes | - | - | - | - | 108-174, 225-374.995 MHz | 144-148, 430-450 MHz | no (2026-09-19) |
| Uniden SDS150 | - | - | yes | yes | yes | all receive bands | none (receive only) | yes (2026-09-19) |
| TIDRADIO TD-H9 | - | - | - | - | - | 108-136 MHz | 136-174, 220-260, 350-390, 400-520 MHz | yes (2026-09-19) |
| Kenwood TH-D75A | yes | - | - | - | - | all receive bands | 144-148, 222-225, 430-450 MHz | yes (2026-09-19) |

## Anytone AT-D890UV (`at-d890uv`)

- Receive: 87.6-108, 108-137, 136-174, 220-225, 400-520 MHz
- Transmit (hardware; licence decides use): 136-174, 220-225, 400-520 MHz
- Modes: AM, DMR, FM, FMB, NFM, NXDN, WFM
- AM only on: 108-137 MHz
- Memory: 4,000 channels; 250 groups/zones of up to 160; scan lists of up to 100; names up to 16 characters
- Contacts: DMR, NXDN, up to 500,000
- Notes: Tri-band DMR/NXDN/analog handheld in band mode 00014, with AM air-band and FM broadcast receive. 220-225 MHz and 480-520 MHz need that mode, set with the AT Options utility rather than the CPS dropdown; a radio in the factory US mode 00007 has neither. Channels live in named zones; scanning uses explicit scan lists of up to 100 members (firmware 1.05). AM air channels (108-137 MHz) and FM broadcast stations are separate CPS lists with their own zones and scan. DMR Tier I/II conventional only; NXDN conventional only via the NX_DMR firmware overlay; DMR and NXDN cannot be active at the same time. No P25. Programmed with the Anytone D890UV CPS by importing a CSV bundle (Tool > Import > .LST).
- Verified: yes, checked 2026-09-19
- Sources:
  - Anytone AT-D890UV user manual (radio-data/at-d890uv/firmware/manuals/)
  - AT-D890UV firmware 1.05 change log (radio-data/at-d890uv/firmware/Change-Log-D890UV-FW-v1.05.pdf)
  - KD0PNQ AT-D890UV Programming Guide rev 2026-04-07 (AM air band and FM broadcast lists)
  - radio-data/at-d890uv/firmware/options/AT_BANDS.txt (band mode 00014)
  - Hardware: bundle written, read back and exported, 2026-09-12

## Yaesu FTX-1 (`ftx1`)

- Receive: 0.03-174, 400-470 MHz
- Transmit (hardware; licence decides use): 1.8-2, 3.5-4, 5.3-5.4, 7-7.3, 10.1-10.15, 14-14.35, 18.068-18.168, 21-21.45, 24.89-24.99, 28-29.7, 50-54, 144-148, 430-450 MHz
- Modes: AM, C4FM, CW, FM, LSB, NFM, USB
- Memory: 999 channels; names up to 12 characters
- Notes: HF/50/144/430 MHz all-mode SDR transceiver: SSB, CW, AM, FM and C4FM digital. No D-STAR, DMR, NXDN or P25. Amateur transmit only. Programmed with RT Systems YPS-FTX1; CHIRP does not support it. PRELIMINARY: per-channel fields not yet confirmed against the manual.
- Verified: no, checked 2026-09-19
- Sources:
  - Yaesu FTX-1 series product page, https://yaesu.com/product-detail.aspx?Model=FTX-1+Series (receive 30 kHz-174 MHz and 400-470 MHz; SSB, CW, AM, FM and C4FM digital; transmit HF/50/144/430 MHz)
  - FTX-1 series operation manual, https://www.yaesu.com/Files/4CB893D7-1018-01AF-FA97E9E9AD48B50C/FTX-1_OM_ENG_EH084M201_2506E-DS.pdf
  - RT Systems FTX-1 Programmer file layout (radio-data/ftx1/templates/README.md)

## Icom ID-52A (`id-52a`)

- Receive: 108-174, 225-479 MHz
- Transmit (hardware; licence decides use): 144-148, 430-450 MHz
- Modes: AM, DV, FM, NFM, WFM
- AM only on: 108-174, 225-374.995 MHz
- Memory: 1,000 channels; 100 groups/zones of up to 100; names up to 16 characters
- Notes: Dual-band D-STAR handheld with a wide receiver (air band, marine, public safety, military UHF air) but no HF and no broadcast bands. Transmits 2 m and 70 cm only; every other band is receive only. No DMR, NXDN, P25, Fusion or trunk tracking. Memories live in named groups of up to 100; D-STAR repeaters have their own 2,500-entry DR list. PRELIMINARY: built from Icom's published specifications and real ID-52 CSV files, not yet confirmed against CS-52 or the radio.
- Verified: no, checked 2026-09-19
- Sources:
  - Icom ID-52A specifications, https://www.gpscentral.ca/wp-content/uploads/Icom_ID-52A_Specifications.pdf (receive A band 108-174 and 225-479 MHz, B band 137-174 and 375-479 MHz; transmit 144-148 and 430-450 MHz; broadcast receiver separate)
  - Icom ID-52A product page, https://www.icomjapan.com/lineup/products/ID-52A/
  - CS-52 1.23 help (Program Scan Edge, Group Link, CSV import) and a CS-52 import on 2026-09-14 that refused AM above 375 MHz

## Uniden SDS150 (`sds150`)

- Receive: 25-512, 758-824, 849-869, 894-960, 1240-1300 MHz
- Transmit (hardware; licence decides use): none (receive only)
- Modes: ALL, AM, AUTO, DMR, FM, FMB, NFM, NXDN, P25, WFM
- Memory: no fixed channel ceiling; names up to any characters
- Notes: Receive-only scanner. P25 Phase I/II native; DMR and NXDN require a paid upgrade keyed to the scanner serial. Organizes channels into Favorites Lists, systems, sites and departments. No D-STAR, Fusion or other amateur digital voice: those channels are left off it.
- Verified: yes, checked 2026-09-19
- Sources:
  - Uniden SDS150 product page, https://uniden.com/products/sds150 (coverage 25-512, 758-824, 849-869, 894-960, 1240-1300 MHz; P25 Phase I/II; DMR, NXDN and ProVoice as paid upgrades)
  - docs/washington-sds150-favorites-master.md section 1.2

## TIDRADIO TD-H9 (`td-h9`)

- Receive: 76-108, 108-136, 136-174, 220-260, 350-390, 400-520 MHz
- Transmit (hardware; licence decides use): 136-174, 220-260, 350-390, 400-520 MHz
- Modes: AM, FM, NFM
- AM only on: 108-136 MHz
- Memory: 199 channels; no groups (memory order is the scan); names up to 8 characters
- Notes: Analog only: no P25, DMR, NXDN, D-STAR or Fusion decode. No 700/800 MHz coverage, so trunked public-safety systems are out of reach. No banks or zones, so memory order is the only organization and scanning walks the list. GNSS, APRS and SMS settings cannot be written by any current tool including the factory CPS.
- Verified: yes, checked 2026-09-19
- Sources:
  - TIDRADIO TD-H9 product page, https://tidradio.com/products/td-h9-10w-bluetooth-aprs-radio-handheld (transmit 136-174, 220-260, 350-390, 400-520 MHz; receive FM 87-108, AM 108-136, 136-174, 220-260, 350-390, 400-520 MHz; 199 memories)
  - TD-H9 user manual
  - CHIRP test driver, https://chirpmyradio.com/issues/12216 (memory layout, 8-character names, no banks)
  - Hardware: written and read back through CHIRP on COM16, 2026-09-14

## Kenwood TH-D75A (`th-d75`)

- Receive: 0.1-524 MHz
- Transmit (hardware; licence decides use): 144-148, 222-225, 430-450 MHz
- Modes: AM, CW, DV, FM, LSB, NFM, USB, WFM
- Memory: 1,000 channels; 30 groups/zones of up to 1000; names up to 16 characters
- Notes: Tri-band 144/222/430 MHz FM/NFM/D-STAR transceiver with a 0.1-524 MHz Band B receiver supporting AM, SSB, CW and WFM. Holds 1,000 ordinary memories in 30 named groups plus a separate 1,500-entry D-STAR repeater list. No P25, DMR, NXDN, trunk tracking or Fusion voice decode. APRS identity is operator-specific and is preserved from the radio rather than synthesized.
- Verified: yes, checked 2026-09-19
- Sources:
  - Kenwood TH-D75A user manual B5A-4505-00 (radio-data/th-d75/reference/manuals/)
  - Kenwood TH-D75 user guide parts 1 and 2, operating tips 2024-05 (same folder)
  - MCP-D75 1.00, and a TH-D75A on firmware 1.03 read and written through it
