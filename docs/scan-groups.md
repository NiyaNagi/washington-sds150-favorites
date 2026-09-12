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
| FTX-1 | banks exist on the radio, but not in a form this project can write | none |
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

## FTX-1 and TD-H9

Neither gets a composite list.

The TD-H9 has nothing to build one with: CHIRP writes memories and a skip
flag, and the radio scans all of them.

The FTX-1 does have banks, but an RT Systems `.FTX1` is a flat array of
295-byte records with no separate bank table - the blank template and a file
saved from the programmer differ nowhere outside the records - so bank
membership must live in bytes inside a record that this project has not
decoded. Decoding it needs a probe pair: in the FTX-1 programmer, save a file,
add one memory to one bank, save again under a new name, and diff. Until then
the FTX-1 gets its memory blocks in plan order and nothing else.
