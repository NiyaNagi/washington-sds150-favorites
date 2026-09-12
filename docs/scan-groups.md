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
| AT-D890UV | scan lists, 100 members, any channel in any number of them | **exactly the 100 curated channels**, plus `Ham All`, `Ham Analog`, `Ham DMR`, `Public Svc`, `Rail & Marine`, `Personal`, `Everything` |
| TH-D75A | Memory Group Link: an ordered list of memory groups scanned as one pass | **the six groups Near Me draws from, whole** - 242 channels rather than 70 |
| ID-52A | Group scan, one memory group at a time; a memory belongs to one group | **its own group of 66 copies**, the same channels in the same order |
| FTX-1 | `M-Grp`, one checkbox per memory: a single subset of the memories | **the 66 curated channels**, flagged in place - no copies, no slots |
| TD-H9 | no group or bank concept at all | none |

## AT-D890UV

A scan list names channels, and a channel can be in several. All eight groups
become scan lists directly; anything over 100 members splits into numbered
lists. See [at-d890uv-programming.md](at-d890uv-programming.md), including the
`.rdt` patch that restores full membership after the CPS's 50-member CSV
import.

## TH-D75A

A memory belongs to exactly one group, so the D75 cannot hold a curated
subset. What it does have is **Memory Group Link**: 30 bytes at image offset
`0x10A0`, an ordered list of group numbers terminated by `0xFF`, scanned
together by Group Link Scan. The exporter writes the groups `Near Me` draws
from - Ham Nets, Ham 2m, Ham 1.25m, Ham 70cm, Ham Simplex, Ham Seattle ACS.

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
one CS-52 imports. Sixty-six memories, which the plan funds by reserving them:
`_ID52A.reserve_slots` carries the operator's fifty free slots **and** the
copy, and the three widest-reaching blocks give up sixty of their most distant
rows to pay for it.

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
