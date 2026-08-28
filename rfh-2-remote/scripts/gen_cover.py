#!/usr/bin/env python3
"""
Generate RS-274X gerbers + Excellon drill for an RFH-2 top cover panel.

All geometry is derived from RFH-2.brd -- nothing is hand-typed.
Written as plain text so that validation (gerbonara) is an independent parse.
"""
import xml.etree.ElementTree as ET
import os, math, json
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
    with open(os.path.join(OUT, fn), 'w') as f:
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
with open(os.path.join(OUT, 'RFH-2-cover.TXT'), 'w') as f:
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
