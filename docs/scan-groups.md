# The same groupings on every radio

Every fleet plan carries the same two things: **blocks**, one per service, and
**scan groups** - the operator's own combinations built from those blocks.
`Near Me` is the first of them: the operator's pinned repeaters, then the
nearest reachable few of every local amateur service, in one list, so there
is one thing to leave running.

Every list reads in **frequency order**: each block's memories, each zone and
memory group, each scan list. Which stations a block or a list holds is still
decided nearest first; frequency order is only where each one sits
(`ChannelPlan.frequency_order`, `ScanGroup.frequency_order`).

## How Near Me is filled

`Near Me` takes a quota from each amateur block (`NEAR_ME_QUOTAS` in
`src/wasds150/plans/template.py`):

| Block | Quota |
|---|---:|
| Nets | 24 |
| Ham 6m Repeaters | 4 |
| Ham 2m Repeaters | 14 |
| Ham 1.25m Repeaters | 4 |
| Ham 70cm Repeaters | 14 |
| D-STAR Repeaters | 10 |
| DMR Core | 20 |
| DMR Local | 10 |
| Simplex Calling | 6 |
| Seattle ACS | 8 |

Within each block the quota takes (`wasds150.plan.scanning.quota_rank`):

1. **Pinned repeaters** first, whatever their distance: `NEAR_ME_PINNED` -
   KC7BAE East Tiger on 443.050 and WW7PSR (PSRG) on 146.960.
2. **Stations within reach** - 35 miles of home (`NEAR_ME_REACH_MILES`) -
   nearest first. Distance is the repeater's own site: a list that only
   fences its rows at one point (the operator-published nets all sit on
   Seattle) takes each machine's site from WWARA's coordination records
   (`locate_channels`). A DMR block takes calling and local talkgroups (tier
   0-1) before wide-area ones; a machine whose coordinations have all lapsed
   comes after live ones.
3. **Stations with no site** - simplex and calling frequencies.
4. Never a station **known to be beyond reach**, unless it is pinned. A block
   with nothing reachable gives nothing, and a radio contributes nothing for a
   band or mode it does not have: the Anytone's list includes thirty DMR
   channels the others cannot hear, the D75 and ID-52A carry D-STAR instead,
   and only the D75 and FTX-1 have 6 m.

"Active" is judged from what is published, because no source records what
is on the air: a repeater that carries a scheduled net, and one whose WWARA
coordination is current. Scanning with the SDS150's activity log running, and
demoting channels that never transmit, is the open item that would measure it.

| Radio | Mechanism | `Near Me` |
|---|---|---|
| AT-D890UV | a zone and its identical scan list; PF1 sweeps the list the channel under the cursor names | **its own zone and scan list of up to 100**, as copies naming the `Near Me` list |
| TH-D75A | Memory Group Link: an ordered list of memory groups scanned as one pass | **its own memory group of copies**, and Group Link names that group alone |
| ID-52A | Group scan, one memory group at a time; a memory belongs to one group | **its own memory group of copies** |
| FTX-1 | `M-Grp`, one checkbox per memory: a single subset of the memories | **the chosen memories, flagged in place** - no copies, no slots |
| TD-H9 | no group or bank concept at all | none: the memory list is the scan |
| SDS150 | Favorites Lists with location control | **NM Ham**: every live amateur station within its fence of the car, not a quota (see [fleet-updates.md](fleet-updates.md#in-the-car-sds150)) |

## AT-D890UV

A scan list can name any channels, but that alone reaches nothing: measured on
the radio, PF1 sweeps the list named on the channel under the cursor and
answers "Scan List No Select" on a channel naming none. There is no zone scan
and no radio-wide choice of list. A composite list is therefore only
reachable through a zone whose channels name it - and a channel names one
list, its own zone's.

So the export keeps one rule: **a zone and its scan list are the same thing.**
Every scanned zone has one list of the same name holding exactly its
channels, and every one of those channels names it. `Near Me` is a zone like
the rest, first on the knob, holding copies (named with a trailing ` N`) so
the originals keep scanning their own zones. Only the first scan group is
built: `Ham All`, `Everything` and the rest are far over 100 and could only
ever be arbitrary slices no zone led to. Stations the fill pass added beyond
the radius leave their block for `Far Ham Analog`, `Far Ham DMR`, `Far Public
Svc` and `Far Other` - scannable zones of their own, each with its identical
list - so the local sweep stays quick; a channel the operator locked out by
label goes to a `Not Scanned` zone with no list.

See [at-d890uv-programming.md](at-d890uv-programming.md), including the
`.rdt` patch that restores full membership after the CPS's 50-member CSV
import.

## TH-D75A

A memory belongs to exactly one group, and **Memory Group Link** (30 bytes at
image offset `0x10A0`, group numbers terminated by `0xFF`) reaches whole
groups. Linking the groups `Near Me` draws from therefore swept every memory
in them - 275 channels, not the curated list.

So the TH-D75A now does what the ID-52A does: the export writes `Near Me` as
**its own memory group of copies**, the last group, and points Memory Group
Link at that one group. Group Link Scan sweeps exactly the list. The copies
cost memories, so `_TH_D75.reserve_slots` carries the operator's fifty free
slots **and** a hundred for the copy; the fill blocks give up their most
distant rows to pay for it.

The table is part of the export, not part of the radio's preserved settings:
`restore_unowned_regions` leaves it alone, or a later MCP-D75 save would put
back the radio's own links.

## ID-52A

Group scan reaches one group, and a memory is in one group, so `Near Me`
exists only as a second copy of its channels in a group of its own - the last
one CS-52 imports. The plan funds it by reserving memories:
`_ID52A.reserve_slots` carries the operator's fifty free slots **and** the
copy, and the widest-reaching blocks give up their most distant rows to pay
for it.

Only the first scan group is copied. A second would cost another group's worth
of memories on a radio that can only scan one of them at a time anyway.

## FTX-1

The FTX-1 has **no banks**. What it has is **`M-Grp`**: one checkbox per
memory, between `Skip` and `Tx DGID`, with `55: MEM Group` as the matching Set
Menu item on the radio. A single subset of the memories, which is exactly the
shape of `Near Me`. Being a flag on the memory itself, it costs neither a
duplicate nor a slot.

It is **bit 1 of byte `0x00`**, sharing that byte with the in-use bit, found
by probe: twelve identical memories on 146.520, six with the box ticked in the
programmer, saved beside an unedited re-save. Exactly those six went `0x01` to
`0x03`. `Ftx1Record.patched` sets each flag without disturbing the other.

Still open: what the radio does with `55: MEM Group` on - whether it scans
only the flagged memories or merely displays them apart.

## TD-H9

No composite list, and nothing to build one with: CHIRP writes memories and a
skip flag, and the radio scans all of them, in memory order - service blocks
in plan order, each in frequency order.
