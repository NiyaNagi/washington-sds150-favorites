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
| Clear clip section | 30 | Measured sketch/user clarification | Horizontal bridge location |
| Under-clip gap | 4.5 | Measured/user confirmed | Maximum bridge thickness |
| Flush clip-tip section | 6.5 | Measured/user confirmed | Lower keep-out |
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
| Replacement-clip overall width | 32 | Published | Outer shoulder envelope |
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
| Self-tap pilot | 5.40 | Repository/proven | Simplest socket variant |
| Self-tap engagement | 8.25 | Repository/proven | Socket depth target |
| Heat-set insert outside diameter | 7.60 | Repository/proven | Insert variant |
| Heat-set insert depth | 6.00 | Repository/proven | Insert variant |
| Captive nut across flats | 11.15 | Repository/proven | Hardware reference |
| Captive nut across corners | 12.876 | Derived | Pocket size driver |
| Captive nut thickness | 5.60 | Repository/proven | Nut pocket depth |

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
