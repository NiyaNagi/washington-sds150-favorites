# The same groupings on every radio

Every fleet plan carries the same two things: **blocks**, one per service, and
**scan groups** - the operator's own combinations built from those blocks.
`Near Me` is the first of them: the nearest few of every local amateur service
in one list, so there is one thing to leave running.

Blocks reach every radio as memory groups or zones, under the same names.
Scan groups are harder, because "a list of channels drawn from several groups"
is not something every radio has. Each target expresses them as far as its
hardware allows, and no further.

| Radio | Mechanism | `Near Me` |
|---|---|---|
| AT-D890UV | a zone and its identical scan list; PF1 sweeps the list the channel under the cursor names | **its own zone of the 100 curated channels**, as copies naming the `Near Me` list |
| TH-D75A | Memory Group Link: an ordered list of memory groups scanned as one pass | **the eight groups Near Me draws from, whole** - 275 channels rather than 84 |
| ID-52A | Group scan, one memory group at a time; a memory belongs to one group | **its own group of 76 copies**, the same channels in the same order |
| FTX-1 | `M-Grp`, one checkbox per memory: a single subset of the memories | **the 70 curated channels**, flagged in place - no copies, no slots |
| TD-H9 | no group or bank concept at all | none |

The totals differ because the radios do. Every one takes the nearest few of
every local amateur service **it can use**: the Anytone's hundred includes
thirty DMR channels the others cannot hear, the D75 and ID-52A carry D-STAR
instead, and the D75 and FTX-1 are the only two with 6 m. The blocks and
their quotas are the same everywhere; a radio simply contributes nothing for
a band or a mode it does not have.

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

A memory belongs to exactly one group, so the D75 cannot hold a curated
subset. What it does have is **Memory Group Link**: 30 bytes at image offset
`0x10A0`, an ordered list of group numbers terminated by `0xFF`, scanned
together by Group Link Scan. The exporter writes the groups `Near Me` draws
from - Ham Nets, Ham 6m, Ham 2m, Ham 1.25m, Ham 70cm, Ham D-STAR, Ham
Simplex, Ham Seattle ACS, which on this radio is groups 7 to 14: the whole
amateur run and nothing else.

That reaches whole groups, so it is a superset: the right stations plus their
more distant neighbours. Blocks are ordered nearest-first, so the nearest are
still the first things the scan reaches in each group.

The table is part of the export, not part of the radio's preserved settings:
`restore_unowned_regions` leaves it alone, or a later MCP-D75 save would put
back the radio's own four links. Verified against the operator's read, where
the four configured links appear as `00 01 02 03 FF...`.

## ID-52A

Group scan reaches one group, and a memory is in one group, so `Near Me`
exists only as a second copy of its channels in a group of its own - the last
one CS-52 imports. Seventy-six memories, which the plan funds by reserving
them: `_ID52A.reserve_slots` carries the operator's fifty free slots **and**
the copy, and the three widest-reaching blocks give up seventy of their most
distant rows to pay for it.

This is the one radio where widening `Near Me` costs anything real. The
Anytone spends a scan list it has 250 of, the D75 links one more group, the
FTX-1 ticks a box - only the ID-52A buys each channel twice.

Only the first scan group is copied. A second would cost another group's worth
of memories on a radio that can only scan one of them at a time anyway.

## FTX-1

The FTX-1 has **no banks**, which this project assumed for a while and was
wrong about. The programmer's memory grid has no Bank column and no
`Settings > Bank Settings` view; the bank symbols in `FTX1_V5.dll` are
inherited RT Systems framework overrides that this radio's grid never uses.

What it has is **`M-Grp`**: one checkbox per memory, between `Skip` and
`Tx DGID`, with `55: MEM Group` as the matching Set Menu item on the radio.
A single subset of the memories - not twenty-four banks, but one list, which
is exactly the shape of `Near Me`. Being a flag on the memory itself, it
costs neither a duplicate nor a slot: the best of the three mechanisms, on
the radio nobody expected it from.

It is **bit 1 of byte `0x00`**, sharing that byte with the in-use bit. The
old guess to that effect had never been tested - every in-use record of every
file here is `0x01`, all 553 memories read from the radio included - so a
probe settled it: twelve identical memories on 146.520, six with the box
ticked in the programmer, saved beside an unedited re-save of the same file.
Exactly those six went `0x01` to `0x03`, and the only other byte that moved
in 559,460 was a timestamp the programmer stamps on any save.

```
ftx1-banks-reference.FTX1 -> ftx1-banks-mgrp.FTX1: 7 differing bytes
  0x000185  record    1 +0x000     01 -> 03
  0x0003D3  record    3 +0x000     01 -> 03
  ...
  0x05605A  record 1194 +0x016     2E -> 38
```

`Ftx1Record.patched` sets each flag without disturbing the other, because
writing a plain `1` for "in use" on a later pass would silently clear the
group. Emptying a record clears both: a memory that is not there is not in
the memory group either.

Still open: what the radio does with `55: MEM Group` on - whether it scans
only the flagged memories or merely displays them apart. That decides whether
`Near Me` is the right list to carry rather than a wider one, not whether to
write the flag.

## TD-H9

No composite list, and nothing to build one with: CHIRP writes memories and a
skip flag, and the radio scans all of them.
