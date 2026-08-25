# Radius-based lists and the HF additions

`ftx1-local` answers a different question from `ftx1-wa`. The statewide plan
asks *what exists in Washington*; this one asks *what can I actually work from
home*. That turns out to be a much smaller list, and building it surfaced a few
things worth writing down.

## Why not RepeaterBook

The original request named RepeaterBook, and its "active" flag is exactly the
signal wanted. It is not used here.

RepeaterBook's API moved to approval-gated access, and its terms prohibit
bundling or redistributing the data offline. This repository commits its
generated programming files so they can be loaded without running anything,
which is precisely the redistribution that is not permitted. A stub adapter
remains in the tree reporting `available=False`, so the gap is visible rather
than silently filled.

The substitute is **WWARA**, the Western Washington Amateur Relay Association —
the body that actually coordinates these pairs, so it is upstream of what
RepeaterBook republishes. Its extract carries 433 Washington entries, and every
one has coordinates, which is what the radius filter needs.

**What is lost by not using RepeaterBook:** its open/closed distinction. WWARA
has a `COMMENT` field that could carry it, but the field is empty on all 433
rows, so there is no open-repeater indicator in the data at all. Every
coordinated repeater is programmed. Some may be closed systems; the list cannot
tell you which, and neither can the radio.

## The expiry proxy

WWARA coordinations expire, and holding a pair requires keeping the
coordination current, so a lapsed record is a reasonable proxy for a repeater
that has gone off the air. 61 of the 433 Washington entries are expired.

Expired entries are marked **avoid** rather than deleted. A lapsed coordination
still tells you a machine was there and on what pair, which is worth seeing
while scanning even if nothing answers. Deleting it would throw away
information to save a slot that is not scarce.

An unparseable or missing expiry date counts as **current**. Guessing that a
malformed field means dead would quietly hide working repeaters, and a
programmed repeater that turns out to be silent is a far more obvious failure
than one that never appears.

## Why 60 miles for a 50-mile request

WWARA publishes fuzzed transmitter locations — coordinates rounded and offset,
because a repeater site is often on private property or a leased tower. The
offset is small but real, and a hard 50-mile cut would drop machines that sit
just inside the line and keep ones just outside, based on noise.

More to the point, 50 miles is not a propagation boundary. A well-sited 2 m
repeater on a Cascade foothill is workable from far past 50 miles; one in a
valley at 20 miles may be unreachable. The radius is a convenience filter, not
a coverage prediction, so the extra 10 miles costs a handful of slots and
avoids arbitrarily cutting usable machines.

The cascade, measured against the 2026-08-24 extract:

```
all Washington rows              433
coordination not expired         372   (-61)
within 60 mi of 98053            255  (-117)
inside FTX-1 receive coverage    219   (-36)
analog FM or Fusion capable      182   (-37)
```

163 reach the plan after per-band block limits. The furthest is 59.2 miles; the
nearest is W7DX Redmond on 147.000 at 1.2 miles.

## How the filter works

Distance filtering needed per-channel coordinates, which the catalog did not
have. It had a *coverage geo-fence* on departments, which is a different thing:
the fence describes the area where a signal is useful, the coordinates describe
where the transmitter physically stands. Only the second one supports "within N
miles of me", so `lat`, `lon` and `location_precision` were added to `Channel`
and populated from WWARA.

Plan selectors gained `within_miles=(lat, lon, radius)`:

```python
_near("PSHAM01", departments=r"2 ?m", limit=48)
```

A channel with no coordinates is **dropped**, not passed through. That matters:
if unlocated channels survived, a source that omits position would turn the
radius into a no-op while appearing to work. The failure is loud instead.

Only the three repeater blocks carry a radius. HF nets and calling frequencies
have no meaningful position, so filtering them by distance would remove all of
them — there is a test asserting no other block sets one.

## The HF content

The second half of the request was HF frequencies worth tuning across 160 m to
6 m. That became `HFNET01`, a 54-channel reference list in eight departments:
emergency and weather nets, IARU Region 2 emergency centres of activity, traffic
and calling nets, Pacific Northwest nets, utility and aeronautical, NCDXF
propagation beacons, WWV time standards, and 6 m calling and beacons.

**Frequencies are stable; schedules are not.** A net's frequency rarely changes
over decades, but its meeting time drifts with net control availability, season
and daylight saving. Every scheduled net therefore carries the note *"Schedule
changes; confirm with the net before relying on it."* Without it, the obvious
reading of a programmed channel is that traffic will be there whenever you
listen, and the silence looks like a broken list rather than the wrong hour.

The propagation beacons and WWV are the most useful entries for a new antenna.
NCDXF beacons transmit in a known rotation on 14.100, 18.110, 21.150, 24.930 and
28.200, so hearing one tells you the band is open and roughly how well your
receive path works. WWV on 2.5 through 25 MHz gives the same reading against a
known-good transmitter at a known distance.

`HFNET01` is marked reference-only. Most of it sits below the SDS150's 25 MHz
floor, so scanner generation projects those channels away and reports how many —
the same treatment `HAM01` already gets. The transceiver plans read the full
list.
