# Peak Design opposed-face radio standoff

A one-piece upright adapter for a Peak Design Standard Plate in a cup-holder
mount. It carries two radios simultaneously:

- a Uniden SDS150 on the front gravity keyhole;
- a Kenwood TH-D75A, TIDRADIO TD-H9, Baofeng UV-5R, or similar belt-clip
  handheld on the rear bridge.

The two radios face opposite directions. This gives each a completely open
vertical insertion path, keeps their controls and antennas apart, and lets
their eccentric gravity moments partially cancel through the spine.

## Print the coupons first

Do not start with the 160 mm production body.

| File | Purpose |
| --- | --- |
| `radio_standoff_coupon_sds_easy.stl` | 0.00 mm preload, 0.40 mm side clearance |
| `radio_standoff_coupon_sds_nominal.stl` | **Default:** 0.05 mm preload, 0.35 mm side clearance |
| `radio_standoff_coupon_sds_firm.stl` | 0.10 mm preload, 0.30 mm side clearance |
| `radio_standoff_coupon_clip_thin.stl` | Actual rear interface with 2.8 mm bridge |
| `radio_standoff_coupon_clip.stl` | **Default:** actual rear interface with 3.0 mm bridge |
| `radio_standoff_coupon_clip_thick.stl` | Actual rear interface with 3.2 mm bridge |

The SDS150 head must pass through without force, slide fully down, remain
stable under gravity, and lift back out deliberately. Select the loosest coupon
that does not chatter. The nominal fit is intentionally easier than the visor
mount because there is no latch to overcome and gravity provides retention.

Test the TH-D75A clip on the three clip coupons. The physically measured clip is
21.3 mm at the hinge, 17.6 mm at the tip, with a 4.5 mm gap. TD-H9 and UV-5R
compatibility remains **envelope-compatible, not physically verified**, until
their real clips pass this coupon.

## Production files

| File | Socket |
| --- | --- |
| `peak_design_radio_standoff_self_tap.stl` / `.3mf` | 5.40 mm pilot; a 1/4"-20 screw forms its thread |
| `peak_design_radio_standoff_insert.stl` / `.3mf` | 7.60 × 6.00 mm heat-set insert pocket |
| `peak_design_radio_standoff_nut.stl` / `.3mf` | captive 1/4" nut, 12.875 mm across corners |

The heat-set insert version is preferred for repeated assembly. The self-tap
version is simplest and has ample calculated capacity. All three have exactly
the same outside envelope and full 39 × 39 mm Peak Design bearing face.

## How the SDS150 side works

1. Put the 15.5 mm lug head through the upper entry hole.
2. Let the radio descend 19 mm.
3. The 8.3 mm neck travels in the narrow slot while the head moves through a
   hidden channel behind the ledge.
4. At the bottom, the head is completely beneath solid ledge material.

There is deliberately no latch. Removal requires lifting the radio against
gravity and then pulling the head through the upper opening. Independent fit
checks report zero interference through 11 travel positions and 132.7 mm³ of
ledge interception when the seated stud is pulled 1.5 mm outward.

The radio bottom is exactly 20 mm above the Peak Design bearing plane when
fully seated. The mount derives the lug height from that requirement instead
of typing the overall standoff height independently.

Two shallow rails follow the raised 25 × 35 mm SDS150 pedestal. They suppress
rotation and rattle but remain open at the top so they never lock the radio.

## How the belt-clip side works

The rear bridge substitutes for a belt. The radio body remains outside the
bridge while its spring clip descends through the 3.6 mm open gap behind it.
The bridge is 3.0 mm thick, leaving 1.5 mm inside the measured Kenwood gap.

The top edge is a rounded lead-in contained within the bridge thickness. Its
first version bulged toward the radio and occupied 61.5 mm³ of the measured
clip; the independent clip sweep caught that before export.

The rails form a gravity-centering funnel:

- 33 mm clear at the top for the published 32 mm UV-5R clip envelope;
- 22.3 mm clear lower down for the measured 21.3 mm Kenwood hinge.

A wider tapered clip stops higher in the funnel. A narrow clip descends farther.
A constant-width 32 mm clip is intentionally rejected: the wide-envelope claim
only applies to clips that narrow toward the tip, as the measured Kenwood does.

## Organic structure

The body is not a rectangular post. Seven rounded cross-sections create a
continuous loft from the 39 mm base through a 23 mm waist and back into the
40 mm radio head. A central lens removes neutral-axis material while retaining
two edge rails, where material contributes most to section modulus.

The shape is functional rather than decorative:

- broad lower sections spread socket load into the Peak Design plate;
- the waist removes low-value interior material;
- full-depth edge rails resist fore/aft bending;
- the upper head grows only where the keyhole and bridge need support;
- large continuous transitions avoid notch stresses.

## Calculated structural performance

Assumptions: upright printed PLA, 400 g per radio, effective layer-normal
modulus 2.4 GPa, conservative strength 25 MPa.

| Load | Worst deflection | Worst stress | Factor of safety |
| --- | ---: | ---: | ---: |
| 1g lateral | 0.176 mm | 1.05 MPa | 23.8 |
| 3g road bump | 0.528 mm | 3.15 MPa | 7.9 |
| 5g shock | 0.880 mm | 5.24 MPa | 4.8 |

The governing section is near z=50 mm in fore/aft bending. Minimum material
area is 143 mm² and minimum fore/aft second moment is approximately
2,014 mm⁴. The opposed radio faces reduce static eccentric-gravity stress to
approximately 0.35 MPa.

The self-tap socket has approximately 140 mm² conservative shear area and a
calculated strip load around 2.5 kN. Over-torque during assembly is a more
credible risk than the 7.85 N combined radio weight.

These are analytical design values, not destructive physical-test results.

## Print settings

| Setting | Value |
| --- | --- |
| Material | PLA for room-temperature use; PETG/ASA for parked-car heat |
| Orientation | Upright, 39 × 39 mm base on plate |
| Layer height | 0.20 mm |
| Nozzle | 0.4 mm |
| Wall loops | 4 |
| Top/bottom shells | 5 / 5 |
| Infill | 20% gyroid |
| Supports | None |
| Brim | 6–8 mm recommended for the 160 mm tall body |

All unsupported production regions classify as bridges no longer than 11.2 mm.
Every production variant is a single watertight solid with no wall below
1.343 mm. The part is 40 × 39 × 160 mm and approximately 75.4 cm³.

The 40 mm upper guide width exceeds the 39 mm base, but the **base itself**
remains exactly 39 × 39 mm and does not interfere with the Capture plate.

## Verification commands

```powershell
.venv-cad\Scripts\python.exe scripts\cad\design_radio_standoff.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_fit.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_clip.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_assembly.py
.venv-cad\Scripts\python.exe scripts\cad\audit_radio_standoff.py
.venv-cad\Scripts\python.exe scripts\cad\export_radio_standoff.py
```

The checks include injected faults: an oversized SDS stud, an undersized clip
gap, a constant-width wide clip, a shifted radio, and a shifted screw path.
A harness that cannot detect its deliberate fault does not count as evidence.

## Known limits

- The 57 mm SDS150 sketch width conflicts with the earlier repository's
  conservative 69.9 mm clearance envelope. The design uses 69.9 mm until a
  caliper measurement resolves it.
- The SDS150 bottom-to-lug datum is derived as 108 mm from the annotated photo.
  Confirm it physically before treating the exact 20 mm bottom clearance as a
  production guarantee.
- TH-D75A clip geometry is physically measured. TD-H9 and UV-5R fit is not.
- PLA is accepted for the stated non-hot-car use. It is not qualified for a
  closed vehicle in summer sun.
- The radio envelopes validate gross interference, not every knob, connector,
  battery latch, or aftermarket antenna.

See [radio-hardware-measurements.md](radio-hardware-measurements.md) for the
measurement registry and [peak-design-radio-standoff-plan.md](peak-design-radio-standoff-plan.md)
for the implementation and acceptance plan.
