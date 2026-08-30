# Peak Design opposed-face radio standoff

A two-piece adjustable adapter for a Peak Design Standard Plate in a cup-holder
mount. It carries either radio on a common tilting head:

- a Uniden SDS150 on the front gravity keyhole;
- a Kenwood TH-D75A, TIDRADIO TD-H9, Baofeng UV-5R, or similar belt-clip
  handheld on the rear bridge.

The two interfaces face opposite directions. One M6×30 hex-head bolt, one
captured-nut knob, and two keyed friction washers clamp the common head
continuously from −45° to +45°. Positive tilt
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
| `radio_standoff_coupon_joint_stalk.stl` | Actual fork ears, bolt bore, and captured hex-head pocket |
| `radio_standoff_coupon_joint_head.stl` | Actual recessed head tongue for keyed washers |
| `radio_standoff_coupon_base_m6_nut.stl` | Actual side-loading M6 base nut tunnel and bearing roof |
| `radio_standoff_coupon_base_quarter_nut.stl` | Actual side-loading 1/4" base nut tunnel and bearing roof |

The SDS150 head must pass through without force, slide fully down, remain
stable under gravity, and lift back out deliberately. Select the loosest coupon
that does not chatter. The nominal fit is intentionally easier than the visor
mount because there is no latch to overcome and gravity provides retention.

Test the TH-D75A clip on the three clip coupons. The physically measured clip is
21.3 mm at the hinge, 17.6 mm at the tip, with a 4.5 mm gap. TD-H9 and UV-5R
compatibility remains **envelope-compatible, not physically verified**, until
their real clips pass this coupon.

Print the two joint coupons and two TPU washers. Assemble them with the intended
M6×30 standard hex-head bolt and M6 nut knob. The tongue and washer pair should
enter the fork without force, rotate freely when loose, and lock without
creeping when the knob is snug.

## Production files

| File | Purpose |
| --- | --- |
| `peak_design_radio_standoff_stalk_m6_nut.stl` / `.3mf` | Stalk with side-loading captive M6 nut |
| `peak_design_radio_standoff_stalk_quarter_nut.stl` / `.3mf` | Stalk with side-loading captive 1/4"-20 nut |
| `peak_design_radio_standoff_head.stl` / `.3mf` | Common adjustable radio head; print one |
| `radio_standoff_knob_gopro_140pct_m6_nut.stl` / `.3mf` | Three-wing GoPro-style knob with side-loading captured M6 nut |
| `radio_standoff_friction_washer_tpu.stl` / `.3mf` | Keyed continuous-friction washer; print **two** in 95A TPU |

Both stalks retain the full 39 × 39 mm Peak Design bearing face. The nut slides
in from the +X side and is trapped between a 1.2 mm floor and a solid roof:
3.3 mm over M6, 2.9 mm over 1/4"-20. Only the screw passage interrupts the
bottom bearing face, so the plate has solid material to clamp against.

Press one keyed washer into each side of the head. Insert a standard M6×30
hex-head bolt from the right: its 10 mm AF head enters the right-ear hex recess
and cannot rotate. Slide a standard M6 nut through the radial tunnel in the
knob, then thread the knob onto the fixed bolt from the left. The knob drives
the nut directly; it is not a sleeve over a socket/button-cap screw.

The three-wing knob is derived from a 36 mm × 13 mm GoPro-style reference and
scaled exactly 1.40×. Its exported envelope is 45.3 × 50.4 × 18.2 mm, with a
50.4 mm maximum grip span. The nut is trapped axially behind a 2 mm clamp floor
and rotationally by a 10.3 mm AF hex pocket. The radial tunnel has 0.35 mm
total corner clearance; the nut is fully captive once the bolt is threaded.
The modeled M6×30 shank engages the full 5.2 mm nut thickness and extends
2.6 mm beyond it into the knob's blind clearance bore.

## How the SDS150 side works

1. Put the 15.5 mm lug head through the upper entry hole.
2. Let the radio descend 19 mm.
3. The 8.3 mm neck travels in the narrow slot while the head moves through a
   hidden channel behind the ledge.
4. At the bottom, the head is completely beneath solid ledge material.

There is deliberately no latch. Removal requires lifting the radio against
gravity and then pulling the head through the upper opening. Independent fit
checks report zero interference through 11 travel positions and 130.5 mm³ of
ledge interception after the intentional 1.385 mm freedom plus 1.5 mm of
pull-out travel.

The radio bottom is exactly 20 mm above the Peak Design bearing plane when
fully seated. The mount derives the lug height from that requirement instead
of typing the overall standoff height independently.

There are no side guides. The broad head face supports the SDS150 pedestal,
while the lug ledge and gravity provide retention.

The highlighted lug-slide wall is exactly **30% thinner** than the prior
version: the nominal ledge changes from 4.45 mm to 3.115 mm. The head-channel
depth grows by the removed 1.385 mm, preserving the original far-side datum.
The wide lug disc therefore gets more axial freedom without changing its
entry-hole clearance, side clearance, or captured depth.

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

The common head has an 11.8 mm central tongue between 6.0 mm fork ears with
0.20 mm bare geometric clearance per face. Circular 13 mm joint lands flow
into the same rounded head language instead of looking like hardware bolted onto a slab.
The lower chord is flat so both parts print upright without support.

### Friction-interface decision

The earlier concentric-ring design was rejected. A ring centred on the pivot is
rotationally invariant: after any angular movement it occupies the same path,
so it cannot positively resist rotation. It can only alter contact pressure,
and the matching oversized grooves actually reduce broad face contact.

Alternatives were compared:

- Hirth/rosette radial teeth transfer high torque but are explicitly indexing
  couplings. They would replace continuous adjustment with discrete positions.
- Radial serrations or crosshatching on PLA introduce the same detent/wear
  problem at smaller scale and depend heavily on first-layer accuracy.
- A wave/Belleville washer preserves preload but does not itself prevent face
  slip; spring washers without serrations have no significant locking action.
- A compliant friction washer is replaceable, conforms to printed layer
  texture, damps vibration, and retains arbitrary angle adjustment.

The implemented interface therefore uses two 23 mm OD × 6.8 mm ID × 0.8 mm
95A-TPU washers. Each is recessed 0.70 mm into the moving head and projects
0.10 mm into the loose clearance. Two opposed 21 mm flats key each washer to
the head so it cannot simply rotate with the tongue. The outer faces rub
against smooth PLA fork faces. The mesh harness proves the flats engage, the
washers do not bind when loose, and they clear the stalk throughout ±45°.

Research references: [Hirth joints](https://en.wikipedia.org/wiki/Hirth_joint)
use tapered radial teeth for backlash-free indexing; the
[washer overview](https://en.wikipedia.org/wiki/Washer_(hardware)) identifies
rubber washers as vibration reducers and washers as wear pads; and
[Belleville washer guidance](https://en.wikipedia.org/wiki/Belleville_washer)
notes that non-serrated disc springs do not provide significant locking.

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

The keyed washer calculation uses a conservative 7.45 mm effective radius.
Using a deliberately conservative design assumption of $\mu=0.30$ for TPU/rubber on
PLA, only 105 N clamp preload is required for the worst 0.471 N·m 3g radio
moment. A realistic 0.5 kN finger-tight preload gives 2.23 N·m modeled
capacity, or 4.7 times that moment. Closing the 0.10 mm per-face loose
clearance strains each fork ear approximately 0.31%, below the 0.8% daily-use
PLA target.
With a conventional nut factor of 0.20, 0.5 kN preload corresponds to roughly
0.60 N·m tightening torque, or about 24 N tangential hand force at the knob's
25.2 mm grip radius.

The coefficient is not a material guarantee: surface finish, TPU formulation,
contamination, and clamp torque matter. Print and test the joint coupon. A
bench equivalent of the 3g design moment is a 0.48 kg mass at a 100 mm arm;
the snugged joint must hold that load without creep before use in a vehicle.

The base now reacts through captive metal nuts rather than printed/self-tapped
threads. Over-tightening the Peak Design screw remains a more credible risk
than the 7.85 N combined radio weight.

These are analytical design values, not destructive physical-test results.

## Print settings

| Setting | Value |
| --- | --- |
| Material | Rigid parts: PLA for room temperature, PETG/ASA for heat; washers: 95A TPU |
| Orientation | Stalk on base; head on flat chord; knob on broad back; washer flat |
| Layer height | 0.20 mm |
| Nozzle | 0.4 mm |
| Wall loops | 4 |
| Top/bottom shells | 5 / 5 |
| Infill | 20% gyroid |
| Supports | None |
| Brim | 6–8 mm on stalk/head; none on knob/washer |

Print the washer file twice, flat, in 95A TPU at 0.20 mm layers and 100% infill.
At 0.8 mm it is four layers thick. If TPU is unavailable, the same profile can
be cut from 0.8–1.0 mm rubber sheet, but it must pass the physical creep test.

The stalk is 39 × 39 × 121 mm. The common head prints at approximately
40 × 34 × 62 mm. Each production file is a single watertight solid. The head
may reach 40 mm across, but the **Peak Design bearing face** remains exactly
39 × 39 mm and does not interfere with the Capture plate.

## Verification commands

```powershell
.venv-cad\Scripts\python.exe scripts\cad\design_radio_standoff.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_tilt.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_knob.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_friction.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_fit.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_clip.py
.venv-cad\Scripts\python.exe scripts\cad\check_radio_standoff_assembly.py
.venv-cad\Scripts\python.exe scripts\cad\audit_radio_standoff.py
.venv-cad\Scripts\python.exe scripts\cad\export_radio_standoff.py
```

The checks include injected faults: rotated nut and bolt-head hexes, rotated
washer flats, an oversized SDS stud, an undersized clip gap, an oversized clip,
a shifted radio, a lowered head, and a shifted screw path.
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
- “GoPro-style” describes the familiar three-wing form, not a controlled
  dimensional standard. The 40% requirement is implemented against the
  explicit 36 × 13 mm reference datum recorded in the model and measurement
  registry; the exported maximum grip span is 50.4 mm.

See [radio-hardware-measurements.md](radio-hardware-measurements.md) for the
measurement registry and [peak-design-radio-standoff-plan.md](peak-design-radio-standoff-plan.md)
for the implementation and acceptance plan.
