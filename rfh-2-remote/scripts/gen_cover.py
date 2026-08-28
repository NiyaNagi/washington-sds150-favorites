#!/usr/bin/env python3
"""
Generate RS-274X gerbers + Excellon drill for an RFH-2 top cover panel.

All geometry is derived from RFH-2.brd -- nothing is hand-typed.
Written as plain text so that validation (gerbonara) is an independent parse.
"""
import xml.etree.ElementTree as ET
import os, math, json, sys
from gerbonara.newstroke import Newstroke

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BRD = os.environ.get('RFH2_BRD', os.path.join(PROJ, 'upstream', 'RFH-2.brd'))
OUT = os.environ.get('RFH2_COVER_OUT', os.path.join(PROJ, 'build', 'cover_gerbers'))
SPEC = os.environ.get('RFH2_COVER_SPEC', os.path.join(PROJ, 'build', 'cover_spec.json'))
os.makedirs(OUT, exist_ok=True)

# ---- design parameters -------------------------------------------------
PLUNGER_HOLE_DIA = 7.0     # mm. plunger is 5.0 x 3.0 -> 5.83 diagonal
SILK_W           = 0.20    # mm. JLCPCB silkscreen minimum is 0.15
OUTLINE_W        = 0.10    # mm
ARC_SEGS         = 1       # full circles drawn as single G03 multiquadrant arc

# ---- 1. extract geometry from the Eagle board --------------------------
root = ET.parse(BRD).getroot()

switches = {}
for e in root.iter('element'):
    if e.get('package') == 'TL6300':
        switches[e.get('name')] = (float(e.get('x')), float(e.get('y')))

mount_holes = [(float(h.get('x')), float(h.get('y')), float(h.get('drill')))
               for h in root.iter('hole')]

outline_wires = [(float(w.get('x1')), float(w.get('y1')),
                  float(w.get('x2')), float(w.get('y2')))
                 for w in root.find('.//plain').iter('wire')
                 if w.get('layer') == '20']

xs = [c for w in outline_wires for c in (w[0], w[2])]
ys = [c for w in outline_wires for c in (w[1], w[3])]
BW, BH = max(xs) - min(xs), max(ys) - min(ys)

plain = root.find('.//plain')
labels = []
for t in plain.iter('text'):
    if t.get('layer') == '21' and t.get('rot') is None and '\n' not in (t.text or ''):
        labels.append((t.text, float(t.get('x')), float(t.get('y')), float(t.get('size'))))

arrows = [[(float(v.get('x')), float(v.get('y'))) for v in p]
          for p in plain.iter('polygon') if p.get('layer') == '21']

print(f'switches      : {len(switches)}')
print(f'mount holes   : {len(mount_holes)}  drills={sorted({h[2] for h in mount_holes})}')
print(f'board outline : {BW} x {BH} mm')
print(f'silk labels   : {[l[0] for l in labels]}')
print(f'arrow polys   : {len(arrows)}')

# ---- 2. gerber primitives ----------------------------------------------
def c(v):
    """mm -> 4.4 fixed point"""
    return f'{int(round(v * 10000)):d}'

def header(name):
    return ['G04 RFH-2 top cover - generated from RFH-2.brd*',
            'G75*', '%MOMM*%', '%FSLAX44Y44*%', '%LPD*%',
            f'%IN{name}*%', '%IPPOS*%', 'G01*']

def write(fn, body):
    # newline='\n' so a Windows run produces the same bytes as a Linux one.
    with open(os.path.join(OUT, fn), 'w', newline='\n') as f:
        f.write('\n'.join(body) + '\nM02*\n')

def polyline(pts):
    out = [f'X{c(pts[0][0])}Y{c(pts[0][1])}D02*']
    for x, y in pts[1:]:
        out.append(f'X{c(x)}Y{c(y)}D01*')
    return out

def full_circle(cx, cy, r):
    """multiquadrant full circle, starts and ends at (cx+r, cy)"""
    return ['G75*',
            f'X{c(cx + r)}Y{c(cy)}D02*',
            f'G03X{c(cx + r)}Y{c(cy)}I{c(-r)}J{c(0)}D01*',
            'G01*']

def region(pts):
    out = ['G36*', f'X{c(pts[0][0])}Y{c(pts[0][1])}D02*']
    for x, y in pts[1:]:
        out.append(f'X{c(x)}Y{c(y)}D01*')
    out.append(f'X{c(pts[0][0])}Y{c(pts[0][1])}D01*')
    out.append('G37*')
    return out

# ---- 3. text -----------------------------------------------------------
font = Newstroke.load()

def text_strokes(s, x0, y0, size):
    """Newstroke returns screen-space y (down-positive); flip to board space
    and put the cap baseline on y0, matching Eagle's text anchor."""
    ref = list(font.render('M', size=size, x0=0, y0=0))
    base = max(p[1] for st in ref for p in st)     # baseline in screen space
    strokes = list(font.render(s, size=size, x0=0, y0=0))
    return [[(px + x0, (base - py) + y0) for px, py in st] for st in strokes]

# ---- 4. build layers ---------------------------------------------------
# silkscreen top
silk = header('Silkscreen Top')
silk += [f'%ADD10C,{SILK_W:.6f}*%', 'D10*']
n_strokes = 0
for txt, x, y, size in labels:
    for st in text_strokes(txt, x, y, size):
        silk += polyline(st)
        n_strokes += 1
for poly in arrows:
    silk += region(poly)
# credit line, rotated 90 deg along the left edge like the original board
credit = 'RFH-2 TOP COVER'
for st in text_strokes(credit, 0, 0, 1.8):
    rot = [(-py + 5.0, px + 30.0) for px, py in st]   # 90 deg CCW + offset
    silk += polyline(rot)

# callsign, centred along the bottom edge below the last row of switches
CALLSIGN = 'KM7HKM / WA7DAM'
_cs = text_strokes(CALLSIGN, 0, 0, 2.6)
_w = max(px for st in _cs for px, py in st)
_cx, _cy = (BW - _w) / 2, 7.4
for st in _cs:
    silk += polyline([(px + _cx, py + _cy) for px, py in st])
print(f'callsign     : {CALLSIGN!r} {_w:.1f}mm wide at x={_cx:.1f} y={_cy}')

# ---- 4b. operating reference in the gaps between switch rows -----------
# Content is chosen to complement the back plate, not repeat it: the back
# carries band edges, Q codes, RST and CW abbreviations, so the front carries
# the phonetic alphabet, CW numerals and the bench formulas instead.
#
# Nothing here is positioned by hand. The free horizontal bands are derived
# from the board's own obstacles, and every line is then re-checked against
# that geometry, so a line that would collide fails the build.

REF_MARGIN_L = 6.5     # clears the rotated credit text at x <= 5.0
REF_MARGIN_R = 3.0
H_HEAD, H_BODY = 1.45, 1.2
GAP = 0.9
PITCH_MIN, PITCH_MAX = 1.75, 2.4
PAD_MIN = 0.3
SWITCH_CLEAR = 0.5     # beyond the 3.5 mm cutout radius
HOLE_KEEPOUT = 3.6

SECTIONS = [
    ('MORSE CODE', [
        'A .-    B -...  C -.-.  D -..   E .     F ..-.  G --.   H ....  I ..',
        'J .---  K -.-   L .-..  M --    N -.    O ---   P .--.  Q --.-  R .-.',
        'S ...   T -     U ..-   V ...-  W .--   X -..-  Y -.--  Z --..',
    ]),
    ('ITU PHONETIC ALPHABET', [
        'A ALFA  B BRAVO  C CHARLIE  D DELTA  E ECHO  F FOXTROT  G GOLF',
        'H HOTEL  I INDIA  J JULIETT  K KILO  L LIMA  M MIKE  N NOVEMBER',
        'O OSCAR  P PAPA  Q QUEBEC  R ROMEO  S SIERRA  T TANGO  U UNIFORM',
        'V VICTOR  W WHISKEY  X XRAY  Y YANKEE  Z ZULU',
    ]),
    ('NUMERALS AND PROSIGNS', [
        '1 .----  2 ..---  3 ...--  4 ....-  5 .....   / -..-.',
        '6 -....  7 --...  8 ---..  9 ----.  0 -----   ? ..--..',
        'AR .-.-. END   SK ...-.- CLEAR   KN -.--. NAMED   BT -...- PAUSE',
    ]),
]


def width_of(s, size):
    st = text_strokes(s, 0, 0, size)
    return max(p[0] for k in st for p in k) if st else 0.0


# obstacles the reference text must avoid: (cx, cy, r) and (x0, y0, x1, y1)
circles = [(sx, sy, PLUNGER_HOLE_DIA / 2 + SWITCH_CLEAR)
           for sx, sy in switches.values()]
circles += [(hx, hy, HOLE_KEEPOUT) for hx, hy, _ in mount_holes]

rects = []
for txt, lx, ly, size in labels:
    rects.append((lx, ly - 0.3, lx + width_of(txt, size), ly + size + 0.3))
for poly in arrows:
    axs = [p[0] for p in poly]
    ays = [p[1] for p in poly]
    rects.append((min(axs), min(ays), max(axs), max(ays)))
rects.append((3.2, 30.0, 5.0, 49.5))                       # rotated credit
rects.append((_cx, _cy - 0.3, _cx + _w, _cy + 2.6 + 0.3))  # callsign

# free full-width horizontal bands = gaps between merged obstacle y-extents.
# Only obstacles that actually intrude into the text column count; the rotated
# credit sits left of it and must not block a band it never reaches.
x_left = REF_MARGIN_L
x_right = BW - REF_MARGIN_R

spans = [(cy - r, cy + r) for cx, cy, r in circles
         if cx - r < x_right and cx + r > x_left]
spans += [(y0, y1) for x0, y0, x1, y1 in rects
          if x0 < x_right and x1 > x_left]
spans.sort()
merged = []
for lo, hi in spans:
    if merged and lo <= merged[-1][1]:
        merged[-1][1] = max(merged[-1][1], hi)
    else:
        merged.append([lo, hi])

bands, prev = [], 0.0
for lo, hi in merged:
    if lo - prev > 1.0:
        bands.append((prev, lo))
    prev = max(prev, hi)
if BH - prev > 1.0:
    bands.append((prev, BH))

# usable bands: tall enough for a section, and not the callsign strip
usable = sorted([b for b in bands if b[1] - b[0] >= 7.5 and b[0] > 12.0],
                key=lambda b: -b[1])
print(f'free bands   : {[f"{a:.1f}-{b:.1f}" for a, b in bands]}')
print(f'usable bands : {[f"{a:.1f}-{b:.1f}" for a, b in usable]}')

if len(usable) < len(SECTIONS):
    sys.exit(f'ERROR: {len(SECTIONS)} sections but only {len(usable)} usable bands')

ref_lines = []
DESC = 0.3 * H_BODY     # descender allowance, matching the collision check
for (band_lo, band_hi), (head, rows) in zip(usable, SECTIONS):
    # Let the line pitch grow into whatever the band leaves spare, so a short
    # section breathes instead of bunching at the top of its gap.
    fixed = H_HEAD + GAP + H_BODY + DESC
    spare = (band_hi - band_lo) - 2 * PAD_MIN - fixed
    pitch = max(PITCH_MIN, min(PITCH_MAX, spare / max(1, len(rows) - 1)))
    total = fixed + (len(rows) - 1) * pitch
    pad = (band_hi - band_lo - total) / 2
    y_head = band_hi - pad - H_HEAD
    print(f'  band {band_lo:5.1f}-{band_hi:5.1f}  pitch {pitch:.2f}  pad {pad:.2f}  {head}')
    ref_lines.append((head, x_left, y_head, H_HEAD))
    for i, row in enumerate(rows):
        ref_lines.append((row, x_left, y_head - GAP - H_BODY - i * pitch, H_BODY))

# ---- validate every line against the real geometry ---------------------
errs = []
for txt, lx, ly, size in ref_lines:
    w = width_of(txt, size)
    bx0, by0, bx1, by1 = lx, ly - 0.3 * size, lx + w, ly + size
    if bx1 > x_right + 0.01:
        errs.append(f'{txt[:34]!r} overruns right margin by {bx1 - x_right:.2f} mm')
    if bx0 < 2.5 or by0 < 2.5 or by1 > BH - 2.5:
        errs.append(f'{txt[:34]!r} outside board margin')
    for cx, cy, r in circles:
        nx, ny = max(bx0, min(cx, bx1)), max(by0, min(cy, by1))
        if math.hypot(cx - nx, cy - ny) < r:
            errs.append(f'{txt[:34]!r} hits cutout/hole at ({cx:.1f}, {cy:.1f})')
    for rx0, ry0, rx1, ry1 in rects:
        if bx0 < rx1 and bx1 > rx0 and by0 < ry1 and by1 > ry0:
            errs.append(f'{txt[:34]!r} overlaps existing silk at y={ry0:.1f}')

widest = max(ref_lines, key=lambda l: width_of(l[0], l[3]))
print(f'reference    : {len(ref_lines)} lines, usable width {x_right - x_left:.1f} mm')
print(f'widest line  : {width_of(widest[0], widest[3]):.1f} mm  {widest[0][:40]!r}')
if errs:
    print('\nLAYOUT ERRORS:')
    for e in sorted(set(errs)):
        print('  -', e)
    sys.exit(1)
print('reference layout fits')

for txt, lx, ly, size in ref_lines:
    for st in text_strokes(txt, lx, ly, size):
        silk += polyline(st)
        n_strokes += 1

write('RFH-2-cover.GTO', silk)

# outline: board rectangle + 12 routed plunger holes (>6.3mm -> not drillable)
prof = header('Profile')
prof += [f'%ADD10C,{OUTLINE_W:.6f}*%', 'D10*']
prof += polyline([(0, 0), (BW, 0), (BW, BH), (0, BH), (0, 0)])
for name, (sx, sy) in sorted(switches.items()):
    prof += full_circle(sx, sy, PLUNGER_HOLE_DIA / 2)
write('RFH-2-cover.GKO', prof)

# empty copper / mask / bottom silk -- present but blank
for fn, nm in [('RFH-2-cover.GTL', 'Copper Top'),
               ('RFH-2-cover.GBL', 'Copper Bottom'),
               ('RFH-2-cover.GTS', 'Soldermask Top'),
               ('RFH-2-cover.GBS', 'Soldermask Bottom'),
               ('RFH-2-cover.GBO', 'Silkscreen Bottom')]:
    write(fn, header(nm) + ['%ADD10C,0.100000*%'])

# Excellon drill: only the 4 mounting holes (5.0mm, under the 6.3mm limit)
drill = ['M48', 'METRIC,TZ', 'FMAT,2']
tools = sorted({h[2] for h in mount_holes})
for i, d in enumerate(tools, 1):
    drill.append(f'T{i:02d}C{d:.3f}')
drill += ['G90', 'G05', '%']
for i, d in enumerate(tools, 1):
    drill.append(f'T{i:02d}')
    for hx, hy, hd in mount_holes:
        if hd == d:
            drill.append(f'X{hx:.3f}Y{hy:.3f}')
drill += ['T00', 'M30']
with open(os.path.join(OUT, 'RFH-2-cover.TXT'), 'w', newline='\n') as f:
    f.write('\n'.join(drill) + '\n')

# machine-readable record of intent, for the validator to check against
spec = {'board': [BW, BH],
        'switches': {k: list(v) for k, v in switches.items()},
        'mount_holes': [list(h) for h in mount_holes],
        'plunger_dia': PLUNGER_HOLE_DIA,
        'labels': [[l[0], l[1], l[2], l[3]] for l in labels],
        'n_arrows': len(arrows)}
json.dump(spec, open(SPEC, 'w'), indent=1)

print(f'\nwrote {len(os.listdir(OUT))} files to {OUT}')
print(f'silk strokes  : {n_strokes}')
