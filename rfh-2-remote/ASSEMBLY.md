# RFH-2 — assembly

Order of operations matters in one place only: the cover standoff height has
to be settled before you order the cover, because it changes nothing about the
gerbers but everything about whether the buttons work.

## 1. Settle the standoff height first

The TL6300 plunger sits **7.30 mm** above the main PCB surface. The cover is
**1.6 mm** thick. So:

```
protrusion = 7.30 − standoff − 1.6
```

| Standoff | Protrusion | Verdict |
|---|---|---|
| 4.0 mm | 1.7 mm | plenty of travel, buttons stand proud |
| 4.5 mm | 1.2 mm | comfortable |
| 5.0 mm | 0.7 mm | flush-ish, still clears 0.3 mm of switch travel |
| 6.0 mm | −0.3 mm | plunger below the cover, unusable |

Switch travel is about 0.3 mm, so anything above ~0.5 mm of protrusion works.

**Measure a real switch before you commit.** The 7.30 mm figure came from a
dimension table that was ambiguous about whether it included the plunger. Print
test spacers at 4.0 / 4.5 / 5.0 mm, drop one real switch on the main board, and
look at it. Boards are cheap; the lead time is not.

## 2. Order the boards

Three separate JLCPCB orders — one board design per upload. Full option table
is in [`ORDERING.md`](ORDERING.md). Short version: 2 layer, 1.6 mm, defaults
otherwise.

The cover and back plate have **no copper at all**. A blank copper layer in the
DFM preview is correct, not a missing file.

## 3. Stuff the main board

Through-hole only, no surprises, but two things will bite you:

- **Check every resistor with a meter before it goes in.** The radio identifies
  each key by the voltage its resistor produces. A swapped 12 kΩ and 1.2 kΩ is
  a wrong keypress, not a slightly-off keypress, and once 21 axial parts are
  soldered in a ground-plane board they are miserable to remove. Colour bands
  on 1% metal film parts are easy to misread under desk light.
- **Solder the switches last and keep them square.** They set the plane the
  cover sits on. If one sits proud or tilted the cover will rock.

Clip the leads on the solder side close, then run a fingernail across —
anything you can catch will be pressing on the back plate later.

## 4. Wire the cable

Cut one end off a 3.5 mm TRS cable. Wire **tip** and **sleeve** to the two
pads. **Leave the ring floating** — do not ground it, do not tie it to the tip.
This is upstream's instruction and it is not optional.

Check continuity from the plug tip to the board pad before you close the case.

## 5. Assemble the sandwich

```
    cover            1.6 mm
    ── 4 standoffs   ~4.5 mm    (set in step 1)
    main board       1.6 mm
    ── 4 standoffs   3-5 mm     (only has to clear clipped leads)
    back plate       1.6 mm
```

**Eight standoffs, not four.** Two gaps means two sets. The lower set exists
purely so the back plate does not sit on clipped leads — and, if you have added
a power or bypass slide switch on the underside, so it does not sit on that
either.

The back plate silkscreen is mirrored onto the bottom layer, so it reads
correctly with the unit face-down. Fit it printed-side-out.

## 6. Test before trusting

Plug into the radio and press every key in turn, including the ones you never
use. A resistor error shows up as one specific key doing the wrong thing while
everything else is fine, so a partial test proves nothing.

If a key does the wrong thing, the resistor for that key is wrong — go back to
`bom/RFH-2-bom-flat.csv`, find the designator, and check that one part.
