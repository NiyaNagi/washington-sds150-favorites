# MeshCore Solar Repeater — Bill of Materials

Quantities below are **per repeater unit**. You're building two, so double anything not marked otherwise. Prices are from your Amazon cart where visible; items without a confirmed price are marked accordingly.

## Core Electronics

| Item | Qty | Source | Notes |
|---|---|---|---|
| WisMesh 1W LoRa Booster Kit (RAK3401 core + RAK13302 IO module, nRF52840 + SX1262 + SKY66122 PA) | 1 | store.rakwireless.com | Ships with BLE PCB antenna (MHF1), mounting screws, USB-C cable |
| M1.2×3mm screws | included in kit | — | For core module + sensor mounting |

## Power System

| Item | Qty | Source | Price |
|---|---|---|---|
| Meshnology 3.7V 10000mAh LiPo battery, model 1163115 | 1 | Amazon | $39.99 / 2-pack |
| SECUPOE 20W Solar Panel w/ built-in 26000mAh battery, 5V USB-C out | 1 | Amazon | $59.99 |

## Enclosure & Weatherproofing

| Item | Qty | Source | Price |
|---|---|---|---|
| XINYIELE IP67 Junction Box, 220×170×110mm (8.7"×6.7"×4.3"), grey, w/ mounting plate + wall brackets + cable glands | 1 | Amazon | $19.88 |
| 580pc M3 Nylon Standoff Kit (board mounting) | 1 kit (shared across both builds) | Amazon | $8.59 |
| Marine Adhesive Sealant 4000 UV, 3oz | 1 tube (shared — may need a 2nd for both builds) | Amazon | $10.99 |
| Self-Fusing Silicone Tape, 1"×36' | 1 roll (shared, plenty for both) | Amazon | $8.99 |
| Plinkwirekb IP67 USB-C F/F waterproof bulkhead coupler | 1 | Amazon | $20.99 / 2-pack |
| M4 Well Nuts w/ M4×20mm stainless screws (solar bracket mount, no-cut) | ~2-4 per unit | Amazon | ~24-pair kit, shared |

## Antenna System

| Item | Qty | Source | Price |
|---|---|---|---|
| ALFA Network AOA-915-5ACM, 5dBi omni, N-Male | 1 | Amazon | $18.97 |
| POBADY U.FL/IPEX-to-N-Type-Female bulkhead pigtail, 6"/15cm | 1 | Amazon | $9.59 / 2-pack |
| N-type bulkhead hardware: nut, lock washer, toothed washer | included with pigtail | — | See install diagram from earlier — toothed washer innermost, nut last, tightened from inside |

## Mounting (tree-mount configuration)

| Item | Qty | Source | Notes |
|---|---|---|---|
| Plywood or HDPE backing board | 1 | hardware store | Sized to hold box + panel together as one assembly |
| Heavy-duty ratchet tie-down straps, 2" wide | 2 | Amazon/hardware store | Upper + lower, for wrapping backing board to trunk |
| Rubber/foam padding strip (old inner tube, pipe insulation, or rubber mulch mat) | as needed | — | Goes between strap and bark — the actual tree-protection step |

## Tools & Consumables (not per-unit — shared across the whole project)

| Item | Notes |
|---|---|
| Step drill bit set | For ABS enclosure holes — bulkhead, USB-C gland, well nuts. Safer than twist bits on brittle plastic |
| 8mm drill bit | Specifically for M4 well nut holes (may be covered by step bit set) |
| Calipers | For confirming N-type bulkhead shaft diameter and solar bracket hole size before drilling |
| Multimeter | For checking Meshnology battery polarity before first connection (known reported QC issue on this battery model) |
| Arborist throw-bag kit or extension ladder | For install height — see earlier safety discussion on ladder vs. rigging vs. hiring an arborist |

## Still to verify before final assembly

- **Solar bracket screw size** — confirm actual hole diameter on the SECUPOE bracket with calipers/a 4mm bit before committing to M4 well nuts
- **N-type bulkhead shaft diameter** — measure before drilling; commonly ~3/8" (9.5mm) but varies by manufacturer
- **Marine sealant quantity** — one 3oz tube may run short across two full builds plus panel mounting; consider a second tube
- **RAK13302 power jumper** — set to EX_5V for sustained 1W repeater operation (per RAK's own guidance for battery + solar configurations)
- **Firmware version** — confirm MeshCore firmware is v1.15.0 or later on both repeaters if you want the `dutycycle` and `rxgain` CLI commands from our last exchange
