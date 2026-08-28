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

# USB dial frequencies in MHz. These are conventions rather than allocations:
# unlike the band edges above, they move by consensus.
DIGITAL = [
    ('160m', '1.840'), ('80m', '3.573'), ('60m', '5.357'), ('40m', '7.074'),
    ('30m', '10.136'), ('20m', '14.074'), ('17m', '18.100'), ('15m', '21.074'),
    ('12m', '24.915'), ('10m', '28.074'), ('6m', '50.313'), ('2m', '144.174'),
]

QCODES = [
    ('QRL', 'freq busy?'),   ('QRZ', 'who calls'),   ('QRM', 'interference'),
    ('QSB', 'fading'),       ('QRN', 'static'),      ('QSL', 'acknowledged'),
    ('QRO', 'incr power'),   ('QSO', 'a contact'),   ('QRP', 'redu power'),
    ('QSY', 'change freq'),  ('QRS', 'send slower'), ('QTH', 'my location'),
    ('QRT', 'closing down'), ('QRG', 'exact freq'),  ('QRV', 'ready'),
    ('QTR', 'correct time'), ('QRX', 'stand by'),    ('QSK', 'break-in ok'),
]

SIGNAL = [
    'RST  R 1-5 readable   S 1-9 strength   T 1-9 tone (CW only)',
    'S9 = 50 uV/50 ohm   1 S-unit = 6 dB   +3 dB = 2x   +6 dB = 4x',
    'DIPOLE 468/f(MHz) ft   VERT 234/f ft   WAVELEN 300/f(MHz) m',
]

OPERATING = [
    'SIMPLEX  6m 52.525   2m 146.520   1.25m 223.500   70cm 446.000',
    'OFFSET   6m -500k   2m +/-600k   1.25m -1.6M   70cm +/-5M',
    'SSTV 14.230   PSK31 14.070   APRS 144.390   SAT call 145.990',
    'EMERG  marine ch16 156.800   air 121.500   NOAA 162.400-.550',
    'UTC = PST+8 = PDT+7    73 regards   88 love   DE from   K over',
]

H_TITLE, H_HEAD, H_BODY = 2.3, 1.5, 1.25
P_BODY = 1.65

x0, x1 = MARGIN, BW - MARGIN
# Stay clear of the mounting-hole keepouts at both ends of the board, so every
# line can run the full width instead of dodging holes at the bottom.
y_top = min(h[1] for h in mount if h[1] > BH/2) - HOLE_KEEPOUT - 1.0
y_bot = max(h[1] for h in mount if h[1] < BH/2) + HOLE_KEEPOUT + 0.2
avail_w = x1 - x0

lines = []
y = y_top - H_TITLE

def put(txt, x, size):
    lines.append((txt, x, y, size))

def nl(p):
    global y
    y -= p

def head(txt):
    """Section heading, with the space above it that separates sections."""
    put(txt, x0, H_HEAD)
    nl(H_HEAD + 0.7)

def row(cells):
    """One row of (text, x) cells at body size."""
    for txt, x in cells:
        lines.append((txt, x, y, H_BODY))
    nl(P_BODY)

put(CALL, x0, H_TITLE); nl(H_TITLE + 0.8)
put('RFH-2 REMOTE  -  OPERATING REFERENCE', x0, H_HEAD); nl(H_HEAD + 1.3)

head('US BANDS  GENERAL   CW/DATA | PHONE')
cw_x, ph_x = x0 + 10.0, x0 + 30.0
for b, cw, ph in BANDS:
    row([(b, x0), (cw, cw_x), (ph, ph_x)])

nl(0.8)
head('FT8 USB DIAL  MHz')
# four bands per row; the table would otherwise cost twice the height
dig_x = [x0, x0 + 7.5, x0 + 18.0, x0 + 25.5, x0 + 36.0, x0 + 43.0, x0 + 53.5, x0 + 60.5]
for i in range(0, len(DIGITAL), 4):
    cells = []
    for j, (band, freq) in enumerate(DIGITAL[i:i + 4]):
        cells += [(band, dig_x[j * 2]), (freq, dig_x[j * 2 + 1])]
    row(cells)

nl(0.8)
head('Q CODES')
qcol = [x0, x0 + 23.5, x0 + 47.0]
for i in range(0, len(QCODES), 3):
    row([(f'{code} {meaning}', qcol[j])
         for j, (code, meaning) in enumerate(QCODES[i:i + 3])])

nl(0.8)
head('SIGNAL REPORTS AND FORMULAS')
for s in SIGNAL:
    row([(s, x0)])

nl(0.8)
head('OPERATING')
for s in OPERATING:
    row([(s, x0)])

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

# Multi-column rows can collide with each other, which a right-margin check
# alone will not catch. Compare every pair of cells sharing a baseline.
COL_GAP = 0.8
rows_by_y = {}
for txt, lx, ly, size in lines:
    rows_by_y.setdefault(round(ly, 3), []).append((lx, txt, size))
for ly, cells in rows_by_y.items():
    cells.sort()
    for (ax, atxt, asize), (bx, btxt, bsize) in zip(cells, cells[1:]):
        right = ax + width_of(atxt, asize)
        if right + COL_GAP > bx:
            errs.append(
                f'columns collide at y={ly:.1f}: {atxt!r} ends {right:.1f}, '
                f'{btxt!r} starts {bx:.1f}'
            )

print(f'usable area   : {avail_w:.1f} x {y_top-y_bot:.1f} mm')
print(f'content height: {y_top-bottom:.1f} mm (bottom y={bottom:.1f}, margin {y_bot})')
print(f'vertical spare: {bottom-y_bot:.1f} mm')
print(f'text objects  : {len(lines)}  rows {len(rows_by_y)}')
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
    # newline='\n' so a Windows run produces the same bytes as a Linux one.
    open(os.path.join(OUT, fn), 'w', newline='\n').write('\n'.join(body) + '\nM02*\n')
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
open(os.path.join(OUT,'RFH-2-bottom.DRL'),'w',newline='\n').write('\n'.join(drill)+'\n')

json.dump({'board':[BW,BH], 'mount_holes':[list(h) for h in mount],
           'n_lines':len(lines), 'callsign':CALL},
          open(os.path.join(PROJ, 'build', 'bottom_spec.json'), 'w'), indent=1)
print(f'silk segments : {nseg}')
print(f'wrote {len(os.listdir(OUT))} files')
