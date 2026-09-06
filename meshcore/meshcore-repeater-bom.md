# MeshCore Solar Repeater — Bill of Materials

Quantities below are **per repeater unit**. You're building two, so double anything not marked otherwise. Prices are from your Amazon cart where visible; items without a confirmed price are marked accordingly.

Note on links: a handful of items only appeared in your cart screenshot, not as separate messages with a URL I captured — for those I've linked the closest matching current listing I could verify, or flagged it for a quick double-check against what's actually in your cart rather than presenting a guess as certain.

## Core Electronics

| Item | Qty | Link | Notes |
|---|---|---|---|
| WisMesh 1W LoRa Booster Kit (RAK3401 core + RAK13302 IO module) | 1 | [store.rakwireless.com](https://store.rakwireless.com/products/meshtastic-1w-lora-booster-kit-rak3401?variant=45678368882886) | Ships with BLE PCB antenna (MHF1), mounting screws, USB-C cable |
| M1.2×3mm screws | included in kit | — | For core module + sensor mounting |

## Power System

| Item | Qty | Link | Price |
|---|---|---|---|
| Meshnology 3.7V 10000mAh LiPo battery, model 1163115 | 1 | Search "Meshnology 10000mAh 1163115" on Amazon — I don't have a captured direct link for this one, only your cart screenshot | $39.99 / 2-pack |
| SECUPOE 20W Solar Panel w/ built-in 26000mAh battery, 5V USB-C out | 1 | Search "SECUPOE 20W solar panel 26000mAh" on Amazon — same caveat, only seen via your cart | $59.99 |

## Enclosure & Weatherproofing

| Item | Qty | Link | Price |
|---|---|---|---|
| XINYIELE IP67 Junction Box, 220×170×110mm (8.7"×6.7"×4.5"), grey | 1 | [XINYIELE storefront](https://www.amazon.com/stores/page/1BE26E26-0497-490A-9D56-DEE706050EAC) — this brand sells many sizes under one storefront; confirm you're selecting the grey 8.7"×6.7"×4.5" variant already in your cart | $19.88 |
| 580pc M3 Nylon Standoff Kit | 1 kit (shared) | Search "580pcs M3 black nylon standoff kit" on Amazon | $8.59 |
| Marine Adhesive Sealant 4000 UV, 3oz | 1 tube (shared, may need a 2nd) | Search "Marine Adhesive Sealant 4000 UV 3oz" on Amazon | $10.99 |
| Self-Fusing Silicone Tape, 1"×36' | 1 roll (shared) | Search "MoltFix self fusing silicone repair tape 1x36" on Amazon | $8.99 |
| Plinkwirekb IP67 USB-C F/F waterproof bulkhead coupler | 1 | [amazon.com/dp/B0FRMNK3CV](https://www.amazon.com/Plinkwirekb-Waterproof-Bulkhead-Connector-Threaded/dp/B0FRMNK3CV) | $20.99 / 2-pack |
| M4 Well Nuts w/ M4×20mm stainless screws | ~2-4 per unit | [amazon.com/dp/B0C6KL5Q25](https://www.amazon.com/MAYEHAY-Stainless-Countersunk-Motorcycle-Windscreen/dp/B0C6KL5Q25) — alt: [EPDM version, dp/B07KJGCNHQ](https://www.amazon.com/EPDM-Rubber-Well-Nuts-Brass-Insert/dp/B07KJGCNHQ) | ~$10-15/kit |

## Antenna System

| Item | Qty | Link | Price |
|---|---|---|---|
| ALFA Network AOA-915-5ACM, 5dBi omni, N-Male | 1 | [amazon.com/dp/B08H8J6ZV6](https://www.amazon.com/dp/B08H8J6ZV6) | $18.97 |
| POBADY U.FL/IPEX-to-N-Type-Female bulkhead pigtail, 6"/15cm | 1 | [amazon.com/dp/B08ZYK5SL9](https://www.amazon.com/dp/B08ZYK5SL9) — functionally identical alt: [dp/B09N3LPBYB](https://www.amazon.com/dp/B09N3LPBYB) | $9.59 / 2-pack |
| N-type bulkhead hardware: nut, lock washer, toothed washer | included with pigtail | — | Toothed washer innermost against plastic, nut last, tightened from inside |

## Mounting (tree-mount configuration)

| Item | Qty | Link | Notes |
|---|---|---|---|
| Plywood or HDPE backing board | 1 | Hardware store, not Amazon | Sized to hold box + panel together as one assembly |
| Heavy-duty ratchet tie-down straps, 2" wide | 2 | Search "ratchet tie down strap 2 inch heavy duty" on Amazon | Upper + lower, wraps backing board to trunk |
| Rubber/foam padding strip | as needed | Old inner tube, pipe insulation, or hardware-store rubber mulch mat | The actual tree-protection step — goes between strap and bark |

## Tools & Consumables (shared across the whole project)

| Item | Link |
|---|---|
| Step drill bit set | Search "titanium step drill bit set" on Amazon |
| 8mm drill bit | May be covered by step bit set above |
| Calipers | Search "digital caliper" on Amazon |
| Multimeter | For checking Meshnology battery polarity before first connection |
| Arborist throw-bag kit | Search "arborist throw bag kit" on Amazon, or a sturdy extension ladder for lower installs |

## Still to verify before final assembly

- **Solar bracket screw size** — confirm actual hole diameter with calipers/a 4mm bit before committing to M4 well nuts
- **N-type bulkhead shaft diameter** — measure before drilling; commonly ~3/8" (9.5mm) but varies by manufacturer
- **Marine sealant quantity** — one 3oz tube may run short across two full builds plus panel mounting
- **RAK13302 power jumper** — set to EX_5V for sustained 1W repeater operation
- **Firmware version** — confirm MeshCore firmware is v1.15.0+ on both repeaters for `dutycycle` and `rxgain` CLI support
