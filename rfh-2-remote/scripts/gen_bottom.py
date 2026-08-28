#!/usr/bin/env python3
"""
RFH-2 bottom plate with an operating reference on the outward face.

Content is laid out programmatically and every line is measured against the
usable area and against the mounting-hole keepouts, so a too-long line fails
the build instead of silently running off the board.

Band data: FCC 97.301 allocations as published in the ARRL band chart,
rev 1/16/2026 (includes the WRC-15 60m segment effective 13 Feb 2026).
Frequencies are regulatory fact; nothing is copied from ARRL's layout.
"""
import xml.etree.ElementTree as ET
import os, json, sys
from gerbonara.newstroke import Newstroke

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BRD = os.environ.get('RFH2_BRD', os.path.join(PROJ, 'upstream', 'RFH-2.brd'))
OUT = os.environ.get('RFH2_BOTTOM_OUT', os.path.join(PROJ, 'build', 'bottom_gerbers'))
os.makedirs(OUT, exist_ok=True)

CALL = 'KM7HKM / WA7DAM'
SILK_W, OUTLINE_W = 0.16, 0.10
MARGIN, HOLE_KEEPOUT = 3.5, 3.6

root = ET.parse(BRD).getroot()
mount = [(float(h.get('x')), float(h.get('y')), float(h.get('drill')))
         for h in root.iter('hole')]
ow = [(float(w.get('x1')), float(w.get('y1')), float(w.get('x2')), float(w.get('y2')))
      for w in root.find('.//plain').iter('wire') if w.get('layer') == '20']
xs = [c for w in ow for c in (w[0], w[2])]; ys = [c for w in ow for c in (w[1], w[3])]
BW, BH = max(xs)-min(xs), max(ys)-min(ys)

font = Newstroke.load()

def strokes_for(s, size):
    ref = list(font.render('M', size=size, x0=0, y0=0))
    base = max(p[1] for st in ref for p in st)
    return [[(px, base - py) for px, py in st] for st in font.render(s, size=size)]

def width_of(s, size):
    st = strokes_for(s, size)
    if not st: return 0.0
    return max(p[0] for k in st for p in k)

BANDS = [
    ('160m', '1.800-2.000',   '1.800-2.000'),
    ('80m',  '3.525-3.600',   '3.800-4.000'),
    ('60m',  '5 chan USB',    '9.15W WRC seg'),
    ('40m',  '7.025-7.125',   '7.175-7.300'),
    ('30m',  '10.100-10.150', 'no phone'),
    ('20m',  '14.025-14.150', '14.225-14.350'),
    ('17m',  '18.068-18.110', '18.110-18.168'),
    ('15m',  '21.025-21.200', '21.275-21.450'),
    ('12m',  '24.890-24.930', '24.930-24.990'),
    ('10m',  '28.000-28.300', '28.300-29.700'),
    ('6m',   '50.0-50.1',     '50.1-54.0'),
    ('2m',   '144.0-144.1',   '144.1-148.0'),
    ('1.25m','222.0-225.0',   '222.0-225.0'),
    ('70cm', '420-450',       '420-450'),
]
QCODES = [
    ('QRL', 'freq in use?'),   ('QRZ', 'who is calling'),
    ('QRM', 'interference'),   ('QSB', 'signal fading'),
    ('QRN', 'static noise'),   ('QSL', 'acknowledged'),
    ('QRO', 'increase pwr'),   ('QSO', 'a contact'),
    ('QRP', 'reduce power'),   ('QSY', 'change freq'),
    ('QRS', 'send slower'),    ('QTH', 'my location'),
    ('QRT', 'closing down'),   ('QRG', 'exact freq'),
    ('QRV', 'ready to copy'),  ('QTR', 'correct time'),
    ('QRX', 'stand by'),       ('QSK', 'break-in ok'),
]
SIMPLEX = [
    '6m 52.525    2m 146.520    70cm 446.000',
    'offset  2m +/-600k   70cm +/-5M   6m -500k',
    'RST  R1-5 readable  S1-9 strength  T1-9 tone',
    '73 regards  DE from  K over  SK end  CQ calling',
]

H_TITLE, H_HEAD, H_BODY = 2.4, 1.7, 1.45
P_BODY = 2.05

x0, x1 = MARGIN, BW - MARGIN
# start below the top mounting-hole keepouts, end above the bottom ones
y_top = min(h[1] for h in mount if h[1] > BH/2) - HOLE_KEEPOUT - 1.0
y_bot = MARGIN
avail_w = x1 - x0

lines = []
y = y_top - H_TITLE

def put(txt, x, size):
    lines.append((txt, x, y, size))

def nl(p):
    global y
    y -= p

put(CALL, x0, H_TITLE); nl(H_TITLE + 1.0)
put('RFH-2 REMOTE  -  OPERATING REFERENCE', x0, H_HEAD); nl(H_HEAD + 1.6)

put('US BANDS  GENERAL  CW/DATA | PHONE', x0, H_HEAD); nl(H_HEAD + 1.0)
cw_x, ph_x = x0 + 11.0, x0 + 32.0
for b, cw, ph in BANDS:
    lines.append((b, x0, y, H_BODY))
    lines.append((cw, cw_x, y, H_BODY))
    lines.append((ph, ph_x, y, H_BODY))
    nl(P_BODY)

nl(1.4)
put('Q CODES', x0, H_HEAD); nl(H_HEAD + 1.0)
col2 = x0 + 34.0
for i in range(0, len(QCODES), 2):
    a = QCODES[i]
    lines.append((f'{a[0]} {a[1]}', x0, y, H_BODY))
    if i + 1 < len(QCODES):
        b = QCODES[i+1]
        lines.append((f'{b[0]} {b[1]}', col2, y, H_BODY))
    nl(P_BODY)

nl(1.4)
put('CALLING / REPORTS', x0, H_HEAD); nl(H_HEAD + 1.0)
for s in SIMPLEX:
    put(s, x0, H_BODY); nl(P_BODY)

errs = []
bottom = min(l[2] for l in lines)
if bottom < y_bot:
    errs.append(f'content overruns bottom margin by {y_bot-bottom:.2f} mm')
for txt, lx, ly, size in lines:
    w = width_of(txt, size)
    if lx + w > x1 + 0.01:
        errs.append(f'too wide by {lx+w-x1:.2f} mm: {txt!r}')
    for hx, hy, hd in mount:
        for cx in (hx, BW - hx):
            if (ly - 0.3 < hy + HOLE_KEEPOUT and ly + size + 0.3 > hy - HOLE_KEEPOUT
                    and lx < cx + HOLE_KEEPOUT and lx + w > cx - HOLE_KEEPOUT):
                errs.append(f'hits mounting hole: {txt!r}')

print(f'usable area   : {avail_w:.1f} x {y_top-y_bot:.1f} mm')
print(f'content height: {y_top-bottom:.1f} mm (bottom y={bottom:.1f}, margin {y_bot})')
print(f'text objects  : {len(lines)}')
wl = max(lines, key=lambda l: width_of(l[0], l[3]))
print(f'widest line   : {width_of(wl[0], wl[3]):.1f} mm  {wl[0]!r}')
if errs:
    print('\nLAYOUT ERRORS:')
    for e in sorted(set(errs)): print('  -', e)
    sys.exit(1)
print('layout fits\n')

def c(v): return f'{int(round(v*10000)):d}'
def hdr(n): return ['G04 RFH-2 bottom plate - generated from RFH-2.brd*',
                    'G75*', '%MOMM*%', '%FSLAX44Y44*%', '%LPD*%',
                    f'%IN{n}*%', '%IPPOS*%', 'G01*']
def write(fn, body):
    open(os.path.join(OUT, fn), 'w').write('\n'.join(body) + '\nM02*\n')
def polyline(pts):
    o = [f'X{c(pts[0][0])}Y{c(pts[0][1])}D02*']
    for x, yy in pts[1:]: o.append(f'X{c(x)}Y{c(yy)}D01*')
    return o

prof = hdr('Profile') + [f'%ADD10C,{OUTLINE_W:.6f}*%', 'D10*']
prof += polyline([(0,0),(BW,0),(BW,BH),(0,BH),(0,0)])
write('RFH-2-bottom.GKO', prof)

silk = hdr('Silkscreen Bottom') + [f'%ADD10C,{SILK_W:.6f}*%', 'D10*']
nseg = 0
for txt, lx, ly, size in lines:
    for st in strokes_for(txt, size):
        pts = [(BW - (px + lx), py + ly) for px, py in st]
        silk += polyline(pts); nseg += len(pts) - 1
write('RFH-2-bottom.GBO', silk)

for fn, nm in [('RFH-2-bottom.GTL','Copper Top'), ('RFH-2-bottom.GBL','Copper Bottom'),
               ('RFH-2-bottom.GTS','Soldermask Top'), ('RFH-2-bottom.GBS','Soldermask Bottom'),
               ('RFH-2-bottom.GTO','Silkscreen Top')]:
    write(fn, hdr(nm) + ['%ADD10C,0.100000*%'])

drill = ['M48','METRIC,TZ','FMAT,2','T01C5.000','G90','G05','%','T01']
drill += [f'X{hx:.3f}Y{hy:.3f}' for hx, hy, hd in mount]
drill += ['T00','M30']
open(os.path.join(OUT,'RFH-2-bottom.DRL'),'w').write('\n'.join(drill)+'\n')

json.dump({'board':[BW,BH], 'mount_holes':[list(h) for h in mount],
           'n_lines':len(lines), 'callsign':CALL},
          open(os.path.join(PROJ, 'build', 'bottom_spec.json'), 'w'), indent=1)
print(f'silk segments : {nseg}')
print(f'wrote {len(os.listdir(OUT))} files')
