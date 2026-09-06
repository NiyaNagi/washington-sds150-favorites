# TH-D75A Operating Tips — what's actually worth trying

Extracted from `TH-D75AE_IDM Operating Tips May_2024.pdf` (Kenwood, 68 pp) and
filtered against how this project already uses the radio: a 545-channel Ames
Lake plan, backcountry/SAR listening, POTA, and antenna measurement work.
Menu numbers are from the document; verify against
[B5A-4505-00_01_EN.pdf](B5A-4505-00_01_EN.pdf) if a setting doesn't match.

---

## Tier 1 — do these today

### 1. Group Link Scan — you already have 22 named groups and probably aren't using them
The D75 has 30 memory groups. Press and hold **[MHz]** to start a Group Link
Scan, which scans *only* the groups linked in **Menu 203**. In Memory mode,
press and hold **[◄]/[►]** to recall a single group instead of All Groups.

This is the highest-value item in the document for you, because the export
already does the hard part: [thd75_target.py:256-279](../src/wasds150/export/thd75_target.py#L256-L279)
assigns one memory group per plan block and writes the block name as the group
name. So `thd75-ames-lake.d75` ships with groups already named `SAR and Interop`,
`Wildland Fire`, `Marine and USCG`, `Civil Aviation`, and so on.

Try: link only `SAR and Interop` + `Wildland Fire` in Menu 203 for a hike, or
`2m Repeaters` + `70cm Repeaters` + `D-STAR Local` for a drive. One menu change
turns 545 channels into a purposeful scan list. Note the plan has 22 blocks and
the radio allows 30 groups, so there's headroom.

### 2. Voice Alert — silent APRS that tells you when someone is in simplex range
§5.3.2. Voice Alert puts a CTCSS tone on your APRS beacon and mutes your speaker
unless an incoming signal carries the matching tone. Two effects at once: no more
packet-burst noise from the APRS band, *and* when you do hear another Voice Alert
station's beacon, that is proof you are in direct simplex range of them.

For backcountry and trailhead use this is the single most practical APRS feature
in the document — it turns the radio into a passive "is anyone workable nearby"
detector without you having to listen to data bursts all day. Pair it with
**Menu 910** (A/B volume balance) so the APRS band sits quieter than the voice band.

### 3. GPS Receiver mode for long hikes
**Menu 403** → "GPS Receiver". Turns the transceiver section off entirely and
runs as a GPS logger, writing NMEA track logs to the microSD card. Current draw
drops to **125 mA** vs. 310 mA dual-band / 260 mA single-band at rated power. The
FM broadcast receiver still works in this mode (Menu 700).

Good for a day where you want the track log for the POTA/park work but don't need
to transmit. Registering waypoints still works.

### 4. Position Memory — 100 waypoints, and a compass that points at them
Press and hold **[MARK]** with a GPS fix to store the current position (lat, lon,
altitude, time, name, icon). 100 entries. You can also copy an entry *out of the
APRS station list* into Position Memory — callsign becomes the position name.

The payoff is the **Target Point** display: distance and bearing to a chosen
waypoint on the compass screen, with [F] toggling North Up / Heading Up. Mark the
car at the trailhead, mark camp, mark a water source. Copy a Position Memory into
**My Position 1-5** or into an **APRS Object** to broadcast a location to others —
that Object path is the one to use if you're ever marking something for a group.

### 5. The battery-life stack
§5.2, all of it, roughly in order of payoff. Rated life single-band, save on,
GPS off is **6 h (H) / 8 h (M) / 12 h (L) / 15 h (EL)** on the KNB-75LA; GPS on
costs about 10%. Alkaline KBP-9 gets 3.5 h at low power only.

| Setting | Menu | Note |
| --- | --- | --- |
| Single Band mode | `[F]`, `[A/B]` (DUAL) | 260 mA → 155 mA at SQ close |
| GPS off | 400 | Also stops the clock auto-setting |
| Bluetooth off | 930 | |
| Backlight to Auto, shorter timer, lower brightness | 900 / 901 / 902 | |
| Interrupt-screen backlight `LCD+Key` → `LCD` or `Off` | 907 | Matters when APRS/D-STAR pop-ups are frequent |
| Battery Saver off-interval longer | 920 | **Disabled entirely in APRS and KISS mode**; fixed at 200 ms in DV/DR |
| Busy (green) LED off for RX | 181 | Leave "FM Radio" LED disabled |
| Auto Power Off | 921 | 30 min default |

### 6. USB charging has a trap
§5.1. **The radio must be powered OFF to charge properly over USB** — if it's on,
the pack doesn't get enough current. No USB-PD; always 5 V. 1.5 A → ~5.5 h,
0.5 A → ~13 h, vs. 3.5 h on the supplied charger. Use a 5 V / 2 A+ adapter, cable
under 3 m, and keep the battery installed (USB alone will not run the radio).

**Menu 923** disables charging at power-on — the right setting when the radio is
tethered to a laptop for MCP or measurement work and you don't want it drawing
from the laptop battery.

---

## Tier 2 — set up once, benefit repeatedly

### 7. Load the repeater list from the microSD card — no MCP needed
§4.7.2, and a cleaner path than the MCP route for the `KWD_*.tsv` in this folder:

1. **Menu 980** → Mass Storage, connect USB-C.
2. Copy `KWD_yyyymmdd_E.tsv` to `[KENWOOD]-[TH-D75]-[SETTINGS]-[RPT_LIST]`.
3. Disconnect, **Menu 812** (Import — Repeater List Only), pick the file.
4. Choose **"Data for TH-D75A"** (not E — that filters to Europe).
5. Radio restarts with the list updated.

### 8. Config export/import over microSD — the same `.d75` format MCP uses
§5.14.3. **Menu 800** exports the full configuration to the card; **Menu 810**
imports it. The doc states plainly that the format is identical to MCP-D75's.

That means a `.d75` this repo generates can be loaded onto the radio from the SD
card without launching MCP at all — copy, Menu 810, done. Worth testing once
against a known-good file, because it removes the Windows/MCP step from the loop.
Kenwood also recommends exporting to the card before any firmware update.

### 9. Program Scan Memory — port the band-scanning ranges you already wrote
§5.11.3. 50 scan ranges (100 channels) as lower/upper pairs: put 145.500 in `L49`
and 145.900 in `U49` and you have Program Scan 49. In VFO mode the display shows
which program scan range the current frequency falls inside.

[docs/band-scanning.md](../docs/band-scanning.md) already defines Custom Search
ranges for the SDS150. The same edges drop straight into L00/U00 … L49/U49 here,
which would give the D75 the same twelve listening packs the scanner has. This is
the most obvious unexploited overlap between the repo and this radio.

### 10. QSY — put your voice frequency inside your APRS beacon
§2.3.3-2.3.5. The APRS band can't carry voice, so the QSY function embeds your
*voice* frequency (with tone/shift/offset for a repeater) in the beacon. Receiving
stations see an **"F"** and can hit **Tune** to jump their non-APRS band straight
to you. It works for D-STAR too: in DR mode the beacon carries the repeater
callsign, and Tune sets the receiver's Gateway CQ destination automatically; in DV
simplex it just carries the frequency.

**Menu 523** restricts Tune to stations within a set distance, so you don't get
offered a QSY to someone 400 miles away whose voice frequency you'll never hear.

### 11. Digipeat with the TEMP alias — the mobile-station-appropriate setup
§2.4.3. Kenwood's actual recommendation: mobile stations should enable **UItrace
with alias `TEMP`** rather than `WIDE`, so you act as a `TEMPn-N` digipeater and
document the packet path without interfering with normal WIDEn-N traffic.

Full fill-in config (§2.5.1), which is what you'd want from a ridge or a dead spot:

| Menu | Setting | Value |
| --- | --- | --- |
| 580 | Digipeat (MyCall) | On |
| 582 | UIdigipeat | On |
| 583 | UIdigi Aliases | WIDE1-1 |
| 584 | UIflood | On |
| 585 | UIflood Alias | `WA` (state abbreviation) |
| 586 | UIflood Substitution | ID |
| 587 | UItrace | On |
| 588 | UItrace Alias | TEMP |

The document is explicit that routinely running UIdigipeat/UIflood from a mobile
causes congestion — the intended use is emergencies, or when you're strategically
placed (a summit, a weak-signal pocket) and can usefully be the first hop. Given
the SAR and backcountry angle of this project, that's exactly the case worth
having pre-configured and switched off until needed. Note §2.5.2 mentions `SAR`
as a UIflood alias convention for permanent search-and-rescue digipeaters.

Also relevant: keep **Total Hops at 2** (the default WIDE1-1, WIDE2-1); the radio
warns you if you try to exceed it. For a statewide drill, the Region setting
(`WA5-5` style) is the correct tool rather than WIDE5-5.

### 12. Hotspot List — 30 entries, and it survives a full reset
§4.6. **Menu 230**. A memory list dedicated to hotspots, separate from the 1500-entry
Repeater List, and — usefully — *not cleared by a full reset*. Set Callsign (RPT1)
and Gateway (RPT2) either to `<CALL> B` / `<CALL> G` or both to `DIRECT`, per your
hotspot's own guidance. Entries can be reordered with Move.

Because the D75 receives D-STAR on both bands simultaneously, you can run a
hotspot on Band B while Band A is in Reflector Terminal Mode.

### 13. Reflector Terminal Mode — reflectors with no hotspot hardware
§4.5. The headline feature. The RF section on Band A shuts off and voice goes over
USB or Bluetooth to a phone or PC acting as the network side.

- **Android**: Menu 985 → Bluetooth, Menu 930 → On, Menu 936 (Auto Connect) → Off,
  Menu 650 → "Reflector TERM Mode", Menu 651 → your callsign. Pair via Menu 934.
  App: BlueDV Connect (Google Play), device name `TH-D75`.
- **Windows**: Menu 650/651 as above, install the
  [TH-D74/75 virtual COM driver](https://www.kenwood.com/i/products/info/amateur/thd74_vcp_e.html),
  BlueDV for Windows from pa7lim.nl, set Your Call and COM port, **check "Enable DTR"**.

Gotchas the doc calls out: Band A only, never in Single Band B mode; Menu 651 is a
*separate* callsign field from Menu 610 (DV/DR mode) and setting 610 alone won't
work; USB is much faster than Bluetooth SPP for data.

---

## Tier 3 — worth knowing, situational

**RX / TX equalizer** (§5.7-5.8). RX is 5 bands (0.4/0.8/1.6/3.2/6.4 kHz) at
±9 dB, Menu 913, enabled via 911. TX is 4 bands at -9/+3 dB, Menu 912, and you
choose whether it applies to FM, D-STAR, or both. For wind noise and speech
intelligibility on a summit: cut 0.4 kHz, lift 1.6 kHz.

**Voice guidance, upgraded to 770+ phrases** (§5.6). Menu 916 set to `Auto 1`/`Auto 2`
reads out received APRS beacons — callsign, position, weather data — not just
messages. Menu 918 speeds it up to 1.45×; Menu 919 chooses how callsigns are
spoken (`Phonetics (Suffix)` is the readable compromise). Genuinely useful with
the radio clipped to a pack strap where you can't see the screen.

**IF output to a PC band scope** (§5.10.5). **Menu 102** → `IF` outputs a 12 kHz-centred,
15 kHz-wide IF over USB while you keep listening on the speaker; the doc shows
HDSDR. Requires Single Band mode on Band B. Setting it to `Detect` gives
post-detection audio instead. Neither applies the RX equalizer. This is a real
spectrum view out of the HT — potentially useful alongside the antenna measurement
work in [antenna-results/](../antenna-results/).

**Screen capture to microSD** (§5.4). Assign Screen Capture to a PF key on the
optional SMC-34 speaker mic (Menu 942/943/944); saves 240×180 24-bit BMPs to
`[KENWOOD]-[TH-D75]-[CAPTURE]`. Handy for documenting a radio state in repo docs.

**FM broadcast alongside APRS/D-STAR** (§5.10.7). Menu 700 turns on FM Radio mode,
which keeps running while APRS and D-STAR operate; it auto-mutes when a signal
arrives on A or B and returns after a delay set in **Menu 701** — raise that delay
in areas with marginal FM reception to stop it flapping. 10 named FM memories,
[A/B] = Seek, direct frequency entry is FM-dedicated in this mode.

**Direct Reply** (§4.3.4.2). After an incoming D-STAR Gateway or Individual call,
the radio pre-loads the caller's callsign into TO — just press PTT to answer. The
Direct Reply icon on the interrupt screen tells you it's armed.

**Kerchunk confirmation** (§4.3.1.3). Hold PTT ~1 second; a response icon within
3 seconds means you reached the repeater. Menu 644 set to `Kerchunk` or `All` makes
the radio *announce* "Operational" — a real convenience test when the screen isn't
visible.

**Repeater-list voice announcements** (§4.7.3). The `Aux 1` and `Aux 2` columns in
`KWD_*.tsv` drive voice guidance: Aux 1 is the ISO 3166-1 alpha-3 country code
("USA"), Aux 2 the call area ("W7"). If you ever generate a repeater TSV from the
catalog, populate those columns or the announcements go silent. The D74 ignores them.

**Beacon a fixed position while still logging your track** (§2.3.6). Menu 401 lets
beacon position come from `My Position 1-5` instead of GPS, so you can record a GPS
track without broadcasting where you actually are.

**Fine mode gotcha** (§5.10.6). On HF, FINE mode is on by default and blocks
switching to FM. Press `[F]`, `[MHz]` (Fine) to turn it off first.

**KISS mode disables your APRS settings** (§2.8.1). In KISS, every APRS menu is
inactive except **505** (Data Speed) and **506** (Data Band). KISS TNC does 1200 bps
AFSK / 9600 bps GMSK, 3 kB TX / 4 kB RX buffers. The standalone digipeater function
(absent on the D74) is back on this model.

**Bluetooth limits** (§5.12). Bluetooth 3.0 Class 2, HSP and SPP only — **no BLE**,
no HFP, and you cannot PTT from a Bluetooth headset (VOX only). A BT headset takes
over the audio path entirely: no USB or speaker-mic output while connected.

**Wideband receive** (§5.9). Band B covers 0.1-523.995 MHz; Band A on the D75**A**
also receives 216-260 MHz, which is why the 1.25 m blocks in the Ames Lake plan
work. TX is 144-148, 222-225, 430-450.
