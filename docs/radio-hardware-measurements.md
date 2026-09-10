# Radio and mounting-hardware measurements

Dimensions are millimetres unless noted. This registry separates physical
measurements from derived dimensions, conservative envelopes, and published
values. A value is not promoted from one status to another without recording
new evidence.

## Status definitions

| Status | Meaning |
| --- | --- |
| Measured | Taken from the user's hardware or measurement sketch |
| Derived | Computed from measured values |
| Repository | Existing project value, with its original design context |
| Published | Third-party product listing; not physically verified here |
| Conservative | Deliberately larger/heavier envelope used for clearance or stress |

## Uniden SDS150

### Belt-clip lug and pedestal

Source of truth: `models/sds150_stud.scad`.

| Feature | Value | Status | Design use |
| --- | ---: | --- | --- |
| Lug head diameter | 15.5 | Measured | Entry hole and ledge coverage |
| Lug head thickness | 3.0 | Measured | Hidden head channel height |
| Lug neck diameter | 8.3 | Measured | Gravity slot width |
| Lug neck height | 4.5 | Measured | Ledge thickness |
| Lug total projection above pedestal | 7.5 | Derived | Radio-to-spine offset |
| Pedestal width | 25.0 | Measured | Anti-rotation guide width |
| Pedestal length | 35.0 | Measured | Anti-rotation guide travel envelope |
| Pedestal projection | 6.0 | Measured | Guide depth and radio back offset |
| Lug offset along pedestal | -2.5 | Derived from 20 mm measured from top of 35 mm pedestal | Attachment datum |
| Lug offset across pedestal | 0.0 | Measured | Centering datum |

### Existing fit values

| Feature | Value | Status | Design use |
| --- | ---: | --- | --- |
| Visor/legacy preload | 0.15 | Repository | Tight-fit reference only |
| Existing slide clearance, per side | 0.30 | Repository | Tight-fit reference only |
| Round-hole compensation | 0.25 | Repository | Preserve for 0.4 mm nozzle |
| Existing pedestal clearance, per side | 0.40 | Repository | Guide starting point |
| Existing head-channel vertical baseline | 0.40 | Repository | Channel starting point |
| Minimum locking travel | 15.925 | Derived | Hard lower bound |
| Standoff preload target | 0.05 | Design target | Easy gravity-assisted removal |
| Standoff slide clearance, per side | 0.35 | Design target | Easy gravity-assisted removal |
| Final standoff ledge thickness | 3.115 | User-requested design | 30% thinner than original 4.45 mm wall |
| Intentional lug axial freedom | 1.385 | Derived | Extra clearance created by thinner ledge |
| Compensated head-channel depth | original total depth preserved | Design | Maintains head clearance and capture |

### Radio envelope

Source image: `models/peak design radio standoff/design pictures/sds150.png`.
The sketch says `cm`; the user confirmed every label is mm.

| Feature | Value | Status | Notes |
| --- | ---: | --- | --- |
| Overall body height | 153 | Measured sketch | Excludes antenna |
| Sketch body width | 57 | Measured sketch | Conflicts with existing clearance envelope below |
| Lower raised/battery region | 93 | Measured sketch | Bottom to first horizontal datum |
| Pedestal/lug region | 35 | Measured sketch | Matches measured pedestal length |
| Upper region | 15 | Measured sketch | Remaining top section |
| Existing body-width clearance envelope | 69.9 | Repository/conservative | Used by the prior PD bracket for control clearance |
| Design collision width | 69.9 | Conservative | Retained until caliper measurement resolves 57 vs 69.9 |
| Nominal mass | 400 g | Repository estimate | Load calculations |

The drawing and pedestal offset imply a lug center approximately 108 mm above
the bottom: 93 mm to the pedestal region plus 15 mm to the lug center. This is
recorded as a derived planning datum and must be checked against the physical
radio before production dimensions are frozen.

## Kenwood TH-D75A

Source image: `models/peak design radio standoff/design pictures/Kenwood
THD75A.png`, plus user-provided caliper measurements. Sketch labels marked
`cm` mean mm.

| Feature | Value | Status | Design use |
| --- | ---: | --- | --- |
| Body height | 121.9 | Measured sketch | Diagnostic radio envelope |
| Body width | 56 | Measured sketch | Bump-pad keep-out |
| Belt-clip length | 66.5 | Measured sketch | Vertical insertion envelope |
| Clear clip section below belt contact | 30 | Measured sketch/user clarification | Must remain open so clip closes flush |
| Under-clip gap | 4.5 | Measured/user confirmed | Maximum bridge thickness |
| Clip back offset from radio | 6.5 | Measured/user confirmed | Radio-to-clip envelope |
| Maximum clip width at hinge | 21.3 | Measured/user caliper | Inner centering shoulders |
| Clip width at lower tip | 17.6 | Measured/user caliper | Lead-in and taper model |

Correct model name is **TH-D75A**, not TDH-75A.

## TIDRADIO TD-H9

| Feature | Value | Status | Notes |
| --- | ---: | --- | --- |
| Exact belt-clip jaw width | Unknown | Unverified | Must pass physical coupon |
| Exact under-clip gap | Unknown | Unverified | Must pass physical coupon |
| OEM compatibility | TD-H9 clip listings also name TD-H3/TD-H8 and several Baofeng-family radios | Published | Evidence for a broad bar, not a dimension |

Correct model name is **TD-H9**. No trustworthy dimensional listing for the
clip jaw was found. The design therefore does not encode a fictional exact
fit.

## Baofeng UV-5R

| Feature | Value | Status | Design use |
| --- | ---: | --- | --- |
| Replacement-clip overall length | 68 | Published | Diagnostic envelope only |
| Replacement-clip overall width | 32 | Published | Conservative outer envelope for 35 mm bar; jaw still unverified |
| Replacement-clip overall depth | 15 | Published | Diagnostic envelope only |

The published 68 × 32 × 15 listing describes the complete replacement clip,
not its exact jaw section. The 32 mm value is therefore an outer compatibility
envelope, not a centering fit.

## Peak Design Standard Plate and 1/4"-20 interface

| Feature | Value | Status | Design use |
| --- | ---: | --- | --- |
| Rubber-bearing footprint | 39 × 39 | Repository/user confirmed | Maximum standoff base |
| Thread major diameter | 6.35 | Standard | Socket interface |
| Thread pitch | 1.27 | Standard (20 TPI) | Socket interface |
| Self-tap pilot | 5.40 | Repository/proven | Superseded standoff variant; retained reference |
| Self-tap engagement | 8.25 | Repository/proven | Superseded standoff variant; retained reference |
| Heat-set insert outside diameter | 7.60 | Repository/proven | Superseded standoff variant; retained reference |
| Heat-set insert depth | 6.00 | Repository/proven | Superseded standoff variant; retained reference |
| Captive nut across flats | 11.15 | Repository/proven | Hardware reference |
| Captive nut across corners | 12.876 | Derived | Pocket size driver |
| Captive nut thickness | 5.60 | Repository/proven | Nut pocket depth |
| Side-loading nut floor | 1.20 | Design | Solid reaction surface under nut |
| 1/4" nut roof | 2.90 | Derived | Solid plate reaction above nut |
| M6 base nut across flats | 10.0 | Standard/user requested | Alternate Peak Design base variant |
| M6 base nut thickness | 5.2 | Standard/common | Side tunnel height |
| M6 base nut roof | 3.30 | Derived | Solid plate reaction above nut |

## Brodit / ProClip vehicle mount interface

Used by `models/proclip mounts/proclip_radio_mount.scad`. The two target
mounts are ProClip **805284** (left mount) and **855100** (angle mount),
both for the Volvo XC90 2015–20xx. Neither is owned yet, so **nothing in
this section is Measured.**

| Feature | Value | Status | Design use |
| --- | ---: | --- | --- |
| AMPS hole pattern, long side | 38.05 | Published standard | Screw pattern |
| AMPS hole pattern, short side | 30.17 | Published standard | Screw pattern |
| AMPS diagonal | 48.41 | Derived | Cross-check against 2-hole bases |
| AMPS maximum screw diameter | 5.2 | Published standard | M4 chosen |
| ProClip plate outline | Unknown | Unverified | Not used |
| ProClip plate thickness | 5.0 | **Estimate** | Screw length only, never geometry |
| ProClip plate hole diameter | Unknown | Unverified | Gauge pin ladder resolves it |
| Brodit "two sets of double-holes" | Unknown | Unverified | Not used |
| Plate material | ABS | Published | Why machine screws beat self-tappers |

Brodit describe the mounting plate's pattern as "one set of AMPS-holes as
well as two sets of double-holes placed in different height". The AMPS
set is a documented industry standard and is the only part this design
relies on. The double-hole pairs have no published spacing, so they are
deliberately unused rather than guessed at.

`proclip_gauge_horizontal.stl` and `proclip_gauge_vertical.stl` exist to
turn the first four rows from Published into Measured. Each carries the
AMPS holes in one orientation, a 3.0/3.5/4.0/4.5/5.0 mm pin ladder for
the ProClip's own hole diameter, and a central window through which the
undocumented double-holes can be seen and measured while the AMPS holes
hold the gauge registered.

Which physical mount takes which orientation is **not established**. The
exporter's `horizontal`/`vertical` filenames are labels, not findings.

### M4 fastener

| Feature | Value | Status | Design use |
| --- | ---: | --- | --- |
| Clearance hole | 4.50 | Design | Through-hole in the plate |
| Countersunk head diameter | 8.00 | Standard (ISO 10642 / DIN 7991) | Head recess |
| Countersink included angle | 90 | Standard | Cone geometry |
| Countersink depth | 1.75 | Derived | Head finishes flush |
| Plate left under the head | 3.25 | Derived | Bearing material |
| Nyloc nut height | 5.00 | Standard (DIN 985) | Screw length |
| Minimum screw length | 15.0 | Derived on the ESTIMATED plate | Buy 16 mm |

Countersunk rather than pan head because the SDS150's pedestal slides
directly across this face; a proud head would foul it.

### Ball-and-socket sizing, for reference

Researched but not implemented — the six plates are rigid. Recorded so
the size question does not have to be re-answered later.

| Feature | Value | Status | Note |
| --- | ---: | --- | --- |
| ProClip / Garmin ball | 17 | Published | ProClip's own phone and GPS mounts |
| RAM B size ball | 25.4 | Published | 2 lb standard / 1 lb heavy-duty use |
| RAM C size ball | 38.1 | Published | Larger tablets |
| AMPS-to-25 mm ball adapters | — | Published | e.g. Arkon APAMPS25MM |
| RAM-B-238U 2-hole spacing | 48.56 | Published | The AMPS diagonal |

A loaded SDS150 at 400 g (0.88 lb) exceeds what a 17 mm ball class is
intended for, which is why ProClip's own ball accessory is not the right
starting point for this radio. The 1" B-size ball is, and it bolts to the
same AMPS pattern.

## Adjustable-head joint hardware

| Feature | Value | Status | Design use |
| --- | ---: | --- | --- |
| Pivot bolt | M6 × 30 | User inventory/confirmed | Continuous −45°…+45° clamp joint |
| Available alternate M6 lengths | 6, 12, 16, 20, 30, 40 | User inventory | 30 mm selected |
| Standard M6 nut across flats | 10.0 | Standard | Captive hex pocket |
| Standard M6 nut thickness | 5.2 | Standard/common | Ear thickness and pocket depth |
| Printed tongue thickness | 11.8 | Design | Fits inside 12.2 mm fork gap |
| Fork-ear thickness | 6.0 each | Design | Captured head plus structural inner wall |
| Bare side clearance | 0.20 per face | Design | Washer installation space |
| TPU washer | 23 OD × 6.8 ID × 0.80 | Design | Replaceable continuous friction face |
| Washer recess | 0.70 | Design | Leaves washer 0.10 mm proud |
| Installed loose clearance | 0.10 per face | Derived | Free adjustment before clamping |
| Washer key flats | 21.0 span, opposed | Design | Prevent washer co-rotation |
| GoPro-style reference | 36 diameter × 13 thick | Design reference | Explicit 1.40× scale datum |
| Final knob envelope | 45.3 × 50.4 × 18.2 | Exported mesh | High finger torque |
| Knob wings | 3 | Design | Familiar GoPro-style grip |
| Knob captured nut | M6, 10 AF × 5.2 | Standard | Side-loaded rotating clamp element |
| Knob nut floor / blind wall | 2.0 / 1.6 | Design | Clamp reaction / covered screw end |
| Knob nut-tunnel clearance | 0.35 total at corners | Design | Printable side insertion |
| Fixed bolt head | M6 hex, 10 AF × 4.0 | Standard | Captured in right fork ear |

## Reference-image inventory

| File | What it establishes |
| --- | --- |
| `IMG20260829084803.jpg` | TH-D75A rear, clip installed, hinge and side taper |
| `IMG20260829084815.jpg` | TH-D75A rear oblique view, clip clearance and battery relationship |
| `IMG20260829084840.jpg` | TH-D75A side profile, clip spring gap and flush tip |
| `IMG20260829084951.jpg` | SDS150 rear view, pedestal/lug relative to battery and controls |
| `IMG20260829085009.jpg` | SDS150 rear oblique, lug projection and pedestal depth |
| `IMG20260829085030.jpg` | SDS150 side profile, battery projection and lug alignment |
| `IMG20260829090958.jpg` | Intended cup-holder/Peak Design stack and corrected 20 mm radio-bottom clearance |
| `Kenwood THD75A.png` | TH-D75A annotated dimensions |
| `sds150.png` | SDS150 annotated dimensions and vertical regions |
