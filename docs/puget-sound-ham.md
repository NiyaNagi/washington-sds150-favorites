# Puget Sound amateur repeater and net monitoring

`PSHAM01 — Puget Sound Ham Repeaters & Nets` combines two layers:

1. A small checked-in set of frequencies and schedules published directly by
   repeater operators.
2. The current WWARA coordination extract, fetched locally and filtered to the
   broad Puget Sound/eastern Olympic/western Cascades region.

The repository does not republish WWARA's full compiled database. WWARA states
that its extract is designed for radio-programming software but reserves rights
against wholesale redistribution. Run the source update workflow to build the
complete personal monitoring list from the current nightly extract.

## Current research result

Research date: **2026-08-06**. WWARA extract date: **2026-08-06**.

- 433 current Washington coordination records were reviewed.
- 359 scanner-range records fall within the Puget bounding box
  (46.75–49.05 N, 123.55–121.25 W).
- They produce 43 region/mode departments plus 10 operator-published net
  channels.
- Analog FM/NFM and P25 are natively monitorable.
- DMR channels require the paid DMR upgrade.
- D-Star and Yaesu Fusion-only carriers are retained in avoided departments;
  the SDS150 cannot decode their voice.
- WWARA coordinates may be deliberately fuzzed, so broad location groups—not
  exact repeater-site claims—control scanning.

The list groups repeaters by five listening regions and by mode/band:

- Seattle Metro
- Eastside & Cascades
- South Sound
- Olympic & Kitsap
- North Sound & Islands

Departments distinguish analog 6 m, 2 m, 1.25 m, 70 cm, 33 cm and 23 cm,
linked analog, P25, DMR, and unsupported digital carriers. Channel notes retain
input frequency, offset, sponsor, link data, source URL and operator comments.

## Operator-published net channels

Times below are Pacific local time and should be rechecked before relying on a
schedule.

| Channel | Repeater/net | Published schedule/details | Source |
|---|---|---|---|
| 146.960, PL 103.5 | WW7PSR Seattle 2 m | Daily Boaters 07:47; social 09:00, 12:00, 21:00; Mon Seattle ACS 19:00; PSRG 19:30 | PSRG |
| 52.870, PL 103.5 | WW7PSR Seattle 6 m | Linked to 2 m for Monday ACS/PSRG nets; AllStar 2464 | PSRG |
| 440.775, DMR CC2 | WW7PSR DMR | Dedicated narrowband DMR repeater | PSRG |
| 146.560 simplex | PSRG Simplex Voice Net | Saturday 20:00 | PSRG |
| 146.820, PL 103.5 | K7LED Mike & Key 2 m | Social 19:30 nightly except Wed; Wed emergency 19:00 and technical 19:30; Thu check-in 18:30 | Mike & Key |
| 224.120, PL 103.5 | K7LED Mike & Key 1.25 m | Sunday informal net 19:00 | Mike & Key |
| 146.720, PL 103.5 | Mason County ARC | Sunday ragchew 19:00 | MCARC |
| 146.8625, PL 114.8 | W7AVM Oak Harbor | North Whidbey repeater, operator reports normal operation | ICARC |
| 147.220, PL 127.3 | W7AVM Clinton | South Whidbey repeater, RF linked to Oak Harbor | ICARC |
| 441.425, PL 110.9 | N7KN Greenbank | Operational; linking temporarily disabled on operator page | ICARC |

Other official/club pages reviewed include Seattle ACS, SnoVARC, Radio Club of
Tacoma, Kitsap County ARC, Whatcom ACS, Skagit amateur groups, Pacific Northwest
VHF Society and the broad Mike & Key Puget net directory. SSB/CW/FT8/HF nets
were documented but not programmed because the SDS150 does not demodulate those
modes.

## Build/update workflow

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources fetch wwara
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources update --only wwara --apply
.\.venv\Scripts\wasds150.exe --home .wasds150-home generate --out wasds150-output
```

Without a WWARA update, PSHAM01 still generates the ten operator-published net
channels. After the update, it becomes the full current coordinated monitoring
list. Because 359 coordinated records create a long scan cycle, enable location
control and only the region/mode departments relevant to the current trip.

## Source hierarchy and limitations

1. WWARA coordination database — primary frequency/input/mode/location source.
2. Repeater operator or club pages — primary net schedules and live status.
3. RepeaterBook/RadioReference — cross-checks only; community status can lag.
4. Search snippets, social posts and third-party net directories — leads only,
   not committed unless confirmed by an operator/coordinator source.

Coordination does not guarantee that a repeater is currently on-air. Coverage
depends on terrain, antennas and propagation. Receive tone is optional; an
incorrect output tone can hide traffic, so WWARA output-tone data is used only
when published. Net schedules change more often than coordinated frequencies.

## Sources reviewed

- WWARA nightly coordination database: https://www.wwara.org/coordinations/
- WWARA programming extract: https://www.wwara.org/DataBaseExtract.zip
- PSRG repeater details: https://web.psrg.org/repeater-system/
- PSRG net schedule: https://web.psrg.org/net_schedule/
- Seattle ACS weekly nets: https://www.seattleacs.org/join/weekly-nets
- Mike & Key repeaters/nets: https://mikeandkey.org/repeaters.php and https://mikeandkey.org/nets.php
- Mason County ARC nets: https://mc-arc.org/nets/
- Island County ARC repeater status: https://www.w7avm.org/repeater-system
- SnoVARC nets: https://snovarc.org/events/nets/
- Radio Club of Tacoma repeaters/nets: https://w7dk.org/nets-repeaters/club-area-repeaters and https://w7dk.org/nets-repeaters/club-nets
- Kitsap County ARC nets: https://kcarc.org/nets/
- Whatcom ACS: https://www.whatcomcounty.us/4319/Auxiliary-Communications-Service-Whatcom
- Skagit Amateur Radio Emergency Communications Club: https://sarecc.org/
- Pacific Northwest VHF Society nets: https://www.pnwvhfs.org/nets.html
- RepeaterBook Washington cross-check: https://www.repeaterbook.com/repeaters/Display_SS.php?state_id=53
- RadioReference Washington amateur cross-check: https://www.radioreference.com/db/browse/stid/53/ham
