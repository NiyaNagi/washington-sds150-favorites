# RF environment survey, 2026-09-23

A full sweep of the receive environment at the operator's office desk (Ames Lake / Redmond), looking for
interference that reaches the radios. It used a basic tinySA (hardware v0.3, firmware `tinySA_v1.4-175`) on COM17,
ran from 20:52 to 22:05 local time, and captured 34 data sets.

> **Bottom line.** Two separate problems.
>
> 1. **At the desk, VHF is buried in locally generated noise.** Between 50 and 300 MHz the floor is 18–29 dB
>    above the analyzer's own floor. That's 3 to 5 S-units of receive sensitivity a handheld or the scanner loses
>    at the desk. A 12.288 MHz digital-audio clock drops birdies on **147.450, 147.4625 and 442.375**, and a
>    68.69 kHz switch-mode supply lays a line every 68.69 kHz across all of 6 m. None of it reaches the outdoor
>    EFHW, so the sources are within a metre or two of the desk.
> 2. **On HF, the outdoor antenna is mostly quiet** (rural-grade noise on 160/80/40/20/15/12/10 m). Two in-house
>    sources flood the gaps between the main bands: a mains-synchronous ~32.7 kHz switcher (humps at 5 and
>    10.7 MHz) and a steady broadband emitter at 16–17 MHz. Together they lift **60, 30 and 17 m** to
>    residential-to-city noise.

## At a glance

| # | What | Where it lands | Level | Heard on | Likely source |
|---|---|---|---|---|---|
| 1 | Harmonics of a **12.288 MHz** clock | 147.456, 442.368, 159.744, 49.152 MHz and 11 more harmonics up to n = 36 | 147.456 at −81.5 dBm (steady); 442.368 at −106 dBm | desk whip | Digital-audio master clock (256 × 48 kHz): USB audio interface/DAC, headset dongle, monitor speakers, the PC's audio |
| 2 | **68.69 kHz** switch-mode comb | every 68.69 kHz across 50–54 MHz (≈57 lines) | −87 to −90 dBm per line (≈S9 VHF) | desk whip | A mains brick or LED driver near the desk (laptop/monitor supply, charger, lamp) |
| 3 | **12 MHz**-spaced clusters (plus a 25 MHz carrier) | 48, 60, 72, 84, 108, 120, 132, 144, 156, 168, 180, 192, 204, 240 MHz; 250.000 MHz | −70 to −80 dBm (240.1 MHz −66 dBm) | desk whip | USB full-speed traffic or clocks (12 Mbit/s), Ethernet/PC 25 MHz clock. The tinySA's own USB link is untested |
| 4 | Broadband desk hash | whole VHF range | floor +18 to +29 dB | desk whip only | The sum of #1–3 plus PC/monitor hash |
| 5 | **~32.7 kHz** switcher, **120 Hz bursts** | HF humps at 4.5–6.5 and 9.5–11 MHz | −73 dBm median at 5.15 MHz (30 kHz RBW) | outdoor EFHW | Mains-fed device with no power-factor correction: LED/CFL/fluorescent lighting, dimmer, older supply, motor drive |
| 6 | Steady broadband hump | 16.0–17.1 MHz | −84 dBm median (11 kHz RBW), 12 dB above the floor either side | outdoor EFHW | A continuous wired data link: powerline-Ethernet adapter, VDSL/modem, network switch, TV |

Everything above passed an **attenuator test**: displayed levels did not change with 10 or 20 dB of input
attenuation, so none of it is overload generated inside the tinySA. Each emission is also absent from an
**empty-port baseline** taken on the same input.

## Impact on each radio

Counts are programmed receive channels, taken from each radio's committed fleet report
(`radio-data/*/exports/*-fleet-report.md`), that fall on a measured problem zone. A birdie counts when it sits
within 7.5 kHz of the channel, inside the FM filter.

| Radio | Birdie channels | 6 m comb | Airband hash (119.9–120.4, 132.0–132.8) | 2 m / VHF-high floor +18–21 dB (at the desk) | HF bands with local noise |
|---|---|---|---|---|---|
| **FTX-1** | 147.450, 442.375 | 37 channels | 8 | 173 + 222 | 60 m (1), 30 m (4), 17 m (5) |
| **AT-D890UV** | 147.450, 147.4625, 442.375 | — | 15 | 208 + 498 | — |
| **TH-D75** | 147.450, 147.4625 | 17 channels (receive) | 7 | 181 + 208 | 60 m (1), 17 m (1) |
| **ID-52A** | 147.450, 147.4625 | — | 8 | 180 + 272 | — |
| **TD-H9** | — | — | 1 | 85 + 59 | — |
| **SDS150** | not cross-checked channel by channel; covers every affected VHF range | yes | yes | yes | — |

What that means in practice:

- **Handhelds and the scanner used at the desk** need a signal 3–5 S-units stronger on 2 m, VHF-high,
  airband and marine than the same radio would out in the room or outdoors. Weak repeaters and simplex that should
  be copyable at the desk won't be.
- **147.450 and 147.4625**, the latter the Eastside DMR repeater programmed in three radios, carry a steady
  −81.5 dBm carrier 6 kHz off channel. Analog squelch can hold open or false-trigger, and DMR decoding degrades
  when the repeater is weak.
- **442.375** (FTX-1, AT-D890UV) has a weaker birdie at −106 dBm, 7 kHz off. It only matters for weak signals.
- **6 m at the desk** has a comb line about every 69 kHz, at roughly S9. On the EFHW the comb is absent, so
  6 m through the outdoor antenna is unaffected.
- **FTX-1 on HF**, through the EFHW: 160/80/40/20/15/12/10 m sit near rural noise, which is good. **60, 30 and
  17 m** carry an extra ~3–7 dB of local noise, roughly one S-unit, and that's a lower bound because the 80 m
  EFHW is mismatched on those bands.

## Findings in detail

### VHF noise is local to the desk

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="charts/floor-excess-dark.svg">
  <img alt="Noise floor above the empty-port baseline from 0 to 350 MHz: the desk whip sits 5 to 29 dB above the analyzer floor across VHF; the outdoor EFHW sits at 0 to 2 dB except for ordinary HF noise below 30 MHz." src="charts/floor-excess-light.svg">
</picture>

The same broadband sweep was run with the Smiley half-wave on the desk and with the outdoor EFHW. The EFHW is
an HF antenna, but it still delivers FM broadcast at −55 to −62 dBm, only ~12 dB below the desk whip. If the
VHF hash were ambient, the EFHW would show it 10+ dB above its floor. It shows 0–2 dB. The emitters are in the near
field of the desk.

| Range | Desk whip, median | Empty port | Excess |
|---|---|---|---|
| 60–86 MHz (30 kHz RBW) | −81.8 dBm | −106 dBm | **+24 dB** (peaks +29) |
| 2 m, 144–148 MHz (10 kHz) | −92.0 dBm | −113 dBm | **+21 dB** |
| Airband, 118–137 MHz (30 kHz) | −88.0 dBm | −106 dBm | **+18 dB** |
| 150–174 MHz (30 kHz) | −88.3 dBm | −106 dBm | **+18 dB** |
| 240–340 MHz (HIGH input, 32 kHz) | −92 to −99 dBm | −116 dBm | **+17 to +24 dB** |
| 420–470 MHz (HIGH input, 11 kHz) | −116.9 dBm | −120.9 dBm | +4 dB (nearly clean) |

### One 12.288 MHz clock, heard from 49 MHz to 442 MHz

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="charts/clock-ladder-dark.svg">
  <img alt="Measured peak level of harmonics of 12.288 MHz by harmonic number: detected at n = 4, 9, 12, 13, 16 and 19 to 25 on the LOW input and 20 to 25, 32, 34 and 36 on the HIGH input, from about −79 to −103 dBm." src="charts/clock-ladder-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="charts/birdies-dark.svg">
  <img alt="Zoomed spectra: a steady carrier at 147.456 MHz sits between the programmed 147.450 and 147.4625 channels; a carrier at 442.368 MHz sits inside the 442.375 channel." src="charts/birdies-light.svg">
</picture>

Narrow carriers sit at exact multiples of 12.288 MHz, at least 6 dB above the local floor: n = 4, 9, 12, 13, 16
and 19–25 on the LOW input, and 20–25, 32, 34 and 36 on the HIGH input. n = 17 and 18 show intermittently just
under that line, and n = 8 falls inside FM broadcast. The headline carriers were present in every sweep and hold
their level with attenuation. Only n = 24 (294.9 MHz) is faintly visible on the outdoor EFHW, where coax pickup
indoors is the likely path. 12.288 MHz is 256 × 48 kHz, the standard master clock of digital audio.

| n | Frequency | Level | Lands on |
|---|---|---|---|
| 4 | 49.152 MHz | −86.7 dBm | just below 6 m |
| 12 | **147.456 MHz** | **−81.5 dBm** | **147.450 / 147.4625** (FTX-1, AT-D890UV, ID-52A, TH-D75) |
| 13 | 159.744 MHz | −81.8 dBm | VHF business |
| 18 | 221.184 MHz | −95 dBm (intermittent, band sweep) | below 1.25 m |
| 36 | **442.368 MHz** | **−106 dBm** | **442.375** (FTX-1, AT-D890UV) |

**Suspects:** anything at the desk with a digital-audio clock. That includes a USB audio interface or DAC, a
USB headset dongle, monitor or soundbar speakers fed over HDMI/DisplayPort, the PC's own audio codec, and any
radio audio interface. The fastest test is to unplug them one at a time with the hunt monitor watching
`birdie_147` (see [RFI-HUNT.md](../RFI-HUNT.md)).

### 6 m: a switch-mode supply at 68.69 kHz

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="charts/six-metre-comb-dark.svg">
  <img alt="Spectrum from 50 to 51 MHz: comb lines at −88 to −92 dBm align with orange ticks at multiples of 68.69 kHz; the empty-port floor sits at −112 dBm." src="charts/six-metre-comb-light.svg">
</picture>

A least-squares harmonic fit over 50–54 MHz gives **68.690, 68.691 and 68.689 kHz** in three sweeps and
68.783 kHz in the fourth. That's harmonics #728–786 of one switcher whose frequency shifts with its load, typical
of quasi-resonant chargers, laptop and monitor bricks, and LED drivers. The lines sit at −87 to −90 dBm
(11 kHz RBW) on a floor 14 dB above the analyzer's own. There is no trace of this comb on the EFHW at HF or 6 m,
so it is a near-field source at the desk.

### 12 MHz clusters and a 25 MHz clock

Clusters about 0.2–0.8 MHz wide sit at exact multiples of 12.000 MHz: 48, 60, 72, 84, 108, 120, 132, 144, 156,
168, 180, 192, 204 and 240 MHz. Among them:

- 120.0 MHz at −73 dBm across Sea-Tac tower and approach, 119.9–120.4
- 132.1–132.7 MHz at −76 dBm, covering Boeing Field's 132.4
- 144.375 MHz at −71 dBm, 650 kHz wide at the bottom of 2 m
- 240.1 MHz at −66 dBm

Their spread shape is typical of data-modulated or spread-spectrum clocks. 12 MHz is the USB full-speed bit
rate. A clean steady carrier at **250.000 MHz** (−78 dBm) is the 10th harmonic of a 25 MHz clock, the usual
Ethernet PHY/PC reference. **Open question:** the tinySA's own USB link runs at full speed, and its cable ran
beside the whip. Part of the 12 MHz family may be the measurement itself. The hunt procedure includes a
test for that.

### HF: two in-house sources between the bands

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="charts/hf-floor-dark.svg">
  <img alt="HF noise floor on the EFHW from 1.6 to 30 MHz with carriers removed: broad humps at about 5, 10.7 and 16.7 MHz rise 10 to 15 dB above the surrounding floor; the empty-port floor is flat at −112 dBm." src="charts/hf-floor-light.svg">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="charts/zero-span-dark.svg">
  <img alt="Zero-span time traces over 219 ms: at 5.15 MHz the level jumps by 10 to 20 dB about every 8.3 ms; at 16.7 MHz it stays flat within a few dB." src="charts/zero-span-light.svg">
</picture>

- **Mains-synchronous hash, humps at 4.5–6.5 and 9.5–11 MHz.** Zero-span captures at 5.15 MHz show
  bursts 10–20 dB high 120 times a second, with harmonics at 240/360/480 Hz. 25% of samples sit ≥ 6 dB above
  the median. The same 120 Hz signature appears at 10.75, 7.15 and 13.2 MHz, weaker with frequency. The fine
  structure inside both humps repeats every **~32.7 kHz** (fits of 32.75 and 32.68 kHz). That's a switcher at
  ~32.7 kHz whose output is gated by its own mains rectifier, i.e. a device with no power-factor correction.
  Typical sources are LED/CFL/fluorescent lighting, dimmers, older supplies and variable-speed motor drives. The
  survey ran after dark, so lighting was on.
- **Steady 16.0–17.1 MHz hump.** No 120 Hz content (0.2% bursts) and a sharp top edge at ~17.1 MHz. It's a
  continuous emitter. Wired data links (powerline-Ethernet adapters, VDSL, a modem or switch, a TV) are the
  usual cause.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="charts/hf-noise-itu-dark.svg">
  <img alt="External noise Fa per HF band against ITU-R P.372 city, residential, rural and quiet-rural curves: 160, 80, 40, 20, 15, 12 and 10 m sit near or below the rural curve; 60 and 30 m sit at residential and 17 m above residential." src="charts/hf-noise-itu-light.svg">
</picture>

| Band | Floor on EFHW | External Fa | vs ITU residential | Read as |
|---|---|---|---|---|
| 160 m | −82.0 dBm | 51.5 dB | −13.3 | between rural and quiet rural |
| 80 m | −88.0 dBm | 45.6 dB | −11.0 | between rural and quiet rural |
| **60 m** | −84.0 dBm | 49.6 dB | **−2.7** | **residential** |
| 40 m | −91.5 dBm | 42.1 dB | −6.7 | rural |
| **30 m** | −89.5 dBm | 44.1 dB | **−0.6** | **residential** |
| 20 m | −97.0 dBm | 36.6 dB | −4.0 | rural |
| **17 m** | −93.9 dBm | 39.7 dB | **+2.0** | **city** |
| 15 m | −103.8 dBm | 29.8 dB | −5.9 | rural |
| 12 m | −105.5 dBm | 28.1 dB | −5.7 | rural |
| 10 m | −104.8 dBm | 28.7 dB | −3.4 | rural |

Floors are the 20th percentile of the per-point minimum over four sweeps (11 kHz RBW), which removes carriers.
The analyzer's own noise is subtracted in linear power. No antenna or feedline loss correction is applied, so
every Fa is a lower bound, and a larger one on 60/30/17 m where the 80 m EFHW is mismatched.

## What is clean

- **No overload.** Every finding keeps its level with 10–20 dB of attenuation. The strongest inputs were AM
  broadcast at −37 dBm (710/770/1000 kHz) and FM at −41 dBm (97.3/98.9 MHz, West Tiger Mountain).
- **HF ham bands are free of birdies.** The only steady carriers inside them were 3.620 MHz and FT8 on
  7.074–7.075 MHz: real stations.
- **UHF is nearly clean at the desk.** 420–470 MHz sits only 4 dB above the analyzer floor, with no mains-periodic
  impulse noise in zero span at 284, 300, 420, 442, 446 or 454 MHz.
- **Licensed carriers, not interference:** 460.950 MHz (−92 dBm) and 454.506 MHz (−98 dBm), both continuous UHF
  business/data carriers; NOAA KHB60 162.550 MHz (−79 dBm); ATSC TV pilots; Sea-Tac/Boeing Field aircraft voice.
- **The tinySA itself** contributes only the documented spurs: 0 Hz leakage below 1 MHz, 30.000 MHz, and 30 MHz
  multiples (270, 300, 330 … 480 MHz) on the HIGH input. These are excluded from every finding above.

## Method

| Phase | LOW input (0.1–350 MHz) | HIGH input (240–960 MHz) |
|---|---|---|
| p1 | open: baseline | stock whip on the desk beside the PC |
| p2 | Smiley 2 m half-wave, 69 cm, on the desk | open: baseline |
| p3 | JYR8010 80 m EFHW feedline (office feed, radio disconnected) | open |

- **Sweeps:** 0–1 MHz, 0.1–30 MHz, 0.1–350 MHz and 240–500 MHz wide, plus band sweeps of 6 m, airband, 2 m,
  VHF-high, 1.25 m, 70 cm and UHF. Resolution was 11 kHz RBW (the tinySA's best-sensitivity setting, within
  2.5 dB of its 3 kHz floor at a tenth of the time), 32 kHz on wide sweeps, and 3 kHz across 1.8–30 MHz. Each
  sweep ran 2–5 times so continuous emitters could be told from intermittent ones. Spur removal was on in LOW
  mode.
- **Checks:**
  - empty-port baselines on both inputs
  - an attenuator test (0/10/20 dB) on every raised floor and headline carrier
  - zero-span time captures with an envelope DFT at 100 kHz and 30 kHz RBW
  - least-squares harmonic fits for switching and clock frequencies
  - autocorrelation of the fine structure
  - ITU-R P.372 man-made-noise comparison
- **Identification:** peaks were matched against the local catalog and each radio's programmed channels. The
  licensed catalog rows (RadioReference) were used locally only and are not reproduced here.

## Limitations

- **500 Hz – ~100 kHz could not be measured.** The basic tinySA is specified from 100 kHz. Below that its own
  local-oscillator leakage sets a floor of −65 dBm at 25–150 kHz, falling to −89 dBm at 1 MHz.
- **One evening snapshot** (20:52–22:05). Daytime-only sources such as solar inverters, workshop tools or a
  neighbour's equipment would not show, and night-time propagation raises natural noise on 160/80 m.
- **Levels are as displayed:** no antenna-factor correction. Desk levels depend on where the whip stood; the
  radios see more or less depending on where they are used.
- **The tinySA was USB-tethered to the PC** at the desk. Its own USB link may add to the 12 MHz family (finding 3).
- **Sources are characterised, not yet located.** Pinning each to a device takes the switch-off hunt in
  [RFI-HUNT.md](../RFI-HUNT.md).

## Data and reproduction

- `data/`: every sweep as JSON (levels rounded to 0.1 dB), zero-span records, zoom captures, the attenuator
  test, `survey.log`, and `manifest.json` describing each file's port, antenna, RBW and pass count.
- `charts/`: light and dark SVGs, regenerated with
  `.venv-nanovna\Scripts\python.exe rf-environment\tools\make_charts.py`.
- Tools and the procedure for a new survey: [../tools/README.md](../tools/README.md).
