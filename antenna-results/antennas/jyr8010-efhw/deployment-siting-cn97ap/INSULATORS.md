# Insulator selection for the rope-to-wire junctions

Researched 2026-09-05 for the JYR8010-150W at 150 W SSB.

## Voltage at the ends — corrected

An earlier revision of this study quoted **2–4 kV** at the wire ends. That was too high.
Working it properly:

```
Feed:     150 W into the 1:64 transformer's ~3,200 ohm primary
          V_rms = sqrt(150 x 3200) = 693 V,  V_peak = 980 V

Far end:  a true open, so a few kOhm higher
          on the order of 1 kV RMS, ~1.4 kV peak
```

Higher with SWR or reactive buildup. **Design for ~2 kV peak** and there is margin.
Roughly half the earlier figure.

## The real failure mode is wet surface tracking, not dielectric breakdown

2 kV is comfortably inside any glazed ceramic insulator's *dry* rating. What actually
fails outdoors is **creepage** — the conductive path length across a wet surface. That is
governed by shape and surface chemistry, not bulk dielectric strength.

This is why the egg shape exists:

- The waist sheds water and interrupts the surface film
- The crossed-wire geometry keeps the wire **captive even if the ceramic cracks**
- Ceramic is inorganic, so it cannot track, erode, or carbonise the way a degraded
  polymer can

## Recommended parts

| Part | What it is | Use |
|---|---|---|
| **MFJ-16A01** (6-pack, ~$12) | Glazed ceramic egg, 2⅛ in long, **7/16 in holes** — large enough to pass ¼ in Dacron directly, which most small eggs are not | **Buy these.** Covers the whole antenna with spares. |
| **MFJ-16A06** | Same egg via DX Engineering | Equivalent, if already ordering from DXE |
| **W5SWL ceramic egg set** (3-pack) | Equivalent glazed ceramic egg for dipole / inverted-V / end-fed use | Fine substitute, smaller pack |
| **UHMW polyethylene dogbone** | 28 kV/mm dielectric strength, ~5× the mechanical strength of PTFE, naturally hydrophobic | Better mechanically and sheds water well, but polymers lose hydrophobicity under years of UV. Good at the apex where load is highest; ceramic wins on 20-year durability. |

The 7/16 in hole size is the deciding detail — many cheap eggs take only thin wire, and
you want the **rope** through the insulator, not a metal shackle that shorts across it.

## Placement

**Two eggs in series at every high-voltage node.** A single 2⅛ in egg gives modest
creepage; soaked in Pacific Northwest rain that is exactly the margin that matters.
Chaining two doubles the surface path for about $4.

High-voltage nodes on this 39.6 m wire (from `data/antenna-spec.json`):

| Location | Wire distance | Why |
|---|---|---|
| Feed | 0 m | Voltage max on every band. The transformer's own end insulator handles this. |
| **Apex support** | **17.86 m** | Sits right beside the **19.8 m voltage maximum on 40 m and 20 m**. Electrically an end, even though it looks like a mid-span support. **Double up here.** |
| **Far end tie-off** | 39.6 m | Voltage max on every band. **Double up here.** |
| Far support (option A) | 29.7 m | A *current* maximum — low voltage. Single insulator is fine. |

## What not to use

- **Nylon rope** — absorbs 4–8% water and stretches badly
- **Cheap polypropylene rope** — UV-dead in a season
- **Hardware-store plastic standoffs** — polycarbonate and nylon degrade in sunlight and
  can carbonise into a conductive path once tracking starts

Rope should be **3/16 or 1/4 in Dacron/polyester**, which absorbs ~0.4% water and
insulates soaked.

## Sources

- [MFJ-16A01 6-pack](https://www.amazon.com/MFJ-Enterprises-Original-MFJ-16A01-Insulator/dp/B0108NSYBU)
- [MFJ-16A06 at DX Engineering](https://www.dxengineering.com/parts/mfj-16a06)
- [W5SWL ceramic egg set](https://www.w5swl.com/products/antenna-insulator-ceramic-egg-hf-dipole-vee-endfed-wire-set-of-3-by-w5swl)
- [Ceramic vs polymer high-voltage insulation](https://electricaltrader.com/blogs/news/ceramic-vs-polymer-high-voltage-insulation-comparison)
- [Antenna insulators, ceramic and poly](https://www.dxhamradiosupply.com/Insulators-Ham-Radio-s/2118.htm)
