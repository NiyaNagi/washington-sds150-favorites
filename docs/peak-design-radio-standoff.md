# Peak Design opposed-face radio standoff

A two-piece adjustable adapter for a Peak Design Standard Plate in a cup-holder
mount. It carries either radio on a common tilting head:

- a Uniden SDS150 on the front gravity keyhole;
- a Kenwood TH-D75A, TIDRADIO TD-H9, Baofeng UV-5R, or similar belt-clip
  handheld on the rear bridge.

The two interfaces face opposite directions. One M6×30 bolt and captive M6
nut clamp the common head continuously from −45° to +45°. Positive tilt
presents the SDS150 display upward; negative tilt presents the belt-clip radio
upward. At 0° both radios may still be installed simultaneously.

## Print the coupons first

Do not start with the full stalk and head.

| File | Purpose |
| --- | --- |
| `radio_standoff_coupon_sds_easy.stl` | 0.00 mm preload, 0.40 mm side clearance |
| `radio_standoff_coupon_sds_nominal.stl` | **Default:** 0.05 mm preload, 0.35 mm side clearance |
| `radio_standoff_coupon_sds_firm.stl` | 0.10 mm preload, 0.30 mm side clearance |
| `radio_standoff_coupon_clip_thin.stl` | Actual rear interface with 2.8 mm bridge |
| `radio_standoff_coupon_clip.stl` | **Default:** actual rear interface with 3.0 mm bridge |
| `radio_standoff_coupon_clip_thick.stl` | Actual rear interface with 3.2 mm bridge |
| `radio_standoff_coupon_joint_stalk.stl` | Actual fork ears, bolt bore, and captive M6 nut pocket |
| `radio_standoff_coupon_joint_head.stl` | Actual head tongue and friction faces |

The SDS150 head must pass through without force, slide fully down, remain
stable under gravity, and lift back out deliberately. Select the loosest coupon
that does not chatter. The nominal fit is intentionally easier than the visor
mount because there is no latch to overcome and gravity provides retention.

Test the TH-D75A clip on the three clip coupons. The physically measured clip is
21.3 mm at the hinge, 17.6 mm at the tip, with a 4.5 mm gap. TD-H9 and UV-5R
compatibility remains **envelope-compatible, not physically verified**, until
their real clips pass this coupon.

Print the two joint coupons together and assemble them with the intended
M6×30 bolt and M6 nut. The tongue should enter the fork without force, rotate
freely when loose, and lock without creeping when the bolt is snug.

## Production files

| File | Purpose |
| --- | --- |
| `peak_design_radio_standoff_stalk_self_tap.stl` / `.3mf` | Stalk with 5.40 mm pilot; a 1/4"-20 screw forms its thread |
| `peak_design_radio_standoff_stalk_insert.stl` / `.3mf` | Stalk with 7.60 × 6.00 mm heat-set insert pocket |
| `peak_design_radio_standoff_stalk_nut.stl` / `.3mf` | Stalk with captive 1/4" nut, 12.875 mm across corners |
| `peak_design_radio_standoff_head.stl` / `.3mf` | Common adjustable radio head; print one |

The heat-set insert version is preferred for repeated assembly. The self-tap
version is simplest and has ample calculated capacity. All three stalks have
exactly the same outside envelope and full 39 × 39 mm Peak Design bearing face.

Join the head to the stalk with one M6×30 bolt and one standard M6 nut. The nut
presses into the hex pocket in the right fork ear. Tighten the exposed bolt
head until the head holds its angle; do not crush the printed friction faces.

## How the SDS150 side works

1. Put the 15.5 mm lug head through the upper entry hole.
2. Let the radio descend 19 mm.
3. The 8.3 mm neck travels in the narrow slot while the head moves through a
   hidden channel behind the ledge.
4. At the bottom, the head is completely beneath solid ledge material.

There is deliberately no latch. Removal requires lifting the radio against
gravity and then pulling the head through the upper opening. Independent fit
checks report zero interference through 11 travel positions and 126.2 mm³ of
ledge interception when the seated stud is pulled 1.5 mm outward.

The radio bottom is exactly 20 mm above the Peak Design bearing plane when
fully seated. The mount derives the lug height from that requirement instead
of typing the overall standoff height independently.

There are no side guides. The broad head face supports the SDS150 pedestal,
while the lug ledge and gravity provide retention.

## How the belt-clip side works

The rear bridge substitutes for a belt. It is the **full-width plate shown in
the final marked-up reference**, shortened to 35 mm wide × 25 mm tall × 3 mm
thick and moved upward to z=132…157. The clip hangs over its rounded top edge.
The measured clear clip section is 30 mm, so the shortened plate leaves 5 mm
below its rounded bottom edge for the spring tip to return flush against the
radio.

The plate is **35 mm wide** and stands 7.0 mm behind the head, far enough
that the clip's inner spring clears the M6 fork ears throughout the closing
path. A 21.3 mm pair of shallow collars centers the measured Kenwood hinge.
Wider tapered clips ride over those 0.65 mm rails and are limited by outer
supports with 33.0 mm between them. The local plate-plus-rail thickness is
3.65 mm, leaving 0.85 mm in the measured 4.5 mm Kenwood gap.

Thirty-five millimetres is the calculated minimum horizontal width for both
envelopes: 32 mm generic width, 0.5 mm insertion clearance per side, and
1.0 mm structural overlap into each end support. A 34 mm plate would leave
only 0.5 mm of support overlap—barely one printed perimeter—and was rejected.

## Organic structure

The stalk is not a rectangular post. Five rounded cross-sections create a
continuous loft from the 39 mm base through a 23 mm waist into a circular
two-ear clevis. A central lens removes neutral-axis material while retaining
two edge rails, where material contributes most to section modulus.

The common head has an 11.8 mm central tongue between 6.6 mm fork ears with
0.20 mm clearance per face. Circular 13 mm friction lands flow into the same
rounded head language instead of looking like hardware bolted onto a slab.
The lower chord is flat so both parts print upright without support.

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
| 1g lateral | 0.218 mm | 1.13 MPa | 22.1 |
| 3g road bump | 0.655 mm | 3.40 MPa | 7.4 |
| 5g shock | 1.092 mm | 5.66 MPa | 4.4 |

The governing section is near z=50 mm in fore/aft bending. Minimum material
area is 143 mm² and minimum fore/aft second moment is approximately
2,015 mm⁴. The opposed radio faces reduce static eccentric-gravity stress to
approximately 0.16 MPa at neutral tilt.

The M6 friction lands have a 9.11 mm effective radius. A conservative dry
PLA-on-PLA model requires only 143 N clamp preload to resist the worst 3g radio
moment. A modest 1.5 kN M6 preload provides 4.92 N·m capacity, approximately
10.5 times that 3g moment. Closing the 0.20 mm side clearance strains each
fork ear approximately 0.69%, below the 0.8% daily-use PLA target. These
figures assume clean, dry printed faces.

The self-tap socket has approximately 140 mm² conservative shear area and a
calculated strip load around 2.5 kN. Over-torque during assembly is a more
credible risk than the 7.85 N combined radio weight.

These are analytical design values, not destructive physical-test results.

## Print settings

| Setting | Value |
| --- | --- |
| Material | PLA for room-temperature use; PETG/ASA for parked-car heat |
| Orientation | Stalk upright on 39 × 39 mm base; head upright on its flat joint chord |
| Layer height | 0.20 mm |
| Nozzle | 0.4 mm |
| Wall loops | 4 |
| Top/bottom shells | 5 / 5 |
| Infill | 20% gyroid |
| Supports | None |
| Brim | 6–8 mm on both parts |

The stalk is 39 × 39 × 121 mm. The common head prints at approximately
40 × 34 × 62 mm. Each production file is a single watertight solid. The head
may reach 40 mm across, but the **Peak Design bearing face** remains exactly
39 × 39 mm and does not interfere with the Capture plate.

## Verification commands

```powershell
.venv-cad\Scripts\python.exe scripts\cad\design_radio_standoff.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_tilt.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_fit.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_clip.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_assembly.py
.venv-cad\Scripts\python.exe scripts\cad\audit_radio_standoff.py
.venv-cad\Scripts\python.exe scripts\cad\export_radio_standoff.py
```

The checks include injected faults: an oversized SDS stud, an undersized clip
gap, an oversized clip, a shifted radio, a lowered head, and a shifted screw path.
A harness that cannot detect its deliberate fault does not count as evidence.

## Known limits

- The 57 mm SDS150 sketch width conflicts with the earlier repository's
  conservative 69.9 mm clearance envelope. The design uses 69.9 mm until a
  caliper measurement resolves it.
- The SDS150 bottom-to-lug datum is derived as 108 mm from the annotated photo.
  Confirm it physically before treating the exact 20 mm bottom clearance as a
  production guarantee.
- TH-D75A clip geometry is physically measured. TD-H9 and UV-5R fit is not.
- The published 32 mm UV-5R value is the complete replacement-clip envelope,
  not a measured jaw section. The 35 mm bar clears that conservative envelope,
  but exact TD-H9 and UV-5R fit still requires the physical coupon.
- PLA is accepted for the stated non-hot-car use. It is not qualified for a
  closed vehicle in summer sun.
- The radio envelopes validate gross interference, not every knob, connector,
  battery latch, or aftermarket antenna.

See [radio-hardware-measurements.md](radio-hardware-measurements.md) for the
measurement registry and [peak-design-radio-standoff-plan.md](peak-design-radio-standoff-plan.md)
for the implementation and acceptance plan.
