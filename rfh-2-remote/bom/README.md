# RFH-2 — bill of materials

Values here are read out of upstream's Eagle schematic
([`../upstream/RFH-2.sch`](../upstream/RFH-2.sch)) by
[`../scripts/gen_bom.py`](../scripts/gen_bom.py), not transcribed by hand.
Re-run that script and the CSVs regenerate.

**Why the values matter more than usual.** The FH-2 protocol has no
microcontroller in the remote. Every button switches a different resistor into
a divider, and the radio decides which key you pressed purely from the voltage
on the tip of the plug. A wrong resistor is not a tolerance problem — it is a
different button, or no button. Use 1% parts and check each one with a meter
before it goes in the board.

## Files

| File | What it is |
|---|---|
| `RFH-2-bom.csv` | Grouped BOM, one row per value. This is the one to buy from. |
| `RFH-2-bom-flat.csv` | One row per reference designator, for stuffing and check-off. |
| `RFH-2-hardware-bom.csv` | Screws, standoffs and cable — not on any PCB order. |
| `digikey-cart.csv` | Bulk-add list for DigiKey, one spare per value. See caveat below. |

## Electronics

34 placed parts, 20 purchasable line items, plus two bare test pads.

| Qty | Ref | Value | Package | Part |
|---|---|---|---|---|
| 12 | `1` `2` `3` `4` `5` `DEC` `DOWN` `LEFT` `MEM` `P/B` `RIGHT` `UP` | — | TL6300 | Tactile switch, SPST-NO, 12 × 12 mm, through hole |
| 1 | R1 | 47 Ω | 0309/10 | 1/4 W 1% metal film, axial |
| 1 | R7 | 91 Ω | 0309/10 | " |
| 1 | R11 | 220 Ω | 0309/10 | " |
| 1 | R9 | 240 Ω | 0309/10 | " |
| 1 | R13 | 270 Ω | 0309/10 | " |
| 1 | R3 | 330 Ω | 0309/10 | " |
| 1 | R17 | 680 Ω | 0309/10 | " |
| 2 | R2, R5 | 820 Ω | 0309/10 | " |
| 2 | R4, R6 | 1 kΩ | 0309/10 | " |
| 1 | R20 | 1.5 kΩ | 0309/10 | " |
| 1 | R8 | 2.4 kΩ | 0309/10 | " |
| 1 | R10 | 3 kΩ | 0309/10 | " |
| 1 | R12 | 3.9 kΩ | 0309/10 | " |
| 1 | R14 | 5.1 kΩ | 0309/10 | " |
| 1 | R15 | 6.8 kΩ | 0309/10 | " |
| 1 | R18 | 8.2 kΩ | 0309/10 | " |
| 2 | R16, R19 | 12 kΩ | 0309/10 | " |
| 1 | R21 | 24 kΩ | 0309/10 | " |
| 1 | C1 | 22 nF | 5 mm radial | 50 V, film or X7R ceramic |
| — | TP1, TP2 | — | PAD1-20Y | Bare pads. Nothing to buy. |

The switches carry function names rather than `SW1`…`SW12` — that is how
upstream drew the schematic, and the silkscreen labels match.

**Resistor package.** The footprint is Eagle `0309/10`, meaning 10 mm lead
pitch. Ordinary 1/4 W metal film parts (≈6.3 × 2.5 mm body, the `0207` size)
drop straight in; the leads just bend a little less than usual. Anything up to
a 9 mm body fits.

**Switches.** Upstream's README names DigiKey `EG6117-ND` and the board has
that specific footprint. Any 12 × 12 mm through-hole tact switch on the same
pin pattern works, but the plunger height drives the cover standoff height, so
if you substitute, measure the new one and redo the check in
[`../ASSEMBLY.md`](../ASSEMBLY.md).

## Caveat on `digikey-cart.csv`

The manufacturer part numbers in that file are a convenience, not a verified
order. Distributor stock and part numbers change, and at least one of them was
already showing as discontinued when this folder was assembled. Treat the CSV
as a starting cart and confirm each line against the value table above before
paying for anything. The value table is the authority; the part numbers are a
shortcut.
