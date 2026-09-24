# RFI hunt: finding the devices behind the 2026-09-23 findings

The [survey](2026-09-23-survey/README.md) characterised six interference sources. This procedure pins each one to
a device: the tinySA watches every fingerprint live while you switch things off one at a time.

Budget about 20 minutes per session. Session A (HF) and session B (desk VHF) can run on different days.
Do session A **after dark** with the usual lights on, because that's when the survey saw the HF hash.

## Before you start

- tinySA on USB, **COM17**. COM3 is an unrelated device; never point a tool at it.
- Everything runs from the repository root with the CHIRP venv, which has pyserial:
  `.venv-chirp\Scripts\python.exe rf-environment\tools\hunt.py --setup <hf|desk|both>`
- **Never transmit into the tinySA.** Disconnect the feedline from the radio first. Touch the PL-259 centre pin
  to its shell to bleed static before connecting it to the tinySA.
- Note which breaker feeds the PC. The PC runs the monitor, so that circuit can't be switched off during a hunt;
  step 6 covers it.
- Each run logs every cycle to `.wasds150-home/rf-environment/hunt-<setup>-<time>.csv` (gitignored).

## How to read the monitor

It takes 3 cycles with everything **on** as the reference, then prints one line per cycle (about every
4 seconds for `hf`, 6–8 for `desk`):

```
22:04:11 hf_hash_5M  -73.0 ( -0.2) | hf_hash_10M  -76.9 ( +0.2) | hf_hump_17M  -83.8 ( +0.0) | hf_ref_13M  -94.4 ( +0.0)
```

- The number in brackets is the change from the reference. Readings repeat within ±1 dB, so treat anything
  under 3 dB as no change.
- **`DOWN`** marks a drop of 6 dB or more. Whatever you just switched off is at least part of that source.
  `hash_120M` and `hash_132M` read the strongest point in their window, so an aircraft transmitting on 119.9 or
  132.4 can briefly push them `up`. Ignore a one-cycle spike.
- A fingerprint that falls to about its **clean level** (table below) means you found the whole source. A
  partial drop means there are two or more.
- Type what you changed and press Enter, for example `office LED lamp off`. It goes into the CSV beside the
  readings.
- Switch one thing off, wait **2 cycles**, type the note, switch it back on unless it was the culprit, then
  move on.
- `hf_ref_13M` is a control. If it moves too, the change is broadband or the antenna was disturbed.

"Monitor, 2026-09-23" is what the monitor read on the survey evening. "Clean" is what it read with no pickup of
that source: the desk fingerprints measured on the EFHW, and the HIGH-input clocks with the HIGH port empty. The
survey sweeps used other resolution bandwidths, so compare against this table, not against the report's figures.

| Fingerprint | Setup | Monitor, 2026-09-23 | Clean | Survey finding |
|---|---|---|---|---|
| `hf_hash_5M` | hf, both | −73 dBm | not measured yet; expect about −85 dBm | #5: 32.7 kHz switcher, 120 Hz bursts |
| `hf_hash_10M` | hf, both | −77 dBm | not measured yet; expect about −88 dBm | #5, second hump |
| `hf_hump_17M` | hf, both | −84 dBm | not measured yet; expect about −95 dBm | #6: steady 16–17 MHz emitter |
| `hf_ref_13M` | hf, both | −94 dBm | (control) | — |
| `birdie_147` | desk | ≈ −80 dBm (desk whip) | −111 dBm | #1: 12.288 MHz × 12 |
| `birdie_159` | desk | ≈ −80 dBm (desk whip) | −111 dBm | #1: 12.288 MHz × 13 |
| `comb_6m` | desk | lines ≈ −88 dBm | −107 dBm | #2: 68.69 kHz switcher |
| `floor_2m` | desk | ≈ −94 dBm | −113 dBm | #4: desk hash |
| `floor_lowvhf` | desk | ≈ −84 dBm | −105 dBm | #4 |
| `hash_120M` | desk | ≈ −73 dBm | −89 dBm (a remnant reaches the EFHW too) | #3: 12 MHz cluster on Sea-Tac tower/approach |
| `hash_132M` | desk | ≈ −76 dBm | −108 dBm | #3: 12 MHz cluster on 132 MHz airband |
| `clk_240M`, `clk_250M`, `clk_258M`, `floor_290M` | both (whip on HIGH) | −66 / −78 / −79 / −95 dBm | −112 / −113 / −115 / −116 dBm | #1, #3, #4 |

The HF "expect" values are the floor either side of each hump in the survey. Desk readings marked ≈ come from the
survey sweeps, not from the monitor itself; your first `--setup desk` baseline replaces them.

## Session A: HF sources (#5 and #6)

**Setup:** EFHW feedline on the tinySA **LOW** port, HIGH port empty.

```
.venv-chirp\Scripts\python.exe rf-environment\tools\hunt.py --setup hf
```

Work through this order, cheapest and most likely first:

1. **Lighting in the office, then the rest of the house.** LED bulbs and lamps, anything on a dimmer, under-cabinet
   and aquarium lights, fluorescent or CFL fittings, outdoor floodlights. Watch `hf_hash_5M`/`hf_hash_10M`.
2. **Wall warts and bricks.** Phone, laptop, tool and radio chargers; the scanner's and radios' supplies; USB
   power strips. Pull the plug; switching off the load isn't enough.
3. **Network gear** (the likely home of #6, `hf_hump_17M`): powerline-Ethernet adapters first, then the modem or
   ONT, router, switches, mesh nodes, and any Ethernet run near the feedline.
4. **Entertainment:** TV, soundbar, game consoles, set-top box.
5. **Motors and HVAC:** furnace or heat-pump blower (variable-speed drives run 16–40 kHz), fridge, pumps, a
   treadmill.
6. **Breakers, one at a time**, skipping the PC's circuit. Give the fridge and freezer circuits a minute at most.
   If a breaker drops a fingerprint, go room by room on that circuit.
7. **If the PC's own circuit is the only one left:** use the **TH-D75 as a portable sniffer**. It receives
   HF AM/SSB. Tune 5.150 MHz AM (for #5) or 16.700 MHz AM (for #6) with the rubber duck, turn the squelch off,
   and walk: the buzz gets louder near the source. #5 sounds like a harsh 120 Hz buzz; #6 is a smooth hiss.
8. **If nothing in the house moves it:** switch off the main breaker for 30 seconds. The tinySA and EFHW keep
   running while the PC stays up on a UPS or laptop battery; otherwise use the TH-D75 as in step 7. If the noise
   stays with the house dark, it comes from outside (a neighbour, a streetlight, utility hardware). Walk the street
   with the TH-D75 before contacting the utility.

## Session B: desk VHF sources (#1–#4)

**Setup:** Smiley half-wave at **69 cm** on the tinySA **LOW** port, standing on the desk where the survey had it.
HIGH port empty.

```
.venv-chirp\Scripts\python.exe rf-environment\tools\hunt.py --setup desk
```

1. **Audio clock (#1, `birdie_147`/`birdie_159`).** Unplug one at a time: USB audio interface or DAC, USB headset
   or dongle, webcam, USB or HDMI-fed speakers and soundbar, the monitor's own speakers (switch the monitor off),
   any radio sound-card interface. If none of them does it, the PC's onboard audio is left: disable the audio
   device in Device Manager and watch.
2. **Switch-mode comb (#2, `comb_6m`).** Unplug bricks near the desk one at a time: the laptop supply, monitor
   power bricks, desk lamp, phone and radio chargers, USB hubs with their own supply.
3. **12 MHz clusters (#3, `hash_120M`, `hash_132M`).** Unplug USB devices one at a time: keyboard and mouse
   receivers, hubs, programming cables, SDR dongles, printers.
   - **Self-test:** clip a ferrite on the tinySA's own USB cable at both ends and route it away from the whip.
     If `hash_120M` drops, part of finding #3 was the measurement itself.
4. **Desk hash (#4, `floor_2m`, `floor_lowvhf`).** Switch the monitors off, then any second PC, laptop or NAS.
   Whatever is left after steps 1–4 is the desktop PC itself; see "Fixes" below.

To watch the 240–300 MHz clocks at the same time as HF, put the EFHW on LOW and the whip on HIGH and run
`--setup both`.

## After the hunt

- Keep the CSVs. The next survey should confirm each fix:
  `.venv-chirp\Scripts\python.exe rf-environment\tools\survey.py p2` (desk whip) and `... survey.py p3` (EFHW),
  then compare with the 2026-09-23 data.
- Record what you found in a new dated folder beside `2026-09-23-survey/`.

## Fixes, once a source is known

| Source type | Usual fix |
|---|---|
| Wall wart / brick (#2, #5) | Replace it with a quieter one (look for a PFC/"Level VI" supply or a linear supply for radio gear); fit a clip-on mix-31 ferrite on the DC lead near the device, several turns |
| LED/CFL lamp or dimmer (#5) | Replace the bulb or driver with a different brand; retire trailing-edge dimmers; a filtered power strip for lamps |
| Powerline adapters / network (#6) | Remove powerline adapters (use Ethernet or Wi-Fi); ferrites on Ethernet runs; keep Ethernet away from the EFHW feed |
| Audio clock / USB (#1, #3) | Ferrites on USB and audio cables at both ends; shielded cables; move the device; use a different audio interface |
| PC hash (#4) | Keep handhelds and the scanner away from the desk, or feed them from an outdoor antenna. The EFHW run showed the outdoor path is clean at VHF. Ferrites on monitor, USB and Ethernet cables |
